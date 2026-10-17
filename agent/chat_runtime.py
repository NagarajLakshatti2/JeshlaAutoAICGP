"""Shared console/browser chat execution and checkpoint/archive handling."""
from contextlib import contextmanager
import os
from pathlib import Path
import threading
import time

process_turn_lock=threading.RLock()

@contextmanager
def session_turn_lock(root,config):
    thread=config["configurable"]["thread_id"]
    import hashlib
    path=Path(root)/"outputs/chat_locks"/(hashlib.sha256(thread.encode()).hexdigest()+".lock")
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL)
    except FileExistsError:
        raise RuntimeError("This chat is busy in another window. Wait for it to finish. If a process crashed, inspect its chat lock before removing it.") from None
    try:
        with os.fdopen(fd,"w") as handle:handle.write(str(os.getpid()))
        yield
    finally:path.unlink(missing_ok=True)


def run_turn(graph,config,catalog,session,question,root):
    from agent.context_summary import compact_context,summary_failure_reason
    from agent.llm_client import call_llm_messages
    notices=[]
    with process_turn_lock,session_turn_lock(root,config):
        saved=graph.get_state(config).values or {}
        history=saved.get("history","");summary=saved.get("summary","")
        state={"question":question,"route":"","prompt":"","context":"","answer":"","final_answer":"",
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
        if archived and time.time()>=retry_at:
            try:
                summary,history,changed=compact_context(summary,history,call_llm_messages,
                    threshold=int(os.getenv("AI_SUMMARY_THRESHOLD_CHARS","10000")),
                    keep=int(os.getenv("AI_RECENT_HISTORY_CHARS","4000")))
                if changed:
                    retry_at=0
                    notices.append("Older conversation summarized. Full turns remain in the transcript archive.")
            except Exception as error:
                retry_at=time.time()+300
                notices.append("Automatic summary unavailable: "+summary_failure_reason(error)+". Retry paused for 5 minutes; archived turns remain saved.")
        graph.update_state(config,{"history":history[-16000:],"summary":summary,"summary_retry_at":retry_at})
        return {**result,"history":history[-16000:],"summary":summary,"notices":notices}
