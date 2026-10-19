"""Stopped-writer backup rehearsal using synthetic stores only."""
import shutil,sqlite3,tempfile,unittest
from pathlib import Path
from typing import TypedDict
from unittest.mock import Mock
from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.chat_catalog import ChatCatalog
from agent.memory.long_term_memory import LongTermMemory
from agent.local_action_receipts import LocalActionReceipts,ActionBlocked

class State(TypedDict):
    history:str
    summary:str

def graph_for(connection):
    builder=StateGraph(State);builder.add_node('echo',lambda state:state)
    builder.add_edge(START,'echo');builder.add_edge('echo',END)
    return builder.compile(checkpointer=SqliteSaver(connection))

class BackupRecoveryTests(unittest.TestCase):
    def test_stopped_copy_restores_facts_chats_summaries_and_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir();out=source/'outputs';out.mkdir()
            with LongTermMemory(out/'facts.sqlite3') as store:
                store.save('u','p','format','PDF',source_kind='user_statement')
                store.save('other','p','format','CSV')
            chats=ChatCatalog(out/'chats.sqlite3','u','p');chats.register('default')
            chats.append('default','fixture question','fixture answer')
            config={'configurable':{'thread_id':'fixture'}}
            conn=sqlite3.connect(source/'agent_memory.db',check_same_thread=False)
            try:graph_for(conn).invoke({'history':'fixture history','summary':'fixture summary'},config)
            finally:conn.close()
            ledger=LocalActionReceipts(out/'actions.sqlite3')
            args={'relative_path':'created.txt','content':'fixture'}
            def create(**kw):
                (source/kw['relative_path']).write_text(kw['content']);return {'created':True}
            ledger.run(source,'create_file',args,create,lambda *a:True,'complete')
            uncertain={'relative_path':'uncertain.txt','content':'fixture'}
            def interrupted(**kw):raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):ledger.run(source,'create_file',uncertain,interrupted,lambda *a:True,'uncertain')
            restored=Path(folder)/'restored';shutil.copytree(source,restored)
            for db in restored.rglob('*'):
                if db.suffix in ('.db','.sqlite3'):
                    conn=sqlite3.connect(db)
                    try:self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                    finally:conn.close()
            with LongTermMemory(restored/'outputs/facts.sqlite3') as store:
                self.assertEqual(store.get('u','p','format'),'PDF')
                self.assertEqual(store.get('other','p','format'),'CSV')
            self.assertEqual(ChatCatalog(restored/'outputs/chats.sqlite3','u','p').transcript('default')[0]['answer'],'fixture answer')
            conn=sqlite3.connect(restored/'agent_memory.db',check_same_thread=False)
            try:self.assertEqual(graph_for(conn).get_state(config).values,{'history':'fixture history','summary':'fixture summary'})
            finally:conn.close()
            restored_ledger=LocalActionReceipts(restored/'outputs/actions.sqlite3');handler=Mock();approve=Mock()
            self.assertEqual(restored_ledger.run(source,'create_file',args,handler,approve,'complete'),{'created':True})
            with self.assertRaises(ActionBlocked):restored_ledger.run(source,'create_file',uncertain,handler,approve,'uncertain')
            with self.assertRaises(ActionBlocked):restored_ledger.run(restored,'create_file',args,handler,approve,'complete')
            handler.assert_not_called();approve.assert_not_called()
            self.assertFalse((restored/'uncertain.txt').exists())
