"""Compatibility alias for agent.policies.tool_registry; existing imports remain valid."""
import sys
from agent.policies import tool_registry as _implementation

# Alias the module itself, preserving function globals and monkeypatch behavior.
sys.modules[__name__] = _implementation
