"""Fail-closed scoring for explicit local source/location relevance labels."""
import unittest
from evaluations.document_relevance_acceptance import score_case


class DocumentRelevanceScoringTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "format", "source": "sample.txt", "location": "2", "expected_fragments": ["archive PDF", "preview HTML"]}
        self.hit = {"source": "sample.txt", "location": "2", "text": "archive PDF and preview HTML", "ref": "DOC-0123456789abcdef", "truncated": False}

    def test_fragments_in_the_wrong_source_or_location_do_not_pass(self):
        for changed in ({"source": "other.txt"}, {"location": "3"}):
            with self.subTest(changed=changed):
                result = score_case(self.case, {"sources": [{**self.hit, **changed}]})
                self.assertFalse(result["passed"])
                self.assertFalse(result["checks"]["expected_source_and_location"])

    def test_missing_visible_fragment_or_invalid_reference_fails(self):
        for changed in ({"text": "archive PDF only"}, {"ref": "invented-reference"}):
            with self.subTest(changed=changed):
                self.assertFalse(score_case(self.case, {"sources": [{**self.hit, **changed}]})["passed"])
        self.assertTrue(score_case(self.case, {"sources": [self.hit]})["passed"])

    def test_absent_keyword_case_rejects_any_returned_candidate(self):
        case = {"id": "absent", "source": None, "location": None, "expected_fragments": []}
        self.assertFalse(score_case(case, {"sources": [self.hit]})["passed"])
        self.assertTrue(score_case(case, {"sources": []})["passed"])


if __name__ == "__main__":
    unittest.main()
