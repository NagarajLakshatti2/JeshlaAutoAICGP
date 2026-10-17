import unittest, importlib.util, tempfile, json, copy
from pathlib import Path
import sys
import os
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.jira import test_case_agent as m
def req():return {'project_key':'T','epic':{'key':'T-1'},'story':{'key':'T-2'},'test_cases':[{'summary':'Independent checkbox clearing','preconditions':['Page open'],'steps':[{'action':'Clear one','expected':'Other stays checked'}],'acceptance_criteria':['Independent state']}]}
class G:
 cloud_id='cloud'
 def __init__(self):self.items=[{'key':'T-1','type':'Epic','parent':None,'fields':{'summary':'Selection controls','status':{'name':'Open'}}},{'key':'T-2','type':'Story','parent':'T-1','fields':{'summary':'Choose skills','status':{'name':'Open'}}}];self.writes=[];self.fail=False
 async def discover_create_schema(self):pass
 async def search(self,q):return copy.deepcopy(self.items)
 async def matches(self,p,k,t,parent,kind):return any(i['key']==k and i['type']==t and (not parent or i['parent']==parent) for i in self.items)
 def create_arguments(self,p,t,n,parent):return {'summary':n['summary'],'type':t,'parent':parent}
 async def create(self,a):
  self.writes.append(a)
  if self.fail:raise TimeoutError()
  k='T-'+str(len(self.items)+1);self.items.append({'key':k,**a,'fields':{'summary':a['summary'],'status':{'name':'Open'}}});return k
class T(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  # Enable writes only to the in-memory G fixture, never the real Jira gateway.
  env=patch.dict(os.environ, {"JIRA_ALLOW_CREATE":"true"})
  env.start(); self.addCleanup(env.stop)

 async def test_disabled_creation_blocks_fake_gateway(self):
  g=G(); p=await m.prepare_plan(g,req())
  with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"JIRA_ALLOW_CREATE":"false"}):
   with self.assertRaisesRegex(m.Blocked,"JIRA_ALLOW_CREATE"):
    await m.apply_plan(g,p,p["approval_sha256"],Path(d)/"r.json")
  self.assertFalse(g.writes)

 async def test_default(self):
  g=G();p=await m.prepare_plan(g,req());self.assertEqual([n['action'] for n in p['nodes']],['reuse','reuse','create']);self.assertFalse(p['blocked']);self.assertFalse(g.writes)
 async def test_missing_parent_disabled(self):
  r=req();r['epic']={'summary':'New payment capability'};p=await m.prepare_plan(G(),r);self.assertTrue(p['blocked'])
 async def test_wrong_parent(self):
  g=G();g.items[1]['parent']='T-99';self.assertTrue((await m.prepare_plan(g,req()))['blocked'])
 async def test_approved_hierarchy(self):
  r=req();r.update(allow_create_epic=True,allow_create_story=True,epic={'summary':'Payment capability'},story={'summary':'Card authentication'})
  g=G();p=await m.prepare_plan(g,r);self.assertFalse(p['blocked'])
  with tempfile.TemporaryDirectory() as d:await m.apply_plan(g,p,p['approval_sha256'],Path(d)/'r.json')
  self.assertEqual([x['parent'] for x in g.writes],[None,'T-3','T-4'])
 async def test_exact_duplicate_review(self):
  g=G();g.items.append({'key':'T-3','type':'Sub-task','parent':'T-2','fields':{'summary':req()['test_cases'][0]['summary'],'status':{'name':'AUTOMATED'}}});p=await m.prepare_plan(g,req());self.assertTrue(p['blocked']);self.assertFalse(g.writes)
 async def test_explicit_duplicate_reuse(self):
  g=G();r=req();r['test_cases'][0]['key']='T-3';g.items.append({'key':'T-3','type':'Sub-task','parent':'T-2','fields':{'summary':r['test_cases'][0]['summary'],'status':{'name':'AUTOMATED'}}});p=await m.prepare_plan(g,r)
  with tempfile.TemporaryDirectory() as d:await m.apply_plan(g,p,p['approval_sha256'],Path(d)/'r.json')
  self.assertFalse(g.writes)
 async def test_wrong_confirmation(self):
  g=G();p=await m.prepare_plan(g,req())
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(m.Blocked):await m.apply_plan(g,p,'wrong',Path(d)/'r.json')
  self.assertFalse(g.writes)
 async def test_tampering(self):
  g=G();p=await m.prepare_plan(g,req());p['nodes'][-1]['summary']='Tampered'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(m.Blocked):await m.apply_plan(g,p,p['approval_sha256'],Path(d)/'r.json')
  self.assertFalse(g.writes)
 async def test_status_change(self):
  g=G();p=await m.prepare_plan(g,req());g.items[0]['fields']['status']['name']='Closed'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(m.Blocked):await m.apply_plan(g,p,p['approval_sha256'],Path(d)/'r.json')
  self.assertFalse(g.writes)
 async def test_unknown_no_retry(self):
  g=G();p=await m.prepare_plan(g,req());g.fail=True
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json'
   with self.assertRaises(TimeoutError):await m.apply_plan(g,p,p['approval_sha256'],f)
   self.assertEqual(json.loads(f.read_text())['actions'][-1]['status'],'unknown_remote_outcome')
   with self.assertRaises(m.Blocked):await m.apply_plan(g,p,p['approval_sha256'],f)
  self.assertEqual(len(g.writes),1)
 async def test_repeat_success(self):
  g=G();p=await m.prepare_plan(g,req())
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json';await m.apply_plan(g,p,p['approval_sha256'],f);await m.apply_plan(g,p,p['approval_sha256'],f)
  self.assertEqual(len(g.writes),1)
 async def test_string_flag(self):
  r=req();r['allow_create_epic']='true'
  with self.assertRaises(m.Blocked):m.validate_request(r)
 async def test_override_parent(self):
  r=req();r['test_cases'][0]['additional_fields']={'parent':'T-99'}
  with self.assertRaises(m.Blocked):m.validate_request(r)
 async def test_similar_duplicate(self):
  g=G();g.items.append({'key':'T-9','type':'Sub-task','parent':'T-2','fields':{'summary':'Independent checkbox clearing UI','status':{'name':'Open'}}});self.assertTrue((await m.prepare_plan(g,req()))['blocked'])
if __name__ == '__main__':
 unittest.main()
