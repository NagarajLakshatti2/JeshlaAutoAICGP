import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.project_context import resolve_project_root


class RootTests(unittest.TestCase):
    def test_explicit_root_overrides_only_this_state(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            with patch.dict(os.environ,{"AI_PROJECT_ROOT":a}):
                state={"question":"My project root is "+b+"\nRead build.gradle; do not modify files."}
                self.assertEqual(resolve_project_root(state,a),str(Path(b).resolve()))
                self.assertEqual(os.environ["AI_PROJECT_ROOT"],a)
                self.assertEqual(resolve_project_root({},a),str(Path(a).resolve()))
                self.assertEqual(resolve_project_root({"project_root":b,"question":"Explain it"},a),str(Path(b).resolve()))

    def test_quoted_path_and_colon_command(self):
        with tempfile.TemporaryDirectory(prefix="root with spaces ") as a:
            self.assertEqual(resolve_project_root({"question":'PROJECT ROOT: "'+a+'"'},a),str(Path(a).resolve()))

    def test_documents_and_mentions_cannot_change_root(self):
        with tempfile.TemporaryDirectory() as a:
            with patch.dict(os.environ,{"AI_PROJECT_ROOT":a}):
                self.assertEqual(resolve_project_root({"question":"Explain what project root means", "history":"My project root is invalid", "memory_context":"My project root is invalid"},a),str(Path(a).resolve()))

    def test_invalid_or_multiple_declarations_rejected(self):
        with tempfile.TemporaryDirectory() as a:
            for question in ["My project root is relative/folder","My project root is "+str(Path(a)/"missing"),"My project root is "+a+"\nMy project root is "+a]:
                with self.assertRaises(ValueError):resolve_project_root({"question":question},a)
