"""Compatibility alias for agent.runtime.project_decisions."""
import sys
from agent.runtime import project_decisions as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
