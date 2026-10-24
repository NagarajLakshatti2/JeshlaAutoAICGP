"""Owned connection metadata and encrypted credentials, separate from chat history."""
from contextlib import closing
from datetime import datetime, timezone
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
from agent.storage.projects import ProjectConfigurationError


KINDS={"github","gitlab","github_mcp","jira_mcp","custom_mcp"}


def protect_token(value, decrypt=False):
    """Use Windows user-bound DPAPI. Hosted deployments use environment secrets."""
    if os.name!="nt":
        raise ProjectConfigurationError("Use an environment-variable credential on this server.")
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[("size",wintypes.DWORD),("data",ctypes.POINTER(ctypes.c_ubyte))]
    raw=value if isinstance(value,bytes) else value.encode("utf-8")
    buffer=ctypes.create_string_buffer(raw)
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    crypt=ctypes.WinDLL("crypt32",use_last_error=True)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if decrypt:
        ok=crypt.CryptUnprotectData(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target))
    else:
        ok=crypt.CryptProtectData(ctypes.byref(source),"JeshlaAutoAI",None,None,None,1,ctypes.byref(target))
    if not ok:raise ProjectConfigurationError("The operating system could not protect this credential.")
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(target.data)


class ConnectionCatalog:
    def __init__(self,path,user,space):
        self.path=Path(path);self.user=user;self.space=space
        if any(not isinstance(x,str) or not x.strip() or len(x)>128 for x in (user,space)):
            raise ProjectConfigurationError("Invalid connection owner.")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("""CREATE TABLE IF NOT EXISTS connections(
                id TEXT,user TEXT,space TEXT,kind TEXT,label TEXT,endpoint TEXT,
                env_name TEXT,sealed TEXT,status TEXT,details TEXT,checked_at TEXT,
                PRIMARY KEY(user,space,id))""")

    def save(self,kind,label,endpoint,*,env_name="",token=""):
        if kind not in KINDS:raise ProjectConfigurationError("Choose a supported connection type.")
        if not isinstance(label,str) or not 1<=len(label.strip())<=100:
            raise ProjectConfigurationError("Enter a connection name of 1–100 characters.")
        if env_name and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}",env_name):
            raise ProjectConfigurationError("Enter a valid environment-variable name.")
        if env_name and token:raise ProjectConfigurationError("Choose one credential source.")
        if token and (len(token)>16000 or any(ord(c)<32 for c in token)):
            raise ProjectConfigurationError("Enter a valid access token.")
        sealed=base64.b64encode(protect_token(token)).decode() if token else ""
        key="connection-"+uuid.uuid4().hex
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("INSERT INTO connections VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (key,self.user,self.space,kind,label.strip(),endpoint,env_name,sealed,"configured","{}",""))
        return self.get(key)

    def _row(self,key):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory=sqlite3.Row
            row=db.execute("SELECT * FROM connections WHERE user=? AND space=? AND id=?",
                           (self.user,self.space,key)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def public(row):
        if not row:return None
        return {key:row[key] for key in ("id","kind","label","endpoint","env_name","status","checked_at")} | {
            "credential_present":bool(row["env_name"] or row["sealed"]),"details":json.loads(row["details"])}

    def get(self,key):return self.public(self._row(key))

    def list(self):
        with closing(sqlite3.connect(self.path)) as db:
            keys=[r[0] for r in db.execute("SELECT id FROM connections WHERE user=? AND space=? ORDER BY label,id",
                                          (self.user,self.space))]
        return [self.get(key) for key in keys]

    def credential(self,key):
        row=self._row(key)
        if not row:raise ProjectConfigurationError("Connection not found in this workspace.")
        value=os.getenv(row["env_name"],"") if row["env_name"] else (
            protect_token(base64.b64decode(row["sealed"]),True).decode() if row["sealed"] else "")
        if (row["env_name"] or row["sealed"]) and not value.strip():
            raise ProjectConfigurationError("The configured credential is unavailable. Update it in Settings.")
        if any(ord(c)<32 for c in value):raise ProjectConfigurationError("Invalid connection credential.")
        return value

    def checked(self,key,details):
        if not self.get(key):raise ProjectConfigurationError("Connection not found.")
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE connections SET status='verified',details=?,checked_at=? WHERE user=? AND space=? AND id=?",
                       (json.dumps(details),datetime.now(timezone.utc).isoformat(),self.user,self.space,key))

    def disconnect(self,key):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("DELETE FROM connections WHERE user=? AND space=? AND id=?",(self.user,self.space,key))
