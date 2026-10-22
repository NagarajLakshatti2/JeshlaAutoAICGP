"""Source-first workflow acceptance with synthetic public evidence; no API/network."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.runtime import source_first as flow
from agent.runtime.conversation import answer_question
from agent.providers.errors import ProviderError


class SourceFirstTests(unittest.TestCase):
    url = "https://official.example.test/v17/rules"
    quote = "A subclass selects exactly one direct superclass."
    other = "A replacement method must preserve the declared method contract."
    question = "Explain programming inheritance with examples. Verify important rules against official documentation."

    def setUp(self):
        patcher = patch.dict(os.environ, {"AI_SOURCE_FIRST_DOCUMENTATION": "true", "AI_TECHNICAL_VERIFICATION": "auto",
            "AI_CHAT_MAX_CONVERSATION_CHARS": "36000"})
        patcher.start(); self.addCleanup(patcher.stop)
        self.plan = {"topics": ["Superclass relationship", "Method contract"],
            "search_queries": ["official version 17 inheritance"], "publisher_domains": ["official.example.test"],
            "candidate_urls": [self.url], "example_required": True}
        self.draft = {"sections": [self.section(1, "A subclass has one direct superclass.", self.quote),
                                   self.section(2, "Replacement methods preserve the declared contract.", self.other)],
            "example": {"language": "java", "code": 'class Parent {}\nclass Child extends Parent {}\nclass Demo { public static void main(String[] args) { System.out.println("example"); } }',
                        "expected_output": "example", "topics": [1]}}
        self.page = {"url": self.url, "text": self.quote + " " + self.other, "title": "Version 17 rules", "truncated": False}
        self.check = {"blocking": [], "advisory": []}
        self.web = Mock(return_value={"results": []})
        self.fetch = Mock(return_value=self.page)

    def section(self, topic, explanation, quote):
        return {"topic": topic, "explanation": explanation, "evidence": [{"source_id": "S1", "quote": quote}]}

    @staticmethod
    def reply(name, value):
        return {"role": "assistant", "tool_calls": [{"id": "data", "function": {"name": name, "arguments": json.dumps(value)}}]}

    def model(self, plan=None, draft=None, check=None):
        return Mock(side_effect=[self.reply("submit_documentation_plan", plan or self.plan),
            self.reply("submit_grounded_sections", draft or self.draft), self.reply("submit_grounding_findings", check or self.check)])

    def run_flow(self, model=None):
        return flow.answer_from_sources(self.question, model=model or self.model(), web=self.web, page_fetch=self.fetch)

    def test_evidence_is_collected_before_drafting_and_used_by_checks(self):
        order = []; captured = []
        replies = iter([self.plan, self.draft, self.check])
        def model(messages, specs):
            name = specs[0]["function"]["name"]
            order.append(name); captured.append(deepcopy(messages))
            return self.reply(name, next(replies))
        self.web.side_effect = lambda **k: order.append("search") or {"results": []}
        self.fetch.side_effect = lambda url: order.append("read") or self.page
        result = self.run_flow(model)
        self.assertEqual(order, ["submit_documentation_plan", "search", "read", "submit_grounded_sections", "submit_grounding_findings"])
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertEqual(json.loads(captured[1][1]["content"])["sources"][0]["text"], self.page["text"])
        self.assertIn(self.url, result["answer"])
        self.assertIn("Expected output (not executed)", result["answer"])
        self.assertIn("No compilation or execution was performed", result["answer"])

    def test_advisory_confirmations_do_not_veto_supported_sections(self):
        self.check["advisory"] = ["The claims agree with the excerpts; headings could be shorter."]
        result = self.run_flow()
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertIn("Replacement methods", result["answer"])

    def test_only_a_concretely_blocked_topic_is_withheld(self):
        self.check["blocking"] = [{"target": "topic-2", "kind": "unsupported",
            "claim": self.draft["sections"][1]["explanation"], "reason": "The supplied evidence lacks the asserted exception."}]
        result = self.run_flow()
        self.assertEqual(result["task_status"], "incomplete")
        self.assertEqual(result["execution_outcome"], "partial")
        self.assertTrue(result["answer_available"])
        self.assertIn(self.draft["sections"][0]["explanation"], result["answer"])
        self.assertNotIn(self.draft["sections"][1]["explanation"], result["answer"])
        self.assertIn("Method contract", result["answer"])
        self.assertIn("Complete example", result["answer"])

    def test_example_depending_on_blocked_topic_is_not_published(self):
        self.draft["example"]["topics"] = [1, 2]
        self.check["blocking"] = [{"target": "topic-2", "kind": "contradicted",
            "claim": self.draft["sections"][1]["explanation"], "reason": "An exact rule contradicts this claim."}]
        result = self.run_flow()
        self.assertNotIn("class Demo", result["answer"])
        self.assertIn("A complete source-grounded code example", result["answer"])
        self.assertEqual(result["execution_outcome"], "partial")

    def test_fabricated_quote_drops_its_section_without_discarding_real_evidence(self):
        self.draft["sections"][1]["evidence"][0]["quote"] = "This sentence was never returned by the actual source reader."
        result = self.run_flow()
        self.assertIn(self.draft["sections"][0]["explanation"], result["answer"])
        self.assertNotIn(self.draft["sections"][1]["explanation"], result["answer"])
        self.assertEqual(result["execution_outcome"], "partial")

    def test_unread_source_id_and_unread_citation_are_not_publishable(self):
        for change in (lambda section: section["evidence"][0].update(source_id="S9"),
                       lambda section: section.update(explanation="Read [unread](https://unread.example.test/rule).")):
            draft = deepcopy(self.draft); change(draft["sections"][1])
            with self.subTest(draft=draft):
                result = self.run_flow(self.model(draft=draft))
                self.assertEqual(result["execution_outcome"], "partial")
                self.assertNotIn("https://unread.example.test", result["answer"])

    def test_no_pages_means_no_draft_or_review_calls(self):
        self.fetch.return_value = {"error": "Source unavailable"}
        model = self.model()
        result = self.run_flow(model)
        self.assertFalse(result["answer_available"])
        self.assertEqual(result["execution_outcome"], "blocked")
        self.assertEqual(model.call_count, 1)

    def test_stale_publisher_redirect_is_not_accepted_as_official_evidence(self):
        self.fetch.return_value = {"url": "https://unrelated.example.test/rules", "text": self.page["text"]}
        result = self.run_flow()
        self.assertEqual(result["execution_outcome"], "blocked")

    def test_search_and_page_attempt_budgets_are_bounded_and_deduplicated(self):
        self.plan["search_queries"] = ["first public query", "second public query"]
        self.plan["candidate_urls"] = [self.url, self.url, self.url + "#part-2", self.url + "#part-3"]
        self.web.return_value = {"results": [{"url": self.url + "#part-4"}, {"url": self.url + "#part-5"}]}
        self.fetch.side_effect = lambda url: {"url": url, "text": self.page["text"]}
        self.run_flow()
        self.assertEqual(self.web.call_count, 2)
        self.assertEqual(self.fetch.call_count, 4)
        self.assertEqual(len({call.args[0] for call in self.fetch.call_args_list}), 4)

    def test_foreign_data_action_never_runs_and_format_retry_is_bounded(self):
        model = Mock(return_value=self.reply("delete_project", {"path": "unsafe"}))
        result = self.run_flow(model)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(result["execution_outcome"], "blocked")
        self.web.assert_not_called(); self.fetch.assert_not_called()
        self.assertIn("GROUNDING_FORMAT", result["answer"])

    def test_bogus_blocking_target_or_claim_is_not_used_to_publish_an_answer(self):
        model = self.model()
        invalid = {"blocking": [{"target": "topic-2", "kind": "unsupported", "claim": "A claim absent from the draft", "reason": "Missing source"}], "advisory": []}
        model.side_effect = [self.reply("submit_documentation_plan", self.plan), self.reply("submit_grounded_sections", self.draft),
                             self.reply("submit_grounding_findings", invalid), self.reply("submit_grounding_findings", invalid)]
        result = self.run_flow(model)
        self.assertEqual(result["execution_outcome"], "blocked")
        self.assertEqual(model.call_count, 4)
        self.assertIn("GROUNDING_FORMAT", result["answer"])

    def test_sections_follow_plan_order_without_duplicate_topic_output(self):
        self.draft["sections"] = [self.draft["sections"][1], self.draft["sections"][0], deepcopy(self.draft["sections"][0])]
        result = self.run_flow()
        self.assertEqual(result["answer"].count("### Superclass relationship"), 1)
        self.assertLess(result["answer"].index("### Superclass relationship"), result["answer"].index("### Method contract"))

    def test_generated_python_is_parsed_but_never_executed(self):
        self.draft["example"] = {"language": "python", "code": "import os\nos.system('never-execute')", "expected_output": "", "topics": [1]}
        with patch("os.system", side_effect=AssertionError("Generated code must never run")) as system:
            result = self.run_flow()
        self.assertEqual(result["execution_outcome"], "completed")
        system.assert_not_called()

    def test_invalid_code_is_withheld_and_supported_prose_survives(self):
        self.draft["example"] = {"language": "python", "code": "def invalid(:\n pass", "expected_output": "", "topics": [1]}
        result = self.run_flow()
        self.assertEqual(result["execution_outcome"], "partial")
        self.assertNotIn("def invalid(:", result["answer"])
        self.assertIn(self.draft["sections"][0]["explanation"], result["answer"])

    def test_context_limit_stops_before_model_call_without_silent_truncation(self):
        model = self.model()
        with patch.dict(os.environ, {"AI_CHAT_MAX_CONVERSATION_CHARS": "4000"}):
            result = flow.answer_from_sources("Public question " * 1000, model=model, web=self.web, page_fetch=self.fetch)
        model.assert_not_called()
        self.assertIn("CONTEXT_LIMIT", result["answer"])

    def test_authentication_error_is_not_disguised_as_a_data_correction(self):
        model = Mock(side_effect=ProviderError("gemini", "AUTHENTICATION", "fixture"))
        with self.assertRaises(ProviderError): self.run_flow(model)
        self.assertEqual(model.call_count, 1)

    def test_opt_in_dispatch_does_not_send_private_context_or_touch_project_tools(self):
        model = self.model()
        tools = SimpleNamespace(root="PRIVATE_CANARY", list_files=Mock(), read_file=Mock(), search_text=Mock())
        result = answer_question({"question": self.question, "route": "web", "memory_context": "PRIVATE_CANARY",
            "summary": "PRIVATE_CANARY", "history": "PRIVATE_CANARY", "previous_exchange": {"question": "PRIVATE_CANARY"}},
            model=model, tools=tools, project_root="PRIVATE_CANARY", document_search=Mock(), web=self.web, page_fetch=self.fetch)
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertNotIn("PRIVATE_CANARY", json.dumps(model.call_args_list, default=str))
        for tool in (tools.list_files, tools.read_file, tools.search_text): tool.assert_not_called()
        names = [call.args[1][0]["function"]["name"] for call in model.call_args_list]
        self.assertEqual(names, ["submit_documentation_plan", "submit_grounded_sections", "submit_grounding_findings"])

    def test_regular_chat_and_private_sources_do_not_enter_the_new_flow(self):
        tools = SimpleNamespace(root="fixture", list_files=Mock(), read_file=Mock(), search_text=Mock())
        with patch.object(flow, "answer_from_sources", side_effect=AssertionError("No source-first dispatch")):
            result = answer_question({"question": "Hello", "route": "direct"}, model=Mock(return_value={"content": "Hello"}),
                tools=tools, project_root=".", document_search=Mock())
            self.assertEqual(result["answer"], "Hello")
            result = answer_question({"question": "Explain my uploaded project documents with official references", "route": "rag"},
                model=Mock(return_value={"content": "Need document evidence"}), tools=tools, project_root=".", document_search=Mock())
            self.assertEqual(result["task_status"], "incomplete")


    def test_public_searches_are_scoped_to_the_planned_publisher(self):
        self.run_flow()
        self.assertTrue(self.web.call_args.kwargs["query"].startswith("site:official.example.test "))


    def test_source_first_is_opt_in_until_live_acceptance_passes(self):
        with patch.dict(os.environ):
            os.environ.pop("AI_SOURCE_FIRST_DOCUMENTATION", None)
            self.assertFalse(flow.enabled())
