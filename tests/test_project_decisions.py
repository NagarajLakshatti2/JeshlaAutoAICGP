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

    def test_nullable_unused_final_fields_are_normalized(self):
        decision={"action":"finish","arguments":None,"question":None,"answer":"Confirmed from settings.gradle"}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)) as model:
            result=json.loads(call_project_decision([{"role":"user","content":"review"}],{}))
        self.assertEqual(result["answer"],decision["answer"])
        self.assertNotIn("question",result)
        self.assertEqual(model.call_count,1)

    def test_nested_final_answer_is_normalized(self):
        decision={"action":"finish","arguments":{"answer":"Confirmed project name"}}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)):
            result=json.loads(call_project_decision([{"role":"user","content":"review"}],{}))
        self.assertEqual(result["answer"],"Confirmed project name")

    def test_invalid_proposal_gets_one_correction(self):
        with patch("agent.project_decisions.call_tool_messages",side_effect=[reply({"action":"invented"}),reply({"action":"finish","answer":"Corrected"})]) as model,patch("agent.project_decisions.LLM_PROVIDER","gemini"):
            result=json.loads(call_project_decision([{"role":"user","content":"review"}],{}))
        self.assertEqual(result["answer"],"Corrected")
        self.assertEqual(model.call_count,2)

    def test_executable_null_arguments_still_rejected_and_bounded(self):
        with patch("agent.project_decisions.call_tool_messages",return_value=reply({"action":"create_file","arguments":None})) as model:
            with self.assertRaisesRegex(RuntimeError,"format correction"):
                call_project_decision([{"role":"user","content":"review"}],{"create_file":object()})
        self.assertEqual(model.call_count,2)

    def test_groq_tool_output_rejection_gets_one_safe_correction(self):
        from agent.provider_errors import ProviderError
        error=ProviderError("groq","TOOL_OUTPUT","Generated call rejected",status=400)
        with patch("agent.project_decisions.LLM_PROVIDER","groq"),patch("agent.project_decisions.call_tool_messages",side_effect=[error,reply({"question":"Which file?"},name="ask")]) as model:
            result=json.loads(call_project_decision([{"role":"user","content":"Inspect a file"}],{"read_file":object()}))
        self.assertEqual(result["action"],"ask");self.assertEqual(model.call_count,2)
        self.assertTrue(model.call_args.kwargs["require_tool"])
        self.assertIn("rejected proposal",model.call_args.args[0][-1]["content"])
    def test_repeated_tool_rejection_and_quota_do_not_loop(self):
        from agent.provider_errors import ProviderError
        for category,count in [("TOOL_OUTPUT",2),("QUOTA_EXHAUSTED",1),("AUTHENTICATION",1)]:
            with patch("agent.project_decisions.call_tool_messages",side_effect=ProviderError("groq",category,"Rejected")) as model:
                with self.assertRaises(ProviderError):call_project_decision([{"role":"user","content":"Inspect"}],{})
            self.assertEqual(model.call_count,count)
    def test_other_providers_keep_existing_tool_selection(self):
        for provider in ["ollama","openrouter","gemini"]:
            with patch("agent.project_decisions.LLM_PROVIDER",provider),patch("agent.project_decisions.call_tool_messages",return_value=reply({"action":"ask","question":"Which file?"})) as model:
                call_project_decision([{"role":"user","content":"Inspect"}],{})
            self.assertNotIn("forced_function",model.call_args.kwargs)

    def test_groq_unknown_wrapper_call_retries_registered_native_action_only(self):
        import tempfile
        from pathlib import Path
        from agent.tools.project_tools import ProjectTools
        with tempfile.TemporaryDirectory() as folder:
            tools=ProjectTools(folder)
            native=reply({"relative_path":"note.txt","content":"draft"},name="create_file")
            with patch("agent.project_decisions.LLM_PROVIDER","groq"),patch("agent.project_decisions.call_tool_messages",side_effect=[reply({"action":"create_file"},name="unregistered"),native]) as model:
                result=json.loads(call_project_decision([{"role":"user","content":"Create a draft"}],{"create_file":tools.create_file}))
            self.assertEqual(result,{"action":"create_file","arguments":{"relative_path":"note.txt","content":"draft"}})
            self.assertFalse((Path(folder)/"note.txt").exists())
            specs=model.call_args.args[1];create=next(item for item in specs if item["function"]["name"]=="create_file")
            self.assertEqual(set(create["function"]["parameters"]["required"]),{"relative_path","content"})
            self.assertTrue(model.call_args.kwargs["require_tool"])
    def test_native_fallback_rejects_missing_and_extra_arguments(self):
        import tempfile
        from agent.tools.project_tools import ProjectTools
        from agent.project_native_specs import decode_native_project_reply
        with tempfile.TemporaryDirectory() as folder:
            tools=ProjectTools(folder)
            for args in [{"relative_path":"note.txt"},{"relative_path":"note.txt","content":"x","shell":"bad"}]:
                with self.assertRaises(ValueError):decode_native_project_reply(reply(args,name="create_file"),{"create_file":tools.create_file})
