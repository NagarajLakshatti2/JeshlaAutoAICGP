"""Real SQLite checkpoint transaction crash test; no provider or user data."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER = r"""
import os,sqlite3,sys
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.chat_catalog import ChatCatalog
from agent.chat_runtime import session_turn_lock
root=Path(sys.argv[1])
class State(TypedDict):
    value:str
builder=StateGraph(State)
builder.add_node('echo',lambda state:state)
builder.add_edge(START,'echo');builder.add_edge('echo',END)
connection=sqlite3.connect(root/'checkpoints.sqlite3',check_same_thread=False)
graph=builder.compile(checkpointer=SqliteSaver(connection))
config={'configurable':{'thread_id':'crash-check'}}
if sys.argv[2]=='crash':
    graph.invoke({'value':'previous committed state'},config)
    catalog=ChatCatalog(root/'chats.sqlite3','fixture','project')
    catalog.register('default');catalog.append('default','fixture question','archived answer')
    lock=session_turn_lock(root,config);lock.__enter__()
    connection.execute('BEGIN IMMEDIATE')
    connection.execute('UPDATE checkpoints SET checkpoint=?',(b'incomplete bytes',))
    os._exit(73)
else:
    assert graph.get_state(config).values['value']=='previous committed state'
    assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    catalog=ChatCatalog(root/'chats.sqlite3','fixture','project')
    assert len(catalog.transcript('default'))==1
    with session_turn_lock(root,config):pass
    connection.close()
"""

class CheckpointCrashTests(unittest.TestCase):
    def test_uncommitted_checkpoint_rolls_back_and_archive_survives(self):
        with tempfile.TemporaryDirectory() as folder:
            for mode,expected in (('crash',73),('reopen',0)):
                run=subprocess.run([sys.executable,'-c',WORKER,folder,mode],capture_output=True,text=True,timeout=60)
                self.assertEqual(run.returncode,expected,run.stderr)

if __name__=='__main__':unittest.main()
