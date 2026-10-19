"""Shared console/browser chat execution and checkpoint/archive handling."""
from contextlib import contextmanager
import os
from pathlib import Path
import threading
import time

process_turn_lock=threading.RLock()

@contextmanager
def session_turn_lock(root,config):
    """Use a kernel-owned lock: process exit releases it, without stale deletion.

    Legacy .lock files remain conservative blockers during migration. Guard files
    are persistent coordination files, never removed or replaced while in use.
    """
    import hashlib
    thread=config["configurable"]["thread_id"]
    directory=Path(root)/"outputs/chat_locks"
    directory.mkdir(parents=True,exist_ok=True)
    stem=hashlib.sha256(thread.encode()).hexdigest()
    legacy=directory/(stem+".lock")
    if legacy.exists():
        raise RuntimeError("This chat is busy or has a legacy chat lock. Close old agent processes and inspect the legacy lock before recovery.")
    handle=open(directory/(stem+".guard"),"a+b")
    locked=False
    try:
        # Windows byte-range locks require a byte. Concurrent initial writes are
        # harmless; all contenders lock the same first byte of the same file.
        handle.seek(0,os.SEEK_END)
        if handle.tell()==0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked=True
        except OSError:
            raise RuntimeError("This chat is busy in another window. Wait for it to finish.") from None
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()


def run_turn(graph,config,catalog,session,question,root):
    from agent.runtime.summaries import compact_context,summary_failure_reason
    from agent.runtime.summary_model import call_summary_messages
    notices=[]
    with process_turn_lock,session_turn_lock(root,config):
        saved=graph.get_state(config).values or {}
        history=saved.get("history","");summary=saved.get("summary","")
        state={"conversation_session":session,"question":question,"route":"","prompt":"","context":"","answer":"","final_answer":"","task_status":"completed","execution_outcome":"unclassified",
               "history":history[-16000:],"summary":summary,"previous_route":saved.get("route",""),
               "summary_retry_at":saved.get("summary_retry_at",0)}
        result=graph.invoke(state,config=config)
        history=history+"\nUser: "+question+"\nAssistant: "+result["answer"]
        archived=False
        try:
            catalog.append(session,question,result["answer"])
            archived=True
        except Exception:
            notices.append("The answer was generated, but the transcript archive could not be updated.")
        retry_at=float(saved.get("summary_retry_at",0) or 0)
        # Deterministic memory controls must remain usable without a provider.
        # Preserve archive/checkpoint writes; compact on a later conversation turn.
        local_control=result.get("route") in {"memory","memory_command"}
        if archived and not local_control and time.time()>=retry_at:
            try:
                summary,history,changed=compact_context(summary,history,call_summary_messages,
                    threshold=int(os.getenv("AI_SUMMARY_THRESHOLD_CHARS","10000")),
                    keep=int(os.getenv("AI_RECENT_HISTORY_CHARS","4000")),
                    question_lookup=lambda questions: catalog.summary_question_evidence(session,questions))
                if changed:
                    retry_at=0
                    notices.append("Older conversation summarized. Full turns remain in the transcript archive.")
            except Exception as error:
                retry_at=time.time()+300
                notices.append("Automatic summary unavailable: "+summary_failure_reason(error)+". Retry paused for 5 minutes; archived turns remain saved.")
        checkpoint_saved=False
        try:
            graph.update_state(config,{"history":history[-16000:],"summary":summary,"summary_retry_at":retry_at})
            checkpoint_saved=True
        except Exception:
            notices.append("The answer was generated, but the conversation checkpoint could not be updated. "
                           "Do not repeat an action to fix this save failure; check its stored receipt first.")
        return {**result,"history":history[-16000:],"summary":summary,"notices":notices,
                "persistence_status":{"archive_saved":archived,"checkpoint_saved":checkpoint_saved}}
