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

    def test_agent_repository_keeps_its_context(self):
        from agent import project_budget
        root=Path(project_budget.__file__).resolve().parents[1]
        state={"question":"Review agent", "memory_context":"project_name: LocalAgent", "summary":"AgentSummary"}
        context=project_user_context(state,root,32000)
        self.assertIn("LocalAgent",context)
        self.assertIn("AgentSummary",context)
