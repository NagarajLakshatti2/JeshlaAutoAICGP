"""Explicit local document snapshots and a separate SQLite index per owner/project."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sqlite3

from agent.storage.projects import ProjectConfigurationError, project_namespace

MAX_DOCUMENTS = 20
MAX_TEXT = 12000
CHUNK_SIZE = 1200
CHUNK_STEP = 1000


class ProjectDocuments:
    def __init__(self, application_root, user, namespace, project_id):
        if any(not isinstance(v, str) or not v.strip() or len(v) > 128 for v in (user, namespace)):
            raise ProjectConfigurationError("Invalid document owner or space.")
        project_namespace(namespace, project_id)
        identity = json.dumps([user, namespace, project_id], ensure_ascii=False)
        self.identity = hashlib.sha256(identity.encode()).hexdigest()
        self.path = Path(application_root) / "outputs/knowledge" / self.identity / "documents.sqlite3"

    @contextmanager
    def _db(self, write=False):
        if not write and not self.path.exists():
            yield None
            return
        db = None
        try:
            if write:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path if write else self.path.resolve().as_uri() + "?mode=ro", uri=not write, timeout=5)
            db.row_factory = sqlite3.Row
            if write:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS identity (scope TEXT PRIMARY KEY)")
                db.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT UNIQUE NOT NULL, text TEXT NOT NULL, sha256 TEXT NOT NULL, truncated INTEGER NOT NULL, updated_at TEXT NOT NULL)")
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(doc_id UNINDEXED, start UNINDEXED, finish UNINDEXED, text, tokenize='unicode61')")
                if not db.execute("SELECT scope FROM identity").fetchone():
                    db.execute("INSERT INTO identity VALUES (?)", (self.identity,))
            identity = db.execute("SELECT scope FROM identity").fetchall()
            if len(identity) != 1 or identity[0][0] != self.identity:
                raise ProjectConfigurationError("Document collection does not belong to this project scope.")
            yield db
            if write:
                db.commit()
        except (sqlite3.Error, OSError):
            raise ProjectConfigurationError("The project document index could not be read or saved. Keep the existing index and check local storage/SQLite support.") from None
        finally:
            if db is not None:
                db.close()

    def list(self):
        with self._db() as db:
            if db is None:
                return []
            return [dict(row) for row in db.execute("SELECT id,name,sha256,truncated,updated_at,length(text) AS characters FROM documents ORDER BY name COLLATE NOCASE,id")]

    def save(self, documents):
        if not isinstance(documents, list) or not 1 <= len(documents) <= 5:
            raise ProjectConfigurationError("Save one to five prepared documents at a time.")
        prepared = []
        for document in documents:
            if not isinstance(document, dict):
                raise ProjectConfigurationError("Prepare a document preview first.")
            name, text = document.get("name"), document.get("text")
            if not isinstance(name, str) or name in {"", ".", ".."} or len(name) > 160 or PureWindowsPath(name).name != name or any(ord(c) < 32 for c in name):
                raise ProjectConfigurationError("Use a document filename without a folder path.")
            if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
                raise ProjectConfigurationError("Prepared document text must contain 1–12,000 characters.")
            if type(document.get("truncated")) is not bool:
                raise ProjectConfigurationError("Document extraction limits must be recorded.")
            key = name.casefold()
            prepared.append((hashlib.sha256(key.encode()).hexdigest()[:32], name, key, text,
                             hashlib.sha256(text.encode()).hexdigest(), int(document["truncated"]), datetime.now(timezone.utc).isoformat()))
        if len({row[2] for row in prepared}) != len(prepared):
            raise ProjectConfigurationError("Choose distinct document filenames; matching names replace their saved snapshot.")
        with self._db(write=True) as db:
            existing = {row[0] for row in db.execute("SELECT name_key FROM documents")}
            if len(existing | {row[2] for row in prepared}) > MAX_DOCUMENTS:
                raise ProjectConfigurationError("This project supports up to 20 saved documents. Remove a saved snapshot first.")
            for row in prepared:
                db.execute("DELETE FROM chunks WHERE doc_id=?", (row[0],))
                db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,text=excluded.text,sha256=excluded.sha256,truncated=excluded.truncated,updated_at=excluded.updated_at", row)
                for start in range(0, len(row[3]), CHUNK_STEP):
                    finish = min(start + CHUNK_SIZE, len(row[3]))
                    db.execute("INSERT INTO chunks(doc_id,start,finish,text) VALUES (?,?,?,?)", (row[0], start, finish, row[3][start:finish]))
                    if finish == len(row[3]):
                        break
        return self.list()

    def remove(self, document_id, expected_sha256):
        if not self.path.exists():
            raise ProjectConfigurationError("The saved document does not exist in this project.")
        with self._db(write=True) as db:
            row = db.execute("SELECT sha256 FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row or row[0] != expected_sha256:
                raise ProjectConfigurationError("The saved document changed or was removed. Refresh its list before removing it.")
            db.execute("DELETE FROM chunks WHERE doc_id=?", (document_id,))
            db.execute("DELETE FROM documents WHERE id=?", (document_id,))

    def search(self, tokens, limit=3):
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ProjectConfigurationError("Search returns one to five document excerpts.")
        if not isinstance(tokens, list) or len(tokens) > 24 or any(not isinstance(t, str) or not re.fullmatch(r"[^\W_]+", t) for t in tokens):
            raise ProjectConfigurationError("Use bounded plain-word search terms.")
        if not tokens:
            return []
        expression = " OR ".join('"' + token + '"' for token in dict.fromkeys(tokens))
        with self._db() as db:
            if db is None:
                return []
            return [dict(row) for row in db.execute("SELECT documents.name,documents.sha256,documents.truncated,length(documents.text) AS characters,chunks.start,chunks.finish,chunks.text,bm25(chunks) AS score FROM chunks JOIN documents ON documents.id=chunks.doc_id WHERE chunks MATCH ? ORDER BY score,documents.name,chunks.rowid LIMIT ?", (expression, limit))]
