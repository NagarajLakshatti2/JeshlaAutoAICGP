"""Per-request local-action policy; console approval is the default."""
from contextvars import ContextVar
from contextlib import contextmanager

approval_handler=ContextVar("approval_handler",default=None)

@contextmanager
def local_action_handler(handler):
    token=approval_handler.set(handler)
    try:yield
    finally:approval_handler.reset(token)
