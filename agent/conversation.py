"""Compatibility alias for agent.runtime.conversation."""
import sys
from agent.runtime import conversation as _implementation

# Preserve shared locks/context variables, function globals and legacy patching.
sys.modules[__name__] = _implementation
