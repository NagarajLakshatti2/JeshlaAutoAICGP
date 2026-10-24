"""MCP connection placeholder: intentionally parked for the free-only UI plan."""
from agent.storage.projects import ProjectConfigurationError


def discover(endpoint,token=""):
    raise ProjectConfigurationError("MCP is parked for the free-only plan; no service was contacted.")
