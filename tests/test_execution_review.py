"""Synthetic post-run checks preserve evidence and never run target projects."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.tools.execution_review import review_execution, attach_review, MAX_SOURCE_FILES
from agent.tools.project_tools import ProjectTools
from tests.test_execution_results import payload, report
from tests import test_projects as fixtures


class PostRunReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def data(self, name="entry", cls="demo.InputTest", **values):
        return payload(reports=[report(total=1, passed=1, tests=[{"class": cls, "name": name, "status": "passed"}])],
                       report_status="fresh_reports_found", **values)["result"]

    def java(self, body, name="entry"):
        return self.put("src/test/java/demo/InputTest.java",
                        "package demo;\nclass InputTest {\n  void " + name + "() {\n" + body + "\n  }\n}\n")

    def kinds(self, review):
        return {item["kind"] for item in review["findings"]}

    def test_commented_and_always_true_checks_have_hashed_source_evidence(self):
        path = self.java('    // assertEquals(actual, expected);\n    assertTrue(true);')
        review = review_execution(self.data(), self.root)
        self.assertEqual(self.kinds(review), {"commented_assertion", "weak_assertion"})
        source = review["source_checks"][0]
        self.assertEqual(source["line"], 3)
        self.assertEqual(source["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIn("not prove", " ".join(review["limits"]))
        self.assertNotIn("passed", review["status"])

    def test_helper_checks_are_unknown_not_a_proven_missing_assertion(self):
        self.java("    checkUsingHelper();")
        review = review_execution(self.data(), self.root)
        self.assertIn("assertion_review", self.kinds(review))
        self.assertIn("helper/inherited", review["findings"][0]["next_check"])
        self.assertNotIn("defect", review["findings"][0]["title"])

    def test_strings_and_other_methods_do_not_supply_assertions(self):
        self.put("src/test/java/demo/InputTest.java", '''package demo;
class InputTest {
  void entry() {
    String log = "assertEquals(value, expected)";
    // assertTrue(actual);
  }
  void other() { assertEquals(2, 2); }
}
''')
        review = review_execution(self.data(), self.root)
        self.assertIn("assertion_review", self.kinds(review))
        self.assertIn("commented_assertion", self.kinds(review))
        self.assertEqual(review["source_checks"][0]["recognized_direct_checks"], 0)

    def test_recognized_check_is_not_certified_as_requirement_correct(self):
        self.java('    assertEquals(field.inputValue(), "expected");')
        review = review_execution(self.data(), self.root)
        self.assertEqual(review["findings"], [])
        self.assertEqual(review["status"], "limited_review")
        self.assertTrue(any("Requirements" in item for item in review["limits"]))

    def test_python_ast_ignores_strings_comments_and_uninvoked_nested_helpers(self):
        self.put("tests/test_input.py", '''class InputTest:
    def entry(self):
        text = "assert actual == expected"
        # assert actual == expected
        def helper():
            assert True
        self.assertTrue(True)
''')
        review = review_execution(self.data(cls="tests.test_input.InputTest"), self.root)
        self.assertEqual(review["source_checks"][0]["recognized_direct_checks"], 1)
        self.assertEqual(self.kinds(review), {"weak_assertion"})

    def test_conflicting_exit_codes_native_failures_skips_and_log_signals(self):
        data = self.data(exit_code=1, stderr="captured\nBUILD FAILED\n")
        review = review_execution(data)
        self.assertIn("outcome_conflict", self.kinds(review))
        self.assertIn("log_signal", self.kinds(review))
        log = next(f for f in review["findings"] if f["kind"] == "log_signal")
        self.assertEqual(log["evidence"], {"field": "stderr", "captured_line": 2})
        data["exit_code"] = 0
        data["reports"][0].update(passed=0, failed=1, overall_status="failed")
        review = review_execution(data)
        self.assertTrue({"outcome_conflict", "native_failure"} <= self.kinds(review))
        data["reports"][0].update(failed=0, skipped=1, overall_status="skipped")
        self.assertIn("coverage_gap", self.kinds(review_execution(data)))

    def test_stale_or_invalid_reports_never_trigger_source_reads(self):
        self.java("    assertTrue(true);")
        for change in ({"freshness": "unverified"}, {"total": 5}, {"format": "unknown"}):
            data = self.data()
            data["reports"][0].update(change)
            with patch("agent.tools.test_failures._load", side_effect=AssertionError("no source")):
                review = review_execution(data, self.root)
            self.assertEqual(review["source_checks"], [])
            self.assertIn("unverified_report", self.kinds(review))

    def test_missing_ambiguous_or_unmatched_sources_are_not_guessed(self):
        review = review_execution(self.data(), self.root)
        self.assertIn("missing or ambiguous", review["source_checks"][0]["status"])
        self.java("    assertTrue(true);")
        self.put("src/main/java/demo/InputTest.java", "class InputTest {}")
        review = review_execution(self.data(), self.root)
        self.assertIn("missing or ambiguous", review["source_checks"][0]["status"])
        (self.root/"src/main/java/demo/InputTest.java").unlink()
        review = review_execution(self.data(name="absent"), self.root)
        self.assertIn("unique test method", review["source_checks"][0]["status"])

    def test_wrong_class_or_overloaded_method_is_not_guessed(self):
        self.put("src/test/java/demo/InputTest.java", "class Other { void entry() { assertTrue(true); } }")
        self.assertIn("unique test method", review_execution(self.data(), self.root)["source_checks"][0]["status"])
        self.put("src/test/java/demo/InputTest.java", "class InputTest { void entry() {} void entry(int n) {} }")
        self.assertIn("unique test method", review_execution(self.data(), self.root)["source_checks"][0]["status"])
        self.put("tests/test_input.py", "def entry():\n    assert True\n")
        review = review_execution(self.data(cls="tests.test_input.InputTest"), self.root)
        self.assertIn("unique test method", review["source_checks"][0]["status"])
        review = review_execution(self.data(cls="tests.test_input"), self.root)
        self.assertIn("weak_assertion", self.kinds(review))

    def test_evidence_reader_accepts_a_stricter_cap_without_changing_default(self):
        from agent.tools.test_failures import _load
        self.put("example.py", "x"*21)
        with self.assertRaises(ValueError):
            _load(self.root, "example.py", max_bytes=20)
        self.assertEqual(_load(self.root, "example.py")[0]["size_bytes"], 21)
        with self.assertRaises(ValueError):
            _load(self.root, "example.py", max_bytes=True)

    def test_source_bounds_and_report_names_cannot_read_credentials_or_escape(self):
        self.java("x"*256_001)
        self.assertIn("not reviewed", review_execution(self.data(), self.root)["source_checks"][0]["status"])
        for cls in ("../outside", "C:/secret", ".env", ".aws.credentials", "../../secret"):
            with patch("agent.tools.test_failures._load", side_effect=AssertionError("no source")):
                review = review_execution(self.data(cls=cls), self.root)
            self.assertEqual(review["findings"], [])

    def test_symlink_source_is_not_followed(self):
        target = self.put("other.java", "class InputTest { void entry() { assertTrue(true); } }")
        link = self.root/"src/test/java/demo/InputTest.java"
        link.parent.mkdir(parents=True)
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest("Symlinks unavailable: " + str(error))
        with patch("agent.tools.test_failures._load", side_effect=AssertionError("no link read")):
            review = review_execution(self.data(), self.root)
        self.assertIn("missing or ambiguous", review["source_checks"][0]["status"])

    def test_junction_candidates_are_excluded_even_without_symlink_privileges(self):
        self.java("    assertTrue(true);")
        original = Path.is_junction
        with patch.object(Path, "is_junction", lambda path: path.name == "demo" or original(path)):
            with patch("agent.tools.test_failures._load", side_effect=AssertionError("no junction read")):
                review = review_execution(self.data(), self.root)
        self.assertIn("missing or ambiguous", review["source_checks"][0]["status"])

    def test_timeout_and_no_reports_never_imply_tests_passed(self):
        review = review_execution({"timed_out": True, "exit_code": None, "stdout": "all tests passed"})
        self.assertIn("uncertain", self.kinds(review))
        self.assertEqual(review["source_checks"], [])
        self.assertTrue(any("No attached native" in item for item in review["limits"]))

    def test_source_file_and_case_limits_are_explicit(self):
        cases = []
        for index in range(25):
            self.put("src/test/java/demo/Test" + str(index) + ".java",
                     "class Test" + str(index) + " { void entry() { assertTrue(true); } }")
            cases.append({"name": "entry", "class": "demo.Test" + str(index), "status": "passed"})
        data = self.data()
        data["reports"][0].update(tests=cases, total=25, passed=25)
        with patch("agent.tools.test_failures._load", wraps=__import__("agent.tools.test_failures", fromlist=["_load"])._load) as load:
            review = review_execution(data, self.root)
        self.assertEqual(load.call_count, MAX_SOURCE_FILES)
        self.assertEqual(len(review["source_checks"]), 20)
        self.assertTrue(any("first 20" in item for item in review["limits"]))

    def test_total_source_byte_budget_stops_before_reading_another_large_file(self):
        cases = []
        for index in range(6):
            self.put("src/test/java/demo/Test" + str(index) + ".java",
                     "class Test" + str(index) + " { void entry() { assertTrue(true); } }\n//" + "x"*220_000)
            cases.append({"name": "entry", "class": "demo.Test" + str(index), "status": "passed"})
        data = self.data()
        data["reports"][0].update(tests=cases, total=6, passed=6)
        from agent.tools.test_failures import _load
        with patch("agent.tools.test_failures._load", wraps=_load) as load:
            review = review_execution(data, self.root)
        self.assertEqual(load.call_count, 4)
        self.assertLessEqual(sum(item.get("size_bytes", 0) for item in review["source_checks"]), 1_000_000)
        self.assertTrue(all("not reviewed" in item["status"] for item in review["source_checks"][4:]))

    def test_review_is_read_only_and_failure_retains_original_outcome(self):
        path = self.java("    assertTrue(true);")
        before = path.read_bytes()
        data = self.data()
        original = copy.deepcopy(data)
        with patch("subprocess.run", side_effect=AssertionError("no execution")), patch(
                "requests.sessions.Session.request", side_effect=AssertionError("no network")):
            reviewed = attach_review(data, self.root)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(data, original)
        self.assertEqual({k: v for k, v in reviewed.items() if k != "post_run_review"}, original)
        with patch("agent.tools.execution_review.review_execution", side_effect=OSError("fixture")):
            reviewed = attach_review(data, self.root)
        self.assertEqual(reviewed["post_run_review"]["status"], "unavailable")
        self.assertEqual(reviewed["exit_code"], 0)
        self.assertIn("Do not rerun", reviewed["post_run_review"]["limits"][0])

    def test_actual_native_collection_attaches_review_without_extra_execution(self):
        self.java("    assertTrue(true);")
        tools = ProjectTools(self.root)
        def command(*args, **kwargs):
            self.put("reports/TEST-input.xml",
                     '<testsuite><testcase name="entry" classname="demo.InputTest"/></testsuite>')
            return {"command": ["gradlew", "test"], "exit_code": 0, "timed_out": False, "stdout": "", "stderr": ""}
        with patch.object(tools, "run_command", side_effect=command) as run:
            result = tools.run_tests_and_parse(["gradlew", "test"], "reports")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["reports"][0]["passed"], 1)
        self.assertIn("weak_assertion", self.kinds(result["post_run_review"]))


class PostRunReceiptTests(unittest.TestCase):
    def setUp(self):
        fixtures.ProjectBackendTests.setUp(self)
        self.backend = self.view_a
        self.session = self.backend.create_chat("Post-run review")

    def test_owned_receipt_saves_review_and_refresh_does_not_rescan_or_rerun(self):
        source = self.a/"src/test/java/demo/InputTest.java"
        source.parent.mkdir(parents=True)
        source.write_text("class InputTest { void entry() { assertTrue(true); } }", encoding="utf-8")
        token = self.backend.actions().propose("u", self.backend.space, self.session, "run_tests_and_parse",
                {"project_root": str(self.a), "action": "run_tests_and_parse",
                 "arguments": {"command": ["python", "-c", "pass"], "relative_report_folder": "reports", "timeout": 10}})
        def command(*args, **kwargs):
            folder = self.a/"reports"
            folder.mkdir(exist_ok=True)
            (folder/"TEST-input.xml").write_text('<testsuite><testcase name="entry" classname="demo.InputTest"/></testsuite>')
            return {"command": ["python", "-c", "pass"], "exit_code": 0, "timed_out": False}
        with patch.object(ProjectTools, "run_command", side_effect=command) as run:
            self.backend.decide_action(self.session, token, True)
            first = self.backend.execution_result(self.session, token)
            self.assertTrue(first["result"]["post_run_review"]["findings"])
            source.write_text("changed after receipt", encoding="utf-8")
            with patch("agent.tools.execution_review.review_execution", side_effect=AssertionError("no rescan")):
                self.assertEqual(first, self.backend.execution_result(self.session, token))
                self.backend.decide_action(self.session, token, True)
            self.assertEqual(run.call_count, 1)
        other = self.backend.create_chat("Other")
        self.assertIsNone(self.backend.execution_result(other, token))
        self.assertIsNone(self.view_b.execution_result(self.session, token))
        self.assertEqual(self.invocations, [])


class ApprovedExecutionReviewTests(unittest.TestCase):
    def test_command_and_python_reviews_are_persisted_once_without_source_access(self):
        from agent.actions.receipts import LocalActionReceipts
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/"demo.py").write_text("print('fixture')", encoding="utf-8")
            receipts = LocalActionReceipts(root/"receipts.sqlite3")
            for action, args in (("run_command", {"command": ["python", "-c", "pass"]}),
                                 ("run_python_file", {"relative_path": "demo.py"})):
                calls = []
                def handler(**kwargs):
                    calls.append(kwargs)
                    return {"exit_code": 0, "timed_out": False, "stderr": "BUILD FAILED"}
                with patch("agent.tools.test_failures._load", side_effect=AssertionError("no implicit source scan")):
                    result = receipts.run(root, action, args, handler, lambda *a: True, receipt_id=action)
                    replay = receipts.run(root, action, args, handler, lambda *a: False, receipt_id=action)
                self.assertEqual(len(calls), 1)
                self.assertEqual(result, replay)
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(result["post_run_review"]["findings"][0]["kind"], "log_signal")
                self.assertEqual(receipts.get(action)["status"], "completed")

    def test_review_failure_cannot_convert_completed_effect_to_uncertain(self):
        from agent.actions.receipts import LocalActionReceipts
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipts = LocalActionReceipts(root/"receipts.sqlite3")
            with patch("agent.tools.execution_review.review_execution", side_effect=OSError("fixture")):
                result = receipts.run(root, "run_command", {"command": ["python", "-c", "pass"]},
                                      lambda **kwargs: {"exit_code": 0, "timed_out": False}, lambda *a: True)
            self.assertEqual(result["post_run_review"]["status"], "unavailable")
            self.assertEqual(result["exit_code"], 0)


class PostRunUITests(unittest.TestCase):
    def test_saved_findings_show_without_source_rescan_and_raw_receipt_is_preserved(self):
        from streamlit.testing.v1 import AppTest
        script = """
from agent.interfaces.execution_results import render_execution_result
from agent.tools.execution_review import review_execution
from tests.test_execution_results import payload, report
class Backend:
    def execution_result(self, session, token):
        result = payload(exit_code=1, reports=[report()], report_status="fresh_reports_found")
        result["result"]["post_run_review"] = review_execution(result["result"])
        return result
render_execution_result(Backend(), "chat", token="a"*32)
"""
        app = AppTest.from_string(script).run()
        self.assertFalse(app.exception)
        review = next(item for item in app.expander if item.label == "Post-run review")
        self.assertTrue(review.proto.expanded)
        self.assertTrue(any("separate interpretation" in item.value for item in app.warning))
        raw = next(item for item in app.expander if item.label == "Raw receipt and logs")
        self.assertFalse(raw.proto.expanded)
        self.assertIn('"post_run_review"', raw.code[0].value)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len([e for e in app.expander if e.label == "Post-run review"]), 1)


if __name__ == "__main__":
    unittest.main()
