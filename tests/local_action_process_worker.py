"""Controlled test worker: only writes a counter inside a supplied temporary fixture."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agent.local_action_receipts import LocalActionReceipts,ActionBlocked
from tests.run_offline import offline_guard

def main():
 data=json.loads(sys.stdin.read());root=Path(data['root']).resolve()
 store=LocalActionReceipts(root/'receipts.sqlite3');counter=root/'effects.txt'
 def handler(**kwargs):
  with counter.open('a',encoding='utf-8') as f:f.write('x');f.flush();os.fsync(f.fileno())
  if data['mode']=='crash':os._exit(73)
  return {'exit_code':0,'effect_count':len(counter.read_text())}
 def approve(*args):
  if data['mode']=='reopen':raise AssertionError('Replay must not request approval or execute.')
  return True
 try:
  if data.get('browser_token'):
   from agent.browser_actions import BrowserActions
   from agent.tools.project_tools import ProjectTools
   from unittest.mock import patch
   def browser_handler(tools,**kwargs):
    if data['mode']=='reopen':raise AssertionError('Browser replay executed the handler.')
    return handler(**kwargs)
   with patch.object(ProjectTools,data['action'],browser_handler):
    result,replayed=BrowserActions(root/'receipts.sqlite3').execute('u','p','chat',data['browser_token'])
  else:
   result=store.run(root,data['action'],data['arguments'],handler,approve,receipt_id='process-receipt')
  print(json.dumps({'outcome':'completed','result':result}))
 except ActionBlocked:
  print(json.dumps({'outcome':'blocked'}))
if __name__=='__main__':
 with offline_guard():main()
