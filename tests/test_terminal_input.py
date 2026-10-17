"""Terminal input tests using real prompt_toolkit key processing, no LLM."""
import unittest
from unittest.mock import patch
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from agent.terminal_input import create_editor, read_message, read_confirmation, configure_input

class InputTests(unittest.TestCase):
    def tearDown(self):configure_input("editor")

    def edit(self,keys):
        with create_pipe_input() as inp:
            session=create_editor(input=inp,output=DummyOutput())
            inp.send_text(keys)
            return session.prompt("You> ")

    def test_enter_sends_without_end(self):
        self.assertEqual(self.edit("hello\r"),"hello")

    def test_alt_enter_inserts_newline(self):
        self.assertEqual(self.edit("first\x1b\rsecond\r"),"first\nsecond")

    def test_ctrl_j_inserts_newline(self):
        self.assertEqual(self.edit("first\nsecond\r"),"first\nsecond")

    def test_bracketed_multiline_paste_is_single_draft(self):
        self.assertEqual(self.edit("\x1b[200~first\nsecond\x1b[201~\r"),"first\nsecond")

    def test_edit_previous_line(self):
        self.assertEqual(self.edit("first\nsecond\x1b[A\x01NEW \r"),"NEW first\nsecond")

    def test_ctrl_c_clears_draft(self):
        self.assertEqual(self.edit("old draft\x03new draft\r"),"new draft")

    def test_ctrl_d_empty_exits(self):
        with self.assertRaises(EOFError):self.edit("\x04")

    def test_ctrl_d_nonempty_deletes(self):
        self.assertEqual(self.edit("ab\x1b[D\x04\r"),"a")

    def test_legacy_end_mode(self):
        configure_input("end")
        with patch("builtins.input",side_effect=["first","second","END"]),patch("builtins.print"):
            self.assertEqual(read_message(),"first\nsecond")

    def test_exit_discards_unfinished_legacy_draft(self):
        configure_input("end")
        with patch("builtins.input",side_effect=["unfinished draft","EXIT"]),patch("builtins.print"):
            with self.assertRaises(EOFError):read_message()

    def test_confirmation_requires_no_end(self):
        configure_input("editor")
        with patch("builtins.input",return_value="yes") as reader:
            self.assertEqual(read_confirmation(),"yes")
            reader.assert_called_once()

    def test_non_terminal_reads_one_line(self):
        configure_input("editor")
        with patch("agent.terminal_input.sys.stdin.isatty",return_value=False),patch("builtins.input",return_value="question"):
            self.assertEqual(read_message(),"question")

if __name__=="__main__":unittest.main()
