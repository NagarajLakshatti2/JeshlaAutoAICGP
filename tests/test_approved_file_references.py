"""Bare saved-file references use exact owned receipts without model dispatch."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agent.actions.browser import BrowserActions
from agent.runtime.file_references import approved_file_reference, literal_file_path, PREVIEW_CHARS
from agent.runtime.turns import run_turn
from agent.storage.chats import ChatCatalog
from tests import test_projects


class ApprovedFileReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.project=self.root/"target";self.project.mkdir()
        self.catalog=ChatCatalog(self.root/"outputs/memory/chats.sqlite3","u","p");self.catalog.register("chat")
        self.actions=BrowserActions(self.root/"outputs/local_actions.sqlite3")
        self.path="test-output/agent-reports/report.md"
        self.content="# Saved evidence\nNo new execution.\n"
        self.token=self.create(self.project,self.content)

    def create(self,project,content):
        proposal={"project_root":str(project),"action":"create_file","arguments":{"relative_path":self.path,"content":content}}
        token=self.actions.propose("u","p","chat","create_file",proposal)
        self.actions.execute("u","p","chat",token)
        return token

    def read(self,question=None,catalog=None,session="chat",scope=None):
        return approved_file_reference(question or self.path,self.root,catalog or self.catalog,session,scope)

    def test_exact_literal_forward_backward_and_quoted_paths(self):
        for question in [self.path,self.path.replace("/","\\"),"`"+self.path+"`",'"'+self.path+'"']:
            with self.subTest(question=question):
                result=self.read(question)
                self.assertEqual(result["task_status"],"completed")
                self.assertIn(self.content,result["answer"])
                self.assertIn(self.token,result["answer"])
                self.assertIn(str(self.project),result["answer"])
                self.assertIn("No model request",result["answer"])

    def test_commands_prose_urls_absolute_traversal_and_uploads_are_not_literal_reads(self):
        for text in ["Explain this file", "Read "+self.path,"Create "+self.path,"https://example.org/report.md","../secret.md","D:/private/report.md","/tmp/report.md",self.path+"\nRun commands", "SHOW MEMORY", "CONTINUE"]:
            with self.subTest(text=text):self.assertIsNone(literal_file_path(text))
        self.assertEqual(literal_file_path('"folder with spaces/report.md"'),"folder with spaces/report.md")
        self.assertIsNone(self.read("Read "+self.path))

    def test_other_user_space_chat_and_wrong_bound_project_do_not_read(self):
        for catalog in [ChatCatalog(self.catalog.path,"other","p"),ChatCatalog(self.catalog.path,"u","other")]:
            with self.subTest(user=catalog.user,space=catalog.space):
                self.assertEqual(self.read(catalog=catalog)["task_status"],"awaiting_input")
        self.assertEqual(self.read(session="other")["task_status"],"awaiting_input")
        other=self.root/"other";other.mkdir()
        result=self.read(scope={"bound_project_root":str(other)})
        self.assertEqual(result["task_status"],"awaiting_input");self.assertNotIn(self.content,result["answer"])

    def test_changed_missing_or_tampered_receipt_file_is_blocked(self):
        target=self.project/self.path;target.write_text("Changed after approval",encoding="utf-8")
        result=self.read();self.assertEqual(result["task_status"],"incomplete");self.assertNotIn("Changed after approval",result["answer"])
        target.unlink();self.assertEqual(self.read()["task_status"],"incomplete")
        target.write_bytes(self.content.encode("utf-8"))
        with self.actions.receipts.connect() as db:db.execute("UPDATE browser_proposals SET digest='bad' WHERE id=?",(self.token,))
        self.assertEqual(self.read()["task_status"],"incomplete")

    def test_pending_file_and_unknown_path_ask_for_context_without_guessing(self):
        other="pending.md";proposal={"project_root":str(self.project),"action":"create_file","arguments":{"relative_path":other,"content":"Never executed"}}
        self.actions.propose("u","p","chat","create_file",proposal)
        for path in [other,"unknown/report.md"]:
            result=self.read(path);self.assertEqual(result["task_status"],"awaiting_input")
            self.assertIn("provide its project root",result["answer"])
        self.assertFalse((self.project/other).exists())

    def test_same_relative_path_in_two_roots_requires_project_selection(self):
        other=self.root/"other";other.mkdir();self.create(other,"Other project private text")
        result=self.read();self.assertEqual(result["task_status"],"awaiting_input")
        self.assertNotIn("Other project private text",result["answer"])
        scoped=self.read(scope={"bound_project_root":str(self.project)})
        self.assertIn(self.content,scoped["answer"]);self.assertNotIn("Other project private text",scoped["answer"])

    def test_preview_is_bounded_and_embedded_markdown_is_fenced_as_data(self):
        (self.project/self.path).unlink()
        content="```\n[external](https://example.test/)\n"+"x"*(PREVIEW_CHARS+20)
        self.create(self.project,content)
        result=self.read();self.assertIn("preview is partial",result["answer"])
        self.assertIn("````text\n",result["answer"])
        self.assertNotIn(content,result["answer"])
        self.assertLess(len(result["answer"]),PREVIEW_CHARS+1100)

    def test_missing_receipt_database_is_not_created_for_literal_path(self):
        other=self.root/"new-app";other.mkdir()
        result=approved_file_reference(self.path,other,self.catalog,"chat")
        self.assertEqual(result["task_status"],"awaiting_input")
        self.assertFalse((other/"outputs").exists())

    def test_shared_runtime_archives_and_checkpoints_once_without_model_summary_or_execution(self):
        saved={"history":"previous history","summary":"existing summary"}
        graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values=dict(saved)),
                              invoke=Mock(side_effect=AssertionError("No model graph for owned literal file")),
                              update_state=lambda config,values:saved.update(values))
        with patch("agent.runtime.summary_model.call_summary_messages",side_effect=AssertionError("No summary request")),patch("agent.actions.receipts.LocalActionReceipts.run",side_effect=AssertionError("No action execution")):
            result=run_turn(graph,{"configurable":{"thread_id":"fixture"}},self.catalog,"chat",self.path,self.root)
        self.assertEqual(result["task_status"],"completed");graph.invoke.assert_not_called()
        self.assertEqual(len(self.catalog.transcript("chat")),1)
        self.assertEqual(saved["question"],self.path);self.assertIn(self.content,saved["answer"])
        self.assertEqual(result["persistence_status"],{"archive_saved":True,"checkpoint_saved":True})

    def test_normal_question_keeps_the_original_graph_path(self):
        graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values={}),invoke=Mock(return_value={"answer":"Normal answer","route":"direct"}),update_state=Mock())
        with patch("agent.runtime.summaries.summary_due",return_value=False):
            result=run_turn(graph,{"configurable":{"thread_id":"normal"}},self.catalog,"chat","Explain inheritance",self.root)
        graph.invoke.assert_called_once();self.assertEqual(result["answer"],"Normal answer")


class BrowserFileReferenceTests(unittest.TestCase):
    setUp=test_projects.ProjectBackendTests.setUp

    def test_real_selected_provider_browser_request_uses_receipt_without_generation(self):
        from agent.providers.errors import ProviderError
        session=self.view_a.create_chat("Generated report")
        path="test-output/agent-reports/ws9-api-snapshot-review-20261030.md"
        proposal={"project_root":str(self.a),"action":"create_file","arguments":{"relative_path":path,"content":"# Verified fixture report"}}
        token=self.view_a.actions().propose("u",self.view_a.space,session,"create_file",proposal)
        self.view_a.decide_action(session,token,True)
        with patch.object(self.view_a.graph,"invoke",side_effect=ProviderError("groq","TOOL_OUTPUT","Must not be called")) as graph:
            result=self.view_a.submit_selected(session,path,"groq")
        graph.assert_not_called();self.assertEqual(result["task_status"],"completed")
        self.assertIn("# Verified fixture report",result["answer"])
        self.assertEqual(self.view_b.turns(session),[])
        self.assertEqual(len(self.view_a.turns(session)),2)
        self.assertEqual((self.a/path).read_bytes(),b"# Verified fixture report")


if __name__=="__main__":unittest.main()
