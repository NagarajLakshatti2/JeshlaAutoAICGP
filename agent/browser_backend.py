"""Compatibility alias for agent.interfaces.browser."""
import sys
from agent.interfaces import browser as _implementation

# Streamlit factory patches and existing imports reach the same implementation.
sys.modules[__name__] = _implementation
