import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from agent.browser_actions import BrowserActions
from agent.local_action_receipts import ActionBlocked,ActionPending
from agent.tools.project_tools import ProjectTools

class BrowserActionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.now=100.;self.store=BrowserActions(self.root/'actions.sqlite3',clock=lambda:self.now)
  self.proposal={'project_root':str(self.root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'draft'}}
 def propose(self):return self.store.propose('u','p','default','create_file',self.proposal)
 def test_propose_and_reopen_do_not_execute(self):
  token=self.propose();self.assertFalse((self.root/'note.txt').exists())
  again=BrowserActions(self.root/'actions.sqlite3',clock=lambda:self.now)
  self.assertEqual(again.pending('u','p','default')[0]['id'],token)
 def test_explicit_approval_executes_once_and_replay_returns_receipt(self):
  token=self.propose()
  with patch.object(ProjectTools,'create_file',autospec=True,wraps=None) as create:
   create.side_effect=lambda tools,relative_path,content:{'created':True}
   first,replayed=self.store.execute('u','p','default',token)
   second,replayed2=self.store.execute('u','p','default',token)
   self.assertFalse(replayed);self.assertTrue(replayed2);self.assertEqual(first,second);self.assertEqual(create.call_count,1)
 def test_real_create_and_decline(self):
  token=self.propose();result,replayed=self.store.execute('u','p','default',token)
  self.assertEqual((self.root/'note.txt').read_text(),'draft')
  self.proposal['arguments']['relative_path']='declined.txt';other=self.propose();self.store.decline('u','p','default',other)
  with self.assertRaises(ActionBlocked):self.store.execute('u','p','default',other)
  self.assertFalse((self.root/'declined.txt').exists())
 def test_cross_user_space_and_chat_are_rejected(self):
  token=self.propose()
  for user,space,session in [('other','p','default'),('u','other','default'),('u','p','other')]:
   self.assertEqual(self.store.pending(user,space,session),[])
   with self.assertRaises(ActionBlocked):self.store.execute(user,space,session,token)
   with self.assertRaises(ActionBlocked):self.store.decline(user,space,session,token)
  self.assertFalse((self.root/'note.txt').exists())
 def test_expiry_and_changed_target_require_new_proposal(self):
  token=self.propose();self.now+=601
  with self.assertRaises(ActionBlocked):self.store.execute('u','p','default',token)
  other=self.propose();(self.root/'note.txt').write_text('external')
  with self.assertRaises(ActionBlocked):self.store.execute('u','p','default',other)
  self.assertEqual((self.root/'note.txt').read_text(),'external')
 def test_stored_arguments_tamper_does_not_execute(self):
  token=self.propose()
  with self.store.receipts.connect() as db:db.execute("UPDATE browser_proposals SET proposal=? WHERE id=?",(json.dumps({**self.proposal,'arguments':{'relative_path':'other.txt','content':'bad'}}),token))
  with self.assertRaises(ActionBlocked):self.store.execute('u','p','default',token)
  self.assertFalse((self.root/'other.txt').exists())
 def test_execution_failure_keeps_uncertain_and_never_replays(self):
  token=self.propose()
  with patch.object(ProjectTools,'create_file',side_effect=KeyboardInterrupt()) as create:
   with self.assertRaises(KeyboardInterrupt):self.store.execute('u','p','default',token)
   with self.assertRaises(ActionBlocked):self.store.execute('u','p','default',token)
   self.assertEqual(create.call_count,1)

class BackendActionTests(unittest.TestCase):
 def test_queue_and_execute_do_not_rerun_model_or_duplicate_transcript(self):
  from agent.browser_backend import BrowserBackend
  from agent.chat_catalog import ChatCatalog
  from agent.runtime_context import approval_handler
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);backend=BrowserBackend.__new__(BrowserBackend);backend.user='u';backend.space='p';backend.provider='test'
   backend.catalog=ChatCatalog(root/'chats.sqlite3','u','p');backend.catalog.register('default')
   backend.session_config=lambda *args:{'configurable':{'thread_id':'browser-action-test'}}
   state={};backend.graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values=dict(state)),update_state=lambda config,values:state.update(values))
   proposal={'project_root':str(root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'draft'}}
   def turn(*args):
    try:approval_handler.get()('create_file',proposal)
    except ActionPending as error:return {'answer':str(error),'notices':[],'task_status':'awaiting_input'}
    self.fail('Approval was not deferred')
   with patch('agent.browser_backend.ROOT',root),patch('agent.chat_runtime.run_turn',side_effect=turn) as model:
    queued=backend.submit('default','Create note.txt');self.assertEqual(queued['task_status'],'awaiting_input')
    self.assertFalse((root/'note.txt').exists());token=backend.pending_actions('default')[0]['id']
    backend.decide_action('default',token,True);backend.decide_action('default',token,True)
    self.assertEqual(model.call_count,1);self.assertEqual(len(backend.catalog.transcript('default')),1)
    self.assertEqual((root/'note.txt').read_text(),'draft')


class ApprovedResultContextTests(unittest.TestCase):
 def backend(self,root,state):
  from agent.interfaces.browser import BrowserBackend
  from agent.storage.chats import ChatCatalog
  backend=BrowserBackend.__new__(BrowserBackend);backend.user='u';backend.space='p';backend.provider='test'
  backend.catalog=ChatCatalog(root/'chats.sqlite3','u','p');backend.catalog.register('default')
  backend.session_config=lambda session,*args:{'configurable':{'thread_id':'approved-result-'+session}}
  backend.graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values=dict(state)),update_state=lambda config,values:state.update(values))
  return backend

 def test_approval_updates_latest_published_exchange_and_next_turn(self):
  from agent.interfaces import browser
  from agent.runtime.turns import run_turn
  from agent.runtime.summaries import recent_conversation_context
  from agent.runtime.project_budget import project_user_context
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);state={'question':'Inspect the selected page','answer':'Waiting for approval.',
       'history':'older '*3000,'route':'project','task_status':'incomplete','execution_outcome':'blocked','answer_available':False}
   backend=self.backend(root,state)
   proposal={'project_root':str(root),'action':'inspect_browser_page','arguments':{'url':'https://example.com'}}
   captured={'status':'inspected','fields':[{'label':'Text Input','id':'text-input','disabled':False,'read_only':False}],
             'other':'x'*7000,'inspection_file':'test-output/agent-web/sample/inspection.json'}
   with patch.object(browser,'ROOT',root):
    token=backend.actions().propose('u','p','default','inspect_browser_page',proposal)
    with patch.object(ProjectTools,'inspect_browser_page',return_value=captured) as inspect:
     approved=backend.decide_action('default',token,True)
    self.assertEqual(inspect.call_count,1)
    self.assertEqual(state['question'],'Approved exact local action '+token)
    self.assertEqual(state['answer'],approved['answer'])
    self.assertEqual(state['execution_outcome'],'completed');self.assertTrue(state['answer_available'])
    config=backend.session_config('default');contexts=[]
    def invoke(current,config):
     context=recent_conversation_context(current['history'],current['previous_exchange'])
     contexts.append(context)
     self.assertEqual(context['previous_exchange']['answer'],approved['answer'])
     self.assertIn('Text Input',project_user_context(current,root,32000))
     return {'route':'direct','answer':'Text Input is enabled and editable.','task_status':'completed'}
    backend.graph.invoke=invoke
    with patch('agent.runtime.summaries.summary_due',return_value=False):
     result=run_turn(backend.graph,config,backend.catalog,'default','Use the saved inspection only.',root)
    self.assertIn('enabled and editable',result['answer']);self.assertEqual(len(contexts),1)
    state.update(question='New follow-up',answer=result['answer'])
    after_followup=dict(state)
    backend.decide_action('default',token,True)
    self.assertEqual(inspect.call_count,1)
    self.assertEqual(state,after_followup)
    self.assertEqual(len(backend.catalog.transcript('default')),2)

 def test_decline_and_failed_action_do_not_publish_a_successful_exchange(self):
  from agent.interfaces import browser
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);state={'question':'Original task','answer':'Pending approval','task_status':'incomplete'}
   backend=self.backend(root,state);before=dict(state)
   with patch.object(browser,'ROOT',root):
    proposal={'project_root':str(root),'action':'create_file','arguments':{'relative_path':'declined.txt','content':'draft'}}
    token=backend.actions().propose('u','p','default','create_file',proposal)
    backend.decide_action('default',token,False);self.assertEqual(state,before)
    proposal['arguments']['relative_path']='failed.txt'
    token=backend.actions().propose('u','p','default','create_file',proposal)
    with patch.object(ProjectTools,'create_file',side_effect=RuntimeError('fixture failed')):
     with self.assertRaises(RuntimeError):backend.decide_action('default',token,True)
    self.assertEqual(state,before);self.assertEqual(backend.catalog.transcript('default'),[])
