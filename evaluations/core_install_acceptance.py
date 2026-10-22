"""Bounded fresh editable-install rehearsal; no model downloads or live providers.

Copies allowlisted source assets only into a disposable directory. All application
state created by startup/tests belongs to that copy. The optional rag profile
adds package imports and synthetic parser/vector/keyword checks with fixture
embeddings. Pretrained model quality, physical-browser behavior, the full learning
profile and a fresh GitHub clone are outside this acceptance.
"""
import argparse
import configparser
from email.parser import Parser
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.metadata
import json
import os
import secrets
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tarfile
import tomllib
import zipfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "test_chat_catalog", "test_chat_runtime", "test_chat_commands",
    "test_named_sessions", "test_archive_search", "test_memory_review",
    "test_memory_provenance", "test_memory_revisions", "test_memory_suggestions",
    "test_semantic_memory", "test_context_summary", "test_summary_model",
    "test_summary_sessions", "test_local_action_receipts", "test_browser_actions",
    "test_browser_action_ui", "test_foundation_errors", "test_provider_errors",
    "test_model_budget", "test_tool_llm", "test_provider_selection",
    "test_conversation_sources", "test_conversation_workflow",
    "test_package_compatibility", "test_backup_recovery", "test_streamlit_ui",
    "test_chat_landing", "test_request_status",
)


def fingerprint_environment():
    rows = sorted((item.metadata.get("Name", "").lower(), item.version) for item in importlib.metadata.distributions())
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


def copy_source(destination):
    excluded = {"__pycache__", ".git", ".venv", "outputs", "uploads", "data", "faiss_index", "indexes"}
    manifest = []
    for package in ("agent", "rag", "integrations", "tests"):
        for source in (ROOT / package).rglob("*"):
            relative = source.relative_to(ROOT)
            if not source.is_file() or source.is_symlink() or any(part in excluded or part.startswith(".") for part in relative.parts):
                continue
            if source.suffix.lower() not in {".py", ".css", ".js", ".html", ".svg"}:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest.append(str(relative))
    for name in ("pyproject.toml", "requirements-core.txt", "README.md", "streamlit_app.py", ".streamlit/config.toml"):
        source = ROOT / name
        if source.exists():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest.append(name)
    target = destination / "evaluations" / Path(__file__).name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__), target)
    manifest.append(str(target.relative_to(destination)))
    (destination / ".env").write_text("LLM_PROVIDER=groq\nGROQ_API_KEY=fixture-key-not-real\nGROQ_MODEL=fixture-model\n", encoding="utf-8")
    return manifest


def isolated_environment(source, scripts):
    prefixes = ("AI_", "GROQ_", "OPENROUTER_", "OLLAMA_", "GEMINI_", "GOOGLE_AI_", "OPENAI_", "JIRA_", "LANGSMITH_", "LANGCHAIN_")
    environment = {
        key: value for key, value in os.environ.items()
        if key.upper() not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "JESHLA_HOME", "LLM_PROVIDER", "LLM_FALLBACK_ENABLED", "LLM_ALLOW_LOCAL_OLLAMA", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"}
        and not key.upper().endswith("_API_KEY") and not key.upper().startswith(prefixes)
    }
    environment.update(
        PYTHONNOUSERSITE="1", PYTHONUTF8="1", LLM_PROVIDER="groq", LLM_FALLBACK_ENABLED="false", LLM_ALLOW_LOCAL_OLLAMA="false",
        GROQ_API_KEY="fixture-key-not-real", GROQ_MODEL="fixture-model",
        AI_PROJECT_ROOT=str(source), AI_MEMORY_USER_ID="local-user",
        AI_MEMORY_NAMESPACE="project", HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1", JESHLA_EXECUTION_MODE="offline",
        PATH=str(scripts) + os.pathsep + environment.get("PATH", ""),
        PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1",
    )
    return environment


def optional_profile_smoke():
    """Real optional-package/API imports and synthetic local indexes; no real models."""
    import importlib
    import pickle
    rows = []
    for name in ("openpyxl", "pypdf", "docx", "langchain_community.vectorstores", "langchain_huggingface", "langchain_text_splitters", "faiss", "rank_bm25", "mcp", "httpx2", "integrations.jira.jira_mcp_client"):
        print("Optional import: " + name, flush=True)
        try:
            importlib.import_module(name)
            rows.append({"module": name, "status": "passed"})
        except Exception as error:
            rows.append({"module": name, "status": "failed", "error_kind": type(error).__name__, "detail": str(error)[:500]})
    report = {"imports": rows, "scope": "Real package imports and synthetic parser/index smoke with deterministic fixture embeddings; not pretrained semantic quality or live Jira acceptance."}
    required = {"openpyxl", "pypdf", "docx", "langchain_community.vectorstores", "langchain_huggingface", "langchain_text_splitters", "faiss", "rank_bm25"}
    if not all(row["status"] == "passed" for row in rows if row["module"] in required):
        report["status"] = "failed"
        return report
    from langchain_core.embeddings import Embeddings
    from langchain_community.vectorstores import FAISS
    from docx import Document
    from pypdf import PdfWriter, PdfReader
    from rag.ingest import create_vector_db

    class FixtureEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [self.embed_query(text) for text in texts]
        def embed_query(self, text):
            return [float(text.lower().count(term)) for term in ("quartz", "cobalt", "amber")]

    with tempfile.TemporaryDirectory(prefix="jeshla-rag-smoke-") as directory:
        root = Path(directory)
        data = root / "documents"
        data.mkdir()
        (data / "quartz.txt").write_text("quartz report", encoding="utf-8")
        (data / "amber.csv").write_text("Name,Value\nTask,amber\n", encoding="utf-8")
        document = Document()
        document.add_paragraph("cobalt workflow")
        document.save(data / "cobalt.docx")
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(data / "blank.pdf")
        assert len(PdfReader(data / "blank.pdf").pages) == 1
        model = FixtureEmbeddings()
        with patch("langchain_huggingface.HuggingFaceEmbeddings", return_value=model):
            create_vector_db(data_folder=data, index_folder=root / "indexes")
        with (root / "indexes/chunks.pkl").open("rb") as handle:
            chunks = pickle.load(handle)
        assert {item.metadata["source"] for item in chunks} == {"quartz.txt", "amber.csv", "cobalt.docx"}
        vector = FAISS.load_local(str(root / "indexes/faiss_db"), model, allow_dangerous_deserialization=True)
        assert vector.similarity_search("quartz", k=1)[0].metadata["source"] == "quartz.txt"
        with (root / "indexes/bm25.pkl").open("rb") as handle:
            keyword = pickle.load(handle)
        assert keyword.get_top_n(["cobalt"], chunks, n=1)[0].metadata["source"] == "cobalt.docx"
        report.update(synthetic_ingestion_and_index_reopen=True, synthetic_keyword_and_vector_lookup=True, blank_pdf_parser=True, chunks=len(chunks))
    # Heavy optional ML imports must not starve unrelated parser/core checks.
    print("Bounded optional import: sentence_transformers", flush=True)
    probe_code = "import faulthandler; faulthandler.enable(); faulthandler.dump_traceback_later(20, repeat=True); import sentence_transformers; print('optional ML import passed', flush=True); faulthandler.cancel_dump_traceback_later()"
    probe = subprocess.Popen([sys.executable, "-u", "-c", probe_code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    began = time.monotonic()
    try:
        output, _ = probe.communicate(timeout=60)
        heavy = {"module": "sentence_transformers", "status": "passed" if probe.returncode == 0 else "failed", "returncode": probe.returncode, "diagnostic_tail": output[-1000:]}
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(probe.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
        if probe.poll() is None:
            probe.kill()
        output, _ = probe.communicate(timeout=10)
        heavy = {"module": "sentence_transformers", "status": "timeout", "diagnostic_tail": output[-4000:]}
    heavy.update(seconds=round(time.monotonic() - began, 2), timeout_seconds=60, process_stopped=probe.poll() is not None)
    rows.append(heavy)
    report["status"] = "passed" if all(row["status"] == "passed" for row in rows) else "pending"
    return report


def worker(profile="core"):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    from agent.config.paths import APPLICATION_ROOT
    from tests.run_offline import offline_guard
    assert APPLICATION_ROOT.resolve() == ROOT.resolve(), "Unexpected application state root."
    assert sys.prefix != sys.base_prefix, "Worker is not in a virtual environment."
    config = (Path(sys.prefix) / "pyvenv.cfg").read_text(encoding="utf-8")
    assert "include-system-site-packages = false" in config.lower()
    # Editable source egg-info can shadow installed dist-info on sys.path.
    installed = importlib.metadata.distributions(path=[sysconfig.get_path("purelib")])
    distribution = next(item for item in installed if item.metadata.get("Name", "").lower().replace("_", "-") == "jeshla-auto-ai")
    direct = json.loads(distribution.read_text("direct_url.json"))
    assert direct.get("dir_info", {}).get("editable") is True
    assert direct.get("url") == ROOT.as_uri(), "Editable distribution targets a different source tree."
    started = time.perf_counter()
    with offline_guard(), patch.dict(os.environ, {"JESHLA_EXECUTION_MODE": "offline"}):
        optional = None
        if profile == "rag":
            try:
                optional = optional_profile_smoke()
            except Exception as error:
                optional = {"status": "failed", "error_kind": type(error).__name__, "diagnostic": str(error)[:1000]}
                print("Optional smoke failed: " + type(error).__name__ + ": " + str(error)[:1000], flush=True)
        selected = MODULES + (("test_document_sources", "test_legacy_rag_entrypoints", "test_rag_paths", "test_table_memory_tools", "test_table_grounding") if profile == "rag" else ())
        suite = unittest.defaultTestLoader.loadTestsFromNames(selected)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        # This is a framework startup smoke check, not DOM/browser acceptance.
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        st.cache_resource.clear()
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()
        ui_ok = not app.exception and bool(app.chat_input) and any(element.value == "What would you like to build?" for element in app.title)
        st.cache_resource.clear()
    report = {
        "status": "passed" if result.wasSuccessful() and ui_ok and (optional is None or optional["status"] == "passed") else "failed",
        "profile": profile, "optional_profile": optional,
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "browser_framework_initial_render": ui_ok, "network_blocked_in_tests": True,
        "isolated_application_root": True, "editable_distribution": True,
        "python": sys.version.split()[0], "streamlit": importlib.metadata.version("streamlit"),
        "seconds": round(time.perf_counter() - started, 2), "modules": list(selected),
        "scope": "Selected offline regressions and AppTest startup; RAG profile adds actual imports and synthetic parser/index checks using fixture embeddings. No pretrained models, real browsers or provider/Jira requests.",
    }
    (ROOT / "worker-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1



def audit_archives(artifacts, source, private_marker):
    """Inspect generated archives without extraction or application imports."""
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    wheels = list(artifacts.glob("*.whl"))
    sdists = list(artifacts.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, "Expected one wheel and one source archive."
    required = {"streamlit_app.py", "agent/langgraph/langgraph_agent.py", "agent/memory/evidence.py", "agent/runtime/conversation.py", "agent/runtime/summary_model.py", "agent/conversation.py", "agent/summary_model.py"}
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        assert required <= set(names), "Current entry points/helpers missing from wheel."
        assert not any(name.startswith(("tests/", "evaluations/", "outputs/", "docs/")) for name in names)
        assert not any(private_marker in archive.read(name) for name in names if not name.endswith("/")), "Private canary entered wheel."
        metadata = Parser().parsestr(archive.read(next(name for name in names if name.endswith(".dist-info/METADATA"))).decode("utf-8"))
        entries = configparser.ConfigParser()
        entries.read_string(archive.read(next(name for name in names if name.endswith(".dist-info/entry_points.txt"))).decode("utf-8"))
        assert entries["console_scripts"]["jeshla-auto-ai"] == "agent.langgraph.langgraph_agent:main"
        declared = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
        base = {canonicalize_name(item.name) for item in declared if item.marker is None}
        expected = {canonicalize_name(Requirement(line).name) for line in (source / "requirements-core.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
        assert base == expected, "Core dependency metadata differs from its requirements file."
        config = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
        for extra, values in config["project"]["optional-dependencies"].items():
            actual = {canonicalize_name(item.name) for item in declared if item.marker is not None and item.marker.evaluate({"extra": extra})}
            assert actual == {canonicalize_name(Requirement(value).name) for value in values}, "Optional profile metadata mismatch: " + extra
        assert metadata["Requires-Python"] == config["project"]["requires-python"]
    with tarfile.open(sdists[0], "r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        relative = {member.name.split("/", 1)[1] for member in members if "/" in member.name}
        assert {"pyproject.toml", "requirements-core.txt", "agent/memory/evidence.py"} <= relative
        assert not any(private_marker in archive.extractfile(member).read() for member in members), "Private canary entered source archive."
    return {"status": "passed", "wheel": wheels[0].name, "sdist": sdists[0].name, "current_helpers_and_aliases_present": True, "core_and_optional_metadata_match": True, "installed_entrypoint_declared": True, "private_canaries_excluded_from_both": True, "wheel_excludes_test_evaluation_and_state_directories": True, "scope": "Prepared source allowlist plus private-data canaries; not an audit of all tracked Git files or non-editable runtime/data-root behavior."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "rag"), default="core", help="RAG profile adds optional document/vector packages and integration import checks; no model downloads.")
    parser.add_argument("--build-only", action="store_true", help="Offline archive/metadata audit with existing build tools; not clean-install acceptance.")
    parser.add_argument("--no-compile", action="store_true", help="Defer Python bytecode compilation to first use; does not alter installed dependency versions.")
    parser.add_argument("--wheelhouse", type=Path, help="Install exclusively from already downloaded wheels; build isolation remains enabled.")
    parser.add_argument("--output-dir", type=Path, help="Acceptance report directory; preserves earlier rehearsal reports.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.profile)
    if args.build_only and args.wheelhouse:
        parser.error("--wheelhouse applies to fresh installation only.")
    wheelhouse = args.wheelhouse.resolve() if args.wheelhouse else None
    if wheelhouse is not None and (not wheelhouse.is_dir() or not any(wheelhouse.glob("*.whl"))):
        parser.error("--wheelhouse must contain downloaded wheel files.")
    output = args.output_dir.resolve() if args.output_dir else ROOT / ("outputs/acceptance/ws8-source-build-current" if args.build_only else "outputs/acceptance/ws8-core-fresh-20261020")
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "pending", "profile": "offline source archive build" if args.build_only else args.profile + " editable source install", "stages": [], "scope": "Offline wheel/source-archive build from a prepared source allowlist and synthetic private-data canaries. No fresh installation, runtime/browser acceptance or Git publication audit." if args.build_only else __doc__.strip()}
    report["install_time_bytecode_compilation"] = not args.no_compile
    report["process_thread_settings"] = {key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    environment_before = fingerprint_environment()
    env_file = ROOT / ".env"
    settings_before = hashlib.sha256(env_file.read_bytes()).hexdigest() if env_file.exists() else None
    started = time.monotonic()
    deadline = started + (540 if args.profile == "rag" else 300)
    with tempfile.TemporaryDirectory(prefix="jeshla-core-install-", ignore_cleanup_errors=True) as directory:
        temporary = Path(directory).resolve()
        source = temporary / "source"
        source.mkdir()
        manifest = copy_source(source)
        (output / "source-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        scripts = temporary / "venv" / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        env = isolated_environment(source, scripts)
        if wheelhouse is not None:
            env.update(PIP_NO_INDEX="1", PIP_FIND_LINKS=str(wheelhouse))
            report["installation_package_index_disabled"] = True
            report["wheelhouse_manifest"] = [{"file": item.name, "sha256": hashlib.sha256(item.read_bytes()).hexdigest()} for item in sorted(wheelhouse.glob("*.whl"))]

        def stage(name, command, cap):
            remaining = min(cap, deadline - time.monotonic())
            if remaining <= 0:
                raise TimeoutError("Overall rehearsal budget exhausted.")
            row = {"name": name, "status": "running"}
            report["stages"].append(row)
            print(json.dumps(row), flush=True)
            (output / "progress.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            began = time.monotonic()
            with (output / (name + ".log")).open("w", encoding="utf-8") as log:
                process = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    code = process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    if os.name == "nt" and process.poll() is None:
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=log, stderr=subprocess.STDOUT, timeout=15, check=False)
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=10)
                    row["status"] = "timeout"
                    raise
                finally:
                    row.update(seconds=round(time.monotonic() - began, 2), process_stopped=process.poll() is not None)
                    (output / "progress.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            row.update(returncode=code, status="passed" if code == 0 else "failed")
            print(json.dumps(row), flush=True)
            (output / "progress.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            if code:
                raise RuntimeError("Rehearsal stage failed: " + name)

        try:
            if args.build_only:
                private_marker = secrets.token_bytes(24).hex().encode("ascii")
                for name in (".env", "outputs/private.sqlite3", "agent/memory/private_fact.json", "rag/data/private_source.csv", "docs/private_note.md"):
                    canary = source / name
                    canary.parent.mkdir(parents=True, exist_ok=True)
                    canary.write_bytes(private_marker)
                artifacts = temporary / "artifacts"
                artifacts.mkdir()
                env.update(PIP_NO_INDEX="1", UV_NO_INDEX="1")
                stage("offline-source-build", [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(artifacts), str(source)], 180)
                report["archive_audit"] = audit_archives(artifacts, source, private_marker)
                report["package_index_disabled"] = True
                report["status"] = "passed"
            else:
                stage("create-venv", [sys.executable, "-m", "venv", str(temporary / "venv")], 45)
                stage("editable-core-install", [str(python), "-m", "pip", "--disable-pip-version-check", "--retries", "0", "--timeout", "20", "install", "--progress-bar", "off", *(["--no-compile"] if args.no_compile else []), "-e", str(source) + ("[rag,integrations]" if args.profile == "rag" else "")], 300 if args.profile == "rag" else 180)
                stage("pip-check", [str(python), "-m", "pip", "check"], 30)
                stage("legacy-console-help", [str(python), "-m", "agent.langgraph.langgraph_agent", "--help"], 60)
                console = scripts / ("jeshla-auto-ai.exe" if os.name == "nt" else "jeshla-auto-ai")
                stage("installed-console-help", [str(console), "--help"], 60)
                stage("offline-core-and-browser-startup", [str(python), "-u", str(source / "evaluations" / Path(__file__).name), "--worker", "--profile", args.profile], 240 if args.profile == "rag" else 180)
                report["worker"] = json.loads((source / "worker-result.json").read_text(encoding="utf-8"))
                report["status"] = "passed" if report["worker"]["status"] == "passed" else "pending"
        except Exception as error:
            report["error_kind"] = type(error).__name__
            saved = source / "worker-result.json"
            if saved.exists():
                report["worker"] = json.loads(saved.read_text(encoding="utf-8"))
    settings_after = hashlib.sha256(env_file.read_bytes()).hexdigest() if env_file.exists() else None
    report.update(
        fixture_removed=not temporary.exists(),
        working_environment_unchanged=fingerprint_environment() == environment_before,
        provider_settings_unchanged=settings_after == settings_before,
        elapsed_seconds=round(time.monotonic() - started, 2),
        private_configuration_copied=False, persistent_user_data_copied=False,
        source_files_copied=len(manifest),
    )
    if not all(report[key] for key in ("fixture_removed", "working_environment_unchanged", "provider_settings_unchanged")):
        report["status"] = "pending"
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "progress.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "wheelhouse_manifest"}, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
