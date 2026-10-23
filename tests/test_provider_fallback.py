"""Quota-chain policy and real adapter dispatch with mocked HTTP only."""
import concurrent.futures
from contextlib import redirect_stdout
import io
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent.providers import fallback, text, tools
from agent.providers.errors import ProviderError
from agent.providers.selection import provider_selection


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "LLM_FALLBACK_ENABLED": "true", "LLM_ALLOW_LOCAL_OLLAMA": "true",
            "LLM_FALLBACK_ORDER": "openrouter,groq,gemini,ollama", "LLM_FALLBACK_ON_OUTPUT_LIMIT": "true",
            "AI_DEPLOYMENT_MODE": "local", "CI": "false", "GITHUB_ACTIONS": "false",
            "CODESPACES": "false", "STREAMLIT_SHARING_MODE": "",
            "OLLAMA_URL": "http://localhost:11434/api/chat",
            "OPENROUTER_API_KEY": "fixture", "OPENROUTER_MODEL": "fixture-or",
            "GROQ_API_KEY": "fixture", "GROQ_MODEL": "fixture-groq",
            "GEMINI_API_KEY": "fixture", "GEMINI_MODEL": "fixture-gemini",
            "OPENROUTER_BUDGET_MODEL": "", "GROQ_BUDGET_MODEL": "", "GEMINI_BUDGET_MODEL": "",
            "OLLAMA_BUDGET_MODEL": "", "OPENROUTER_CONNECT_ATTEMPTS": "1",
            "GROQ_CONNECT_ATTEMPTS": "1", "GEMINI_CONNECT_ATTEMPTS": "1"})
        self.env.start(); self.addCleanup(self.env.stop)
        self.output = redirect_stdout(io.StringIO()); self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.scope = fallback.fallback_scope(); self.notices = self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

    def quota(self, provider):
        return ProviderError(provider, "QUOTA_EXHAUSTED", "fixture", status=429)


    def test_manual_plan_read_only_tools_recover_to_gemini_without_replaying_read(self):
        import json
        from agent.runtime.conversation import TOOL_SPECS
        specs = [spec for spec in TOOL_SPECS if spec['function']['name'] in {'read_file', 'validate_test_plan'}]
        history = [{'role': 'user', 'content': 'Check the draft from the already read requirement.'},
                   {'role': 'assistant', 'tool_calls': [{'id': 'read-1', 'function': {'name': 'read_file', 'arguments': '{"relative_path":"requirements.md"}'}}]},
                   {'role': 'tool', 'tool_call_id': 'read-1', 'name': 'read_file', 'content': '{"content":"Entered text can be cleared."}'}]
        calls = []
        def invoke(provider, messages, offered, **options):
            calls.append((provider, messages, offered, options))
            if provider == 'openrouter': raise self.quota(provider)
            if provider == 'groq': raise ProviderError('groq', 'TOOL_OUTPUT', 'Rejected native or JSON fixture', status=400)
            return {'role':'assistant','tool_calls':[{'id':'check','function':{'name':'validate_test_plan','arguments':json.dumps({'plan_json':'{"cases":[]}'})}}]}
        with patch.dict(os.environ, {'LLM_FALLBACK_ORDER':'openrouter,groq,gemini'}), patch.object(tools,'LLM_PROVIDER','openrouter'), patch.object(tools,'_call_tool_provider',side_effect=invoke):
            reply = tools.call_tool_messages(history,specs,max_tokens=2048)
        self.assertEqual([row[0] for row in calls],['openrouter','groq','groq','gemini'])
        self.assertTrue(calls[2][3]['json_mode'])
        self.assertEqual(reply['tool_calls'][0]['function']['name'],'validate_test_plan')
        self.assertEqual([m for m in calls[-1][1] if m.get('role')=='tool'],[history[-1]])
        # Adapter returns data only: no handler executed and the original history is untouched.
        self.assertEqual(history[-1]['content'],'{"content":"Entered text can be cleared."}')
        self.assertFalse(tools._read_only_fallback_registry(specs+[{'type':'function','function':{'name':'create_file'}}]))
        self.assertFalse(tools._read_only_fallback_registry(specs+[{'type':'function','function':{'name':'suggest_memory'}}]))

    def test_exact_order_and_single_successful_reply(self):
        calls = []
        def invoke(provider):
            calls.append(provider)
            if provider != "ollama": raise self.quota(provider)
            return "local answer"
        self.assertEqual(fallback.call_with_fallback("openrouter", invoke), "local answer")
        self.assertEqual(calls, list(fallback.ORDER))
        self.assertEqual(fallback.last_provider("openrouter"), "ollama")

    def test_success_stops_without_contacting_next_provider(self):
        calls = []
        self.assertEqual(fallback.call_with_fallback("openrouter", lambda p: calls.append(p) or "ok"), "ok")
        self.assertEqual(calls, ["openrouter"])

    def test_manual_selection_starts_at_selected_provider(self):
        calls = []
        with provider_selection("gemini"):
            fallback.call_with_fallback("openrouter", lambda p: calls.append(p) or "ok")
        self.assertEqual(calls, ["gemini"])

    def test_non_quota_errors_never_switch(self):
        for category in ("AUTHENTICATION", "TLS_CERTIFICATE", "PROXY", "RESPONSE_TIMEOUT",
                         "TOOL_OUTPUT", "INVALID_RESPONSE", "CONTEXT_LIMIT", "BILLING"):
            with self.subTest(category=category):
                calls = []
                def invoke(p):
                    calls.append(p); raise ProviderError(p, category, "fixture")
                with self.assertRaises(ProviderError) as caught:
                    fallback.call_with_fallback("openrouter", invoke)
                self.assertEqual(caught.exception.category, category)
                self.assertEqual(calls, ["openrouter"])

    def test_rate_limit_switches_after_transport_exhaustion(self):
        def invoke(p):
            if p == "openrouter": raise ProviderError(p, "RATE_LIMIT", "fixture", status=429)
            return p
        self.assertEqual(fallback.call_with_fallback("openrouter", invoke), "groq")

    def test_disabled_preserves_original_error(self):
        with patch.dict(os.environ, {"LLM_FALLBACK_ENABLED": "false"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("openrouter", lambda p: (_ for _ in ()).throw(self.quota(p)))
        self.assertEqual(caught.exception.provider, "openrouter")

    def test_missing_secondary_credentials_are_skipped(self):
        calls = []
        def invoke(p):
            calls.append(p)
            if p == "openrouter": raise self.quota(p)
            return p
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.assertEqual(fallback.call_with_fallback("openrouter", invoke), "gemini")
        self.assertEqual(calls, ["openrouter", "gemini"])

    def test_quota_provider_is_not_retried_within_same_turn(self):
        calls = []
        def invoke(p):
            calls.append(p)
            if p == "openrouter": raise self.quota(p)
            return p
        fallback.call_with_fallback("openrouter", invoke)
        fallback.call_with_fallback("openrouter", invoke)
        self.assertEqual(calls, ["openrouter", "groq", "groq"])
        with fallback.fallback_scope():
            fallback.call_with_fallback("openrouter", invoke)
        self.assertEqual(calls[-2:], ["openrouter", "groq"])

    def test_hosted_never_contacts_ollama_even_when_allowed(self):
        for setting in ({"GITHUB_ACTIONS": "true"}, {"CI": "true"}, {"AI_DEPLOYMENT_MODE": "hosted"}):
            calls = []
            def invoke(p):
                calls.append(p); raise self.quota(p)
            with self.subTest(setting=setting), patch.dict(os.environ, setting), fallback.fallback_scope():
                with self.assertRaises(ProviderError): fallback.call_with_fallback("openrouter", invoke)
            self.assertEqual(calls, ["openrouter", "groq", "gemini"])

    def test_direct_ollama_is_rejected_in_hosted_execution(self):
        with patch.dict(os.environ, {"AI_DEPLOYMENT_MODE": "hosted", "LLM_FALLBACK_ENABLED": "false"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("ollama", lambda p: self.fail("must not contact local server"))
        self.assertEqual(caught.exception.category, "PROVIDERS_UNAVAILABLE")

    def test_local_permission_required_for_automatic_ollama(self):
        with patch.dict(os.environ, {"LLM_ALLOW_LOCAL_OLLAMA": "false"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("gemini", lambda p: (_ for _ in ()).throw(self.quota(p)))
        self.assertEqual(caught.exception.provider, "gemini")

    def test_remote_ollama_url_is_rejected_before_contact(self):
        with patch.dict(os.environ, {"OLLAMA_URL": "https://remote.example/api/chat"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("ollama", lambda p: self.fail("remote forbidden"))
        self.assertEqual(caught.exception.category, "CONFIGURATION")

    def test_scopes_do_not_leak_to_other_threads(self):
        fallback.call_with_fallback("openrouter", lambda p: "ok")
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = pool.submit(fallback.last_provider, "gemini").result()
        self.assertEqual(result, "gemini")

    def test_gemini_signatures_do_not_cross_provider_or_mutate_history(self):
        messages = [{"role": "assistant", "tool_calls": [{"function": {"name": "read", "arguments": "{}"},
                     "extra_content": {"google": {"thought_signature": "opaque"}}}]}]
        self.assertNotIn("extra_content", fallback.messages_for_provider(messages, "groq")[0]["tool_calls"][0])
        self.assertIn("extra_content", messages[0]["tool_calls"][0])
        self.assertEqual(fallback.messages_for_provider(messages, "gemini"), messages)

    @staticmethod
    def response(status, data):
        return SimpleNamespace(status_code=status, headers={}, json=lambda: data)

    def test_native_adapters_rebuild_auth_and_budget_without_executing_tools(self):
        responses = [self.response(429, {"error": {"message": "daily quota exceeded"}}),
                     self.response(200, {"choices": [{"finish_reason": "tool_calls", "message": {
                         "content": None, "tool_calls": [{"id": "fixture", "type": "function", "function": {
                             "name": "create_file", "arguments": '{"path":"review-only.txt"}'}}]}}]})]
        specs = [{"type": "function", "function": {"name": "create_file", "parameters": {"type": "object"}}}]
        with patch.object(tools, "LLM_PROVIDER", "openrouter"), patch.object(tools, "OPENROUTER_MODEL", "fixture-or"), \
             patch("requests.post", side_effect=responses) as post:
            result = tools.call_tool_messages([{"role": "user", "content": "Propose a file"}], specs, max_tokens=128)
        self.assertEqual(post.call_count, 2)
        first, second = post.call_args_list
        self.assertIn("openrouter.ai", first.args[0]); self.assertIn("api.groq.com", second.args[0])
        self.assertEqual(first.kwargs["json"]["model"], "fixture-or")
        self.assertEqual(second.kwargs["json"]["model"], "fixture-groq")
        self.assertIn("max_tokens", first.kwargs["json"])
        self.assertIn("max_completion_tokens", second.kwargs["json"])
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "create_file")
        self.assertEqual(fallback.last_provider("openrouter"), "groq")

    def test_shared_text_dispatch_falls_back_and_preserves_requested_output_budget(self):
        with patch.object(text, "LLM_PROVIDER", "openrouter"), patch.dict(text.PROVIDERS, {
            "openrouter": lambda *a, **k: (_ for _ in ()).throw(self.quota("openrouter")),
            "groq": lambda messages, **options: (messages[-1]["content"], options)}):
            answer, options = text.call_llm_messages([{"role": "user", "content": "hello"}], max_tokens=128)
        self.assertEqual(answer, "hello")
        self.assertEqual(options, {"json_mode": False, "max_tokens": 128})

    def test_groq_summary_alias_uses_actual_fallback_provider(self):
        import json
        from agent.runtime.summary_model import call_summary_messages
        data = {"facts": ["user-stated: User prefers PDF"], "decisions": [], "open_questions": []}
        def invoke(p):
            if p == "openrouter": raise self.quota(p)
            return {"tool_calls": [{"function": {"name": "functions.submit_conversation_summary",
                                                  "arguments": json.dumps(data)}}]}
        with patch.object(tools, "LLM_PROVIDER", "openrouter"), patch(
                "agent.runtime.summary_model.call_tool_messages",
                side_effect=lambda *a, **k: fallback.call_with_fallback("openrouter", invoke)):
            self.assertEqual(json.loads(call_summary_messages([])), data)

    def test_all_four_native_adapters_use_their_own_http_payload(self):
        quota = lambda: self.response(429, {"error": {"message": "daily quota exceeded"}})
        replies = [quota(), quota(), quota(), self.response(200, {
            "done": True, "done_reason": "stop", "message": {"role": "assistant", "content": "local"}})]
        with patch.object(tools, "LLM_PROVIDER", "openrouter"), patch.object(tools, "OPENROUTER_MODEL", "fixture-or"), \
             patch("requests.post", side_effect=replies) as post:
            reply = tools.call_tool_messages([{"role": "user", "content": "fixture"}], [])
        self.assertEqual(reply["content"], "local")
        calls = post.call_args_list
        self.assertEqual(len(calls), 4)
        self.assertIn("generativelanguage.googleapis.com", calls[2].args[0])
        self.assertIn("localhost", calls[3].args[0])
        self.assertNotIn("Authorization", calls[3].kwargs["headers"])
        self.assertIn("options", calls[3].kwargs["json"])
        self.assertEqual(calls[2].kwargs["json"]["model"], "fixture-gemini")

    def test_turn_returns_fallback_notice_and_archives_answer_once(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock
        from agent.runtime.turns import run_turn
        graph, catalog = Mock(), Mock()
        graph.get_state.return_value.values = {}
        def invoke(p):
            if p == "openrouter": raise self.quota(p)
            return "ok"
        def answer(*a, **k):
            return {"answer": fallback.call_with_fallback("openrouter", invoke), "route": "direct"}
        graph.invoke.side_effect = answer
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"AI_SUMMARY_THRESHOLD_CHARS": "100000"}):
            result = run_turn(graph, {"configurable": {"thread_id": "fixture"}}, catalog, "fixture", "hello", directory)
        self.assertTrue(any("using groq" in notice for notice in result["notices"]))
        self.assertEqual(graph.invoke.call_count, 1)
        self.assertEqual(catalog.append.call_count, 1)
        self.assertEqual(result["answer"], "ok")

    def test_imported_gemini_trace_marks_only_unsigned_message_without_mutation(self):
        unsigned = {"function": {"name": "read", "arguments": "{}"}}
        original = [{"role": "assistant", "tool_calls": [unsigned, unsigned.copy()]}]
        prepared = fallback.messages_for_provider(original, "gemini", imported_history=True)
        self.assertEqual(prepared[0]["tool_calls"][0]["extra_content"]["google"]["thought_signature"],
                         "skip_thought_signature_validator")
        self.assertNotIn("extra_content", prepared[0]["tool_calls"][1])
        self.assertNotIn("extra_content", original[0]["tool_calls"][0])
        signed = [{"role": "assistant", "tool_calls": [
            {"extra_content": {"google": {"thought_signature": "opaque"}}, **unsigned}, unsigned]}]
        self.assertEqual(fallback.messages_for_provider(signed, "gemini", imported_history=True), signed)

    def test_groq_project_format_correction_survives_primary_quota_switch(self):
        import json
        from agent.runtime import project_decisions
        captured = []
        def model(messages, specs, **options):
            captured.append(({item["function"]["name"] for item in specs}, options))
            def invoke(p):
                if p == "openrouter": raise self.quota(p)
                if len(captured) == 1: raise ProviderError("groq", "TOOL_OUTPUT", "fixture", status=400)
                return {"tool_calls": [{"function": {"name": "finish", "arguments": '{"answer":"reviewed"}'}}]}
            return fallback.call_with_fallback("openrouter", invoke)
        with patch.object(project_decisions, "LLM_PROVIDER", "openrouter"), \
             patch.object(project_decisions, "call_tool_messages", side_effect=model):
            answer = json.loads(project_decisions.call_project_decision([{"role": "user", "content": "fixture"}], {}))
        self.assertEqual(answer["answer"], "reviewed")
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[1][0], {"ask", "finish"})
        self.assertTrue(captured[1][1]["require_tool"])

    def test_output_limit_falls_through_hosted_chain_without_merging_drafts(self):
        import json
        original = [{"role":"user","content":"Explain the requested topic completely."}]
        snapshot = json.dumps(original)
        partial = {"choices":[{"finish_reason":"length","message":{"content":"DISCARDED PARTIAL DRAFT", "tool_calls":[{"function":{"name":"create_file","arguments":"BROKEN JSON"}}]}}]}
        complete = {"choices":[{"finish_reason":"stop","message":{"content":"One complete final answer."}}]}
        with patch.dict(os.environ,{"LLM_FALLBACK_ORDER":"openrouter,groq,gemini"}), \
             patch.object(tools,"LLM_PROVIDER","openrouter"), patch.object(tools,"OPENROUTER_MODEL","fixture-or"), \
             patch("requests.post",side_effect=[self.response(200,partial),self.response(200,partial),self.response(200,complete)]) as post:
            reply = tools.call_tool_messages(original,[],max_tokens=128)
        self.assertEqual(reply["content"],"One complete final answer.")
        self.assertNotIn("tool_calls",reply)
        self.assertEqual(post.call_count,3)
        self.assertEqual(json.dumps(original),snapshot)
        for call in post.call_args_list:
            self.assertNotIn("DISCARDED PARTIAL",json.dumps(call.kwargs["json"]["messages"]))
            self.assertEqual(call.kwargs["json"]["messages"],original)
        self.assertEqual(fallback.last_provider("openrouter"),"gemini")

    def test_all_hosted_output_limits_stop_without_a_partial_answer_or_ollama(self):
        calls=[]
        def invoke(p):
            calls.append(p)
            raise ProviderError(p,"OUTPUT_LIMIT","fixture")
        with patch.dict(os.environ,{"LLM_FALLBACK_ORDER":"openrouter,groq,gemini"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("openrouter",invoke)
        self.assertEqual(calls,["openrouter","groq","gemini"])
        self.assertEqual(caught.exception.category,"OUTPUT_LIMIT")
        self.assertIn("No complete response",str(caught.exception))
        self.assertIn("Incomplete replies were discarded",str(caught.exception))

    def test_output_failover_can_be_disabled_without_disabling_quota_failover(self):
        calls=[]
        def invoke(p):
            calls.append(p)
            raise ProviderError(p,"OUTPUT_LIMIT","fixture")
        with patch.dict(os.environ,{"LLM_FALLBACK_ON_OUTPUT_LIMIT":"false"}):
            with self.assertRaises(ProviderError): fallback.call_with_fallback("openrouter",invoke)
        self.assertEqual(calls,["openrouter"])

    def test_text_adapters_consistently_classify_truncation(self):
        for provider in fallback.ORDER:
            with self.subTest(provider=provider), patch.object(text,"OPENROUTER_API_KEY","fixture"), \
                 patch.object(text,"OPENROUTER_MODEL","fixture-or"), patch("requests.post") as post:
                data = {"done_reason":"length","message":{"content":"DISCARDED"}} if provider=="ollama" else {
                    "choices":[{"finish_reason":"length","message":{"content":"DISCARDED"}}]}
                post.return_value=self.response(200,data)
                with self.assertRaises(ProviderError) as caught: text.PROVIDERS[provider]("fixture",max_tokens=128)
                self.assertEqual(caught.exception.category,"OUTPUT_LIMIT")

    def test_public_text_dispatch_never_publishes_truncated_text(self):
        partial=self.response(200,{"choices":[{"finish_reason":"length","message":{"content":"DISCARDED"}}]})
        complete=self.response(200,{"choices":[{"finish_reason":"stop","message":{"content":"FINAL ONLY"}}]})
        with patch.object(text,"LLM_PROVIDER","openrouter"), patch.object(text,"OPENROUTER_API_KEY","fixture"), \
             patch.object(text,"OPENROUTER_MODEL","fixture-or"), patch("requests.post",side_effect=[partial,complete]) as post:
            answer=text.call_llm_messages([{"role":"user","content":"fixture"}],max_tokens=128)
        self.assertEqual(answer,"FINAL ONLY")
        self.assertEqual(post.call_count,2)

    def test_partial_tool_proposal_never_becomes_the_successful_proposal(self):
        partial=self.response(200,{"choices":[{"finish_reason":"length","message":{"content":"","tool_calls":[
            {"id":"partial","function":{"name":"create_file","arguments":"{"}}]}}]})
        complete=self.response(200,{"choices":[{"finish_reason":"tool_calls","message":{"content":"","tool_calls":[
            {"id":"complete","type":"function","function":{"name":"submit_project_action","arguments":'{"action":"ask","question":"Which file?"}'}}]}}]})
        spec=[{"type":"function","function":{"name":"submit_project_action","parameters":{"type":"object"}}}]
        with patch.object(tools,"LLM_PROVIDER","openrouter"),patch.object(tools,"OPENROUTER_MODEL","fixture-or"), \
             patch("requests.post",side_effect=[partial,complete]):
            reply=tools.call_tool_messages([{"role":"user","content":"fixture"}],spec)
        self.assertEqual([call["id"] for call in reply["tool_calls"]],["complete"])
        self.assertEqual(reply["tool_calls"][0]["function"]["name"],"submit_project_action")

    def test_manual_local_selection_survives_a_hosted_only_fallback_order(self):
        with patch.dict(os.environ,{"LLM_FALLBACK_ORDER":"openrouter,groq,gemini"}),provider_selection("ollama"):
            self.assertEqual(fallback.call_with_fallback("openrouter",lambda p:p),"ollama")

    def test_invalid_order_is_rejected_before_requests(self):
        with patch.dict(os.environ,{"LLM_FALLBACK_ORDER":"groq,openrouter,gemini"}):
            with self.assertRaises(ProviderError):fallback.call_with_fallback("openrouter",lambda p:self.fail("invalid order"))

    def test_output_limit_switch_persists_exactly_one_final_answer(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock
        from agent.runtime.turns import run_turn
        graph,catalog=Mock(),Mock();graph.get_state.return_value.values={}
        providers=[]
        def invoke(p):
            providers.append(p)
            if p=="openrouter":raise ProviderError(p,"OUTPUT_LIMIT","fixture")
            return "Only the completed final answer."
        graph.invoke.side_effect=lambda *a,**k:{"answer":fallback.call_with_fallback("openrouter",invoke),"route":"direct"}
        with TemporaryDirectory() as directory,patch.dict(os.environ,{"AI_SUMMARY_THRESHOLD_CHARS":"100000"}):
            result=run_turn(graph,{"configurable":{"thread_id":"fixture"}},catalog,"fixture","Question",directory)
        self.assertEqual(providers,["openrouter","groq"])
        self.assertEqual(graph.invoke.call_count,1)
        catalog.append.assert_called_once_with("fixture","Question","Only the completed final answer.")
        self.assertEqual(result["history"].count("Assistant:"),1)
        self.assertEqual(result["answer"],"Only the completed final answer.")


    def test_read_only_format_failure_switches_without_repeating_completed_reads(self):
        import json
        specs = [{"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}
                 for name in ("web_search", "fetch_web_page")]
        messages = [{"role": "user", "content": "Explain this public documentation."},
                    {"role": "assistant", "tool_calls": [{"id": "read", "type": "function", "function": {
                        "name": "fetch_web_page", "arguments": '{"url":"https://example.org/docs"}'}}]},
                    {"role": "tool", "tool_call_id": "read", "name": "fetch_web_page",
                     "content": '{"url":"https://example.org/docs","text":"Already retrieved evidence."}'}]
        before = json.dumps(messages)
        quota = self.response(429, {"error": {"message": "daily quota exceeded"}})
        rejected = self.response(400, {"error": {"code": "tool_use_failed", "message": "DISCARDED INVALID DRAFT"}})
        complete = self.response(200, {"choices": [{"finish_reason": "stop", "message": {"content": "Final only."}}]})
        with patch.dict(os.environ, {"LLM_FALLBACK_ORDER": "openrouter,groq,gemini"}), \
             patch.object(tools, "LLM_PROVIDER", "openrouter"), patch.object(tools, "OPENROUTER_MODEL", "fixture-or"), \
             patch("requests.post", side_effect=[quota, rejected, rejected, complete, complete]) as post:
            reply = tools.call_tool_messages(messages, specs, max_tokens=128)
            next_reply = tools.call_tool_messages(messages, specs, max_tokens=128)
        self.assertEqual(reply, {"role": "assistant", "content": "Final only."})
        self.assertEqual(next_reply, reply)
        hosts = [call.args[0] for call in post.call_args_list]
        self.assertIn("openrouter.ai", hosts[0])
        self.assertIn("api.groq.com", hosts[1])
        self.assertTrue(all("generativelanguage.googleapis.com" in host for host in hosts[3:]))
        self.assertEqual(json.dumps(messages), before)
        for call in post.call_args_list:
            payload = call.kwargs["json"]
            self.assertIn("Already retrieved evidence.", json.dumps(payload["messages"]))
            self.assertNotIn("DISCARDED INVALID DRAFT", json.dumps(payload))
            if payload.get("response_format"):
                self.assertNotIn("tools", payload)
                self.assertIn("untrusted_tool_result", json.dumps(payload["messages"]))
            else:
                self.assertEqual(payload["tools"], specs)
        self.assertEqual(fallback.last_provider("openrouter"), "gemini")
        self.assertTrue(any("rejected read-only tool output" in notice for notice in self.notices))

    def test_review_data_function_is_eligible_for_format_failover(self):
        import json
        spec = [{"type": "function", "function": {"name": "submit_answer_review", "parameters": {"type": "object"}}}]
        data = {"status": "revise", "issues": ["Claim lacks evidence."], "source_urls": []}
        replies = [self.response(400, {"error": {"code": "json_validate_failed"}}),
                   self.response(400, {"error": {"code": "json_validate_failed"}}),
                   self.response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{
                       "id": "review", "function": {"name": "submit_answer_review", "arguments": json.dumps(data)}}]}}]})]
        with patch.object(tools, "LLM_PROVIDER", "groq"), patch("requests.post", side_effect=replies) as post:
            reply = tools.call_tool_messages([{"role": "user", "content": "Review public evidence."}], spec)
        self.assertEqual(json.loads(reply["tool_calls"][0]["function"]["arguments"]), data)
        self.assertEqual(post.call_count, 3)
        self.assertIn("api.groq.com", post.call_args_list[0].args[0])
        self.assertIn("api.groq.com", post.call_args_list[1].args[0])
        self.assertIn("generativelanguage.googleapis.com", post.call_args_list[2].args[0])

    def test_action_mixed_and_empty_registries_do_not_format_failover(self):
        safe = {"type": "function", "function": {"name": "web_search", "parameters": {"type": "object"}}}
        for name in ("create_file", "submit_project_action", "submit_conversation_summary", "unknown_tool"):
            action = {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}
            for specs in ([action], [safe, action]):
                with self.subTest(names=[item["function"]["name"] for item in specs]), fallback.fallback_scope(), \
                     patch.object(tools, "LLM_PROVIDER", "groq"), patch("requests.post", return_value=self.response(
                         400, {"error": {"code": "tool_use_failed"}})) as post:
                    with self.assertRaises(ProviderError) as caught:
                        tools.call_tool_messages([{"role": "user", "content": "Fixture"}], specs)
                    self.assertEqual(caught.exception.category, "TOOL_OUTPUT")
                    self.assertEqual(post.call_count, 1)
        with patch.object(tools, "LLM_PROVIDER", "groq"), patch("requests.post", return_value=self.response(
                400, {"error": {"code": "tool_use_failed"}})) as post:
            with self.assertRaises(ProviderError): tools.call_tool_messages([], [])
        self.assertEqual(post.call_count, 1)

    def test_disabled_fallback_still_bounds_read_only_encoding_recovery(self):
        specs = [{"type": "function", "function": {"name": "fetch_web_page", "parameters": {"type": "object"}}}]
        with patch.dict(os.environ, {"LLM_FALLBACK_ENABLED": "false"}), \
             patch.object(tools, "LLM_PROVIDER", "groq"), patch("requests.post", return_value=self.response(
                 400, {"error": {"code": "tool_use_failed"}})) as post:
            with self.assertRaises(ProviderError) as caught: tools.call_tool_messages([], specs)
        self.assertEqual(caught.exception.category, "TOOL_OUTPUT")
        self.assertEqual(post.call_count, 2)

    def test_read_only_format_opt_in_does_not_hide_other_errors(self):
        for category in ("AUTHENTICATION", "TLS_CERTIFICATE", "CONFIGURATION", "INVALID_REQUEST", "ANSWER_REVIEW_FORMAT"):
            calls = []
            def invoke(provider):
                calls.append(provider)
                raise ProviderError(provider, category, "fixture")
            with self.subTest(category=category), fallback.fallback_scope():
                with self.assertRaises(ProviderError) as caught:
                    fallback.call_with_fallback("groq", invoke, allow_tool_output_fallback=True)
                self.assertEqual(caught.exception.category, category)
                self.assertEqual(calls, ["groq"])

    def test_all_format_failures_stop_once_per_eligible_provider(self):
        calls = []
        def invoke(provider):
            calls.append(provider)
            raise ProviderError(provider, "TOOL_OUTPUT", "fixture", status=400)
        with patch.dict(os.environ, {"LLM_FALLBACK_ORDER": "openrouter,groq,gemini"}):
            with self.assertRaises(ProviderError) as caught:
                fallback.call_with_fallback("openrouter", invoke, allow_tool_output_fallback=True)
        self.assertEqual(calls, ["openrouter", "groq", "gemini"])
        self.assertEqual(caught.exception.category, "TOOL_OUTPUT")
        self.assertIn("tool-format compatibility", str(caught.exception))
        for name in calls: self.assertIn(name + " (TOOL_OUTPUT)", str(caught.exception))

    def test_read_only_format_failure_does_not_disable_provider_next_turn(self):
        calls = []
        def invoke(provider):
            calls.append(provider)
            if provider == "groq": raise ProviderError(provider, "TOOL_OUTPUT", "fixture", status=400)
            return "done"
        for _ in range(2):
            with fallback.fallback_scope():
                self.assertEqual(fallback.call_with_fallback("groq", invoke, allow_tool_output_fallback=True), "done")
        self.assertEqual(calls, ["groq", "gemini", "groq", "gemini"])

    def test_malformed_registry_cannot_opt_in(self):
        for specs in (None, [], {}, [None], [{"type": "custom", "function": {"name": "web_search"}}],
                      [{"type": "function", "function": "web_search"}],
                      [{"type": "function", "function": {"name": ["web_search"]}}]):
            with self.subTest(specs=specs): self.assertFalse(tools._read_only_fallback_registry(specs))


    def test_source_first_data_functions_failover_without_executing_tools(self):
        for name in ("submit_documentation_plan", "submit_grounded_sections", "submit_grounding_findings"):
            specs = [{"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}]
            rejected = self.response(400, {"error": {"code": "tool_use_failed"}})
            valid = self.response(200, {"choices": [{"finish_reason": "tool_calls", "message": {"tool_calls": [{
                "id": "data", "function": {"name": name, "arguments": "{}"}}]}}]})
            with self.subTest(name=name), fallback.fallback_scope(), patch.object(tools, "LLM_PROVIDER", "groq"), \
                 patch("requests.post", side_effect=[rejected, rejected, valid]) as post:
                reply = tools.call_tool_messages([{"role": "user", "content": "Public fixture"}], specs)
                self.assertEqual(reply["tool_calls"][0]["function"]["name"], name)
                self.assertEqual(post.call_count, 3)
                self.assertIn("generativelanguage.googleapis.com", post.call_args.args[0])
