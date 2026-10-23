"""Fail-closed checks for the opt-in actual-chat browser acceptance fixture."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from agent.storage.chats import ChatCatalog
from evaluations.summary_snapshot_browser_acceptance import digest, inspect_stores, read_snapshot, snapshot_graph


class ActualSummarySnapshotTests(unittest.TestCase):
    def seed(self, root, session="default", user="local-user", space="project", summary=None):
        summary = summary if summary is not None else json.dumps({"facts": ["legacy source detail"], "decisions": [], "open_questions": []})
        identity = json.dumps([user, space, session], ensure_ascii=False)
        thread = "main-agent-session" if (user, space, session) == ("local-user", "project", "default") else "session-" + digest(identity)
        catalog = ChatCatalog(root / "outputs/memory/chats.sqlite3", user, space)
        catalog.register(session)
        catalog.append(session, "Original question", "Original answer")
        with closing(sqlite3.connect(root / "agent_memory.db")) as connection:
            snapshot_graph(connection).update_state({"configurable": {"thread_id": thread}}, {"summary": summary, "history": "Original history"})
        return summary

    def test_read_only_snapshot_keeps_legacy_summary_and_exact_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = self.seed(root)
            paths = [root / "agent_memory.db", root / "outputs/memory/chats.sqlite3"]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            result = read_snapshot(root, "default")
            self.assertEqual(result["summary"], summary)
            self.assertEqual(result["turns"], [["Original question", "Original answer"]])
            self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths])

    def test_other_user_and_missing_summary_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.seed(root)
            with self.assertRaisesRegex(ValueError, "no saved summary"):
                read_snapshot(root, "default", user="other-user")
            self.seed(root, session="empty", summary="")
            with self.assertRaisesRegex(ValueError, "no saved summary"):
                read_snapshot(root, "empty")

    def test_store_review_rejects_cross_chat_summary_swap_and_archive_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = ChatCatalog(root / "chats.sqlite3", "snapshot-user", "snapshot-space")
            cases = {name: {"summary": json.dumps({"facts": [name], "decisions": [], "open_questions": []}), "turns": [[name + " question", name + " answer"]]} for name in ("alpha", "beta")}
            for case in cases.values():
                case["summary_sha256"] = digest(case["summary"])
            with closing(sqlite3.connect(root / "checkpoints.sqlite3")) as connection:
                graph = snapshot_graph(connection)
                for name, case in cases.items():
                    catalog.register(name)
                    catalog.append(name, *case["turns"][0])
                    graph.update_state({"configurable": {"thread_id": "snapshot-" + name}}, {"summary": case["summary"]})
                self.assertTrue(all(all(values.values()) for values in inspect_stores(root, cases, {"alpha": 0, "beta": 0}).values()))
                graph.update_state({"configurable": {"thread_id": "snapshot-alpha"}}, {"summary": cases["beta"]["summary"]})
            with closing(sqlite3.connect(root / "chats.sqlite3")) as connection, connection:
                connection.execute("DELETE FROM turns WHERE session='beta'")
            checks = inspect_stores(root, cases, {"alpha": 0, "beta": 0})
            self.assertFalse(checks["alpha"]["exact_original_summary_retained"])
            self.assertFalse(checks["alpha"]["summary_differs_from_other_chat"])
            self.assertFalse(checks["beta"]["all_original_turns_intact"])
            self.assertFalse(checks["beta"]["expected_full_transcript_count"])


if __name__ == "__main__":
    unittest.main()
