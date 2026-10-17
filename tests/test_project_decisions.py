"""Native proposals remain separate from project action execution."""
import json
import unittest
from unittest.mock import patch
from agent.project_decisions import call_project_decision


def reply(decision, name="submit_project_action"):
    return {"role":"assistant","content":"","tool_calls":[{
        "id":"proposal-1","function":{"name":name,"arguments":json.dumps(decision)}}]}


class ProjectDecisionTests(unittest.TestCase):
    def test_native_function_is_registered(self):
        decision={"action":"read_file","arguments":{"relative_path":"build.gradle"}}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)) as model:
            self.assertEqual(json.loads(call_project_decision([{"role":"user","content":"Read build.gradle"}],{"read_file":object()})),decision)
        self.assertEqual(model.call_args.kwargs["max_tokens"],4096)
        messages,specs=model.call_args.args
        self.assertEqual(specs[0]["function"]["name"],"submit_project_action")
        self.assertEqual(specs[0]["function"]["parameters"]["properties"]["action"]["enum"],["ask","finish","read_file"])

    def test_unknown_and_unavailable_actions_rejected(self):
        for decision in [{"action":"delete_file"},{"action":"create_file"},{"action":"read_file","result":"invented"},{"action":"read_file","arguments":[]}]:
            with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)):
                with self.assertRaises(RuntimeError):call_project_decision([{"role":"user","content":"read"}],{"read_file":object()})

    def test_unregistered_function_and_multiple_calls_rejected(self):
        for output in [reply({"action":"read_file"},name="read_file"),{"tool_calls":reply({"action":"ask"})["tool_calls"]*2}]:
            with patch("agent.project_decisions.call_tool_messages",return_value=output):
                with self.assertRaises(RuntimeError):call_project_decision([{"role":"user","content":"read"}],{"read_file":object()})

    def test_finish_and_clarification(self):
        for decision in [{"action":"finish","answer":"Evidence-based summary"},{"action":"ask","question":"Which module?"}]:
            with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)):
                self.assertEqual(json.loads(call_project_decision([{"role":"user","content":"read"}],{})),decision)

    def test_plain_final_text_is_not_executed_as_an_action(self):
        with patch("agent.project_decisions.call_tool_messages",return_value={"content":"Summary from inspected files"}):
            result=json.loads(call_project_decision([{"role":"user","content":"review"}],{"read_file":object()}))
        self.assertEqual(result,{"action":"finish","answer":"Summary from inspected files"})

    def test_text_action_json_remains_an_action(self):
        decision={"action":"read_file","arguments":{"relative_path":"build.gradle","start_line":101}}
        with patch("agent.project_decisions.call_tool_messages",return_value={"content":json.dumps(decision)}):
            result=json.loads(call_project_decision([{"role":"user","content":"review"}],{"read_file":object()}))
        self.assertEqual(result,decision)
