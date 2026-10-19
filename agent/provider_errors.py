"""Compatibility alias for agent.providers.errors; existing callers remain supported."""
import sys
from agent.providers import errors as _implementation

# Preserve live module globals, exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
