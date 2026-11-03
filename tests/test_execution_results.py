"""Readable results never execute work or promote unverified report claims."""
import copy
import json
import unittest
from unittest.mock import patch

from agent.interfaces.execution_results import execution_summary, FRESH_PREFIX
from agent.tools.project_tools import ProjectTools
from tests import test_projects as fixtures


def payload(action="run_tests_and_parse", **result):
    return {"receipt_id": "a"*32, "receipt_status": "completed", "action": action,
            "project_root": "fixture-project", "arguments": {"command": ["python", "-c", "pass"]},
            "result": {"command": ["python", "-c", "pass"], "exit_code": 0, "timed_out": False, **result}}


def report(**values):
    return {"file": "reports/TEST-demo.xml", "format": "junit-xml",
            "freshness": FRESH_PREFIX + " and execution time window",
            "overall_status": "passed", "total": 3, "passed": 3,
            "failed": 0, "skipped": 0, "incomplete": 0, **values}


class ExecutionSummaryTests(unittest.TestCase):
    def test_zero_exit_and_pass_text_do_not_invent_native_test_results(self):
        summary=execution_summary(payload("run_command", stdout="100 tests passed"))
        self.assertEqual(summary["command_status"], "Succeeded (exit 0)")
        self.assertIn("Not verified", summary["tests"])
        self.assertEqual(summary["reports"], [])
        self.assertTrue(any("does not prove" in item for item in summary["limits"]))

    def test_command_failure_and_fresh_passing_report_remain_separate(self):
        summary=execution_summary(payload(exit_code=1, reports=[report()], report_status="fresh_reports_found"))
        self.assertEqual(summary["command_status"], "Failed (exit 1)")
        self.assertEqual(summary["reports"][0]["status"], "Reported passed")
        self.assertTrue(any("unsuccessful command" in item for item in summary["limits"]))

    def test_timeout_and_uncertain_receipt_never_show_command_success(self):
        data=payload(timed_out=True, exit_code=None);data["receipt_status"]="uncertain"
        summary=execution_summary(data)
        self.assertEqual(summary["command_status"], "Timed out")
        self.assertTrue(any("do not repeat" in item for item in summary["limits"]))
        data["result"]["timed_out"]=False;data["result"]["exit_code"]=0
        self.assertEqual(execution_summary(data)["command_status"], "Uncertain")

    def test_stale_unlinked_and_inconsistent_counts_are_not_verified(self):
        for native in (report(freshness="unverified"), report(total=4), report(passed=-1),
                       report(passed="3"), report(format="unknown")):
            with self.subTest(report=native):
                summary=execution_summary(payload(reports=[native], report_status="fresh_reports_found"))
                self.assertEqual(summary["reports"][0]["status"], "Not verified")

    def test_overlapping_reports_stay_separate_and_limits_are_visible(self):
        data=payload(reports=[report(),report(file="reports/testng-results.xml",format="testng-xml",details_truncated=True)],
                     report_status="fresh_reports_found",output_truncated=True,
                     report_errors=[{"file":"reports/broken.xml","error":"fixture"}],
                     unchanged_reports_ignored=["reports/old.xml"],
                     outside_execution_window_ignored=["reports/outside.xml"], report_folder="reports")
        summary=execution_summary(data)
        self.assertEqual(len(summary["reports"]),2)
        self.assertNotIn("total",summary)
        self.assertIn("Not fully verified",summary["tests"])
        for needle in ("not added","truncated","could not be parsed","Unchanged","outside run window"):
            self.assertTrue(any(needle in item for item in summary["limits"]),needle)
        self.assertIn(("Unreadable report","reports/broken.xml"),summary["evidence"])

    def test_skipped_empty_configuration_and_failed_reports_are_distinct(self):
        for native,expected in (
            (report(total=3,passed=2,skipped=1),"Reported with skips"),
            (report(total=0,passed=0),"No test cases reported"),
            (report(configuration_failure_count=1),"Reported failures"),
            (report(passed=2,failed=1,overall_status="failed"),"Reported failures"),
            (report(passed=2,incomplete=1),"Incomplete report")):
            with self.subTest(report=native):
                result=execution_summary(payload(reports=[native],report_status="fresh_reports_found"))
                self.assertEqual(result["reports"][0]["status"],expected)


class ReceiptReadTests(unittest.TestCase):
    def setUp(self):
        fixtures.ProjectBackendTests.setUp(self)
        self.backend=self.view_a
        self.session=self.backend.create_chat("Execution")
        self.result=payload()["result"]

    def queue(self,action="run_command"):
        args={"command":["python","-c","pass"],"timeout":10}
        if action=="run_tests_and_parse":args["relative_report_folder"]="reports"
        return self.backend.actions().propose("u",self.backend.space,self.session,action,
            {"project_root":str(self.a),"action":action,"arguments":args})

    def test_reads_only_matching_owned_completed_receipt_and_preserves_transcript(self):
        token=self.queue()
        with patch.object(ProjectTools,"run_command",return_value=self.result) as run:
            self.backend.decide_action(self.session,token,True)
            before=self.backend.turns(self.session)
            for _ in range(2):
                data=self.backend.execution_result(self.session,token)
                self.assertEqual({k:v for k,v in data["result"].items() if k!="post_run_review"},self.result)
                self.assertEqual(data["result"]["post_run_review"]["version"],1)
            self.assertEqual(run.call_count,1)
        self.assertEqual(self.backend.turns(self.session),before)
        other=self.backend.create_chat("Other")
        self.assertIsNone(self.backend.execution_result(other,token))
        self.assertIsNone(self.view_b.execution_result(self.session,token))
        impostor=copy.copy(self.backend);impostor.user="other"
        self.assertIsNone(impostor.execution_result(self.session,token))
        self.assertEqual(self.invocations,[])

    def test_pending_receipt_and_tampered_identity_cannot_render_as_execution(self):
        token=self.queue()
        self.assertIsNone(self.backend.execution_result(self.session,token))
        with patch.object(ProjectTools,"run_command",return_value=self.result):
            self.backend.decide_action(self.session,token,True)
        with self.backend.actions().receipts.connect() as db:
            db.execute("UPDATE actions SET fingerprint='tampered' WHERE id=?",(token,))
        self.assertIsNone(self.backend.execution_result(self.session,token))
        self.assertIsNone(self.backend.execution_result(self.session,"not-a-token"))


class ExecutionResultUITests(unittest.TestCase):
    open_projects=fixtures.ProjectUITests.open_projects

    def setUp(self):
        fixtures.ProjectUITests.setUp(self)
        self.backend=self.base.for_project(self.pa["id"])
        self.session=self.backend.create_chat("Run summary")
        self.app.run();self.open_projects()
        self.app.button(key="choose_project_"+self.pa["id"]).click().run()
        self.app.session_state["active_chat"]=self.session
        self.app.session_state["chat_opened"]=True
        self.app.session_state["chat_draft"]=False

    def queue(self,action):
        args={"command":["python","-c","pass"],"timeout":10}
        if action=="run_tests_and_parse":args["relative_report_folder"]="reports"
        token=self.backend.actions().propose("u",self.backend.space,self.session,action,
            {"project_root":str(self.a),"action":action,"arguments":args})
        self.app.run()
        return token

    def test_fresh_results_are_readable_collapsed_and_stable_across_refresh(self):
        token=self.queue("run_tests_and_parse")
        result=payload(reports=[report()],report_status="fresh_reports_found",report_folder="reports")["result"]
        with patch.object(ProjectTools,"run_tests_and_parse",return_value=result) as run:
            self.app.button(key="approve_"+token).click().run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any("Succeeded (exit 0)" in item.value for item in self.app.success))
            self.assertTrue(any(item.value=="Reported passed" for item in self.app.markdown))
            raw=next(item for item in self.app.expander if item.label=="Raw receipt and logs")
            self.assertFalse(raw.proto.expanded)
            self.assertIn('"report_status": "fresh_reports_found"',raw.code[0].value)
            saved=self.backend.turns(self.session)
            self.assertIn("Stored action returned",saved[-1]["answer"])
            for _ in range(2):self.app.run()
            self.assertFalse(self.app.exception);self.assertEqual(run.call_count,1)
            self.assertEqual(len([item for item in self.app.markdown if item.value=="**Execution result**"]),1)
            self.assertEqual(self.backend.turns(self.session),saved)
            self.open_projects();self.app.button(key="choose_project_"+self.pb["id"]).click().run()
            self.assertFalse(any(item.value=="**Execution result**" for item in self.app.markdown))
        self.assertEqual(self.invocations,[])

    def test_failed_command_is_visible_even_when_native_report_has_passes(self):
        token=self.queue("run_tests_and_parse")
        result=payload(exit_code=1,reports=[report()],report_status="fresh_reports_found")["result"]
        with patch.object(ProjectTools,"run_tests_and_parse",return_value=result):
            self.app.button(key="approve_"+token).click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Failed (exit 1)" in item.value for item in self.app.error))
        self.assertTrue(any(item.value=="Reported passed" for item in self.app.markdown))
        self.assertTrue(any("unsuccessful command" in item.value for item in self.app.markdown))

    def test_timeout_result_survives_without_archive_and_does_not_execute_again(self):
        token=self.queue("run_command")
        result=payload("run_command",timed_out=True,exit_code=None,stdout="partial fixture")["result"]
        with patch.object(ProjectTools,"run_command",return_value=result) as run:
            self.app.button(key="approve_"+token).click().run()
            self.app.run()
            self.assertFalse(self.app.exception);self.assertEqual(run.call_count,1)
        self.assertEqual(self.backend.turns(self.session),[])
        self.assertTrue(any("Command: Timed out" in item.value for item in self.app.warning))
        self.assertEqual(len([item for item in self.app.markdown if item.value=="**Execution result**"]),1)
        self.assertEqual(self.invocations,[])

    def test_receipt_fallback_after_archive_failure_remains_visible(self):
        token=self.queue("run_command")
        with patch.object(ProjectTools,"run_command",return_value=payload("run_command")["result"]) as run:
            with patch.object(self.backend.catalog.__class__,"append",side_effect=OSError("fixture archive failure")):
                self.app.button(key="approve_"+token).click().run()
            self.app.run()
            self.assertFalse(self.app.exception);self.assertEqual(run.call_count,1)
        self.assertEqual(self.backend.turns(self.session),[])
        self.assertTrue(any("Succeeded (exit 0)" in item.value for item in self.app.success))
        self.assertTrue(any("Not verified" in item.value for item in self.app.markdown))
