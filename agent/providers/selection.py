"""Per-request provider choice; no shared environment or global provider mutation."""
from contextlib import contextmanager
from contextvars import ContextVar

_selected=ContextVar("selected_model_provider",default=None)


def current_provider(default):return _selected.get() or default


@contextmanager
def provider_selection(provider):
    if provider not in {"ollama","openrouter","groq","gemini"}:raise ValueError("Choose a supported provider.")
    token=_selected.set(provider)
    try:yield
    finally:_selected.reset(token)


_output_limit_mode=ContextVar("output_limit_passthrough",default=None)


@contextmanager
def output_limit_passthrough(*, data_only=False):
    """Let the conversation composer handle truncation; never accept a draft."""
    token=_output_limit_mode.set("data" if data_only else "text")
    try:yield
    finally:_output_limit_mode.reset(token)


def defer_output_limit(error):
    mode=_output_limit_mode.get()
    return mode=="data" or (mode=="text" and not getattr(error,"tool_call_output",False))
