"""Compatibility alias for agent.runtime.turns."""
import sys
from agent.runtime import turns as _implementation

# Preserve shared locks/context variables, function globals and legacy patching.
sys.modules[__name__] = _implementation
