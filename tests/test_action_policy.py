import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from agent.local_action_receipts import LocalActionReceipts,ActionBlocked,ActionDeclined
from agent.tool_policy import CONTROLLED_PROJECT_ACTIONS,READ_ONLY_PROJECT_ACTIONS,PROJECT_ACTIONS
from agent.tools.project_tools import ProjectTools

ROOT=Path(__file__).resolve().parents[1]
def arguments(action):
 return {
  'create_file':{'relative_path':'target.txt','content':'fixture'},
  'replace_text':{'relative_path':'target.txt','old_text':'old','new_text':'new'},
  'run_python_file':{'relative_path':'fixture.py','timeout':1},
  'run_command':{'command':['python','-c','print("fixture")'],'timeout':1},
  'run_tests_and_parse':{'command':['python','-c','print("fixture")'],'relative_report_folder':'reports','timeout':1},
 }[action]
def prepare(root):
 (root/'fixture.py').write_text('print("fixture")',encoding='utf-8')
 (root/'target.txt').write_text('old',encoding='utf-8')

class PolicyMatrixTests(unittest.TestCase):
 def test_every_core_project_tool_is_classified_and_implemented(self):
  self.assertFalse(CONTROLLED_PROJECT_ACTIONS&READ_ONLY_PROJECT_ACTIONS)
  self.assertEqual(len(PROJECT_ACTIONS),11)
  for name in PROJECT_ACTIONS:self.assertTrue(callable(getattr(ProjectTools,name)))
  from agent.conversation import TOOL_SPECS
  exposed={item['function']['name'] for item in TOOL_SPECS}
  self.assertFalse(exposed&CONTROLLED_PROJECT_ACTIONS)
 def test_all_controlled_kinds_require_approval_and_return_saved_receipt(self):
  for action in CONTROLLED_PROJECT_ACTIONS:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root);store=LocalActionReceipts(root/'r.sqlite3');handler=Mock(return_value={'effect':'once'})
    with self.assertRaises(ActionDeclined):store.run(root,action,arguments(action),handler,lambda *a:False,'declined')
    handler.assert_not_called()
    first=store.run(root,action,arguments(action),handler,lambda *a:True,'approved')
    again=LocalActionReceipts(root/'r.sqlite3').run(root,action,arguments(action),handler,Mock(side_effect=AssertionError('must not reapprove')),'approved')
    self.assertEqual(first,again);self.assertEqual(handler.call_count,1)
 def test_all_controlled_kinds_preserve_uncertain_outcome_after_cancel(self):
  for action in CONTROLLED_PROJECT_ACTIONS:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root);store=LocalActionReceipts(root/'r.sqlite3');handler=Mock(side_effect=KeyboardInterrupt())
    with self.assertRaises(KeyboardInterrupt):store.run(root,action,arguments(action),handler,lambda *a:True,'cancelled')
    with self.assertRaises(ActionBlocked):LocalActionReceipts(root/'r.sqlite3').run(root,action,arguments(action),handler,lambda *a:True,'fresh-token')
    self.assertEqual(handler.call_count,1)
 def test_file_read_write_and_report_paths_cannot_escape_root(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/'project';root.mkdir();outside=Path(folder)/'outside.txt';outside.write_text('unchanged');tools=ProjectTools(root)
   operations=[lambda:tools.read_file('../outside.txt'),lambda:tools.create_file('../new.txt','x'),lambda:tools.replace_text('../outside.txt','unchanged','bad'),lambda:tools.parse_test_results('../outside.xml'),lambda:tools.list_files(relative_folder='..')]
   for operation in operations:
    with self.assertRaises((ValueError,FileNotFoundError)):operation()
   self.assertEqual(outside.read_text(),'unchanged');self.assertFalse((root.parent/'new.txt').exists())
 def test_credentials_and_unregistered_commands_are_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'.env').write_text('fixture-not-a-key');tools=ProjectTools(root)
   for operation in [lambda:tools.read_file('.env'),lambda:tools.replace_text('.env','fixture','changed'),lambda:tools.create_file('.env.secret','x'),lambda:tools.run_command(['powershell','-Command','anything'])]:
    with patch('agent.tools.project_tools.subprocess.run') as run:
     with self.assertRaises(ValueError):operation()
     run.assert_not_called()
 def test_real_python_script_and_command_replay_does_not_execute_again(self):
  for action in ['run_python_file','run_command']:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root);tools=ProjectTools(root);store=LocalActionReceipts(root/'r.sqlite3');handler=Mock(wraps=getattr(tools,action));args=arguments(action);args['timeout']=10
    result=store.run(root,action,args,handler,lambda *a:True,'real-python')
    self.assertEqual(result['exit_code'],0);self.assertIn('fixture',result['stdout'])
    again=LocalActionReceipts(root/'r.sqlite3').run(root,action,args,handler,lambda *a:False,'real-python')
    self.assertEqual(again,result);self.assertEqual(handler.call_count,1)

 def test_browser_dispatch_requires_decision_for_every_controlled_kind(self):
  from agent.browser_actions import BrowserActions
  for action in CONTROLLED_PROJECT_ACTIONS:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root);store=BrowserActions(root/'r.sqlite3');args=arguments(action)
    if action=='create_file':args['relative_path']='new.txt'
    proposal={'project_root':str(root),'action':action,'arguments':args}
    declined=store.propose('u','p','chat',action,proposal);store.decline('u','p','chat',declined)
    approved=store.propose('u','p','chat',action,proposal)
    with patch.object(ProjectTools,action,return_value={'effect':'once'}) as handler:
     with self.assertRaises(ActionBlocked):store.execute('u','p','chat',declined)
     handler.assert_not_called()
     result,replayed=store.execute('u','p','chat',approved)
     again,replayed2=store.execute('u','p','chat',approved)
     self.assertFalse(replayed);self.assertTrue(replayed2);self.assertEqual(result,again);self.assertEqual(handler.call_count,1)
 def test_unclassified_or_duplicate_conversation_tool_never_reaches_model(self):
  from agent import conversation
  unknown={'type':'function','function':{'name':'unclassified_write','parameters':{'type':'object'}}}
  for specs in [conversation.TOOL_SPECS+[unknown],conversation.TOOL_SPECS+[conversation.TOOL_SPECS[0]]]:
   with tempfile.TemporaryDirectory() as folder,patch.object(conversation,'TOOL_SPECS',specs):
    model=Mock()
    with self.assertRaises(ValueError):conversation.answer_question({'question':'Inspect files'},model=model,project_root=folder,document_search=Mock())
    model.assert_not_called()

class FreshProcessReceiptTests(unittest.TestCase):
 def worker(self,root,action,mode):
  payload={'root':str(root),'action':action,'arguments':arguments(action),'mode':mode}
  return subprocess.run([sys.executable,str(ROOT/'tests/local_action_process_worker.py')],input=json.dumps(payload),capture_output=True,text=True,timeout=20,cwd=ROOT,shell=False)
 def test_all_action_kinds_return_completed_receipt_in_new_process(self):
  for action in CONTROLLED_PROJECT_ACTIONS:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root)
    first=self.worker(root,action,'complete');self.assertEqual(first.returncode,0,first.stderr)
    second=self.worker(root,action,'reopen');self.assertEqual(second.returncode,0,second.stderr)
    self.assertEqual(json.loads(second.stdout.splitlines()[-1])['outcome'],'completed')
    self.assertEqual((root/'effects.txt').read_text(),'x')
 def test_hard_process_exit_blocks_all_action_kinds_without_reexecution(self):
  for action in CONTROLLED_PROJECT_ACTIONS:
   with self.subTest(action=action),tempfile.TemporaryDirectory() as folder:
    root=Path(folder);prepare(root)
    first=self.worker(root,action,'crash');self.assertEqual(first.returncode,73,first.stderr)
    second=self.worker(root,action,'reopen');self.assertEqual(second.returncode,0,second.stderr)
    self.assertEqual(json.loads(second.stdout.splitlines()[-1])['outcome'],'blocked')
    self.assertEqual((root/'effects.txt').read_text(),'x')

class BrowserFreshProcessTests(unittest.TestCase):
 def worker(self,root,token,mode):
  payload={'root':str(root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'fixture'},'mode':mode,'browser_token':token}
  return subprocess.run([sys.executable,str(ROOT/'tests/local_action_process_worker.py')],input=json.dumps(payload),capture_output=True,text=True,timeout=20,cwd=ROOT,shell=False)
 def test_completed_and_declined_browser_proposals_survive_new_process(self):
  from agent.browser_actions import BrowserActions
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);store=BrowserActions(root/'receipts.sqlite3')
   proposal={'project_root':str(root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'fixture'}}
   token=store.propose('u','p','chat','create_file',proposal);store.execute('u','p','chat',token)
   before=(root/'note.txt').stat().st_mtime_ns
   replay=self.worker(root,token,'reopen');self.assertEqual(replay.returncode,0,replay.stderr)
   self.assertEqual(json.loads(replay.stdout.splitlines()[-1])['outcome'],'completed')
   self.assertEqual((root/'note.txt').stat().st_mtime_ns,before)
   proposal['arguments']['relative_path']='declined.txt';declined=store.propose('u','p','chat','create_file',proposal);store.decline('u','p','chat',declined)
   blocked=self.worker(root,declined,'reopen');self.assertEqual(blocked.returncode,0,blocked.stderr)
   self.assertEqual(json.loads(blocked.stdout.splitlines()[-1])['outcome'],'blocked');self.assertFalse((root/'declined.txt').exists())
 def test_browser_hard_exit_after_effect_blocks_restart(self):
  from agent.browser_actions import BrowserActions
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);store=BrowserActions(root/'receipts.sqlite3')
   token=store.propose('u','p','chat','create_file',{'project_root':str(root),'action':'create_file','arguments':{'relative_path':'note.txt','content':'fixture'}})
   crashed=self.worker(root,token,'crash');self.assertEqual(crashed.returncode,73,crashed.stderr)
   replay=self.worker(root,token,'reopen');self.assertEqual(replay.returncode,0,replay.stderr)
   self.assertEqual(json.loads(replay.stdout.splitlines()[-1])['outcome'],'blocked')
   self.assertEqual((root/'effects.txt').read_text(),'x')

class ReceiptPersistenceFailureTests(unittest.TestCase):
 def test_failed_completion_and_cleanup_writes_leave_running_claim(self):
  import sqlite3
  from contextlib import contextmanager
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);store=LocalActionReceipts(root/'r.sqlite3');original=store.connect;calls=[];handler=Mock(return_value={'created':True})
   @contextmanager
   def failing_connection():
    calls.append(1)
    if len(calls)>=4:raise sqlite3.OperationalError('Synthetic receipt-write failure')
    with original() as db:yield db
   with patch.object(store,'connect',failing_connection):
    with self.assertRaises(sqlite3.OperationalError):store.run(root,'create_file',{'relative_path':'note.txt','content':'fixture'},handler,lambda *a:True,'saved-running')
   self.assertEqual(store.get('saved-running')['status'],'running')
   with self.assertRaises(ActionBlocked):LocalActionReceipts(root/'r.sqlite3').run(root,'create_file',{'relative_path':'note.txt','content':'fixture'},handler,lambda *a:True,'new-token')
   self.assertEqual(handler.call_count,1)
