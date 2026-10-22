"""Compatibility alias for agent.runtime.project_budget."""
import sys
from agent.runtime import project_budget as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
