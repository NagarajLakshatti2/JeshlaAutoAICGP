"""Compatibility alias for agent.runtime.summaries."""
import sys
from agent.runtime import summaries as _implementation

# Preserve shared locks/context variables, function globals and legacy patching.
sys.modules[__name__] = _implementation
