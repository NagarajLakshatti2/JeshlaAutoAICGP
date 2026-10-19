"""Compatibility alias for agent.policies.routing; existing imports remain valid."""
import sys
from agent.policies import routing as _implementation

# Alias the module itself, preserving function globals and monkeypatch behavior.
sys.modules[__name__] = _implementation
