"""Bounded project explorer UI uses local scope and never submits a chat."""
from pathlib import Path
import unittest
from unittest.mock import patch

from agent.interfaces.project_files import entry_key, project_view_key


class ProjectFileUITests(unittest.TestCase):
    def setUp(self):
        from tests.test_projects import ProjectUITests
        ProjectUITests.setUp(self)
        (self.a / "nested").mkdir()
        (self.a / "nested" / "notes.txt").write_text("Project A notes", encoding="utf-8")
        (self.a / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        (self.b / "nested").mkdir()
        (self.b / "nested" / "notes.txt").write_text("Project B notes", encoding="utf-8")

    def select(self, project):
        self.app.button(key="projects_menu").click().run()
        self.app.button(key="choose_project_" + project["id"]).click().run()
        self.assertFalse(self.app.exception)

    def open_files(self):
        self.app.button(key="browse_project_files").click().run()
        self.assertFalse(self.app.exception)

    def prefix(self, backend=None):
        backend = backend or self.view_a
        return project_view_key(backend, backend.request_scope())

    def entry(self, path, backend=None):
        return self.app.button(key=entry_key(self.prefix(backend), path))

    def test_entry_is_disabled_without_selected_project(self):
        self.app.run()
        self.assertTrue(self.app.button(key="browse_project_files").disabled)
        self.assertEqual(self.invocations, [])

    def test_folder_and_preview_preserve_chat_without_model_or_action(self):
        self.app.run(); self.select(self.pa)
        active = self.app.session_state["active_chat"]
        with patch("agent.tools.project_tools.ProjectTools.run_command", side_effect=AssertionError("no command")), patch("requests.sessions.Session.request", side_effect=AssertionError("no request")):
            self.open_files()
            self.entry("nested").click().run()
            self.entry("nested/notes.txt").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Project A notes" in row.value for row in self.app.code))
        self.assertEqual(self.app.session_state["active_chat"], active)
        self.assertIsNone(self.view_a.get_chat(active))
        self.assertEqual(self.invocations, [])

    def test_navigation_up_and_root_clear_selected_preview(self):
        self.app.run(); self.select(self.pa); self.open_files()
        self.entry("nested").click().run()
        self.entry("nested/notes.txt").click().run()
        self.app.button(key=self.prefix() + "_up").click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(any("Project A notes" in row.value for row in self.app.code))
        self.assertTrue(self.app.button(key=self.prefix() + "_up").disabled)
        self.entry("nested").click().run()
        self.app.button(key=self.prefix() + "_root").click().run()
        self.assertTrue(self.app.button(key=self.prefix() + "_root").disabled)

    def test_binary_is_listed_without_preview_action(self):
        self.app.run(); self.select(self.pa); self.open_files()
        self.assertTrue(self.entry("image.png").disabled)
        self.assertFalse(self.app.code)

    def test_project_switch_does_not_expose_previous_preview(self):
        self.app.run(); self.select(self.pa); self.open_files()
        self.entry("nested").click().run()
        self.entry("nested/notes.txt").click().run()
        self.app.button(key="close_project_files").click().run()
        self.select(self.pb); self.open_files()
        self.assertFalse(self.app.exception)
        self.assertFalse(any("Project A notes" in row.value for row in self.app.code))
        self.entry("nested", self.view_b).click().run()
        self.entry("nested/notes.txt", self.view_b).click().run()
        self.assertTrue(any("Project B notes" in row.value for row in self.app.code))
        self.assertFalse(any("Project A notes" in row.value for row in self.app.code))
        self.assertEqual(self.invocations, [])

    def test_preview_refresh_reads_current_bytes_without_chat(self):
        self.app.run(); self.select(self.pa); self.open_files()
        self.entry("nested").click().run()
        self.entry("nested/notes.txt").click().run()
        (self.a / "nested/notes.txt").write_text("Updated current notes", encoding="utf-8")
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Updated current notes" in row.value for row in self.app.code))
        self.assertFalse(any("Project A notes" in row.value for row in self.app.code))
        self.assertEqual(self.invocations, [])

    def test_deleted_preview_shows_local_message_and_no_stale_content(self):
        self.app.run(); self.select(self.pa); self.open_files()
        self.entry("nested").click().run()
        self.entry("nested/notes.txt").click().run()
        (self.a / "nested/notes.txt").unlink()
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertFalse(any("Project A notes" in row.value for row in self.app.code))
        self.assertTrue(any("file is unavailable" in row.value for row in self.app.warning))
        self.assertFalse(any("provider" in row.value.lower() for row in self.app.warning))

    def test_close_returns_to_same_draft_and_keeps_one_composer(self):
        self.app.run(); self.select(self.pa)
        active = self.app.session_state["active_chat"]
        self.open_files()
        self.app.button(key="close_project_files").click().run()
        self.assertFalse(self.app.exception)
        self.assertIsNone(self.app.session_state["ui_dialog"])
        self.assertEqual(self.app.session_state["active_chat"], active)
        self.assertEqual(len(self.app.chat_input), 1)
        self.assertEqual(self.invocations, [])


if __name__ == "__main__":
    unittest.main()
