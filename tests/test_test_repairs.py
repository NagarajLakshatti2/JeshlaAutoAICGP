"""Bounded repair workflow tested only with synthetic temporary projects."""
from contextlib import redirect_stdout
import copy
from datetime import datetime,timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.actions.browser import BrowserActions
from agent.actions.receipts import ActionBlocked, ActionDeclined, LocalActionReceipts
from agent.tools.project_tools import ProjectTools
from agent.tools.test_repairs import validate_plan
from tests.repair_fixtures import make_plan, put, real_runner
from tests import test_project_budget


class RepairHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.tools=ProjectTools(self.root)
        self.prepared=make_plan(self.root)
        self.plan=self.prepared["plan"]

    def request(self):
        plan=self.plan;change=plan["replacement"]
        return {"relative_path":"reports/TEST-demo.xml","case_name":"entry","case_class":"Demo","run_file":"baseline.json",
                "source_file":change["file"],"old_text":change["old_text"],"new_text":change["new_text"],
                "diagnosis":plan["diagnosis"]["hypothesis"],
                "requirements":[{"relative_path":"requirements.md","start_line":1,"max_lines":1}],**plan["rerun"]}

    def apply(self):
        store=LocalActionReceipts(self.root/"receipts.sqlite3")
        return store.run(self.root,"apply_test_repair",{"plan":self.plan},self.tools.apply_test_repair,
                         lambda *args:True,receipt_id="repair")

    def passing_run(self, **overrides):
        self.apply()
        before=validate_plan(self.tools,self.plan,"after")
        put(self.root,"reports/TEST-demo.xml",'<testsuite><testcase name="entry" classname="Demo"/></testsuite>')
        parsed=self.tools.parse_test_results("reports/TEST-demo.xml")
        parsed["freshness"]="associated with this command by changed content/metadata and execution time window"
        stamp=datetime.fromisoformat(parsed["modified_at"])
        run={**self.plan["rerun"],"exit_code":0,"timed_out":False,"report_status":"fresh_reports_found",
             "reports":[parsed],"report_errors":[],"started_at":(stamp-timedelta(seconds=1)).isoformat(),
             "finished_at":(stamp+timedelta(seconds=1)).isoformat(),"repair_plan_id":self.plan["id"],
             "repair_source":{"before":before,"after":before,"unchanged":True},**overrides}
        put(self.root,"rerun.json",json.dumps(run))
        return run

    def test_planning_is_read_only_bounded_and_not_approval(self):
        before={p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("subprocess.run",side_effect=AssertionError("no command")),patch("requests.sessions.Session.request",side_effect=AssertionError("no network")):
            prepared=self.tools.prepare_test_repair(self.request())
        self.assertEqual(prepared["actions_executed"],[])
        self.assertEqual(prepared["plan"],self.plan)
        self.assertEqual(self.plan["diagnosis"]["root_cause"],"unconfirmed")
        self.assertIn("-    return a - b",self.plan["replacement"]["diff"])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertLess(len(json.dumps(prepared)),12000)

    def test_missing_requirements_unknown_timeout_or_stale_baseline_rejected(self):
        request=self.request()
        for requirements in ([],[{"relative_path":"missing.md","start_line":1,"max_lines":1}]):
            with self.subTest(requirements=requirements),self.assertRaises((ValueError,OSError)):
                self.tools.prepare_test_repair({**request,"requirements":requirements})
        original=(self.root/"baseline.json").read_text()
        for values in ({"timed_out":True,"exit_code":None},{"timed_out":False,"exit_code":None},
                       {"timed_out":False,"exit_code":1,"report_status":"no_fresh_results"}):
            put(self.root,"baseline.json",json.dumps({**json.loads(original),**values}))
            with self.assertRaises(ValueError):
                self.tools.prepare_test_repair(request)

    def test_broad_extra_or_wrong_case_commands_rejected(self):
        for command in (["gradlew","test"],["gradlew","test","--tests","Demo.*"],
                        ["gradlew","test","--tests","Demo.entry","clean"],
                        ["gradlew","test","--tests","Other.entry"],["git","push"]):
            with self.subTest(command=command),patch("subprocess.run",side_effect=AssertionError("no execution")):
                with self.assertRaises(ValueError):
                    self.tools.prepare_test_repair({**self.request(),"command":command})

    def test_assertion_removal_replacement_and_skip_addition_rejected(self):
        for original,old,new in (
            ("def f(x):\n    assert x == 5\n","assert x == 5","assert x is not None"),
            ("def f(x):\n    assert x == 5\n","assert x == 5","pass"),
            ("def f(x):\n    return x\n","return x","return x\n    skip()"),
        ):
            put(self.root,"calculator.py",original)
            with self.subTest(old=old,new=new),self.assertRaisesRegex(ValueError,"assertion|skipped"):
                self.tools.prepare_test_repair({**self.request(),"old_text":old,"new_text":new})

    def test_skip_text_inside_strings_does_not_invent_test_disabling(self):
        request={**self.request(),"new_text":'return "skip("'}
        result=self.tools.prepare_test_repair(request)
        self.assertIn('"skip("',result["plan"]["replacement"]["new_text"])
        self.assertEqual(result["plan"]["diagnosis"]["root_cause"],"unconfirmed")

    def test_bare_expected_failure_decorator_cannot_be_added(self):
        put(self.root,"calculator.py","def add(a,b):\n    return a - b\n")
        with self.assertRaisesRegex(ValueError,"skipped"):
            self.tools.prepare_test_repair({**self.request(),"old_text":"def add(a,b):","new_text":"@unittest.expectedFailure\ndef add(a,b):"})

    def test_java_assertions_keep_exact_string_values(self):
        put(self.root,"Demo.java",'class Demo { void entry() { assertEquals(actual, "a b"); } }')
        with self.assertRaisesRegex(ValueError,"assertion"):
            self.tools.prepare_test_repair({**self.request(),"source_file":"Demo.java",
                                           "old_text":'assertEquals(actual, "a b")',"new_text":'assertEquals(actual, "ab")'})

    def test_source_revision_or_requirement_change_invalidates_pending_approval(self):
        for name in ("calculator.py","requirements.md","baseline.json","reports/TEST-demo.xml"):
            with self.subTest(file=name):
                actions=BrowserActions(self.root/"browser.sqlite3")
                token=actions.propose("u","p","c","apply_test_repair",
                    {"project_root":str(self.root),"action":"apply_test_repair","arguments":{"plan":self.plan}})
                path=self.root/name;old=path.read_bytes()
                path.write_bytes(old+b"\nchanged")
                with patch.object(ProjectTools,"apply_test_repair",side_effect=AssertionError("must not execute")):
                    with self.assertRaises(ActionBlocked):
                        actions.execute("u","p","c",token)
                path.write_bytes(old)

    def test_decline_then_approve_changes_only_selected_file_and_never_reruns(self):
        actions=BrowserActions(self.root/"browser.sqlite3")
        proposal={"project_root":str(self.root),"action":"apply_test_repair","arguments":{"plan":self.plan}}
        declined=actions.propose("u","p","c","apply_test_repair",proposal)
        actions.decline("u","p","c",declined)
        self.assertIn("a - b",(self.root/"calculator.py").read_text())
        with self.assertRaises(ActionBlocked):
            actions.execute("u","p","c",declined)
        token=actions.propose("u","p","c","apply_test_repair",proposal)
        with patch.object(ProjectTools,"run_tests_and_parse",side_effect=AssertionError("no implicit run")):
            result,replay=actions.execute("u","p","c",token)
            again,replayed=actions.execute("u","p","c",token)
        self.assertFalse(replay);self.assertTrue(replayed)
        self.assertEqual(result,again);self.assertFalse(result["rerun_executed"])
        self.assertIn("a + b",(self.root/"calculator.py").read_text())

    def test_source_change_between_validation_and_replacement_is_not_applied(self):
        original=self.tools._replace_text
        def changed(*args,**kwargs):
            put(self.root,"calculator.py","# concurrent change\ndef add(a,b):\n    return a - b\n")
            return original(*args,**kwargs)
        with patch.object(self.tools,"_replace_text",side_effect=changed):
            with self.assertRaisesRegex(ValueError,"revision changed"):
                self.tools.apply_test_repair(self.plan)
        self.assertIn("a - b",(self.root/"calculator.py").read_text())

    def test_cross_project_tampered_plan_and_unapplied_rerun_rejected(self):
        for plan in ({**self.plan,"id":"0"*64},{**self.plan,"project_root":"other"}):
            with self.assertRaises(ValueError):
                validate_plan(self.tools,plan,"before")
        with self.assertRaises(ValueError):
            validate_plan(self.tools,self.plan,"after")
        actions=BrowserActions(self.root/"browser.sqlite3")
        token=actions.propose("u","p","c","apply_test_repair",
                 {"project_root":str(self.root),"action":"apply_test_repair","arguments":{"plan":self.plan}})
        with self.assertRaises(ActionBlocked):
            actions.execute("another-user","p","c",token)

    def test_matching_saved_rerun_retains_native_result_not_causal_proof(self):
        self.passing_run()
        with patch("subprocess.run",side_effect=AssertionError("read only")):
            result=self.tools.compare_test_rerun(self.plan,"rerun.json")
        self.assertEqual(result["status"],"selected_rerun_passed")
        self.assertEqual(result["root_cause"],"unconfirmed")
        self.assertEqual(result["actions_executed"],[])

    def test_rerun_timeout_exit_source_or_command_mismatch_remains_incomplete(self):
        run=self.passing_run()
        for override in ({"timed_out":True,"exit_code":None},{"exit_code":1},
                         {"command":["gradlew","test"]},{"repair_plan_id":"other"},
                         {"repair_source":{"unchanged":False}},{"report_errors":[{"error":"fixture"}]}):
            with self.subTest(override=override):
                put(self.root,"rerun.json",json.dumps({**run,**override}))
                self.assertEqual(self.tools.compare_test_rerun(self.plan,"rerun.json")["status"],"incomplete")

    def test_extra_case_never_qualifies_as_exact_focused_acceptance(self):
        run=self.passing_run()
        put(self.root,"reports/TEST-demo.xml",'<testsuite><testcase name="entry" classname="Demo"/><testcase name="other" classname="Demo"/></testsuite>')
        parsed=self.tools.parse_test_results("reports/TEST-demo.xml")
        parsed["freshness"]="associated with this command by changed content/metadata and execution time window"
        run["reports"]=[parsed]
        run["finished_at"]=datetime.fromisoformat(parsed["modified_at"]).isoformat()
        put(self.root,"rerun.json",json.dumps(run))
        result=self.tools.compare_test_rerun(self.plan,"rerun.json")
        self.assertEqual(result["status"],"incomplete")
        self.assertTrue(any("outside" in gap for gap in result["gaps"]))

    def test_native_schema_and_actual_project_loop_expose_read_only_plan(self):
        from agent.runtime.project_native_specs import native_project_specs
        specs=native_project_specs({"prepare_test_repair":self.tools.prepare_test_repair})
        self.assertEqual(specs[0]["function"]["parameters"]["required"],["request"])
        decisions=[{"action":"prepare_test_repair","arguments":{"request":self.request()}},
                   {"action":"finish","answer":"A revision-bound patch is ready for separate approval. No repair or rerun has executed."}]
        with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.call_project_decision",side_effect=[json.dumps(v) for v in decisions]) as model,redirect_stdout(io.StringIO()):
            result=test_project_budget.BudgetTests().project_function(self.root)({"question":"Prepare one repair plan using the saved evidence, without execution.","project_root":str(self.root)})
        self.assertEqual(result["task_status"],"completed",result["answer"])
        self.assertEqual(model.call_count,2)
        self.assertIn("a - b",(self.root/"calculator.py").read_text())


class BrowserRepairUITests(unittest.TestCase):
    def setUp(self):
        from tests import test_projects as fixtures
        fixtures.ProjectUITests.setUp(self)
        self.backend=self.base.for_project(self.pa["id"])
        self.session=self.backend.create_chat("Repair acceptance")
        self.plan=make_plan(self.a)["plan"]
        self.app.run()
        self.app.button(key="projects_menu").click().run()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.app.session_state["active_chat"]=self.session
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False

    def propose(self, action):
        return self.backend.actions().propose("u",self.backend.space,self.session,action,
                {"project_root":str(self.a),"action":action,"arguments":{"plan":self.plan}})

    def test_browser_keeps_separate_approvals_then_renders_selected_native_result_once(self):
        patch_token=self.propose("apply_test_repair")
        self.app.run()
        self.assertFalse(self.app.exception)
        with patch.object(ProjectTools,"run_command",side_effect=AssertionError("no automatic rerun")):
            self.app.button(key="approve_"+patch_token).click().run()
        self.assertFalse(self.app.exception)
        self.assertIn("a + b",(self.a/"calculator.py").read_text())
        run_token=self.propose("rerun_test_repair")
        self.app.run()
        def run(*args,**kwargs):
            put(self.a,"reports/TEST-demo.xml",'<testsuite><testcase name="entry" classname="Demo"/></testsuite>')
            return {"command":self.plan["rerun"]["command"],"exit_code":0,"timed_out":False,"stdout":"fixture only","stderr":""}
        with patch.object(ProjectTools,"run_command",side_effect=run) as command:
            self.app.button(key="approve_"+run_token).click().run()
            self.app.run()
            self.assertEqual(command.call_count,1)
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Succeeded (exit 0)" in item.value for item in self.app.success))
        self.assertTrue(any(item.value=="Reported passed" for item in self.app.markdown))
        data=self.backend.execution_result(self.session,run_token)
        self.assertEqual(data["result"]["repair_plan_id"],self.plan["id"])
        self.assertEqual(self.invocations,[])


class RealRepairPipelineTests(unittest.TestCase):
    def test_actual_failed_unit_case_then_separately_approved_patch_rerun_and_compare(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            real_runner(root)
            tools=ProjectTools(root)
            baseline=tools.run_tests_and_parse(["gradlew","test","--tests","Demo.entry"],"reports",20)
            self.assertEqual(baseline["exit_code"],1)
            self.assertEqual(baseline["reports"][0]["failed"],1)
            put(root,"baseline.json",json.dumps(baseline))
            plan=make_plan(root)["plan"]
            actions=BrowserActions(root/"receipts.sqlite3")
            patch_token=actions.propose("u","p","chat","apply_test_repair",
                {"project_root":str(root),"action":"apply_test_repair","arguments":{"plan":plan}})
            applied,_=actions.execute("u","p","chat",patch_token)
            self.assertFalse(applied["rerun_executed"])
            rerun_token=actions.propose("u","p","chat","rerun_test_repair",
                {"project_root":str(root),"action":"rerun_test_repair","arguments":{"plan":plan}})
            self.assertNotEqual(patch_token,rerun_token)
            result,_=actions.execute("u","p","chat",rerun_token)
            self.assertEqual(result["exit_code"],0,result)
            self.assertEqual(result["reports"][0]["passed"],1)
            put(root,"rerun.json",json.dumps(result))
            compared=tools.compare_test_rerun(plan,"rerun.json")
            self.assertEqual(compared["status"],"selected_rerun_passed",compared)
            self.assertEqual(compared["root_cause"],"unconfirmed")
            with patch.object(ProjectTools,"rerun_test_repair",side_effect=AssertionError("no replay")):
                saved,replay=actions.execute("u","p","chat",rerun_token)
            self.assertTrue(replay);self.assertEqual(saved,result)


if __name__=="__main__":
    unittest.main()
