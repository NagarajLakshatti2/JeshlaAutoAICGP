"""Scoped browser proposals; only an explicit UI approval executes a stored action."""
import hashlib
import inspect
import json
import time
import uuid
from pathlib import Path
from agent.actions.receipts import LocalActionReceipts,ActionBlocked,ACTIONS,canonical,target_version
from agent.tools.project_tools import ProjectTools

class BrowserActions:
    def __init__(self,path,clock=time.time,tools_factory=None):
        self.tools_factory=tools_factory or ProjectTools
        self.receipts=LocalActionReceipts(path);self.clock=clock
        with self.receipts.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS browser_proposals (id TEXT PRIMARY KEY, user TEXT, space TEXT, session TEXT, proposal TEXT, digest TEXT, version TEXT, status TEXT, expires REAL, result TEXT)")
    @staticmethod
    def _validate_command(tools,action,args):
        if action in {"run_command","run_tests_and_parse"}:
            try:tools._command_argv(args.get("command"),args.get("timeout",60))
            except ValueError as error:raise ActionBlocked(str(error)) from None

    def propose(self,user,space,session,action,proposal):
        value=json.loads(canonical(proposal))
        if action not in ACTIONS or value.get("action")!=action or set(value)!={"project_root","action","arguments"}:
            raise ActionBlocked("Unsupported browser action proposal.")
        root=Path(value["project_root"]).resolve();tools=self.tools_factory(root)
        if not callable(getattr(tools,action,None)):raise ActionBlocked("This action requires a selected Git workspace.")
        bound=inspect.signature(getattr(tools,action)).bind(**value["arguments"]);bound.apply_defaults()
        value["arguments"]=dict(bound.arguments);value["project_root"]=str(root)
        self._validate_command(tools,action,value["arguments"])
        encoded=canonical(value)
        if len(encoded)>1_100_000:raise ActionBlocked("Proposal is too large to review safely.")
        version=target_version(root,action,value["arguments"])
        digest=hashlib.sha256(canonical([value,version]).encode()).hexdigest();token=uuid.uuid4().hex
        with self.receipts.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE browser_proposals SET status='expired' WHERE status='pending' AND expires<=?",(self.clock(),))
            count=db.execute("SELECT count(*) FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='pending'",(user,space,session)).fetchone()[0]
            if count>=20:raise ActionBlocked("Review or decline pending actions before requesting more.")
            db.execute("INSERT INTO browser_proposals VALUES (?,?,?,?,?,?,?,?,?,NULL)",(token,user,space,session,encoded,digest,version,"pending",self.clock()+600))
        return token
    def reconcile_git_push_review(self,user,space,review,*,credential=""):
        """Trusted fresh-review path: observe the remote before resolving uncertainty."""
        if review.get("kind")!="git_push":raise ActionBlocked("Only a fresh Git push review can be reconciled.")
        project=review["project"];root=Path(project["root"]).resolve()
        proposal={"project_root":str(root),"action":"git_push","arguments":{"review":review}}
        fingerprint=hashlib.sha256(canonical(proposal).encode()).hexdigest()
        with self.receipts.connect() as db:
            rows=db.execute("SELECT a.id,b.proposal FROM actions a JOIN browser_proposals b ON b.id=a.id WHERE a.fingerprint=? AND a.status='uncertain' AND b.status='uncertain' AND b.user=? AND b.space=?",
                (fingerprint,user,space)).fetchall()
        if not rows:return []
        # Fresh review data is necessary but not accepted as proof by itself.
        # Re-read only the registered HTTPS branch. The selected credential is
        # transport-only and is never stored in review or reconciliation data.
        from integrations.git.repositories import repository_url,git_command
        url=repository_url(project["remote_url"]);target=review["target"]
        if target!="refs/heads/"+review["state"]["branch"] or review["remote_tip"]==review["state"]["head"]:
            raise ActionBlocked("No unchanged prior remote tip is available for reconciliation.")
        observed=git_command(["ls-remote","--refs",url,target],cwd=root,host=url.split("/")[2],token=credential,timeout=30).split()
        if len(observed)!=2 or observed[1]!=target or observed[0]!=review["remote_tip"]:
            raise ActionBlocked("Remote branch changed during reconciliation. Inspect it and prepare a fresh review.")
        if target_version(root,"git_push",proposal["arguments"])!=review["version"]:
            raise ActionBlocked("Local Git state changed during reconciliation.")
        audit={"outcome":"reviewed_commit_not_currently_published","remote_url":url,"target":target,
               "observed_remote_tip":observed[0],"reviewed_head":review["state"]["head"],
               "requires_fresh_approval":True}
        resolved=[]
        with self.receipts.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS git_push_reconciliations (receipt_id TEXT PRIMARY KEY, observed REAL NOT NULL, evidence TEXT NOT NULL)")
            for row in rows:
                if canonical(json.loads(row["proposal"]))!=canonical(proposal):continue
                changed=db.execute("UPDATE actions SET status='reconciled_not_applied',updated=? WHERE id=? AND status='uncertain' AND fingerprint=?",
                    (self.clock(),row["id"],fingerprint)).rowcount
                if not changed:continue
                db.execute("INSERT INTO git_push_reconciliations VALUES (?,?,?)",(row["id"],self.clock(),canonical(audit)))
                db.execute("UPDATE browser_proposals SET status='reconciled_not_applied' WHERE id=? AND user=? AND space=? AND status='uncertain'",(row["id"],user,space))
                resolved.append(row["id"])
            # A duplicate blocked before a durable action claim never ran a
            # handler. Resolve that display row against the same observation.
            if resolved:
                blocked=db.execute("SELECT id,proposal FROM browser_proposals b WHERE user=? AND space=? AND status='uncertain' AND NOT EXISTS (SELECT 1 FROM actions a WHERE a.id=b.id)",
                    (user,space)).fetchall()
                for row in blocked:
                    if canonical(json.loads(row["proposal"]))!=canonical(proposal):continue
                    db.execute("INSERT INTO git_push_reconciliations VALUES (?,?,?)",(row["id"],self.clock(),canonical({**audit,"handler_not_started":True})))
                    db.execute("UPDATE browser_proposals SET status='reconciled_not_applied' WHERE id=? AND status='uncertain'",(row["id"],))
                    resolved.append(row["id"])
        return resolved

    def pending(self,user,space,session):
        with self.receipts.connect() as db:
            db.execute("UPDATE browser_proposals SET status='expired' WHERE status='pending' AND expires<=?",(self.clock(),))
            rows=db.execute("SELECT id,proposal,expires FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='pending' ORDER BY rowid LIMIT 20",(user,space,session)).fetchall()
        return [{"id":row["id"],"proposal":json.loads(row["proposal"]),"expires":row["expires"]} for row in rows]
    def expired_file_reviews(self,user,space,session):
        """List latest expired file reviews, never older consumed duplicates."""
        self.pending(user,space,session)  # Apply the normal expiration policy.
        with self.receipts.connect() as db:
            rows=db.execute("SELECT * FROM browser_proposals WHERE user=? AND space=? AND session=? ORDER BY rowid DESC LIMIT 50",(user,space,session)).fetchall()
        seen=set();result=[]
        for row in rows:
            try:
                proposal=json.loads(row["proposal"])
                if proposal.get("action")!="create_file":continue
                if hashlib.sha256(canonical([proposal,row["version"]]).encode()).hexdigest()!=row["digest"]:continue
                identity=hashlib.sha256(canonical(proposal).encode()).hexdigest()
                if identity in seen:continue
                seen.add(identity)
                if row["status"]!="expired":continue
                result.append({"id":row["id"],"path":proposal["arguments"]["relative_path"],"project_root":proposal["project_root"]})
                if len(result)==20:break
            except (ValueError,TypeError,KeyError):continue
        return result

    def refresh_file_review(self,user,space,session,token):
        """Renew one intact expired new-file proposal; never execute/rebuild it."""
        self.pending(user,space,session)
        row=self._row(user,space,session,token)
        if row["status"]!="expired":raise ActionBlocked("Only an expired file review can be refreshed.")
        proposal=json.loads(row["proposal"])
        if proposal.get("action")!="create_file":raise ActionBlocked("Prepare a new review for this action type.")
        if hashlib.sha256(canonical([proposal,row["version"]]).encode()).hexdigest()!=row["digest"]:
            raise ActionBlocked("Stored proposal changed. Prepare a new review.")
        if self.receipts.get(token):raise ActionBlocked("This review has an execution receipt. Inspect that outcome; no refresh or replay.")
        args=proposal.get("arguments",{})
        if set(args)!={"relative_path","content"} or not all(isinstance(args.get(k),str) for k in ("relative_path","content")):
            raise ActionBlocked("File review is incomplete. Prepare a new review.")
        root=Path(proposal["project_root"])
        if str(root.resolve())!=str(root) or row["version"]!="missing" or target_version(root,"create_file",args)!="missing":
            raise ActionBlocked("The file target changed. Prepare a new review; no overwrite is allowed.")
        for item in self.pending(user,space,session):
            if canonical(item["proposal"])==canonical(proposal):return item["id"]
        with self.receipts.connect() as db:
            newer=db.execute("SELECT id,proposal FROM browser_proposals WHERE user=? AND space=? AND session=? ORDER BY rowid DESC LIMIT 50",(user,space,session)).fetchall()
        for item in newer:
            if canonical(json.loads(item["proposal"]))==canonical(proposal):
                if item["id"]!=token:
                    raise ActionBlocked("A newer review supersedes this expired action. Reload the chat and review its current state.")
                break
        return self.propose(user,space,session,"create_file",proposal)

    def _row(self,user,space,session,token):
        with self.receipts.connect() as db:
            row=db.execute("SELECT * FROM browser_proposals WHERE id=? AND user=? AND space=? AND session=?",(token,user,space,session)).fetchone()
        if not row:raise ActionBlocked("Action proposal not found in this user/chat.")
        return dict(row)
    def decline(self,user,space,session,token):
        self._row(user,space,session,token)
        with self.receipts.connect() as db:
            changed=db.execute("UPDATE browser_proposals SET status='declined' WHERE id=? AND user=? AND space=? AND session=? AND status='pending'",(token,user,space,session)).rowcount
        if not changed:raise ActionBlocked("This proposal is no longer pending.")
    def execute(self,user,space,session,token):
        row=self._row(user,space,session,token)
        if row["status"]=="completed":return json.loads(row["result"]),True
        if row["status"]!="pending":raise ActionBlocked("This action is no longer pending; no replay is allowed.")
        value=json.loads(row["proposal"])
        if hashlib.sha256(canonical([value,row["version"]]).encode()).hexdigest()!=row["digest"]:
            raise ActionBlocked("Stored proposal changed. Request a fresh proposal.")
        if row["expires"]<=self.clock():
            self._status(token,"expired");raise ActionBlocked("Approval expired. Request a fresh proposal.")
        root=Path(value["project_root"]).resolve();action=value["action"];args=value["arguments"]
        if action not in ACTIONS:raise ActionBlocked("Unsupported action.")
        try:
            current_version=target_version(root,action,args)
        except ValueError:
            self._status(token,"stale")
            raise ActionBlocked("Target changed since the proposal. Prepare a fresh review.") from None
        if current_version!=row["version"]:
            self._status(token,"stale");raise ActionBlocked("Target changed since the proposal. Read it again and request a fresh action.")
        tools=self.tools_factory(root);handler=getattr(tools,action)
        try:self._validate_command(tools,action,args)
        except ActionBlocked:
            self._status(token,"blocked")
            raise
        with self.receipts.connect() as db:
            changed=db.execute("UPDATE browser_proposals SET status='running' WHERE id=? AND user=? AND space=? AND session=? AND status='pending' AND expires>?",(token,user,space,session,self.clock())).rowcount
        if not changed:raise ActionBlocked("Another request already consumed this proposal; no replay.")
        try:
            result=self.receipts.run(root,action,args,handler,lambda name,shown:name==action and canonical(shown)==canonical(value) and target_version(root,action,args)==row["version"],receipt_id=token)
            encoded=canonical(result)
            with self.receipts.connect() as db:db.execute("UPDATE browser_proposals SET status='completed',result=? WHERE id=?",(encoded,token))
            return result,False
        except BaseException:
            self._status(token,"uncertain")
            raise
    def _status(self,token,status):
        with self.receipts.connect() as db:db.execute("UPDATE browser_proposals SET status=? WHERE id=?",(status,token))
