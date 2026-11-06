import tempfile
import unittest
from pathlib import Path
from agent.runtime.project_skills import project_skills


class ProjectSkillTests(unittest.TestCase):
    def test_project_discovery_reads_only_bounded_skill_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            selected = root / "selected"
            valid = selected / ".agents/skills/review"
            valid.mkdir(parents=True)
            (valid / "SKILL.md").write_text("Review the project source.", encoding="utf-8")
            large = selected / ".agents/skills/large"
            large.mkdir()
            (large / "SKILL.md").write_text("x" * 16001, encoding="utf-8")
            other = root / "other/.agents/skills/private"
            other.mkdir(parents=True)
            (other / "SKILL.md").write_text("Other project content.", encoding="utf-8")
            rows = project_skills(selected)
            self.assertEqual([row["name"] for row in rows], ["review"])
            self.assertEqual(rows[0]["path"], ".agents/skills/review/SKILL.md")
            self.assertEqual(project_skills(root / "empty"), [])


    def test_skill_ui_previews_and_drafts_current_project_skill(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            skill = root / ".agents/skills/review"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("Review selected project files.", encoding="utf-8")
            source = """
import streamlit as st
from agent.interfaces.skills import render_skills
class Backend:
    project_id = "project-fixture"
    def request_scope(self):
        return {"project_id": self.project_id, "bound_project_root": ROOT}
st.session_state.setdefault("active_chat", "chat-fixture")
st.session_state.setdefault("selected_project_id", "project-fixture")
render_skills(Backend(), "chat-fixture")
st.text_area("Message draft", key="message")
""".replace("ROOT", repr(str(root)))
            app = AppTest.from_string(source).run()
            self.assertFalse(app.exception)
            self.assertIn("Review selected project files.", app.code[0].value)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertIn("Review selected project files.", app.text_area[0].value)
            app.session_state["selected_project_id"] = "different-project"
            app.session_state["message"] = "Keep my new draft"
            app.button[0].click().run()
            self.assertEqual(app.text_area[0].value, "Keep my new draft")
