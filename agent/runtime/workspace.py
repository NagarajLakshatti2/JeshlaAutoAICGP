"""UI-facing workspace operations; no implicit account access on project selection."""
from urllib.parse import urlsplit
from agent.storage.projects import ProjectConfigurationError


class WorkspaceSupport:
    def prepare_new_project(self, name, parent, template, package):
        import re
        from agent.storage.projects import validate_local_folder
        from agent.tools.project_tools import ProjectTools
        from agent.tools.project_creation import starter_files
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ProjectConfigurationError("Enter a project name of 1–100 characters.")
        folder_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-")
        root = validate_local_folder(parent)
        tools = ProjectTools(root)
        plan = tools.prepare_project(folder_name, starter_files(folder_name, template, package))["plan"]
        proposal = {"project_root": root, "action": "create_project", "arguments": {"plan": plan}}
        actions = self.actions()
        for old in actions.pending(self.user, self.space, "project-setup"):
            actions.decline(self.user, self.space, "project-setup", old["id"])
        token = actions.propose(self.user, self.space, "project-setup", "create_project", proposal)
        return {"token": token, "proposal": proposal, "name": name.strip()}

    def new_project_status(self, token):
        actions = self.actions()
        row = actions._row(self.user, self.space, "project-setup", token)
        import json
        if json.loads(row["proposal"])["action"] != "create_project":
            raise ProjectConfigurationError("This is not a new-project review.")
        receipt = actions.receipts.get(token)
        return {"proposal": row["status"], "receipt": receipt["status"] if receipt else None}

    def cancel_new_project(self, token):
        self.actions().decline(self.user, self.space, "project-setup", token)

    def create_new_project(self, token, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ProjectConfigurationError("Enter a project name of 1–100 characters.")
        actions = self.actions()
        row = actions._row(self.user, self.space, "project-setup", token)
        import json
        if json.loads(row["proposal"])["action"] != "create_project":
            raise ProjectConfigurationError("Prepare a new-project review first.")
        result, replayed = actions.execute(self.user, self.space, "project-setup", token)
        project = self.project_store().add_local(name.strip(), result["project_root"])
        return {"project": project, "creation": result, "replayed": replayed, "receipt": token}

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

    def git_changes(self):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import changes
        return changes(selected_git_project(self))

    def review_git_commit(self,paths,message,author_name,author_email):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import prepare_commit
        return prepare_commit(selected_git_project(self),paths,message,author_name,author_email)

    def review_git_push(self):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import prepare_push
        project=selected_git_project(self)
        token=self.repository_credential(project["remote_url"],project.get("account_id",""))
        review=prepare_push(project,token)
        self.actions().reconcile_git_push_review(self.user,self.space,review,credential=token)
        return review

    def queue_git_review(self,session,review):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import project_data
        if not self.catalog.get(session):raise ProjectConfigurationError("Open a chat in this project first.")
        project=selected_git_project(self)
        if review.get("project")!=project_data(project) or review.get("kind") not in {"git_commit","git_push"}:
            raise ProjectConfigurationError("Prepare a review for this selected project.")
        proposal={"project_root":project["root"],"action":review["kind"],"arguments":{"review":review}}
        return self.actions().propose(self.user,self.space,session,review["kind"],proposal)
