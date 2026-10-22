"""Bounded offline CI checks with disposable state; no server or live provider.

Run with python -m evaluations.ci_smoke --interface console|browser.
Application modules run in a fresh child process with private environment settings
removed. Existing dependencies are reused; this is not clean-install acceptance.
"""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def check_initial_page(page):
    """Reject a crashed/error page or a missing/duplicated composer."""
    if page.exception:
        raise RuntimeError("Initial page raised an exception")
    if page.error:
        raise RuntimeError("Initial page displayed an error")
    if len(page.chat_input) != 1:
        raise RuntimeError("Initial page must have exactly one chat composer")
    if not any(item.value == "What would you like to build?" for item in page.title):
        raise RuntimeError("Initial page welcome title is missing")


def worker(interface, source, state):
    # This worker is launched only by the parent with its owned temporary state.
    from tests.run_offline import offline_guard
    source, state = Path(source).resolve(), Path(state).resolve()
    if Path(os.environ["JESHLA_HOME"]).resolve() != state or state.is_relative_to(source):
        raise RuntimeError("CI worker requires a separate fixture data directory")
    with offline_guard(), patch.dict(os.environ, {
        "AI_DEPLOYMENT_MODE": "hosted", "LLM_ALLOW_LOCAL_OLLAMA": "false",
        "LLM_FALLBACK_ENABLED": "false",
    }):
        from agent.config.paths import APPLICATION_ROOT, DATA_ROOT
        from agent.langgraph import langgraph_agent as module
        if APPLICATION_ROOT != source or DATA_ROOT != state:
            raise RuntimeError("CI worker resolved the wrong code or data root")
        report = {"interface": interface, "provider_requests": 0, "external_network": "blocked"}
        try:
            if interface == "console":
                output = io.StringIO()
                draft = "REMEMBER ci_probe = CI persistence verified\nEND\nSHOW MEMORY\nEND\nEXIT\n"
                with redirect_stdout(output), patch.object(sys, "argv", [
                    "agent", "--input-mode", "end", "--session", "ci-console",
                    "--user", "ci-user", "--memory-space", "ci-space",
                ]), patch.object(sys, "stdin", io.StringIO(draft)):
                    module.main()
                if "Saved memory: ci_probe" not in output.getvalue():
                    raise RuntimeError("Console did not save its fixture memory")
                # Closing and reading again forces a real graph/checkpoint reopen.
                module.graph.close()
                with redirect_stdout(io.StringIO()):
                    config, _, _, _ = module.restore_session("ci-console", "ci-user", "ci-space")
                snapshot = module.graph.get_state(config)
                if "ci_probe" not in snapshot.values.get("answer", ""):
                    raise RuntimeError("Saved SHOW MEMORY result did not survive graph reopen")
                with sqlite3.connect(state / "agent_memory.db") as connection:
                    count = connection.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
                if count < 1:
                    raise RuntimeError("Console did not produce real checkpoints")
                report.update(console_save_show=True, graph_initialized=True,
                              checkpoint_reopened=True, checkpoint_rows=count)
            elif interface == "browser":
                import streamlit as st
                from streamlit.testing.v1 import AppTest
                try:
                    st.cache_resource.clear()
                    with redirect_stdout(io.StringIO()):
                        page = AppTest.from_file(str(source / "streamlit_app.py"), default_timeout=45).run()
                    check_initial_page(page)
                    report.update(initial_page_rendered=True, chat_composers=len(page.chat_input),
                                  page_exceptions=0, page_errors=0)
                finally:
                    st.cache_resource.clear()
            else:
                raise ValueError("Unsupported CI interface")
        finally:
            module.graph.close()
    print(json.dumps(report), flush=True)


def run_check(interface, output, source=ROOT, timeout=120):
    from evaluations.core_install_acceptance import isolated_environment
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "P", "interface": interface, "scope": "Local offline source smoke; existing dependencies",
              "provider_requests": 0}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="jeshla-ci-smoke-", ignore_cleanup_errors=True) as directory:
        fixture = Path(directory)
        state, cwd = fixture / "state", fixture / "unrelated"
        state.mkdir(); cwd.mkdir()
        (state / ".env").write_text("LLM_PROVIDER=groq\nGROQ_API_KEY=fixture-key-not-real\nGROQ_MODEL=fixture-model\n", encoding="utf-8")
        env = isolated_environment(source, Path(sys.executable).parent)
        env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1", JESHLA_HOME=str(state),
                   LLM_ALLOW_LOCAL_OLLAMA="false", AI_DEPLOYMENT_MODE="hosted",
                   AI_MEMORY_USER_ID="ci-user", AI_MEMORY_NAMESPACE="ci-space",
                   AI_SUMMARY_THRESHOLD_CHARS="16000", STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
        command = [sys.executable, "-B", "-c",
                   "import sys; from evaluations.ci_smoke import worker; worker(*sys.argv[1:])",
                   interface, str(source), str(state)]
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", start_new_session=os.name != "nt",
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Workers run only guarded startup/memory checks; no user commands
            # or browser/server subprocesses are launched on Windows.
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=10)
        (output / (interface + ".log")).write_text(stdout + "\n" + stderr, encoding="utf-8")
        report.update(timed_out=timed_out, exit_code=process.returncode,
                      owned_process_stopped=process.poll() is not None)
        if not timed_out and process.returncode == 0:
            try:
                report["checks"] = json.loads(stdout)
                report["status"] = "Y"
            except json.JSONDecodeError:
                report["failure"] = "CI worker returned no valid result"
    report.update(fixture_removed=not fixture.exists(), seconds=round(time.monotonic() - started, 2))
    if not report["fixture_removed"]:
        report["status"] = "P"
    (output / (interface + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True, choices=("console", "browser"))
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/ci")
    args = parser.parse_args()
    report = run_check(args.interface, args.output_dir, args.source)
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "Y" else 1


if __name__ == "__main__":
    raise SystemExit(main())
