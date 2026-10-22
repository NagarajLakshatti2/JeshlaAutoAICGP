"""SQLite-backed structured memory that survives agent process restarts.

This store is separate from LangGraph's checkpoint database:
checkpoints resume a conversation/thread, while this module stores reusable
facts under an explicit ``user_id`` and ``namespace`` across threads.
Only JSON-serializable values are accepted so memory remains portable.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from agent.config.paths import DATA_ROOT
from typing import Any


class LongTermMemory:
    """Persist JSON values keyed by user, namespace, and memory key.

    Example::

        with LongTermMemory("data/long_term_memory.sqlite3") as memory:
            memory.save("user-123", "preferences", "language", "Kannada")
            language = memory.get("user-123", "preferences", "language")

    A database file is created automatically. Pass ``:memory:`` for an
    in-memory database, mainly useful for isolated tests.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        project_root = DATA_ROOT
        if db_path is None:
            db_path = project_root / "data" / "long_term_memory.sqlite3"
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.db_path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    user_id TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, namespace, memory_key)
                )
                """
            )

            columns={row["name"] for row in self._connection.execute("PRAGMA table_info(long_term_memories)")}
            additions={"source_kind":"TEXT NOT NULL DEFAULT 'legacy_unknown'",
                       "source_ref":"TEXT NOT NULL DEFAULT ''",
                       "verification_status":"TEXT NOT NULL DEFAULT 'unverified'"}
            for name,definition in additions.items():
                if name not in columns:
                    self._connection.execute(f"ALTER TABLE long_term_memories ADD COLUMN {name} {definition}")

            self._connection.execute("""CREATE TABLE IF NOT EXISTS memory_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, namespace TEXT NOT NULL, memory_key TEXT NOT NULL,
                value_json TEXT NOT NULL, source_kind TEXT NOT NULL, source_ref TEXT NOT NULL,
                verification_status TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, superseded_at TEXT NOT NULL,
                FOREIGN KEY(user_id,namespace,memory_key)
                    REFERENCES long_term_memories(user_id,namespace,memory_key) ON DELETE CASCADE
            )""")
            self._connection.execute("CREATE INDEX IF NOT EXISTS memory_revision_scope ON memory_revisions(user_id,namespace,memory_key,id)")

            self._connection.execute("""CREATE TABLE IF NOT EXISTS memory_suggestions (
                id TEXT PRIMARY KEY,user_id TEXT NOT NULL,namespace TEXT NOT NULL,
                memory_key TEXT NOT NULL,value_json TEXT NOT NULL,source_kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL
            )""")

    @staticmethod
    def _validate_identity(user_id: str, namespace: str, key: str) -> None:
        for name, value in (("user_id", user_id), ("namespace", namespace), ("key", key)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def save(
        self,
        user_id: str,
        namespace: str,
        key: str,
        value: Any,
        *,
        source_kind: str = "unspecified",
        source_ref: str = "",
        verification_status: str = "unverified",
    ) -> None:
        """Insert/replace a fact and its current provenance; creation time stays fixed.

        Replacing a value resets verification unless explicitly supplied by a
        trusted evidence-producing caller. This API does not verify truth.
        """
        self._validate_identity(user_id, namespace, key)
        if source_kind not in {"unspecified","user_statement","seed_import","tool_evidence","assistant_report"}:
            raise ValueError("Unsupported memory source kind")
        if not isinstance(source_ref,str) or len(source_ref)>500 or "\n" in source_ref or "\r" in source_ref:
            raise ValueError("source_ref must be a single-line reference within 500 characters")
        if verification_status not in {"unverified","verified"}:
            raise ValueError("Unsupported verification status")
        if verification_status=="verified" and (source_kind!="tool_evidence" or not source_ref.strip()):
            raise ValueError("Verified memory requires tool evidence and a source reference")
        try:
            value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise ValueError("value must be JSON-serializable") from error

        now = self._now()
        with self._lock, self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            previous=self._connection.execute("SELECT * FROM long_term_memories WHERE user_id=? AND namespace=? AND memory_key=?",(user_id,namespace,key)).fetchone()
            if previous and (previous["value_json"],previous["source_kind"],previous["source_ref"],previous["verification_status"]) != (value_json,source_kind,source_ref,verification_status):
                self._connection.execute("""INSERT INTO memory_revisions
                    (user_id,namespace,memory_key,value_json,source_kind,source_ref,verification_status,created_at,updated_at,superseded_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (user_id,namespace,key,previous["value_json"],previous["source_kind"],previous["source_ref"],previous["verification_status"],previous["created_at"],previous["updated_at"],now))
            self._connection.execute(
                """
                INSERT INTO long_term_memories
                    (user_id, namespace, memory_key, value_json, created_at, updated_at, source_kind, source_ref, verification_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, namespace, memory_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at,
                    source_kind = excluded.source_kind,
                    source_ref = excluded.source_ref,
                    verification_status = excluded.verification_status
                """,
                (user_id, namespace, key, value_json, now, now, source_kind, source_ref, verification_status),
            )

    def history(self, user_id: str, namespace: str, key: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return superseded versions only; never inject them as current facts."""
        self._validate_identity(user_id,namespace,key)
        if type(limit) is not int or not 1<=limit<=50:
            raise ValueError("History limit must be from 1 to 50")
        with self._lock:
            rows=self._connection.execute("SELECT * FROM memory_revisions WHERE user_id=? AND namespace=? AND memory_key=? ORDER BY id DESC LIMIT ?",(user_id,namespace,key,limit)).fetchall()
        result=[]
        for row in rows:
            record=dict(row)
            record["value"]=json.loads(record.pop("value_json"))
            result.append(record)
        return result

    def get(self, user_id: str, namespace: str, key: str, default: Any = None) -> Any:
        """Return a decoded value, or ``default`` if no memory exists."""
        self._validate_identity(user_id, namespace, key)
        with self._lock:
            row = self._connection.execute(
                """
                SELECT value_json FROM long_term_memories
                WHERE user_id = ? AND namespace = ? AND memory_key = ?
                """,
                (user_id, namespace, key),
            ).fetchone()
        return json.loads(row["value_json"]) if row else default

    def list(
        self,
        user_id: str,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """List one user's memories, optionally limited to a namespace."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")

        with self._lock:
            if namespace is None:
                rows = self._connection.execute(
                    """
                    SELECT namespace, memory_key, value_json, created_at, updated_at, source_kind, source_ref, verification_status
                    FROM long_term_memories WHERE user_id = ?
                    ORDER BY namespace, memory_key
                    """,
                    (user_id,),
                ).fetchall()
            else:
                if not isinstance(namespace, str) or not namespace.strip():
                    raise ValueError("namespace must be a non-empty string")
                rows = self._connection.execute(
                    """
                    SELECT namespace, memory_key, value_json, created_at, updated_at, source_kind, source_ref, verification_status
                    FROM long_term_memories
                    WHERE user_id = ? AND namespace = ?
                    ORDER BY memory_key
                    """,
                    (user_id, namespace),
                ).fetchall()

        return [
            {
                "namespace": row["namespace"],
                "key": row["memory_key"],
                "value": json.loads(row["value_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "source_kind": row["source_kind"],
                "source_ref": row["source_ref"],
                "verification_status": row["verification_status"],
            }
            for row in rows
        ]

    def search(self, user_id: str, namespace: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Rank scoped facts by lexical overlap; no model/network calls or cross-user search."""
        if not isinstance(query, str) or not query.strip() or len(query) > 1500:
            raise ValueError("query must contain 1 to 1500 characters")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        terms = set(re.findall(r"[^\W_]+", query.casefold()))
        ranked = []
        for row in self.list(user_id, namespace):
            text = row["key"] + " " + json.dumps(row["value"], ensure_ascii=False)
            tokens = set(re.findall(r"[^\W_]+", text.casefold()))
            score = len(terms & tokens)
            if score:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["key"]))
        return [row for _, row in ranked[:limit]]

    def semantic_search(self,user_id,namespace,query,limit=20,*,encoder=None):
        """Optional CPU embeddings; no automatic downloads or fact mutation."""
        self._validate_identity(user_id,namespace,"search")
        if not isinstance(query,str) or not query.strip() or len(query)>1500:raise ValueError("Query must contain 1 to 1500 characters")
        if type(limit) is not int or not 1<=limit<=50:raise ValueError("Limit must be 1 to 50")
        with self._lock:
            rows=self._connection.execute("SELECT memory_key,value_json,created_at,updated_at,source_kind,source_ref,verification_status FROM long_term_memories WHERE user_id=? AND namespace=? ORDER BY updated_at DESC,memory_key LIMIT 201",(user_id,namespace)).fetchall()
        facts=[{"key":row["memory_key"],"namespace":namespace,"value":json.loads(row["value_json"]),**{key:row[key] for key in ("created_at","updated_at","source_kind","source_ref","verification_status")}} for row in rows[:200]]
        if not facts:return {"facts":[],"mode":"semantic","truncated":False,"note":"No facts in selected scope."}
        from agent.memory.semantic_search import rank_facts
        ranked=rank_facts(facts,query,limit,encoder=encoder)
        return {"facts":ranked,"mode":"semantic","truncated":len(rows)>200,"note":"Local cosine similarity, not truth or contradiction verification. Newest 200 facts considered; values bounded to 2000 characters for embedding. Scores below 0.35 omitted."}

    def review(self,user_id,namespace,query,*,mode="lexical",stale_days=90,encoder=None):
        """Advisory candidates only: never infer truth, merge or delete facts."""
        if type(stale_days) is not int or not 1<=stale_days<=36500:raise ValueError("stale_days must be 1 to 36500")
        if mode=="semantic":
            retrieved=self.semantic_search(user_id,namespace,query,limit=10,encoder=encoder)
            facts=retrieved["facts"];truncated=retrieved["truncated"]
        elif mode=="lexical":
            facts=self.search(user_id,namespace,query,limit=10);truncated=len(facts)==10
        else:raise ValueError("Unsupported review mode")
        now=datetime.now(timezone.utc);reviewed=[]
        for fact in facts:
            try:
                updated=datetime.fromisoformat(fact["updated_at"])
                if updated.tzinfo is None:raise ValueError()
                age=max(0,(now-updated).total_seconds()/86400)
                review_status="age_review" if age>=stale_days else "recently_stored"
            except (ValueError,TypeError):age=None;review_status="unknown_date"
            reviewed.append({**fact,"age_days":round(age,2) if age is not None else None,"review_status":review_status})
        pairs=[]
        for i,left in enumerate(reviewed):
            for right in reviewed[i+1:]:
                if left["value"]!=right["value"] and len(pairs)<10:
                    pairs.append({"keys":[left["key"],right["key"]],"status":"potential_conflict_requires_review"})
        return {"facts":reviewed,"candidate_pairs":pairs,"mode":mode,"stale_days":stale_days,"truncated":truncated,"note":"Related differing facts are candidates, not proven contradictions; check source, project, timeframe and user intent before deciding. Storage age does not prove staleness. Ask for clarification; use explicit REMEMBER/FORGET only when instructed. No values or verification states changed. At most ten facts and ten pairs; this is not exhaustive conflict detection."}

    def propose(self,user_id,namespace,key,value,*,source_kind="assistant_report"):
        self._validate_identity(user_id,namespace,key)
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}",key) or not isinstance(value,str) or not value.strip() or len(value)>2000:
            raise ValueError("Suggestion requires a valid key and 1 to 2000 characters")
        if source_kind not in {"assistant_report","user_statement"}:raise ValueError("Invalid suggestion source")
        with self._lock,self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            count=self._connection.execute("SELECT count(*) FROM memory_suggestions WHERE user_id=? AND namespace=? AND status='pending'",(user_id,namespace)).fetchone()[0]
            if count>=20:raise ValueError("Review pending suggestions before proposing more")
            identifier="suggest-"+uuid.uuid4().hex
            self._connection.execute("INSERT INTO memory_suggestions VALUES (?,?,?,?,?,?,?,?)",(identifier,user_id,namespace,key,json.dumps(value,ensure_ascii=False),source_kind,"pending",self._now()))
        return {"id":identifier,"key":key,"value":value,"status":"pending","note":"Not saved as a fact. Review with SHOW SUGGESTIONS, then ACCEPT MEMORY id or REJECT MEMORY id."}

    def suggestions(self,user_id,namespace):
        self._validate_identity(user_id,namespace,"suggestions")
        with self._lock:
            rows=self._connection.execute("SELECT id,memory_key,value_json,source_kind,created_at FROM memory_suggestions WHERE user_id=? AND namespace=? AND status='pending' ORDER BY created_at,id LIMIT 20",(user_id,namespace)).fetchall()
        return [{"id":r["id"],"key":r["memory_key"],"value":json.loads(r["value_json"]),"source_kind":r["source_kind"],"created_at":r["created_at"]} for r in rows]

    def decide_suggestion(self,user_id,namespace,identifier,*,accept):
        self._validate_identity(user_id,namespace,identifier)
        if type(accept) is not bool:raise ValueError("Explicit accept/reject required")
        with self._lock,self._connection:
            self._connection.execute("BEGIN IMMEDIATE")
            row=self._connection.execute("SELECT * FROM memory_suggestions WHERE id=? AND user_id=? AND namespace=?",(identifier,user_id,namespace)).fetchone()
            if not row:raise ValueError("Suggestion not found in this memory scope")
            if row["status"]!="pending":return {"id":identifier,"status":row["status"],"note":"Already decided; no writes."}
            if accept:
                if self._connection.execute("SELECT 1 FROM long_term_memories WHERE user_id=? AND namespace=? AND memory_key=?",(user_id,namespace,row["memory_key"])).fetchone():
                    raise ValueError("Key already exists. Suggestion not applied; use explicit REMEMBER to correct that key or reject this suggestion.")
                now=self._now()
                self._connection.execute("INSERT INTO long_term_memories (user_id,namespace,memory_key,value_json,created_at,updated_at,source_kind,source_ref,verification_status) VALUES (?,?,?,?,?,?,?,?,?)",(user_id,namespace,row["memory_key"],row["value_json"],now,now,row["source_kind"],"Accepted suggestion "+identifier,"unverified"))
            status="accepted" if accept else "rejected"
            self._connection.execute("UPDATE memory_suggestions SET status=? WHERE id=?",(status,identifier))
        return {"id":identifier,"status":status}

    def delete(self, user_id: str, namespace: str, key: str) -> bool:
        """Delete one value and return whether a row was removed."""
        self._validate_identity(user_id, namespace, key)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                DELETE FROM long_term_memories
                WHERE user_id = ? AND namespace = ? AND memory_key = ?
                """,
                (user_id, namespace, key),
            )
            suggestions=self._connection.execute("DELETE FROM memory_suggestions WHERE user_id=? AND namespace=? AND memory_key=?",(user_id,namespace,key))
        return cursor.rowcount > 0 or suggestions.rowcount > 0

    def delete_user(self, user_id: str) -> int:
        """Delete all memories for one user; return the number removed."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM long_term_memories WHERE user_id = ?", (user_id,)
            )
            self._connection.execute("DELETE FROM memory_suggestions WHERE user_id=?",(user_id,))
        return cursor.rowcount

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "LongTermMemory":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def format_memory_record(row):
    """Same fact prefix as before, with provenance visible to users and the LLM."""
    metadata={key:row.get(key,"unknown") for key in ("source_kind","source_ref","verification_status","created_at","updated_at")}
    return f"- {row['key']}: {json.dumps(row['value'],ensure_ascii=False)} | metadata: {json.dumps(metadata,ensure_ascii=False)}"
