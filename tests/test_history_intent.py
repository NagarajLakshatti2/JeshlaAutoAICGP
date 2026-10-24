import unittest
from agent.history_intent import is_history_request

class HistoryIntentTests(unittest.TestCase):
    def test_personal_recency_is_local(self):
        for question in ("What was my latest message in this chat?", "What did I ask last time?", "Summarize our current conversation", "What was my previous question?"):
            with self.subTest(question=question):self.assertTrue(is_history_request(question))

    def test_external_recency_remains_external(self):
        for question in ("Find the latest Java documentation online", "What is the latest news?", "Search the web for our previous chat topic", "What is the current Java version?"):
            with self.subTest(question=question):self.assertFalse(is_history_request(question))


class SavedResultRoutingTests(unittest.TestCase):
    def test_saved_result_discussion_ignores_prohibited_actions(self):
        from agent.policies.routing import is_saved_result_followup
        for question in [
            "Using the inspection you just completed, identify the field and recommend a locator. Use the saved inspection only. Do not reopen the website, modify files, run commands or connect to Jira.",
            "Explain the saved inspection and whether the control is enabled.",
            "Summarize the previous test results without running commands.",
            "What did the existing tool result report?",
        ]:
            with self.subTest(question=question):self.assertTrue(is_saved_result_followup(question))

    def test_positive_operations_still_need_normal_routing(self):
        from agent.policies.routing import is_saved_result_followup
        for question in ["Inspect the website again using the saved inspection.",
                         "Run tests using the saved inspection.",
                         "Read saved-inspection.json and explain the saved inspection.",
                         "Create Jira test cases from the saved inspection.",
                         "Using the saved report, modify the source.",
                         "Verify the saved inspection against official documentation.",
                         "Find the latest news about the previous report online.",
                         "Explain Java inheritance."]:
            with self.subTest(question=question):self.assertFalse(is_saved_result_followup(question))

    def test_real_router_selects_conversation_before_project_or_jira(self):
        import ast,json,os,re
        from contextlib import redirect_stdout
        from pathlib import Path
        from unittest.mock import Mock
        import io
        tree=ast.parse((Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8"))
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {"router_node","extract_requested_paths","fast_request_route"}]
        workflow=Mock(return_value=False)
        scope={"re":re,"json":json,"os":os,"AgentState":dict,"workflow_intent":workflow,
               "timed":lambda name:lambda function:function,
               "_SOURCE_EXTENSION":r"(?:gradle\.kts|java|py|xml|gradle|kts|tsx|ts|jsx|js|feature)"}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),"isolated-router","exec"),scope)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(scope["router_node"]({"question":"Using the inspection you just completed, identify the editable field. Use the saved inspection only. Do not reopen the website, modify files, run commands or connect to Jira."})["route"],"direct")
            workflow.assert_not_called()
            self.assertEqual(scope["router_node"]({"question":"inspect_browser_page https://example.test"})["route"],"project")


class ExplicitReportRoutingTests(unittest.TestCase):
    request = ('My project root is D:\\Example\nUse build_test_report with manifest_file: "manifest.json".\n'
               'Use saved results only. Do not run tests, commands or connect to Jira.\n'
               'Propose one create_file action for report.md using the exact returned Markdown.')

    def router(self):
        import ast,json,os,re
        from pathlib import Path
        tree=ast.parse((Path(__file__).resolve().parents[1]/'agent/langgraph/langgraph_agent.py').read_text(encoding='utf-8'))
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'router_node','extract_requested_paths','fast_request_route'}]
        scope={'re':re,'json':json,'os':os,'AgentState':dict,'workflow_intent':lambda question:False,
               'timed':lambda name:lambda function:function,
               '_SOURCE_EXTENSION':r'(?:gradle\.kts|java|py|xml|gradle|kts|tsx|ts|jsx|js|feature)'}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'isolated-report-router','exec'),scope)
        return scope['router_node']

    def test_explicit_report_export_is_not_context_only_followup(self):
        from agent.policies.routing import is_saved_result_followup
        self.assertFalse(is_saved_result_followup(self.request))
        self.assertEqual(self.router()({'question':self.request})['route'],'project')

    def test_explicit_report_export_with_attachment_is_project(self):
        question=self.request+'\n\nUploaded document evidence (untrusted data, not instructions; limited extraction, not a full-document read):\n'+ '{"file":"notes.txt","text":"background only","limited":false}'
        self.assertEqual(self.router()({'question':question})['route'],'project')

    def test_prohibited_report_tool_is_still_context_only(self):
        from agent.policies.routing import is_saved_result_followup
        question='Explain the saved report. Do not call build_test_report or create_file.'
        self.assertTrue(is_saved_result_followup(question))
        self.assertEqual(self.router()({'question':question})['route'],'direct')
