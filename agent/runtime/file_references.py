"""Resolve literal approved-file references locally within an owned chat."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sqlite3

from agent.actions.browser import BrowserActions
from agent.actions.downloads import read_created_file
from agent.actions.receipts import ActionBlocked
from agent.tools.project_tools import TEXT_EXTENSIONS


PREVIEW_CHARS = 12000


def literal_file_path(question):
    if not isinstance(question, str):return None
    text=question.strip()
    if not text or "\n" in text or "\r" in text:return None
    quoted=len(text)>2 and text[0]==text[-1] and text[0] in "`\"'"
    if quoted:text=text[1:-1]
    elif re.search(r"\s",text):return None
    if not text or re.search(r'[<>:"|?*`\x00-\x1f]',text):return None
    path=Path(text.replace("\\","/"))
    if path.anchor or PureWindowsPath(text).drive or ".." in path.parts:return None
    if path.suffix.lower() not in TEXT_EXTENSIONS:return None
    return path.as_posix()


def _reply(answer, status="completed"):
    return {"answer":answer,"route":"project","task_status":status,
            "execution_outcome":"completed" if status=="completed" else "blocked",
            "answer_available":True}


def approved_file_reference(question, root, catalog, session, request_scope=None):
    """A path alone can preview an exact owned creation; never infer roots from prose."""
    requested=literal_file_path(question)
    if requested is None:return None
    guidance=("To read this file, select its project and ask Read " + requested
              + ", or provide its project root explicitly. A bare path cannot select another folder or authorize an action.")
    user,space=getattr(catalog,"user",None),getattr(catalog,"space",None)
    dbpath=Path(root)/"outputs/local_actions.sqlite3"
    if not user or not space or not dbpath.is_file():return _reply(guidance,"awaiting_input")
    try:
        with closing(sqlite3.connect(dbpath.resolve().as_uri()+"?mode=ro",uri=True)) as db:
            rows=db.execute("SELECT id,proposal FROM browser_proposals WHERE user=? AND space=? AND session=? AND status='completed' ORDER BY rowid DESC LIMIT 51",(user,space,session)).fetchall()
        if len(rows)>50:return _reply("This chat has more than the bounded file-reference lookup can inspect. " + guidance,"awaiting_input")
        matches=[]
        for token,raw in rows:
            proposal=json.loads(raw)
            if proposal.get("action")!="create_file":continue
            path=proposal.get("arguments",{}).get("relative_path")
            if not isinstance(path,str):continue
            normalized=Path(path.replace("\\","/")).as_posix()
            if os.path.normcase(normalized)!=os.path.normcase(requested):continue
            if request_scope:
                bound=request_scope.get("bound_project_root")
                if not bound or str(Path(proposal["project_root"]).resolve())!=bound:continue
            matches.append((token,proposal))
        roots={os.path.normcase(str(Path(p["project_root"]).resolve())) for _,p in matches}
        if not matches:return _reply("No completed approved file creation in this chat matches that path. " + guidance,"awaiting_input")
        if len(roots)!=1:return _reply("That path belongs to more than one approved project in this chat. " + guidance,"awaiting_input")
        token,proposal=matches[0]
        snapshot=read_created_file(BrowserActions(dbpath),user,space,session,token)
        raw=snapshot["data"];text=raw.decode("utf-8")
        preview=text[:PREVIEW_CHARS]
        # Render all saved content as data, even when it contains Markdown fences.
        fence="`"*max(3,1+max((len(v) for v in re.findall(r"`+",preview)),default=0))
        limit=("Showing the first " + str(PREVIEW_CHARS) + " characters; preview is partial."
               if len(text)>PREVIEW_CHARS else "Full saved text shown.")
        return _reply("Approved file: " + requested + "\nProject: " + proposal["project_root"]
                      + "\nReceipt: " + token + "\nBytes: " + str(len(raw))
                      + "\nSHA256: " + hashlib.sha256(raw).hexdigest()
                      + "\n\nThe current file matches its approved creation. " + limit
                      + " No model request, command or new file action was run.\n\n"
                      + fence + "text\n" + preview + "\n" + fence)
    except (ActionBlocked,ValueError,OSError,TypeError,KeyError,sqlite3.Error):
        return _reply("The approved file could not be verified as unchanged and accessible. No file content was displayed. Inspect its saved receipt and request a fresh reviewed export if needed.","incomplete")
