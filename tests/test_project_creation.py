"""Project creation requires an exact review and never merges or executes setup."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.actions.receipts import LocalActionReceipts, ActionBlocked, ActionDeclined
from agent.interfaces.execution_results import creation_summary
from agent.tools.project_tools import ProjectTools
from agent.tools.project_creation import starter_files
from tests import test_projects as fixtures


class CreationToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.tools = ProjectTools(self.root)
        self.files = [{"relative_path": "src/demo/__init__.py", "content": "# package\n"},
                      {"relative_path": "README.md", "content": "# Demo\n"}]

    def plan(self, name="demo", files=None):
        return self.tools.prepare_project(name, self.files if files is None else files)["plan"]

    def test_prepare_is_read_only_and_plan_content_is_integrity_bound(self):
        plan = self.plan()
        self.assertEqual(list(self.root.iterdir()), [])
        altered = copy.deepcopy(plan); altered["files"][0]["content"] = "different"
        with self.assertRaises(ValueError): self.tools.create_project(altered)
        self.assertFalse((self.root / "demo").exists())
        other = self.root / "other"; other.mkdir()
        with self.assertRaises(ValueError): ProjectTools(other).create_project(plan)

    def test_approval_creates_exact_files_once_without_commands_or_installation(self):
        plan = self.plan(); store = LocalActionReceipts(self.root / "receipts.sqlite3")
        with self.assertRaises(ActionDeclined):
            store.run(self.root, "create_project", {"plan": plan}, self.tools.create_project, lambda *args: False)
        self.assertFalse((self.root / "demo").exists())
        with patch.object(ProjectTools, "run_command", side_effect=AssertionError("no command")):
            result = store.run(self.root, "create_project", {"plan": plan}, self.tools.create_project, lambda *args: True, "approved")
            replay = store.run(self.root, "create_project", {"plan": plan}, lambda **args: self.fail("no replay"), lambda *args: False, "approved")
        self.assertEqual(result, replay)
        self.assertFalse(result["commands_executed"]); self.assertFalse(result["tests_executed"])
        for item in plan["files"]:
            self.assertEqual((self.root / "demo" / item["relative_path"]).read_bytes(), item["content"].encode())

    def test_existing_directory_or_file_is_not_merged_or_overwritten(self):
        plan = self.plan(); destination = self.root / "demo"; destination.mkdir()
        keep = destination / "keep.txt"; keep.write_text("keep")
        with self.assertRaises(ValueError): self.tools.create_project(plan)
        self.assertEqual(list(destination.iterdir()), [keep]); self.assertEqual(keep.read_text(), "keep")
        with self.assertRaises(ValueError): self.plan()
        (self.root / "taken").write_text("file")
        with self.assertRaises(ValueError): self.plan("taken")

    def test_traversal_reserved_credentials_binary_and_case_collisions_are_rejected(self):
        for name in ("../outside", "D:\\outside", ".git", "CON", "new."):
            with self.subTest(folder=name), self.assertRaises(ValueError): self.plan(name)
        for path in ("../outside.py", "C:/outside.py", ".git/config", ".env", "src/CON.py", "build/demo.py", "program.exe"):
            with self.subTest(path=path), self.assertRaises(ValueError): self.plan(files=[{"relative_path": path, "content": "x"}])
        for files in ([{"relative_path": "a.py", "content": "x"}, {"relative_path": "A.py", "content": "y"}],
                      [{"relative_path": "a.py", "content": "x"}, {"relative_path": "a.py/b.py", "content": "y"}],
                      [{"relative_path": "a.py", "content": "\0"}],
                      [{"relative_path": "a.py", "content": "x" * 50001}]):
            with self.subTest(files=str(files)[:60]), self.assertRaises(ValueError): self.plan(files=files)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_partial_failure_is_uncertain_and_never_automatically_removed_or_replayed(self):
        plan = self.plan(); store = LocalActionReceipts(self.root / "r.sqlite3")
        original = Path.open
        def fail_second(path, *args, **kwargs):
            if path.name == "__init__.py" and args and args[0] == "xb": raise OSError("fixture interruption")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", fail_second):
            with self.assertRaises(OSError):
                store.run(self.root, "create_project", {"plan": plan}, self.tools.create_project, lambda *args: True, "partial")
        self.assertEqual(store.get("partial")["status"], "uncertain")
        self.assertEqual((self.root / "demo/README.md").read_text(), "# Demo\n")
        with self.assertRaises(ActionBlocked):
            store.run(self.root, "create_project", {"plan": plan}, lambda **args: self.fail("no retry"), lambda *args: True, "partial")
        self.assertTrue((self.root / "demo").exists())

    def test_nested_python_template_runs_standard_library_test_without_installing(self):
        files = starter_files("example-agent", "python", "company.agent")
        result = self.tools.create_project(self.plan("example-agent", files))
        destination = Path(result["project_root"])
        self.assertTrue((destination / "src/company/__init__.py").exists())
        self.assertTrue((destination / "src/company/agent/__init__.py").exists())
        env = dict(os.environ, PYTHONPATH=str(destination / "src"), PYTHONDONTWRITEBYTECODE="1")
        run = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=destination, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)
        self.assertFalse((destination / ".git").exists())

    def test_java_template_has_separate_page_test_packages_and_no_fake_wrapper(self):
        files = starter_files("java-pilot", "java-playwright", "com.example.pilot")
        names = {item["relative_path"] for item in files}
        self.assertIn("src/main/java/com/example/pilot/ExamplePage.java", names)
        self.assertIn("src/test/java/com/example/pilot/LocalPageTest.java", names)
        self.assertNotIn("gradlew.bat", names)
        self.assertIn("does not bundle a Gradle wrapper", next(item["content"] for item in files if item["relative_path"] == "README.md"))
        for package, template in (("class", "python"), ("company..agent", "python"), ("com.class.demo", "java-playwright")):
            with self.assertRaises(ValueError): starter_files("demo", template, package)

    def test_created_summary_does_not_claim_tests_and_requires_matching_manifest(self):
        plan = self.plan(); result = self.tools.create_project(plan)
        payload = {"arguments": {"plan": plan}, "result": result, "receipt_status": "completed"}
        summary = creation_summary(payload)
        self.assertEqual(summary["status"], "Project files created")
        self.assertTrue(any("not installation" in line for line in summary["limits"]))
        payload["receipt_status"] = "uncertain"
        self.assertEqual(creation_summary(payload)["status"], "Uncertain")
        payload["receipt_status"] = "completed"; payload["result"]["files"] = []
        self.assertEqual(creation_summary(payload)["status"], "Creation not verified")


class CreationBackendTests(unittest.TestCase):
    setUp = fixtures.ProjectBackendTests.setUp

    def test_prepare_decline_create_register_and_replay_stay_owner_bound(self):
        review = self.base.prepare_new_project("New Demo", str(self.root), "python", "company.demo")
        destination = Path(review["proposal"]["arguments"]["plan"]["destination"])
        self.assertFalse(destination.exists())
        other = copy.copy(self.base); other.user = "other"
        with self.assertRaises(ActionBlocked): other.create_new_project(review["token"], review["name"])
        self.base.cancel_new_project(review["token"])
        with self.assertRaises(ActionBlocked): self.base.create_new_project(review["token"], review["name"])
        self.assertFalse(destination.exists())
        review = self.base.prepare_new_project("New Demo", str(self.root), "python", "company.demo")
        result = self.base.create_new_project(review["token"], review["name"])
        again = self.base.create_new_project(review["token"], review["name"])
        self.assertEqual(result["project"], again["project"]); self.assertTrue(again["replayed"])
        self.assertEqual(self.base.project_store().get(result["project"]["id"])["root"], str(destination))
        self.assertEqual(self.invocations, [])

    def test_registration_failure_can_reuse_completed_receipt_without_file_recreation(self):
        review = self.base.prepare_new_project("Recover Demo", str(self.root), "python", "recover.demo")
        with patch("agent.storage.projects.ProjectCatalog.add_local", side_effect=OSError("fixture registration unavailable")):
            with self.assertRaises(OSError): self.base.create_new_project(review["token"], review["name"])
        self.assertEqual(self.base.new_project_status(review["token"])["proposal"], "completed")
        with patch.object(ProjectTools, "create_project", side_effect=AssertionError("must not execute again")):
            result = self.base.create_new_project(review["token"], review["name"])
        self.assertTrue(result["replayed"]); self.assertTrue(Path(result["project"]["root"]).is_dir())


class CreationUITests(unittest.TestCase):
    setUp = fixtures.ProjectUITests.setUp
    open_projects = fixtures.ProjectUITests.open_projects

    def creator(self):
        self.app.run(); self.open_projects()
        self.app.button(key="add_project_menu").click().run()
        self.app.segmented_control(key="setup_project_type").set_value("New project").run()
        self.app.text_input(key="create_project_name").set_value("UI Demo").run()
        self.app.text_input(key="create_project_parent").set_value(str(self.root)).run()

    def test_preview_refresh_cancel_and_create_require_explicit_approval(self):
        self.creator()
        self.app.button(key="prepare_new_project").click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse((self.root / "UI-Demo").exists())
        self.app.run(); self.assertFalse((self.root / "UI-Demo").exists())
        self.assertTrue(any(item.label == "pyproject.toml" for item in self.app.expander))
        self.app.button(key="cancel_new_project").click().run()
        self.assertFalse((self.root / "UI-Demo").exists())
        self.app.button(key="prepare_new_project").click().run()
        self.app.button(key="approve_new_project").click().run()
        self.assertFalse(self.app.exception); self.assertTrue((self.root / "UI-Demo/pyproject.toml").is_file())
        row = next(row for row in self.base.project_store().list() if row["name"] == "UI Demo")
        self.assertTrue(any(button.key == "choose_project_" + row["id"] for button in self.app.button))
        self.app.button(key="choose_project_" + row["id"]).click().run()
        self.assertFalse(self.app.exception); self.assertEqual(self.app.session_state["selected_project_id"], row["id"])
        self.assertFalse(self.app.session_state["chat_opened"])
        self.assertEqual(self.invocations, [])

    def test_input_change_withdraws_old_review_and_preexisting_folder_is_protected(self):
        self.creator(); self.app.button(key="prepare_new_project").click().run()
        self.app.text_input(key="create_project_name").set_value("Changed Demo").run()
        self.assertFalse(any(button.key == "approve_new_project" for button in self.app.button))
        destination = self.root / "Changed-Demo"; destination.mkdir(); (destination / "keep.txt").write_text("keep")
        self.app.button(key="prepare_new_project").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("already exists" in item.value for item in self.app.warning))
        self.assertEqual(list(destination.iterdir()), [destination / "keep.txt"])
        self.assertFalse((self.root / "UI-Demo").exists())
