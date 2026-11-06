"""User-scoped project registrations and connection assignments."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid


class ProjectConfigurationError(ValueError):
    """A validated, user-facing project configuration problem."""


def project_namespace(space, project_id):
    if not isinstance(project_id,str) or not re.fullmatch(r"project-[a-f0-9]{32}",project_id):
        raise ProjectConfigurationError("Select a registered project.")
    return "project-"+hashlib.sha256(json.dumps([space,project_id]).encode()).hexdigest()[:48]


def validate_local_folder(value):
    if not isinstance(value,str) or not value.strip():
        raise ProjectConfigurationError("Enter an absolute project folder path.")
    requested=Path(value.strip()).expanduser()
    if not requested.is_absolute():
        raise ProjectConfigurationError("Use an absolute project folder path.")
    try:
        root=requested.resolve(strict=True)
        if not root.is_dir():raise OSError("not a directory")
        with os.scandir(root) as entries:next(entries,None)
    except (OSError,RuntimeError):
        raise ProjectConfigurationError("The project folder is missing or cannot be read by this server.") from None
    return str(root)


class ProjectCatalog:
    def __init__(self,path,user,space):
        if any(not isinstance(v,str) or not v.strip() or len(v)>128 for v in (user,space)):
            raise ProjectConfigurationError("Invalid project owner or memory space.")
        self.path=Path(path);self.user=user;self.space=space
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS local_projects (
                id TEXT NOT NULL,user TEXT NOT NULL,space TEXT NOT NULL,
                name TEXT NOT NULL,root TEXT NOT NULL,root_key TEXT NOT NULL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                PRIMARY KEY(user,space,id),UNIQUE(user,space,root_key))""")
            columns={row[1] for row in db.execute("PRAGMA table_info(local_projects)")}
            for name in ("source","remote_url","account_id"):
                if name not in columns:db.execute("ALTER TABLE local_projects ADD COLUMN "+name+" TEXT NOT NULL DEFAULT '"+("local" if name=="source" else "")+"'")
            if "archived" not in columns:db.execute("ALTER TABLE local_projects ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
            db.execute("""CREATE TABLE IF NOT EXISTS project_connections(
                user TEXT,space TEXT,project_id TEXT,kind TEXT,connection_id TEXT,options TEXT,
                PRIMARY KEY(user,space,project_id,kind))""")

    def add_local(self,name,folder):
        if not isinstance(name,str):raise ProjectConfigurationError("Enter a project name.")
        name=" ".join(name.split())
        if not 1<=len(name)<=100:raise ProjectConfigurationError("Use a project name of 1–100 characters.")
        root=validate_local_folder(folder);key=os.path.normcase(root)
        now=datetime.now(timezone.utc).isoformat();token="project-"+uuid.uuid4().hex
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("INSERT OR IGNORE INTO local_projects(id,user,space,name,root,root_key,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",(token,self.user,self.space,name,root,key,now,now))
            db.execute("UPDATE local_projects SET name=?,archived=0,updated_at=? WHERE user=? AND space=? AND root_key=?",(name,now,self.user,self.space,key))
            row=db.execute("SELECT id FROM local_projects WHERE user=? AND space=? AND root_key=?",(self.user,self.space,key)).fetchone()
        return self.get(row[0])

    def get(self,project_id,*,include_archived=False):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory=sqlite3.Row
            query="SELECT id,name,root,created_at,updated_at,source,remote_url,account_id FROM local_projects WHERE user=? AND space=? AND id=?"
            if not include_archived:query+=" AND archived=0"
            row=db.execute(query,(self.user,self.space,project_id)).fetchone()
        return dict(row) if row else None

    def list(self,*,include_archived=False):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory=sqlite3.Row
            query="SELECT id,name,root,created_at,updated_at,source,remote_url,account_id FROM local_projects WHERE user=? AND space=?"
            if not include_archived:query+=" AND archived=0"
            query+=" ORDER BY name COLLATE NOCASE,id"
            rows=db.execute(query,(self.user,self.space)).fetchall()
        return [dict(row) for row in rows]

    def archive(self,project_id):
        if not self.get(project_id):raise ProjectConfigurationError("Project not found.")
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE local_projects SET archived=1,updated_at=? WHERE user=? AND space=? AND id=?",
                       (datetime.now(timezone.utc).isoformat(),self.user,self.space,project_id))

    def restore(self,project_id):
        if not self.get(project_id,include_archived=True):raise ProjectConfigurationError("Project not found.")
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE local_projects SET archived=0,updated_at=? WHERE user=? AND space=? AND id=?",
                       (datetime.now(timezone.utc).isoformat(),self.user,self.space,project_id))

    def configure_git(self,project_id,url,account_id=""):
        if not self.get(project_id):raise ProjectConfigurationError("Project not found.")
        from integrations.git.repositories import repository_url
        url=repository_url(url)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE local_projects SET source='git',remote_url=?,account_id=?,updated_at=? WHERE user=? AND space=? AND id=?",
                       (url,account_id,datetime.now(timezone.utc).isoformat(),self.user,self.space,project_id))
        return self.get(project_id)

    def set_binding(self,project_id,kind,connection_id,options):
        if not self.get(project_id):raise ProjectConfigurationError("Project not found.")
        if kind not in {"jira_mcp","github_mcp","custom_mcp"}:raise ProjectConfigurationError("Unsupported project connection.")
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("INSERT OR REPLACE INTO project_connections VALUES(?,?,?,?,?,?)",
                       (self.user,self.space,project_id,kind,connection_id,json.dumps(options)))

    def bindings(self,project_id):
        if not self.get(project_id):raise ProjectConfigurationError("Project not found.")
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute("SELECT kind,connection_id,options FROM project_connections WHERE user=? AND space=? AND project_id=?",
                            (self.user,self.space,project_id)).fetchall()
        return {kind:{"connection_id":key,"options":json.loads(options)} for kind,key,options in rows}

    def remove_binding(self,project_id,kind):
        if not self.get(project_id):raise ProjectConfigurationError("Project not found.")
        if kind not in {"jira_mcp","github_mcp","custom_mcp"}:raise ProjectConfigurationError("Unsupported project connection.")
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("DELETE FROM project_connections WHERE user=? AND space=? AND project_id=? AND kind=?",
                       (self.user,self.space,project_id,kind))
