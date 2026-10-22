"""Compatibility alias for agent.interfaces.action_approval."""
import sys
from agent.interfaces import action_approval as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
