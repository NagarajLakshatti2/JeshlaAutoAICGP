"""Compatibility alias for agent.providers.gemini; existing callers remain supported."""
import sys
from agent.providers import gemini as _implementation

# Preserve live module globals, exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
