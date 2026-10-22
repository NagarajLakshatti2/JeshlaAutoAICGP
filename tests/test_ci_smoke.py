"""Regression checks for CI false positives; no application/provider is started."""
import unittest
from evaluations.ci_smoke import check_initial_page


class CiPageAcceptanceTests(unittest.TestCase):
    def page(self, tail):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_string("import streamlit as st\nst.title('What would you like to build?')\n" + tail, default_timeout=30).run()

    def test_rendered_error_does_not_pass_startup(self):
        page = self.page("st.chat_input('Message')\nst.error('Synthetic fixture error')")
        with self.assertRaisesRegex(RuntimeError, "displayed an error"):
            check_initial_page(page)

    def test_script_exception_does_not_pass_startup(self):
        page = self.page("raise RuntimeError('Synthetic fixture exception')")
        with self.assertRaisesRegex(RuntimeError, "raised an exception"):
            check_initial_page(page)

    def test_duplicate_composer_does_not_pass_startup(self):
        page = self.page("st.chat_input('First', key='first')\nst.chat_input('Second', key='second')")
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            check_initial_page(page)

    def test_expected_initial_page_passes(self):
        check_initial_page(self.page("st.chat_input('Message')"))


class CiProcessDeadlineTests(unittest.TestCase):
    def test_timed_out_worker_fails_and_removes_owned_state(self):
        import tempfile
        from pathlib import Path
        from evaluations.ci_smoke import run_check
        with tempfile.TemporaryDirectory(prefix="ci-deadline-test-") as directory:
            report = run_check("console", Path(directory), timeout=0.01)
            self.assertEqual(report["status"], "P")
            self.assertTrue(report["timed_out"])
            self.assertTrue(report["owned_process_stopped"])
            self.assertTrue(report["fixture_removed"])
