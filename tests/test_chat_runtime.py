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
            saved={"history":"previous history","summary":"existing summary","route":"direct","task_status":"incomplete"}
            seen=[]
            def invoke(state,config):
                seen.append(state)
                return {"answer":"answer","final_answer":"answer","route":"direct"}
            graph=SimpleNamespace(get_state=lambda config:SimpleNamespace(values=dict(saved)),invoke=invoke,
                                  update_state=lambda config,values:saved.update(values))
            with patch("agent.context_summary.compact_context",side_effect=lambda summary,history,*a,**k:(summary,history,False)):
                result=run_turn(graph,{"configurable":{"thread_id":"test"}},catalog,"default","question",folder)
            self.assertEqual(seen[0]["history"],"previous history")
            self.assertEqual(seen[0]["task_status"],"completed")
            self.assertEqual(len(catalog.transcript("default")),1)
            self.assertIn("question",saved["history"])
            self.assertEqual(result["summary"],"existing summary")

    def test_save_failures_preserve_answer_without_reexecuting(self):
        for archive_fails,checkpoint_fails in ((True,False),(False,True),(True,True)):
            with self.subTest(archive=archive_fails,checkpoint=checkpoint_fails), tempfile.TemporaryDirectory() as folder:
                catalog=Mock()
                if archive_fails: catalog.append.side_effect=OSError("private filesystem details")
                graph=Mock()
                graph.get_state.return_value=SimpleNamespace(values={"history":"prior","summary":""})
                graph.invoke.return_value={"answer":"Action receipt saved: fixture", "task_status":"completed"}
                if checkpoint_fails: graph.update_state.side_effect=OSError("private checkpoint details")
                with patch("agent.context_summary.compact_context",return_value=("","retained",False)) as compact:
                    result=run_turn(graph,{"configurable":{"thread_id":"test"}},catalog,"default","question",folder)
                self.assertEqual(graph.invoke.call_count,1)
                self.assertEqual(catalog.append.call_count,1)
                self.assertEqual(result["answer"],"Action receipt saved: fixture")
                self.assertEqual(result["task_status"],"completed")
                self.assertEqual(result["persistence_status"],{"archive_saved":not archive_fails,"checkpoint_saved":not checkpoint_fails})
                self.assertNotIn("private",str(result["notices"]))
                if archive_fails:
                    compact.assert_not_called()
                    self.assertIn("prior",result["history"])
                if checkpoint_fails:self.assertIn("Do not repeat an action",str(result["notices"]))
                with session_turn_lock(folder,{"configurable":{"thread_id":"test"}}):pass

    def test_kernel_lock_releases_after_process_exit(self):
        import subprocess,sys
        worker = ("import sys,os; from agent.chat_runtime import session_turn_lock; "
                  "cm=session_turn_lock(sys.argv[1],{'configurable':{'thread_id':'crash'}}); "
                  "cm.__enter__(); print('locked',flush=True); sys.stdin.readline(); os._exit(73)")
        with tempfile.TemporaryDirectory() as folder:
            child=subprocess.Popen([sys.executable,"-c",worker,folder],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(),"locked")
                config={"configurable":{"thread_id":"crash"}}
                with self.assertRaises(RuntimeError):
                    with session_turn_lock(folder,config):pass
                child.communicate("exit\n",timeout=15)
                self.assertEqual(child.returncode,73)
                with session_turn_lock(folder,config):pass
                self.assertEqual(len(list((Path(folder)/"outputs/chat_locks").glob("*.guard"))),1)
            finally:
                if child.poll() is None:child.kill();child.communicate()

    def test_legacy_lock_is_never_removed(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"outputs/chat_locks"/(hashlib.sha256(b"legacy").hexdigest()+".lock")
            path.parent.mkdir(parents=True);path.write_text("123")
            with self.assertRaises(RuntimeError):
                with session_turn_lock(folder,{"configurable":{"thread_id":"legacy"}}):pass
            self.assertEqual(path.read_text(),"123")

    def test_explicit_memory_controls_never_trigger_summary_model(self):
        for route in ("memory","memory_command"):
            with self.subTest(route=route),tempfile.TemporaryDirectory() as folder:
                catalog=Mock();saved={"history":"previous history "*1500,"summary":"existing summary"}
                graph=Mock();graph.get_state.return_value=SimpleNamespace(values=saved)
                graph.invoke.return_value={"route":route,"answer":"local memory result","task_status":"completed"}
                with patch("agent.context_summary.compact_context",side_effect=AssertionError("No compaction for local controls")) as compact:
                    result=run_turn(graph,{"configurable":{"thread_id":"fixture"}},catalog,"default","SHOW MEMORY",folder)
                compact.assert_not_called();catalog.append.assert_called_once()
                graph.update_state.assert_called_once()
                self.assertEqual(result["answer"],"local memory result")
                self.assertEqual(result["summary"],"existing summary")
                self.assertEqual(result["notices"],[])

    def test_browser_policy_is_scoped(self):
        self.assertIsNone(approval_handler.get())
        handler=lambda *a:False
        with local_action_handler(handler):self.assertIs(approval_handler.get(),handler)
        self.assertIsNone(approval_handler.get())

if __name__=="__main__":unittest.main()
