"""Stored file/inspection result presentation preserves evidence and approvals."""
import copy
import json
import unittest
from unittest.mock import patch

from agent.interfaces.execution_results import (
    FILE_ACTIONS, RESULT_ACTIONS, MAX_FIELDS, MAX_DIFF,
    file_action_summary, inspection_summary,
)
from agent.policies.tool_registry import CONTROLLED_PROJECT_ACTIONS
from agent.tools.project_tools import ProjectTools
from tests import test_execution_results as result_fixtures
from tests.repair_fixtures import make_plan


def file_payload(action="create_file", **values):
    args = {"relative_path": "outputs/note.md", "content": "approved"}
    result = {"file": "outputs/note.md", "created": True, "size_bytes": 8}
    if action == "replace_text":
        args = {"relative_path": "outputs/note.md", "old_text": "old", "new_text": "new"}
        result = {"file": "outputs/note.md", "changed": True, "diff": "-old\n+new\n"}
    if action == "apply_test_repair":
        args = {"plan": {"id": "reviewed-plan", "replacement": {"file": "calculator.py", "after_sha256": "a" * 64}}}
        result = {"file": "calculator.py", "changed": True, "repair_plan_id": "reviewed-plan",
                  "source_after": {"sha256": "a" * 64}, "rerun_executed": False, "causal_repair_verified": False}
    result.update(values)
    return {"receipt_id": "b" * 32, "receipt_status": "completed", "action": action,
            "project_root": "fixture-project", "arguments": args, "result": result}


def inspection_payload(**values):
    result = {"status": "inspected", "requested_url": "https://example.com/#inputs", "url": "https://example.com/#inputs",
              "inspection_file": "test-output/agent-web/sample/inspection.json",
              "screenshot": "test-output/agent-web/sample/inspection.png", "inspection_sha256": "c" * 64,
              "captured_at": "2026-10-29T10:00:00+00:00", "fields": [
                  {"label": "Text Input", "type": "text", "disabled": False, "read_only": False},
                  {"label": "Locked", "type": "text", "disabled": True, "read_only": True},
                  {"label": "Unknown", "type": "text", "disabled": "false", "read_only": 0}]}
    result.update(values)
    return {"receipt_id": "c" * 32, "receipt_status": "completed", "action": "inspect_browser_page",
            "project_root": "fixture-project", "arguments": {"url": "https://example.com/#inputs"}, "result": result}


class SavedActionSummaryTests(unittest.TestCase):
    def test_every_core_controlled_action_has_an_explicit_display_kind(self):
        self.assertEqual(RESULT_ACTIONS, CONTROLLED_PROJECT_ACTIONS)
        self.assertNotIn("git_push", RESULT_ACTIONS)
        self.assertNotIn("git_commit", RESULT_ACTIONS)

    def test_file_creation_and_change_do_not_claim_test_or_task_completion(self):
        for action, expected in (("create_file", "File created"), ("replace_text", "File updated")):
            with self.subTest(action=action):
                data = file_payload(action)
                original = copy.deepcopy(data)
                summary = file_action_summary(data)
                self.assertEqual(summary["status"], expected)
                self.assertEqual(summary["severity"], "success")
                self.assertIn(("Approved file", "outputs/note.md"), summary["evidence"])
                self.assertTrue(any("completed task" in line for line in summary["limits"]))
                self.assertTrue(any("still exists" in line for line in summary["limits"]))
                self.assertEqual(data, original)
                self.assertEqual(summary["download_hint"], action == "create_file")

    def test_uncertain_creation_never_becomes_success(self):
        data = file_payload(); data["receipt_status"] = "uncertain"
        summary = file_action_summary(data)
        self.assertEqual(summary["status"], "Uncertain")
        self.assertNotEqual(summary["severity"], "success")
        self.assertFalse(summary["download_hint"])
        self.assertTrue(any("Do not repeat" in line for line in summary["limits"]))

    def test_mismatched_or_unsafe_file_paths_do_not_claim_success(self):
        for path in ("../outside.md", "/outside.md", "D:\\outside.md", "other.md", None, ""):
            with self.subTest(path=path):
                summary = file_action_summary(file_payload(file=path))
                self.assertEqual(summary["status"], "Outcome unavailable")
        data = file_payload(); data["arguments"]["relative_path"] = "outputs\\note.md"
        self.assertEqual(file_action_summary(data)["status"], "File created")

    def test_flags_sizes_and_no_change_are_not_inferred_from_truthy_values(self):
        for value in ("true", 1, False, None):
            self.assertNotEqual(file_action_summary(file_payload(created=value))["severity"], "success")
        for value in (True, -1, "8", None):
            self.assertIsNone(file_action_summary(file_payload(size_bytes=value))["size_bytes"])
        self.assertEqual(file_action_summary(file_payload("replace_text", changed=False))["status"], "No file change")
        self.assertEqual(file_action_summary(file_payload(size_bytes=0))["size_bytes"], 0)

    def test_diff_is_bounded_without_discarding_raw_payload(self):
        data = file_payload("replace_text", diff="x" * (MAX_DIFF + 10))
        summary = file_action_summary(data)
        self.assertEqual(len(summary["diff"]), MAX_DIFF)
        self.assertEqual(len(data["result"]["diff"]), MAX_DIFF + 10)
        self.assertTrue(any("truncated" in line for line in summary["limits"]))

    def test_repair_requires_matching_plan_and_after_digest_and_never_certifies_cause(self):
        data = file_payload("apply_test_repair")
        summary = file_action_summary(data)
        self.assertEqual(summary["status"], "Repair source updated")
        self.assertTrue(any("separately approve" in line for line in summary["limits"]))
        self.assertTrue(any("not confirmed" in line for line in summary["limits"]))
        for change in ({"repair_plan_id": "different"}, {"source_after": {}},
                       {"source_after": {"sha256": "b" * 64}}):
            self.assertEqual(file_action_summary(file_payload("apply_test_repair", **change))["status"], "Outcome unavailable")

    def test_browser_attributes_are_observed_flags_not_editing_proof(self):
        data = inspection_payload()
        summary = inspection_summary(data)
        self.assertEqual(summary["status"], "Page inspected")
        self.assertEqual(summary["fields"][0], {"Field": "Text Input", "Type": "text", "Enabled": "Yes", "Read only": "No"})
        self.assertEqual(summary["fields"][1]["Enabled"], "No")
        self.assertEqual(summary["fields"][2]["Enabled"], "Unknown")
        self.assertEqual(summary["fields"][2]["Read only"], "Unknown")
        self.assertTrue(any("successful editing" in line for line in summary["limits"]))
        self.assertTrue(any("fresh website check" in line for line in summary["limits"]))

    def test_inspection_uncertainty_and_scope_mismatches_are_not_success(self):
        data = inspection_payload(); data["receipt_status"] = "uncertain"
        self.assertEqual(inspection_summary(data)["status"], "Uncertain")
        for changes in ({"requested_url": "https://other.example"}, {"url": "https://other.example"},
                        {"inspection_file": "../elsewhere.json"}, {"fields": "not a list"}, {"status": "blocked"}):
            with self.subTest(changes=changes):
                summary = inspection_summary(inspection_payload(**changes))
                self.assertNotEqual(summary["severity"], "success")

    def test_inspection_sampling_and_malformed_rows_remain_explicit(self):
        fields = [{"label": "<script>alert('data')</script>" + "x" * 300, "type": "text"}] * (MAX_FIELDS + 3)
        summary = inspection_summary(inspection_payload(fields=fields, fields_may_be_truncated=True))
        self.assertEqual(len(summary["fields"]), MAX_FIELDS)
        self.assertEqual(len(summary["fields"][0]["Field"]), 160)
        self.assertTrue(any("bounded field sample" in line for line in summary["limits"]))
        summary = inspection_summary(inspection_payload(fields=[None]))
        self.assertEqual(summary["fields"], [])
        self.assertTrue(any("malformed" in line for line in summary["limits"]))
        summary = inspection_summary(inspection_payload(screenshot="D:\\private\\image.png"))
        self.assertFalse(any(label == "Screenshot" for label, value in summary["evidence"]))


class FileReceiptReadTests(unittest.TestCase):
    setUp = result_fixtures.ReceiptReadTests.setUp

    def test_file_receipt_remains_owned_fingerprint_bound_and_read_only(self):
        args = {"relative_path": "note.md", "content": "approved"}
        proposal = {"project_root": str(self.a), "action": "create_file", "arguments": args}
        token = self.backend.actions().propose("u", self.backend.space, self.session, "create_file", proposal)
        self.assertIsNone(self.backend.execution_result(self.session, token))
        self.backend.decide_action(self.session, token, True)
        saved = self.backend.turns(self.session)
        for _ in range(2):
            data = self.backend.execution_result(self.session, token)
            self.assertTrue(data["result"]["created"])
        self.assertEqual(self.backend.turns(self.session), saved)
        self.assertIsNone(self.backend.execution_result(self.backend.create_chat("Other"), token))
        self.assertIsNone(self.view_b.execution_result(self.session, token))
        other = copy.copy(self.backend); other.user = "other"
        self.assertIsNone(other.execution_result(self.session, token))
        with self.backend.actions().receipts.connect() as db:
            db.execute("UPDATE actions SET fingerprint='tampered' WHERE id=?", (token,))
        self.assertIsNone(self.backend.execution_result(self.session, token))
        self.assertEqual(self.invocations, [])


class SavedActionUITests(unittest.TestCase):
    setUp = result_fixtures.ExecutionResultUITests.setUp
    open_projects = result_fixtures.ExecutionResultUITests.open_projects

    def queue(self, action, args):
        proposal = {"project_root": str(self.a), "action": action, "arguments": args}
        token = self.backend.actions().propose("u", self.backend.space, self.session, action, proposal)
        self.app.run()
        return token

    def assert_one_result(self, title):
        self.assertFalse(self.app.exception)
        self.assertEqual([item.value for item in self.app.markdown].count(title), 1)

    def test_created_file_renders_once_and_download_remains_an_explicit_snapshot(self):
        original = ProjectTools.create_file
        token = self.queue("create_file", {"relative_path": "note.md", "content": "approved"})
        with patch.object(ProjectTools, "create_file", autospec=True, side_effect=original) as create:
            self.app.button(key="approve_" + token).click().run()
            saved = self.backend.turns(self.session)
            for _ in range(2):
                self.app.run(); self.assert_one_result("**File result**")
            self.assertEqual(create.call_count, 1)
        self.assertTrue(any(item.value == "File created" for item in self.app.success))
        self.assertTrue(any("Prepare download" in item.value for item in self.app.caption))
        self.assertFalse(next(item for item in self.app.expander if item.label == "Raw receipt and logs").proto.expanded)
        self.assertIn("Stored action returned", saved[-1]["answer"])
        self.assertEqual(self.backend.turns(self.session), saved)
        self.assertEqual((self.a / "note.md").read_text(), "approved")
        self.assertFalse(self.app.session_state.get("generated_downloads", {}))
        self.open_projects(); self.app.button(key="choose_project_" + self.pb["id"]).click().run()
        self.assertFalse(any(item.value == "**File result**" for item in self.app.markdown))
        self.assertEqual(self.invocations, [])

    def test_changed_file_shows_collapsed_diff_and_refresh_does_not_apply_again(self):
        (self.a / "note.md").write_text("old")
        original = ProjectTools.replace_text
        token = self.queue("replace_text", {"relative_path": "note.md", "old_text": "old", "new_text": "new"})
        with patch.object(ProjectTools, "replace_text", autospec=True, side_effect=original) as replace:
            self.app.button(key="approve_" + token).click().run()
            self.app.run(); self.assert_one_result("**File result**")
            self.assertEqual(replace.call_count, 1)
        self.assertTrue(any(item.value == "File updated" for item in self.app.success))
        change = next(item for item in self.app.expander if item.label == "Applied change")
        self.assertFalse(change.proto.expanded)
        self.assertIn("+new", change.code[0].value)
        self.assertEqual((self.a / "note.md").read_text(), "new")
        self.assertEqual(self.invocations, [])

    def test_browser_inspection_displays_stored_fields_without_reopening_website(self):
        captured = inspection_payload()["result"]
        token = self.queue("inspect_browser_page", {"url": "https://example.com/#inputs"})
        with patch.object(ProjectTools, "inspect_browser_page", return_value=captured) as inspect:
            self.app.button(key="approve_" + token).click().run()
            for _ in range(2):
                self.app.run(); self.assert_one_result("**Browser inspection**")
            self.assertEqual(inspect.call_count, 1)
        self.assertTrue(any(item.value == "Page inspected" for item in self.app.success))
        data = self.app.dataframe[0].value
        self.assertEqual(data.iloc[0]["Field"], "Text Input")
        self.assertEqual(data.iloc[2]["Enabled"], "Unknown")
        self.assertEqual(self.invocations, [])

    def test_repair_source_result_does_not_rerun_or_certify_diagnosis(self):
        plan = make_plan(self.a)["plan"]
        token = self.queue("apply_test_repair", {"plan": plan})
        with patch.object(ProjectTools, "rerun_test_repair", side_effect=AssertionError("no automatic rerun")) as rerun:
            self.app.button(key="approve_" + token).click().run()
            self.app.run(); self.assert_one_result("**File result**")
            rerun.assert_not_called()
        self.assertTrue(any(item.value == "Repair source updated" for item in self.app.success))
        self.assertTrue(any("separately approve" in item.value for item in self.app.text))
        self.assertEqual((self.a / "calculator.py").read_text(), "def add(a, b):\n    return a + b\n")
        self.assertEqual(self.invocations, [])

    def test_file_result_fallback_after_archive_failure_is_visible_without_reexecution(self):
        original = ProjectTools.create_file
        token = self.queue("create_file", {"relative_path": "fallback.md", "content": "saved"})
        with patch.object(ProjectTools, "create_file", autospec=True, side_effect=original) as create:
            with patch.object(self.backend.catalog.__class__, "append", side_effect=OSError("fixture archive failure")):
                self.app.button(key="approve_" + token).click().run()
            self.app.run(); self.assert_one_result("**File result**")
            self.assertEqual(create.call_count, 1)
        self.assertEqual(self.backend.turns(self.session), [])
        self.assertTrue(any(item.value == "File created" for item in self.app.success))
        self.assertEqual(self.invocations, [])

    def test_uncertain_saved_file_receipt_is_warning_even_with_created_flag(self):
        token = self.queue("create_file", {"relative_path": "uncertain.md", "content": "saved"})
        self.app.button(key="approve_" + token).click().run()
        with self.backend.actions().receipts.connect() as db:
            db.execute("UPDATE actions SET status='uncertain' WHERE id=?", (token,))
        self.app.run(); self.assert_one_result("**File result**")
        self.assertTrue(any(item.value == "Uncertain" for item in self.app.warning))
        self.assertFalse(any(item.value == "File created" for item in self.app.success))
        self.assertEqual(self.invocations, [])
