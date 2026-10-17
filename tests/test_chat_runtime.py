import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from agent.chat_runtime import session_turn_lock,run_turn
from agent.chat_catalog import ChatCatalog
from agent.runtime_context import approval_handler,local_action_handler

class RuntimeTests(unittest.TestCase):
    def test_same_chat_lock_blocks_and_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            config={"configurable":{"thread_id":"test"}}
            with session_turn_lock(folder,config):
                with self.assertRaises(RuntimeError):
                    with session_turn_lock(folder,config):pass
            with session_turn_lock(folder,config):pass

    def test_turn_uses_latest_checkpoint_and_archives_once(self):
        with tempfile.TemporaryDirectory() as folder:
            catalog=ChatCatalog(Path(folder)/"chats.sqlite3","u","p");catalog.register("default")
            saved={"history":"previous history","summary":"existing summary","route":"direct"}
            seen=[]
            def invoke(state,config):
                seen.append(state)
                return {"answer":"answer","final_answer":"answer","route":"direct"}
            graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values=dict(saved)),invoke=invoke,
                                  update_state=lambda config,values:saved.update(values))
            with patch("agent.context_summary.compact_context",side_effect=lambda summary,history,*a,**k:(summary,history,False)):
                result=run_turn(graph,{"configurable":{"thread_id":"test"}},catalog,"default","question",folder)
            self.assertEqual(seen[0]["history"],"previous history")
            self.assertEqual(len(catalog.transcript("default")),1)
            self.assertIn("question",saved["history"])
            self.assertEqual(result["summary"],"existing summary")

    def test_browser_policy_is_scoped(self):
        self.assertIsNone(approval_handler.get())
        handler=lambda *a:False
        with local_action_handler(handler):self.assertIs(approval_handler.get(),handler)
        self.assertIsNone(approval_handler.get())

if __name__=="__main__":unittest.main()
