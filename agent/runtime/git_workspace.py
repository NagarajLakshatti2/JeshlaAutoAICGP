"""Trusted workspace-only Git handlers; credentials never enter action arguments."""
from pathlib import Path
from agent.tools.project_tools import ProjectTools
from agent.storage.projects import ProjectConfigurationError
from integrations.git import writes


def selected_git_project(backend,root=None):
    if not getattr(backend,"project_id",None):
        raise ProjectConfigurationError("Select a saved Git project first.")
    scope=backend.request_scope()
    project=backend.project_store().get(backend.project_id)
    if not project or project.get("source")!="git":
        raise ProjectConfigurationError("Select a configured Git repository.")
    if root is not None and Path(root).resolve()!=Path(scope["bound_project_root"]):
        raise ProjectConfigurationError("This Git action belongs to another project.")
    return project


class WorkspaceActionTools(ProjectTools):
    def __init__(self,backend,root):
        super().__init__(root)
        self.backend=backend

    def _terminal_identity(self, chat_id):
        scope = self.backend.request_scope()
        if not scope or Path(scope["bound_project_root"]).resolve() != self.root:
            raise ProjectConfigurationError("Select the terminal's project.")
        if not self.backend.catalog.get(chat_id):
            raise ProjectConfigurationError("Terminal chat is unavailable.")
        return (self.backend.user, self.backend.space, chat_id, str(self.root))

    def terminal_start(self, chat_id: str, command: list, lifetime: int = 300):
        from agent.actions.terminal_sessions import start
        return start(self._terminal_identity(chat_id), self, command, lifetime)

    def terminal_input(self, chat_id: str, terminal_id: str, revision: int, text: str):
        from agent.actions.terminal_sessions import send
        return send(self._terminal_identity(chat_id), terminal_id, revision, text)

    def terminal_stop(self, chat_id: str, terminal_id: str, revision: int):
        from agent.actions.terminal_sessions import stop
        return stop(self._terminal_identity(chat_id), terminal_id, revision)

    def git_branch(self, review: dict):
        project = selected_git_project(self.backend, self.root)
        if review.get("project") != writes.project_data(project):
            raise ProjectConfigurationError("Project settings changed. Prepare a fresh review.")
        return writes.create_branch(project, review)

    def git_commit(self,review:dict):
        project=selected_git_project(self.backend,self.root)
        if review.get("project")!=writes.project_data(project):
            raise ProjectConfigurationError("Project/account settings changed. Prepare a new Git review.")
        return writes.commit(project,review)

    def git_push(self,review:dict):
        project=selected_git_project(self.backend,self.root)
        if review.get("project")!=writes.project_data(project):
            raise ProjectConfigurationError("Project/account settings changed. Prepare a new Git review.")
        token=self.backend.repository_credential(project["remote_url"],project.get("account_id",""))
        return writes.push(project,review,token)


def git_status_reply(backend,session,question):
    """Answer Git progress/approval followups from owned receipts, without actions."""
    import json,re
    from agent.runtime.input_evidence import split_uploaded_input
    text=split_uploaded_input(question)[0].strip().casefold().strip(".!? ")
    approval=bool(re.fullmatch(r"(?:i (?:will |have )?)?(?:approve|approved|confirm|confirmed)(?: it| the action)?",text))
    topic=bool(re.search(r"\b(?:git|push|pushed|commit|committed)\b",text))
    status=bool(re.fullmatch(r"how to confirm|how do i confirm|(?:what(?:'s| is) )?(?:git |push |commit )?status",text) or
        (topic and (re.search(r"\b(?:status|confirm|verify|latest|completed|succeeded|queued|pending|result)\b",text) or
                    re.match(r"^(?:did|have|has|is|was|were|pushed|committed)\b",text))))
    if re.match(r"^(?:explain|what does|how does)\b",text):status=False
    command=re.match(r"^(?:(?:please|can you|could you|would you)\s+)?(?:git\s+)?(?:commit|push)\b",text)
    if command and not re.fullmatch(r"(?:git )?(?:push|commit) status",text):return None
    if not (approval or status):return None
    if not getattr(backend,"project_id",None) or getattr(backend,"project",{}).get("source")!="git":return None
    actions=backend.actions()
    with actions.receipts.connect() as db:
        latest=db.execute("SELECT status,json_extract(proposal,'$.action') AS action FROM browser_proposals WHERE user=? AND space=? AND session=? ORDER BY rowid DESC LIMIT 1",
            (backend.user,backend.space,session)).fetchone()
        rows=db.execute("SELECT id,status,result,expires,json_extract(proposal,'$.action') AS action FROM browser_proposals WHERE user=? AND space=? AND session=? AND json_extract(proposal,'$.action') IN ('git_commit','git_push') ORDER BY rowid DESC LIMIT 1",
            (backend.user,backend.space,session)).fetchall()
    if approval and latest and latest["status"]=="pending" and latest["action"] not in {"git_commit","git_push"}:return None
    if not rows:
        # A just-opened Git review has no approval proposal yet. Inspect only this
        # chat's last ten exchanges; an unrelated chat cannot establish context.
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(backend.catalog.path)) as db:
            context=db.execute("SELECT answer FROM turns WHERE user=? AND space=? AND session=? ORDER BY id DESC LIMIT 10",
                (backend.user,backend.space,session)).fetchall()
        if not any(row[0].startswith("Git commit/push requires a review") for row in context) and not (topic and status):return None
        answer="No Git action has been queued or confirmed in this chat. Prepare the Commit or Push review and request its exact-action approval first."
    else:
        row=dict(rows[0]);state=row["status"];action=row["action"]
        if state=="pending" and row["expires"]<=actions.clock():state="expired"
        if state=="completed":
            result=json.loads(row["result"] or "{}")
            if action=="git_push" and result.get("pushed") is True:
                answer=("Saved receipt confirms push of "+result["commit"]+" on "+result["branch"]+
                        ". Remote: "+result["remote_url"]+". Receipt: "+row["id"]+
                        ". This records confirmation at execution time; no fresh remote check was performed for this reply.")
            elif action=="git_commit" and result.get("committed") is True:
                answer=("Latest recorded commit: "+result["commit"]+" on "+result["branch"]+
                        ". This commit is local. No push has been queued or confirmed for it in this chat. "+
                        "Open Push review, select the repository account, prepare the review and approve the separate git_push action.")
            else:answer="The saved receipt does not confirm a successful Git publication. Inspect the receipt before another action."
        elif state=="pending":
            label="Push" if action=="git_push" else "Commit"
            answer=label+" is waiting for its exact-action approval. It has not executed. Review the form and click Approve exact action or Decline."
        elif state=="reconciled_not_applied":
            answer="The failed push was reconciled against the remote: the reviewed commit was not currently published at that check. The failed receipt is retained. Prepare a fresh review and approve its new git_push action; no retry has executed."
        elif state in {"running","uncertain"}:
            answer="The Git action outcome is running or uncertain. Inspect its saved receipt and actual repository state before another attempt. No automatic retry was performed."
        else:
            answer="The last Git proposal is "+state+". It does not confirm a push. Prepare a fresh review if you want to proceed."
    if approval:answer+=" A chat message does not approve or execute Git actions."
    return {"answer":answer,"notices":[],"task_status":"completed","execution_outcome":"completed"}
