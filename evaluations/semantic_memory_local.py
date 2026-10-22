"""Bounded cached-only semantic memory sample; synthetic stores, no downloads/API calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/acceptance/ws8-semantic-memory-20261021"
FACTS = {
    "travel": "I commute to work by train.",
    "report_format": "Please deliver reports as PDF documents.",
    "ui_tool": "We automate web browser testing with Playwright.",
    "build_tool": "Gradle is the build system for our Java codebase.",
    "api_tool": "Our API testing library is REST Assured.",
}
CASES = [
    ("commute_paraphrase", "How do I travel to my job?", "travel"),
    ("report_paraphrase", "What file type should the report be delivered in?", "report_format"),
    ("browser_paraphrase", "Which library drives our web browser tests?", "ui_tool"),
    ("build_paraphrase", "Which build system is used for this codebase?", "build_tool"),
    ("unrelated_birds", "Which tropical birds migrate across the Pacific?", None),
    ("unrelated_currency", "What is the national currency of Iceland?", None),
]


def worker():
    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from tests.run_offline import offline_guard
    from agent.memory.long_term_memory import LongTermMemory
    report = {"status": "pending", "cases": [], "scope": "Eight fixed synthetic real-encoder checks at the unchanged 0.35 threshold; not broad/domain recall or latency certification."}
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="facts-", dir=os.environ["JESHLA_SEMANTIC_FIXTURE_PARENT"]) as folder:
            with offline_guard(), LongTermMemory(Path(folder) / "facts.sqlite3") as memory:
                for key, value in FACTS.items():
                    memory.save("fixture-user", "fixture-space", key, value)
                memory.save("foreign-user", "fixture-space", "private", "PRIVATE_SCOPE_CANARY train PDF")
                memory.save("fixture-user", "foreign-space", "private", "PRIVATE_SCOPE_CANARY train PDF")
                for case, question, expected in CASES:
                    before = hashlib.sha256("\n".join(memory._connection.iterdump()).encode()).hexdigest()
                    print("Semantic case: " + case, flush=True)
                    result = memory.semantic_search("fixture-user", "fixture-space", question, limit=3)
                    facts = result["facts"]
                    matched = bool(facts) and facts[0]["key"] == expected if expected is not None else not facts
                    unchanged = before == hashlib.sha256("\n".join(memory._connection.iterdump()).encode()).hexdigest()
                    scoped = "PRIVATE_SCOPE_CANARY" not in json.dumps(result)
                    report["cases"].append({"id": case, "passed": matched and unchanged and scoped, "expected_top": expected, "returned": [{"key": row["key"], "score": row["semantic_score"]} for row in facts], "no_mutation": unchanged, "other_scopes_excluded": scoped})
                memory.save("fixture-user", "fixture-space", "travel", "I commute to work by bicycle.")
                result = memory.semantic_search("fixture-user", "fixture-space", "What do I ride to my job now?", limit=3)
                report["cases"].append({"id": "updated_value", "passed": bool(result["facts"]) and result["facts"][0]["key"] == "travel" and "bicycle" in result["facts"][0]["value"]})
                memory.delete("fixture-user", "fixture-space", "travel")
                result = memory.semantic_search("fixture-user", "fixture-space", "How do I travel to work?", limit=3)
                report["cases"].append({"id": "deleted_fact", "passed": all(row["key"] != "travel" for row in result["facts"])})
            report["temporary_store_removed"] = False
        report["temporary_store_removed"] = not Path(folder).exists()
        report["status"] = "passed" if all(row["passed"] for row in report["cases"]) else "pending"
    except Exception as error:
        report.update(error_kind=type(error).__name__, explanation="The cached-only sample could not complete; no resource download or threshold change was attempted.")
    report.update(seconds=round(time.monotonic() - started, 2), passed=sum(row["passed"] for row in report["cases"]), requested=8, threshold=0.35, external_requests_blocked=True, model_downloads=False)
    (OUTPUT / "worker-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if "--worker" in sys.argv:
        return worker()
    environment = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    settings = ROOT / ".env"
    before = hashlib.sha256(settings.read_bytes()).hexdigest()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="jeshla-semantic-run-", ignore_cleanup_errors=True) as fixture_parent:
        environment["JESHLA_SEMANTIC_FIXTURE_PARENT"] = fixture_parent
        with (OUTPUT / "run.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--worker"], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=90)
                status = "passed" if code == 0 else "pending"
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=log, stderr=subprocess.STDOUT, timeout=10)
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
                code = None
                status = "timeout"
    report = {"status": status, "returncode": code, "seconds": round(time.monotonic() - started, 2), "process_stopped": process.poll() is not None, "fixture_removed": not Path(fixture_parent).exists(), "settings_unchanged": before == hashlib.sha256(settings.read_bytes()).hexdigest()}
    if code is not None and (OUTPUT / "worker-result.json").exists():
        report["worker"] = json.loads((OUTPUT / "worker-result.json").read_text(encoding="utf-8"))
    (OUTPUT / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
