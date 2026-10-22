"""Compatibility alias for agent.interfaces.errors."""
import sys
from agent.interfaces import errors as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
