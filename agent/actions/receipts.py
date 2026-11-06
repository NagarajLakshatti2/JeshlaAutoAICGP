"""Durable receipts for approved local actions; not an OS command sandbox."""
from contextlib import contextmanager
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

from agent.policies.tool_registry import CONTROLLED_PROJECT_ACTIONS,WORKSPACE_CONTROLLED_ACTIONS
ACTIONS=CONTROLLED_PROJECT_ACTIONS|WORKSPACE_CONTROLLED_ACTIONS

class ActionBlocked(ValueError):
    pass

class ActionDeclined(ActionBlocked):
    pass

class ActionPending(ActionDeclined):
    pass

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def target_version(root,action,args):
    if action == "create_project":
        from agent.tools.project_creation import validate_creation
        from agent.tools.project_tools import ProjectTools
        try:
            plan = validate_creation(ProjectTools(root), args.get("plan"))
        except ValueError as error:
            raise ActionBlocked("Project creation review is stale or invalid: " + str(error)) from None
        return plan["id"] + ":destination-missing"
    if action in {"apply_test_repair","rerun_test_repair"}:
        from agent.tools.test_repairs import repair_version
        try:return repair_version(root,action,args.get("plan"))
        except (ValueError,KeyError,TypeError,OSError) as error:
            raise ActionBlocked("Repair plan is stale, incomplete or outside its evidence scope: "+str(error)) from None
    if action.startswith("terminal_"):
        if action == "terminal_start":
            return None
        from agent.actions.terminal_sessions import _sessions, _lock
        with _lock:
            entry = _sessions.get(args.get("terminal_id"))
            if not entry or entry["identity"][2] != args.get("chat_id") or entry["identity"][3] != str(root.resolve()):
                raise ActionBlocked("Terminal session expired or scope changed.")
            if entry["revision"] != args.get("revision"):
                raise ActionBlocked("Terminal review is stale.")
            return str(entry["revision"])
    if action in WORKSPACE_CONTROLLED_ACTIONS:
        from integrations.git.writes import version
        review=args.get("review")
        if not isinstance(review,dict) or review.get("kind")!=action:
            raise ActionBlocked("Prepare a complete Git review first.")
        observed=version(root,action,review)
        if observed!=review.get("version"):raise ActionBlocked("Git review is stale. Prepare a new review.")
        return observed
    if action not in {"create_file","replace_text","run_python_file"}:return None
    from agent.tools.project_tools import SKIP_DIRS,SKIP_FILES
    requested=Path(args.get("relative_path",""))
    path=(root/requested).resolve()
    if requested.is_absolute() or ".." in requested.parts or not path.is_relative_to(root):
        raise ActionBlocked("Action target must stay inside the approved project root.")
    if any(part in SKIP_DIRS or part in SKIP_FILES or part.startswith(".env") for part in path.relative_to(root).parts):
        raise ActionBlocked("Excluded action target.")
    if path.exists():
        if not path.is_file() or path.stat().st_size>1_000_000:raise ActionBlocked("Action target is not a supported bounded file.")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return "missing"

class LocalActionReceipts:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, result TEXT)")
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:
            db.close()
    def get(self,receipt_id):
        with self.connect() as db:
            row=db.execute("SELECT * FROM actions WHERE id=?",(receipt_id,)).fetchone()
            return dict(row) if row else None
    def run(self,root,action,arguments,handler,approve,receipt_id=None):
        if action not in ACTIONS:raise ActionBlocked("Unsupported controlled action.")
        root=Path(root).resolve()
        if not root.is_dir():raise ActionBlocked("Project root no longer exists.")
        snapshot=json.loads(canonical(arguments))
        if not isinstance(snapshot,dict):raise ActionBlocked("Action arguments must be an object.")
        identity={"project_root":str(root),"action":action,"arguments":snapshot}
        digest=hashlib.sha256(canonical(identity).encode()).hexdigest()
        token=receipt_id or uuid.uuid4().hex
        previous=self.get(token)
        if previous:
            if previous["fingerprint"]!=digest:raise ActionBlocked("Receipt does not match this exact action/root/arguments.")
            if previous["status"]=="completed":return json.loads(previous["result"])
            raise ActionBlocked("Action outcome is running or uncertain. Inspect its receipt and actual effects; no replay.")
        with self.connect() as db:
            unresolved=db.execute("SELECT id FROM actions WHERE fingerprint=? AND status IN ('running','uncertain')",(digest,)).fetchone()
        if unresolved:
            raise ActionBlocked("Uncertain local action blocks this exact request. Review receipt "+unresolved["id"]+" in "+str(self.path)+"; no automatic retry.")
        version=target_version(root,action,snapshot)
        # Display a separate copy so approval handlers cannot change the action.
        proposal=json.loads(canonical(identity))
        if not approve(action,proposal):raise ActionDeclined("Action declined. No local action executed.")
        if canonical(arguments)!=canonical(snapshot) or canonical(proposal)!=canonical(identity):
            raise ActionBlocked("Action changed during approval. Request fresh approval.")
        if target_version(root,action,snapshot)!=version:
            raise ActionBlocked("Target changed during approval. Read it again and request fresh approval.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM actions WHERE id=? OR (fingerprint=? AND status IN ('running','uncertain'))",(token,digest)).fetchone():
                raise ActionBlocked("An existing or uncertain action receipt blocks execution. No automatic retry.")
            now=time.time()
            db.execute("INSERT INTO actions VALUES (?,?,?,?,?,NULL)",(token,digest,"running",now,now))
        print("Local action receipt:",token,"|",self.path)
        # The durable running claim is committed before any side effect occurs.
        try:
            result=handler(**snapshot)
            # Review is local/read-only and cannot approve, replay or change effects.
            # Native test collection already attaches its bounded source review.
            if action in {"run_command","run_python_file","run_tests_and_parse"} and isinstance(result,dict):
                if not isinstance(result.get("post_run_review"),dict):
                    from agent.tools.execution_review import attach_review
                    result=attach_review(result,root if action=="run_tests_and_parse" else None)
            encoded=canonical(result)
            uncertain=isinstance(result,dict) and bool(result.get("timed_out"))
            with self.connect() as db:
                db.execute("UPDATE actions SET status=?,updated=?,result=? WHERE id=?",("uncertain" if uncertain else "completed",time.time(),encoded,token))
            if uncertain:raise ActionBlocked("Action timed out; its effects are uncertain. Inspect the saved receipt before another attempt.")
            return result
        except BaseException:
            try:
                with self.connect() as db:db.execute("UPDATE actions SET status='uncertain',updated=? WHERE id=? AND status='running'",(time.time(),token))
            except sqlite3.Error:
                pass  # The previously committed running claim still blocks replay.
            raise
