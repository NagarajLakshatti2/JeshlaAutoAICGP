"""Resolve a chat's local project folder without changing global configuration."""
import os
from pathlib import Path
import re


def resolve_project_root(state, default_root):
    # Only explicit user declaration lines can change the boundary. Model output,
    # memories, documents and tool results are never consulted.
    declarations = re.findall(
        r"^\s*(?:(?:my\s+)?project\s+root\s+is\s+|PROJECT\s+ROOT\s*:\s*)(.+?)\s*$",
        state.get("question", ""), flags=re.I | re.M)
    if len(declarations)>1:
        raise ValueError("Provide one project-root declaration per message.")
    if declarations:
        raw=declarations[0].strip()
        if raw.endswith("."): raw=raw[:-1].rstrip()
        if len(raw)>=2 and raw[0]==raw[-1] and raw[0] in {chr(34),chr(39)}:
            raw=raw[1:-1]
        path=Path(raw).expanduser()
        if not path.is_absolute():
            raise ValueError("Project root must be an absolute folder path.")
    else:
        path=Path(state.get("project_root") or os.getenv("AI_PROJECT_ROOT") or default_root).expanduser()
    path=path.resolve()
    if not path.is_dir():
        raise ValueError("Project root must be an existing directory accessible to the agent.")
    return str(path)
