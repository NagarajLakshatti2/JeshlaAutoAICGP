"""Compatibility alias for agent.providers.text; existing callers remain supported."""
import sys
from agent.providers import text as _implementation

# Preserve live module globals, exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
