"""Welcome-screen messages start new chats; saved chats require selection."""
import tempfile,unittest
from pathlib import Path
from types import MethodType
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from tests.test_streamlit_ui import FakeBackend

class LandingChatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend(self.temp.name)
        self.backend.catalog.append("default","Earlier question","Earlier General chat answer")
        st.cache_resource.clear();self.addCleanup(st.cache_resource.clear)
        for target in ("agent.browser_backend.make_browser_backend","agent.browser_activity.log_browser_event"):
            mock=patch(target,return_value=self.backend if target.endswith("make_browser_backend") else None)
            mock.start();self.addCleanup(mock.stop)
        self.app=self.new_app()

    def new_app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=15)

    def test_welcome_is_an_unsaved_draft(self):
        self.app.run();self.assertFalse(self.app.exception)
        self.assertNotEqual(self.app.session_state["active_chat"],"default")
        self.assertIsNone(self.backend.get_chat(self.app.session_state["active_chat"]))
        self.assertEqual(len(self.backend.list_chats()),1)
        self.assertEqual(self.backend.calls,[])
        self.assertFalse(any(row.value=="Earlier General chat answer" for row in self.app.markdown))

    def test_first_message_creates_chat_and_followup_reuses_it(self):
        self.app.run();self.app.chat_input[0].set_value("Hi").run()
        self.assertFalse(self.app.exception)
        chat=self.app.session_state["active_chat"]
        self.assertNotEqual(chat,"default")
        self.assertEqual(self.backend.get_chat(chat)["title"],"Hi")
        self.assertEqual(self.backend.calls,[(chat,"Hi")])
        self.assertEqual(len(self.backend.turns("default")),1)
        self.assertFalse(any(row.value=="Earlier General chat answer" for row in self.app.markdown))
        self.app.chat_input[0].set_value("Explain Java inheritance").run();self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[(chat,"Hi"),(chat,"Explain Java inheritance")])
        self.assertEqual(len(self.backend.list_chats()),2)

    def test_general_chat_opens_only_when_selected(self):
        self.app.run();self.app.button(key="open_chat_default").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["active_chat"],"default")
        self.assertTrue(any(row.value=="Earlier General chat answer" for row in self.app.markdown))
        self.app.chat_input[0].set_value("Continue here").run()
        self.assertEqual(self.backend.calls,[("default","Continue here")])
        self.assertEqual(len(self.backend.list_chats()),1)

    def test_new_chat_clicks_do_not_save_empty_conversations(self):
        self.app.run()
        for _ in range(2):self.app.button(key="create_new_chat").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.backend.list_chats()),1)
        self.app.chat_input[0].set_value("Plan my automation project").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.backend.list_chats()),2)
        self.assertEqual(self.backend.get_chat(self.app.session_state["active_chat"])["title"],"Plan my automation project")

    def test_draft_uploads_move_only_to_its_new_chat(self):
        self.app.run();draft=self.app.session_state["active_chat"]
        document={"id":"fixture","name":"draft.txt","text":"Fresh uploaded evidence","truncated":False}
        existing={"id":"older","name":"old.txt","text":"General-only document","truncated":False}
        self.app.session_state["attachment_collections"]={draft:[document],"default":[existing]}
        self.app.run();self.app.chat_input[0].set_value("Summarize this file").run()
        self.assertFalse(self.app.exception)
        chat=self.app.session_state["active_chat"]
        self.assertNotEqual(chat,"default")
        self.assertIn("Fresh uploaded evidence",self.backend.calls[-1][1])
        self.assertNotIn("General-only document",self.backend.calls[-1][1])
        self.assertEqual(self.app.session_state["attachment_collections"][chat],[document])
        self.assertEqual(self.app.session_state["attachment_collections"]["default"],[existing])
        self.assertNotIn(draft,self.app.session_state["attachment_collections"])

    def test_failure_retry_does_not_create_another_chat(self):
        from agent.provider_errors import ProviderError
        self.app.run()
        with patch.object(self.backend,"submit",side_effect=ProviderError("groq","RATE_LIMIT","Fixture rate limit")):
            self.app.chat_input[0].set_value("Explain interfaces").run()
        chat=self.app.session_state["active_chat"]
        self.assertNotEqual(chat,"default");self.assertFalse(self.app.exception)
        self.app.chat_input[0].set_value("Explain interfaces again").run()
        self.assertEqual(self.app.session_state["active_chat"],chat)
        self.assertEqual(len(self.backend.list_chats()),2)
        self.assertEqual(len(self.backend.turns("default")),1)

    def test_fresh_browser_session_starts_fresh_draft(self):
        self.app.run();self.app.chat_input[0].set_value("First browser question").run()
        first=self.app.session_state["active_chat"]
        fresh=self.new_app();fresh.run()
        self.assertNotEqual(fresh.session_state["active_chat"],first)
        self.assertNotEqual(fresh.session_state["active_chat"],"default")
        fresh.chat_input[0].set_value("Second browser question").run()
        self.assertFalse(fresh.exception)
        self.assertNotEqual(fresh.session_state["active_chat"],first)
        self.assertEqual(len(self.backend.list_chats()),3)

    def test_memory_edit_from_welcome_has_valid_chat_scope(self):
        from agent.interfaces.browser import BrowserBackend
        self.backend.edit_memory=MethodType(BrowserBackend.edit_memory,self.backend)
        self.app.run();self.app.button(key="open_memory").click().run()
        self.app.text_input(key="memory_key").set_value("report_format")
        self.app.text_area(key="memory_edit_value").set_value("PDF")
        self.app.checkbox(key="memory_confirm").check()
        next(button for button in self.app.button if button.label=="Apply memory change").click().run()
        self.assertFalse(self.app.exception);self.assertFalse(self.app.error)
        chat=self.app.session_state["active_chat"]
        self.assertNotEqual(chat,"default")
        self.assertEqual(self.backend.calls,[(chat,"REMEMBER report_format = PDF")])
        self.assertEqual(len(self.backend.turns("default")),1)

    def test_titles_use_one_to_one_hundred_characters_and_keep_full_message(self):
        self.app.run()
        for message in ("H","x"*100,"Long message "+"word "*40):
            self.app.button(key="create_new_chat").click().run()
            self.app.chat_input[0].set_value(message).run()
            self.assertFalse(self.app.exception)
            chat=self.app.session_state["active_chat"]
            self.assertEqual(self.backend.get_chat(chat)["title"]," ".join(message.split())[:100])
            self.assertEqual(self.backend.turns(chat)[0]["question"],message)
            self.assertTrue(any(button.label==self.backend.get_chat(chat)["title"] for button in self.app.button))
        self.assertEqual(len(self.backend.turns("default")),1)

    def test_saved_first_message_is_visible_after_a_title_filter(self):
        self.app.run()
        self.app.text_input(key="chat_title_filter").set_value("unrelated title").run()
        self.app.chat_input[0].set_value("Hi").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any(button.label=="Hi" for button in self.app.button))
        self.assertEqual(self.app.session_state["chat_title_filter"],"")
        self.assertEqual(len(self.backend.turns("default")),1)
