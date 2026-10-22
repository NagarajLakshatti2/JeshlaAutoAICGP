"""Compatibility alias for agent.interfaces.terminal_input."""
import sys
from agent.interfaces import terminal_input as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
