"""Shared secret-safe frontend error presentation."""
from agent.provider_errors import ProviderError


def user_error_message(error):
    if isinstance(error,ProviderError):
        return str(error)
    if isinstance(error,RuntimeError) and str(error).startswith("This chat is busy"):
        return "This chat is busy in another window. Try again when it finishes."
    return "The request could not complete. Check the selected provider and local configuration. Existing saved chats remain available."


def print_agent_error(error):
    print("Agent execution failed:",user_error_message(error))
    print("No success is claimed. For saved Jira work enter STATUS.")
