"""Read-only encoding recovery; actual transport payloads with no live HTTP."""
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.providers import tools
from agent.providers.errors import ProviderError
from agent.providers.fallback import fallback_scope
from agent.providers.read_only_json import normalize, prepare


def response(content=None, *, calls=None, status=200, reason=None):
    data = {"error": {"code": "tool_use_failed", "message": "DISCARD THIS REJECTED GENERATION"}} if status == 400 else {
        "choices": [{"finish_reason": reason or ("tool_calls" if calls else "stop"),
                     "message": {"content": content, **({"tool_calls": calls} if calls else {})}}]}
    return SimpleNamespace(status_code=status, json=lambda: data)


def proposal(name, arguments):
    return {"id": name + "-id", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


class ReadOnlyJsonTests(unittest.TestCase):
    def setUp(self):
        self.spec = {"type": "function", "function": {"name": "fetch_web_page", "parameters": {
            "type": "object", "properties": {"url": {"type": "string", "maxLength": 1500}},
            "required": ["url"], "additionalProperties": False}}}
        self.environment = patch.dict(os.environ, {"LLM_FALLBACK_ENABLED": "false", "GROQ_API_KEY": "fixture", "GROQ_MODEL": "fixture",
            "AI_DOCUMENTATION_DRAFT_TOKENS": "4096", "GROQ_MAX_TOKENS": "1024", "GROQ_BUDGET_MODEL": ""})
        self.environment.start();self.addCleanup(self.environment.stop)
        self.provider = patch.object(tools, "LLM_PROVIDER", "groq")
        self.provider.start();self.addCleanup(self.provider.stop)

    def test_completed_page_preserved_and_final_text_recovered_without_replay(self):
        messages = [{"role": "user", "content": "Explain the public source."},
                    {"role": "assistant", "content": "", "tool_calls": [proposal("fetch_web_page", {"url": "https://example.org/docs"})]},
                    {"role": "tool", "name": "fetch_web_page", "tool_call_id": "fetch_web_page-id",
                     "content": '{"url":"https://example.org/docs","text":"Already read evidence."}'}]
        before = json.dumps(messages)
        complete = json.dumps({"kind": "answer", "content": "A grounded answer."})
        with patch.object(tools.requests, "post", side_effect=[response(status=400), response(complete)]) as post:
            result = tools.call_tool_messages(messages, [self.spec])
        self.assertEqual(result, {"role": "assistant", "content": "A grounded answer."})
        self.assertEqual(post.call_count, 2)
        native, recovery = [call.kwargs["json"] for call in post.call_args_list]
        self.assertEqual(native["max_completion_tokens"], 1024)
        self.assertEqual(recovery["max_completion_tokens"], 4096)
        self.assertEqual(recovery["response_format"], {"type": "json_object"})
        for field in ("tools", "tool_choice", "parallel_tool_calls"): self.assertNotIn(field, recovery)
        self.assertTrue(all(item["role"] != "tool" and "tool_calls" not in item for item in recovery["messages"]))
        self.assertIn("Already read evidence.", json.dumps(recovery))
        self.assertNotIn("DISCARD THIS", json.dumps(recovery))
        self.assertEqual(json.dumps(messages), before)

    def test_valid_read_proposal_uses_existing_caller_validation_contract(self):
        raw = json.dumps({"kind": "tool", "name": "fetch_web_page", "arguments": {"url": "https://example.org/docs"}})
        with patch.object(tools.requests, "post", side_effect=[response(status=400), response(raw)]) as post:
            result = tools.call_tool_messages([{"role": "user", "content": "Read."}], [self.spec], max_tokens=128)
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"]), {"url": "https://example.org/docs"})
        self.assertEqual(post.call_args.kwargs["json"]["max_completion_tokens"], 128)

    def test_invalid_json_actions_extras_and_schema_mismatch_are_rejected(self):
        values = [
            {"kind": "tool", "name": "create_file", "arguments": {}},
            {"kind": "tool", "name": "fetch_web_page", "arguments": {"url": 3}},
            {"kind": "tool", "name": "fetch_web_page", "arguments": {}},
            {"kind": "tool", "name": "fetch_web_page", "arguments": {"url": "https://example.org", "command": "write"}},
            {"kind": "answer", "content": "ok", "executed": True},
            {"kind": "answer", "content": ""},
            {"kind": "tool", "name": ["fetch_web_page"], "arguments": {}},
        ]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ProviderError): normalize({"content": json.dumps(value)}, [self.spec])
        for raw in ('{"kind":"answer","content":"one","content":"two"}', '{"kind":"answer","content":NaN}', '```json\n{}\n```'):
            with self.subTest(raw=raw), self.assertRaises(ProviderError): normalize({"content": raw}, [self.spec])

    def test_recovery_is_once_and_truncated_response_is_discarded(self):
        for last in (response(status=400), response('{"kind":"answer","content":"partial"}', reason="length")):
            with self.subTest(last=last), patch.object(tools.requests, "post", side_effect=[response(status=400), last]) as post:
                with self.assertRaises(ProviderError): tools.call_tool_messages([{"role": "user", "content": "Read"}], [self.spec])
                self.assertEqual(post.call_count, 2)

    def test_truncated_json_is_not_treated_as_partial_prose(self):
        from agent.providers.selection import output_limit_passthrough
        with patch.object(tools.requests, "post", side_effect=[response(status=400), response('{"kind":"answer"', reason="length")]), output_limit_passthrough():
            with self.assertRaises(ProviderError) as caught:
                tools.call_tool_messages([{"role": "user", "content": "Read"}], [self.spec])
        self.assertEqual(caught.exception.category, "OUTPUT_LIMIT")
        self.assertTrue(caught.exception.tool_call_output)

    def test_actions_and_mixed_registry_never_use_compatibility(self):
        action = {"type": "function", "function": {"name": "submit_project_action", "parameters": {"type": "object"}}}
        for specs in ([action], [action, self.spec], []):
            with self.subTest(specs=specs), patch.object(tools.requests, "post", return_value=response(status=400)) as post:
                with self.assertRaises(ProviderError): tools.call_tool_messages([{"role": "user", "content": "Propose."}], specs)
                self.assertEqual(post.call_count, 1)

    def test_data_review_cannot_turn_into_unreviewed_answer(self):
        from agent.runtime.source_first import CHECK
        _, required = prepare([{"role": "user", "content": "Review"}], [CHECK])
        self.assertTrue(required)
        with self.assertRaises(ProviderError): normalize({"content": '{"kind":"answer","content":"Skip review"}'}, [CHECK], required=required)
        result = normalize({"content": json.dumps({"kind": "tool", "name": "submit_grounding_findings", "arguments": {"blocking": [], "advisory": []}})}, [CHECK], required=True)
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "submit_grounding_findings")
        bad = {"kind": "tool", "name": "submit_grounding_findings", "arguments": {"blocking": [], "advisory": [True]}}
        with self.assertRaises(ProviderError): normalize({"content": json.dumps(bad)}, [CHECK], required=True)

    def test_forced_proposal_and_required_tool_cannot_be_replaced_by_text(self):
        for kwargs in ({"require_tool": True}, {"forced_function": "fetch_web_page"}):
            with self.subTest(kwargs=kwargs), patch.object(tools.requests, "post", side_effect=[response(status=400), response('{"kind":"answer","content":"Skip read"}')]):
                with self.assertRaises(ProviderError): tools.call_tool_messages([{"role": "user", "content": "Read"}], [self.spec], **kwargs)

    def test_exact_documentation_flow_reaches_existing_review_without_repeating_tools(self):
        from agent.runtime.conversation import answer_question
        url = "https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.1.4"
        answer = "A class has one direct superclass. [Java 17 specification](" + url + ")."
        review = {"status": "supported", "issues": [], "source_urls": [url], "evidence": [{"claim": "A class has one direct superclass.", "source_url": url, "quote": "The direct superclass of a class is specified by its extends clause."}]}
        replies = [response(calls=[proposal("web_search", {"query": "site:docs.oracle.com Java 17 superclass"})]),
                   response(calls=[proposal("fetch_web_page", {"url": url})]), response(status=400),
                   response(json.dumps({"kind": "answer", "content": answer})),
                   response(calls=[proposal("submit_answer_review", review)])]
        web = unittest.mock.Mock(return_value={"results": [{"url": url, "title": "Java 17 specification"}]})
        page = unittest.mock.Mock(return_value={"url": url, "title": "Java 17 specification", "text": "The direct superclass of a class is specified by its extends clause.", "truncated": False})
        with patch.dict(os.environ, {"AI_TECHNICAL_VERIFICATION": "auto", "AI_SOURCE_FIRST_DOCUMENTATION": "false"}), \
             patch.object(tools.requests, "post", side_effect=replies) as post, fallback_scope():
            result = answer_question({"question": "Explain Java 17 inheritance with examples and pitfalls. Verify against official documentation.", "route": "direct"},
                model=tools.call_tool_messages, project_root=".", tools=SimpleNamespace(root="public-fixture", list_files=lambda **kwargs: self.fail("no local reads"), read_file=lambda **kwargs: self.fail("no local reads"), search_text=lambda **kwargs: self.fail("no local reads")),
                document_search=lambda **kwargs: self.fail("no private documents"), web=web, page_fetch=page)
        self.assertEqual(result.get("execution_outcome"), "completed")
        self.assertIn("one direct superclass", result["answer"])
        self.assertEqual(web.call_count, 1);self.assertEqual(page.call_count, 1)
        self.assertEqual(post.call_count, 5)
        self.assertEqual(post.call_args_list[-1].kwargs["json"]["tools"][0]["function"]["name"], "submit_answer_review")


if __name__ == "__main__": unittest.main()
