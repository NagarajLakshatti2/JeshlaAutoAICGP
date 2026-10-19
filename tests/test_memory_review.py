import unittest
from unittest.mock import patch
from agent.memory.long_term_memory import LongTermMemory
class MemoryReviewTests(unittest.TestCase):
    def test_candidates_age_scope_and_no_mutation(self):
        with LongTermMemory(":memory:") as m:
            with patch.object(m,"_now",return_value="2000-01-01T00:00:00+00:00"):
                m.save("u","p","report_a","HTML")
            m.save("u","p","report_b","PDF")
            m.save("other","p","report_private","CSV")
            before=m.list("u","p")
            result=m.review("u","p","report",stale_days=30)
            self.assertEqual(len(result["facts"]),2)
            self.assertEqual(result["candidate_pairs"][0]["status"],"potential_conflict_requires_review")
            self.assertEqual(next(r for r in result["facts"] if r["key"]=="report_a")["review_status"],"age_review")
            self.assertEqual(m.list("u","p"),before)
    def test_equal_facts_are_not_conflict_candidates(self):
        with LongTermMemory(":memory:") as m:
            m.save("u","p","report_a","PDF");m.save("u","p","report_b","PDF")
            self.assertEqual(m.review("u","p","report")["candidate_pairs"],[])
            with self.assertRaises(ValueError):m.review("u","p","report",stale_days=0)
