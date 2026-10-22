"""One durable text-answer continuation per scoped chat; no action receipts."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time

MAX_PAYLOAD_BYTES = 512000


class AnswerContinuations:
    def __init__(self, path):
        self.path = Path(path)

    def load(self, scope):
        if not self.path.exists(): return None
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            row = db.execute("SELECT payload FROM answer_continuations WHERE scope=?", (scope,)).fetchone()
        if not row: return None
        if len(row[0].encode("utf-8")) > MAX_PAYLOAD_BYTES: raise ValueError("Saved answer exceeds its data budget.")
        return json.loads(row[0])

    def save(self, scope, value):
        from agent.runtime.continuations import validate_ledger
        validate_ledger(value)
        data = json.dumps(value, ensure_ascii=False)
        if len(data.encode("utf-8")) > MAX_PAYLOAD_BYTES: raise ValueError("Saved answer exceeds its data budget.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS answer_continuations (scope TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at REAL NOT NULL)")
            db.execute("INSERT INTO answer_continuations(scope,payload,updated_at) VALUES(?,?,?) "
                       "ON CONFLICT(scope) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at", (scope, data, time.time()))

    def discard(self, scope):
        if not self.path.exists(): return
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute("DELETE FROM answer_continuations WHERE scope=?", (scope,))
