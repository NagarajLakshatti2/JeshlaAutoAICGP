"""Offline real-checkpointer tests for named conversations and shared memory."""
import ast
import hashlib
import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.memory.long_term_memory import LongTermMemory

source=(Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8")
fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=="session_config")
scope={"re":re,"json":json,"hashlib":hashlib}
exec(compile(ast.Module(body=[fn],type_ignores=[]),"session-config","exec"),scope)
config=scope["session_config"]

class State(TypedDict):
    history:str

def build(conn):
    builder=StateGraph(State)
    builder.add_node("echo",lambda state:state)
    builder.add_edge(START,"echo");builder.add_edge("echo",END)
    return builder.compile(checkpointer=SqliteSaver(conn))

class SessionTests(unittest.TestCase):
    def test_existing_default_is_preserved(self):
        self.assertEqual(config("default","local-user","project")["configurable"]["thread_id"],"main-agent-session")

    def test_session_user_and_space_are_distinct(self):
        rows=[config("a","u","p"),config("b","u","p"),config("a","v","p"),config("a","u","q")]
        self.assertEqual(len({row["configurable"]["thread_id"] for row in rows}),4)

    def test_invalid_names(self):
        for name in ["", "../../file", "a b", "x"*65]:
            with self.assertRaises(ValueError):config(name,"u","p")

    def test_checkpoint_history_survives_restart_and_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"checkpoints.sqlite3"
            a=config("a","u","p");b=config("b","u","p")
            with sqlite3.connect(path,check_same_thread=False) as conn:
                graph=build(conn)
                graph.invoke({"history":"session A"},a)
                self.assertFalse(graph.get_state(b).values)
                graph.invoke({"history":"session B"},b)
                self.assertEqual(graph.get_state(a).values["history"],"session A")
            conn.close()
            with sqlite3.connect(path,check_same_thread=False) as reopened:
                graph=build(reopened)
                self.assertEqual(graph.get_state(a).values["history"],"session A")
                self.assertEqual(graph.get_state(b).values["history"],"session B")
            reopened.close()

    def test_memory_shared_by_scope_not_session(self):
        with LongTermMemory(":memory:") as memory:
            memory.save("u","p","name","JeshlaAutoAI")
            self.assertEqual(memory.get("u","p","name"),"JeshlaAutoAI")
            self.assertIsNone(memory.get("u","another-project","name"))
            self.assertIsNone(memory.get("another-user","p","name"))

if __name__=="__main__":unittest.main()
