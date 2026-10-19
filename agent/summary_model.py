"""Compatibility alias for agent.runtime.summary_model."""
import sys
from agent.runtime import summary_model as _implementation

# Preserve shared locks/context variables, function globals and legacy patching.
sys.modules[__name__] = _implementation
