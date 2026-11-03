"""Explicit snapshot preparation and format isolation in the downloads UI."""
import base64
import io
import unittest
import zipfile
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from agent.actions.receipts import ActionBlocked


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a9sAAAAASUVORK5CYII="
)


class LegacyDownloadsBackend:
    def __init__(self):
        self.calls = []
        self.failure = None
        self.files = [{"id": "inspection", "path": "inspection.png"}]
        self.original = {"name": "inspection.png", "mime": "image/png", "data": PNG_BYTES}

    def generated_files(self, session):
        return self.files

    def generated_file(self, session, token):
        self.calls.append(("original", session, token))
        if self.failure == "original":
            raise ActionBlocked("The file changed after approval.")
        return self.original


class BinaryDownloadsBackend(LegacyDownloadsBackend):
    def __init__(self):
        super().__init__()
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
            output.writestr("inspection.png", PNG_BYTES)
        self.archive = {"name": "inspection.zip", "mime": "application/zip", "data": archive.getvalue()}

    def generated_zip_file(self, session, token):
        self.calls.append(("zip", session, token))
        if self.failure == "zip":
            raise ActionBlocked("The file changed after approval.")
        return self.archive


class BinaryDownloadsUiTests(unittest.TestCase):
    def setUp(self):
        self.backend = BinaryDownloadsBackend()
        self.app = AppTest.from_string(
            "import streamlit as st\n"
            "from agent.interfaces.generated_files import render_generated_files\n"
            "backend = st.session_state['backend']\n"
            "session = st.session_state['chat']\n"
            "render_generated_files(backend, session, key_prefix='files_')\n"
            "if st.session_state.get('second_pane', False):\n"
            "    render_generated_files(backend, session, key_prefix='conversation_')\n",
            default_timeout=15,
        )
        self.app.session_state["backend"] = self.backend
        self.app.session_state["chat"] = "chat-a"

    def run_app(self):
        with patch("agent.interfaces.generated_files.st.download_button", wraps=st.download_button) as download:
            self.app.run()
        self.assertFalse(self.app.exception)
        return download.call_args_list

    def select_format(self, value, prefix="files_", token="inspection"):
        self.app.selectbox(key=prefix + "generated_format_" + token).select(value)
        return self.run_app()

    def prepare(self, prefix="files_", token="inspection"):
        self.app.button(key=prefix + "prepare_generated_" + token).click()
        return self.run_app()

    def assert_snapshot_call(self, call, snapshot):
        self.assertEqual(call.args, ("Download " + snapshot["name"], snapshot["data"]))
        self.assertEqual(call.kwargs["file_name"], snapshot["name"])
        self.assertEqual(call.kwargs["mime"], snapshot["mime"])

    def test_format_selection_is_draft_only(self):
        self.assertEqual(self.run_app(), [])
        self.assertEqual(self.app.selectbox[0].options, ["Original file", "ZIP archive"])
        self.assertEqual(self.select_format("ZIP archive"), [])
        self.assertEqual(self.select_format("Original file"), [])
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(len(self.app.get("download_button")), 0)

    def test_original_and_zip_prepare_once_and_preserve_typed_bytes(self):
        self.run_app()
        self.assert_snapshot_call(self.prepare()[0], self.backend.original)
        self.assertEqual(self.backend.calls, [("original", "chat-a", "inspection")])
        self.assertEqual(self.select_format("ZIP archive"), [])
        self.assert_snapshot_call(self.prepare()[0], self.backend.archive)
        self.assert_snapshot_call(self.run_app()[0], self.backend.archive)
        self.assertEqual(self.backend.calls, [("original", "chat-a", "inspection"), ("zip", "chat-a", "inspection")])
        cache = self.app.session_state["generated_downloads"]
        self.assertEqual(cache[("chat-a", "inspection")], self.backend.original)
        self.assertEqual(cache[("chat-a", "inspection", "ZIP archive")], self.backend.archive)
        self.assert_snapshot_call(self.select_format("Original file")[0], self.backend.original)
        self.assertEqual(len(self.backend.calls), 2)

    def test_two_panes_keep_different_formats_without_exposing_prior_format(self):
        self.app.session_state["second_pane"] = True
        self.run_app()
        self.prepare()
        calls = self.select_format("ZIP archive", prefix="conversation_")
        self.assertEqual(len(calls), 1)
        self.assert_snapshot_call(calls[0], self.backend.original)
        self.assertEqual(calls[0].kwargs["key"], "files_generated_download_inspection")
        calls = self.prepare(prefix="conversation_")
        self.assertEqual(len(calls), 2)
        self.assert_snapshot_call(calls[0], self.backend.original)
        self.assert_snapshot_call(calls[1], self.backend.archive)
        calls = self.run_app()
        self.assert_snapshot_call(calls[0], self.backend.original)
        self.assert_snapshot_call(calls[1], self.backend.archive)
        self.assertEqual(len(self.backend.calls), 2)

    def test_snapshot_cache_isolates_sessions_and_tokens(self):
        self.backend.files.append({"id": "other", "path": "other.png"})
        self.run_app()
        self.assertEqual(len(self.prepare()), 1)
        self.app.session_state["chat"] = "chat-b"
        self.assertEqual(self.run_app(), [])
        self.assertEqual(self.select_format("ZIP archive"), [])
        self.assertEqual(len(self.prepare()), 1)
        self.app.session_state["chat"] = "chat-a"
        self.assertEqual(self.run_app(), [])
        self.assert_snapshot_call(self.select_format("Original file")[0], self.backend.original)
        cache = self.app.session_state["generated_downloads"]
        self.assertEqual(set(cache), {("chat-a", "inspection"), ("chat-b", "inspection", "ZIP archive")})
        self.assertEqual(self.backend.calls, [("original", "chat-a", "inspection"), ("zip", "chat-b", "inspection")])

    def test_failed_prepare_withdraws_only_the_selected_snapshot(self):
        self.run_app()
        self.prepare()
        self.select_format("ZIP archive")
        self.prepare()
        self.backend.failure = "zip"
        self.assertEqual(self.prepare(), [])
        self.assertEqual(self.app.warning[0].value, "The file changed after approval.")
        cache = self.app.session_state["generated_downloads"]
        self.assertNotIn(("chat-a", "inspection", "ZIP archive"), cache)
        self.assertIn(("chat-a", "inspection"), cache)
        self.assert_snapshot_call(self.select_format("Original file")[0], self.backend.original)
        self.backend.failure = "original"
        self.assertEqual(self.prepare(), [])
        self.assertNotIn(("chat-a", "inspection"), self.app.session_state["generated_downloads"])

    def test_legacy_backend_and_original_cache_remain_usable(self):
        legacy = LegacyDownloadsBackend()
        legacy.original = {"name": "approved.txt", "mime": "text/plain", "data": b"Approved text"}
        self.app.session_state["backend"] = legacy
        self.app.session_state["generated_downloads"] = {("chat-a", "inspection"): legacy.original}
        self.assert_snapshot_call(self.run_app()[0], legacy.original)
        self.assertEqual(len(self.app.selectbox), 0)
        self.assertEqual(legacy.calls, [])
        self.assert_snapshot_call(self.prepare()[0], legacy.original)
        self.assertEqual(legacy.calls, [("original", "chat-a", "inspection")])
