"""Ensure semantic calibration cannot claim success from weak match metrics."""
import unittest
from unittest.mock import patch
from agent.memory.long_term_memory import LongTermMemory
from evaluations.semantic_memory_calibration import retrieval_case


def fact(key):
    return {"key": key, "value": key, "namespace": "calibration-space", "semantic_score": 0.6}


class SemanticCalibrationTests(unittest.TestCase):
    def test_correct_candidate_is_not_enough_for_a_top_one_question(self):
        with LongTermMemory(":memory:") as memory, patch.object(memory, "semantic_search", return_value={"facts": [fact("wrong"), fact("expected")]}):
            row = retrieval_case(memory, "clear", "question", "expected", top_one=True)
            self.assertFalse(row["passed"])
            contextual = retrieval_case(memory, "context", "question", "expected", top_one=False)
            self.assertTrue(contextual["passed"])
            self.assertEqual(contextual["metric"], "recall_at_3")

    def test_unrelated_query_false_positive_fails_abstention(self):
        with LongTermMemory(":memory:") as memory, patch.object(memory, "semantic_search", return_value={"facts": [fact("unexpected")]}):
            row = retrieval_case(memory, "unrelated", "question", None, top_one=True)
            self.assertFalse(row["passed"])
            self.assertEqual(row["metric"], "abstention")

    def test_right_answer_with_foreign_scope_or_mutation_still_fails(self):
        with LongTermMemory(":memory:") as memory:
            def changed(*args, **kwargs):
                memory.save("calibration-user", "calibration-space", "new", "unwanted mutation")
                return {"facts": [{**fact("expected"), "namespace": "other-space", "value": "FOREIGN_SCOPE_CANARY"}]}
            with patch.object(memory, "semantic_search", side_effect=changed):
                row = retrieval_case(memory, "scope", "question", "expected", top_one=True)
            self.assertFalse(row["passed"])
            self.assertFalse(row["checks"]["read_does_not_mutate"])
            self.assertFalse(row["checks"]["other_scopes_excluded"])
            self.assertFalse(row["checks"]["scope_metadata_retained"])


if __name__ == "__main__":
    unittest.main()
