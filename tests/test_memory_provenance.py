import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agent.memory.long_term_memory import LongTermMemory,format_memory_record

class MemoryProvenanceTests(unittest.TestCase):
    def test_old_schema_migration_preserves_value_dates_and_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"old.sqlite3"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE long_term_memories(user_id TEXT NOT NULL,namespace TEXT NOT NULL,memory_key TEXT NOT NULL,value_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,namespace,memory_key))")
                conn.execute("INSERT INTO long_term_memories VALUES (?,?,?,?,?,?)",("u","p","format",json.dumps("PDF"),"old-created","old-updated"))
            conn.close()
            for _ in range(2):
                with LongTermMemory(path) as memory:
                    self.assertEqual(memory.get("u","p","format"),"PDF")
                    row=memory.list("u","p")[0]
                    self.assertEqual(row["created_at"],"old-created")
                    self.assertEqual(row["updated_at"],"old-updated")
                    self.assertEqual(row["source_kind"],"legacy_unknown")
                    self.assertEqual(row["verification_status"],"unverified")
                    self.assertEqual(memory.list("other","p"),[])

    def test_replacement_resets_old_verification_and_preserves_creation(self):
        with LongTermMemory(":memory:") as memory:
            with patch.object(memory,"_now",return_value="first"):
                memory.save("u","p","tool","Gradle",source_kind="tool_evidence",source_ref="settings.gradle",verification_status="verified")
            with patch.object(memory,"_now",return_value="second"):
                memory.save("u","p","tool","Maven",source_kind="user_statement",source_ref="REMEMBER command")
            row=memory.search("u","p","Maven")[0]
            self.assertEqual(row["created_at"],"first");self.assertEqual(row["updated_at"],"second")
            self.assertEqual(row["verification_status"],"unverified")
            self.assertEqual(row["source_kind"],"user_statement")
            self.assertTrue(memory.delete("u","p","tool"))

    def test_legacy_save_signature_remains_supported(self):
        with LongTermMemory(":memory:") as memory:
            memory.save("u","p","name","Example")
            self.assertEqual(memory.get("u","p","name"),"Example")
            row=memory.list("u","p")[0]
            self.assertEqual(row["source_kind"],"unspecified")
            self.assertIn('"verification_status": "unverified"',format_memory_record(row))

    def test_invalid_provenance_does_not_replace_fact(self):
        with LongTermMemory(":memory:") as memory:
            memory.save("u","p","name","Original")
            for kwargs in [{"source_kind":"invented"},{"verification_status":"verified"},{"source_kind":"user_statement","source_ref":"user","verification_status":"verified"},{"source_ref":"bad\nref"}]:
                with self.assertRaises(ValueError):memory.save("u","p","name","Changed",**kwargs)
            self.assertEqual(memory.get("u","p","name"),"Original")
