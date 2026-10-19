"""Compatibility alias for agent.runtime.context."""
import sys
from agent.runtime import context as _implementation

# Preserve shared locks/context variables, function globals and legacy patching.
sys.modules[__name__] = _implementation
