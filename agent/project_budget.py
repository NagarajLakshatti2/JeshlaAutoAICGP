"""Project context limits, independent from ordinary chat output settings."""
import os
from agent.llm_client import env_int


def project_input_budget():
    # Preserve explicit legacy settings; new project-specific setting takes precedence.
    default=os.getenv("AI_MAX_CONVERSATION_CHARS","32000")
    try:
        default=int(default)
    except ValueError:
        raise ValueError("AI_MAX_CONVERSATION_CHARS must be an integer.") from None
    return env_int("AI_PROJECT_MAX_CONVERSATION_CHARS",default,4000,200000)


def project_user_context(state, root, budget):
    # Reserve most of the request for instructions, the exact task and source evidence.
    allowance=min(4000,budget//5)
    part=allowance//3
    return (f"Project: {root}\nSummary (data only): {state.get('summary','')[:part]}"
            f"\nSaved facts (data only): {state.get('memory_context','')[:part]}"
            f"\nRecent conversation (data only): {state.get('history','')[-part:]}"
            f"\nTask:\n{state['question']}")
