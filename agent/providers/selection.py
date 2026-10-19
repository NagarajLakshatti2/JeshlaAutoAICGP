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
