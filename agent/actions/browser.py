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
    def __init__(self,path,clock=time.time):
        self.receipts=LocalActionReceipts(path);self.clock=clock
        with self.receipts.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS browser_proposals (id TEXT PRIMARY KEY, user TEXT, space TEXT, session TEXT, proposal TEXT, digest TEXT, version TEXT, status TEXT, expires REAL, result TEXT)")
    def propose(self,user,space,session,action,proposal):
        value=json.loads(canonical(proposal))
        if action not in ACTIONS or value.get("action")!=action or set(value)!={"project_root","action","arguments"}:
            raise ActionBlocked("Unsupported browser action proposal.")
        root=Path(value["project_root"]).resolve();tools=ProjectTools(root)
        bound=inspect.signature(getattr(tools,action)).bind(**value["arguments"]);bound.apply_defaults()
        value["arguments"]=dict(bound.arguments);value["project_root"]=str(root)
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
    def pending(self,user,space,session):
        with self.receipts.connect() as db:
            db.execute("UPDATE browser_proposals SET status='expired' WHERE status='pending' AND expires<=?",(self.clock(),))
            rows=db.execute("SELECT id,proposal,expires FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='pending' ORDER BY rowid LIMIT 20",(user,space,session)).fetchall()
        return [{"id":row["id"],"proposal":json.loads(row["proposal"]),"expires":row["expires"]} for row in rows]
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
        if target_version(root,action,args)!=row["version"]:
            self._status(token,"stale");raise ActionBlocked("Target changed since the proposal. Read it again and request a fresh action.")
        tools=ProjectTools(root);handler=getattr(tools,action)
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
