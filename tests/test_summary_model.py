import json
import unittest
from unittest.mock import patch
from agent.summary_model import call_summary_messages
from agent.context_summary import summary_failure_reason
from agent.provider_errors import ProviderError


DATA={"facts":["User corrected the project name"],"decisions":[],"open_questions":["Which report?"]}


def native(data,name="submit_conversation_summary"):
    return {"tool_calls":[{"id":"summary-1","function":{"name":name,"arguments":json.dumps(data)}}]}


class SummaryModelTests(unittest.TestCase):
    def test_native_summary_returns_validated_data(self):
        with patch("agent.summary_model.call_tool_messages",return_value=native(DATA)) as model:
            self.assertEqual(json.loads(call_summary_messages([{"role":"user","content":"old history"}])),DATA)
        self.assertEqual(model.call_args.args[1][0]["function"]["name"],"submit_conversation_summary")
        self.assertEqual(model.call_args.kwargs["max_tokens"],4096)

    def test_plain_summary_json_remains_compatible(self):
        with patch("agent.summary_model.call_tool_messages",return_value={"content":json.dumps(DATA)}):
            self.assertEqual(json.loads(call_summary_messages([])),DATA)

    def test_invalid_summary_gets_one_correction(self):
        with patch("agent.summary_model.call_tool_messages",side_effect=[native({"facts":"wrong"}),native(DATA)]) as model:
            self.assertEqual(json.loads(call_summary_messages([])),DATA)
            self.assertEqual(model.call_count,2)

    def test_historical_action_is_not_a_summary(self):
        with patch("agent.summary_model.call_tool_messages",return_value=native({"action":"create_file"},name="create_file")) as model:
            with self.assertRaises(ValueError):call_summary_messages([])
            self.assertEqual(model.call_count,2)

    def test_provider_diagnostic_is_category_based(self):
        error=ProviderError("groq","TOOL_OUTPUT","private failed generation")
        self.assertEqual(summary_failure_reason(error),"provider rejected summary format")
        self.assertNotIn("private",summary_failure_reason(error))

    def test_provider_format_rejection_gets_one_changed_request(self):
        error=ProviderError("groq","TOOL_OUTPUT","safe",status=400)
        with patch("agent.summary_model.call_tool_messages",side_effect=[error,native(DATA)]) as model:
            self.assertEqual(json.loads(call_summary_messages([])),DATA)
            self.assertEqual(model.call_count,2)
            self.assertNotEqual(model.call_args_list[0].args[0],model.call_args_list[1].args[0])

    def test_repeated_provider_format_rejection_is_bounded(self):
        error=ProviderError("groq","TOOL_OUTPUT","safe",status=400)
        with patch("agent.summary_model.call_tool_messages",side_effect=error) as model:
            with self.assertRaises(ProviderError):call_summary_messages([])
            self.assertEqual(model.call_count,2)

    def test_quota_error_does_not_get_format_retry(self):
        error=ProviderError("groq","QUOTA_EXHAUSTED","safe",status=429)
        with patch("agent.summary_model.call_tool_messages",side_effect=error) as model:
            with self.assertRaises(ProviderError):call_summary_messages([])
            self.assertEqual(model.call_count,1)
