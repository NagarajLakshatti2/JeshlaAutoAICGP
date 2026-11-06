"""Adapter keeping AutoGen AgentChat behind the existing validated tool contract."""
import json
import os
import queue
import subprocess
import threading
import atexit
import uuid
from datetime import datetime, timezone

from agent.providers.errors import ProviderError


class _AutoGenWorker:
    """Keep imports warm across model/tool turns; never replay a timed-out request."""
    def __init__(self):
        self._lock = threading.Lock()
        self._process = None
        self._responses = None
        self._stderr_log = None

    @staticmethod
    def _log(message):
        from agent.config.paths import DATA_ROOT
        path = DATA_ROOT / "outputs" / "logs" / "autogen-worker.log"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(datetime.now(timezone.utc).isoformat() + " " + message + "\n")
        except OSError:
            pass

    def _start(self):
        from agent.config.paths import APPLICATION_ROOT
        python = _worker_python()
        if python is None:
            raise ProviderError("autogen", "CONFIGURATION",
                "AutoGen is not installed in the isolated .venv-autogen environment. Install the optional multi-agent extra there.", attempts=0)
        try:
            from agent.config.paths import DATA_ROOT
            log_path = DATA_ROOT / "outputs" / "logs" / "autogen-worker.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self._stderr_log = log_path.open("a", encoding="utf-8")
            self._process = subprocess.Popen(
                [str(python), "-u", "-m", "integrations.autogen.worker"], cwd=APPLICATION_ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr_log,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._log("worker_started pid=" + str(self._process.pid))
        except OSError:
            if self._stderr_log is not None:
                self._stderr_log.close()
                self._stderr_log = None
            raise ProviderError("autogen", "CONNECTION", "The isolated AutoGen runtime could not start.", attempts=1) from None
        self._responses = queue.Queue()
        threading.Thread(target=self._read, args=(self._process.stdout, self._responses), daemon=True).start()

    @staticmethod
    def _read(stream, responses):
        try:
            for line in stream:
                responses.put(line)
        finally:
            responses.put(None)

    def request(self, provider, payload, timeout):
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._start()
            try:
                self._log("request_started provider=" + provider)
                self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self._process.stdin.flush()
                line = self._responses.get(timeout=timeout)
            except queue.Empty:
                self._log("request_timeout provider=" + provider + " pid=" + str(self._process.pid if self._process else "stopped"))
                self._stop()
                raise ProviderError(provider, "RESPONSE_TIMEOUT", "AutoGen did not complete within its request limit.", attempts=1) from None
            except (OSError, ValueError):
                self._stop()
                raise ProviderError(provider, "CONNECTION", "The isolated AutoGen runtime stopped unexpectedly.", attempts=1) from None
            if line is None:
                self._log("worker_exited_without_response provider=" + provider)
                self._stop()
                raise ProviderError(provider, "AUTOGEN_RUNTIME", "The isolated AutoGen runtime stopped unexpectedly.", attempts=1)
            try:
                result = json.loads(line)
                self._log("response_received provider=" + provider + " result=" + ("error" if result.get("error") else "ok"))
                return result
            except (ValueError, TypeError):
                raise ProviderError(provider, "AUTOGEN_RUNTIME", "The isolated AutoGen runtime returned an invalid response.", attempts=1) from None

    def _stop(self):
        process, self._process = self._process, None
        self._responses = None
        if process is None:return
        try:
            process.terminate()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            try:process.kill()
            except OSError:pass
        if self._stderr_log is not None:
            try:self._stderr_log.close()
            except OSError:pass
            self._stderr_log = None

    def close(self):
        with self._lock:self._stop()


_worker = _AutoGenWorker()
atexit.register(_worker.close)


def _worker_python():
    from agent.config.paths import APPLICATION_ROOT
    candidates = [APPLICATION_ROOT / ".venv-autogen" / "Scripts" / "python.exe",
                  APPLICATION_ROOT / ".venv-autogen" / "bin" / "python"]
    return next((path for path in candidates if path.is_file()), None)


def _call_worker(provider, messages, tools, *, max_tokens, json_mode=False):
    request = {"provider": provider, "messages": messages, "tools": tools, "max_tokens": max_tokens, "json_mode": bool(json_mode)}
    setting = "AUTOGEN_GEMINI_TOOL_TIMEOUT" if provider == "gemini" and tools else "AUTOGEN_TIMEOUT"
    default = 90 if setting == "AUTOGEN_GEMINI_TOOL_TIMEOUT" else 45
    try:timeout = int(os.getenv(setting, str(default)))
    except (ValueError, TypeError):timeout = default
    maximum = 180 if setting == "AUTOGEN_GEMINI_TOOL_TIMEOUT" else 600
    if not 15 <= timeout <= maximum:timeout = default
    result = _worker.request(provider, request, timeout)
    if not isinstance(result, dict):
        raise ProviderError(provider, "AUTOGEN_RUNTIME", "The isolated AutoGen runtime returned an invalid response.", attempts=1)
    if result.get("error"):
        status = result.get("status")
        category = result.get("category", "PROVIDER_TEMPORARY")
        raise ProviderError(provider, category, result["error"], status=status, attempts=1)
    calls = result.get("tool_calls", [])
    if not isinstance(calls, list) or len(calls) > 8:
        raise ProviderError(provider, "TOOL_OUTPUT", "AutoGen returned an invalid tool proposal. No tool was executed.", attempts=1)
    normalized = []
    for index, call in enumerate(calls):
        if not isinstance(call, dict) or set(call) != {"name", "arguments"} or not isinstance(call["name"], str) or not isinstance(call["arguments"], dict):
            raise ProviderError(provider, "TOOL_OUTPUT", "AutoGen returned an invalid tool proposal. No tool was executed.", attempts=1)
        # Tool-call IDs must remain unique across the whole conversation: the
        # host pairs each later tool result with its originating assistant
        # call and rejects reused IDs, even when a new worker request begins.
        normalized.append({"id": "autogen_" + uuid.uuid4().hex + "_" + str(index), "type": "function",
                           "function": {"name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False)}})
    if normalized:
        return {"content": "", "tool_calls": normalized}
    content = result.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ProviderError(provider, "INVALID_RESPONSE", "AutoGen returned an empty response.", attempts=1)
    return {"content": content, "tool_calls": []}


def call_tool_messages(messages, tools, *, max_tokens=None, forced_function=None, require_tool=False, json_mode=False):
    """Run the selected provider through AgentChat; the host still validates and runs tools."""
    from agent.providers.fallback import call_with_fallback
    from agent.providers.selection import current_provider
    from agent.providers.text import LLM_PROVIDER, env_int
    from agent.runtime.timing import timed

    if type(json_mode) is not bool or (json_mode and tools):
        raise ValueError("JSON output mode is only supported for text-only AutoGen requests.")
    offered = tools
    if forced_function:
        offered = [item for item in tools if item.get("function", {}).get("name") == forced_function]
    def invoke(provider):
        if max_tokens is not None:
            limit = max_tokens
        else:
            key, default = {"openrouter": ("OPENROUTER_MAX_TOKENS", 1024),
                            "groq": ("GROQ_MAX_TOKENS", 1024),
                            "gemini": ("GEMINI_MAX_TOKENS", 4096),
                            "ollama": ("OLLAMA_NUM_PREDICT", 1024)}[provider]
            limit = env_int(key, default, 64, 16384)
        return _call_worker(provider, messages, offered, max_tokens=limit, json_mode=json_mode)
    read_only = bool(offered) and all(
        item.get("type") == "function" and item.get("function", {}).get("name") in {
            "web_search", "fetch_web_page", "read_file", "validate_test_plan", "draft_test_observations",
            "submit_answer_review", "submit_documentation_plan", "submit_grounded_sections", "submit_grounding_findings"}
        for item in offered)
    return call_with_fallback(current_provider(LLM_PROVIDER), invoke,
                              allow_tool_output_fallback=read_only,
                              allow_transient_fallback=True)
