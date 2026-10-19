import sqlite3,tempfile,unittest
from pathlib import Path
from typing import TypedDict
from unittest.mock import Mock,patch
from langgraph.graph import StateGraph,START,END
from agent.runtime.graph import LazyGraph

class State(TypedDict):
    value:str

def build(checkpointer):
    builder=StateGraph(State);builder.add_node('echo',lambda state:state)
    builder.add_edge(START,'echo');builder.add_edge('echo',END)
    return builder.compile(checkpointer=checkpointer)

class GraphLifecycleTests(unittest.TestCase):
    def test_lazy_initialization_close_and_reopen_preserve_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.sqlite3';factory=Mock(side_effect=build)
            graph=LazyGraph(path,factory);self.addCleanup(graph.close)
            self.assertFalse(path.exists());factory.assert_not_called()
            config={'configurable':{'thread_id':'fixture'}}
            graph.invoke({'value':'saved'},config)
            self.assertEqual(graph.get_state(config).values['value'],'saved')
            self.assertEqual(factory.call_count,1)
            graph.close();graph.close()
            self.assertEqual(graph.get_state(config).values['value'],'saved')
            self.assertEqual(factory.call_count,2)
            graph.close()

    def test_failed_build_closes_connection_without_retaining_graph(self):
        connection=Mock();factory=Mock(side_effect=ValueError('fixture'))
        graph=LazyGraph('unused',factory)
        with patch('agent.runtime.graph.sqlite3.connect',return_value=connection):
            with self.assertRaises(ValueError):graph.get_state({})
        connection.close.assert_called_once()
        self.assertIsNone(graph._graph);self.assertIsNone(graph._connection)

    def test_concurrent_first_access_initializes_once(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as folder:
            factory=Mock(return_value=Mock());graph=LazyGraph(Path(folder)/'state.sqlite3',factory)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:graph.get_state({}),range(2)))
                self.assertEqual(factory.call_count,1)
            finally:graph.close()

    def test_console_import_and_help_do_not_open_database(self):
        import subprocess,sys
        code="""import sys,importlib
from unittest.mock import patch
from tests.run_offline import offline_guard
with offline_guard(),patch('sqlite3.connect',side_effect=AssertionError('Unexpected database initialization')):
    module=importlib.import_module('agent.langgraph.langgraph_agent')
    sys.argv=['agent','--help']
    try:module.main()
    except SystemExit as error:assert error.code==0
    else:raise AssertionError('Expected argparse help exit')
"""
        run=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr)
