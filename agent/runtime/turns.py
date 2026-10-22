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


def run_turn(graph,config,catalog,session,question,root,*,continuation_model=None):
    from agent.runtime.summaries import compact_context,summary_failure_reason,summary_due
    from agent.runtime.summary_model import call_summary_messages
    notices=[]
    from agent.providers.fallback import fallback_scope
    with process_turn_lock,session_turn_lock(root,config),fallback_scope() as fallback_notices:
        saved=graph.get_state(config).values or {}
        history=saved.get("history","");summary=saved.get("summary","")
        state={"conversation_session":session,"question":question,"route":"","prompt":"","context":"","answer":"","final_answer":"","task_status":"completed","execution_outcome":"unclassified","answer_available":True,
               "history":history[-16000:],"summary":summary,"previous_route":saved.get("route",""),
               "previous_exchange":{"question":saved.get("question",""),"answer":saved.get("answer","")},
               "previous_response_status":{"task_status":saved.get("task_status",""),"execution_outcome":saved.get("execution_outcome",""),**({"answer_available":saved["answer_available"]} if "answer_available" in saved else {})},
               "summary_retry_at":saved.get("summary_retry_at",0),
               "summary_turns":saved.get("summary_turns",0)}
        from agent.storage.answer_continuations import AnswerContinuations
        from agent.runtime.continuations import command,explicit_command,progress_scope,validate_ledger,full_result,resume_result
        import hashlib
        store=AnswerContinuations(Path(root)/"outputs/memory/answer_continuations.sqlite3")
        scope=hashlib.sha256(config["configurable"]["thread_id"].encode()).hexdigest()
        progress_ids=set()
        def persist_progress(value):
            store.save(scope,value)
            progress_ids.add(value["id"])
        control=command(question)
        ledger=None
        manual=False
        if control:
            try:
                ledger=store.load(scope)
                if ledger is not None:
                    validate_ledger(ledger)
                    prior_question=saved.get("question","")
                    if (not explicit_command(question) and prior_question and command(prior_question) is None
                            and prior_question!=ledger["origin_question"]):
                        ledger=None
            except Exception:
                # Damaged text progress must never fall into a workflow/action.
                result={"answer":"Saved answer progress could not be read or validated. No workflow was resumed; check its local store before retrying.",
                        "route":"direct","task_status":"incomplete","answer_available":False,"execution_outcome":"blocked"}
                manual=True
        else:
            try:
                prior=store.load(scope)
                if prior is not None:
                    validate_ledger(prior)
                    last_question=saved.get("question","")
                    if prior["published"] and (last_question==prior["origin_question"] or command(last_question) in {"continue","full"}):
                        from agent.runtime.long_answers import render_answer
                        # One logical answer can span several published messages.
                        # Never include a section held back by generation/save failure.
                        published=prior["completed"][:prior["published"]]
                        state["previous_exchange"]={"question":prior["origin_question"],"answer":render_answer(prior["outline"],published)}
                        state["previous_response_status"]={"task_status":"completed" if prior["status"]=="complete" else "incomplete",
                            "execution_outcome":"completed" if prior["status"]=="complete" else "partial","answer_available":True}
                store.discard(scope)
            except Exception:notices.append("Older answer progress could not be cleared. It cannot authorize any action.")
        if not manual:
            with progress_scope(ledger["origin_question"] if ledger else question,persist_progress):
                if control=="cancel":
                    store.discard(scope)
                    result={"answer":"Answer continuation cancelled. Previously archived messages remain saved.","route":"direct","task_status":"completed","execution_outcome":"completed"}
                    manual=True
                elif ledger is not None and control in {"continue","full"}:
                    if control=="full":result=full_result(ledger)
                    else:
                        if continuation_model is None:
                            from agent.providers.tools import call_tool_messages
                            continuation_model=call_tool_messages
                        result=resume_result(ledger,continuation_model)
                    manual=True
                elif explicit_command(question):
                    result={"answer":"There is no saved text answer to resume or consolidate in this chat.","route":"direct","task_status":"completed","execution_outcome":"completed"}
                    manual=True
                else:result=graph.invoke(state,config=config)
        amended=False
        pending_text=False
        try:
            active=store.load(scope)
            if active is not None and (active.get("id") in progress_ids or (ledger is not None and active.get("id")==ledger["id"])):
                validate_ledger(active)
                # Every ordinary new question discards old progress. Controls
                # only ever invoke registered text-data generation, never graph actions.
                if active["status"]=="pending":
                    pending_text=True
                    result["answer"]+="\n\nType CONTINUE to resume this answer, FULL ANSWER to view completed sections, or CANCEL ANSWER to stop. Provider quotas still apply."
                elif control!="full" and "FULL ANSWER" not in result["answer"]:
                    result["answer"]+="\n\nAnswer complete. Type FULL ANSWER for the consolidated result."
                amended=True
                if result.get("answer_available",True) and active["completed"]:
                    active["published"]=len(active["completed"])
                    store.save(scope,active)
        except Exception:
            notices.append("Answer progress could not be updated. Use FULL ANSWER to inspect saved sections before repeating a request.")
        history=history+"\nUser: "+question+"\nAssistant: "+result["answer"]
        archived=False
        try:
            catalog.append(session,question,result["answer"])
            archived=True
        except Exception:
            notices.append("The answer was generated, but the transcript archive could not be updated.")
        retry_at=float(saved.get("summary_retry_at",0) or 0)
        prior_turns=saved.get("summary_turns",0)
        summary_turns=(prior_turns if type(prior_turns) is int and prior_turns>=0 else 0)+int(archived)
        # Deterministic memory controls must remain usable without a provider.
        # Preserve archive/checkpoint writes; compact on a later conversation turn.
        local_control=manual or pending_text or result.get("route") in {"memory","memory_command"}
        if archived and not local_control and time.time()>=retry_at:
            try:
                changed=False
                if summary_due(history,summary_turns,minimum_turns=int(os.getenv("AI_SUMMARY_MIN_TURNS","3"))):
                    summary,history,changed=compact_context(summary,history,call_summary_messages,
                        threshold=int(os.getenv("AI_SUMMARY_THRESHOLD_CHARS","10000")),
                        keep=int(os.getenv("AI_RECENT_HISTORY_CHARS","4000")),
                        question_lookup=lambda questions: catalog.summary_question_evidence(session,questions))
                if changed:
                    retry_at=0
                    summary_turns=0
                    notices.append("Older conversation summarized. Full turns remain in the transcript archive.")
            except Exception as error:
                retry_at=time.time()+300
                notices.append("Automatic summary unavailable: "+summary_failure_reason(error)+". Retry paused for 5 minutes; archived turns remain saved.")
        checkpoint_saved=False
        try:
            checkpoint={"history":history[-16000:],"summary":summary,"summary_retry_at":retry_at,"summary_turns":summary_turns}
            if manual or amended:
                checkpoint.update(question=question,answer=result["answer"],route=result.get("route","direct"),
                    task_status=result.get("task_status","completed"),execution_outcome=result.get("execution_outcome","completed"),
                    answer_available=result.get("answer_available",True))
            graph.update_state(config,checkpoint)
            checkpoint_saved=True
        except Exception:
            notices.append("The answer was generated, but the conversation checkpoint could not be updated. "
                           "Do not repeat an action to fix this save failure; check its stored receipt first.")
        notices.extend(fallback_notices)
        return {**result,"history":history[-16000:],"summary":summary,"summary_turns":summary_turns,"notices":notices,
                "persistence_status":{"archive_saved":archived,"checkpoint_saved":checkpoint_saved}}
