"""Native provider adapter transport checks; all HTTP calls are mocked."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from agent import tool_llm as adapter

class AdapterTests(unittest.TestCase):
    def run_request(self,provider,data,status=200,messages=None):
        response=SimpleNamespace(status_code=status,json=lambda:data)
        with patch.object(adapter,"LLM_PROVIDER",provider), patch.dict(adapter.os.environ,{"GROQ_API_KEY":"offline-fake","GROQ_MODEL":"test-model","OPENROUTER_API_KEY":"offline-fake"}), patch.object(adapter.requests,"post",return_value=response) as post:
            result=adapter.call_tool_messages(messages or [{"role":"user","content":"public test"}],[])
            return result,post.call_args.kwargs

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
            result,payload=self.run_request(provider,data)
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
