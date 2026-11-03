import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.project_context import resolve_project_root


class RootTests(unittest.TestCase):
    def test_explicit_root_overrides_only_this_state(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            with patch.dict(os.environ,{"AI_PROJECT_ROOT":a}):
                state={"question":"My project root is "+b+"\nRead build.gradle; do not modify files."}
                self.assertEqual(resolve_project_root(state,a),str(Path(b).resolve()))
                self.assertEqual(os.environ["AI_PROJECT_ROOT"],a)
                self.assertEqual(resolve_project_root({},a),str(Path(a).resolve()))
                self.assertEqual(resolve_project_root({"project_root":b,"question":"Explain it"},a),str(Path(b).resolve()))

    def test_quoted_path_and_colon_command(self):
        with tempfile.TemporaryDirectory(prefix="root with spaces ") as a:
            self.assertEqual(resolve_project_root({"question":'PROJECT ROOT: "'+a+'"'},a),str(Path(a).resolve()))

    def test_documents_and_mentions_cannot_change_root(self):
        with tempfile.TemporaryDirectory() as a:
            with patch.dict(os.environ,{"AI_PROJECT_ROOT":a}):
                self.assertEqual(resolve_project_root({"question":"Explain what project root means", "history":"My project root is invalid", "memory_context":"My project root is invalid"},a),str(Path(a).resolve()))

    def test_invalid_or_multiple_declarations_rejected(self):
        with tempfile.TemporaryDirectory() as a:
            for question in ["My project root is relative/folder","My project root is "+str(Path(a)/"missing"),"My project root is "+a+"\nMy project root is "+a]:
                with self.assertRaises(ValueError):resolve_project_root({"question":question},a)


class InlineRootTests(unittest.TestCase):
    def test_same_line_instructions_and_quoted_roots_resolve_without_changing_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/"project with spaces.v1";root.mkdir()
            for declaration in ("My project root is "+str(root)+". Read build.gradle. Read only.",
                                'My project root is "'+str(root)+'". Read build.gradle.',
                                "PROJECT ROOT: "+str(root)+". Read build.gradle.",
                                "My project root is "+str(root)+".\nRead build.gradle."):
                with self.subTest(declaration=declaration):
                    state={"question":declaration}
                    self.assertEqual(resolve_project_root(state,folder),str(root.resolve()))
                    self.assertEqual(set(state),{"question"})

    def test_complete_folder_with_sentence_like_name_wins_and_ambiguous_prefixes_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            short=Path(folder)/"Alpha";short.mkdir()
            long=Path(folder)/"Alpha. Read Notes";long.mkdir()
            self.assertEqual(resolve_project_root({"question":"My project root is "+str(long)},folder),str(long.resolve()))
            with self.assertRaisesRegex(ValueError,"Ambiguous"):
                resolve_project_root({"question":"My project root is "+str(long)+". Read build.gradle."},folder)
            self.assertEqual(resolve_project_root({"question":'My project root is "'+str(long)+'". Read build.gradle.'},folder),str(long.resolve()))

    def test_bound_project_cannot_be_switched_by_inline_declaration(self):
        from agent.storage.projects import ProjectConfigurationError
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/"a";a.mkdir();b=Path(folder)/"b";b.mkdir()
            state={"project_id":"project-"+"a"*32,"bound_project_root":str(a.resolve()),
                   "question":"My project root is "+str(b)+". Read build.gradle."}
            with self.assertRaisesRegex(ProjectConfigurationError,"Switch Projects"):
                resolve_project_root(state,folder)
            state["question"]="My project root is "+str(a)+". Read build.gradle."
            self.assertEqual(resolve_project_root(state,folder),str(a.resolve()))

    def test_missing_relative_and_malformed_quoted_roots_remain_invalid_and_safe(self):
        from agent.interfaces.errors import user_error_message
        with tempfile.TemporaryDirectory() as folder:
            for declaration in ("My project root is missing. Read build.gradle.",
                                "My project root is "+str(Path(folder)/"missing")+". Read build.gradle.",
                                'My project root is "'+folder,
                                'My project root is "'+folder+'" without a sentence boundary'):
                with self.subTest(declaration=declaration),self.assertRaises(ValueError) as caught:
                    resolve_project_root({"question":declaration},folder)
                message=user_error_message(caught.exception)
                self.assertNotIn("selected provider",message)
                self.assertNotIn(folder,message)


class RealConsoleRootTests(unittest.TestCase):
    def test_new_chat_console_reaches_real_graph_and_reads_inline_root_without_hosted_calls(self):
        import io,json,sys
        from contextlib import redirect_stdout
        from agent.langgraph import langgraph_agent as module
        from agent.runtime.graph import LazyGraph
        from agent.interfaces.console import run_console
        from agent.storage.chats import ChatCatalog
        from tests.run_offline import offline_guard
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)/"data";data.mkdir()
            target=Path(folder)/"target project.v1";target.mkdir()
            (target/"build.gradle").write_text("dependencies { testImplementation 'org.testng:testng:fixture' }\ntest { useTestNG() }\n",encoding="utf-8")
            graph=LazyGraph(data/"agent_memory.db",module.build_graph)
            prompt="My project root is "+str(target)+". Read build.gradle and identify the test framework using file evidence. Read only. Do not edit files, run commands/tests, or connect to Jira or Git."
            decisions=[{"action":"read_file","arguments":{"relative_path":"build.gradle","max_lines":80}},
                       {"action":"finish","answer":"TestNG is declared and useTestNG() is configured in build.gradle."}]
            output=io.StringIO()
            try:
                with offline_guard(),patch.dict(os.environ,{"AI_MEMORY_USER_ID":"fixture-user","AI_MEMORY_NAMESPACE":"fixture"}),patch.object(module,"PROJECT_ROOT",data),patch.object(module,"graph",graph),patch("agent.runtime.execution_log.APPLICATION_ROOT",data),patch.object(sys,"argv",["agent"]),patch("builtins.input",side_effect=["Y","test"]),patch("agent.interfaces.terminal_input.configure_input"),patch("agent.interfaces.terminal_input.read_message",side_effect=[prompt,"EXIT"]),patch("agent.project_decisions.call_project_decision",side_effect=[json.dumps(v) for v in decisions]) as model,patch("agent.local_action_receipts.LocalActionReceipts.run",side_effect=AssertionError("No controlled action allowed")),redirect_stdout(output):
                    run_console(graph=graph,project_root=data,provider="openrouter",session_config=module.session_config,restore_session=module.restore_session)
                text=output.getvalue()
                self.assertIn("Created chat: test",text)
                self.assertIn("New conversation session started",text)
                self.assertIn("Route Used: project",text)
                self.assertIn("TestNG",text)
                self.assertNotIn("Agent execution failed",text)
                self.assertEqual(model.call_count,2)
                catalog=ChatCatalog(data/"outputs/memory/chats.sqlite3","fixture-user","fixture")
                chats=catalog.list()
                self.assertEqual(len(chats),1)
                self.assertEqual(len(catalog.transcript(chats[0]["session"])),1)
            finally:
                graph.close()
