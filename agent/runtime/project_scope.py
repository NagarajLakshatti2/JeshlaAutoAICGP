"""Explicit request state for project identity; no process-wide selection changes."""
import os
from pathlib import Path
from agent.storage.projects import ProjectConfigurationError,project_namespace,validate_local_folder


def memory_identity(state=None):
    state=state or {}
    return (state.get("memory_user_id") or os.getenv("AI_MEMORY_USER_ID","local-user"),
            state.get("memory_namespace") or os.getenv("AI_MEMORY_NAMESPACE","project"))


def validate_request_scope(scope):
    if scope is None:return {}
    allowed={"memory_user_id","memory_namespace","project_id","bound_project_root"}
    if not isinstance(scope,dict) or set(scope)!=allowed:
        raise ProjectConfigurationError("Invalid project request scope.")
    for key in ("memory_user_id","memory_namespace"):
        if not isinstance(scope[key],str) or not scope[key].strip() or len(scope[key])>128:
            raise ProjectConfigurationError("Invalid project memory scope.")
    project_namespace("validation",scope["project_id"])
    root=validate_local_folder(scope["bound_project_root"])
    if root!=scope["bound_project_root"]:
        raise ProjectConfigurationError("The configured project folder changed. Review its registration.")
    return {**scope,"project_root":root}


def tools_for_state(state,default_root):
    from agent.runtime.project_context import resolve_project_root
    from agent.tools.project_tools import ProjectTools
    root=resolve_project_root(state,default_root)
    if state.get("project_id"):
        evidence=Path(default_root)/"outputs/acceptance/projects"/state["project_id"]
        return ProjectTools(root,project_id=state["project_id"],evidence_root=evidence)
    return ProjectTools(root)
