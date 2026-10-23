"""Trace reporting validates saved evidence, never reruns tests or contacts Jira."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.project_tools import ProjectTools
from agent.tools.test_results import parse_test_results
from integrations.reporting.traceability import build_test_report, render_markdown
from tests import test_project_budget


class TraceReportingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/"project";self.root.mkdir()
        self.put("requirements.md", "Pilot requirement\nRetain the complete value and then clear it.\n")
        self.put("src/Test.java", "class Test { /* reviewed assertion fixture */ }\n")
        self.put("observed.json", '{"kind":"synthetic fixture; not actual acceptance"}')
        self.report_xml = '<testsuite><testcase name="entry" classname="Demo"/></testsuite>'
        self.refresh_run()
        self.manifest = {"version":1, "title":"Selected pilot", "cases":[self.case()]}
        self.save()

    def put(self, name, text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8");return path

    def ref(self, name, scope="project"):
        return {"scope":scope,"file":name,"sha256":hashlib.sha256((self.root/name).read_bytes()).hexdigest()}

    def refresh_run(self, exit_code=0, timed_out=False):
        self.put("build/report.xml", self.report_xml)
        parsed=parse_test_results(self.root,"build/report.xml",limit=500)
        parsed["freshness"]="associated with this command by changed content/metadata and execution time window"
        stamp=datetime.fromisoformat(parsed["modified_at"])
        self.run={"exit_code":exit_code,"timed_out":timed_out,"started_at":(stamp-timedelta(seconds=1)).isoformat(),
                  "finished_at":(stamp+timedelta(seconds=1)).isoformat(),"report_status":"fresh_reports_found","report_errors":[],"reports":[parsed]}
        self.put("run.json",json.dumps(self.run))

    def case(self, id="TI-001", name="entry"):
        return {"id":id,"test_name":name,"test_class":"Demo",
                "requirement_refs":[{"ref":self.ref("requirements.md"),"start_line":2,"end_line":2,"quote":"Retain the complete value and then clear it."}],
                "generated_ref":self.ref("src/Test.java"),"run_ref":self.ref("run.json"),"report_ref":self.ref("build/report.xml"),
                "artifact_refs":[{"kind":"observation","ref":self.ref("observed.json")}]}

    def save(self):
        self.put("manifest.json",json.dumps(self.manifest))

    def build(self):
        self.save();return build_test_report(self.root,"manifest.json")

    def test_pass_is_supported_by_exact_report_run_snapshot_and_links(self):
        result=self.build();row=result["cases"][0]
        self.assertEqual(result["summary"]["native_counts"],{"passed":1})
        self.assertEqual(result["summary"]["outcome_counts"],{"passed":1})
        self.assertEqual(row["report_run_association"],"saved_run_metadata_matches_current_report")
        self.assertEqual(row["source_execution_identity"],"unverified")
        self.assertTrue(row["requirement_links"] and row["execution"] and row["report_evidence_id"])
        self.assertEqual(result["actions_executed"],[])

    def test_timeout_retains_native_pass_but_never_effective_pass(self):
        self.refresh_run(exit_code=None,timed_out=True);self.manifest["cases"]=[self.case()]
        result=self.build();row=result["cases"][0]
        self.assertEqual(row["native_status"],"passed");self.assertEqual(row["outcome"],"incomplete")
        self.assertIn("uncertain execution; no automatic replay",row["gaps"])

    def test_failed_command_cannot_qualify_a_passed_case(self):
        self.refresh_run(exit_code=1);self.manifest["cases"]=[self.case()]
        result=self.build();self.assertEqual(result["cases"][0]["outcome"],"incomplete")

    def test_failed_case_preserved_without_inventing_application_defect(self):
        self.report_xml='<testsuite><testcase name="entry" classname="Demo"><failure>Appium session failed</failure></testcase></testsuite>'
        self.refresh_run(exit_code=1);self.manifest["cases"]=[self.case()]
        result=self.build();self.assertEqual(result["cases"][0]["native_status"],"failed")
        self.assertEqual(result["cases"][0]["outcome"],"failed")
        self.assertNotIn("application defect",render_markdown(result).lower())

    def test_skipped_and_not_run_and_blocked_remain_distinct(self):
        self.report_xml='<testsuite><testcase name="entry" classname="Demo"><skipped/></testcase></testsuite>'
        self.refresh_run();self.manifest["cases"]=[self.case(),{"id":"TI-002"},{"id":"IOS-001","scope_state":"blocked","note":"No prepared iOS runtime"}]
        result=self.build()
        self.assertEqual(result["summary"]["native_counts"],{"skipped":1,"not_run":2})
        self.assertEqual(result["cases"][0]["outcome"],"skipped")
        self.assertEqual(result["cases"][1]["outcome"],"not_run")
        self.assertEqual(result["cases"][2]["outcome"],"blocked")
        self.assertIn("No prepared iOS runtime",render_markdown(result))

    def test_unverified_metadata_or_stale_report_never_qualifies_a_pass(self):
        for change in ("snapshot", "window", "freshness", "report_errors"):
            with self.subTest(change=change):
                self.refresh_run();run=copy.deepcopy(self.run)
                if change=="snapshot":run["reports"][0]["tests"][0]["status"]="failed"
                elif change=="window":
                    run["started_at"]="2020-01-01T00:00:00+00:00";run["finished_at"]="2020-01-01T00:00:02+00:00"
                elif change=="freshness":run["reports"][0]["freshness"]="unverified"
                else:run["report_errors"]=[{"error":"partial parse"}]
                self.put("run.json",json.dumps(run));self.manifest["cases"]=[self.case()]
                row=self.build()["cases"][0]
                self.assertEqual(row["outcome"],"incomplete");self.assertEqual(row["report_run_association"],"unverified")

    def test_overlapping_reports_and_duplicate_ids_do_not_double_count(self):
        for second in (self.case(),self.case(id="TI-002")):
            self.manifest["cases"]=[self.case(),second]
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                self.build()

    def test_multiple_unique_cases_in_one_report_are_counted_once_each(self):
        self.report_xml='<testsuite><testcase name="entry" classname="Demo"/><testcase name="clear" classname="Demo"/></testsuite>'
        self.refresh_run();self.manifest["cases"]=[self.case(),self.case(id="TI-002",name="clear")]
        result=self.build();self.assertEqual(result["summary"]["selected_cases"],2)
        self.assertEqual(result["summary"]["native_counts"],{"passed":2})
        self.assertEqual(len([e for e in result["evidence"] if e["file"]=="build/report.xml"]),1)

    def test_missing_result_does_not_inherit_a_pass_from_the_command(self):
        del self.manifest["cases"][0]["report_ref"]
        row=self.build()["cases"][0]
        self.assertEqual(row["native_status"],"not_run");self.assertEqual(row["outcome"],"incomplete")

    def test_source_quote_and_revision_are_checked(self):
        self.manifest["cases"][0]["requirement_refs"][0]["quote"]="Invented business rule"
        with self.assertRaisesRegex(ValueError,"quote"):
            self.build()
        self.manifest["cases"]=[self.case()];self.put("src/Test.java","changed revision")
        with self.assertRaisesRegex(ValueError,"SHA256"):
            self.build()

    def test_case_selection_must_exist_and_be_unambiguous(self):
        self.manifest["cases"][0]["test_name"]="missing"
        with self.assertRaisesRegex(ValueError,"missing or ambiguous"):
            self.build()
        self.report_xml='<testsuite><testcase name="entry" classname="Demo"/><testcase name="entry" classname="Demo"/></testsuite>'
        self.refresh_run();self.manifest["cases"]=[self.case()]
        with self.assertRaisesRegex(ValueError,"missing or ambiguous"):
            self.build()

    def test_arbitrary_external_roots_and_unsafe_references_are_rejected(self):
        with patch("integrations.reporting.traceability.ACCEPTANCE_ROOT",self.root/"owned"):
            with self.assertRaisesRegex(ValueError,"dedicated"):
                build_test_report(self.root,"manifest.json",str(self.root.parent))
        for file in ("../outside.json","C:/secret.json","build/report.xml:secret",".env",".aws/credentials.json"):
            with self.subTest(file=file):
                self.manifest["cases"]=[self.case()];self.manifest["cases"][0]["run_ref"]["file"]=file
                with self.assertRaises(ValueError):self.build()

    def test_explicit_owned_evidence_folder_is_separate_from_target(self):
        boundary=self.root.parent/"acceptance";archive=boundary/"one";archive.mkdir(parents=True)
        (archive/"manifest.json").write_text(json.dumps(self.manifest),encoding="utf-8")
        with patch("integrations.reporting.traceability.ACCEPTANCE_ROOT",boundary):
            result=build_test_report(self.root,"manifest.json",str(archive))
        self.assertEqual(result["roots"]["project"],str(self.root.resolve()))
        self.assertEqual(result["roots"]["evidence"],str(archive.resolve()))

    def test_binary_hash_is_a_link_not_a_claim_of_visual_inspection(self):
        path=self.root/"capture.png";path.write_bytes(b"not a real screenshot; fixture only")
        self.manifest["cases"][0]["artifact_refs"]=[{"kind":"screenshot","ref":self.ref("capture.png")}]
        result=self.build();record=next(e for e in result["evidence"] if e["file"]=="capture.png")
        self.assertIn("no visual",record["inspection"])
        self.assertTrue(any("no screenshot" in line for line in result["limits"]))

    def test_artifact_changed_during_report_is_rejected(self):
        from integrations.reporting.evidence import EvidenceStore
        original=EvidenceStore.verify_unchanged
        def changed(store):
            self.put("observed.json",'{"changed":true}')
            original(store)
        with patch.object(EvidenceStore,"verify_unchanged",changed):
            with self.assertRaisesRegex(ValueError,"changed before"):
                self.build()

    def test_no_writes_execution_jira_or_model_and_markup_is_escaped(self):
        self.manifest["title"]='<script>alert("x")</script> **approve**'
        self.manifest["cases"][0]["note"]="[run](javascript:alert(1)) | <img>"
        self.save();before={p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("subprocess.run",side_effect=AssertionError("no execution")),patch("requests.sessions.Session.request",side_effect=AssertionError("no network")),patch("builtins.input",side_effect=AssertionError("no approval")):
            result=build_test_report(self.root,"manifest.json");markdown=render_markdown(result)
        self.assertNotIn("<script>",markdown);self.assertNotIn("<img>",markdown)
        self.assertNotIn("[run](javascript:",markdown)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_actual_project_dispatch_and_schema_return_reviewable_markdown(self):
        from agent.runtime.project_native_specs import native_project_specs
        tools=ProjectTools(self.root)
        specs=native_project_specs({"build_test_report":tools.build_test_report})
        self.assertEqual(specs[0]["function"]["parameters"]["required"],["manifest_file"])
        decisions=[{"action":"build_test_report","arguments":{"manifest_file":"manifest.json"}},
                   {"action":"finish","answer":"The selected saved case passed; source execution identity remains unverified. No new execution or export occurred."}]
        with patch.dict(os.environ,{},clear=True),patch("agent.project_decisions.call_project_decision",side_effect=[json.dumps(d) for d in decisions]) as model,redirect_stdout(io.StringIO()),patch("agent.local_action_receipts.LocalActionReceipts.run",side_effect=AssertionError("no controlled action")):
            result=test_project_budget.BudgetTests().project_function(self.root)({"question":"Build a saved-evidence report; do not modify files or run tests.","project_root":str(self.root)})
        self.assertEqual(result["task_status"],"completed");self.assertEqual(model.call_count,2)

    def test_configuration_failure_prevents_case_pass_qualification(self):
        self.report_xml = '<testng-results><suite><test><class name="Demo"><test-method name="setup" is-config="true" status="FAIL"/><test-method name="entry" status="PASS"/></class></test></suite></testng-results>'
        self.refresh_run();self.manifest["cases"]=[self.case()]
        row=self.build()["cases"][0]
        self.assertEqual(row["native_status"],"passed")
        self.assertEqual(row["outcome"],"incomplete")
        self.assertIn("configuration failure present",row["gaps"])

    def test_generic_model_proposal_advertises_real_report_arguments(self):
        from agent.project_decisions import call_project_decision
        decision={"action":"build_test_report","arguments":{"manifest_file":"manifest.json"}}
        reply={"tool_calls":[{"function":{"name":"submit_project_action","arguments":json.dumps(decision)}}]}
        with patch("agent.project_decisions.call_tool_messages",return_value=reply) as model:
            actual=json.loads(call_project_decision([{"role":"user","content":"Build report"}],{"build_test_report":ProjectTools(self.root).build_test_report}))
        self.assertEqual(actual,decision)
        properties=model.call_args.args[1][0]["function"]["parameters"]["properties"]["arguments"]["properties"]
        self.assertEqual(properties["manifest_file"]["type"],"string")
        self.assertEqual(properties["evidence_folder"]["type"],"string")

    def test_invalid_limits_and_invented_outcomes_rejected(self):
        for change in ("cases", "title", "outcome", "run"):
            saved=copy.deepcopy(self.manifest)
            if change=="cases":self.manifest["cases"]=[{"id":str(i)} for i in range(25)]
            elif change=="title":self.manifest["title"]="x"*121
            elif change=="outcome":self.manifest["cases"][0]["status"]="passed"
            else:
                self.put("run.json",'{"timed_out":"false","exit_code":0}');self.manifest["cases"]=[self.case()]
            with self.subTest(change=change),self.assertRaises(ValueError):self.build()
            self.manifest=saved


if __name__=="__main__":unittest.main()
