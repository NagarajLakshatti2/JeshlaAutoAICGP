import tempfile,unittest
from pathlib import Path
from agent.memory.long_term_memory import LongTermMemory

class MemorySuggestionTests(unittest.TestCase):
    def test_accept_is_explicit_persistent_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/"memory.sqlite3"
            with LongTermMemory(db) as m:
                suggestion=m.propose("u","p","format","PDF")
                self.assertIsNone(m.get("u","p","format"))
                self.assertEqual(m.search("u","p","PDF"),[])
            with LongTermMemory(db) as m:
                self.assertEqual(len(m.suggestions("u","p")),1)
                self.assertEqual(m.decide_suggestion("u","p",suggestion["id"],accept=True)["status"],"accepted")
                self.assertEqual(m.get("u","p","format"),"PDF")
                self.assertEqual(m.list("u","p")[0]["verification_status"],"unverified")
                self.assertEqual(m.list("u","p")[0]["source_kind"],"assistant_report")
                self.assertIn("no writes",m.decide_suggestion("u","p",suggestion["id"],accept=True)["note"])
                self.assertEqual(m.history("u","p","format"),[])

    def test_existing_key_cannot_be_overwritten_and_scope_is_fixed(self):
        with LongTermMemory(":memory:") as m:
            proposal=m.propose("u","p","format","PDF")
            m.save("u","p","format","HTML")
            for user,space in [("u","other"),("other","p")]:
                with self.assertRaises(ValueError):m.decide_suggestion(user,space,proposal["id"],accept=True)
            with self.assertRaises(ValueError):m.decide_suggestion("u","p",proposal["id"],accept=True)
            self.assertEqual(m.get("u","p","format"),"HTML")
            self.assertEqual(len(m.suggestions("u","p")),1)

    def test_reject_and_forget_do_not_resurrect(self):
        with LongTermMemory(":memory:") as m:
            proposal=m.propose("u","p","format","PDF")
            m.decide_suggestion("u","p",proposal["id"],accept=False)
            self.assertEqual(m.decide_suggestion("u","p",proposal["id"],accept=True)["status"],"rejected")
            self.assertIsNone(m.get("u","p","format"))
            proposal=m.propose("u","p","format","PDF")
            self.assertTrue(m.delete("u","p","format"))
            with self.assertRaises(ValueError):m.decide_suggestion("u","p",proposal["id"],accept=True)
            m.propose("u","p","other","test");m.delete_user("u")
            self.assertEqual(m.suggestions("u","p"),[])

    def test_pending_limit_and_validation(self):
        with LongTermMemory(":memory:") as m:
            for i in range(20):m.propose("u","p","key"+str(i),"value")
            with self.assertRaises(ValueError):m.propose("u","p","extra","value")
            self.assertEqual(len(m.suggestions("u","p")),20)
            for key,value in [("bad key","value"),("key",""),("key","x"*2001)]:
                with self.assertRaises(ValueError):m.propose("u","p",key,value)
