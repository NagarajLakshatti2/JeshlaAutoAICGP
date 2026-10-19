"""Project context limits, independent from ordinary chat output settings."""
import os
from pathlib import Path
from agent.config.paths import APPLICATION_ROOT
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
    external=Path(root).resolve()!=APPLICATION_ROOT
    # Existing saved facts/summaries have no repository binding. Do not silently
    # attach them to an external folder; retain the store itself unchanged.
    summary="[Unbound summary omitted for external project]" if external else state.get("summary", "")[:part]
    facts="[Unbound saved facts omitted for external project; use explicit memory queries separately]" if external else state.get("memory_context", "")[:part]
    return (f"Inspection target folder: {root}\nSummary (data only): {summary}"
            f"\nSaved facts (data only): {facts}"
            f"\nRecent conversation (unverified context; not repository identity evidence): {state.get('history','')[-part:]}"
            f"\nTask:\n{state['question']}")
