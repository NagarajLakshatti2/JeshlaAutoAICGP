"""Run one explicitly mapped, eligible Jira subtask using existing Gradle automation.

No model calls, source generation, or Jira writes. Normal Scenarios are supported;
Scenario Outlines need example-row evidence and are deliberately left incomplete.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def select_mapping(discovery, issue_key=None):
    rows = discovery.get("scenarios", [])
    verified = [r for r in rows if r.get("verification") == "verified_subtask"
                and r.get("jira_subtask_verified") is True]
    keys = sorted({r["jira_keys"][0] for r in verified if len(r.get("jira_keys", [])) == 1})
    if issue_key is None:
        if len(keys) != 1:
            raise ValueError("Specify --issue from verified eligible mappings: " + ", ".join(keys)
                             if keys else "No explicit tag mapping to an eligible Jira subtask. No tests run.")
        issue_key = keys[0]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", issue_key):
        raise ValueError("Invalid issue key.")
    selected = [r for r in rows if issue_key in r.get("jira_keys", [])]
    if not selected or any(r not in verified or r.get("jira_keys") != [issue_key] for r in selected):
        raise ValueError("Issue lacks an unambiguous, verified eligible mapping. No tests run.")
    work_status = discovery.get("work_status")
    if " ".join(str(work_status or "").casefold().split()) not in {"to be automate", "to be automated"}:
        raise ValueError("This workflow processes only To Be Automate/Automated work statuses, never completed automation.")
    if not work_status or any(r.get("jira_issue", {}).get("status", "").strip().casefold()
                              != work_status.strip().casefold() for r in selected):
        raise ValueError("Jira status evidence does not match the configured work status.")
    if any(r.get("kind") not in {"Scenario", "Example"} for r in selected):
        raise ValueError("Scenario Outline execution needs example-row mapping; not supported here yet.")
    identities = [(r["feature"], r["scenario"]) for r in selected]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate feature/scenario names prevent reliable XML result attribution.")
    tags = set.intersection(*(set(r.get("tags", [])) for r in selected))
    tag = "@" + issue_key
    if tag not in tags:
        raise ValueError("Expected an explicit @ISSUE-KEY tag; no inferred tag selection.")
    return issue_key, selected, tag


def assess_execution(execution, runner, selected):
    """Only a complete, fresh, exact runner/scenario match can be marked passed."""
    reasons = []
    if execution.get("timed_out") is not False:
        reasons.append("Execution timed out or timeout outcome is unknown.")
    if execution.get("exit_code") != 0:
        reasons.append("Gradle did not return exit_code 0.")
    if execution.get("report_errors"):
        reasons.append("One or more fresh reports could not be parsed.")
    reports = execution.get("reports", [])
    if execution.get("report_status") != "fresh_reports_found" or not reports:
        reasons.append("No fresh report associated with this execution.")
    # This workflow uses the focused Gradle JUnit directory, not overlapping formats.
    if len(reports) != 1 or (reports and reports[0].get("format") != "junit-xml"):
        reasons.append("Expected exactly one fresh Gradle JUnit runner report.")
    actual = []
    tests = []
    if len(reports) == 1:
        report = reports[0]
        tests = report.get("tests", [])
        if report.get("details_truncated") or report.get("total") != len(tests):
            reasons.append("Test details are incomplete.")
        if report.get("configuration_failure_count", 0):
            reasons.append("Test configuration failed.")
        for test in tests:
            if test.get("class") != runner:
                reasons.append("Unexpected test class in fresh report.")
            match = re.fullmatch(r"runScenario(?:\[\d+\])?\((.*)\)", test.get("name", ""))
            try:
                parameters = json.loads("[" + match.group(1) + "]") if match else None
            except (ValueError, TypeError):
                parameters = None
            if not isinstance(parameters, list) or len(parameters) != 2 or not all(isinstance(p, str) for p in parameters):
                reasons.append("Unrecognized Cucumber scenario result name.")
            else:
                actual.append((parameters[1], parameters[0]))
    expected = [(r["feature"], r["scenario"]) for r in selected]
    if not expected or Counter(actual) != Counter(expected):
        reasons.append("Executed scenarios do not exactly match the selected source mappings.")
    failed = any(t.get("status") == "failed" for t in tests)
    if any(t.get("status") != "passed" for t in tests):
        reasons.append("Not every scenario passed.")
    return {"status": "passed" if not reasons else "failed" if failed else "incomplete",
            "reasons": list(dict.fromkeys(reasons)),
            "expected_scenarios": len(expected), "reported_tests": len(tests),
            "note": "A pass reflects existing assertions, not proof of requirement coverage. "
                    "Attribution combines Jira eligibility, source tags, command selection and XML names; "
                    "JUnit XML does not itself contain the Jira tag."}


def source_hashes(root, rows):
    result = {}
    for name in sorted({r["file"] for r in rows}):
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Selected source is missing or outside the project.")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def save_evidence(path, evidence):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def main(argv=None, *, return_evidence=False):
    from dotenv import load_dotenv
    from agent.tools.project_tools import ProjectTools
    from agent.tools.feature_mapping import discover_feature_mappings
    from integrations.jira.feature_jira_mapping import discover_jira_mappings

    app_root = Path(__file__).resolve().parents[2]
    load_dotenv(app_root / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.getenv("AI_PROJECT_ROOT"))
    parser.add_argument("--project", default=os.getenv("JIRA_PROJECT_KEY"))
    parser.add_argument("--issue", help="Optional when exactly one verified eligible mapping exists.")
    parser.add_argument("--runner", default=os.getenv("QA_TEST_RUNNER"))
    parser.add_argument("--reports", default=os.getenv("QA_REPORT_FOLDER"))
    parser.add_argument("--env", default=os.getenv("QA_TEST_ENV", "dev"))
    parser.add_argument("--browser", default=os.getenv("QA_TEST_BROWSER", "chromium"))
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--execute", action="store_true", help="Execute once; otherwise save the selected plan only.")
    args = parser.parse_args(argv)
    if not all((args.root, args.project, args.runner, args.reports)):
        parser.error("Provide root, project, runner and relative report folder through options or environment.")
    if not re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+", args.runner):
        parser.error("--runner must be a fully qualified Java class.")
    if not 1 <= args.timeout <= 300:
        parser.error("--timeout must be 1..300 seconds (ProjectTools limit).")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", v) for v in (args.env, args.browser)):
        parser.error("Environment/browser must be simple names.")
    tools = ProjectTools(args.root)
    root = tools.root
    folder = (root / args.reports).resolve()
    if Path(args.reports).is_absolute() or not folder.is_relative_to(root) or ".." in Path(args.reports).parts:
        parser.error("--reports must be a relative folder inside the automation project.")
    if not callable(getattr(tools, "run_tests_and_parse", None)):
        parser.error("ProjectTools.run_tests_and_parse is required.")
    if not (root / "gradlew.bat").is_file() and not (root / "gradlew").is_file():
        parser.error("Gradle wrapper not found in selected project.")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output_dir = app_root / "outputs" / "qa_workflow"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / (run_id + ".json")
    evidence = {"run_id": run_id, "created_at": utc_now(), "project_root": str(root),
                "status": "discovering", "jira_changed": False, "source_changed_by_workflow": False}
    lock = root / ".qa-workflow.lock"
    acquired = False
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps({"run_id": run_id, "pid": os.getpid()}))
        acquired = True
        discovery = asyncio.run(discover_jira_mappings(str(root), args.project))
        evidence["discovery"] = discovery
        evidence["eligibility_checked_at"] = utc_now()
        key, selected, tag = select_mapping(discovery, args.issue)
        # Check the local inventory again immediately before running; never use title guesses.
        current = discover_feature_mappings(root, limit=5000)
        current_rows = [r for r in current["scenarios"] if key in r.get("jira_keys", [])]
        fields = ("file", "line", "feature", "scenario", "kind", "tags", "jira_keys")
        project_rows = lambda rows: [{f: r.get(f) for f in fields} for r in rows]
        if current["errors"] or current["details_truncated"] or project_rows(current_rows) != project_rows(selected):
            raise ValueError("Source mappings changed during discovery; execution stopped.")
        hashes = source_hashes(root, selected)
        command = ["gradlew", "test", f"-Dtest.runner={args.runner}",
                   f"-Dcucumber.filter.tags={tag}", f"-Denv={args.env}", f"-Dbrowser={args.browser}",
                   "--rerun-tasks", "--console=plain", "-x", "openExtentReport"]
        evidence.update(status="planned", issue_key=key, selected_scenarios=selected,
                        source_sha256=hashes, command=command, report_folder=args.reports)
        save_evidence(output, evidence)
        print(json.dumps({"issue": key, "runner": args.runner, "tag": tag,
                          "scenario_definitions": len(selected), "command": command}, indent=2))
        if args.execute:
            evidence["status"] = "running"
            save_evidence(output, evidence)
            execution = tools.run_tests_and_parse(command, args.reports, timeout=args.timeout)
            evidence["execution"] = execution
            assessment = assess_execution(execution, args.runner, selected)
            if hashes != source_hashes(root, selected):
                assessment = {**assessment, "status": "incomplete",
                              "reasons": [*assessment["reasons"], "Selected source changed during execution."]}
            evidence.update(status=assessment["status"], assessment=assessment)
            print(json.dumps(assessment, indent=2))
            print("exit_code:", execution.get("exit_code"), "timed_out:", execution.get("timed_out"))
            if assessment["status"] != "passed":
                print("Command stdout (tail):", execution.get("stdout", "")[-4000:])
                print("Command stderr (tail):", execution.get("stderr", "")[-4000:])
        else:
            print("Plan only. Use --execute to run the selected existing automation.")
        return evidence if return_evidence else (0 if evidence["status"] in {"planned", "passed"} else 1)
    except FileExistsError:
        evidence.update(status="blocked", error="Another workflow lock exists. Check for an active run before removing .qa-workflow.lock.")
        print(evidence["error"])
        return evidence if return_evidence else 1
    except Exception as error:
        # OAuth/HTTP exception text can contain callback URLs; do not dump it.
        evidence.update(status="incomplete", error_type=type(error).__name__)
        if isinstance(error, ValueError):
            evidence["error"] = str(error)
        print("Workflow incomplete:", evidence.get("error", evidence["error_type"]))
        return evidence if return_evidence else 1
    finally:
        evidence["finished_at"] = utc_now()
        save_evidence(output, evidence)
        if acquired:
            lock.unlink(missing_ok=True)
        print("Evidence saved:", output)
        print("Jira unchanged. Avoid other processes writing to the same report folder during execution.")


if __name__ == "__main__":
    sys.exit(main())
