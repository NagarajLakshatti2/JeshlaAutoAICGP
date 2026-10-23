"""Build a scoped historical test report without executing, exporting or filing."""
from collections import Counter
from datetime import datetime, timedelta
import html
import json
from pathlib import Path
import re
from urllib.parse import quote

from agent.tools.test_results import parse_test_results
from integrations.reporting.evidence import EvidenceStore, resolve_evidence

ACCEPTANCE_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "acceptance"
CASE_KEYS = {"id", "test_name", "test_class", "requirement_refs", "generated_ref", "run_ref", "report_ref", "artifact_refs", "scope_state", "note"}
COUNTS = ("total", "passed", "failed", "skipped", "incomplete", "configuration_failure_count")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("Saved run/report timestamps must be ISO strings.")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Saved run/report timestamps require a timezone.")
    return result


def _association(run, parsed, ref):
    # Compare the original selected-project report with the saved run snapshot.
    # Matching metadata is not cryptographic execution/source provenance.
    if ref["scope"] != "project" or run.get("report_status") != "fresh_reports_found" or run.get("report_errors"):
        return False
    snapshots = run.get("reports", [])
    if not isinstance(snapshots, list):
        return False
    matches = [r for r in snapshots if isinstance(r, dict) and r.get("file") == parsed["file"]]
    if len(matches) != 1:
        return False
    snapshot = matches[0]
    if (snapshot.get("freshness") != "associated with this command by changed content/metadata and execution time window"
            or any(snapshot.get(k) != parsed[k] for k in (*COUNTS, "tests", "configuration_failures", "details_truncated", "overall_status", "modified_at", "format"))):
        return False
    start, finish, modified = _time(run.get("started_at")), _time(run.get("finished_at")), _time(parsed["modified_at"])
    return start <= finish and start - timedelta(seconds=2) <= modified <= finish + timedelta(seconds=2)


def _safe_text(value):
    value = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
    value = html.escape(value, quote=True)
    return re.sub(r"([\\`*_{\[\]()|#!])", r"\\\1", value)


def render_markdown(report):
    lines = ["# " + _safe_text(report["title"]), "", "Historical selected-scope evidence report; no new test execution or release certification.", "",
             "| Case | Native report | Effective outcome | Scope | Evidence | Notes and gaps |", "| --- | --- | --- | --- | --- | --- |"]
    for case in report["cases"]:
        req = ",".join(r["evidence_id"] + ":" + str(r["start_line"]) + "-" + str(r["end_line"]) for r in case["requirement_links"]) or "missing"
        refs = f'req={req}; source={case["generated_evidence_id"] or "missing"}; run={(case["execution"] or {}).get("evidence_id", "missing")}; report={case["report_evidence_id"] or "missing"}'
        if case["artifacts"]:
            refs += "; " + ",".join(a["kind"]+"="+a["evidence_id"] for a in case["artifacts"])
        lines.append("| " + " | ".join(_safe_text(v) for v in (case["id"], case["native_status"], case["outcome"], case["scope_state"], refs, "; ".join(case["gaps"] + ([case["note"]] if case["note"] else [])))) + " |")
    lines += ["", "Native observations: " + _safe_text(json.dumps(report["summary"]["native_counts"], sort_keys=True)),
              "", "Effective outcomes: " + _safe_text(json.dumps(report["summary"]["outcome_counts"], sort_keys=True)),
              "", "## Evidence references", ""]
    for item in report["evidence"]:
        url = quote(item["path"], safe="/:")
        lines.append(f'- {item["id"]}: [{_safe_text(item["scope"] + ":" + item["file"])}](<{url}>) — SHA256 `{item["sha256"]}`')
    lines += ["", "## Limits", ""] + ["- " + _safe_text(item) for item in report["limits"]]
    return "\n".join(lines) + "\n"


def build_test_report(project_root, manifest_file, evidence_folder=""):
    """Read a manifest from the project or one owned acceptance subdirectory.

    No arbitrary external evidence root is accepted. Artifact scopes explicitly
    distinguish the selected target project from the agent's acceptance archive.
    """
    project_root = Path(project_root).resolve()
    if not isinstance(evidence_folder, str):
        raise ValueError("evidence_folder must be text.")
    if evidence_folder:
        evidence_root = Path(evidence_folder).resolve()
        boundary = ACCEPTANCE_ROOT.resolve()
        if evidence_root == boundary or not evidence_root.is_relative_to(boundary):
            raise ValueError("Choose one dedicated directory under the agent outputs/acceptance folder.")
    else:
        evidence_root = project_root
    path = resolve_evidence(evidence_root, manifest_file)
    if path.suffix.lower() != ".json" or path.stat().st_size > 100_000:
        raise ValueError("Manifest must be JSON up to 100,000 bytes.")
    import hashlib
    with path.open("rb") as handle:
        raw = handle.read(100_001)
    if len(raw) > 100_000:
        raise ValueError("Manifest exceeds its size limit.")
    store = EvidenceStore(project_root, evidence_root)
    manifest_ref = {"scope":"evidence", "file":str(path.relative_to(evidence_root)), "sha256":hashlib.sha256(raw).hexdigest()}
    _, manifest = store.json(manifest_ref)
    if not isinstance(manifest, dict) or set(manifest) != {"version", "title", "cases"} or type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ValueError("Manifest requires version 1, title and cases only.")
    if not isinstance(manifest["title"], str) or not 1 <= len(manifest["title"]) <= 120:
        raise ValueError("Report title must be 1–120 characters.")
    cases = manifest["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 24:
        raise ValueError("Select 1–24 cases, with each logical case represented once.")
    ids, methods, rows = set(), set(), []
    reports_cache = {}
    for case in cases:
        if not isinstance(case, dict) or set(case) - CASE_KEYS or not isinstance(case.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", case["id"]):
            raise ValueError("Invalid case fields or case ID.")
        if case["id"] in ids:
            raise ValueError("Duplicate case ID; do not pool attempts into one count.")
        ids.add(case["id"])
        scope_state = case.get("scope_state", "included")
        if scope_state not in {"included", "blocked", "deferred"}:
            raise ValueError("Scope state must be included, blocked or deferred.")
        note = case.get("note", "")
        if not isinstance(note, str) or len(note) > 500:
            raise ValueError("Case notes must be bounded text, never instructions.")
        gaps, evidence_ids, requirement_links = [], [], []
        refs = case.get("requirement_refs", [])
        if not isinstance(refs, list) or len(refs) > 3:
            raise ValueError("Use up to three requirement spans per case.")
        for span in refs:
            if not isinstance(span, dict) or set(span) != {"ref", "start_line", "end_line", "quote"}:
                raise ValueError("Requirement span needs ref, start_line, end_line and quote.")
            record, content, _ = store.read(span["ref"], text=True)
            start, end, excerpt = span["start_line"], span["end_line"], span["quote"]
            if type(start) is not int or type(end) is not int or not 1 <= start <= end or end-start >= 80 or not isinstance(excerpt, str) or not 1 <= len(excerpt) <= 1600:
                raise ValueError("Invalid requirement span bounds/quote.")
            lines = content.splitlines()
            normalize = lambda value: " ".join(value.split())
            if end > len(lines) or normalize(excerpt) not in normalize("\n".join(lines[start-1:end])):
                raise ValueError("Requirement quote is absent from its exact source span.")
            evidence_ids.append(record["id"])
            requirement_links.append({"evidence_id":record["id"], "start_line":start, "end_line":end, "quote":excerpt})
        if not refs:
            gaps.append("requirement link missing")
        generated = None
        if case.get("generated_ref"):
            record, _, _ = store.read(case["generated_ref"], text=True)
            evidence_ids.append(record["id"]);generated = record["id"]
        else:
            gaps.append("generated source link missing")
        artifact_links = []
        artifacts = case.get("artifact_refs", [])
        if not isinstance(artifacts, list) or len(artifacts) > 6:
            raise ValueError("Use up to six artifact links per case.")
        for item in artifacts:
            if not isinstance(item, dict) or set(item) != {"kind", "ref"} or item["kind"] not in {"response", "observation", "screenshot", "trace", "log", "investigation", "source_provenance"}:
                raise ValueError("Invalid evidence artifact link.")
            record, _, _ = store.read(item["ref"])
            evidence_ids.append(record["id"]);artifact_links.append({"kind":item["kind"], "evidence_id":record["id"]})
        if not artifacts:
            gaps.append("supporting artifact link missing")
        native, outcome, association = "not_run", "not_run", "not_assessed"
        run_info, report_id = None, None
        run = None
        if case.get("run_ref"):
            record, run = store.json(case["run_ref"])
            if not isinstance(run, dict) or "exit_code" not in run or type(run.get("timed_out")) is not bool or (run.get("exit_code") is not None and type(run.get("exit_code")) is not int):
                raise ValueError("Saved execution needs boolean timed_out and integer/null exit_code.")
            evidence_ids.append(record["id"])
            run_info = {"evidence_id":record["id"], "exit_code":run.get("exit_code"), "timed_out":run["timed_out"],
                        "started_at":run.get("started_at"), "finished_at":run.get("finished_at")}
        if case.get("report_ref"):
            if not isinstance(case.get("test_name"), str) or not isinstance(case.get("test_class", ""), str):
                raise ValueError("Report mapping requires an exact test_name and optional test_class.")
            record, _, _ = store.read(case["report_ref"], text=True)
            evidence_ids.append(record["id"]);report_id=record["id"]
            cache_key = (record["scope"], record["file"])
            if cache_key not in reports_cache:
                reports_cache[cache_key] = parse_test_results(store.roots[record["scope"]], record["file"], limit=500)
            parsed = reports_cache[cache_key]
            if parsed["details_truncated"]:
                raise ValueError("Report inventory is truncated; choose a smaller report.")
            selected = [r for r in parsed["tests"] if r["name"] == case["test_name"] and (not case.get("test_class") or r.get("class", "") == case["test_class"])]
            if len(selected) != 1:
                raise ValueError("Selected test is missing or ambiguous in its report.")
            test = selected[0]
            identity = (test.get("class", ""), test["name"])
            if identity in methods:
                raise ValueError("Duplicate native test mapping; select one attempt per logical case.")
            methods.add(identity)
            native = test["status"]
            associated = run is not None and _association(run, parsed, case["report_ref"])
            association = "saved_run_metadata_matches_current_report" if associated else "unverified"
            if not associated:
                gaps.append("report/run association unverified")
            if run is None:
                gaps.append("execution record missing")
            successful = (associated and run["exit_code"] == 0 and not run["timed_out"]
                          and not parsed["configuration_failure_count"] and parsed["overall_status"] == "passed")
            if associated and run["exit_code"] == 0 and not run["timed_out"] and not parsed["configuration_failure_count"] and native == "skipped":
                outcome = "skipped"
            elif successful:
                outcome = native
            elif associated and native == "failed" and run["exit_code"] is not None and not run["timed_out"]:
                outcome = "failed"
            else:
                outcome = "incomplete"
            if run and (run["timed_out"] or run["exit_code"] is None):
                gaps.append("uncertain execution; no automatic replay")
            elif run and run["exit_code"] != 0:
                gaps.append("command unsuccessful")
            if parsed["configuration_failure_count"]:
                gaps.append("configuration failure present")

        elif run is not None:
            outcome = "incomplete";gaps.append("native results report missing")
        if native == "not_run" and scope_state == "blocked" and run is None:
            outcome = "blocked"
        rows.append({"id":case["id"], "scope_state":scope_state, "note":note, "native_status":native,
                     "outcome":outcome, "source_execution_identity":"unverified", "requirement_links":requirement_links, "generated_evidence_id":generated,
                     "execution":run_info, "report_evidence_id":report_id, "report_run_association":association,
                     "artifacts":artifact_links, "evidence_ids":list(dict.fromkeys(evidence_ids)), "gaps":gaps})
    store.verify_unchanged()
    return {"version":1, "build_status":"Y", "status":"P" if any(row["gaps"] or row["outcome"] != "passed" for row in rows) else "Y",
            "title":manifest["title"], "roots":{k:str(v) for k,v in store.roots.items()},
            "summary":{"selected_cases":len(rows), "native_counts":dict(Counter(r["native_status"] for r in rows)),
                       "outcome_counts":dict(Counter(r["outcome"] for r in rows)),
                       "cases_with_trace_gaps":sum(bool(r["gaps"]) for r in rows)},
            "cases":rows, "evidence":store.records,
            "limits":["Counts cover selected unique cases, not all application requirements or overlapping reports.",
                      "Saved run/report metadata association is evidence, not cryptographic proof of execution or executed source identity.",
                      "Requirement quote membership and file hashes do not establish semantic coverage, business correctness or approval.",
                      "Binary artifacts have verified bytes only; no screenshot or trace-content inspection is claimed.",
                      "Partial/failed/blocked cases remain explicit. No rerun, file export, Jira login/write, GitHub operation or release acceptance occurred."],
            "actions_executed":[]}


def report_for_agent(project_root, manifest_file, evidence_folder=""):
    report = build_test_report(project_root, manifest_file, evidence_folder)
    result = {"status":report["status"], "summary":report["summary"], "markdown":render_markdown(report),
              "export_policy":"Review this content; save only through an existing approved create_file action. No file was exported.",
              "actions_executed":[]}
    if len(json.dumps(result)) > 16000:
        raise ValueError("Report exceeds the agent response budget; select fewer cases/artifact links.")
    return result
