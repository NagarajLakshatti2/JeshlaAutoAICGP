"""Compatibility alias for agent.policies.clarification."""
import sys
from agent.policies import clarification as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
