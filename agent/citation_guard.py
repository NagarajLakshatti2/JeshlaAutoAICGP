"""Compatibility alias for agent.policies.citations."""
import sys
from agent.policies import citations as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
