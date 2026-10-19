import sqlite3,tempfile,unittest
from pathlib import Path
from agent.memory.long_term_memory import LongTermMemory

class MemoryRevisionTests(unittest.TestCase):
    def test_revision_restart_and_current_value_separation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"facts.sqlite3"
            with LongTermMemory(path) as m:
                m.save("u","p","format","HTML",source_kind="user_statement")
                m.save("u","p","format","PDF",source_kind="user_statement")
                m.save("u","p","format","PDF",source_kind="user_statement")
            with LongTermMemory(path) as m:
                self.assertEqual(m.get("u","p","format"),"PDF")
                self.assertEqual(len(m.history("u","p","format")),1)
                self.assertEqual(m.history("u","p","format")[0]["value"],"HTML")
                self.assertEqual(m.search("u","p","HTML"),[])
                self.assertEqual(m.history("other","p","format"),[])
                self.assertEqual(m.history("u","other","format"),[])
                self.assertEqual(m.history("u","p","other"),[])

    def test_forget_erases_revisions_and_different_keys_stay_separate(self):
        with LongTermMemory(":memory:") as m:
            m.save("u","p","format","HTML");m.save("u","p","format","PDF")
            m.save("u","p","other_format","HTML")
            self.assertTrue(m.delete("u","p","format"))
            self.assertEqual(m.history("u","p","format"),[])
            self.assertEqual(m.get("u","p","other_format"),"HTML")
            m.save("u","p","other_format","CSV")
            m.delete_user("u")
            self.assertEqual(m.history("u","p","other_format"),[])

    def test_failed_update_rolls_back_revision(self):
        with LongTermMemory(":memory:") as m:
            m.save("u","p","key","original")
            m._connection.execute("CREATE TRIGGER deny_update BEFORE UPDATE ON long_term_memories BEGIN SELECT RAISE(ABORT,'blocked'); END;")
            with self.assertRaises(sqlite3.IntegrityError):m.save("u","p","key","changed")
            self.assertEqual(m.get("u","p","key"),"original")
            self.assertEqual(m.history("u","p","key"),[])
