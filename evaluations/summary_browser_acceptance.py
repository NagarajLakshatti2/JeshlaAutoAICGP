"""Real-browser summary reload/restart acceptance using isolated synthetic chats.

The installed Streamlit UI and BrowserBackend run unchanged. A deterministic
acknowledgement graph keeps this check focused on live summary generation and
persistence; ordinary answer quality is outside its scope. --offline validates
the browser fixture without any model requests. No user stores are opened.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NODE = Path("C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")


def browser_entry(directory, offline=False):
    """Install only process-local fixtures before executing the real UI entry point."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import streamlit as st
    from agent.config import paths
    paths.APPLICATION_ROOT = Path(directory)
    from agent.interfaces import browser
    from agent.runtime import summary_model
    from agent.storage.chats import ChatCatalog
    from evaluations.summary_restart_acceptance import fixture_graph

    @st.cache_resource
    def build_fixture():
        import faulthandler
        faulthandler.dump_traceback_later(35)
        folder = Path(directory)
        cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))
        live_summary = summary_model.call_summary_messages

        def summarize(messages, **options):
            record = {"phase": os.environ["SUMMARY_ACCEPTANCE_PHASE"]}
            try:
                if offline:
                    payload = json.loads(messages[-1]["content"])
                    case = next(item for item in cases.values() if item["marker"] in payload["older_turns"])
                    result = json.dumps({"facts": ["user-stated: reference " + case["marker"], "user-stated: preferred report format " + case["format"]], "decisions": [], "open_questions": ["Where should the final report be saved?"]})
                else:
                    result = live_summary(messages, **options)
                record["status"] = "generated"
                return result
            except Exception as error:
                record.update(status="failed", error_kind=type(error).__name__)
                raise
            finally:
                with (folder / "summary-events.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")

        summary_model.call_summary_messages = summarize

        class FixtureBackend(browser.BrowserBackend):
            def submit(self, session, question):
                saved = self.graph.get_state(self.session_config(session, self.user, self.space)).values or {}
                # Compact each initial long chat once. Later probes inspect that
                # same persisted summary, rather than generating a replacement.
                settings = {"AI_SUMMARY_THRESHOLD_CHARS": "10000" if saved.get("summary") else "3000", "AI_RECENT_HISTORY_CHARS": "2000"}
                with patch.dict(os.environ, settings):
                    return super().submit(session, question)

            def provider_info(self, provider=None):
                info = super().provider_info(provider)
                if offline:
                    info.update(key_present=True, model="offline-fixture")
                return info

        backend = FixtureBackend.__new__(FixtureBackend)
        backend.provider = "groq"
        backend.user, backend.space = "acceptance-user", "acceptance-space"
        backend.session_config = lambda session, user, space: {"configurable": {"thread_id": "acceptance-" + session}}
        backend.catalog = ChatCatalog(folder / "chats.sqlite3", backend.user, backend.space)
        backend._fixture_connection = sqlite3.connect(folder / "checkpoints.sqlite3", check_same_thread=False)
        backend.graph = fixture_graph(backend._fixture_connection)
        for name, case in cases.items():
            if backend.catalog.get(name):
                continue
            backend.catalog.register(name, "Summary " + name.title())
            history = ""
            for question, answer in case["turns"]:
                backend.catalog.append(name, question, answer)
                history += "\nUser: " + question + "\nAssistant: " + answer
            backend.graph.update_state(backend.session_config(name, backend.user, backend.space), {"history": history, "summary": "", "summary_retry_at": 0})
        faulthandler.cancel_dump_traceback_later()
        return backend

    browser.make_browser_backend = build_fixture
    entry = ROOT / "streamlit_app.py"
    exec(compile(entry.read_text(encoding="utf-8"), str(entry), "exec"), {"__name__": "__main__", "__file__": str(entry)})


def inspect_stores(folder, cases, counts):
    from agent.storage.chats import ChatCatalog
    from evaluations.summary_restart_acceptance import fixture_graph
    catalog = ChatCatalog(folder / "chats.sqlite3", "acceptance-user", "acceptance-space")
    checks, summaries = {}, {}
    with closing(sqlite3.connect(folder / "checkpoints.sqlite3", check_same_thread=False)) as connection:
        graph = fixture_graph(connection)
        for name, case in cases.items():
            rows = catalog.transcript(name)
            state = graph.get_state({"configurable": {"thread_id": "acceptance-" + name}}).values
            summary = state.get("summary", "")
            facts = json.loads(summary).get("facts", []) if summary else []
            other = next(item["marker"] for key, item in cases.items() if key != name)
            checks[name] = {
                "original_turns_intact": [(row["question"], row["answer"]) for row in rows[:4]] == [tuple(row) for row in case["turns"]],
                "complete_turn_count": len(rows) == 4 + counts[name],
                "reference_retained": case["marker"] in summary,
                "format_retained": case["format"] in " ".join(facts),
                "other_chat_excluded": other not in summary + state.get("history", ""),
            }
            summaries[name] = summary
    stranger = ChatCatalog(folder / "chats.sqlite3", "another-user", "acceptance-space")
    checks["scope"] = {"other_user_excluded": all(not stranger.transcript(name) for name in cases)}
    return checks, summaries


def run_phase(folder, output, phase):
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        port = connection.getsockname()[1]
    url = f"http://127.0.0.1:{port}/JeshlaAutoAI/"
    with (output / (phase + "-server.log")).open("w", encoding="utf-8") as log:
        server = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--serve", str(folder), "--port", str(port)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONUTF8": "1", "SUMMARY_ACCEPTANCE_PHASE": phase})
        metadata = {"server_pid": server.pid, "port": port, "phase": phase, "status": "running"}
        process_path = output / "fixture-process.json"
        process_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        try:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("Fixture server exited; inspect the phase server log.")
                try:
                    with urllib.request.urlopen(url + "_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(.25)
            else:
                raise RuntimeError("Fixture server startup timed out.")
            driver = subprocess.Popen([str(NODE), str(ROOT / "evaluations/summary_browser.cjs"), url, str(output), phase, str(folder / "cases.json")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            driver_path = output / (phase + "-driver.json")
            driver_path.write_text(json.dumps({"pid": driver.pid, "status": "running"}), encoding="utf-8")
            try:
                code = driver.wait(timeout=240)
            except subprocess.TimeoutExpired:
                # This Popen child is owned by this fixture. Kill its browser
                # descendants too; never enumerate or terminate user browsers.
                if os.name == "nt" and driver.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(driver.pid), "/T", "/F"], stdout=log, stderr=subprocess.STDOUT, timeout=15, check=False)
                if driver.poll() is None:
                    driver.kill()
                driver.wait(timeout=10)
                raise
            finally:
                driver_path.write_text(json.dumps({"pid": driver.pid, "status": "stopped" if driver.poll() is not None else "cleanup_failed"}), encoding="utf-8")
            saved = output / (phase + ".json")
            report = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {"status": "failed", "phase": phase, "exit_code": code}
            if code:
                report["status"] = "failed"
            return report
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            metadata["status"] = "stopped"
            process_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--serve", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        # Warm graph dependencies before Streamlit installs module watchers.
        # This is fixture startup preparation, not production startup acceptance.
        import faulthandler
        faulthandler.dump_traceback_later(60)
        started = time.perf_counter()
        from langgraph.graph import StateGraph
        from langgraph.checkpoint.sqlite import SqliteSaver
        faulthandler.cancel_dump_traceback_later()
        print(json.dumps({"event": "fixture_dependencies_ready", "seconds": round(time.perf_counter() - started, 2)}), flush=True)
        from streamlit.web import cli
        sys.argv = ["streamlit", "run", str(Path(args.serve) / "entry.py"), "--server.address", "127.0.0.1", "--server.port", str(args.port), "--server.baseUrlPath", "JeshlaAutoAI", "--server.headless", "true", "--server.fileWatcherType", "none"]
        return cli.main()
    output = ROOT / "outputs/acceptance" / ("ws2-browser-offline" if args.offline else "ws2-browser-groq")
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "mode": "offline_fixture" if args.offline else "live_synthetic_groq", "scope": "Chrome desktop, real UI/backend, synthetic summaries, page reload, server and browser restart, alpha/beta switching; deterministic acknowledgement answers; fixture graph dependencies preloaded before Streamlit watchers", "phases": []}
    with tempfile.TemporaryDirectory(prefix="jeshla-summary-browser-") as temporary:
        folder = Path(temporary)
        cases = {}
        for name, fmt in (("alpha", "PDF"), ("beta", "HTML")):
            marker = name.upper() + "_" + secrets.token_hex(6)
            cases[name] = {"marker": marker, "format": fmt, "turns": [["My reference code for this chat is " + marker + ". My preferred report format is " + fmt + ".", "Noted."], ["Where should the final report be saved?", "No folder has been selected."], ["Background context: " + "neutral " * 210, "Noted."], ["Recent background: " + "neutral " * 210, "Noted."]]}
        (folder / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        (folder / "entry.py").write_text("import sys\nsys.path.insert(0, " + repr(str(ROOT)) + ")\nfrom evaluations.summary_browser_acceptance import browser_entry\nbrowser_entry(" + repr(str(folder)) + ", offline=" + repr(args.offline) + ")\n", encoding="utf-8")
        counts, initial = {name: 0 for name in cases}, None
        try:
            for phase in ("create", "reopen"):
                print(json.dumps({"phase": phase, "event": "starting"}), flush=True)
                browser_report = run_phase(folder, output, phase)
                print(json.dumps({"phase": phase, "status": browser_report["status"]}), flush=True)
                report["phases"].append(browser_report)
                if browser_report["status"] != "passed":
                    break
                for name in counts:
                    counts[name] += browser_report["submitted"][name]
                checks, summaries = inspect_stores(folder, cases, counts)
                browser_report["store_checks"] = checks
                if initial is not None:
                    browser_report["summaries_unchanged_after_restart"] = summaries == initial
                initial = summaries
                if not all(all(values.values()) for values in checks.values()) or browser_report.get("summaries_unchanged_after_restart") is False:
                    browser_report["status"] = "failed"
                    break
            events = [json.loads(line) for line in (folder / "summary-events.jsonl").read_text(encoding="utf-8").splitlines()] if (folder / "summary-events.jsonl").exists() else []
            report["summary_generation_events"] = events
            report["no_summary_generation_after_restart"] = len(events) == 2 and all(event == {"phase": "create", "status": "generated"} for event in events)
            if len(report["phases"]) == 2 and all(item["status"] == "passed" for item in report["phases"]) and report["no_summary_generation_after_restart"]:
                report["status"] = "passed"
        except Exception as error:
            report["error_kind"] = type(error).__name__
    report["fixture_removed"] = not folder.exists()
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
