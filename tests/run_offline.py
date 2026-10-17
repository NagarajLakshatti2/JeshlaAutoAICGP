"""Run unit tests with external network and browser launches blocked.

From the project root: python tests/run_offline.py
Loopback sockets remain available for asyncio and local framework internals.
This guard applies to this Python process; it is not a sandbox for subprocesses.
"""
from contextlib import ExitStack, contextmanager
import ipaddress
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def is_loopback(address):
    if not isinstance(address, tuple) or not address:
        return False
    try:
        return ipaddress.ip_address(address[0]).is_loopback
    except ValueError:
        return False


@contextmanager
def offline_guard():
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def connect(sock, address):
        if not is_loopback(address):
            raise RuntimeError("Offline tests blocked an external socket connection")
        return original_connect(sock, address)

    def connect_ex(sock, address):
        if not is_loopback(address):
            raise RuntimeError("Offline tests blocked an external socket connection")
        return original_connect_ex(sock, address)

    def blocked(*args, **kwargs):
        raise RuntimeError("Offline tests require a mock for HTTP requests or browser launches")

    with ExitStack() as stack:
        stack.enter_context(patch("socket.socket.connect", connect))
        stack.enter_context(patch("socket.socket.connect_ex", connect_ex))
        stack.enter_context(patch("requests.sessions.Session.request", blocked))
        for name in ("open", "open_new", "open_new_tab"):
            stack.enter_context(patch("webbrowser." + name, blocked))
        yield


def main():
    with offline_guard():
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
