"""Resolve a chat's local project folder without changing global configuration."""
import os
from pathlib import Path
import re
from agent.storage.projects import ProjectConfigurationError


def _declared_path(value):
    """Keep full folder names intact; accept one unambiguous sentence boundary."""
    raw=value.strip()
    if raw[:1] in {chr(34),chr(39)}:
        end=raw.find(raw[0],1)
        if end<1 or (raw[end+1:].strip() and not re.match(r"^\.(?:\s|$)",raw[end+1:].strip())):
            raise ProjectConfigurationError("Quote the complete project folder and put following instructions after a period or on a new line.")
        return Path(raw[1:end]).expanduser()
    # Prefer a complete existing path, including folder names containing '. '.
    full=Path(raw[:-1].rstrip() if raw.endswith(".") else raw).expanduser()
    if full.is_absolute() and full.is_dir():return full
    candidates={}
    for boundary in re.finditer(r"\.\s+",raw):
        path=Path(raw[:boundary.start()].rstrip()).expanduser()
        if path.is_absolute() and path.is_dir():
            candidates[os.path.normcase(str(path.resolve()))]=path
    if len(candidates)>1:
        raise ProjectConfigurationError("Ambiguous project root. Put the folder on its own line or quote the complete path.")
    return next(iter(candidates.values())) if candidates else full


def resolve_project_root(state, default_root):
    # Only explicit user declaration lines can change the boundary. Model output,
    # memories, documents and tool results are never consulted.
    from agent.runtime.input_evidence import split_uploaded_input
    question=split_uploaded_input(state.get("question",""))[0]
    declarations = re.findall(
        r"^\s*(?:(?:my\s+)?project\s+root\s+is\s+|PROJECT\s+ROOT\s*:\s*)(.+?)\s*$",
        question, flags=re.I | re.M)
    if len(declarations)>1:
        raise ProjectConfigurationError("Provide one project-root declaration per message.")
    if declarations:
        path=_declared_path(declarations[0])
        if not path.is_absolute():
            raise ProjectConfigurationError("Project root must be an absolute folder path.")
    else:
        path=Path(state.get("project_root") or os.getenv("AI_PROJECT_ROOT") or default_root).expanduser()
    if state.get("project_id"):
        from agent.storage.projects import validate_local_folder
        bound=validate_local_folder(state.get("bound_project_root",""))
        if bound!=state.get("bound_project_root"):
            raise ProjectConfigurationError("The selected project folder changed. Review its registration.")
        if declarations and str(path.resolve())!=bound:
            raise ProjectConfigurationError("This chat belongs to the selected project. Switch Projects to use a different folder.")
        path=Path(bound)
    path=path.resolve()
    if not path.is_dir():
        raise ProjectConfigurationError("Project root must be an existing directory accessible to the agent.")
    return str(path)
