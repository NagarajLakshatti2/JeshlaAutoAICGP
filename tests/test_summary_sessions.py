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
    summary_turns:int
    previous_exchange:dict
    previous_response_status:dict
    execution_outcome:str
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


class CompleteExchangeRestartTests(unittest.TestCase):
    def test_full_previous_answer_survives_restart_switch_and_history_compaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); db=root/"checkpoints.sqlite3"
            catalog=ChatCatalog(root/"chats.sqlite3","u","p")
            for name in ("alpha","beta"): catalog.register(name)
            long_answer="FIRST_TOPIC\n" + "content " * 2600 + "\nLAST_TOPIC"
            seen=[]
            def build(connection):
                builder=StateGraph(State)
                def answer(state):
                    seen.append(dict(state))
                    return {"answer":long_answer if state["question"]=="Initial topic" else "Acknowledged",
                            "route":"direct","task_status":"completed"}
                builder.add_node("answer",answer)
                builder.add_edge(START,"answer");builder.add_edge("answer",END)
                return builder.compile(checkpointer=SqliteSaver(connection))
            configs={name:{"configurable":{"thread_id":name}} for name in ("alpha","beta")}
            def compact(summary,history,*args,**kwargs):
                return "compact summary", history[-2000:], True
            with patch("agent.context_summary.compact_context", side_effect=compact):
                from contextlib import closing
                with closing(sqlite3.connect(db,check_same_thread=False)) as connection:
                    run_turn(build(connection),configs["alpha"],catalog,"alpha","Initial topic",root)
                with closing(sqlite3.connect(db,check_same_thread=False)) as connection:
                    graph=build(connection)
                    run_turn(graph,configs["beta"],catalog,"beta","Different topic",root)
                    self.assertEqual(seen[-1]["previous_exchange"], {"question":"","answer":""})
                    run_turn(graph,configs["alpha"],catalog,"alpha","List previous topics",root)
            self.assertEqual(seen[-1]["previous_exchange"], {"question":"Initial topic","answer":long_answer})
            self.assertNotIn("FIRST_TOPIC", seen[-1]["history"])
            self.assertEqual(len(catalog.transcript("alpha")),2)
            self.assertEqual(len(catalog.transcript("beta")),1)


class SummaryBatchRestartTests(unittest.TestCase):
    def test_long_explanation_then_followup_skips_extra_model_and_survives_restart(self):
        from contextlib import closing
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=root/"checkpoints.sqlite3"
            catalog=ChatCatalog(root/"chats.sqlite3","u","p")
            for name in ("alpha","beta"):catalog.register(name)
            long_answer="First topic\n"+"detailed material "*700+"\nLast topic"
            seen=[]
            def build(connection):
                builder=StateGraph(State)
                def answer(state):
                    seen.append(dict(state))
                    return {"answer":long_answer if state["question"]=="Explain" else "First topic\nLast topic", "route":"direct"}
                builder.add_node("answer",answer);builder.add_edge(START,"answer");builder.add_edge("answer",END)
                return builder.compile(checkpointer=SqliteSaver(connection))
            configs={name:{"configurable":{"thread_id":name}} for name in ("alpha","beta")}
            with patch.dict(os.environ,{"AI_SUMMARY_MIN_TURNS":"3","AI_SUMMARY_THRESHOLD_CHARS":"10000","AI_RECENT_HISTORY_CHARS":"4000"}),patch("agent.summary_model.call_summary_messages",return_value=json.dumps({"facts":["assistant-reported: discussed topics"],"decisions":[],"open_questions":[]})) as model:
                with closing(sqlite3.connect(db,check_same_thread=False)) as connection:
                    first=run_turn(build(connection),configs["alpha"],catalog,"alpha","Explain",root)
                    self.assertEqual(first["summary_turns"],1);model.assert_not_called()
                with closing(sqlite3.connect(db,check_same_thread=False)) as connection:
                    graph=build(connection)
                    other=run_turn(graph,configs["beta"],catalog,"beta","Greeting",root)
                    self.assertEqual(other["summary_turns"],1)
                    second=run_turn(graph,configs["alpha"],catalog,"alpha","List topics",root)
                    self.assertEqual(second["summary_turns"],2);model.assert_not_called()
                    self.assertEqual(seen[-1]["previous_exchange"]["answer"],long_answer)
                    third=run_turn(graph,configs["alpha"],catalog,"alpha","Explain briefly",root)
                    self.assertEqual(third["summary_turns"],0)
                    self.assertEqual(model.call_count,1)
                    self.assertEqual(graph.get_state(configs["beta"]).values["summary_turns"],1)
            self.assertEqual(len(catalog.transcript("alpha")),3)
            self.assertEqual(len(catalog.transcript("beta")),1)
            self.assertEqual(catalog.transcript("alpha")[0]["answer"],long_answer)


    def test_interval_halves_summary_calls_for_long_answer_plus_followup_in_an_existing_chat(self):
        from contextlib import closing
        counts={}
        for minimum in (1,3):
            with self.subTest(interval=minimum),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);catalog=ChatCatalog(root/"chats.sqlite3","u","p");catalog.register("alpha")
                long_answer="topic details "*850
                with closing(sqlite3.connect(root/"checkpoints.sqlite3",check_same_thread=False)) as connection:
                    builder=StateGraph(State)
                    builder.add_node("answer",lambda state:{"answer":long_answer if state["question"]=="Explain" else "Topic names", "route":"direct"})
                    builder.add_edge(START,"answer");builder.add_edge("answer",END)
                    graph=builder.compile(checkpointer=SqliteSaver(connection));config={"configurable":{"thread_id":"alpha"}}
                    graph.update_state(config,{"question":"Old explanation","answer":long_answer,"history":"\nUser: Old explanation\nAssistant: "+long_answer,"summary":""})
                    data=json.dumps({"facts":["assistant-reported: discussed topics"],"decisions":[],"open_questions":[]})
                    with patch.dict(os.environ,{"AI_SUMMARY_MIN_TURNS":str(minimum),"AI_SUMMARY_THRESHOLD_CHARS":"10000","AI_RECENT_HISTORY_CHARS":"4000"}),patch("agent.summary_model.call_summary_messages",return_value=data) as model:
                        run_turn(graph,config,catalog,"alpha","Explain",root)
                        result=run_turn(graph,config,catalog,"alpha","List topics",root)
                        counts[minimum]=model.call_count
                    self.assertIn("List topics",result["history"])
                    self.assertEqual(len(catalog.transcript("alpha")),2)
        self.assertEqual(counts,{1:2,3:1})


class PreviousStatusPersistenceTests(unittest.TestCase):
    def test_restart_passes_actual_previous_failure_status_without_changing_exchange_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);database=root/"checkpoint.sqlite3"
            catalog=ChatCatalog(root/"catalog.sqlite3","u","p");catalog.register("chat")
            config={"configurable":{"thread_id":"chat"}}
            seen=[]
            def make_graph(connection):
                builder=StateGraph(State)
                def node(state):
                    seen.append(state)
                    failed=state["question"]=="Original request"
                    return {"answer":"No explanation published" if failed else "No topics to extract","route":"direct",
                        "task_status":"incomplete" if failed else "completed","execution_outcome":"blocked" if failed else "completed"}
                builder.add_node("answer",node);builder.add_edge(START,"answer");builder.add_edge("answer",END)
                return builder.compile(checkpointer=SqliteSaver(connection))
            with sqlite3.connect(database,check_same_thread=False) as connection:
                run_turn(make_graph(connection),config,catalog,"chat","Original request",root)
            connection.close()
            with sqlite3.connect(database,check_same_thread=False) as connection:
                run_turn(make_graph(connection),config,catalog,"chat","List previous answer topics",root)
            connection.close()
            self.assertEqual(seen[-1]["previous_response_status"],{"task_status":"incomplete","execution_outcome":"blocked"})
            self.assertEqual(seen[-1]["previous_exchange"],{"question":"Original request","answer":"No explanation published"})


class AttributionPreservationTests(unittest.TestCase):
    def test_rejected_new_summary_preserves_legacy_context_across_restart(self):
        from contextlib import closing
        from tests.test_summary_model import native
        import time
        legacy=json.dumps({"facts":["Legacy saved fact without a label"],"decisions":[],"open_questions":[]})
        invalid={"facts":["A new unlabelled claim"],"decisions":[],"open_questions":[]}
        history="".join("\nUser: Existing note "+str(i)+" "+"neutral "*100+"\nAssistant: Noted." for i in range(8))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);database=root/"checkpoints.sqlite3"
            catalog=ChatCatalog(root/"chats.sqlite3","u","p")
            catalog.register("alpha");catalog.register("beta")
            catalog.append("alpha","Original archived question","Original archived answer")
            config={"configurable":{"thread_id":"alpha"}};other={"configurable":{"thread_id":"beta"}}
            with closing(sqlite3.connect(database,check_same_thread=False)) as connection:
                graph=graph_for(connection)
                graph.invoke({"history":history,"summary":legacy},config)
                graph.invoke({"history":"Other chat only","summary":"other summary"},other)
                with patch.dict(os.environ,{"AI_SUMMARY_MIN_TURNS":"1","AI_SUMMARY_THRESHOLD_CHARS":"3000","AI_RECENT_HISTORY_CHARS":"2000"}),patch("agent.summary_model.call_tool_messages",return_value=native(invalid)) as model:
                    result=run_turn(graph,config,catalog,"alpha","Continue our discussion",root)
                self.assertEqual(model.call_count,2)
                self.assertEqual(result["summary"],legacy)
                self.assertIn("Existing note 0",result["history"])
                self.assertIn("Continue our discussion",result["history"])
                self.assertTrue(result["persistence_status"]["archive_saved"])
                self.assertTrue(any("Automatic summary unavailable" in notice for notice in result["notices"]))
                self.assertEqual(graph.get_state(other).values["summary"],"other summary")
            with closing(sqlite3.connect(database,check_same_thread=False)) as connection:
                graph=graph_for(connection);saved=graph.get_state(config).values
                self.assertEqual(saved["summary"],legacy)
                self.assertGreater(saved["summary_retry_at"],time.time())
                self.assertIn("Existing note 0",saved["history"])
                self.assertEqual(graph.get_state(other).values["history"],"Other chat only")
            self.assertEqual(len(catalog.transcript("alpha")),2)
            self.assertEqual(catalog.transcript("beta"),[])
