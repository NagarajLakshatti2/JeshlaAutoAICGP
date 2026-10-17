"""Command validation and CLI no-model regression checks."""
import argparse
import ast
import hashlib
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from agent.chat_catalog import validate_chat_command

class CommandTests(unittest.TestCase):
    def test_exact_multiline_placeholder_is_rejected(self):
        command,error=validate_chat_command("OPEN CHAT <paste-the-chat-ID>\nchat-abc")
        self.assertIn("one line",error)

    def test_missing_or_extra_id(self):
        for text in ["OPEN CHAT","OPEN CHAT <id>","OPEN CHAT a b","SESSION","LIST CHATS extra"]:
            with self.subTest(text=text):self.assertIsNotNone(validate_chat_command(text)[1])

    def test_case_and_spacing(self):
        self.assertEqual(validate_chat_command("open   chat   chat-AbC"),("OPEN CHAT chat-AbC",None))
        self.assertEqual(validate_chat_command("list chats"),("LIST CHATS",None))
        self.assertEqual(validate_chat_command("session Learning"),("SESSION Learning",None))

    def test_titles(self):
        self.assertEqual(validate_chat_command("new chat Java Learning"),("NEW CHAT Java Learning",None))
        self.assertIsNone(validate_chat_command("NEW CHAT "+"x"*80)[1])
        self.assertIsNotNone(validate_chat_command("NEW CHAT "+"x"*81)[1])

    def test_ordinary_question_not_intercepted(self):
        text="How do I open a chat in my application?"
        self.assertEqual(validate_chat_command(text),(text,None))

    def test_malformed_command_never_invokes_graph(self):
        source=(Path(__file__).resolve().parents[1]/"agent/langgraph/langgraph_agent.py").read_text(encoding="utf-8")
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in {"main","session_config","restore_session"}]
        fake=SimpleNamespace(get_state=Mock(return_value=SimpleNamespace(values={})),invoke=Mock(side_effect=AssertionError("Model graph must not run")))
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{}), patch("sys.argv",["agent","--session","default"]), patch("builtins.input",side_effect=["OPEN CHAT <paste-the-chat-ID>","chat-abc","END","OPEN CHAT","END","EXIT"]), patch("builtins.print") as output:
            scope={"argparse":argparse,"ast":ast,"hashlib":hashlib,"json":json,"os":os,"re":re,"PROJECT_ROOT":Path(folder),"LLM_PROVIDER":"groq","graph":fake}
            exec(compile(ast.Module(body=nodes,type_ignores=[]),"cli-test","exec"),scope)
            scope["main"]()
            fake.invoke.assert_not_called()
            self.assertTrue(any("Chat command format" in str(call) for call in output.call_args_list))

if __name__=="__main__":unittest.main()
