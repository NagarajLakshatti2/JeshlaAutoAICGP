"""Request-local AutoGen/LangGraph selection; never a process-wide setting."""
from contextlib import contextmanager
from contextvars import ContextVar

_mode = ContextVar("jeshla_agent_mode", default="autogen")


def current_agent_mode():
    return _mode.get()


@contextmanager
def agent_mode_selection(mode):
    if mode not in {"autogen", "langgraph"}:
        raise ValueError("Select AutoGen or LangGraph agent mode.")
    token = _mode.set(mode)
    try:
        yield
    finally:
        _mode.reset(token)
