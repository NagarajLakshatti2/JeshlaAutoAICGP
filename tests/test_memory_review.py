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


class MemoryReviewEvidenceTests(unittest.TestCase):
    def test_small_review_keeps_existing_contract(self):
        from agent.memory.evidence import bound_review_evidence
        with LongTermMemory(":memory:") as memory:
            memory.save("u", "p", "report_format", "PDF")
            original = memory.review("u", "p", "report")
            self.assertIs(bound_review_evidence(original), original)

    def test_large_review_preserves_whole_facts_sources_and_visible_pairs(self):
        import copy
        import json
        from agent.memory.evidence import bound_review_evidence
        with LongTermMemory(":memory:") as memory:
            for index in range(6):
                memory.save("u", "p", "report_" + str(index), "context " * 175 + str(index), source_kind="user_statement", source_ref="fixture-" + str(index))
            stored = memory.list("u", "p")
            original = memory.review("u", "p", "report")
            before = copy.deepcopy(original)
            bounded = bound_review_evidence(original)
            raw = json.dumps(bounded, ensure_ascii=False, default=str)
            self.assertLessEqual(len(raw), 8000)
            self.assertTrue(json.loads(raw)["truncated"])
            self.assertGreater(len(bounded["facts"]), 0)
            self.assertLess(len(bounded["facts"]), len(original["facts"]))
            self.assertIn("not proven contradictions", bounded["note"])
            self.assertIn("omitted", bounded["note"])
            keys = {fact["key"] for fact in bounded["facts"]}
            originals = {fact["key"]: fact for fact in original["facts"]}
            for fact in bounded["facts"]:
                self.assertEqual(fact, originals[fact["key"]])
            for pair in bounded["candidate_pairs"]:
                self.assertTrue(set(pair["keys"]) <= keys)
            self.assertEqual(original, before)
            self.assertEqual(memory.list("u", "p"), stored)

    def test_oversized_metadata_returns_bounded_failure(self):
        import json
        from agent.memory.evidence import bound_review_evidence
        result = bound_review_evidence({"facts": [], "candidate_pairs": [], "note": "x" * 9000})
        self.assertIn("error", result)
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(json.dumps(result)), 8000)

    def test_real_conversation_delivers_valid_review_json(self):
        import json
        from pathlib import Path
        import tempfile
        from agent.runtime.conversation import answer_question
        from agent.tools.project_tools import ProjectTools
        seen = []
        with tempfile.TemporaryDirectory() as folder, LongTermMemory(":memory:") as memory:
            for index in range(6):
                memory.save("u", "p", "report_" + str(index), "context " * 175 + str(index))
            before = memory.list("u", "p")
            def model(messages, specs):
                if not seen:
                    seen.append("requested")
                    return {"role": "assistant", "content": "", "tool_calls": [{"id": "review-1", "type": "function", "function": {"name": "review_memory", "arguments": '{"query":"report"}'}}]}
                raw = messages[-1]["content"]
                self.assertLessEqual(len(raw), 8000)
                evidence = json.loads(raw)
                self.assertTrue(evidence["truncated"])
                self.assertIn("not proven contradictions", evidence["note"])
                seen.append(evidence)
                return {"role": "assistant", "content": "The review is limited; which report fact should I inspect?"}
            result = answer_question({"question": "Review report facts."}, model=model, project_root=Path(folder), tools=ProjectTools(folder), document_search=lambda **kwargs: None, memory_review=lambda **kwargs: memory.review("u", "p", **kwargs))
            self.assertEqual(len(seen), 2)
            self.assertIn("limited", result["answer"])
            self.assertEqual(memory.list("u", "p"), before)


class MemorySourceKeyTests(unittest.TestCase):
    def test_exact_keys_and_complete_json_fence_pass(self):
        from agent.memory.evidence import memory_key_issue
        question = "Return sources as an array of exact saved fact keys."
        for answer in ('{"sources":["report_atlas"]}', '```json\n{"sources":["report_atlas"]}\n```'):
            self.assertIsNone(memory_key_issue(question, answer, {"report_atlas"}))

    def test_provenance_and_constructed_ids_are_rejected_without_rewriting(self):
        import json
        from agent.memory.evidence import memory_key_issue
        for sources in (["fixture#report_atlas"], ["space/report_atlas"], ["unknown"], "report_atlas", [42]):
            answer = json.dumps({"sources": sources})
            self.assertIsNotNone(memory_key_issue("Use exact saved fact keys", answer, {"report_atlas"}))
            self.assertEqual(json.loads(answer)["sources"], sources)

    def test_non_key_requests_and_unrelated_formats_are_unchanged(self):
        from agent.memory.evidence import memory_key_issue
        cases = [("Give provenance references", '{"sources":["fixture#report_atlas"]}', {"report_atlas"}),
                 ("Use exact keys", "ordinary prose", {"report_atlas"}),
                 ("Use exact keys", '{"answer":"report_atlas"}', {"report_atlas"}),
                 ("Use exact keys", '{"sources":["report_atlas"]}', set())]
        for question, answer, visible in cases:
            self.assertIsNone(memory_key_issue(question, answer, visible))

    def conversation(self, *, repair, question="Review report facts; return sources as exact saved fact keys."):
        import json
        from pathlib import Path
        import tempfile
        from agent.runtime.conversation import answer_question
        from agent.tools.project_tools import ProjectTools
        with tempfile.TemporaryDirectory() as folder, LongTermMemory(":memory:") as memory:
            memory.save("u", "p", "report_atlas", "PDF", source_kind="user_statement", source_ref="fixture#report_atlas")
            memory.save("other", "p", "report_private", "CSV")
            before = memory.list("u", "p")
            calls, reviews = [], []
            def model(messages, specs):
                calls.append(messages)
                if len(calls) == 1:
                    return {"role":"assistant", "tool_calls":[{"id":"review", "function":{"name":"review_memory", "arguments":'{"query":"report"}'}}]}
                keys = ["report_atlas"] if repair and len(calls) == 3 else ["fixture#report_atlas"]
                return {"role":"assistant", "content":json.dumps({"sources":keys, "answer":"PDF"})}
            def review(**kwargs):
                reviews.append(kwargs)
                return memory.review("u", "p", **kwargs)
            result = answer_question({"question":question}, model=model, project_root=Path(folder), tools=ProjectTools(folder), document_search=lambda **k: {}, memory_review=review)
            self.assertEqual(memory.list("u", "p"), before)
            self.assertEqual(len(reviews), 1)
            return result, len(calls)

    def test_real_review_corrects_provenance_id_once_without_replaying_tools(self):
        import json
        result, calls = self.conversation(repair=True)
        self.assertEqual(calls, 3)
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertEqual(json.loads(result["answer"])["sources"], ["report_atlas"])

    def test_repeated_wrong_key_is_not_published_as_completed(self):
        result, calls = self.conversation(repair=False)
        self.assertEqual(calls, 3)
        self.assertEqual(result["task_status"], "incomplete")
        self.assertFalse(result["answer_available"])
        self.assertNotIn("fixture#", result["answer"])

    def test_provenance_reference_remains_valid_when_exact_keys_not_requested(self):
        result, calls = self.conversation(repair=False, question="Review report facts and return provenance references.")
        self.assertEqual(calls, 2)
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertIn("fixture#report_atlas", result["answer"])
