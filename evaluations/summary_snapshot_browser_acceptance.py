"""Opt-in local browser restart checks using read-only saved-chat snapshots.

No model calls. Original stores are read with mode=ro; test writes and copied
private text stay in a temporary directory that is removed after both phases.
This checks persistence and isolation, not summary semantic correctness.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_snapshot(data_root, session, user="local-user", space="project"):
    """Read exactly one requested user/space/session, never create a source DB."""
    from langgraph.checkpoint.sqlite import SqliteSaver
    from agent.runtime.summaries import validate_summary
    identity = json.dumps([user, space, session], ensure_ascii=False)
    thread = "main-agent-session" if (user, space, session) == ("local-user", "project", "default") else "session-" + digest(identity)
    with closing(sqlite3.connect((data_root / "agent_memory.db").as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(":memory:")) as snapshot:
        src.backup(snapshot)
        saved = SqliteSaver(snapshot).get_tuple({"configurable": {"thread_id": thread}})
        state = saved.checkpoint["channel_values"] if saved else {}
    summary, history = state.get("summary", ""), state.get("history", "")
    if not summary:
        raise ValueError("Selected chat has no saved summary.")
    validate_summary(summary)  # Legacy attribution strings remain readable.
    with closing(sqlite3.connect((data_root / "outputs/memory/chats.sqlite3").as_uri() + "?mode=ro", uri=True)) as catalog:
        rows = catalog.execute("SELECT question,answer FROM turns WHERE user=? AND space=? AND session=? ORDER BY id", (user, space, session)).fetchall()
    if not rows:
        raise ValueError("Selected chat has no scoped archived turns.")
    return {"summary": summary, "summary_sha256": digest(summary), "history": history, "turns": [list(row) for row in rows]}


def snapshot_graph(connection):
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    from evaluations.summary_restart_acceptance import State
    def probe(state):
        answer = digest(state.get("summary", ""))
        return {"answer": answer, "final_answer": answer, "route": "direct", "task_status": "completed", "execution_outcome": "completed"}
    graph = StateGraph(State)
    graph.add_node("snapshot_probe", probe)
    graph.add_edge(START, "snapshot_probe")
    graph.add_edge("snapshot_probe", END)
    return graph.compile(checkpointer=SqliteSaver(connection))


def browser_entry(directory):
    """Real UI/backend, with a deterministic summary-digest node and network guard."""
    folder = Path(directory)
    from agent.config.paths import DATA_ROOT, APPLICATION_ROOT
    if DATA_ROOT != folder / "runtime" or APPLICATION_ROOT != ROOT:
        raise RuntimeError("Fixture data/code roots are not safely isolated.")
    from tests.run_offline import offline_guard
    guard = offline_guard()
    guard.__enter__()  # Process-lifetime guard; server termination closes the fixture.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import streamlit as st
    from agent.interfaces import browser
    from agent.runtime import summary_model
    from agent.storage.chats import ChatCatalog

    @st.cache_resource
    def build_fixture():
        cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))
        def forbidden_summary(*args, **kwargs):
            with (folder / "unexpected-summary.txt").open("a", encoding="utf-8") as log:
                log.write("unexpected summary invocation\n")
            raise AssertionError("Snapshot acceptance must reuse the saved summary.")
        summary_model.call_summary_messages = forbidden_summary
        class SnapshotBackend(browser.BrowserBackend):
            def provider_info(self, provider=None):
                return {"provider": provider or "groq", "model": "local-snapshot-fixture", "key_present": True, "local": False, "supported": True}
            def submit(self, session, question):
                with patch.dict(os.environ, {"AI_SUMMARY_MIN_TURNS": "100", "AI_SUMMARY_THRESHOLD_CHARS": "16000", "AI_RECENT_HISTORY_CHARS": "4000"}):
                    return super().submit(session, question)
        backend = SnapshotBackend.__new__(SnapshotBackend)
        backend.provider = "groq"
        backend.user, backend.space = "snapshot-user", "snapshot-space"
        backend.session_config = lambda session, user, space: {"configurable": {"thread_id": "snapshot-" + session}}
        backend.catalog = ChatCatalog(folder / "chats.sqlite3", backend.user, backend.space)
        backend._fixture_connection = sqlite3.connect(folder / "checkpoints.sqlite3", check_same_thread=False)
        backend.graph = snapshot_graph(backend._fixture_connection)
        for name, case in cases.items():
            if backend.catalog.get(name):
                continue
            backend.catalog.register(name, "Snapshot " + name.title())
            for question, answer in case["turns"]:
                backend.catalog.append(name, question, answer)
            backend.graph.update_state(backend.session_config(name, backend.user, backend.space), {"summary": case["summary"], "history": case["history"], "summary_retry_at": 0})
        return backend
    browser.make_browser_backend = build_fixture
    entry = ROOT / "streamlit_app.py"
    exec(compile(entry.read_text(encoding="utf-8"), str(entry), "exec"), {"__name__": "__main__", "__file__": str(entry)})


def inspect_stores(folder, cases, counts):
    from agent.storage.chats import ChatCatalog
    catalog = ChatCatalog(folder / "chats.sqlite3", "snapshot-user", "snapshot-space")
    checks = {}
    with closing(sqlite3.connect(folder / "checkpoints.sqlite3", check_same_thread=False)) as connection:
        graph = snapshot_graph(connection)
        for name, case in cases.items():
            rows = catalog.transcript(name)
            state = graph.get_state({"configurable": {"thread_id": "snapshot-" + name}}).values
            checks[name] = {
                "exact_original_summary_retained": state.get("summary") == case["summary"],
                "all_original_turns_intact": [[row["question"], row["answer"]] for row in rows[:len(case["turns"])]] == case["turns"],
                "expected_full_transcript_count": len(rows) == len(case["turns"]) + counts[name],
                "summary_differs_from_other_chat": digest(state.get("summary", "")) != cases["beta" if name == "alpha" else "alpha"]["summary_sha256"],
            }
    stranger = ChatCatalog(folder / "chats.sqlite3", "other-user", "snapshot-space")
    checks["scope"] = {"other_user_excluded": all(not stranger.transcript(name) for name in cases), "no_summary_generation": not (folder / "unexpected-summary.txt").exists()}
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--second-chat", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    from agent.config.paths import DATA_ROOT
    from evaluations.summary_browser_acceptance import run_phase
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sessions = {"alpha": "default", "beta": args.second_chat}
    cases = {name: read_snapshot(DATA_ROOT, session) for name, session in sessions.items()}
    if cases["alpha"]["summary_sha256"] == cases["beta"]["summary_sha256"]:
        raise ValueError("Choose distinct saved summaries for isolation acceptance.")
    report = {"status": "P", "scope": "Local Chrome desktop: two actual saved-chat snapshots, exact summary reuse, page reload, fresh server/browser restart and alpha-beta-alpha switching. Deterministic digest answers; no semantic quality or live provider-generation claim.", "original_turn_counts": {name: len(case["turns"]) for name, case in cases.items()}, "phases": [], "model_requests": 0}
    with tempfile.TemporaryDirectory(prefix="jeshla-actual-summary-") as temporary:
        folder = Path(temporary)
        (folder / "runtime").mkdir()
        (folder / "cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
        (folder / "entry.py").write_text("import sys\nsys.path.insert(0, " + repr(str(ROOT)) + ")\nfrom evaluations.summary_snapshot_browser_acceptance import browser_entry\nbrowser_entry(" + repr(str(folder)) + ")\n", encoding="utf-8")
        counts = {name: 0 for name in cases}
        try:
            with patch.dict(os.environ, {"JESHLA_HOME": str(folder / "runtime"), "LLM_FALLBACK_ENABLED": "false", "PYTHONDONTWRITEBYTECODE": "1"}):
                for phase in ("snapshot-create", "snapshot-reopen"):
                    print(json.dumps({"phase": phase, "event": "starting"}), flush=True)
                    result = run_phase(folder, output, phase)
                    report["phases"].append(result)
                    print(json.dumps({"phase": phase, "status": result["status"]}), flush=True)
                    if result["status"] != "passed":
                        break
                    for name in counts:
                        counts[name] += result["submitted"][name]
                    checks = inspect_stores(folder, cases, counts)
                    result["store_checks"] = checks
                    if not all(all(group.values()) for group in checks.values()):
                        result["status"] = "failed"
                        break
            report["original_source_rows_and_summary_unchanged"] = all(read_snapshot(DATA_ROOT, session) == cases[name] for name, session in sessions.items())
            if len(report["phases"]) == 2 and all(row["status"] == "passed" for row in report["phases"]) and report["original_source_rows_and_summary_unchanged"]:
                report["status"] = "Y"
        except Exception as error:
            report["error_type"] = type(error).__name__
    report["temporary_private_snapshots_removed"] = not folder.exists()
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "Y" else 1


if __name__ == "__main__":
    raise SystemExit(main())
