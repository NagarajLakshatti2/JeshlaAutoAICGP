import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from tests.test_streamlit_ui import FakeBackend
from agent.browser_actions import BrowserActions

class ActionBackend(FakeBackend):
 def __init__(self,folder):
  super().__init__(folder);self.root=Path(folder);self.store=BrowserActions(self.root/'actions.sqlite3');self.decisions=[]
 def propose(self):
  return self.store.propose('u','p','default','create_file',{'project_root':str(self.root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'draft'}})
 def pending_actions(self,session):return self.store.pending('u','p',session)
 def decide_action(self,session,token,approve):
  self.decisions.append(approve)
  if approve:
   result,replayed=self.store.execute('u','p',session,token)
   if not replayed:self.catalog.append(session,'Approved action','Action returned.')
   return {'answer':'Action returned.','notices':[]}
  self.store.decline('u','p',session,token);return {'answer':'Action declined.','notices':[]}

class BrowserActionUITests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.backend=ActionBackend(self.temp.name);self.token=self.backend.propose()
  st.cache_resource.clear();self.addCleanup(st.cache_resource.clear)
  self.p=patch('agent.browser_backend.make_browser_backend',return_value=self.backend);self.p.start();self.addCleanup(self.p.stop)
  self.log=patch('agent.browser_activity.log_browser_event');self.log.start();self.addCleanup(self.log.stop)
  self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'streamlit_app.py'),default_timeout=10)
  # Existing saved-chat fixtures intentionally select General chat.
  self.app.session_state["active_chat"]="default"
  self.app.session_state["chat_opened"]=True
  self.app.session_state["chat_draft"]=False
 def test_render_refresh_and_chat_switch_do_not_approve(self):
  self.app.run();self.app.run();self.assertFalse(self.app.exception)
  self.assertFalse((self.backend.root/'note.txt').exists());self.assertEqual(self.backend.decisions,[])
  self.assertTrue(any(json.loads(block.value)['project_root']==str(self.backend.root) and json.loads(block.value)['arguments']['content']=='draft' for block in self.app.code))
  other=self.backend.create_chat('Other');self.app.run();self.app.selectbox(key="chat_picker").set_value(other).run()
  self.assertFalse(any(button.label=='Approve exact action' for button in self.app.button))
 def test_explicit_approval_and_rerender_execute_once(self):
  self.app.run();self.app.button(key='approve_'+self.token).click().run();self.assertFalse(self.app.exception)
  self.assertEqual((self.backend.root/'note.txt').read_text(),'draft');self.app.run()
  self.assertEqual(self.backend.decisions,[True]);self.assertEqual(len(self.backend.turns('default')),1)
 def test_decline_has_no_file_effect(self):
  self.app.run();self.app.button(key='decline_'+self.token).click().run();self.assertFalse(self.app.exception)
  self.assertFalse((self.backend.root/'note.txt').exists());self.assertEqual(self.backend.decisions,[False])

 def test_new_message_shows_proposal_without_resubmitting_after_rerun(self):
  self.backend.store.decline('u','p','default',self.token)
  def queue(session,question):
   self.backend.propose();self.backend.catalog.append(session,question,'Review the proposed action.')
   return {'answer':'Review the proposed action.','task_status':'awaiting_input','notices':[]}
  self.app.run()
  with patch.object(self.backend,'submit',side_effect=queue) as submit:
   self.app.chat_input[0].set_value('Create a draft note').run()
   self.assertFalse(self.app.exception)
   self.assertTrue(any(button.label=='Approve exact action' for button in self.app.button))
   self.app.run();self.assertEqual(submit.call_count,1)
  self.assertFalse((self.backend.root/'note.txt').exists())
