"""Compatibility alias for agent.storage.chats; saved state is unchanged."""
import sys
from agent.storage import chats as _implementation

# Preserve class/exception identity and legacy patch targets.
sys.modules[__name__] = _implementation
