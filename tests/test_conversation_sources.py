"""Offline conversation-loop regression tests: no model or external requests."""
import json
import unittest
from types import SimpleNamespace
from agent.conversation import answer_question


class ConversationTests(unittest.TestCase):
    def run_answer(self, decisions, state=None, web=None, documents=None):
        calls = []
        choices = iter(decisions)
        def model(messages, tools):
            calls.append([dict(m) for m in messages])
            decision=next(choices)
            if decision.get("action") in {"finish","ask"}:
                return {"role":"assistant","content":decision.get("answer") or decision.get("question")}
            return {"role":"assistant","content":"", "tool_calls":[{
                "id":f"call_{len(calls)}", "type":"function", "function":{
                    "name":decision["action"], "arguments":json.dumps(decision.get("arguments",{}))}}]}
        tools = SimpleNamespace(root="local-project", list_files=lambda **k: {"files": []},
                                read_file=lambda **k: {"content": "source"},
                                search_text=lambda **k: {"matches": []})
        result = answer_question(state or {"question": "What is my project?", "route": "direct",
                                           "memory_context": "project_name: JeshlaAutoAI"},
                                 model=model, project_root=".", document_search=documents or (lambda query: "document evidence"),
                                 web=web or (lambda query: {"results": []}), tools=tools)
        return result, calls

    def test_large_task_is_rejected_without_model_or_silent_truncation(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{"AI_CHAT_MAX_CONVERSATION_CHARS":"4000"}):
            result,calls=self.run_answer([],state={"question":"Exact task "*2000,"route":"direct"})
        self.assertEqual(calls,[])
        self.assertEqual(result["task_status"],"incomplete")
        self.assertIn("context budget",result["answer"])

    def test_memory_reaches_model(self):
        result, calls = self.run_answer([{"action":"finish", "answer":"JeshlaAutoAI"}])
        self.assertIn("JeshlaAutoAI", calls[0][1]["content"])
        self.assertEqual(result["answer"], "JeshlaAutoAI")

    def test_web_requires_real_search(self):
        searched=[]
        result, calls = self.run_answer([
            {"action":"finish", "answer":"unverified"},
            {"action":"web_search", "arguments":{"query":"public release"}},
            {"action":"finish", "answer":"According to the search snippet: [source](https://example.com)"},
        ], state={"question":"Latest release?", "route":"web"},
           web=lambda query: searched.append(query) or {"results":[{"url":"https://example.com", "snippet":"release"}]})
        self.assertEqual(searched,["public release"])
        self.assertNotEqual(result["answer"],"unverified")

    def test_mixed_sources(self):
        result,calls=self.run_answer([
            {"action":"search_documents", "arguments":{"query":"project tools"}},
            {"action":"web_search", "arguments":{"query":"public tool documentation"}},
            {"action":"finish", "answer":"Combined answer"},
        ])
        self.assertIn("document evidence",str(calls[-1]))
        self.assertEqual(result["answer"],"Combined answer")

    def test_write_action_rejected(self):
        result,calls=self.run_answer([
            {"action":"run_command", "arguments":{"command":"anything"}},
            {"action":"ask", "question":"Which existing file should I inspect?"},
        ])
        self.assertIn("Invalid tool name or arguments",str(calls[-1]))
        self.assertIn("Which",result["answer"])

    def test_failure_visible_to_model(self):
        result,calls=self.run_answer([
            {"action":"web_search", "arguments":{"query":"public query"}},
            {"action":"finish", "answer":"Search failed; please retry."},
        ],web=lambda query:{"error":"search unavailable"})
        self.assertIn("search unavailable",str(calls[-1]))

    def test_repeated_search_not_executed(self):
        queries=[]
        result,_=self.run_answer([
            {"action":"web_search", "arguments":{"query":"same"}},
            {"action":"web_search", "arguments":{"query":"same"}},
            {"action":"finish", "answer":"No further evidence"},
        ],web=lambda query:queries.append(query) or {"results":[]})
        self.assertEqual(queries,["same"])

    def test_rag_retrieved_before_answer(self):
        result,calls=self.run_answer([
            {"action":"search_documents","arguments":{"query":"My indexed document"}},
            {"action":"finish","answer":"Document answer"},
        ],state={"question":"My indexed document?","route":"rag"})
        self.assertIn("document evidence",str(calls[-1]))
        self.assertEqual(calls[-1][-1]["role"],"tool")
        self.assertEqual(calls[-1][-1]["tool_call_id"],"call_1")

    def test_invalid_arguments_do_not_execute(self):
        queried=[]
        result,calls=self.run_answer([
            {"action":"web_search","arguments":{"query":"test","extra":"invalid"}},
            {"action":"finish","answer":"Need clarification"},
        ],web=lambda query:queried.append(query))
        self.assertEqual(queried,[])
        self.assertIn("Invalid tool name",str(calls[-1]))



if __name__ == "__main__":
    unittest.main()


class ConversationFinalizationTests(unittest.TestCase):
    def tools(self):
        from unittest.mock import Mock
        return SimpleNamespace(root="fixture", list_files=Mock(return_value={"files": []}),
                               read_file=Mock(), search_text=Mock())

    def run_question(self, model, state=None, tools=None):
        return answer_question(state or {"question": "can list all inheritance points without missing anything", "route": "direct",
            "history": "User: Explain Java inheritance.\nAssistant: Java uses extends for class inheritance."},
            model=model, project_root=".", tools=tools or self.tools(), document_search=lambda **k: {"sources": []})

    @staticmethod
    def repeated_call(index):
        return {"role": "assistant", "content": "", "tool_calls": [{"id": "repeat-"+str(index), "type": "function",
            "function": {"name": "list_files", "arguments": "{}"}}]}

    def test_general_followup_preserves_subject_and_can_answer_without_tools(self):
        seen=[]
        def model(messages, tools):
            seen.extend(messages)
            self.assertEqual(tools, [])
            return {"content": "Java inheritance: extends, implements, overriding and access rules."}
        result=self.run_question(model)
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertIn("Java inheritance", json.dumps(json.loads(seen[1]["content"])["previous_exchange"]))
        self.assertIn("comprehensive coverage does not itself require tools", seen[0]["content"])

    def test_last_step_is_reserved_for_answer_without_replaying_tools(self):
        requests=[]; tools=self.tools()
        def model(messages, specs):
            requests.append((list(messages), specs))
            if specs: return self.repeated_call(len(requests))
            return {"content": "Java inheritance checklist: superclass, subclass, overriding, constructors, access and interfaces."}
        result=self.run_question(model, state={"question":"List the project folders", "route":"direct"}, tools=tools)
        self.assertEqual(result["execution_outcome"], "completed")
        self.assertEqual(len(requests), 6)
        self.assertEqual(requests[-1][1], [])
        tools.list_files.assert_called_once()
        self.assertIn("final response step", requests[-1][0][-1]["content"])

    def test_source_required_task_cannot_claim_success_without_retrieval(self):
        count=[]
        def model(messages, specs):
            count.append(specs)
            return {"content": "An unsupported source-specific answer"}
        result=self.run_question(model, state={"question": "Search my indexed documents", "route": "rag"})
        self.assertEqual(result["task_status"], "incomplete")
        self.assertNotEqual(result["answer"], "An unsupported source-specific answer")
        self.assertEqual(len(count), 6)

    def test_final_step_never_executes_an_unexpected_tool_call(self):
        count=[]; tools=self.tools()
        def model(messages, specs):
            count.append(specs)
            if specs: return {"content": "Need source evidence first"}
            return self.repeated_call(len(count))
        result=self.run_question(model, state={"question": "Search online", "route": "web"}, tools=tools)
        self.assertEqual(result["task_status"], "incomplete")
        self.assertEqual(count[-1], [])
        tools.list_files.assert_not_called()


class KnowledgeScopeTests(unittest.TestCase):
    def test_teaching_topics_are_not_fixed_answers_or_language_specific(self):
        from agent.policies.knowledge import knowledge_only
        for question in ("Explain SQL joins", "What is photosynthesis?", "List all inheritance points", "Define polymorphism"):
            with self.subTest(question=question): self.assertTrue(knowledge_only({"route":"direct"},question))

    def test_sources_history_upload_and_required_routes_keep_tools(self):
        from agent.policies.knowledge import knowledge_only
        for question in ("Explain inheritance in my project", "List all points from attached documents", "Explain the latest Java changes", "What is my preferred format?", "Explain src/Animal.java", "Explain inheritance with official references", "Explain inheritance and cite documentation"):
            with self.subTest(question=question): self.assertFalse(knowledge_only({"route":"direct"},question))
        self.assertFalse(knowledge_only({"route":"direct","history":"User: Inspect the repository."},"Explain those concepts"))
        self.assertFalse(knowledge_only({"route":"web"},"Explain inheritance"))
        self.assertFalse(knowledge_only({"route":"direct"},"Explain inheritance",has_upload=True))

    def test_general_scope_does_not_execute_unregistered_model_requests(self):
        from unittest.mock import Mock
        tools=SimpleNamespace(root="fixture",list_files=Mock(),read_file=Mock(),search_text=Mock())
        result=answer_question({"question":"Explain a concept", "route":"direct"},
            model=lambda *args:ConversationFinalizationTests.repeated_call(1),project_root=".",tools=tools,document_search=lambda **k:None)
        self.assertEqual(result["execution_outcome"],"blocked")
        tools.list_files.assert_not_called()


class KnowledgeRetryTests(unittest.TestCase):
    def test_assistant_source_error_does_not_turn_retry_into_a_source_task(self):
        from agent.policies.knowledge import knowledge_only
        state={"route":"direct", "history":"User: Explain inheritance.\nAssistant: Java supports class inheritance.\nUser: List all inheritance points.\nAssistant: I reached the model/tool step limit. Please specify the source."}
        self.assertTrue(knowledge_only(state,"List all inheritance points"))


class GeneralRequestInterpretationTests(unittest.TestCase):
    def test_instruction_keeps_current_format_with_no_fixed_response_mode(self):
        captured=[]
        def model(messages, specs):
            captured.extend(messages)
            return {"content":"An explanation with the requested examples."}
        tools=SimpleNamespace(root="fixture",list_files=lambda **k:None,read_file=lambda **k:None,search_text=lambda **k:None)
        result=answer_question({"question":"Explain with examples","history":"User: Give a short list.\nAssistant: Earlier list.","route":"direct"},
            model=model,tools=tools,project_root=".",document_search=lambda **k:None)
        self.assertEqual(result["execution_outcome"],"completed")
        self.assertIn("latest request's intended topic, output format and level of detail",captured[0]["content"])
        self.assertFalse(any("POINTS ONLY" in message["content"] for message in captured))
        self.assertIn("examples",result["answer"])

    def test_completeness_request_does_not_become_a_canned_answer(self):
        from unittest.mock import Mock
        model=Mock(return_value={"content":"- Topic A\n- Topic B"})
        tools=SimpleNamespace(root="fixture",list_files=lambda **k:None,read_file=lambda **k:None,search_text=lambda **k:None)
        result=answer_question({"question":"List all learning topics","route":"direct"},model=model,tools=tools,
            project_root=".",document_search=lambda **k:None)
        model.assert_called_once()
        self.assertEqual(result["answer"],"- Topic A\n- Topic B")


class CompleteFollowupContextTests(unittest.TestCase):
    run_answer = ConversationTests.run_answer
    def test_long_previous_answer_is_not_cut_to_last_topics(self):
        answer = "\n".join("### Topic " + str(i) + "\n" + "Explanation. " * 65 for i in range(1, 11))
        history = "\nUser: Explain the topic.\nAssistant: " + answer
        result, calls = self.run_answer([{"action": "finish", "answer": "All requested topic names."}],
            state={"question": "Now give only the topic names from that explanation.", "route": "direct", "history": history})
        payload = json.loads(calls[0][1]["content"])
        self.assertEqual(payload["previous_exchange"]["answer"], answer)
        self.assertIn("### Topic 1\n", payload["previous_exchange"]["answer"])
        self.assertEqual(payload["recent_conversation"], "")
        self.assertEqual(result["execution_outcome"], "completed")

    def test_structured_exchange_survives_a_capped_checkpoint_history(self):
        answer = "BEGINNING_MARKER\n" + "body " * 3500 + "\nENDING_MARKER"
        result, calls = self.run_answer([{"action": "finish", "answer": "Reformatted response."}],
            state={"question": "Reformat your answer.", "route": "direct",
                   "history": ("\nUser: Long question\nAssistant: " + answer)[-16000:],
                   "previous_exchange": {"question": "Long question", "answer": answer}})
        payload = json.loads(calls[0][1]["content"])
        self.assertEqual(payload["previous_exchange"]["answer"], answer)
        self.assertEqual(payload["recent_conversation"], "")
        self.assertEqual(result["execution_outcome"], "completed")

    def test_oversized_previous_exchange_is_rejected_without_silent_partial_context(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"AI_CHAT_MAX_CONVERSATION_CHARS": "12000"}):
            result, calls = self.run_answer([], state={"question": "Summarize your answer.", "route": "direct",
                "previous_exchange": {"question": "Long question", "answer": "large answer " * 4000}})
        self.assertEqual(calls, [])
        self.assertEqual(result["task_status"], "incomplete")
        self.assertIn("context budget", result["answer"])


class FollowupSourceScopeTests(unittest.TestCase):
    def test_source_request_is_retained_when_checkpoint_only_contains_answer_tail(self):
        from agent.policies.knowledge import knowledge_only
        state={"route":"direct", "history":"explanation "*1500,
            "previous_exchange":{"question":"Explain the indexed documents", "answer":"explanation "*1500}}
        self.assertFalse(knowledge_only(state,"List the topics from that explanation"))
