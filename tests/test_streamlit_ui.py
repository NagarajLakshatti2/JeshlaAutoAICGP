"""Headless browser UI tests with a fake agent; no hosted requests or Jira writes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from agent.chat_catalog import ChatCatalog

class FakeBackend:
    provider="test-provider"
    def __init__(self,folder):
        self.catalog=ChatCatalog(Path(folder)/"chats.sqlite3","u","p")
        self.catalog.register("default")
        self.calls=[]
    def list_chats(self):return self.catalog.list()
    def list_chat_page(self,offset=0):return self.catalog.list(limit=31,offset=offset)
    def create_chat(self,title):return self.catalog.create(title)
    def get_chat(self,session):return self.catalog.get(session)
    def turns(self,session):return self.catalog.transcript(session)
    def search_chats(self,query,session=None):return self.catalog.search_turns(query,session=session,limit=10)
    def provider_info(self):return {"provider":"groq","model":"fixture-model","key_present":True,"local":False,"supported":True}
    def memory(self):return '- project_name: "JeshlaAutoAI"'
    def submit(self,session,question):
        self.calls.append((session,question))
        self.catalog.append(session,question,"Test answer")
        return {"answer":"Test answer","notices":[]}

class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend(self.temp.name)
        activity=patch("agent.browser_activity.log_browser_event")
        self.activity=activity.start();self.addCleanup(activity.stop)
        st.cache_resource.clear()
        self.patch=patch("agent.browser_backend.make_browser_backend",return_value=self.backend)
        self.patch.start();self.addCleanup(self.patch.stop);self.addCleanup(st.cache_resource.clear)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=10)
    def test_initial_render_without_model_call(self):
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[])
        self.assertEqual(self.app.title[0].value,"What would you like to build?")
    def test_new_chat_and_multiline_message(self):
        self.app.run()
        self.app.button(key="create_new_chat").click().run()
        self.assertFalse(self.app.exception)
        self.assertIsNone(self.backend.get_chat(self.app.session_state["active_chat"]))
        self.app.chat_input[0].set_value("first line\nsecond line").run()
        self.assertFalse(self.app.exception)
        active=self.app.session_state["active_chat"]
        self.assertEqual(self.backend.get_chat(active)["title"],"first line second line")
        self.assertEqual(self.backend.calls,[(active,"first line\nsecond line")])
        self.app.run()
        self.assertEqual(len(self.backend.calls),1)
        self.assertTrue(any(row.value=="Test answer" for row in self.app.markdown))
    def test_memory_view_without_model(self):
        self.app.run()
        self.app.button(key="open_memory").click().run()
        self.app.button(key="show_facts").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[])
        self.assertIn("JeshlaAutoAI",self.app.session_state["saved_facts"])
        self.assertTrue(any(call.args[0]=="memory_viewed" for call in self.activity.call_args_list))

    def test_title_filter_does_not_switch_or_call_model(self):
        self.backend.create_chat("Java learning")
        self.app.run()
        active=self.app.session_state["active_chat"]
        self.app.text_input(key="chat_title_filter").set_value("java").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],active)
        self.assertEqual(self.backend.calls,[])
        self.assertTrue(any(b.label=="Java learning" for b in self.app.button))
        self.app.text_input(key="chat_title_filter").set_value("no matching title").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],active)

    def test_recent_chat_button_restores_correct_history_without_model(self):
        other=self.backend.create_chat("Other conversation")
        self.backend.catalog.append(other,"Question in other chat","Answer in other chat")
        self.app.run()
        self.app.button(key="open_chat_"+other).click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],other)
        self.assertEqual(self.backend.calls,[])
        self.assertTrue(any(row.value=="Answer in other chat" for row in self.app.markdown))

    def test_archive_search_opens_old_chat_only_on_selection(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        old=self.backend.create_chat("Old learning")
        self.backend.catalog.append(old,"Explain platypus","Saved mammal answer")
        for index in range(32):self.backend.create_chat("Recent "+str(index))
        self.app.run()
        self.app.text_input(key="archive_query").set_value("platypus")
        next(b for b in self.app.button if b.label=="Search saved messages").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],"default")
        next(b for b in self.app.button if b.label=="Open chat: Old learning").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],old)
        self.assertEqual(self.backend.calls,[])
        self.assertTrue(any(row.value=="Saved mammal answer" for row in self.app.markdown))

    def test_archive_search_scope_and_no_match_preserve_chat(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        other=self.backend.create_chat("Other")
        self.backend.catalog.append(other,"Special narwhal","Answer")
        foreign=ChatCatalog(self.backend.catalog.path,"other-user","p")
        foreign.register("default");foreign.append("default","Private narwhal","Private")
        self.app.run()
        self.app.text_input(key="archive_query").set_value("narwhal")
        self.app.checkbox(key="archive_current_only").check()
        next(b for b in self.app.button if b.label=="Search saved messages").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["archive_results"]["result"]["matches"],[])
        self.app.checkbox(key="archive_current_only").uncheck()
        next(b for b in self.app.button if b.label=="Search saved messages").click().run()
        matches=self.app.session_state["archive_results"]["result"]["matches"]
        self.assertEqual([m["chat_id"] for m in matches],[other])
        self.assertEqual(self.app.session_state["active_chat"],"default")
        self.assertEqual(self.backend.calls,[])

    def test_model_settings_render_without_request(self):
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("fixture-model" in row.value for row in self.app.text))
        self.assertTrue(any("Availability and quota are checked" in row.value for row in self.app.caption))
        self.assertEqual(self.backend.calls,[])

    def test_memory_editor_requires_confirmation_and_does_not_repeat_on_rerun(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        with patch.object(self.backend,"edit_memory",create=True,return_value={"answer":"Saved memory: report_format.","notices":[]}) as edit:
            self.app.run()
            self.app.button(key="open_memory").click().run()
            self.app.text_input(key="memory_key").set_value("report_format")
            self.app.text_area(key="memory_edit_value").set_value("PDF")
            next(b for b in self.app.button if b.label=="Apply memory change").click().run()
            edit.assert_not_called()
            self.app.checkbox(key="memory_confirm").check()
            next(b for b in self.app.button if b.label=="Apply memory change").click().run()
            self.assertFalse(self.app.exception)
            edit.assert_called_once_with("default","save","report_format","PDF")
            self.app.run()
            self.assertEqual(edit.call_count,1)
            self.app.button(key="open_memory").click().run()
            self.assertFalse(self.app.checkbox(key="memory_confirm").value)
            self.app.radio(key="memory_operation").set_value("Forget")
            self.app.checkbox(key="memory_confirm").check()
            next(b for b in self.app.button if b.label=="Apply memory change").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(edit.call_args.args,("default","forget","report_format","PDF"))
            self.assertEqual(self.backend.calls,[])

    def test_request_status_survives_rerender_and_is_scoped_by_chat(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        self.app.run()
        with patch.object(self.backend,"submit",return_value={"answer":"Need more details","task_status":"incomplete","notices":[]}):
            self.app.chat_input[0].set_value("inspect project").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["request_status_by_chat"]["default"]["label"],"Incomplete")
        self.app.run()
        self.assertTrue(any("Last request: Incomplete" in row.value for row in self.app.warning))
        other=self.backend.create_chat("No request yet")
        self.app.run();self.app.selectbox(key="chat_picker").set_value(other).run()
        self.assertFalse(any("Last request:" in row.value for row in self.app.warning))
        self.app.selectbox(key="chat_picker").set_value("default").run()
        self.assertTrue(any("Last request: Incomplete" in row.value for row in self.app.warning))

    def test_attachment_is_scoped_and_answer_can_be_downloaded(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        self.app.run()
        self.app.session_state["attachments_by_chat"]={"default":{"name":"notes.txt","text":"Unique document evidence","truncated":False}}
        self.app.run()
        self.app.chat_input[0].set_value("Summarize the attachment").run()
        self.assertFalse(self.app.exception)
        self.assertIn("Unique document evidence",self.backend.calls[-1][1])
        self.assertEqual(self.app.session_state["answer_downloads"]["default"],"Test answer")
        other=self.backend.create_chat("Separate")
        self.app.run();self.app.selectbox(key="chat_picker").set_value(other).run()
        self.app.chat_input[0].set_value("hello").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls[-1],(other,"hello"))

    def test_settings_require_confirmation_and_keep_running_provider(self):
        with patch.object(self.backend,"save_model_settings",create=True,return_value={"provider":"groq","model":"new-model"}) as save:
            self.app.run()
            self.app.button(key="open_settings").click().run()
            self.app.text_input(key="next_model").set_value("new-model")
            next(b for b in self.app.button if b.label=="Save model settings").click().run()
            save.assert_not_called()
            self.app.checkbox(key="confirm_settings").check()
            next(b for b in self.app.button if b.label=="Save model settings").click().run()
            self.assertFalse(self.app.exception)
            save.assert_called_once_with("groq","new-model")
            self.app.button(key="open_settings").click().run()
            self.assertFalse(self.app.checkbox(key="confirm_settings").value)
            self.assertEqual(self.backend.provider,"test-provider")
            self.app.run();self.assertEqual(save.call_count,1)

    def test_generated_download_preparation_does_not_submit_or_repeat(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        with patch.object(self.backend,"generated_files",create=True,return_value=[{"id":"fixture-id","path":"export.txt"}]),patch.object(self.backend,"generated_file",create=True,return_value={"name":"export.txt","data":b"export","mime":"application/octet-stream"}) as prepare:
            self.app.run();prepare.assert_not_called()
            self.app.button(key="prepare_generated_fixture-id").click().run()
            self.assertFalse(self.app.exception)
            prepare.assert_called_once_with("default","fixture-id")
            self.app.run();self.assertEqual(prepare.call_count,1)
            self.assertEqual(self.backend.calls,[])

    def test_landing_hides_old_default_content_until_opened(self):
        self.backend.catalog.append("default","Old question","Old answer")
        self.app.run()
        self.assertFalse(any(row.value=="Old answer" for row in self.app.markdown))
        self.assertFalse(any(row.value=="Conversations" for row in self.app.header))
        self.app.button(key="open_chat_default").click().run()
        self.assertTrue(any(row.value=="Old answer" for row in self.app.markdown))
        self.assertFalse(self.app.title)

    def test_cowork_is_explicit_placeholder_and_provider_has_no_model_label(self):
        self.app.run()
        self.assertEqual(self.app.selectbox(key="browser_provider").value,"test-provider")
        self.app.segmented_control(key="work_mode").set_value("Cowork").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Project connection is planned" in row.value for row in self.app.info))
        self.app.run()
        self.assertTrue(self.app.chat_input[0].disabled)
        self.app.segmented_control(key="work_mode").set_value("Chat").run()
        self.app.run();self.assertFalse(self.app.chat_input[0].disabled)

    def test_provider_configuration_error_is_actionable(self):
        from agent.provider_errors import ProviderError
        self.app.run()
        with patch.object(self.backend,"submit",side_effect=ProviderError("groq","CONFIGURATION","Set GROQ_API_KEY locally in .env and restart.",attempts=0)):
            self.app.chat_input[0].set_value("hello").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("GROQ_API_KEY" in row.value and "CONFIGURATION" in row.value for row in self.app.error))

    def test_all_provider_failure_categories_allow_next_request(self):
        # This test exercises a deliberately selected saved General chat.
        self.app.session_state["active_chat"]="default"
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False
        from agent.provider_errors import ProviderError
        self.app.run()
        categories=("AUTHENTICATION","RATE_LIMIT","QUOTA_EXHAUSTED","RESPONSE_TIMEOUT","TOOL_OUTPUT","OUTPUT_LIMIT")
        for provider in ("groq","openrouter","ollama","gemini"):
            for category in categories:
                with self.subTest(provider=provider,category=category):
                    error=ProviderError(provider,category,"Safe recovery instruction.")
                    before=len(self.backend.turns("default"))
                    with patch.object(self.backend,"submit",side_effect=error) as submit:
                        self.app.chat_input[0].set_value("failure fixture").run()
                    submit.assert_called_once()
                    self.assertFalse(self.app.exception)
                    self.assertTrue(any(provider.upper() in row.value and category in row.value for row in self.app.error))
                    self.assertEqual(len(self.backend.turns("default")),before)
                    self.assertEqual(self.app.session_state["active_chat"],"default")
                    self.app.chat_input[0].set_value("recovery fixture").run()
                    self.assertFalse(self.app.exception)
                    self.assertEqual(len(self.backend.turns("default")),before+1)
                    self.assertFalse(self.app.error)

    def test_unknown_exception_is_not_exposed(self):
        self.app.run()
        with patch.object(self.backend,"submit",side_effect=RuntimeError("secret-private-token")):
            self.app.chat_input[0].set_value("hello").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertFalse(any("secret-private-token" in row.value for row in self.app.error))

if __name__=="__main__":unittest.main()
