"""Real checkpoint/archive persistence across summaries and chat restarts."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import TypedDict
import unittest
from unittest.mock import patch
from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.chat_catalog import ChatCatalog
from agent.chat_runtime import run_turn


class State(TypedDict,total=False):
    question:str
    answer:str
    final_answer:str
    route:str
    history:str
    summary:str
    summary_retry_at:float
    task_status:str


def graph_for(connection):
    builder=StateGraph(State)
    builder.add_node("answer",lambda state:{"answer":"Acknowledged","final_answer":"Acknowledged","route":"direct","task_status":"completed"})
    builder.add_edge(START,"answer");builder.add_edge("answer",END)
    return builder.compile(checkpointer=SqliteSaver(connection))


class SummarySessionTests(unittest.TestCase):
    def test_summary_restart_switch_and_full_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/"checkpoints.sqlite3"
            catalog=ChatCatalog(root/"chats.sqlite3","u","p")
            for name in ["alpha","beta"]:catalog.register(name)
            def summary_model(messages,**kwargs):
                payload=json.loads(messages[-1]["content"])
                label="SESSION_A" if "SESSION_A" in payload["older_turns"] else "SESSION_B"
                return json.dumps({"facts":[label],"decisions":[],"open_questions":[]})
            configs={name:{"configurable":{"thread_id":name}} for name in ["alpha","beta"]}
            with sqlite3.connect(db,check_same_thread=False) as connection:
                graph=graph_for(connection)
                with patch.dict(os.environ,{"AI_SUMMARY_THRESHOLD_CHARS":"4000","AI_RECENT_HISTORY_CHARS":"2000"}),patch("agent.summary_model.call_summary_messages",side_effect=summary_model) as model:
                    for name,label in [("alpha","SESSION_A"),("beta","SESSION_B")]:
                        for i in range(8):run_turn(graph,configs[name],catalog,name,label+" turn "+str(i)+" "+"x"*750,root)
                self.assertGreaterEqual(model.call_count,2)
            connection.close()
            with sqlite3.connect(db,check_same_thread=False) as reopened:
                graph=graph_for(reopened)
                a=graph.get_state(configs["alpha"]).values;b=graph.get_state(configs["beta"]).values
                self.assertIn("SESSION_A",a["summary"])
                self.assertNotIn("SESSION_B",a["summary"]+a["history"])
                self.assertIn("SESSION_B",b["summary"])
                self.assertNotIn("SESSION_A",b["summary"]+b["history"])
            reopened.close()
            for name,label in [("alpha","SESSION_A"),("beta","SESSION_B")]:
                turns=catalog.transcript(name)
                self.assertEqual(len(turns),8)
                self.assertEqual(turns[0]["question"],label+" turn 0 "+"x"*750)

    def test_question_evidence_is_chat_and_user_scoped_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"chats.sqlite3"
            catalog=ChatCatalog(path,"u","p")
            catalog.register("alpha");catalog.register("beta")
            catalog.append("alpha","Where is my report?","Not decided.")
            catalog.append("beta","Where is my report?","Wrong chat.")
            other=ChatCatalog(path,"other","p");other.register("alpha")
            other.append("alpha","Where is my report?","Wrong user.")
            evidence=catalog.summary_question_evidence("alpha",["Where is my report?"])
            self.assertEqual(len(evidence),1)
            self.assertEqual(evidence[0]["answer"],"Not decided.")
            self.assertEqual(catalog.summary_question_evidence("alpha",["Invented question?"]),[])
            self.assertEqual(catalog.summary_question_evidence("alpha",["Where is my report?"],max_chars=1),[])
