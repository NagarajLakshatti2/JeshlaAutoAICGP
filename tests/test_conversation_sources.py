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
