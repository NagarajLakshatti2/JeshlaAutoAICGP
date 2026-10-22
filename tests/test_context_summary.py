import json
import unittest
from unittest.mock import Mock
from agent.context_summary import compact_context

class SummaryTests(unittest.TestCase):
    def history(self):
        return "".join("\nUser: topic "+str(i)+" "+"x"*700+"\nAssistant: answer "+str(i) for i in range(20))

    def test_short_history_skips_model(self):
        model=Mock()
        self.assertEqual(compact_context("old","short",model),("old","short",False))
        model.assert_not_called()

    def test_long_history_keeps_recent_complete_turns(self):
        raw=json.dumps({"facts":["User uses Java"],"decisions":["Study inheritance"],"open_questions":[]})
        model=Mock(return_value=raw)
        summary,recent,changed=compact_context("prior summary",self.history(),model)
        self.assertTrue(changed);self.assertTrue(recent.startswith("\nUser: "))
        self.assertIn("topic 19",recent)
        payload=json.loads(model.call_args.args[0][1]["content"])
        self.assertEqual(payload["prior_summary"],"prior summary")
        self.assertNotIn("topic 19",payload["older_turns"])
        self.assertEqual(json.loads(summary)["facts"],["User uses Java"])

    def test_invalid_summaries_rejected(self):
        for raw in ['not json','[]','{}',json.dumps({"facts":"wrong","decisions":[],"open_questions":[]}),json.dumps({"facts":["x"*301],"decisions":[],"open_questions":[]})]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                compact_context("old",self.history(),Mock(return_value=raw))

    def test_model_failure_propagates_to_preserving_caller(self):
        with self.assertRaises(RuntimeError):compact_context("old",self.history(),Mock(side_effect=RuntimeError("unavailable")))

    def test_single_oversized_turn_not_split(self):
        model=Mock()
        history="\nUser: "+"x"*17000
        self.assertEqual(compact_context("old",history,model),("old",history,False))
        model.assert_not_called()

    def test_cli_summary_failure_pauses_next_turn(self):
        import argparse, ast, hashlib, os, re, tempfile, time
        from pathlib import Path
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest.mock import patch
        source=(Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8")
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in {"main","session_config","restore_session"}]
        saved={}
        graph=SimpleNamespace(
            get_state=lambda config:SimpleNamespace(values=dict(saved)),
            invoke=lambda state,config:{"final_answer":"answer","answer":"answer","route":"direct"},
            update_state=lambda config,values:saved.update(values),
        )
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"AI_SUMMARY_MIN_TURNS":"1"}),patch("sys.argv",["agent","--session","default","--input-mode","end"]),patch("builtins.input",side_effect=["question one","END","question two","END","EXIT"]),patch("builtins.print"),patch("agent.context_summary.compact_context",side_effect=RuntimeError("failure")) as compact:
            scope={"argparse":argparse,"hashlib":hashlib,"json":json,"os":os,"re":re,"time":time,"PROJECT_ROOT":Path(folder),"LLM_PROVIDER":"groq","graph":graph,"timer":lambda label:nullcontext()}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),"summary-cli","exec"),scope)
            scope["main"]()
            self.assertEqual(compact.call_count,1)
            self.assertGreater(saved["summary_retry_at"],time.time())
            self.assertIn("question two",saved["history"])

    def test_grounding_instructions_and_untrusted_prior_are_supplied(self):
        raw=json.dumps({"facts":[],"decisions":[],"open_questions":[]})
        model=Mock(return_value=raw)
        prior=json.dumps({"facts":[],"decisions":[],"open_questions":["Unsupported browser question?"]})
        compact_context(prior,self.history(),model)
        messages=model.call_args.args[0]
        policy=messages[0]["content"]
        self.assertIn("assistant-reported",policy)
        self.assertIn("actual tool evidence",policy)
        self.assertIn("still unanswered",policy)
        self.assertIn("omit them when no supporting turn",policy)
        self.assertEqual(json.loads(json.loads(messages[1]["content"])["prior_summary"])["open_questions"],[])

    def test_unsupported_prior_question_cannot_be_saved_again(self):
        raw=json.dumps({"facts":[],"decisions":[],"open_questions":["Which browser versions?"]})
        with self.assertRaisesRegex(ValueError,"Unverified prior-summary"):
            compact_context(raw,self.history(),Mock(return_value=raw))

    def test_prior_question_with_available_history_support_is_allowed(self):
        raw=json.dumps({"facts":[],"decisions":[],"open_questions":["Which browser versions?"]})
        history="\nUser: Which browser versions?\nAssistant: Undecided."+self.history()
        self.assertTrue(compact_context(raw,history,Mock(return_value=raw))[2])

    def test_archived_question_support_preserves_prior_question(self):
        raw=json.dumps({"facts":[],"decisions":[],"open_questions":["Where is the report?"]})
        lookup=Mock(return_value=[{"turn_id":1,"question":"Where is the report?","answer":"Undecided."}])
        model=Mock(return_value=raw)
        self.assertTrue(compact_context(raw,self.history(),model,question_lookup=lookup)[2])
        payload=json.loads(model.call_args.args[0][1]["content"])
        self.assertEqual(payload["archived_question_evidence"][0]["turn_id"],1)

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):compact_context("","",Mock(),threshold=3000,keep=4000)

if __name__=="__main__":unittest.main()


class RecentConversationContextTests(unittest.TestCase):
    def test_structured_exchange_preserves_literal_role_labels_inside_text(self):
        from agent.runtime.summaries import recent_conversation_context
        exchange={"question":"Question", "answer":"Code sample\nUser: literal\nAssistant: literal"}
        context=recent_conversation_context("old context", exchange)
        self.assertEqual(context["previous_exchange"], exchange)
        self.assertEqual(context["recent_conversation"], "old context")

    def test_older_context_remains_bounded_and_marked(self):
        from agent.runtime.summaries import recent_conversation_context
        older="older " * 2000
        context=recent_conversation_context(older + "\nUser: Q\nAssistant: A")
        self.assertEqual(context["previous_exchange"], {"question":"Q", "answer":"A"})
        self.assertEqual(context["recent_conversation"], older[-4000:])
        self.assertTrue(context["recent_conversation_truncated"])

    def test_legacy_empty_or_invalid_structured_context_remains_usable(self):
        from agent.runtime.summaries import recent_conversation_context
        for value in (None, {}, {"question":1, "answer":False}):
            context=recent_conversation_context("User: Q\nAssistant: A", value)
            self.assertEqual(context["previous_exchange"], {"question":"Q", "answer":"A"})
        self.assertEqual(recent_conversation_context("")["previous_exchange"], {})


class SummaryScheduleTests(unittest.TestCase):
    def test_short_followup_defers_summary_until_interval(self):
        from agent.runtime.summaries import summary_due
        self.assertFalse(summary_due("x"*12000,2))
        self.assertTrue(summary_due("x"*12000,3))

    def test_history_pressure_overrides_interval(self):
        from agent.runtime.summaries import summary_due
        self.assertTrue(summary_due("x"*16001,1,minimum_turns=10))

    def test_interval_is_configurable_and_validated(self):
        from agent.runtime.summaries import summary_due
        self.assertTrue(summary_due("small",1,minimum_turns=1))
        for value in (0,101,False,"3"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                summary_due("",0,minimum_turns=value)
