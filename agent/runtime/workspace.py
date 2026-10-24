"""UI-facing workspace operations; no implicit account access on project selection."""
from urllib.parse import urlsplit
from agent.storage.projects import ProjectConfigurationError


class WorkspaceSupport:
    def connection_store(self):
        from agent.storage.connections import ConnectionCatalog
        return ConnectionCatalog(self.project_store().path.with_name("connections.sqlite3"),
                                 self.user,getattr(self,"base_space",self.space))

    def save_connection(self,kind,label,endpoint="",*,env_name="",token=""):
        if kind.endswith("_mcp"):raise ProjectConfigurationError("MCP is parked for the free-only plan; no service was contacted.")
        endpoint={"github":"https://api.github.com","gitlab":"https://gitlab.com"}.get(kind,"")
        return self.connection_store().save(kind,label,endpoint,env_name=env_name,token=token)

    def test_connection(self,key):
        store=self.connection_store();row=store.get(key)
        if not row:raise ProjectConfigurationError("Connection not found.")
        token=store.credential(key)
        if row["kind"] in {"github","gitlab"}:
            from integrations.git.accounts import check_account
            details=check_account(row["kind"],token)
        else:
            raise ProjectConfigurationError("MCP is parked for the free-only plan; no service was contacted.")
        store.checked(key,details)
        return store.get(key)

    def repository_credential(self,url,account_id):
        if not account_id:return ""
        from integrations.git.repositories import repository_url
        host=urlsplit(repository_url(url)).hostname
        store=self.connection_store();row=store.get(account_id)
        expected="github" if host=="github.com" else "gitlab"
        if not row or row["kind"]!=expected:
            raise ProjectConfigurationError("Choose an account for the repository's Git provider.")
        return store.credential(account_id)

    def clone_project(self,name,url,destination,account_id=""):
        from integrations.git.repositories import clone_repository,repository_url
        if not isinstance(name,str) or not 1<=len(" ".join(name.split()))<=100:
            raise ProjectConfigurationError("Enter a project name of 1–100 characters.")
        url=repository_url(url);token=self.repository_credential(url,account_id)
        result=clone_repository(url,destination,token=token)
        project=self.project_store().add_local(name,result["root"])
        return self.project_store().configure_git(project["id"],url,account_id)

    def attach_git_project(self,name,folder,url,account_id=""):
        from integrations.git.repositories import repository_url,git_command
        from agent.storage.projects import validate_local_folder
        root=validate_local_folder(folder);url=repository_url(url)
        self.repository_credential(url,account_id)
        observed=git_command(["remote","get-url","origin"],cwd=root,timeout=15)
        if repository_url(observed)!=url:
            raise ProjectConfigurationError("The selected checkout has a different origin.")
        from pathlib import Path
        if Path(git_command(["rev-parse","--show-toplevel"],cwd=root,timeout=15)).resolve()!=Path(root):
            raise ProjectConfigurationError("Choose the repository's top-level working folder.")
        project=self.project_store().add_local(name,root)
        return self.project_store().configure_git(project["id"],url,account_id)

    def sync_project(self,project_id):
        from integrations.git.repositories import synchronize_repository
        project=self.project_store().get(project_id)
        if not project or project.get("source")!="git":
            raise ProjectConfigurationError("Choose a configured Git project.")
        token=self.repository_credential(project["remote_url"],project.get("account_id",""))
        return synchronize_repository(project,token=token)

    def assign_connection(self,project_id,kind,connection_id,options=None):
        if connection_id:
            connection=self.connection_store().get(connection_id)
            if not connection or connection["kind"]!=kind:
                raise ProjectConfigurationError("Choose a connection from this workspace.")
        options=options or {}
        import re
        if kind=="jira_mcp" and options.get("project_key") and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}",options["project_key"]):
            raise ProjectConfigurationError("Use a valid uppercase Jira project key.")
        self.project_store().set_binding(project_id,kind,connection_id,options)

    def update_project_account(self,project_id,account_id):
        project=self.project_store().get(project_id)
        if not project or project.get("source")!="git":raise ProjectConfigurationError("Choose a Git project.")
        self.repository_credential(project["remote_url"],account_id)
        return self.project_store().configure_git(project_id,project["remote_url"],account_id)
