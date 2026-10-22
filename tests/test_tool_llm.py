"""Native provider adapter transport checks; all HTTP calls are mocked."""
import os
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from agent import tool_llm as adapter

class AdapterTests(unittest.TestCase):
    def run_request(self,provider,data,status=200,messages=None,specs=None):
        response=SimpleNamespace(status_code=status,json=lambda:data)
        with patch.object(adapter,"LLM_PROVIDER",provider), patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","OPENROUTER_API_KEY":"offline-fake","OPENROUTER_BUDGET_MODEL":"","GROQ_BUDGET_MODEL":""}), patch.object(adapter.requests,"post",return_value=response) as post:
            result=adapter.call_tool_messages(messages or [{"role":"user","content":"public test"}],specs or [])
            return result,post.call_args.kwargs

    def test_ollama_registered_text_tool_proposal_is_normalized(self):
        spec={"type":"function","function":{"name":"read_fact","parameters":{"type":"object"}}}
        response=SimpleNamespace(status_code=200,json=lambda:{"message":{"content":'{"name":"read_fact","arguments":{}}'}})
        with patch.object(adapter,"LLM_PROVIDER","ollama"),patch.object(adapter.requests,"post",return_value=response):
            result=adapter.call_tool_messages([{"role":"user","content":"read"}],[spec])
        self.assertEqual(result["content"],"")
        self.assertEqual(result["tool_calls"][0]["function"]["name"],"read_fact")
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"]),{})

    def test_ollama_text_fallback_does_not_execute_prose_or_results(self):
        spec=[{"function":{"name":"read_fact"}}]
        for text in ['Call {"name":"read_fact","arguments":{}}', '{"name":"read_fact","arguments":{},"result":"invented"}', 'ordinary answer']:
            self.assertIsNone(adapter.ollama_text_tool_call(text,spec))
        for text in ['{"name":"delete_file","arguments":{}}','{"name":"read_fact","arguments":[]}']:
            with self.assertRaises(adapter.ProviderError):adapter.ollama_text_tool_call(text,spec)

    def test_per_request_budget_preserves_default(self):
        response=SimpleNamespace(status_code=200,json=lambda:{"choices":[{"finish_reason":"stop","message":{"content":"done"}}]})
        with patch.object(adapter,"LLM_PROVIDER","groq"),patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","GROQ_MAX_TOKENS":"1024"}),patch.object(adapter.requests,"post",return_value=response) as post:
            adapter.call_tool_messages([{"role":"user","content":"project"}],[],max_tokens=4096)
            self.assertEqual(post.call_args.kwargs["json"]["max_completion_tokens"],4096)
            adapter.call_tool_messages([{"role":"user","content":"chat"}],[])
            self.assertEqual(post.call_args.kwargs["json"]["max_completion_tokens"],1024)
        with self.assertRaises(ValueError):adapter.call_tool_messages([],[],max_tokens=True)

    def test_connect_failure_recovers_without_actions(self):
        response=SimpleNamespace(status_code=200,json=lambda:{"choices":[{"finish_reason":"stop","message":{"content":"Recovered"}}]})
        with patch.object(adapter,"LLM_PROVIDER","groq"), patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","GROQ_CONNECT_ATTEMPTS":"2","GROQ_CONNECT_TIMEOUT":"30"}), patch.object(adapter.requests,"post",side_effect=[adapter.requests.exceptions.ConnectTimeout(),response]) as post, patch.object(adapter.time,"sleep"):
            result=adapter.call_tool_messages([{"role":"user","content":"read"}],[])
        self.assertEqual(result["content"],"Recovered")
        self.assertEqual(post.call_count,2)
        self.assertEqual(post.call_args.kwargs["timeout"][0],30)

    def test_connect_retries_are_bounded(self):
        with patch.object(adapter,"LLM_PROVIDER","groq"), patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","GROQ_CONNECT_ATTEMPTS":"2"}), patch.object(adapter.requests,"post",side_effect=adapter.requests.exceptions.ConnectionError("secret proxy address")) as post, patch.object(adapter.time,"sleep"):
            with self.assertRaisesRegex(RuntimeError,"after 2 attempt") as caught:
                adapter.call_tool_messages([{"role":"user","content":"read"}],[])
        self.assertEqual(post.call_count,2)
        self.assertNotIn("secret proxy",str(caught.exception))

    def test_response_timeout_and_tls_failure_do_not_retry(self):
        for failure in [adapter.requests.exceptions.ReadTimeout(),adapter.requests.exceptions.SSLError()]:
            with patch.object(adapter,"LLM_PROVIDER","groq"), patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model"}), patch.object(adapter.requests,"post",side_effect=failure) as post:
                with self.assertRaises(RuntimeError):adapter.call_tool_messages([{"role":"user","content":"read"}],[])
                self.assertEqual(post.call_count,1)

    def test_hosted_tool_calls_preserved(self):
        data={"choices":[{"finish_reason":"tool_calls","message":{"content":None,"tool_calls":[{"id":"tool-1","function":{"name":"web_search","arguments":'{"query":"public"}'}}]}}]}
        for provider in ["groq","openrouter"]:
            spec={"type":"function","function":{"name":"web_search","parameters":{"type":"object"}}}
            result,payload=self.run_request(provider,data,specs=[spec])
            self.assertEqual(result["tool_calls"][0]["id"],"tool-1")
            self.assertIn("tools",payload["json"])
            self.assertFalse(payload["allow_redirects"])

    def test_plain_answer(self):
        result,_=self.run_request("groq",{"choices":[{"finish_reason":"stop","message":{"content":"Answer"}}]})
        self.assertEqual(result["content"],"Answer")

    def test_ollama_argument_and_result_conversion(self):
        messages=[{"role":"assistant","content":"","tool_calls":[{"id":"id1","type":"function","function":{"name":"web_search","arguments":'{"query":"public"}'}}]},
                  {"role":"tool","tool_call_id":"id1","name":"web_search","content":"result"}]
        data={"message":{"content":"","tool_calls":[{"function":{"name":"web_search","arguments":{"query":"public"}}}]}}
        result,kwargs=self.run_request("ollama",data,messages=messages)
        self.assertIsInstance(kwargs["json"]["messages"][0]["tool_calls"][0]["function"]["arguments"],dict)
        self.assertEqual(kwargs["json"]["messages"][1]["tool_name"],"web_search")
        self.assertIsInstance(result["tool_calls"][0]["function"]["arguments"],str)

    def test_truncation_rejected(self):
        with self.assertRaises(RuntimeError):
            self.run_request("groq",{"choices":[{"finish_reason":"length","message":{"content":"partial"}}]})

    def test_quota_error(self):
        with self.assertRaisesRegex(RuntimeError,"HTTP 429"):
            self.run_request("groq",{},status=429)

    def test_duplicate_ids_rejected(self):
        call={"id":"same","function":{"name":"web_search","arguments":"{}"}}
        with self.assertRaises(RuntimeError):
            self.run_request("groq",{"choices":[{"finish_reason":"tool_calls","message":{"tool_calls":[call,call]}}]})

if __name__=="__main__": unittest.main()

class ForcedProposalTests(unittest.TestCase):
    def test_registered_groq_function_is_selected_and_parallel_disabled(self):
        spec={"type":"function","function":{"name":"submit_project_action","parameters":{"type":"object"}}}
        response=SimpleNamespace(status_code=200,json=lambda:{"choices":[{"finish_reason":"tool_calls","message":{"content":None,"tool_calls":[{"id":"one","function":{"name":"submit_project_action","arguments":"{}"}}]}}]})
        with patch.object(adapter,"LLM_PROVIDER","groq"),patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model"}),patch.object(adapter.requests,"post",return_value=response) as post:
            adapter.call_tool_messages([{"role":"user","content":"Propose"}],[spec],forced_function="submit_project_action")
        payload=post.call_args.kwargs["json"]
        self.assertEqual(payload["tool_choice"],{"type":"function","function":{"name":"submit_project_action"}})
        self.assertFalse(payload["parallel_tool_calls"])
    def test_unregistered_forcing_fails_before_network(self):
        with patch.object(adapter.requests,"post") as post:
            with self.assertRaises(ValueError):adapter.call_tool_messages([],[],forced_function="delete_project")
        post.assert_not_called()

    def test_groq_native_fallback_requires_one_tool_without_forcing_wrapper(self):
        spec={"type":"function","function":{"name":"create_file","parameters":{"type":"object"}}}
        response=SimpleNamespace(status_code=200,json=lambda:{"choices":[{"finish_reason":"tool_calls","message":{"content":None,"tool_calls":[{"id":"one","function":{"name":"create_file","arguments":"{}"}}]}}]})
        with patch.object(adapter,"LLM_PROVIDER","groq"),patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model"}),patch.object(adapter.requests,"post",return_value=response) as post:
            adapter.call_tool_messages([{"role":"user","content":"Propose"}],[spec],require_tool=True)
        self.assertEqual(post.call_args.kwargs["json"]["tool_choice"],"required")
        self.assertFalse(post.call_args.kwargs["json"]["parallel_tool_calls"])
        with self.assertRaises(ValueError):adapter.call_tool_messages([],[],require_tool=True)


class TextOnlyToolAdapterTests(unittest.TestCase):
    def test_final_answer_omits_empty_tools_and_auto_choice_for_all_providers(self):
        from agent.providers import tools as adapter
        from agent.providers.fallback import fallback_scope
        for provider in ("openrouter", "groq", "gemini", "ollama"):
            with self.subTest(provider=provider), fallback_scope(), patch.dict(os.environ, {
                "LLM_FALLBACK_ENABLED": "false", "GROQ_API_KEY": "fixture", "GROQ_MODEL": "fixture",
                "OPENROUTER_API_KEY": "fixture", "GEMINI_API_KEY": "fixture", "GEMINI_MODEL": "fixture",
                "OPENROUTER_BUDGET_MODEL": "", "GROQ_BUDGET_MODEL": "", "GEMINI_BUDGET_MODEL": ""}), \
                patch.object(adapter, "LLM_PROVIDER", provider), patch.object(adapter.requests, "post") as post:
                data = {"message": {"content": "answer"}, "done": True} if provider == "ollama" else {
                    "choices": [{"finish_reason": "stop", "message": {"content": "answer"}}]}
                post.return_value=SimpleNamespace(status_code=200, json=lambda: data)
                result=adapter.call_tool_messages([{"role": "user", "content": "Answer now"}], [])
                self.assertEqual(result["content"], "answer")
                self.assertNotIn("tools", post.call_args.kwargs["json"])
                self.assertNotIn("tool_choice", post.call_args.kwargs["json"])


class SourceDraftBudgetTests(unittest.TestCase):
    def request(self, specs, max_tokens=None):
        response = SimpleNamespace(status_code=200, json=lambda: {"choices": [{"finish_reason": "stop", "message": {"content": "data"}}]})
        with patch.object(adapter, "LLM_PROVIDER", "groq"), patch.dict(os.environ, {
                "GROQ_API_KEY": "fixture", "GROQ_MODEL": "fixture", "GROQ_MAX_TOKENS": "1024"}), \
             patch.object(adapter.requests, "post", return_value=response) as post:
            adapter.call_tool_messages([{"role": "user", "content": "Public fixture"}], specs, max_tokens=max_tokens)
        return post.call_args.kwargs["json"]["max_completion_tokens"]

    def spec(self, name):
        return {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}

    def test_source_draft_budget_does_not_change_general_chat_or_checks(self):
        with patch.dict(os.environ, {"AI_DOCUMENTATION_DRAFT_TOKENS": "4096"}):
            self.assertEqual(self.request([self.spec("submit_grounded_sections")]), 4096)
            for specs in ([], [self.spec("submit_documentation_plan")], [self.spec("submit_grounding_findings")]):
                self.assertEqual(self.request(specs), 1024)

    def test_source_draft_budget_is_configurable_and_explicit_budget_wins(self):
        with patch.dict(os.environ, {"AI_DOCUMENTATION_DRAFT_TOKENS": "2048"}):
            self.assertEqual(self.request([self.spec("submit_grounded_sections")]), 2048)
            self.assertEqual(self.request([self.spec("submit_grounded_sections")], max_tokens=128), 128)

    def test_mixed_registry_does_not_use_the_source_draft_budget(self):
        self.assertEqual(self.request([self.spec("submit_grounded_sections"), self.spec("submit_project_action")]), 1024)
