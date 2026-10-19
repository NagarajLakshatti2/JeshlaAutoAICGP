"""Compatibility alias for agent.providers.tools; existing callers remain supported."""
import sys
from agent.providers import tools as _implementation

# Preserve live module globals, exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
