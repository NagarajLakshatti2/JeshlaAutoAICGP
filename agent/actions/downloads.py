"""Read-only downloads tied to scoped completed create-file approval receipts."""
import hashlib,json
import io,os,re,stat,zipfile
from pathlib import Path,PurePosixPath,PureWindowsPath
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


def _relative_parts(value, *, allow_root=False):
    if not isinstance(value,str) or not value or len(value)>1000:
        raise ActionBlocked("Invalid artifact path.")
    normalized=value.replace('\\','/')
    win=PureWindowsPath(value)
    if win.drive or win.root or any(c in value for c in ':\r\n\0') or '..' in normalized.split('/'):
        raise ActionBlocked("Artifact path must stay inside the approved project.")
    parts=PurePosixPath(normalized).parts
    from agent.tools.project_tools import SKIP_DIRS,SKIP_FILES
    denied={str(p).lower() for p in SKIP_DIRS|SKIP_FILES}|{'.aws','.ssh','.azure','.codex','.agents','credentials','credentials.json','secrets.json','secrets.toml'}
    if (not parts and not allow_root) or any(p.lower() in denied or p.lower().startswith(('.env','secrets.')) for p in parts):
        raise ActionBlocked("Private/excluded artifact paths cannot be downloaded.")
    return parts


def _inspection_record(actions,row):
    value=json.loads(row['proposal'])
    if row['status']!='completed' or value.get('action')!='inspect_browser_page':
        raise ActionBlocked("A completed approved inspection is required.")
    if hashlib.sha256(canonical([value,row['version']]).encode()).hexdigest()!=row['digest']:
        raise ActionBlocked("Stored proposal changed.")
    receipt=actions.receipts.get(row['id'])
    if not receipt or receipt['status']!='completed' or receipt['fingerprint']!=hashlib.sha256(canonical(value).encode()).hexdigest():
        raise ActionBlocked("Completed inspection receipt is unavailable.")
    result=json.loads(receipt['result'])
    if not isinstance(result,dict) or canonical(result)!=canonical(json.loads(row['result'])) or result.get('status')!='inspected':
        raise ActionBlocked("Inspection result changed or is incomplete.")
    for key in ('screenshot_sha256','inspection_sha256'):
        if not isinstance(result.get(key),str) or not re.fullmatch('[0-9a-f]{64}',result[key]):
            raise ActionBlocked("This inspection has no verified screenshot bytes; older captures are not backfilled.")
    if type(result.get('screenshot_size_bytes')) is not int or not 8<=result['screenshot_size_bytes']<=5_000_000:
        raise ActionBlocked("Screenshot exceeds its verified download size.")
    base=_relative_parts(value['arguments'].get('evidence_folder','test-output/agent-web'),allow_root=True)
    png=_relative_parts(result.get('screenshot'))
    manifest=_relative_parts(result.get('inspection_file'))
    if (len(png)!=len(base)+2 or png[:len(base)]!=base or not re.fullmatch('[0-9a-f]{32}',png[-2]) or
            png[-1]!='inspection.png' or manifest!=(*png[:-1],'inspection.json')):
        raise ActionBlocked("Screenshot does not match the approved inspection destination.")
    return value,result,png,manifest


def list_downloadable_files(actions,user,space,session):
    """Metadata only: original text creations and new verified inspection PNGs."""
    with actions.receipts.connect() as db:
        rows=db.execute("SELECT * FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='completed' ORDER BY rowid DESC LIMIT 20",(user,space,session)).fetchall()
    items=[]
    for row in rows:
        try:
            action=json.loads(row['proposal']).get('action')
            if action=='create_file':
                value=_proposal(actions,row);path=value['arguments']['relative_path']
            elif action=='inspect_browser_page':
                _,result,_,_=_inspection_record(actions,row);path=result['screenshot']
            else:continue
            items.append({'id':row['id'],'path':path})
        except (ValueError,TypeError,KeyError,AttributeError):continue
    return items


def _artifact_path(root,parts):
    current=root
    for part in ('',*parts):
        current=current/part
        if current.is_symlink() or (hasattr(current,'is_junction') and current.is_junction()):
            raise ActionBlocked("Artifact links and junctions cannot be downloaded.")
    if not current.resolve().is_relative_to(root):raise ActionBlocked("Artifact escaped the approved project.")
    return current


def _artifact_bytes(path,maximum,digest,size=None):
    before=path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size>maximum:raise ActionBlocked("Artifact is not a bounded regular file.")
    with path.open('rb') as handle:
        opened=os.fstat(handle.fileno());data=handle.read(maximum+1);finished=os.fstat(handle.fileno())
    after=path.stat()
    def signature(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if (any(signature(s)!=signature(before) for s in (opened,finished,after)) or len(data)>maximum or
            len(data)!=before.st_size or size is not None and len(data)!=size or hashlib.sha256(data).hexdigest()!=digest):
        raise ActionBlocked("Artifact changed after its approved capture. This download is blocked.")
    return data


def read_downloadable_file(actions,user,space,session,token):
    row=actions._row(user,space,session,token)
    if json.loads(row['proposal']).get('action')=='create_file':
        return read_created_file(actions,user,space,session,token)
    value,result,png,manifest=_inspection_record(actions,row)
    root=Path(value['project_root'])
    if not root.is_absolute() or str(root.resolve())!=str(root):raise ActionBlocked("Approved project location changed.")
    try:
        png_path=_artifact_path(root,png);manifest_path=_artifact_path(root,manifest)
        encoded=_artifact_bytes(manifest_path,512_000,result['inspection_sha256'])
        stored=json.loads(encoded.decode('utf-8-sig'))
        expected={k:v for k,v in result.items() if k!='inspection_sha256'}
        if canonical(stored)!=canonical(expected):raise ActionBlocked("Saved inspection metadata changed.")
        data=_artifact_bytes(png_path,5_000_000,result['screenshot_sha256'],result['screenshot_size_bytes'])
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ActionBlocked("Capture is not a PNG snapshot.")
        _artifact_path(root,png);_artifact_path(root,manifest)
        return {'name':'inspection.png','data':data,'mime':'image/png'}
    except (OSError,UnicodeError,ValueError) as error:
        if isinstance(error,ActionBlocked):raise
        raise ActionBlocked("Verified inspection files are missing, changed or unreadable.") from None


def zip_snapshot(snapshot):
    """One in-memory entry, derived only from a previously verified snapshot."""
    name=snapshot.get('name');data=snapshot.get('data')
    if (not isinstance(name,str) or not name or len(name)>200 or name in {'.','..'} or
            PureWindowsPath(name).drive or any(c in name for c in '/\\:\r\n\0') or
            not isinstance(data,bytes) or len(data)>5_000_000):
        raise ActionBlocked("Invalid download snapshot.")
    output=io.BytesIO()
    entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
    entry.create_system=3;entry.external_attr=0o100600<<16
    with zipfile.ZipFile(output,'w') as archive:archive.writestr(entry,data)
    return {'name':name+'.zip','data':output.getvalue(),'mime':'application/zip'}
