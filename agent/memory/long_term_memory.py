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
from datetime import datetime, timezone
from pathlib import Path
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
        project_root = Path(__file__).resolve().parents[2]
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
    ) -> None:
        """Insert or replace one memory value."""
        self._validate_identity(user_id, namespace, key)
        try:
            value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise ValueError("value must be JSON-serializable") from error

        now = self._now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO long_term_memories
                    (user_id, namespace, memory_key, value_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, namespace, memory_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, namespace, key, value_json, now, now),
            )

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
                    SELECT namespace, memory_key, value_json, created_at, updated_at
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
                    SELECT namespace, memory_key, value_json, created_at, updated_at
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
        return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> int:
        """Delete all memories for one user; return the number removed."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM long_term_memories WHERE user_id = ?", (user_id,)
            )
        return cursor.rowcount

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "LongTermMemory":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
