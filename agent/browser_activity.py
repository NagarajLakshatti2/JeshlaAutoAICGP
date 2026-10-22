"""Compatibility alias for agent.interfaces.activity."""
import sys
from agent.interfaces import activity as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
