"""Compatibility alias for agent.actions.browser; saved state is unchanged."""
import sys
from agent.actions import browser as _implementation

# Preserve class/exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
