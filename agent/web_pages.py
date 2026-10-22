"""Compatibility alias for agent.tools.web_pages."""
import sys
from agent.tools import web_pages as _implementation

# Share implementation globals and preserve existing imports and patches.
sys.modules[__name__] = _implementation
