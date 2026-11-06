import tempfile
import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest


class TerminalUITests(unittest.TestCase):
    def test_terminal_queues_owned_exact_action(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = Mock()
            backend.user = "owner"
            backend.space = "space"
            backend.request_scope.return_value = {"project_id": "fixture", "bound_project_root": folder}
            with patch("agent.interfaces.project_terminal.selected_backend", return_value=backend), patch(
                    "agent.interfaces.project_terminal.ensure_message_chat", return_value="chat"):
                app = AppTest.from_string("""
from agent.interfaces.project_terminal import render_project_terminal
render_project_terminal(None)
""").run()
                self.assertFalse(app.exception)
                next(button for button in app.button if button.label == "Request command approval").click().run()
                self.assertFalse(app.exception)
            args = backend.actions.return_value.propose.call_args.args
            self.assertEqual(args[:4], ("owner", "space", "chat", "run_command"))
            self.assertEqual(args[4]["project_root"], folder)
            self.assertEqual(args[4]["arguments"], {"command": ["python", "--version"], "timeout": 60})


    def test_history_is_persistent_and_scoped_to_owner_chat_and_root(self):
        from pathlib import Path
        from agent.actions.browser import BrowserActions
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            other = root / "other"
            other.mkdir()
            path = root / "receipts.sqlite3"
            actions = BrowserActions(path)
            def queue(directory):
                return actions.propose("owner", "space", "chat", "run_command",
                    {"project_root": str(directory), "action": "run_command",
                     "arguments": {"command": ["python", "--version"], "timeout": 60}})
            token = queue(root)
            queue(other)
            reopened = BrowserActions(path)
            history = reopened.command_history("owner", "space", "chat", root)
            self.assertEqual([row["id"] for row in history], [token])
            self.assertEqual(history[0]["status"], "pending")
            reopened.decline("owner", "space", "chat", token)
            history = BrowserActions(path).command_history("owner", "space", "chat", root)
            self.assertEqual(history[0]["status"], "declined")
            self.assertEqual(reopened.command_history("other-owner", "space", "chat", root), [])
            self.assertEqual(reopened.command_history("owner", "space", "other-chat", root), [])


    def test_owned_process_honours_stop_and_captures_normal_output(self):
        from agent.actions.command_process import run_command
        from agent.tools.project_tools import ProjectTools
        with tempfile.TemporaryDirectory() as folder:
            tools = ProjectTools(folder)
            result = run_command(tools, ["python", "-c", "import time; time.sleep(30)"], 60,
                                 cancelled=lambda: True)
            self.assertTrue(result["cancelled"])
            result = run_command(tools, ["python", "-c", "print('fixture output')"], 10,
                                 cancelled=lambda: False)
            self.assertFalse(result["cancelled"])
            self.assertIn("fixture output", result["stdout"])


    def test_running_command_stop_is_owned_and_receipt_replay_safe(self):
        import time
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        from agent.actions.browser import BrowserActions
        from agent.actions.receipts import ActionBlocked
        with tempfile.TemporaryDirectory() as folder:
            store = BrowserActions(Path(folder) / "receipts.sqlite3")
            token = store.propose("owner", "space", "chat", "run_command",
                {"project_root": folder, "action": "run_command",
                 "arguments": {"command": ["python", "-c", "import time; time.sleep(30)"], "timeout": 60}})
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(store.execute, "owner", "space", "chat", token)
                deadline = time.monotonic() + 10
                while store._row("owner", "space", "chat", token)["status"] != "running":
                    if time.monotonic() >= deadline:
                        self.fail("Command never entered running state")
                    time.sleep(0.05)
                with self.assertRaises(ActionBlocked):
                    store.cancel_command("other-owner", "space", "chat", token, folder)
                store.cancel_command("owner", "space", "chat", token, folder)
                result, replayed = future.result(timeout=15)
            self.assertTrue(result["cancelled"])
            self.assertFalse(replayed)
            again, replayed = store.execute("owner", "space", "chat", token)
            self.assertTrue(replayed)
            self.assertEqual(result, again)


    def test_persistent_session_input_scope_and_stale_revision(self):
        import time
        from pathlib import Path
        from agent.actions.terminal_sessions import start, send, snapshot, stop
        from agent.tools.project_tools import ProjectTools
        with tempfile.TemporaryDirectory() as folder:
            identity = ("owner", "space", "chat", str(Path(folder).resolve()))
            initial = start(identity, ProjectTools(folder),
                ["python", "-u", "-c", "import sys; [print(line.strip(), flush=True) for line in sys.stdin]"], 10)
            token = initial["terminal_id"]
            try:
                send(identity, token, 0, "hello session\n")
                with self.assertRaises(ValueError):
                    send(identity, token, 0, "stale")
                with self.assertRaises(ValueError):
                    snapshot(("other", *identity[1:]), token)
                deadline = time.monotonic() + 5
                while "hello session" not in snapshot(identity, token)["stdout"] and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertIn("hello session", snapshot(identity, token)["stdout"])
            finally:
                stop(identity, token, 1)

