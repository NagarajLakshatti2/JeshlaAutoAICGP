"""Compatibility alias for agent.runtime.project_native_specs."""
import sys
from agent.runtime import project_native_specs as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
