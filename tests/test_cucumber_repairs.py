"""Synthetic Cucumber repair contracts; no target project, providers or real Gradle."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta
import io
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import quoteattr

from agent.actions.browser import BrowserActions
from agent.actions.receipts import ActionBlocked
from agent.tools.project_tools import ProjectTools
from agent.tools.test_repairs import validate_plan
from tests.repair_fixtures import make_plan, put

RUNNER = "src/test/java/runners/Demo.java"
FEATURE = "src/test/resources/features/pilot/selected.feature"
REPORT = "reports/TEST-runners.Demo.xml"
BASE_NAME = 'runScenario[2]("Selected scenario", "Selected feature")'
PASS_NAME = 'runScenario[0]("Selected scenario", "Selected feature")'
RUNNER_SOURCE = '''package runners;
import io.cucumber.testng.AbstractTestNGCucumberTests;
import io.cucumber.testng.CucumberOptions;
@CucumberOptions(features = "src/test/resources/features/pilot", glue = "steps")
public class Demo extends AbstractTestNGCucumberTests {
}
'''
FEATURE_SOURCE = '''Feature: Selected feature
  @ONE
  Scenario: Selected scenario
    Given two numbers
    Then their sum is correct

  @TWO
  Scenario: Other scenario
    Given another number
    Then its value is correct
'''
BUILD_SOURCE = '''plugins { id 'java' }
test {
    def selectedRunner = System.getProperty("test.runner", "").trim()
    useTestNG { testngOptions ->
        if (selectedRunner) {
            def xml = testngOptions.suiteXmlBuilder()
            xml.suite(name: "Selected Automation") {
                xml.test(name: "Selected Runner") {
                    xml.classes { xml.'class'(name: selectedRunner) }
                }
            }
        } else {
            testngOptions.suites('testng.xml')
        }
    }
    def cucumberTags = System.getProperty("cucumber.filter.tags")
    if (cucumberTags?.trim()) {
        systemProperty "cucumber.filter.tags", cucumberTags
    }
}
'''


class CucumberRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.tools = ProjectTools(self.root)
        put(self.root, RUNNER, RUNNER_SOURCE)
        put(self.root, FEATURE, FEATURE_SOURCE)
        put(self.root, "build.gradle", BUILD_SOURCE)
        put(self.root, "calculator.py", "def add(a, b):\n    return a - b\n")
        put(self.root, "requirements.md", "Adding two numbers returns their arithmetic sum.\n")
        put(self.root, "gradlew.bat", "@echo off\r\necho synthetic fixture only\r\n")
        if os.name != "nt":
            put(self.root, "gradlew", "#!/bin/sh\necho synthetic fixture only\n").chmod(0o755)
        self.write_report([(BASE_NAME, "runners.Demo", "failed")])
        parsed = self.tools.parse_test_results(REPORT)
        self.save_run("baseline.json", parsed, exit_code=1)
        self.command = ["gradlew", "test", "--tests", "runners.Demo.runScenario",
                        "-Dtest.runner=runners.Demo", "-Dcucumber.filter.tags=@ONE",
                        "--offline", "--no-daemon", "--console=plain", "--rerun-tasks"]

    def write_report(self, cases):
        rows = []
        for name, cls, status in cases:
            issue = "<failure>AssertionError: expected sum</failure>" if status == "failed" else "<skipped/>" if status == "skipped" else ""
            rows.append("<testcase name=" + quoteattr(name) + " classname=" + quoteattr(cls) + ">" + issue + "</testcase>")
        put(self.root, REPORT, "<testsuite>" + "".join(rows) + "</testsuite>")

    def save_run(self, filename, parsed, **extra):
        parsed = copy.deepcopy(parsed)
        parsed["freshness"] = "associated with this command by changed content/metadata and execution time window"
        stamp = datetime.fromisoformat(parsed["modified_at"])
        run = {"command":getattr(self, "command", []), "exit_code":0, "timed_out":False,
               "report_status":"fresh_reports_found", "report_errors":[], "reports":[parsed],
               "started_at":(stamp-timedelta(seconds=1)).isoformat(),
               "finished_at":(stamp+timedelta(seconds=1)).isoformat(), **extra}
        put(self.root, filename, json.dumps(run))
        return run

    def request(self, **changes):
        return {"relative_path":REPORT, "case_name":BASE_NAME, "case_class":"runners.Demo",
                "run_file":"baseline.json", "source_file":"calculator.py",
                "old_text":"return a - b", "new_text":"return a + b",
                "diagnosis":"The source subtracts where the explicit requirement expects addition.",
                "requirements":[{"relative_path":"requirements.md", "start_line":1, "max_lines":1}],
                "command":self.command, "relative_report_folder":"reports", "timeout":20,
                "cucumber":{"runner_file":RUNNER, "feature_file":FEATURE, "tag":"@ONE"}, **changes}

    def prepare(self, **changes):
        return self.tools.prepare_test_repair(self.request(**changes))["plan"]

    def passing_run(self, cases=None):
        plan = self.prepare()
        self.tools.apply_test_repair(plan)
        ref = validate_plan(self.tools, plan, "after")
        self.write_report(cases or [(PASS_NAME, "runners.Demo", "passed")])
        run = self.save_run("rerun.json", self.tools.parse_test_results(REPORT),
                            repair_plan_id=plan["id"], repair_source={"before":ref, "after":ref, "unchanged":True},
                            repair_selection={"before":plan["cucumber"], "after":plan["cucumber"], "unchanged":True})
        return plan, run

    def test_v2_planning_reads_only_and_binds_selection(self):
        before = {p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch("subprocess.run", side_effect=AssertionError("no command")), patch("requests.sessions.Session.request", side_effect=AssertionError("no network")):
            result = self.tools.prepare_test_repair(self.request())
        plan = result["plan"]
        self.assertEqual(plan["version"], 2)
        for key, value in self.request()["cucumber"].items():
            self.assertEqual(plan["cucumber"][key], value)
        self.assertEqual(result["actions_executed"], [])
        self.assertEqual(before, {p:p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertEqual(plan["diagnosis"]["root_cause"], "unconfirmed")

    def test_legacy_v1_plan_contract_is_retained(self):
        legacy = self.root / "legacy"
        plan = make_plan(legacy)["plan"]
        self.assertEqual(plan["version"], 1)
        self.assertNotIn("cucumber", plan)
        validate_plan(ProjectTools(legacy), plan, "before")

    def test_tag_expression_missing_or_extra_selection_fields_rejected(self):
        selection = self.request()["cucumber"]
        invalid = [dict(selection, tag=tag) for tag in ("@ONE or @TWO", "@ONE and not @TWO", "ONE", "@*", "")]
        invalid += [{"runner_file":RUNNER, "tag":"@ONE"}, dict(selection, unexpected=True)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.prepare(cucumber=value)

    def test_command_scope_and_duplicate_selectors_rejected(self):
        wrong = [
            ["gradlew", "test"],
            [v.replace("runners.Demo.runScenario", "runners.*") for v in self.command],
            [v.replace("-Dtest.runner=runners.Demo", "-Dtest.runner=runners.Other") for v in self.command],
            [v.replace("@ONE", "@ONE or @TWO") for v in self.command],
            [v for v in self.command if not v.startswith("-Dtest.runner=")],
            [v for v in self.command if not v.startswith("-Dcucumber.filter.tags=")],
            self.command + ["-Dtest.runner=runners.Other"],
            self.command + ["-Dcucumber.filter.tags=@TWO"],
            self.command + ["--tests", "runners.Other.runScenario"],
            self.command + ["clean"], self.command + ["-I", "unreviewed.gradle"],
            self.command + ["-Denv=dev", "-Denv=prod"],
        ]
        for command in wrong:
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.prepare(command=command)

    def test_tag_on_another_feature_is_ambiguous(self):
        put(self.root, "src/test/resources/features/pilot/another.feature", "Feature: Another\n @ONE\n Scenario: Duplicate tag\n  Given something\n")
        with self.assertRaises(ValueError):
            self.prepare()

    def test_duplicate_scenario_titles_cannot_bind_baseline_to_unique_tag(self):
        put(self.root, FEATURE, FEATURE_SOURCE.replace("Scenario: Other scenario", "Scenario: Selected scenario"))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_shared_feature_tag_is_not_exact_scenario_selection(self):
        put(self.root, FEATURE, "@ONE\n" + FEATURE_SOURCE.replace("  @ONE\n", "", 1))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_outline_rule_docstring_and_localized_feature_rejected(self):
        bad = [FEATURE_SOURCE.replace("Scenario: Selected scenario", "Scenario Outline: Selected scenario"),
               FEATURE_SOURCE.replace("  @ONE", "  Rule: Nested rule\n  @ONE", 1),
               FEATURE_SOURCE.replace("    Given two numbers", '    Given two numbers\n      """\n      data\n      """'),
               "# language: fr\n" + FEATURE_SOURCE]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                put(self.root, FEATURE, text)
                self.prepare()

    def test_native_title_feature_and_runner_must_match_selection(self):
        cases = [(BASE_NAME.replace("Selected scenario", "Wrong scenario"), "runners.Demo"),
                 (BASE_NAME.replace("Selected feature", "Wrong feature"), "runners.Demo"),
                 (BASE_NAME, "runners.Other")]
        for name, cls in cases:
            with self.subTest(name=name, cls=cls):
                self.write_report([(name, cls, "failed")])
                self.save_run("baseline.json", self.tools.parse_test_results(REPORT), exit_code=1)
                with self.assertRaises(ValueError):
                    self.prepare(case_name=name, case_class=cls)

    def test_runner_must_be_direct_and_declared_feature_path_must_contain_selection(self):
        for source in (RUNNER_SOURCE.replace("AbstractTestNGCucumberTests {", "OtherBase {"),
                       RUNNER_SOURCE.replace('"src/test/resources/features/pilot"', '"src/test/resources/features/elsewhere"'),
                       RUNNER_SOURCE.replace('features = "src/test/resources/features/pilot"', 'features = FEATURE_PATH')):
            with self.subTest(source=source), self.assertRaises(ValueError):
                put(self.root, RUNNER, source)
                self.prepare()

    def test_changed_selection_files_invalidate_before_and_after_repair(self):
        plan = self.prepare()
        for name in (RUNNER, FEATURE, "build.gradle"):
            path = self.root / name
            old = path.read_bytes()
            path.write_bytes(old + b"\n// changed\n" if name.endswith((".java", ".gradle")) else old + b"\n# changed\n")
            with self.subTest(stage="before", file=name), self.assertRaises(ValueError):
                validate_plan(self.tools, plan, "before")
            path.write_bytes(old)
        self.tools.apply_test_repair(plan)
        for name in (RUNNER, FEATURE, "build.gradle"):
            path = self.root / name
            old = path.read_bytes()
            path.write_bytes(old + b"\n")
            with self.subTest(stage="after", file=name), self.assertRaises(ValueError):
                validate_plan(self.tools, plan, "after")
            path.write_bytes(old)

    def test_new_feature_invalidates_reviewed_inventory(self):
        plan = self.prepare()
        self.tools.apply_test_repair(plan)
        put(self.root, "src/test/resources/features/pilot/new.feature", "Feature: New\n @THREE\n Scenario: New scenario\n  Given another value\n")
        with self.assertRaises(ValueError):
            validate_plan(self.tools, plan, "after")

    def test_selection_sources_are_not_repair_targets(self):
        with self.assertRaises(ValueError):
            self.prepare(source_file=RUNNER, old_text="glue = \"steps\"", new_text="glue = \"other\"")

    def test_assertion_weakening_remains_rejected(self):
        put(self.root, "calculator.py", "def add(a,b):\n    assert a == 2\n    return a - b\n")
        with self.assertRaisesRegex(ValueError, "assertion"):
            self.prepare(old_text="assert a == 2", new_text="assert a is not None")

    def test_passing_rerun_accepts_changed_native_ordinal(self):
        plan, _ = self.passing_run()
        with patch("subprocess.run", side_effect=AssertionError("saved review only")):
            result = self.tools.compare_test_rerun(plan, "rerun.json")
        self.assertEqual(result["status"], "selected_rerun_passed", result)
        self.assertEqual(result["root_cause"], "unconfirmed")
        self.assertEqual(result["actions_executed"], [])

    def test_extra_wrong_or_duplicate_cases_never_accept(self):
        cases = [
            [(PASS_NAME.replace("Selected scenario", "Wrong scenario"), "runners.Demo", "passed")],
            [(PASS_NAME.replace("Selected feature", "Wrong feature"), "runners.Demo", "passed")],
            [(PASS_NAME, "runners.Other", "passed")],
            [(PASS_NAME, "runners.Demo", "passed"), ('runScenario[1]("Other scenario", "Selected feature")', "runners.Demo", "passed")],
            [(PASS_NAME, "runners.Demo", "passed"), (PASS_NAME, "runners.Demo", "passed")],
        ]
        plan, run = self.passing_run()
        for rows in cases:
            with self.subTest(rows=rows):
                self.write_report(rows)
                self.save_run("rerun.json", self.tools.parse_test_results(REPORT), repair_plan_id=plan["id"], repair_source=run["repair_source"], repair_selection=run["repair_selection"])
                result = self.tools.compare_test_rerun(plan, "rerun.json")
                self.assertEqual(result["status"], "incomplete", result)

    def test_failed_skipped_unknown_exit_and_stale_report_remain_incomplete(self):
        plan, run = self.passing_run()
        for status in ("failed", "skipped"):
            self.write_report([(PASS_NAME, "runners.Demo", status)])
            self.save_run("rerun.json", self.tools.parse_test_results(REPORT), repair_plan_id=plan["id"], repair_source=run["repair_source"], repair_selection=run["repair_selection"])
            self.assertEqual(self.tools.compare_test_rerun(plan, "rerun.json")["status"], "incomplete")
        put(self.root, "rerun.json", json.dumps(dict(run, exit_code=None)))
        self.assertEqual(self.tools.compare_test_rerun(plan, "rerun.json")["status"], "incomplete")
        put(self.root, "rerun.json", json.dumps(run))
        self.write_report([(PASS_NAME, "runners.Demo", "passed"), ('runScenario[1]("Unexpected", "Selected feature")', "runners.Demo", "passed")])
        self.assertEqual(self.tools.compare_test_rerun(plan, "rerun.json")["status"], "incomplete")

    def test_missing_or_changed_execution_selection_is_incomplete(self):
        plan, run = self.passing_run()
        missing = {k:v for k,v in run.items() if k != "repair_selection"}
        changed = copy.deepcopy(run)
        changed["repair_selection"]["after"]["tag"] = "@TWO"
        for invalid in (missing, changed, dict(run, repair_selection={"unchanged":False})):
            with self.subTest(selection=invalid.get("repair_selection")):
                put(self.root, "rerun.json", json.dumps(invalid))
                result = self.tools.compare_test_rerun(plan, "rerun.json")
                self.assertEqual(result["status"], "incomplete", result)

    def test_build_must_forward_runner_and_tag_settings(self):
        for name in ("test.runner", "cucumber.filter.tags"):
            with self.subTest(setting=name), self.assertRaises(ValueError):
                put(self.root, "build.gradle", BUILD_SOURCE.replace(name, "unsupported.setting"))
                self.prepare()

    def test_feature_file_inventory_limit_is_bounded(self):
        for number in range(40):
            put(self.root, "src/test/resources/features/pilot/extra-%02d.feature" % number,
                "Feature: Extra %d\n @EXTRA%d\n Scenario: Another scenario\n  Given a value\n" % (number, number))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_runner_requires_real_cucumber_imports(self):
        for name in ("CucumberOptions", "AbstractTestNGCucumberTests"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                put(self.root, RUNNER, RUNNER_SOURCE.replace("import io.cucumber.testng." + name, "import untrusted." + name))
                self.prepare()

    def test_nonfeature_directory_entries_are_bounded(self):
        for number in range(1000):
            put(self.root, "src/test/resources/features/pilot/nonfeature-%04d.txt" % number, "ignored text")
        with self.assertRaises(ValueError):
            self.prepare()

    def test_total_feature_bytes_are_bounded(self):
        for number in range(3):
            put(self.root, "src/test/resources/features/pilot/large-%d.feature" % number,
                "#" + "x" * 180000 + "\nFeature: Extra %d\n @EXTRA%d\n Scenario: Another scenario\n  Given a value\n" % (number, number))
        with self.assertRaises(ValueError):
            self.prepare()

    def test_actual_project_loop_prepares_v2_then_waits_for_repair_approval(self):
        from agent.actions.receipts import ActionPending
        from agent.runtime.project_native_specs import native_project_specs
        from tests.test_project_budget import BudgetTests
        specs = native_project_specs({"prepare_test_repair":self.tools.prepare_test_repair,
                                      "apply_test_repair":self.tools.apply_test_repair})
        schemas = {item["function"]["name"]:item["function"]["parameters"] for item in specs}
        self.assertEqual(schemas["prepare_test_repair"]["required"], ["request"])
        self.assertEqual(schemas["apply_test_repair"]["required"], ["plan"])
        plan = self.prepare()
        before = (self.root / "calculator.py").read_bytes()
        decisions = [{"action":"prepare_test_repair", "arguments":{"request":self.request()}},
                     {"action":"apply_test_repair", "arguments":{"plan":plan}}]
        with patch.dict(os.environ, {}, clear=True), patch("agent.project_decisions.call_project_decision",
                side_effect=[json.dumps(value) for value in decisions]) as model, \
                patch("agent.local_action_receipts.LocalActionReceipts.run",
                      side_effect=ActionPending("Action is waiting for your browser approval. Review the exact action.")) as pending, \
                patch("subprocess.run", side_effect=AssertionError("no command in proposal path")), redirect_stdout(io.StringIO()):
            project = BudgetTests().project_function(self.root)
            project.__globals__["approve_local_action"] = lambda *args: False
            result = project({"question":"Prepare the evidence-bound Cucumber repair and show its exact approval before editing.",
                              "project_root":str(self.root)})
        self.assertEqual(result["task_status"], "awaiting_input", result)
        self.assertIn("awaiting approval", result["answer"])
        self.assertEqual(model.call_count, 2)
        pending.assert_called_once()
        self.assertEqual(pending.call_args.args[1], "apply_test_repair")
        self.assertEqual(pending.call_args.args[2], {"plan":plan})
        self.assertEqual(before, (self.root / "calculator.py").read_bytes())

    def test_browser_separate_approvals_and_saved_result_replay(self):
        plan = self.prepare()
        actions = BrowserActions(self.root / "receipts.sqlite3")
        repair = actions.propose("u", "p", "chat", "apply_test_repair",
                                 {"project_root":str(self.root), "action":"apply_test_repair", "arguments":{"plan":plan}})
        with patch.object(ProjectTools, "run_tests_and_parse", side_effect=AssertionError("no automatic rerun")):
            applied, replay = actions.execute("u", "p", "chat", repair)
        self.assertFalse(replay)
        self.assertFalse(applied["rerun_executed"])
        rerun = actions.propose("u", "p", "chat", "rerun_test_repair",
                                {"project_root":str(self.root), "action":"rerun_test_repair", "arguments":{"plan":plan}})
        self.assertNotEqual(repair, rerun)
        def command(*args, **kwargs):
            self.write_report([(PASS_NAME, "runners.Demo", "passed")])
            return {"command":self.command, "exit_code":0, "timed_out":False, "stdout":"synthetic fixture only", "stderr":""}
        with patch.object(ProjectTools, "run_command", side_effect=command) as invoked:
            result, replay = actions.execute("u", "p", "chat", rerun)
            again, replayed = actions.execute("u", "p", "chat", rerun)
        self.assertFalse(replay)
        self.assertTrue(replayed)
        self.assertEqual(invoked.call_count, 1)
        self.assertEqual(again, result)
        put(self.root, "rerun.json", json.dumps(result))
        self.assertEqual(self.tools.compare_test_rerun(plan, "rerun.json")["status"], "selected_rerun_passed")


if __name__ == "__main__":
    unittest.main()
