"""Bounded provider failover; truncated replies are discarded, never executed."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import ipaddress
import os
from urllib.parse import urlsplit

from agent.providers.errors import ProviderError
from agent.providers.selection import current_provider

ORDER = ("openrouter", "groq", "gemini", "ollama")
QUOTA_ERRORS = frozenset({"RATE_LIMIT", "QUOTA_EXHAUSTED"})
_turn = ContextVar("provider_fallback_turn", default=None)
_last = ContextVar("last_successful_model_provider", default=None)


def enabled():
    return os.getenv("LLM_FALLBACK_ENABLED", "false").strip().lower() == "true"


def configured_order():
    order = tuple(item.strip().lower() for item in os.getenv("LLM_FALLBACK_ORDER", ",".join(ORDER)).split(","))
    if not order or len(set(order)) != len(order) or any(item not in ORDER for item in order):
        raise ProviderError("model", "CONFIGURATION", "LLM_FALLBACK_ORDER must contain distinct supported provider names.", attempts=0)
    if tuple(sorted(order, key=ORDER.index)) != order:
        raise ProviderError("model", "CONFIGURATION", "Keep fallback order openrouter, groq, gemini, then optional ollama.", attempts=0)
    return order


def local_ollama_allowed():
    # A clone running on a local workstation is local. GitHub runners and hosted
    # deployments must never fall through to their own localhost Ollama port.
    if any(os.getenv(key, "").strip().lower() not in {"", "false", "0"}
           for key in ("GITHUB_ACTIONS", "CI", "CODESPACES", "STREAMLIT_SHARING_MODE")):
        return False
    return (os.getenv("AI_DEPLOYMENT_MODE", "local").strip().lower() == "local"
            and os.getenv("LLM_ALLOW_LOCAL_OLLAMA", "false").strip().lower() == "true")


def _check_local_endpoint():
    from agent.providers.text import OLLAMA_URL
    for endpoint in {OLLAMA_URL, os.getenv("OLLAMA_URL", OLLAMA_URL)}:
        _validate_loopback(endpoint)


def _validate_loopback(endpoint):
    try:
        url = urlsplit(endpoint)
        loopback = url.hostname == "localhost" or ipaddress.ip_address(url.hostname or "").is_loopback
    except ValueError:
        raise ProviderError("ollama", "CONFIGURATION", "Quota fallback requires a valid local loopback Ollama URL.", attempts=0) from None
    if url.scheme not in {"http", "https"} or not loopback or url.username or url.password:
        raise ProviderError("ollama", "CONFIGURATION", "Quota fallback requires a local loopback Ollama URL.", attempts=0)


def _configured(provider):
    if provider == "ollama":
        return True
    if provider == "gemini":
        from agent.providers.gemini import KEY_NAMES
        return bool(os.getenv("GEMINI_MODEL", "").strip()) and any(os.getenv(key, "").strip() for key in KEY_NAMES)
    prefix = provider.upper()
    return bool(os.getenv(prefix + "_API_KEY", "").strip() and os.getenv(prefix + "_MODEL", "").strip())


def last_provider(default):
    requested = current_provider(default)
    last = _last.get()
    return last[1] if last and last[0] == requested else requested


@contextmanager
def fallback_scope():
    state = {"exhausted": set(), "notices": [], "last_error": None, "failures": {}}
    token = _turn.set(state)
    previous = _last.set(None)
    try:
        yield state["notices"]
    finally:
        _last.reset(previous)
        _turn.reset(token)


def messages_for_provider(messages, provider, *, imported_history=False):
    result = deepcopy(messages)
    if provider != "gemini":
        # Google thought signatures are opaque provider-specific metadata.
        for message in result:
            message.pop("extra_content", None)
            for call in message.get("tool_calls") or []:
                call.pop("extra_content", None)
    elif imported_history:
        # Google documents this marker specifically for traces imported from
        # other models. Preserve real signatures and parallel-call grouping.
        for message in result:
            calls = message.get("tool_calls") or []
            if calls and not any(call.get("extra_content", {}).get("google", {}).get("thought_signature") for call in calls):
                calls[0].setdefault("extra_content", {}).setdefault("google", {})["thought_signature"] = "skip_thought_signature_validator"
    return result


def call_with_fallback(default, invoke, *, allow_tool_output_fallback=False):
    requested = current_provider(default)
    if requested not in ORDER:
        raise ProviderError("model", "CONFIGURATION", "Set LLM_PROVIDER to openrouter, groq, gemini or ollama.", attempts=0)
    active = enabled()
    order = configured_order() if active else (requested,)
    candidates = order[order.index(requested):] if requested in order else (requested,)
    state = _turn.get() or {"exhausted": set(), "notices": [], "last_error": None, "failures": {}}
    last_error = state["last_error"]
    for provider in candidates:
        if provider == "ollama":
            # Direct local Ollama remains backward compatible; hosted execution
            # is forbidden even when fallback is disabled.
            hosted = os.getenv("AI_DEPLOYMENT_MODE", "local").strip().lower() != "local" or any(
                os.getenv(key, "").strip().lower() not in {"", "false", "0"}
                for key in ("GITHUB_ACTIONS", "CI", "CODESPACES", "STREAMLIT_SHARING_MODE"))
            if hosted or (active and provider != requested and not local_ollama_allowed()):
                continue
            if active:
                _check_local_endpoint()
        if active and provider in state["exhausted"]:
            continue
        # The first selected provider retains its original configuration errors.
        # Later providers without a key/model are skipped after quota exhaustion.
        if active and provider != requested and not _configured(provider):
            notice = f"Provider fallback: skipped {provider}; key/model is not configured."
            state["notices"].append(notice)
            print(notice)
            continue
        try:
            result = invoke(provider)
        except ProviderError as error:
            output_limit = error.category == "OUTPUT_LIMIT" and os.getenv("LLM_FALLBACK_ON_OUTPUT_LIMIT", "true").strip().lower() == "true"
            from agent.providers.selection import defer_output_limit
            if output_limit and defer_output_limit(error):
                raise
            # Only the native adapter may opt in for its confined read-only
            # registry. Never fail over arbitrary action/JSON-format errors.
            read_only_format = allow_tool_output_fallback and error.category == "TOOL_OUTPUT"
            if not active or (error.category not in QUOTA_ERRORS and not output_limit and not read_only_format):
                raise
            last_error = error
            state["last_error"] = error
            state["exhausted"].add(provider)
            state["failures"][provider] = error.category
            if read_only_format:
                reason = "rejected read-only tool output; invalid response discarded"
            else:
                reason = "reached its output-token limit; partial reply discarded" if output_limit else "reached its rate/quota limit"
            notice = f"Provider fallback: {provider} {reason}; trying the next configured provider."
            state["notices"].append(notice)
            print(notice)
            continue
        _last.set((requested, provider))
        if provider != requested:
            notice = f"Provider fallback: using {provider} for this turn."
            if notice not in state["notices"]:
                state["notices"].append(notice)
                print(notice)
        return result
    if last_error is not None:
        if len(state["failures"]) > 1:
            attempts = ", ".join(f"{name} ({category})" for name, category in state["failures"].items())
            failure=ProviderError(last_error.provider, last_error.category,
                "No complete response from eligible providers: " + attempts +
                ". Incomplete replies were discarded. Check provider budgets/quotas and tool-format compatibility or request a smaller scope.",
                status=last_error.status, attempts=last_error.attempts)
            failure.tool_call_output=getattr(last_error,"tool_call_output",False)
            raise failure from None
        raise last_error
    raise ProviderError(requested, "PROVIDERS_UNAVAILABLE", "No eligible provider remains in this turn. Ollama requires local execution and explicit fallback permission.", attempts=0)
