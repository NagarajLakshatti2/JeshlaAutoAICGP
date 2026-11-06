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
    required={"memory_user_id","memory_namespace","project_id","bound_project_root"}
    allowed=required|{"jira_scope"}
    if not isinstance(scope,dict) or set(scope) not in (required,allowed):
        raise ProjectConfigurationError("Invalid project request scope.")
    for key in ("memory_user_id","memory_namespace"):
        if not isinstance(scope[key],str) or not scope[key].strip() or len(scope[key])>128:
            raise ProjectConfigurationError("Invalid project memory scope.")
    project_namespace("validation",scope["project_id"])
    root=validate_local_folder(scope["bound_project_root"])
    if root!=scope["bound_project_root"]:
        raise ProjectConfigurationError("The configured project folder changed. Review its registration.")
    jira=scope.get("jira_scope")
    if jira is not None:
        import re
        base_fields={"connection_id","site_url","project_key","connected"}
        if (not isinstance(jira,dict) or set(jira) not in (base_fields,base_fields|{"connection_namespace"}) or
            not isinstance(jira.get("connection_id"),str) or not re.fullmatch(r"connection-[a-f0-9]{32}",jira["connection_id"]) or
            not isinstance(jira.get("site_url"),str) or not re.fullmatch(r"https://[a-z0-9.-]+\.atlassian\.net",jira["site_url"]) or
            not isinstance(jira.get("project_key"),str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}",jira["project_key"]) or
            type(jira.get("connected")) is not bool or
            "connection_namespace" in jira and (not isinstance(jira["connection_namespace"],str) or not jira["connection_namespace"].strip() or len(jira["connection_namespace"])>128)):
            raise ProjectConfigurationError("Invalid project Jira assignment scope.")
    return {**scope,"project_root":root}


def tools_for_state(state,default_root):
    from agent.runtime.project_context import resolve_project_root
    from agent.tools.project_tools import ProjectTools
    root=resolve_project_root(state,default_root)
    if state.get("project_id"):
        evidence=Path(default_root)/"outputs/acceptance/projects"/state["project_id"]
        jira=state.get("jira_scope")
        return ProjectTools(
            root, project_id=state["project_id"], evidence_root=evidence,
            jira_scope=jira,
            jira_user=state.get("memory_user_id"),
            jira_connection_namespace=(jira or {}).get("connection_namespace"),
            jira_catalog_path=Path(default_root)/"outputs/memory/connections.sqlite3",
        )
    return ProjectTools(root)
