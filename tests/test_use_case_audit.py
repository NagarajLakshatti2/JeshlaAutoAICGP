"""Boundary regressions discovered during the UI/agent use-case audit.

All data is synthetic and stored in temporary folders; no provider or Jira calls.
"""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from agent.config.ui_settings import save_model_settings
from agent.interfaces.attachments import attachment_question
from agent.langgraph import langgraph_agent as graph
from agent.actions.receipts import ActionBlocked
from tests.test_streamlit_ui import FakeBackend

class UseCaseAuditTests(unittest.TestCase):
    def test_model_change_cannot_leave_an_incompatible_budget_binding(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict("os.environ",{},clear=True):
            path=Path(folder)/".env"
            for provider in ("openrouter","groq","gemini"):
                prefix=provider.upper()
                path.write_text(prefix+"_API_KEY=fixture\n"+prefix+"_MODEL=old-model\n"+prefix+"_BUDGET_MODEL=old-model\n"+prefix+"_CONTEXT_TOKENS=8192\n",encoding="utf-8")
                before=path.read_bytes()
                with self.subTest(provider=provider):
                    with self.assertRaisesRegex(ValueError,"budget"):
                        save_model_settings(path,provider,"different-model")
                    self.assertEqual(path.read_bytes(),before)
                    self.assertTrue(save_model_settings(path,provider,"old-model")["restart_required"])

    def test_runtime_budget_override_is_checked_before_saving(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict("os.environ",{"GROQ_BUDGET_MODEL":"runtime-model"},clear=True):
            path=Path(folder)/".env";path.write_text("GROQ_API_KEY=fixture\nGROQ_BUDGET_MODEL=file-model\n",encoding="utf-8")
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,"budget"):
                save_model_settings(path,"groq","file-model")
            self.assertEqual(path.read_bytes(),before)

    def test_document_jira_reference_and_explicit_no_connection_stay_local(self):
        document={"name":"requirements.txt","text":"Jira TEST-7 requirement: summary only.","truncated":False}
        questions=("Read Jira issue TEST-7 from the attached file.",
                   "Get Jira TEST-7 from my uploaded document.",
                   "Open Jira TEST-7 in this attachment.",
                   "Summarize Jira TEST-7 in the uploaded document.",
                   "Read Jira TEST-7; do not connect to Jira.",
                   "Create test cases from my attachment, not in Jira.",
                   "Do not create anything in Jira; summarize my file.")
        with patch("builtins.print"):
            for question in questions:
                with self.subTest(question=question):
                    self.assertEqual(graph.router_node({"question":attachment_question(question,[document])})["route"],"direct")

    def test_explicit_external_jira_is_still_available(self):
        from agent.runtime.input_evidence import explicit_jira_request
        for question in ("Read Jira TEST-7 and compare with the attachment.","Fetch Jira issue TEST-7","Create tickets in Jira based on the attached document","STATUS","WORKFLOW HELP"):
            with self.subTest(question=question):self.assertTrue(explicit_jira_request(question))

class CatalogPageAuditTests(unittest.TestCase):
    def test_pages_are_scoped_ordered_and_validated(self):
        from agent.storage.chats import ChatCatalog
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"chats.sqlite3";catalog=ChatCatalog(path,"u","p")
            expected={catalog.create("Chat "+str(i)) for i in range(65)}
            other=ChatCatalog(path,"other-user","p");other.create("Private chat")
            pages=[catalog.list(offset=offset) for offset in (0,30,60)]
            actual=[row["session"] for page in pages for row in page]
            self.assertEqual([len(page) for page in pages],[30,30,5])
            self.assertEqual(set(actual),expected);self.assertEqual(len(actual),len(set(actual)))
            for kwargs in ({"offset":-1},{"offset":True},{"limit":0},{"limit":101},{"limit":True}):
                with self.assertRaises(ValueError):catalog.list(**kwargs)

class AuditUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend(self.temp.name)
        st.cache_resource.clear();self.addCleanup(st.cache_resource.clear)
        for target,value in [("agent.browser_backend.make_browser_backend",self.backend)]:
            mock=patch(target,return_value=value);mock.start();self.addCleanup(mock.stop)
        activity=patch("agent.browser_activity.log_browser_event");activity.start();self.addCleanup(activity.stop)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=10)
        # Existing saved-chat fixtures intentionally select General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False

    def test_removing_first_attachment_updates_preview_and_download(self):
        self.app.run()
        self.app.session_state["attachment_collections"]={"default":[
            {"name":"first.txt","id":"first","text":"First document","truncated":False},
            {"name":"second.txt","id":"second","text":"Second document","truncated":False}]}
        self.app.run()
        remove=next(b for b in self.app.button if b.key and b.key.startswith("remove_doc_default"))
        remove.click().run()
        self.assertFalse(self.app.exception)
        previews=[row.value for row in self.app.text_area if row.label=="Document preview"]
        self.assertEqual(previews,["Second document"])
        self.app.chat_input[0].set_value("Summarize attached document").run()
        self.assertIn("Second document",self.backend.calls[-1][1])
        self.assertNotIn("First document",self.backend.calls[-1][1])

    def test_failed_download_revalidation_clears_previous_snapshot(self):
        with patch.object(self.backend,"generated_files",create=True,return_value=[{"id":"fixture","path":"export.txt"}]),patch.object(self.backend,"generated_file",create=True,side_effect=[{"name":"export.txt","data":b"approved","mime":"text/plain"},ActionBlocked("File changed since approval.")]) as read:
            self.app.run()
            self.app.button(key="prepare_generated_fixture").click().run()
            self.assertIn(("default","fixture"),self.app.session_state["generated_downloads"])
            self.app.button(key="prepare_generated_fixture").click().run()
            self.assertFalse(self.app.exception)
            self.assertNotIn(("default","fixture"),self.app.session_state["generated_downloads"])
            self.assertTrue(any("File changed" in row.value for row in self.app.warning))
            self.assertEqual(read.call_count,2)
            self.assertEqual(self.backend.calls,[])

    def test_memory_preview_refreshes_when_existing_fact_changes(self):
        with patch.object(self.backend,"memory_records",create=True,side_effect=[[{"key":"format","value":"PDF"}],[{"key":"format","value":"DOCX"}]]):
            self.app.run();self.app.button(key="open_memory").click().run()
            self.app.button(key="show_facts").click().run()
            self.assertEqual(next(row.value for row in self.app.text_area if row.label=="format"),"PDF")
            self.app.button(key="show_facts").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(next(row.value for row in self.app.text_area if row.label=="format"),"DOCX")

    def test_view_all_can_open_chat_older_than_recent_thirty(self):
        old=self.backend.create_chat("Oldest saved title")
        self.backend.catalog.append(old,"Old question","Old answer")
        for index in range(35):self.backend.create_chat("Recent "+str(index))
        self.app.run()
        self.assertEqual(self.app.session_state["active_chat"],"default")
        self.app.button(key="older_chat_page").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],"default")
        self.app.selectbox(key="chat_picker").set_value(old).run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],old)
        self.assertTrue(any(row.value=="Old answer" for row in self.app.markdown))
        self.assertEqual(self.backend.calls,[])

    def test_same_named_folder_documents_keep_distinct_previews(self):
        self.app.run()
        self.app.session_state["attachment_collections"]={"default":[
            {"name":"README.md","id":"folder-one","text":"Shared readme","truncated":False},
            {"name":"README.md","id":"folder-two","text":"Shared readme","truncated":False}]}
        self.app.run()
        self.assertFalse(self.app.exception)
        previews=[row for row in self.app.text_area if row.label=="Document preview"]
        self.assertEqual(len(previews),2)
        self.assertEqual(len({row.key for row in previews}),2)
