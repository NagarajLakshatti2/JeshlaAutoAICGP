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
        if kind=="jira_mcp":
            if env_name or token:
                raise ProjectConfigurationError("Jira MCP profiles do not accept API tokens here; no service was contacted.")
            try:
                parsed=urlsplit(endpoint.strip() if isinstance(endpoint,str) else "")
                port=parsed.port
            except ValueError:
                raise ProjectConfigurationError("Enter a Jira site URL such as https://your-company.atlassian.net.") from None
            host=(parsed.hostname or "").lower()
            if (parsed.scheme!="https" or not host.endswith(".atlassian.net") or
                parsed.username or parsed.password or port not in (None,443) or
                parsed.path not in ("","/") or parsed.query or parsed.fragment):
                raise ProjectConfigurationError("Enter a Jira site URL such as https://your-company.atlassian.net.")
            site_url=f"https://{host}"
            return self.connection_store().save(kind,label,"https://mcp.atlassian.com/v2/mcp",
                                                details={"jira_site_url":site_url})
        if kind.endswith("_mcp"):raise ProjectConfigurationError("This MCP connector is parked for the free-only plan; no service was contacted.")
        endpoint={"github":"https://api.github.com","gitlab":"https://gitlab.com"}.get(kind,"")
        return self.connection_store().save(kind,label,endpoint,env_name=env_name,token=token)

    def test_connection(self,key):
        store=self.connection_store();row=store.get(key)
        if not row:raise ProjectConfigurationError("Connection not found.")
        if row["kind"] in {"github","gitlab"}:
            token=store.credential(key)
            from integrations.git.accounts import check_account
            details=check_account(row["kind"],token)
        elif row["kind"]=="jira_mcp":
            import asyncio
            from integrations.jira.jira_mcp_client import CatalogOAuthTokenStorage,jira_session,get_cloud_id,validate_site_url
            site=row.get("details",{}).get("jira_site_url","")
            try:site=validate_site_url(site)
            except ValueError:raise ProjectConfigurationError("Review the Jira site URL before connecting this profile.") from None
            token_storage=CatalogOAuthTokenStorage(store,key)
            async def verify_jira_site():
                async with jira_session(token_storage=token_storage,jira_site_url=site) as session:
                    cloud_id=await get_cloud_id(session,jira_site_url=site)
                    return {"jira_site_url":site,"cloud_id":cloud_id}
            try:details=asyncio.run(verify_jira_site())
            except Exception:
                raise ProjectConfigurationError("Jira sign-in or site verification failed. Check account access and try again.") from None
        else:
            raise ProjectConfigurationError("MCP is parked for the free-only plan; no service was contacted.")
        store.checked(key,details)
        return store.get(key)

    def repository_credential(self,url,account_id):
        from integrations.git.repositories import repository_url
        if urlsplit(repository_url(url)).scheme == "ssh":
            if account_id:
                raise ProjectConfigurationError("SSH projects use the local SSH agent or keys. Choose no token account.")
            return ""
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
        if kind!="jira_mcp":raise ProjectConfigurationError("Only Jira MCP project assignments are supported in this setup slice.")
        if not self.project_store().get(project_id):raise ProjectConfigurationError("Project not found in this workspace.")
        connection=self.connection_store().get(connection_id) if connection_id else None
        if not connection or connection["kind"]!=kind:
            raise ProjectConfigurationError("Choose a saved Jira MCP profile from this workspace.")
        if not isinstance(options,dict) or set(options)-{"project_key"}:
            raise ProjectConfigurationError("Only a Jira project key can be assigned here.")
        import re
        project_key=options.get("project_key")
        if not isinstance(project_key,str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}",project_key):
            raise ProjectConfigurationError("Use a valid uppercase Jira project key.")
        self.project_store().set_binding(project_id,kind,connection_id,{"project_key":project_key})

    def remove_connection_assignment(self,project_id,kind):
        if kind!="jira_mcp":raise ProjectConfigurationError("Only Jira MCP project assignments are supported in this setup slice.")
        self.project_store().remove_binding(project_id,kind)

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

    def prepare_git_pr(self, base, head, title, body):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import prepare_pull_request
        return prepare_pull_request(selected_git_project(self), base, head, title, body)

    def review_git_branch(self, name):
        from agent.runtime.git_workspace import selected_git_project
        from integrations.git.writes import prepare_branch
        return prepare_branch(selected_git_project(self), name)

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
        if review.get("project")!=project_data(project) or review.get("kind") not in {"git_commit","git_push","git_branch"}:
            raise ProjectConfigurationError("Prepare a review for this selected project.")
        proposal={"project_root":project["root"],"action":review["kind"],"arguments":{"review":review}}
        return self.actions().propose(self.user,self.space,session,review["kind"],proposal)
