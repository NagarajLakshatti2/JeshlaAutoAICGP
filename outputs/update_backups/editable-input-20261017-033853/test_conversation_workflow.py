"""Offline regression checks: no LLM, network, OAuth or Jira writes."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.jira import test_case_agent as tc
from agent.langgraph import jira_workflow_node as wf

CASE = {"summary": "Selection coverage", "gherkin": "Scenario: Select\n Given an unselected skill\n When it is selected\n Then it is selected\n\nScenario: Deselect\n Given a selected skill\n When it is deselected\n Then it is unselected", "preconditions": ["Skills available"], "steps": [{"action": "Select a skill", "expected": "Selected"}], "acceptance_criteria": ["Independent selection"]}
STORY = {"key": "QAP-7", "fields": {"summary": "Skills", "description": "Users independently select and deselect skills.", "parent": {"key": "QAP-6"}, "status": {"name": "Ready for QA"}, "issuetype": {"name": "Story", "subtask": False}}}
EPIC = {"key": "QAP-6", "fields": {"summary": "Selection", "status": {"name": "Backlog"}, "issuetype": {"name": "Epic", "subtask": False}}}
SOURCE = {"story": STORY, "epic": EPIC, "subtasks": []}
REQUEST = {"project_key": "QAP", "epic": {"key": "QAP-6"}, "story": {"key": "QAP-7"}, "test_cases": [CASE]}

class Gateway:
    session = None
    cloud_id = "mock-cloud"
    async def matches(self, project, key, type_name, parent, kind):
        return (key, kind) in {("QAP-6", "epic"), ("QAP-7", "story")}
    async def search(self, query):
        return [] if "parent =" in query else deepcopy([EPIC, STORY])
    async def discover_create_schema(self):
        pass
    def create_arguments(self, *args):
        return {}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for mod in (wf, tc):
            p = patch.object(mod, "APP_ROOT", self.root); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, {"JIRA_PROJECT_KEY": "QAP", "JIRA_SITE_URL": "https://test.invalid", "AI_PROJECT_ROOT": str(self.root), "JIRA_ALLOW_CREATE": "false"}); p.start(); self.addCleanup(p.stop)
        self.store = wf.Store()
        self.client = types.ModuleType("integrations.jira.jira_mcp_client")
        async def get_issue(session, cloud, key, fields=None):
            return deepcopy(STORY if key == "QAP-7" else EPIC)
        self.client.get_jira_issue = AsyncMock(side_effect=get_issue)
        @asynccontextmanager
        async def jira_session():
            yield None
        self.client.jira_session = jira_session
        self.client.get_cloud_id = AsyncMock(return_value="mock-cloud")
        p=patch.dict(sys.modules, {self.client.__name__: self.client});p.start();self.addCleanup(p.stop)
        p=patch.object(wf,"JiraGateway",lambda *args: Gateway());p.start();self.addCleanup(p.stop)

    def plan(self):
        return asyncio.run(tc.prepare_plan(Gateway(), REQUEST, check_create_schema=False))

    def state(self):
        return {"status":"awaiting_approval", "plan":self.plan(), "request":deepcopy(REQUEST), "story_source":deepcopy(SOURCE), "source_sha256":tc.fingerprint(SOURCE), "brief":"Read QAP-7 and propose test cases"}

    def test_followup_routes(self):
        for q in ["yes", "continue", "no", "next", "Generate Gherkin subtasks for QAP-7"]:
            self.assertTrue(wf.workflow_intent(q), q)

    def test_continue_never_applies(self):
        self.store.write(self.state())
        with patch.object(wf, "approve_connected", AsyncMock()) as apply:
            self.assertIn("does not approve", wf.handle("continue"))
            apply.assert_not_called()

    def test_yes_binds_exact_saved_proposal(self):
        state=self.state(); self.store.write(state)
        with patch.object(wf,"approve_connected",AsyncMock(return_value="approved")) as approve:
            self.assertEqual(wf.handle("yes"),"approved")
            self.assertEqual(approve.call_args.args[2],state["plan"]["approval_sha256"])

    def test_yes_without_plan(self):
        self.assertIn("no pending",wf.handle("yes"))

    def test_false_flag_blocks_apply(self):
        with self.assertRaisesRegex(tc.Blocked,"JIRA_ALLOW_CREATE"):
            asyncio.run(wf.approve_connected(self.store,self.state(),self.plan()["approval_sha256"]))

    def test_uncertain_receipt_survives_cancel(self):
        receipt=self.root / "outputs/jira_creation/old.receipt.json"
        tc.save(receipt,{"status":"stopped_needs_review"})
        self.store.write(self.state()); wf.handle("no")
        self.assertTrue(receipt.exists())
        with patch.dict(os.environ,{"JIRA_ALLOW_CREATE":"true"}):
            with self.assertRaisesRegex(tc.Blocked,"reconciliation"):
                asyncio.run(wf.approve_connected(self.store,self.state(),self.plan()["approval_sha256"]))

    def test_old_block_allows_new_draft(self):
        self.store.write({"status":"needs_review","journal":"old.receipt.json"})
        with patch.object(wf,"plan_connected",AsyncMock(return_value="new draft")) as draft:
            self.assertEqual(wf.handle("Read QAP-7 and propose Gherkin subtasks"),"new draft")
            self.assertEqual(draft.call_args.args[1]["status"],"draft")
        self.assertTrue(list((self.store.folder / "history").glob("*.json")))

    def test_story_gate_and_epic_status(self):
        source=asyncio.run(wf.read_story_source(Gateway(),"QAP-7"))
        self.assertEqual(source["epic"]["fields"]["status"]["name"],"Backlog")
        bad=deepcopy(STORY); bad["fields"]["status"]["name"]="Backlog"
        self.client.get_jira_issue=AsyncMock(return_value=bad)
        with self.assertRaisesRegex(tc.Blocked,"not Ready for QA"):
            asyncio.run(wf.read_story_source(Gateway(),"QAP-7"))

    def test_multiple_cases_and_scenarios(self):
        other=deepcopy(CASE); other["summary"]="Another coverage group"
        result,_=wf.build_request({"epic":{"key":"QAP-6"},"story":{"key":"QAP-7"},"test_cases":[CASE,other]},"QAP",{"epic":[{"key":"QAP-6","summary":"Selection"}],"story":[{"key":"QAP-7","summary":"Skills"}]})
        self.assertEqual(len(result["test_cases"]),2)
        self.assertIn("Scenario: Deselect",tc.description(result["test_cases"][0],True))

    def test_incomplete_gherkin_rejected(self):
        req=deepcopy(REQUEST); req["test_cases"][0]["gherkin"]="Scenario: Broken\nGiven x"
        with self.assertRaisesRegex(tc.Blocked,"Given, When and Then"):
            tc.validate_request(req)

    def test_changed_requirements_invalidates_approval(self):
        changed=deepcopy(SOURCE);changed["story"]["fields"]["description"]="Changed"
        with patch.dict(os.environ,{"JIRA_ALLOW_CREATE":"true"}), patch.object(wf,"read_story_source",AsyncMock(return_value=changed)), patch.object(wf,"apply_plan",AsyncMock()) as apply:
            with self.assertRaisesRegex(tc.Blocked,"changed after your review"):
                asyncio.run(wf.approve_connected(self.store,self.state(),self.plan()["approval_sha256"]))
            apply.assert_not_called()

    def test_schema_not_needed_for_draft(self):
        gateway=Gateway();gateway.discover_create_schema=AsyncMock(side_effect=AssertionError("Must not discover write tools for draft"))
        self.assertFalse(asyncio.run(tc.prepare_plan(gateway,REQUEST,check_create_schema=False))["blocked"])

    def test_run_qa_waits_for_approval(self):
        with patch.object(wf,"run_qa",return_value="test outcome") as run:
            self.assertIn("Run this now?",wf.handle("RUN QA QAP-3"));run.assert_not_called()
            self.assertIn("Run this now?",wf.handle("continue"));run.assert_not_called()
            self.assertEqual(wf.handle("yes"),"test outcome");run.assert_called_once()
            wf.handle("yes");run.assert_called_once()

    def test_new_story_draft_receives_requirements(self):
        llm=types.ModuleType("agent.llm_client")
        calls=[]
        def model(messages,**kwargs):
            calls.append(messages)
            return json.dumps({"test_cases":[CASE],"assumptions":[]})
        llm.call_llm_messages=model
        with patch.dict(sys.modules,{"agent.llm_client":llm}):
            output=asyncio.run(wf.plan_connected(self.store,{"status":"draft"},"Read QAP-7 and propose Gherkin subtasks"))
        self.assertIn("Scenario: Deselect",output)
        self.assertIn("Users independently select",calls[0][1]["content"])
        self.assertEqual(self.store.read()["request"]["story"]["key"],"QAP-7")

    def test_failed_search_prevents_generation(self):
        g=Gateway();g.search=AsyncMock(side_effect=RuntimeError("Incomplete pagination"))
        with self.assertRaisesRegex(RuntimeError,"Incomplete pagination"):
            asyncio.run(wf.read_story_source(g,"QAP-7"))

    def test_apply_checks_flag_at_boundary(self):
        with self.assertRaisesRegex(tc.Blocked,"JIRA_ALLOW_CREATE"):
            asyncio.run(tc.apply_plan(Gateway(),self.plan(),self.plan()["approval_sha256"],self.root / "receipt.json"))

    def test_approved_create_and_repeat_are_idempotent(self):
        class CreatingGateway(Gateway):
            created = False
            writes = 0
            async def search(self, query):
                rows = await super().search(query)
                if self.created and "parent =" not in query:
                    rows += [{"key":"QAP-8", "fields":{"summary":CASE["summary"]}}]
                return rows
            async def create(self, args):
                self.created=True; self.writes+=1
                return "QAP-8"
            async def matches(self, project, key, type_name, parent, kind):
                if key == "QAP-8":
                    return self.created and parent == "QAP-7" and kind == "subtask"
                return await super().matches(project,key,type_name,parent,kind)
        g=CreatingGateway(); plan=self.plan(); path=self.root / "outputs/jira_creation/new.receipt.json"
        with patch.dict(os.environ,{"JIRA_ALLOW_CREATE":"true"}):
            result=asyncio.run(tc.apply_plan(g,plan,plan["approval_sha256"],path))
            self.assertEqual(result["status"],"complete")
            self.assertEqual(result["actions"][-1]["status"],"created_verified")
            self.assertEqual(asyncio.run(tc.apply_plan(g,plan,plan["approval_sha256"],path)),result)
            self.assertEqual(g.writes,1)

    def test_unknown_write_is_not_retried(self):
        class FailingGateway(Gateway):
            writes=0
            async def create(self, args):
                self.writes+=1
                raise TimeoutError("remote response lost")
        g=FailingGateway();plan=self.plan();path=self.root / "outputs/jira_creation/new.receipt.json"
        with patch.dict(os.environ,{"JIRA_ALLOW_CREATE":"true"}):
            with self.assertRaises(TimeoutError):
                asyncio.run(tc.apply_plan(g,plan,plan["approval_sha256"],path))
            self.assertEqual(json.loads(path.read_text())["actions"][-1]["status"],"unknown_remote_outcome")
            with self.assertRaises(tc.Blocked):
                asyncio.run(tc.apply_plan(g,plan,plan["approval_sha256"],path))
            self.assertEqual(g.writes,1)

    def test_local_action_requires_explicit_yes(self):
        import ast
        script=Path(__file__).resolve().parents[1] / "agent/langgraph/langgraph_agent.py"
        tree=ast.parse(script.read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="approve_local_action")
        scope={"json":json}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(script),"exec"),scope)
        for reply, expected in [("yes",True),("no",False),("continue",False),("yes but change it",False)]:
            with patch("builtins.input",side_effect=[reply,"END"]), patch("builtins.print"):
                self.assertEqual(scope["approve_local_action"]("create_file",{"content":"draft"}),expected)

    def test_failed_revision_invalidates_old_approval(self):
        state=self.state();self.store.write(state)
        with patch.object(wf,"read_story_source",AsyncMock(side_effect=tc.Blocked("Cannot read Jira"))):
            with self.assertRaises(tc.Blocked):
                asyncio.run(wf.plan_connected(self.store,state,"Read QAP-7 and revise test cases"))
        self.assertEqual(self.store.read()["status"],"draft")
        self.assertNotIn("plan",self.store.read())
        self.assertIn("no pending",wf.handle("yes"))

if __name__ == "__main__":
    unittest.main()
