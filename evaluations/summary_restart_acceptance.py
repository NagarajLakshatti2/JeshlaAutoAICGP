"""Isolated fresh-process summary restart/switch acceptance.

Live mode sends synthetic data only. --offline verifies the fixture without API calls.
All chat/checkpoint writes stay inside an automatically removed temporary directory.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
from typing import TypedDict
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class State(TypedDict, total=False):
    question: str
    answer: str
    final_answer: str
    route: str
    task_status: str
    execution_outcome: str
    history: str
    summary: str
    summary_retry_at: float


def fixture_graph(connection):
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    def acknowledge(state):
        answer = "Acknowledged."
        if state["question"].startswith("REOPEN_CHECK "):
            marker = state["question"].split(" ", 1)[1]
            answer = marker if marker in state.get("summary", "") else "MISSING SUMMARY"
        return {"answer": answer, "final_answer": answer, "route": "direct", "task_status": "completed", "execution_outcome": "completed"}
    graph = StateGraph(State)
    graph.add_node("acknowledge", acknowledge)
    graph.add_edge(START, "acknowledge")
    graph.add_edge("acknowledge", END)
    return graph.compile(checkpointer=SqliteSaver(connection))


def worker(args):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from agent.storage.chats import ChatCatalog
    from agent.runtime.turns import run_turn
    from agent.runtime import summary_model
    from agent.providers.selection import provider_selection
    fixture = Path(args.fixture)
    cases = json.loads((fixture / "cases.json").read_text(encoding="utf-8"))
    catalog = ChatCatalog(fixture / "chats.sqlite3", "acceptance-user", "acceptance-space")
    configs = {name: {"configurable": {"thread_id": "acceptance-" + name}} for name in cases}
    checks = {}
    live_summary = summary_model.call_summary_messages
    calls = []
    def summarize(messages, **options):
        calls.append(1)
        if args.worker == "reopen":
            raise AssertionError("Reopen must not need a new summary")
        if not args.offline:
            return live_summary(messages, **options)
        payload = json.loads(messages[-1]["content"])
        case = next(value for value in cases.values() if value["marker"] in payload["older_turns"])
        return json.dumps({"facts": ["user-stated: reference " + case["marker"], "user-stated: preferred report format " + case["format"]], "decisions": [], "open_questions": ["Where should the final report be saved?"]})
    with closing(sqlite3.connect(fixture / "checkpoints.sqlite3", check_same_thread=False)) as connection:
        graph = fixture_graph(connection)
        with patch.dict(os.environ, {"AI_SUMMARY_THRESHOLD_CHARS": "3000", "AI_RECENT_HISTORY_CHARS": "2000"}), provider_selection(args.provider), patch.object(summary_model, "call_summary_messages", side_effect=summarize):
            if args.worker == "create":
                for name, case in cases.items():
                    catalog.register(name)
                    history = ""
                    for question, answer in case["turns"]:
                        catalog.append(name, question, answer)
                        history += "\nUser: " + question + "\nAssistant: " + answer
                    graph.update_state(configs[name], {"history": history, "summary": "", "summary_retry_at": 0})
                    result = run_turn(graph, configs[name], catalog, name, "Please acknowledge my preference.", fixture)
                    summary = result["summary"]
                    other = next(value["marker"] for key, value in cases.items() if key != name)
                    value = json.loads(summary) if summary else {}
                    checks[name] = {"summary_created": bool(summary), "marker_retained": case["marker"] in summary, "format_retained": case["format"] in " ".join(value.get("facts", [])), "other_chat_excluded": other not in summary + result["history"], "full_transcript": len(catalog.transcript(name)) == 5, "saved": all(result["persistence_status"].values())}
            else:
                initial = {name: graph.get_state(configs[name]).values["summary"] for name in cases}
                for index, name in enumerate(("alpha", "beta", "alpha")):
                    case = cases[name]
                    other = next(value["marker"] for key, value in cases.items() if key != name)
                    result = run_turn(graph, configs[name], catalog, name, "REOPEN_CHECK " + case["marker"], fixture)
                    checks[str(index)] = {"restored_summary_used": result["answer"] == case["marker"], "same_summary": result["summary"] == initial[name], "other_chat_excluded": other not in result["summary"] + result["history"], "saved": all(result["persistence_status"].values())}
                for name, case in cases.items():
                    rows = catalog.transcript(name)
                    checks[name + "_archive"] = {"original_turns_intact": [(r["question"], r["answer"]) for r in rows[:4]] == [tuple(row) for row in case["turns"]], "expected_count": len(rows) == (7 if name == "alpha" else 6)}
                stranger = ChatCatalog(fixture / "chats.sqlite3", "another-user", "acceptance-space")
                checks["scope"] = {"other_user_excluded": not stranger.transcript("alpha"), "no_resummary_calls": not calls}
    passed = all(all(group.values()) for group in checks.values())
    report = {"status": "passed" if passed else "failed", "phase": args.worker, "mode": "offline_fixture" if args.offline else "live_synthetic", "provider": args.provider, "summary_calls": len(calls), "checks": checks}
    (fixture / (args.worker + "-result.json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("groq", "openrouter", "gemini", "ollama"), default="groq")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--worker", choices=("create", "reopen"))
    parser.add_argument("--fixture")
    args = parser.parse_args()
    if args.worker:
        return worker(args)
    reports = []
    suffix = "offline" if args.offline else args.provider
    output = ROOT / "outputs/acceptance" / ("ws2-restart-" + suffix + ".json")
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        cases = {}
        for name, fmt in (("alpha", "PDF"), ("beta", "HTML")):
            marker = name.upper() + "_" + secrets.token_hex(6)
            cases[name] = {"marker": marker, "format": fmt, "turns": [["My reference code for this chat is " + marker + ". My preferred report format is " + fmt + ".", "Noted."], ["Where should the final report be saved?", "No folder has been selected."], ["Background context: " + "neutral " * 210, "Noted."], ["Recent background: " + "neutral " * 210, "Noted."]]}
        (fixture / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        log_path = output.with_suffix(".log")
        with log_path.open("w", encoding="utf-8") as log:
            for phase in ("create", "reopen"):
                command = [sys.executable, "-u", str(Path(__file__).resolve()), "--provider", args.provider, "--worker", phase, "--fixture", directory]
                if args.offline:
                    command.append("--offline")
                try:
                    result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180, env={**os.environ, "PYTHONUTF8": "1"})
                except subprocess.TimeoutExpired:
                    reports.append({"phase": phase, "status": "timeout"})
                    break
                saved = fixture / (phase + "-result.json")
                reports.append(json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {"phase": phase, "status": "failed", "exit_code": result.returncode})
                if result.returncode:
                    break
    report = {"status": "passed" if len(reports) == 2 and all(r["status"] == "passed" for r in reports) else "failed", "scope": "Fresh-process backend restart/switch with isolated temporary stores; not live UI click acceptance", "mode": "offline_fixture" if args.offline else "live_synthetic", "phases": reports, "fixture_removed": True}
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
