"""Exercise the real project loop against temporary sources and fake decisions."""
import ast
from contextlib import nullcontext,redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from agent.project_budget import project_input_budget,project_user_context


class BudgetTests(unittest.TestCase):
    def test_defaults_and_legacy_override(self):
        with patch.dict(os.environ,{},clear=True):self.assertEqual(project_input_budget(),32000)
        with patch.dict(os.environ,{"AI_MAX_CONVERSATION_CHARS":"12000"},clear=True):self.assertEqual(project_input_budget(),12000)
        with patch.dict(os.environ,{"AI_MAX_CONVERSATION_CHARS":"12000","AI_PROJECT_MAX_CONVERSATION_CHARS":"40000"},clear=True):self.assertEqual(project_input_budget(),40000)

    def test_task_is_not_truncated_by_context_selection(self):
        state={"question":"Exact requested task", "summary":"s"*10000,"history":"h"*10000,"memory_context":"m"*10000}
        context=project_user_context(state,"root",32000)
        self.assertIn(state["question"],context)
        self.assertLess(len(context),4300)

    def project_function(self,root):
        source=(Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8")
        tree=ast.parse(source)
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {"extract_requested_paths","project_node"}]
        scope={"re":re,"json":json,"os":os,"PROJECT_ROOT":root,"AgentState":dict,
               "_SOURCE_EXTENSION":r"(?:gradle\.kts|java|py|xml|gradle|kts|tsx|ts|jsx|js|feature)",
               "timed":lambda name:lambda fn:fn,"timer":lambda name:nullcontext()}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),"isolated-project-loop","exec"),scope)
        return scope["project_node"]

    def test_full_305_line_read_survives_restored_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"build.gradle").write_text("dependency configuration content\n"*305,encoding="utf-8")
            decisions=[{"action":"list_files","arguments":{"limit":50}},
                       {"action":"read_file","arguments":{"relative_path":"build.gradle","max_lines":100}},
                       {"action":"read_file","arguments":{"relative_path":"build.gradle","start_line":101,"max_lines":205}},
                       {"action":"finish","answer":"Reviewed the requested configuration."}]
            with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.call_project_decision",side_effect=[json.dumps(d) for d in decisions]) as model,redirect_stdout(io.StringIO()):
                result=self.project_function(root)({"question":"Read build.gradle and project structure. Do not modify any files.","project_root":str(root),"history":"h"*3000,"summary":"s"*5000,"memory_context":"m"*4000})
            self.assertNotIn("Task status: incomplete",result["answer"])
            self.assertIn("lines 101",result["answer"])
            self.assertEqual(model.call_count,4)

    def test_explicit_small_budget_still_stops_honestly(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.dict(os.environ,{"AI_PROJECT_MAX_CONVERSATION_CHARS":"4000"},clear=True),patch("agent.project_decisions.call_project_decision") as model,redirect_stdout(io.StringIO()):
                result=self.project_function(root)({"question":"Read build.gradle " + "x"*5000,"project_root":str(root)})
            self.assertIn("Task status: incomplete",result["answer"])
            self.assertIn("AI_PROJECT_MAX_CONVERSATION_CHARS",result["answer"])
            model.assert_not_called()

    def test_external_project_excludes_unbound_identity_and_summary(self):
        state={"question":"Review this external repository", "summary":"AgentProjectOldSummary", "memory_context":"project_name: AgentProjectPrivate", "history":"User: read the build"}
        with tempfile.TemporaryDirectory() as directory:
            context=project_user_context(state,directory,32000)
        self.assertNotIn("AgentProjectPrivate",context)
        self.assertNotIn("AgentProjectOldSummary",context)
        self.assertIn("User: read the build",context)
        self.assertIn("Inspection target folder:",context)
        self.assertEqual(state["memory_context"],"project_name: AgentProjectPrivate")

    def test_latest_exchange_preserves_inspection_head_and_tail(self):
        exchange={"question":"Approved exact local action sample-receipt",
                  "answer":"Stored action returned. Receipt: sample-receipt\n\n"+json.dumps({
                      "fields":[{"label":"Text Input","id":"text-input","disabled":False,"read_only":False},
                                {"label":"Other metadata","placeholder":"x"*7000}],
                      "inspection_file":"test-output/agent-web/sample/inspection.json"})}
        state={"question":"Use the saved inspection only; identify the editable field.",
               "history":"older context"*1000+"\nUser: "+exchange["question"]+"\nAssistant: "+exchange["answer"],
               "previous_exchange":exchange}
        context=project_user_context(state,"root",32000)
        self.assertIn("Text Input",context)
        self.assertIn("text-input",context)
        self.assertIn("test-output/agent-web/sample/inspection.json",context)
        self.assertIn(json.dumps(exchange,ensure_ascii=False),context)
        self.assertEqual(context.count("sample-receipt"),2)
        self.assertTrue(context.endswith(state["question"]))

    def test_prior_exchange_does_not_replace_a_new_requested_source_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"build.gradle").write_text("current source",encoding="utf-8")
            state={"question":"Read build.gradle and explain its current contents.","project_root":str(root),
                   "previous_exchange":{"question":"Earlier read","answer":"Old source result"}}
            with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.call_project_decision",
                    return_value=json.dumps({"action":"finish","answer":"Old source result"})),redirect_stdout(io.StringIO()):
                result=self.project_function(root)(state)
            self.assertEqual(result["task_status"],"incomplete")
            self.assertIn("Inspect requested files",result["answer"])

    def test_agent_repository_keeps_its_context(self):
        from agent import project_budget
        root=project_budget.APPLICATION_ROOT
        state={"question":"Review agent", "memory_context":"project_name: LocalAgent", "summary":"AgentSummary"}
        context=project_user_context(state,root,32000)
        self.assertIn("LocalAgent",context)
        self.assertIn("AgentSummary",context)

    def test_browser_approval_is_waiting_not_an_incomplete_execution(self):
        from agent.actions.receipts import ActionPending
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            decision={'action':'create_file','arguments':{'relative_path':'note.txt','content':'draft'}}
            with patch.dict(os.environ,{},clear=True),patch('agent.project_decisions.call_project_decision',return_value=json.dumps(decision)),patch('agent.local_action_receipts.LocalActionReceipts.run',side_effect=ActionPending('Action is waiting for your browser approval. Review the exact action.')),redirect_stdout(io.StringIO()):
                project=self.project_function(root)
                project.__globals__['approve_local_action']=lambda *args: False
                result=project({'question':'Create note.txt after approval','project_root':str(root)})
            self.assertEqual(result['task_status'],'awaiting_input')
            self.assertNotIn('Task status: incomplete.',result['answer'])
            self.assertIn('awaiting approval',result['answer'])
            self.assertFalse((root/'note.txt').exists())
