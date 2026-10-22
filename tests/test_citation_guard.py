import unittest
from agent.citation_guard import citation_issue,visible_web_urls
from tests import test_conversation_sources as source_tests

class CitationGuardTests(unittest.TestCase):
    def test_unseen_url_and_internal_markers_rejected(self):
        self.assertIsNotNone(citation_issue("[fake](https://fake.test)",{"https://real.test"}))
        self.assertIsNone(citation_issue("[real](https://real.test)",{"https://real.test"}))
        self.assertIsNotNone(citation_issue("Docs【commentary:functions.web_search#1】",set()))
        self.assertIsNone(citation_issue("```java\nString url=\"https://example.test\";\n```",set()))
    def test_only_visible_successful_urls_are_registered(self):
        result={"results":[{"url":"https://real.test"},{"url":"https://hidden.test"},{"url":"https://user:pass@host.test"}]}
        self.assertEqual(visible_web_urls(result,'https://real.test https://user:pass@host.test'),{"https://real.test"})
        self.assertEqual(visible_web_urls({**result,"error":"failed"},'https://real.test'),set())
    def test_loop_corrects_citation_once(self):
        runner=source_tests.ConversationTests()
        result,calls=runner.run_answer([
            {"action":"web_search","arguments":{"query":"public docs"}},
            {"action":"finish","answer":"[fake](https://fake.test)"},
            {"action":"finish","answer":"[real](https://real.test)"}],web=lambda **k:{"results":[{"url":"https://real.test","snippet":"docs"}]})
        self.assertEqual(result["answer"],"[real](https://real.test)")
        self.assertEqual(len(calls),3)
    def test_repeated_bad_citations_stop_incomplete(self):
        result,_=source_tests.ConversationTests().run_answer([
            {"action":"web_search","arguments":{"query":"public docs"}},
            {"action":"finish","answer":"[fake](https://fake.test)"},
            {"action":"finish","answer":"[fake](https://fake.test)"}],web=lambda **k:{"results":[{"url":"https://real.test","snippet":"docs"}]})
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotIn("https://fake.test",result["answer"])
    def test_failed_required_search_cannot_claim_current_answer(self):
        result,_=source_tests.ConversationTests().run_answer([
            {"action":"web_search","arguments":{"query":"current version"}},
            {"action":"finish","answer":"Latest is 999."}],state={"question":"Latest version?","route":"web"},web=lambda **k:{"error":"offline"})
        self.assertEqual(result["task_status"],"incomplete")
        self.assertNotIn("999",result["answer"])


class ReadSourceLabelTests(unittest.TestCase):
    def test_missing_labels_preserve_code_and_only_add_actual_read_urls(self):
        from agent.policies.citations import append_read_sources,citation_issue
        url="https://official.example.test/rules"
        content="Explanation.\n```java\nclass Example {}\n```"
        result=append_read_sources(content,{url})
        self.assertTrue(result.startswith(content))
        self.assertIn(url,result);self.assertIsNone(citation_issue(result,{url}))

    def test_unknown_url_and_internal_markers_are_never_replaced_by_added_labels(self):
        from agent.policies.citations import append_read_sources,citation_issue
        url="https://official.example.test/rules"
        for content in ("[Unknown](https://unread.example.test)","Claim【commentary:functions.web_search#1】"):
            self.assertEqual(append_read_sources(content,{url}),content)
            self.assertIsNotNone(citation_issue(content,{url}))
