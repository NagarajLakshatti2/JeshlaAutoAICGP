"""Loopback-browser OAuth callback handling for the Atlassian MCP client."""
import asyncio
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import AuthorizationCodeResult


CALLBACK_HOST = "localhost"
CALLBACK_PORT = 3000
CALLBACK_PATH = "/callback"
CALLBACK_URL = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
MAX_REQUEST_LINE = 8192


def parse_callback_target(target):
    """Return a validated OAuth result from a bounded loopback request target."""
    if not isinstance(target, str) or len(target) > MAX_REQUEST_LINE:
        raise ValueError("Invalid OAuth callback request.")
    if not target.startswith("/") or target.startswith("//"):
        raise ValueError("Invalid OAuth callback target.")
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or parsed.path != CALLBACK_PATH or parsed.fragment:
        raise ValueError("Invalid OAuth callback path.")
    query = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=8)
    if query.get("error"):
        raise ValueError("Browser authorization was denied or failed; start again.")
    codes = query.get("code", [])
    states = query.get("state", [])
    issuers = query.get("iss", [])
    if len(codes) != 1 or len(states) != 1 or len(issuers) > 1:
        raise ValueError("OAuth callback is missing valid authorization data.")
    code = codes[0]
    state = states[0]
    issuer = issuers[0] if issuers else None
    if not code or not state or len(code) > 4096 or len(state) > 2048 or (issuer and len(issuer) > 2048):
        raise ValueError("OAuth callback is missing valid authorization data.")
    return AuthorizationCodeResult(code=code, state=state, iss=issuer)


class BrowserOAuthFlow:
    """Open consent in the user's browser and receive the one-time loopback callback."""

    def __init__(self, *, timeout=300, browser_open=None):
        self.timeout = timeout
        self.browser_open = browser_open
        self.server = None
        self.result = None

    async def redirect_handler(self, auth_url):
        parsed = urlparse(auth_url)
        if parsed.scheme != "https" or parsed.hostname != "auth.atlassian.com" or parsed.username or parsed.password:
            raise ValueError("Atlassian returned an unexpected authorization URL.")
        loop = asyncio.get_running_loop()
        self.result = loop.create_future()
        try:
            self.server = await asyncio.start_server(self._handle, CALLBACK_HOST, CALLBACK_PORT, limit=MAX_REQUEST_LINE)
        except OSError:
            raise ValueError("The local Jira sign-in callback is unavailable; close an existing sign-in attempt and retry.") from None
        open_browser = self.browser_open
        if open_browser is None:
            import webbrowser
            open_browser = webbrowser.open
        if not open_browser(auth_url):
            await self._close()
            raise ValueError("Could not open the Atlassian sign-in page in the browser.")

    async def callback_handler(self):
        if self.result is None:
            raise ValueError("The browser sign-in flow did not start.")
        try:
            return await asyncio.wait_for(self.result, timeout=self.timeout)
        except asyncio.TimeoutError:
            raise ValueError("Jira browser authorization timed out; no connection was verified.") from None
        finally:
            await self._close()

    async def _handle(self, reader, writer):
        status = "400 Bad Request"
        body = "Sign-in could not be completed. Return to JeshlaAutoAI and try again."
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=5)
            if len(request_line) > MAX_REQUEST_LINE:
                raise ValueError("Invalid OAuth callback request.")
            method, target, version = request_line.decode("ascii").strip().split(" ", 2)
            if method != "GET" or version not in {"HTTP/1.0", "HTTP/1.1"}:
                status = "405 Method Not Allowed"
                raise ValueError("Invalid OAuth callback method.")
            # Drain a small bounded header set. Header contents are not logged or retained.
            header_bytes = 0
            host_header = ""
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=5)
                header_bytes += len(line)
                if header_bytes > 8192:
                    raise ValueError("Invalid OAuth callback headers.")
                if line in {b"\r\n", b"\n", b""}:
                    break
                name, separator, value = line.decode("ascii", errors="strict").partition(":")
                if separator and name.strip().casefold() == "host":
                    host_header = value.strip().casefold()
            if host_header != f"{CALLBACK_HOST}:{CALLBACK_PORT}":
                raise ValueError("Invalid OAuth callback host.")
            result = parse_callback_target(target)
            if self.result is None or self.result.done():
                status = "409 Conflict"
                raise ValueError("This OAuth callback has already been used.")
            self.result.set_result(result)
            status = "200 OK"
            body = "Jira sign-in completed. You can return to JeshlaAutoAI."
        except Exception:
            if self.result is not None and not self.result.done():
                self.result.set_exception(ValueError("Jira browser authorization did not complete."))
        finally:
            encoded = body.encode("utf-8")
            writer.write(
                f"HTTP/1.1 {status}\r\nContent-Type: text/plain; charset=utf-8\r\n"
                f"Cache-Control: no-store\r\nContent-Length: {len(encoded)}\r\nConnection: close\r\n\r\n".encode("ascii")
                + encoded
            )
            try:
                await writer.drain()
            except (ConnectionError, OSError):
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    async def _close(self):
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
