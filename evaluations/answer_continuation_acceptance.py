"""Fresh-process Continue acceptance; offline by default, optional explicit Groq probe."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def phase(name, workspace, live_provider=None):
    from contextlib import closing, redirect_stdout, redirect_stderr, nullcontext
    import sqlite3
    from types import SimpleNamespace
    from unittest.mock import patch
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    from agent.runtime.conversation import answer_question
    from agent.runtime.turns import run_turn
    from agent.storage.chats import ChatCatalog
    from agent.providers.selection import provider_selection
    from tests.run_offline import offline_guard
    from tests.test_answer_continuations import State, ScriptedSections
    from tests.test_named_sessions import config as session_config
    if live_provider:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        from agent.providers.tools import call_tool_messages
        from agent.providers.errors import ProviderError
        class LiveSections(ScriptedSections):
            """Script only outline/boundaries; generate section bodies through Groq."""
            def __init__(self):
                super().__init__(stop="section-2" if name == "partial" else None)
                self.live_calls = 0
                self.plan.update(title="A fictional community discussion club", scope="A synthetic planning example, not an executed project.")
                purposes = ("Choose the club purpose and first discussion topic", "Agree meeting and discussion rules", "Avoid recruitment and scheduling mistakes")
                for part, purpose in zip(self.plan["sections"], purposes):
                    part["purpose"] = purpose
            def __call__(self, messages, specs):
                if not specs or specs[0]["function"]["name"] == "submit_answer_outline":
                    return super().__call__(messages, specs)
                prompt = next(m["content"] for m in reversed(messages) if "Section assignment: " in m.get("content", ""))
                identity = json.loads(prompt.split("Section assignment: ", 1)[1])["assigned_section_id"]
                self.ids.append(identity)
                if identity == self.stop:
                    raise ProviderError(live_provider, "RATE_LIMIT", "Injected acceptance pause, not an actual provider quota response", status=429)
                self.live_calls += 1
                if self.live_calls > 4:
                    raise AssertionError("Live acceptance request ceiling reached")
                return call_tool_messages(messages, specs, max_tokens=1536, require_tool=True)
        model = LiveSections()
    else:
        model = ScriptedSections(stop="section-2" if name == "partial" else None)
    tools = SimpleNamespace(root="synthetic-public-fixture", list_files=lambda **k: {}, read_file=lambda **k: {}, search_text=lambda **k: {})
    config = session_config("fixture", "fixture-user", "fixture-space")
    settings = {"JESHLA_EXECUTION_MODE": "offline", "LLM_FALLBACK_ENABLED": "true", "LLM_FALLBACK_ORDER": "openrouter,groq,gemini", "AI_LONG_ANSWERS_ENABLED": "true",
        "AI_LONG_ANSWER_MAX_CALLS": "8", "AI_LONG_ANSWER_MAX_SECTIONS": "3", "AI_LONG_ANSWER_MAX_CHARS": "60000",
        "AI_CHAT_MAX_CONVERSATION_CHARS": "36000", "AI_TECHNICAL_VERIFICATION": "off", "AI_SUMMARY_THRESHOLD_CHARS": "100000"}
    if live_provider:
        settings.update(LLM_PROVIDER=live_provider, LLM_FALLBACK_ORDER=live_provider,
                        GROQ_TIMEOUT="20", JESHLA_EXECUTION_MODE="online")
    network_scope = nullcontext() if live_provider else offline_guard()
    with (workspace / (name + ".log")).open("w", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log), network_scope, patch.dict(os.environ, settings), provider_selection(live_provider or "openrouter"):
        catalog = ChatCatalog(workspace / "chats.sqlite3", "fixture-user", "fixture-space"); catalog.register("fixture")
        with closing(sqlite3.connect(workspace / "checkpoints.sqlite3", check_same_thread=False)) as db:
            builder = StateGraph(State)
            def answer(state):
                result = answer_question({**state, "route": "direct"}, model=model, tools=tools, project_root=".", document_search=lambda **k: {})
                return {**result, "route": "direct"}
            builder.add_node("answer", answer); builder.add_edge(START, "answer"); builder.add_edge("answer", END)
            graph = builder.compile(checkpointer=SqliteSaver(db))
            question = ("Explain how to organize a fictional community discussion club in three distinct sections. Keep each section under 100 words." if live_provider else "Explain a long topic.") if name == "partial" else "CONTINUE" if name == "resume" else "FULL ANSWER"
            if name != "partial":
                graph.invoke = lambda *a, **k: (_ for _ in ()).throw(AssertionError("Continuation must not replay the graph"))
            result = run_turn(graph, config, catalog, "fixture", question, workspace, continuation_model=model)
            if name == "full":
                repeated = run_turn(graph, config, catalog, "fixture", "CONTINUE", workspace, continuation_model=model)
                assert repeated.get("execution_outcome") == "completed"
        if name == "partial":
            passed = result.get("execution_outcome") == "partial" and "## Foundations" in result["answer"] and "## Rules" not in result["answer"]
        elif name == "resume":
            passed = result.get("execution_outcome") == "completed" and model.ids == ["section-2", "section-3"] and model.outlines == 0 and "## Foundations" not in result["answer"]
        else:
            passed = all(result["answer"].count("## " + title) == 1 for title in ("Foundations", "Rules", "Pitfalls")) and not model.ids and not model.outlines
        report = {"phase": name, "pid": os.getpid(), "passed": passed, "section_requests": model.ids,
            "outline_requests": model.outlines, "live_requests": getattr(model, "live_calls", 0), "answer": result["answer"], "persistence_status": result["persistence_status"], "transcript_turns": len(catalog.transcript("fixture"))}
    print(json.dumps(report))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/acceptance/answer-continuations-process")
    parser.add_argument("--live-provider", choices=["groq"], help="Explicit live synthetic sections; outline and pause remain injected")
    parser.add_argument("--phase", choices=["partial", "resume", "full"])
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.phase:
        if args.workspace is None: parser.error("--workspace is required for a child phase")
        try:
            return phase(args.phase, args.workspace, args.live_provider)
        except Exception as error:
            from agent.user_errors import user_error_message
            print(json.dumps({"phase": args.phase, "passed": False, "error_type": type(error).__name__, "error": user_error_message(error)}))
            return 1
    folder = args.output_dir.resolve(); folder.mkdir(parents=True, exist_ok=True)
    reports = []
    with tempfile.TemporaryDirectory(prefix="continuation-fixture-", dir=folder) as temporary:
        workspace = Path(temporary).resolve()
        if not workspace.is_relative_to(folder): raise ValueError("Acceptance fixture escaped its output folder")
        for name in ("partial", "resume", "full"):
            try:
                live_options = ["--live-provider", args.live_provider] if args.live_provider else []
                child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--phase", name, "--workspace", str(workspace), *live_options],
                    cwd=ROOT, capture_output=True, text=True, timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                report = json.loads(child.stdout) if child.stdout.strip() else {"phase": name, "passed": False, "exit_code": child.returncode}
            except (subprocess.TimeoutExpired, ValueError): report = {"phase": name, "passed": False, "error": "Owned phase timeout or invalid report"}
            log_path = workspace / (name + ".log")
            if log_path.exists():
                (folder / (name + ".log")).write_text(log_path.read_text(encoding="utf-8"), encoding="utf-8")
            reports.append(report)
            (folder / (name + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
            if not report.get("passed"): break
    passed = len(reports) == 3 and all(item["passed"] for item in reports) and len({item.get("pid") for item in reports}) == 3
    report = {"passed": passed, "scope": ("Three fresh processes, temporary SQLite, actual Groq section generation; outline and pause injected. Shared backend acceptance, not UI clicks, natural quota exhaustion, all-provider or factual-quality acceptance." if args.live_provider else "Three fresh processes, real SQLite, scripted provider failures; network blocked. No live provider or factual-quality acceptance."), "phases": reports}
    (folder / "process-restart.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "phases": len(reports), "report": str(folder / "process-restart.json")}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
