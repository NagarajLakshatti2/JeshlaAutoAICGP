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
    def create_chat(self,title):return self.catalog.create(title)
    def get_chat(self,session):return self.catalog.get(session)
    def turns(self,session):return self.catalog.transcript(session)
    def memory(self):return '- project_name: "JeshlaAutoAI"'
    def submit(self,session,question):
        self.calls.append((session,question))
        self.catalog.append(session,question,"Test answer")
        return {"answer":"Test answer","notices":[]}

class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend(self.temp.name)
        st.cache_resource.clear()
        self.patch=patch("agent.browser_backend.make_browser_backend",return_value=self.backend)
        self.patch.start();self.addCleanup(self.patch.stop);self.addCleanup(st.cache_resource.clear)
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=10)
    def test_initial_render_without_model_call(self):
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[])
        self.assertEqual(self.app.title[0].value,"JeshlaAutoAI")
    def test_new_chat_and_multiline_message(self):
        self.app.run()
        self.app.text_input[0].set_value("Browser learning")
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        active=self.app.session_state["active_chat"]
        self.assertEqual(self.backend.get_chat(active)["title"],"Browser learning")
        self.app.chat_input[0].set_value("first line\nsecond line").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[(active,"first line\nsecond line")])
        self.app.run()
        self.assertEqual(len(self.backend.calls),1)
        self.assertTrue(any(row.value=="Test answer" for row in self.app.markdown))
    def test_memory_view_without_model(self):
        self.app.run()
        self.app.button(key="show_facts").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.backend.calls,[])
        self.assertIn("JeshlaAutoAI",self.app.session_state["saved_facts"])

if __name__=="__main__":unittest.main()
