"""Compatibility alias for agent.runtime.timing."""
import sys
from agent.runtime import timing as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
