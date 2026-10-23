"""Opt-in, cached-only WS3 semantic calibration over fixed synthetic facts.

Expectations are declared before encoding. No provider calls, downloads, threshold
changes or original memory access. This finite sample is not broad-domain proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluations.semantic_memory_local import FACTS

PARAPHRASES = [
    ("commute_transport", "What transportation do I use for commuting?", "travel"),
    ("report_export", "How are the test reports supposed to be exported?", "report_format"),
    ("browser_interactions", "What automates our browser interactions?", "ui_tool"),
    ("java_build", "What compiles and builds our Java project?", "build_tool"),
    ("http_api_tool", "Which tool handles checks of HTTP APIs?", "api_tool"),
    ("rest_endpoints", "How do we test the REST endpoints?", "api_tool"),
    ("unrelated_cad", "Which software renders CAD drawings?", None),
    ("unrelated_password", "What is my database password?", None),
    ("unrelated_medical", "What is my blood group?", None),
    ("unrelated_calendar", "When is my next dentist appointment?", None),
]
CONTEXT_FACTS = {
    "report_atlas_2026_archive": {"project": "Atlas", "year": "2026", "role": "archive export", "format": "PDF"},
    "report_atlas_2026_preview": {"project": "Atlas", "year": "2026", "role": "browser preview", "format": "HTML"},
    "report_boreal_2026_archive": {"project": "Boreal", "year": "2026", "role": "archive export", "format": "HTML"},
    "report_atlas_2025_archive": {"project": "Atlas", "year": "2025", "role": "archive export", "format": "HTML"},
}
CONTEXT_CASES = [
    ("atlas_archive_2026", "What file format is used for Atlas archive export in 2026?", "report_atlas_2026_archive"),
    ("atlas_preview_2026", "What file format is used for Atlas browser preview in 2026?", "report_atlas_2026_preview"),
    ("boreal_archive_2026", "What file format is used for Boreal archive export in 2026?", "report_boreal_2026_archive"),
    ("atlas_archive_2025", "What file format was used for Atlas archive export in 2025?", "report_atlas_2025_archive"),
]


def fingerprint(memory):
    return hashlib.sha256("\n".join(memory._connection.iterdump()).encode()).hexdigest()


def retrieval_case(memory, case_id, question, expected, *, top_one):
    before = fingerprint(memory)
    result = memory.semantic_search("calibration-user", "calibration-space", question, limit=3)
    facts = result["facts"]
    keys = [row["key"] for row in facts]
    match = (bool(keys) and keys[0] == expected if top_one else expected in keys) if expected is not None else not keys
    checks = {"expected_retrieval": match, "read_does_not_mutate": fingerprint(memory) == before,
              "other_scopes_excluded": "FOREIGN_SCOPE_CANARY" not in json.dumps(result),
              "scope_metadata_retained": all(row["namespace"] == "calibration-space" for row in facts)}
    return {"id": case_id, "expected_key": expected, "metric": "abstention" if expected is None else "top_one" if top_one else "recall_at_3",
            "checks": checks, "passed": all(checks.values()), "returned": [{"key": row["key"], "score": row["semantic_score"]} for row in facts]}


def worker(output, fixture_parent):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from tests.run_offline import offline_guard
    from agent.memory.long_term_memory import LongTermMemory
    report = {"status": "P", "scope": __doc__.strip(), "model": os.getenv("AI_MEMORY_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"), "threshold": 0.35, "cases": [], "expected_cases": 16,
              "matching_policy": "Clear paraphrases require top one; unrelated queries require no results; contextual candidates require expected key in top three. No truth/contradiction conclusion from similarity.", "provider_requests": 0, "downloads": False}
    start = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="facts-", dir=fixture_parent) as directory, offline_guard():
            folder = Path(directory)
            with LongTermMemory(folder / "facts.sqlite3") as memory:
                for key, value in FACTS.items():
                    memory.save("calibration-user", "calibration-space", key, value)
                memory.save("other-user", "calibration-space", "private", "FOREIGN_SCOPE_CANARY commute PDF Playwright Gradle REST API")
                memory.save("calibration-user", "other-space", "private", "FOREIGN_SCOPE_CANARY commute PDF Playwright Gradle REST API")
                for name, question, expected in PARAPHRASES:
                    print(json.dumps({"case": name, "phase": "encoding"}), flush=True)
                    report["cases"].append(retrieval_case(memory, name, question, expected, top_one=True))
                memory.save("calibration-user", "calibration-space", "report_format", "Please deliver reports as DOCX documents.")
                row = retrieval_case(memory, "corrected_docx", "What file type should reports be delivered in now?", "report_format", top_one=True)
                current = memory.semantic_search("calibration-user", "calibration-space", "What file type should reports be delivered in now?", limit=3)
                row["checks"]["current_value_only"] = any(fact["key"] == "report_format" and fact["value"] == "Please deliver reports as DOCX documents." for fact in current["facts"]) and not any(fact["key"] == "report_format" and "PDF" in str(fact["value"]) for fact in current["facts"])
                row["passed"] = all(row["checks"].values()); report["cases"].append(row)
                memory.delete("calibration-user", "calibration-space", "report_format")
                before = fingerprint(memory)
                result = memory.semantic_search("calibration-user", "calibration-space", "What file type should reports be delivered in?", limit=3)
                checks = {"deleted_key_absent": all(row["key"] != "report_format" for row in result["facts"]), "no_mutation": fingerprint(memory) == before, "scope_excluded": "FOREIGN_SCOPE_CANARY" not in json.dumps(result)}
                report["cases"].append({"id": "deleted_report", "metric": "deletion", "checks": checks, "passed": all(checks.values())})
            with LongTermMemory(folder / "contexts.sqlite3") as memory:
                for key, value in CONTEXT_FACTS.items():
                    memory.save("calibration-user", "calibration-space", key, value)
                memory.save("other-user", "calibration-space", "private", "FOREIGN_SCOPE_CANARY Atlas Boreal 2026 report archive preview PDF HTML")
                memory.save("calibration-user", "other-space", "private", "FOREIGN_SCOPE_CANARY Atlas Boreal 2026 report archive preview PDF HTML")
                for name, question, expected in CONTEXT_CASES:
                    report["cases"].append(retrieval_case(memory, name, question, expected, top_one=False))
        report["temporary_store_removed"] = not folder.exists()
        report["status"] = "Y" if len(report["cases"]) == 16 and all(case["passed"] for case in report["cases"]) else "P"
    except Exception as error:
        import traceback
        traceback.print_exc()  # Synthetic, local-only fixture diagnostics; no user facts.
        reason = "APPLICATION_CONTROL" if "Application Control policy" in str(error) else "LOCAL_RUNTIME"
        report.update(error_type=type(error).__name__, reason=reason, error="Cached-only local calibration could not complete; no download, provider call or threshold adjustment attempted.")
    report["seconds"] = round(time.monotonic() - start, 2)
    report["passed"] = sum(case["passed"] for case in report["cases"])
    (output / "worker-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "Y" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--fixture-parent", help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=True)
    if args.worker:
        return worker(output, args.fixture_parent)
    settings = ROOT / ".env"
    before = hashlib.sha256(settings.read_bytes()).hexdigest()
    environment = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic(); timed_out = False
    with tempfile.TemporaryDirectory(prefix="jeshla-semantic-calibration-") as fixture_parent:
        with (output / "run.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--worker", "--fixture-parent", fixture_parent, "--output-dir", str(output)], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
            print(json.dumps({"event": "worker_started", "pid": process.pid, "configured_timeout_seconds": 90}), flush=True)
            try:
                code = process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                timed_out = True; process.kill(); process.wait(timeout=10); code = process.returncode
    report = {"status": "Y" if code == 0 and not timed_out else "P", "exit_code": code, "timed_out": timed_out, "configured_timeout_seconds": 90, "elapsed_seconds": round(time.monotonic() - started, 2), "owned_process_stopped": process.poll() is not None, "fixture_removed": not Path(fixture_parent).exists(), "saved_settings_unchanged": before == hashlib.sha256(settings.read_bytes()).hexdigest(), "scope": "New fixed local semantic calibration, not cold fresh-install acceptance or universal retrieval quality."}
    path = output / "worker-result.json"
    if path.exists(): report["worker"] = json.loads(path.read_text(encoding="utf-8"))
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "Y" else 1


if __name__ == "__main__":
    raise SystemExit(main())
