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
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{}),patch("sys.argv",["agent","--session","default","--input-mode","end"]),patch("builtins.input",side_effect=["question one","END","question two","END","EXIT"]),patch("builtins.print"),patch("agent.context_summary.compact_context",side_effect=RuntimeError("failure")) as compact:
            scope={"argparse":argparse,"hashlib":hashlib,"json":json,"os":os,"re":re,"time":time,"PROJECT_ROOT":Path(folder),"LLM_PROVIDER":"groq","graph":graph,"timer":lambda label:nullcontext()}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),"summary-cli","exec"),scope)
            scope["main"]()
            self.assertEqual(compact.call_count,1)
            self.assertGreater(saved["summary_retry_at"],time.time())
            self.assertIn("question two",saved["history"])

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):compact_context("","",Mock(),threshold=3000,keep=4000)

if __name__=="__main__":unittest.main()
