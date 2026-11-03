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

    def test_legacy_empty_action_list_exposes_only_ask_and_finish(self):
        decision={"action":"finish","answer":"Inspected evidence."}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)) as model:
            self.assertEqual(json.loads(call_project_decision([],[])),decision)
        allowed=model.call_args.args[1][0]["function"]["parameters"]["properties"]["action"]["enum"]
        self.assertEqual(allowed,["ask","finish"])

    def test_generic_envelope_advertises_real_handler_arguments(self):
        def read_file(relative_path: str, start_line: int = 1, max_lines: int = 40):pass
        def inspect_browser_page(url: str, evidence_folder: str = "test-output/agent-web", limit: int = 20):pass
        decision={"action":"read_file","arguments":{"relative_path":"requirements.md","start_line":15,"max_lines":15}}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply(decision)) as model:
            result=json.loads(call_project_decision([{"role":"user","content":"Read the selected source"}],
                {"read_file":read_file,"inspect_browser_page":inspect_browser_page}))
        self.assertEqual(result,decision)
        properties=model.call_args.args[1][0]["function"]["parameters"]["properties"]["arguments"]["properties"]
        for name in ("files","relative_path","start_line","max_lines","url","evidence_folder","limit"):
            self.assertIn(name,properties)
        self.assertEqual(properties['relative_path']['type'],'string')
        self.assertEqual(properties['start_line']['type'],'integer')

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


class CrossProviderProposalCorrectionTests(unittest.TestCase):
    def test_wrong_wrapper_function_gets_registered_native_correction(self):
        from unittest.mock import Mock
        def read_file(relative_path: str, start_line: int = 1, max_lines: int = 40):
            raise AssertionError("Proposal decoding must not execute a handler")
        native=reply({"relative_path":"inspection.json","start_line":1,"max_lines":30},name="read_file")
        for provider in ["openrouter","gemini"]:
            with self.subTest(provider=provider),patch("agent.project_decisions.LLM_PROVIDER",provider),patch("agent.project_decisions.last_provider",return_value=provider),patch("agent.project_decisions.call_tool_messages",side_effect=[reply({},name="unregistered"),native]) as model:
                result=json.loads(call_project_decision([{"role":"user","content":"Read the saved inspection file"}],{"read_file":read_file}))
                self.assertEqual(result,{"action":"read_file","arguments":{"relative_path":"inspection.json","start_line":1,"max_lines":30}})
                self.assertEqual(model.call_count,2)
                names={item['function']['name'] for item in model.call_args.args[1]}
                self.assertEqual(names,{"read_file","ask","finish"})
                self.assertNotIn("submit_project_action",names)

    def test_multiple_first_calls_are_discarded_before_one_native_correction(self):
        def read_file(relative_path: str):raise AssertionError("No execution")
        first=reply({},name="unregistered");first['tool_calls']*=2
        final=reply({"relative_path":"inspection.json"},name="read_file")
        with patch("agent.project_decisions.LLM_PROVIDER","openrouter"),patch("agent.project_decisions.last_provider",return_value="openrouter"),patch("agent.project_decisions.call_tool_messages",side_effect=[first,final]) as model:
            result=json.loads(call_project_decision([{"role":"user","content":"Read inspection.json"}],{"read_file":read_file}))
        self.assertEqual(result['action'],'read_file');self.assertEqual(model.call_count,2)

    def test_invalid_native_correction_stops_without_selecting_one_call(self):
        def read_file(relative_path: str):raise AssertionError("No execution")
        for second in [reply({'relative_path':'inspection.json'},name='unregistered'),
                       {'tool_calls':reply({'relative_path':'inspection.json'},name='read_file')['tool_calls']*2},
                       reply({'relative_path':'inspection.json','unexpected':'data'},name='read_file')]:
            with self.subTest(second=second),patch("agent.project_decisions.LLM_PROVIDER","openrouter"),patch("agent.project_decisions.last_provider",return_value="openrouter"),patch("agent.project_decisions.call_tool_messages",side_effect=[reply({},name='unregistered'),second]) as model:
                with self.assertRaisesRegex(RuntimeError,'format correction'):
                    call_project_decision([{'role':'user','content':'Read saved file'}],{'read_file':read_file})
                self.assertEqual(model.call_count,2)


class NativeFinalResponseTests(unittest.TestCase):
    def test_final_text_and_terminal_json_are_safe_terminal_responses(self):
        from agent.project_native_specs import decode_native_project_reply
        from unittest.mock import Mock
        handler=Mock(side_effect=AssertionError("No action during decoding"))
        samples=[("TestNG is declared in the inspected file.","finish"),
                 (json.dumps({"action":"finish","answer":"TestNG from dependencies."}),"finish"),
                 (json.dumps({"answer":"TestNG from useTestNG()."}),"finish"),
                 (json.dumps({"action":"ask","question":"Which module?"}),"ask"),
                 ("\x60\x60\x60json\n"+json.dumps({"action":"finish","answer":"TestNG."})+"\n\x60\x60\x60","finish")]
        for content,expected in samples:
            with self.subTest(content=content):
                decision=json.loads(decode_native_project_reply({"content":content,"tool_calls":[]},{"read_file":handler}))
                self.assertEqual(decision["action"],expected)
        handler.assert_not_called()

    def test_text_action_malformed_json_empty_and_parallel_calls_remain_rejected(self):
        from agent.project_native_specs import decode_native_project_reply
        samples=[{"content":json.dumps({"action":"create_file","arguments":{"relative_path":"x.py","content":"x"}})},
                 {"content":json.dumps({"name":"read_file","arguments":{"relative_path":"build.gradle"}})},
                 {"content":json.dumps([{"action":"read_file","arguments":{"relative_path":"build.gradle"}}])},
                 {"content":"\x60\x60\x60json\n{\"action\":\"finish\"}"},
                 {"content":'{"action":"finish","answer":'}, {"content":""},
                 {"tool_calls":reply({"answer":"ambiguous"},name="finish")["tool_calls"]*2,"content":"Do not use as fallback"}]
        for sample in samples:
            with self.subTest(sample=sample),self.assertRaises(ValueError):
                decode_native_project_reply(sample,{"read_file":object(),"create_file":object()})

    def test_native_correction_accepts_final_answer_for_each_hosted_provider(self):
        def read_file(relative_path:str):raise AssertionError("No execution")
        for provider in ("openrouter","groq","gemini"):
            with self.subTest(provider=provider),patch("agent.project_decisions.LLM_PROVIDER",provider),patch("agent.project_decisions.last_provider",return_value=provider),patch("agent.project_decisions.call_tool_messages",side_effect=[reply({"answer":"TestNG"},name="finish"),{"content":"TestNG is configured in the inspected build.gradle."}]) as model:
                result=json.loads(call_project_decision([{"role":"user","content":"Identify the framework from the inspected file."}],{"read_file":read_file}))
                self.assertEqual(result["action"],"finish")
                self.assertEqual(model.call_count,2)
                self.assertTrue(model.call_args.kwargs["require_tool"])

    def test_actual_read_only_project_loop_preserves_inspected_evidence(self):
        import io,os,tempfile
        from pathlib import Path
        from contextlib import redirect_stdout
        from tests.test_project_budget import BudgetTests
        from agent.project_decisions import call_project_decision as real_decision
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"build.gradle").write_text("dependencies { testImplementation 'org.testng:testng:fixture' }\ntest { useTestNG() }\n",encoding="utf-8")
            sequence=[reply({"action":"read_file","arguments":{"relative_path":"build.gradle","max_lines":40}}),
                      reply({"answer":"TestNG"},name="finish"),
                      {"content":"TestNG: build.gradle declares org.testng:testng and useTestNG()."}]
            with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.LLM_PROVIDER","openrouter"),patch("agent.project_decisions.last_provider",return_value="openrouter"),patch("agent.project_decisions.call_tool_messages",side_effect=sequence) as provider,patch("agent.project_decisions.call_project_decision",side_effect=real_decision),patch("agent.local_action_receipts.LocalActionReceipts.run",side_effect=AssertionError("Read only; no approval or execution")),redirect_stdout(io.StringIO()):
                result=BudgetTests().project_function(root)({"question":"Read build.gradle and identify the test framework. Read only; no changes, commands, Jira or Git.","project_root":str(root)})
            self.assertEqual(result["task_status"],"completed",result["answer"])
            self.assertIn("TestNG",result["answer"])
            self.assertIn("build.gradle: lines 1",result["answer"])
            self.assertEqual(provider.call_count,3)

    def test_final_text_does_not_bypass_requested_file_coverage(self):
        import io,os,tempfile
        from pathlib import Path
        from contextlib import redirect_stdout
        from tests.test_project_budget import BudgetTests
        from agent.project_decisions import call_project_decision as real_decision
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.call_tool_messages",return_value={"content":"TestNG is configured."}),patch("agent.project_decisions.call_project_decision",side_effect=real_decision),redirect_stdout(io.StringIO()):
                result=BudgetTests().project_function(root)({"question":"Read build.gradle and identify the test framework.","project_root":str(root)})
            self.assertEqual(result["task_status"],"incomplete")
            self.assertNotIn("Inspected sources",result["answer"])


class MalformedTerminalJSONTests(unittest.TestCase):
    def test_malformed_or_truncated_terminal_json_is_not_displayed_as_plain_text(self):
        from agent.runtime.project_decisions import decode_project_reply
        samples = ['{"action":"finish","answer":',
                   '{"action":"finish","answer":"A malformed quote: \\” text"}',
                   '\x60\x60\x60json\n{"action":"finish","answer":']
        for content in samples:
            with self.subTest(content=content), self.assertRaises(ValueError):
                decode_project_reply({'content':content,'tool_calls':[]},{'finish','ask'})

    def test_plain_prose_and_valid_data_json_remain_readable(self):
        from agent.runtime.project_decisions import decode_project_reply
        for content in ['The saved report has one failed case.', '{"passed":2,"failed":1}']:
            with self.subTest(content=content):
                decision=json.loads(decode_project_reply({'content':content,'tool_calls':[]},{'finish','ask'}))
                self.assertEqual(decision['action'],'finish')
                self.assertEqual(decision['answer'],content)

    def test_existing_single_format_correction_recovers_without_executing_an_action(self):
        malformed={'content':'{"action":"finish","answer":','tool_calls':[]}
        with patch('agent.project_decisions.call_tool_messages',side_effect=[malformed,reply({'action':'finish','answer':'Two passed; one failed.'})]) as model:
            decision=json.loads(call_project_decision([{'role':'user','content':'Explain the saved evidence.'}],{}))
        self.assertEqual(decision['answer'],'Two passed; one failed.')
        self.assertEqual(model.call_count,2)


class SourceIdentifierPresentationTests(unittest.TestCase):
    def test_only_observed_tokens_get_their_ascii_hyphens_restored(self):
        from agent.runtime.project_decisions import source_identifier_tokens,preserve_source_identifiers
        observed=source_identifier_tokens('QPH-012; login-username; qapracticehub-test-cases.md')
        answer='QPH\u2011012 failed; login\u2011username empty; qapracticehub\u2011test\u2011cases.md. UNKNOWN\u201199 is unchanged.'
        result=preserve_source_identifiers(answer,observed)
        self.assertIn('QPH-012 failed',result)
        self.assertIn('login-username',result)
        self.assertIn('qapracticehub-test-cases.md',result)
        self.assertIn('UNKNOWN\u201199',result)

    def test_normal_text_and_unobserved_lookalikes_are_preserved(self):
        from agent.runtime.project_decisions import preserve_source_identifiers
        answer='A normal reply: QPH\u2011012 and arithmetic 5\u22123.'
        self.assertEqual(preserve_source_identifiers(answer,set()),answer)

    def test_capture_is_bounded_and_never_reads_a_file(self):
        from agent.runtime.project_decisions import source_identifier_tokens
        self.assertEqual(source_identifier_tokens(None),set())
        self.assertNotIn('LATE-999',source_identifier_tokens('x'*16000+' LATE-999'))

    def test_actual_project_finish_uses_only_the_current_read_evidence(self):
        import io,tempfile
        from pathlib import Path
        from contextlib import redirect_stdout
        from tests.test_project_budget import BudgetTests
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'report.md').write_text('QPH-012 failed. login-username is empty.',encoding='utf-8')
            decisions=[json.dumps({'action':'read_file','arguments':{'relative_path':'report.md','max_lines':40}}),
                       json.dumps({'action':'finish','answer':'QPH\u2011012 failed; login\u2011username empty.'})]
            with patch('agent.project_decisions.call_project_decision',side_effect=decisions),redirect_stdout(io.StringIO()):
                result=BudgetTests().project_function(root)({'question':'Read report.md and explain.','project_root':str(root)})
            self.assertIn('QPH-012 failed',result['answer'])
            self.assertIn('login-username',result['answer'])
