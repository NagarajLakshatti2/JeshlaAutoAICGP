"""Read-only downloads tied to scoped completed create-file approval receipts."""
import hashlib,json
from pathlib import Path
from agent.actions.receipts import ActionBlocked,canonical
from agent.tools.project_tools import ProjectTools


def _proposal(actions,row):
    value=json.loads(row["proposal"])
    if row["status"]!="completed" or value.get("action")!="create_file":raise ActionBlocked("Only completed approved file creations can be downloaded.")
    if hashlib.sha256(canonical([value,row["version"]]).encode()).hexdigest()!=row["digest"]:raise ActionBlocked("Stored proposal changed.")
    receipt=actions.receipts.get(row["id"])
    if not receipt or receipt["status"]!="completed" or receipt["fingerprint"]!=hashlib.sha256(canonical(value).encode()).hexdigest():raise ActionBlocked("Completed action receipt is unavailable.")
    return value


def list_created_files(actions,user,space,session):
    with actions.receipts.connect() as db:
        rows=db.execute("SELECT * FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='completed' ORDER BY rowid DESC LIMIT 20",(user,space,session)).fetchall()
    result=[]
    for row in rows:
        try:value=_proposal(actions,row)
        except (ValueError,TypeError,KeyError):continue
        result.append({"id":row["id"],"path":value["arguments"]["relative_path"]})
    return result


def read_created_file(actions,user,space,session,token):
    row=actions._row(user,space,session,token)
    value=_proposal(actions,row);root=Path(value["project_root"])
    if str(root.resolve())!=str(root):raise ActionBlocked("Approved project location changed.")
    requested=Path(value["arguments"]["relative_path"])
    current=root
    for part in requested.parts:
        current=current/part
        if current.is_symlink():raise ActionBlocked("Symlink download paths are excluded.")
    path=ProjectTools(str(root))._resolve_file(str(requested))
    if path.stat().st_size>1_000_000:raise ActionBlocked("File exceeds the 1 MB download limit.")
    with path.open('rb') as handle:data=handle.read(1_000_001)
    expected=value["arguments"]["content"].encode('utf-8')
    if len(data)>1_000_000 or data!=expected:raise ActionBlocked("File changed after its approved creation. Request a fresh reviewed export; this download is blocked.")
    return {"name":path.name,"data":data,"mime":"application/octet-stream"}
