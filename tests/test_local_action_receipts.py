import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from agent.local_action_receipts import LocalActionReceipts,ActionBlocked,ActionDeclined

class ReceiptTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.path=self.root/'receipts.sqlite3';self.store=LocalActionReceipts(self.path)
 def yes(self,*args):return True
 def write(self,relative_path,content):
  (self.root/relative_path).write_text(content);return {'file':relative_path,'created':True}
 def test_decline_never_writes_or_consumes(self):
  with self.assertRaises(ActionDeclined):self.store.run(self.root,'create_file',{'relative_path':'a.txt','content':'A'},self.write,lambda *x:False,'one')
  self.assertFalse((self.root/'a.txt').exists());self.assertIsNone(self.store.get('one'))
 def test_reopen_completed_token_returns_receipt_without_write_or_approval(self):
  args={'relative_path':'a.txt','content':'A'};handler=Mock(side_effect=self.write)
  expected=self.store.run(self.root,'create_file',args,handler,self.yes,'one')
  again=LocalActionReceipts(self.path);approve=Mock(side_effect=AssertionError('must not ask again'))
  self.assertEqual(again.run(self.root,'create_file',args,handler,approve,'one'),expected)
  self.assertEqual(handler.call_count,1)
 def test_changed_args_or_root_cannot_reuse_completed_receipt(self):
  args={'relative_path':'a.txt','content':'A'};self.store.run(self.root,'create_file',args,self.write,self.yes,'one')
  with self.assertRaises(ActionBlocked):self.store.run(self.root,'create_file',{**args,'content':'B'},self.write,self.yes,'one')
  other=self.root/'other';other.mkdir()
  with self.assertRaises(ActionBlocked):self.store.run(other,'create_file',args,self.write,self.yes,'one')
 def test_cancel_after_effect_blocks_restart_and_new_token(self):
  def interrupted(**kw):self.write(**kw);raise KeyboardInterrupt()
  args={'relative_path':'a.txt','content':'A'}
  with self.assertRaises(KeyboardInterrupt):self.store.run(self.root,'create_file',args,interrupted,self.yes,'one')
  self.assertEqual(self.store.get('one')['status'],'uncertain')
  handler=Mock();approve=Mock()
  with self.assertRaises(ActionBlocked):LocalActionReceipts(self.path).run(self.root,'create_file',args,handler,approve,'two')
  handler.assert_not_called();approve.assert_not_called()
 def test_timeout_blocks_another_execution(self):
  args={'command':['python','-c','pass'],'timeout':1};handler=Mock(return_value={'timed_out':True})
  with self.assertRaises(ActionBlocked):self.store.run(self.root,'run_command',args,handler,self.yes,'one')
  with self.assertRaises(ActionBlocked):self.store.run(self.root,'run_command',args,handler,self.yes,'two')
  self.assertEqual(handler.call_count,1)
 def test_approval_mutation_is_rejected(self):
  args={'relative_path':'a.txt','content':'A'}
  def mutate(action,proposal):proposal['arguments']['content']='B';return True
  with self.assertRaises(ActionBlocked):self.store.run(self.root,'create_file',args,self.write,mutate)
  self.assertFalse((self.root/'a.txt').exists())
 def test_target_changed_during_approval_requires_fresh_review(self):
  path=self.root/'a.txt';path.write_text('old')
  def mutate(*x):path.write_text('other');return True
  with self.assertRaises(ActionBlocked):self.store.run(self.root,'replace_text',{'relative_path':'a.txt','old_text':'old','new_text':'new'},Mock(),mutate)
  self.assertEqual(path.read_text(),'other')
 def test_same_token_concurrent_execution_runs_once(self):
  import threading
  entered=threading.Event();release=threading.Event();args={'command':['python','-c','pass']};calls=[]
  def run(**kw):calls.append(1);entered.set();release.wait(3);return {'exit_code':0}
  with ThreadPoolExecutor(max_workers=2) as pool:
   first=pool.submit(self.store.run,self.root,'run_command',args,run,self.yes,'one')
   self.assertTrue(entered.wait(2))
   try:
    with self.assertRaises(ActionBlocked):LocalActionReceipts(self.path).run(self.root,'run_command',args,run,self.yes,'one')
   finally:release.set()
   self.assertEqual(first.result()['exit_code'],0)
  self.assertEqual(len(calls),1)
 def test_outside_and_credentials_are_rejected_before_approval(self):
  approve=Mock();handler=Mock()
  for path in ['../outside.txt','.env']:
   with self.assertRaises(ActionBlocked):self.store.run(self.root,'create_file',{'relative_path':path,'content':'x'},handler,approve)
  approve.assert_not_called();handler.assert_not_called()

 def test_fresh_explicit_approval_allows_intentional_repeat_after_completion(self):
  args={'command':['python','-c','pass']};handler=Mock(return_value={'exit_code':0});approval=Mock(return_value=True)
  self.store.run(self.root,'run_command',args,handler,approval,'one')
  self.store.run(self.root,'run_command',args,handler,approval,'two')
  self.assertEqual(handler.call_count,2);self.assertEqual(approval.call_count,2)

class ProjectReceiptIntegrationTests(unittest.TestCase):
 def run_project(self,root,decisions,approval):
  import json,io
  from contextlib import redirect_stdout
  from unittest.mock import patch
  from tests.test_project_budget import BudgetTests
  node=BudgetTests().project_function(root)
  node.__globals__["approve_local_action"]=approval
  with patch("agent.project_decisions.call_project_decision",side_effect=[json.dumps(d) for d in decisions]),redirect_stdout(io.StringIO()):
   return node({"question":"Create or update the requested local note file.","project_root":str(root)})
 def test_approved_create_records_receipt_and_preserves_readback_flow(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);seen=[]
   result=self.run_project(root,[{"action":"create_file","arguments":{"relative_path":"note.txt","content":"draft"}},{"action":"read_file","arguments":{"relative_path":"note.txt"}},{"action":"finish","answer":"Created and read back note.txt."}],lambda action,proposal:seen.append(proposal) or True)
   self.assertEqual((root/'note.txt').read_text(),'draft')
   self.assertEqual(result['task_status'],'completed')
   self.assertEqual(seen[0]['project_root'],str(root.resolve()))
   db=sqlite3.connect(root/'outputs/local_actions.sqlite3')
   try:self.assertEqual(db.execute('SELECT status FROM actions').fetchone()[0],'completed')
   finally:db.close()
 def test_browser_style_decline_never_creates_file(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   result=self.run_project(root,[{"action":"create_file","arguments":{"relative_path":"note.txt","content":"draft"}}],lambda *args:False)
   self.assertEqual(result['task_status'],'incomplete');self.assertFalse((root/'note.txt').exists())
 def test_changed_target_stops_real_project_loop(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);target=root/'note.txt';target.write_text('old')
   def changed(*args):target.write_text('changed externally');return True
   result=self.run_project(root,[{"action":"read_file","arguments":{"relative_path":"note.txt"}},{"action":"replace_text","arguments":{"relative_path":"note.txt","old_text":"old","new_text":"new"}}],changed)
   self.assertEqual(result['task_status'],'incomplete');self.assertIn('Target changed',result['answer']);self.assertEqual(target.read_text(),'changed externally')
