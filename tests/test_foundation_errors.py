import io
from contextlib import redirect_stdout
import os
import unittest
from unittest.mock import patch
from agent import llm_client,tool_llm
from agent.provider_errors import ProviderError
from agent.user_errors import print_agent_error,user_error_message


class FoundationErrorTests(unittest.TestCase):
    def test_missing_hosted_keys_fail_before_network(self):
        for provider in ["groq","openrouter"]:
            with patch.object(tool_llm,"LLM_PROVIDER",provider),patch.dict(os.environ,{provider.upper()+"_API_KEY":""}),patch("requests.post") as post:
                with self.assertRaises(ProviderError) as caught:tool_llm.call_tool_messages([{"role":"user","content":"hello"}],[])
                self.assertIn(provider.upper()+"_API_KEY",user_error_message(caught.exception))
                post.assert_not_called()

    def test_bad_numeric_config_does_not_echo_value(self):
        with patch.dict(os.environ,{"GROQ_TIMEOUT":"secret-private-token"}):
            with self.assertRaises(ProviderError) as caught:llm_client.env_int("GROQ_TIMEOUT",90,10,600)
        self.assertIn("GROQ_TIMEOUT",str(caught.exception))
        self.assertNotIn("secret-private-token",str(caught.exception))

    def test_unknown_provider_does_not_echo_value(self):
        with patch.object(llm_client,"LLM_PROVIDER","secret-private-token"):
            with self.assertRaises(ProviderError) as caught:llm_client.call_llm_messages([{"role":"user","content":"hello"}])
        self.assertIn("LLM_PROVIDER",str(caught.exception))
        self.assertNotIn("secret-private-token",str(caught.exception))

    def test_console_shows_actionable_safe_provider_error(self):
        error=ProviderError("groq","CONFIGURATION","Set GROQ_MODEL locally and restart.",attempts=0)
        output=io.StringIO()
        with redirect_stdout(output):print_agent_error(error)
        self.assertIn("GROQ_MODEL",output.getvalue())
        self.assertIn("No success is claimed",output.getvalue())

    def test_unknown_exception_text_is_hidden_in_both_presentations(self):
        error=RuntimeError("secret-private-token")
        self.assertNotIn("secret-private-token",user_error_message(error))
        output=io.StringIO()
        with redirect_stdout(output):print_agent_error(error)
        self.assertNotIn("secret-private-token",output.getvalue())

    def test_console_provider_failure_matrix(self):
        for provider in ("groq","openrouter","ollama","gemini"):
            for category in ("AUTHENTICATION","RATE_LIMIT","QUOTA_EXHAUSTED","RESPONSE_TIMEOUT","TOOL_OUTPUT","OUTPUT_LIMIT"):
                with self.subTest(provider=provider,category=category):
                    output=io.StringIO()
                    with redirect_stdout(output):
                        print_agent_error(ProviderError(provider,category,"Safe recovery instruction."))
                    text=output.getvalue()
                    self.assertIn(provider.upper(),text)
                    self.assertIn(category,text)
                    self.assertIn("No success is claimed",text)
