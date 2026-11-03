"""Read-only action summaries from scoped, durable receipts."""
import json
import re
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

EXECUTION_ACTIONS = frozenset({"run_command", "run_python_file", "run_tests_and_parse", "rerun_test_repair"})
FILE_ACTIONS = frozenset({"create_file", "replace_text", "apply_test_repair"})
RESULT_ACTIONS = EXECUTION_ACTIONS | FILE_ACTIONS | {"inspect_browser_page", "create_project"}
MAX_FIELDS = 20
MAX_DIFF = 20000
FRESH_PREFIX = "associated with this command by changed content/metadata"
MAX_REPORTS = 20


def execution_summary(payload):
    """Keep command status, report claims and unverified limits separate."""
    result = payload["result"]
    uncertain = payload["receipt_status"] != "completed"
    code = result.get("exit_code")
    if result.get("timed_out") is True:
        command_status = "Timed out"
    elif uncertain:
        command_status = "Uncertain"
    elif type(code) is not int:
        command_status = "Outcome unavailable"
    elif code == 0:
        command_status = "Succeeded (exit 0)"
    else:
        command_status = f"Failed (exit {code})"
    command = result.get("command", payload["arguments"].get("command"))
    if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
        command = ["python", payload["arguments"]["relative_path"]] if payload["action"] == "run_python_file" else []
    reports = result.get("reports", []) if payload["action"] in {"run_tests_and_parse", "rerun_test_repair"} else []
    if not isinstance(reports, list):
        reports = []
    rows, evidence = [], []
    limits = ["A command exit code does not prove test correctness or requirement coverage."]
    if uncertain:
        limits.append("The receipt is not completed. Effects may be uncertain; do not repeat the action to repair its display.")
    for report in reports[:MAX_REPORTS]:
        if not isinstance(report, dict):
            continue
        name = report.get("file", "Unnamed report")
        counts = {key: report.get(key) for key in ("passed", "failed", "skipped", "incomplete", "total")}
        valid = all(type(value) is int and value >= 0 for value in counts.values())
        valid = valid and sum(counts[key] for key in ("passed", "failed", "skipped", "incomplete")) == counts["total"]
        fresh = (result.get("report_status") == "fresh_reports_found"
                 and str(report.get("freshness", "")).startswith(FRESH_PREFIX)
                 and report.get("format") in {"junit-xml", "testng-xml", "cucumber-json"})
        if not fresh or not valid:
            status = "Not verified"
        elif report.get("configuration_failure_count", 0) or counts["failed"]:
            status = "Reported failures"
        elif counts["incomplete"]:
            status = "Incomplete report"
        elif counts["total"] == 0:
            status = "No test cases reported"
        elif counts["skipped"]:
            status = "Reported with skips"
        elif report.get("overall_status") == "passed" and counts["passed"] == counts["total"]:
            status = "Reported passed"
        else:
            status = "Not verified"
        rows.append({"file": str(name), "status": status, "counts": counts if valid else None, "fresh": fresh})
        evidence.append(("Report", str(name)))
        if report.get("details_truncated"):
            limits.append("Some per-case report details were truncated; counts and complete case details are different evidence.")
    if not rows:
        tests = "Not verified — no fresh native test report is attached."
    elif result.get("report_errors") or any(row["status"] == "Not verified" for row in rows):
        tests = "Not fully verified — inspect each report below."
    else:
        tests = "Native report results below; each report is shown separately."
    if len(reports) > 1:
        limits.append("Reports may overlap. Their counts are not added together.")
    if len(reports) > MAX_REPORTS:
        limits.append(f"Showing the first {MAX_REPORTS} reports; the raw receipt retains the remaining reports.")
    if rows:
        limits.append("Report freshness is a file/time-window association, not proof of an exclusive run ID.")
    if result.get("report_errors"):
        limits.append("Some reports could not be parsed. Available counts do not establish complete test results.")
        for item in result["report_errors"][:MAX_REPORTS]:
            if isinstance(item, dict) and item.get("file"):
                evidence.append(("Unreadable report", str(item["file"])))
    for field, label in (("unchanged_reports_ignored", "Unchanged report excluded"),
                         ("outside_execution_window_ignored", "Report outside run window excluded")):
        paths = result.get(field, [])
        if isinstance(paths, list) and paths:
            limits.append(label + "; it is not used as evidence of this run's result.")
            evidence.extend((label, str(path)) for path in paths[:MAX_REPORTS])
    if result.get("report_folder"):
        evidence.insert(0, ("Report folder", str(result["report_folder"])))
    if result.get("output_truncated"):
        limits.append("Captured output was truncated; the saved receipt does not contain the full process log.")
    if code != 0 or result.get("timed_out") is True:
        limits.append("Any reported passing tests do not make an unsuccessful command a successful execution.")
    return {"command_status": command_status, "command": command, "tests": tests,
            "reports": rows, "evidence": evidence, "limits": list(dict.fromkeys(limits))}



def _relative_path(value):
    """Validate stored relative paths without opening or resolving any file."""
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        return None
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or PureWindowsPath(value).drive or ".." in path.parts or not path.parts:
        return None
    return path.as_posix()


def file_action_summary(payload):
    action, args, result = payload["action"], payload["arguments"], payload["result"]
    if action not in FILE_ACTIONS:
        raise ValueError("Not a file action.")
    plan = args.get("plan", {}) if action == "apply_test_repair" else {}
    if not isinstance(plan, dict):
        plan = {}
    replacement = plan.get("replacement", {})
    if not isinstance(replacement, dict):
        replacement = {}
    expected = _relative_path(replacement.get("file") if action == "apply_test_repair" else args.get("relative_path"))
    actual = _relative_path(result.get("file"))
    matched = bool(expected and actual == expected)
    limits = ["This is the saved action result, not a check that the file still exists or has the same content.",
              "A file change does not establish test correctness, requirement coverage or a completed task."]
    evidence = [("Approved file", expected)] if expected else []
    repair_id = result.get("repair_plan_id")
    if action == "apply_test_repair":
        after = result.get("source_after", {})
        valid_after = (isinstance(after, dict) and isinstance(after.get("sha256"), str)
                       and re.fullmatch(r"[0-9a-f]{64}", after["sha256"]) is not None
                       and after["sha256"] == replacement.get("after_sha256"))
        matched = matched and bool(plan.get("id")) and repair_id == plan["id"] and valid_after
        limits.append("This receipt records the source edit only. Review and separately approve a focused rerun; the diagnosis is not confirmed by this edit.")
        if isinstance(repair_id, str):
            evidence.append(("Repair plan", repair_id))
        if valid_after:
            evidence.append(("Recorded source SHA256", after["sha256"]))
    severity, status = "warning", "Outcome unavailable"
    uncertain = payload["receipt_status"] != "completed"
    if uncertain:
        status = "Uncertain"
        limits.append("The receipt is not completed. Do not repeat the action to repair its display; inspect its actual effects first.")
    elif matched:
        if action == "create_file" and result.get("created") is True:
            severity, status = "success", "File created"
        elif action != "create_file" and result.get("changed") is True:
            severity, status = "success", "Repair source updated" if action == "apply_test_repair" else "File updated"
        elif action != "create_file" and result.get("changed") is False:
            severity, status = "info", "No file change"
    if not matched:
        limits.append("The saved result does not match the approved file/repair details; no successful file outcome is claimed.")
    size = result.get("size_bytes")
    if type(size) is not int or size < 0:
        size = None
    diff = result.get("diff", "")
    if not isinstance(diff, str):
        diff = ""
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF]
        limits.append("The change preview is truncated; the raw receipt retains the stored diff.")
    return {"status": status, "severity": severity, "file": expected, "size_bytes": size,
            "diff": diff, "evidence": evidence, "limits": limits,
            "download_hint": action == "create_file" and severity == "success"}


def inspection_summary(payload):
    args, result = payload["arguments"], payload["result"]
    evidence, limits, rows = [], [], []
    requested = args.get("url")
    folder = _relative_path(args.get("evidence_folder", "test-output/agent-web"))
    inspection = _relative_path(result.get("inspection_file"))
    matched = bool(folder and inspection and PurePosixPath(inspection).is_relative_to(PurePosixPath(folder))
                   and result.get("requested_url") == requested)
    try:
        before, after = urlsplit(requested), urlsplit(result.get("url", ""))
        matched = matched and before.scheme == after.scheme == "https" and before.netloc == after.netloc
    except (TypeError, ValueError):
        matched = False
    fields = result.get("fields")
    valid_fields = isinstance(fields, list)
    if valid_fields:
        for item in fields[:MAX_FIELDS]:
            if not isinstance(item, dict):
                limits.append("Some saved field observations are malformed and are not displayed.")
                continue
            label = item.get("label") or item.get("id") or item.get("name") or "Unnamed field"
            rows.append({"Field": str(label)[:160], "Type": str(item.get("type", ""))[:40],
                         "Enabled": "Yes" if item.get("disabled") is False else "No" if item.get("disabled") is True else "Unknown",
                         "Read only": "Yes" if item.get("read_only") is True else "No" if item.get("read_only") is False else "Unknown"})
        if len(fields) > MAX_FIELDS or result.get("fields_may_be_truncated"):
            limits.append("Only a bounded field sample is displayed; this is not an inventory of every page element.")
    else:
        limits.append("Saved field observations are unavailable.")
    uncertain = payload["receipt_status"] != "completed"
    complete = not uncertain and matched and valid_fields and result.get("status") == "inspected"
    status = "Page inspected" if complete else "Uncertain" if uncertain else "Inspection not verified"
    if uncertain:
        limits.append("The receipt is not completed. Do not run the inspection again merely to repair its display.")
    if not matched:
        limits.append("Saved URL/evidence metadata does not match the approved inspection scope.")
    if inspection and folder and PurePosixPath(inspection).is_relative_to(PurePosixPath(folder)):
        evidence.append(("Inspection JSON", inspection))
    screenshot = _relative_path(result.get("screenshot"))
    if screenshot and folder and PurePosixPath(screenshot).is_relative_to(PurePosixPath(folder)):
        evidence.append(("Screenshot", screenshot))
    if isinstance(result.get("inspection_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", result["inspection_sha256"]):
        evidence.append(("Recorded inspection SHA256", result["inspection_sha256"]))
    limits.extend(["These are saved page observations, not a fresh website check or an application-test result.",
                   "Enabled/read-only flags are observed attributes; successful editing, submission and requirement coverage are not established.",
                   "Evidence paths are recorded locations; their current existence/content has not been rechecked."])
    return {"status": status, "severity": "success" if complete else "warning", "url": requested,
            "captured_at": result.get("captured_at"), "fields": rows, "evidence": evidence,
            "limits": list(dict.fromkeys(limits))}


def creation_summary(payload):
    import hashlib
    from agent.tools.project_creation import canonical
    plan = payload["arguments"].get("plan", {})
    result = payload["result"]
    expected = [{key: item[key] for key in ("relative_path", "size_bytes", "sha256")} for item in plan.get("files", [])]
    body = {key: value for key, value in plan.items() if key != "id"}
    matched = (plan.get("id") == hashlib.sha256(canonical(body).encode()).hexdigest()
               and result.get("plan_id") == plan.get("id") and result.get("project_root") == plan.get("destination")
               and result.get("files") == expected and 1 <= len(expected) <= 20
               and result.get("commands_executed") is False and result.get("tests_executed") is False)
    uncertain = payload["receipt_status"] != "completed"
    complete = not uncertain and matched and result.get("created") is True
    limits = ["This receipt records creation and byte verification, not installation, test execution or production readiness.",
              "These are recorded paths/hashes; their current on-disk contents have not been reread for this view."]
    if uncertain:
        limits.append("Creation may be partial. Inspect the receipt/folder before any new action; do not automatically retry or delete it.")
    if not matched:
        limits.append("Saved creation details do not match the approved plan; successful creation is not claimed.")
    return {"status": "Project files created" if complete else "Uncertain" if uncertain else "Creation not verified",
            "severity": "success" if complete else "warning", "destination": plan.get("destination"),
            "files": [{"File": item["relative_path"], "Bytes": item["size_bytes"]} for item in expected],
            "limits": limits, "evidence": [("Creation plan", str(plan.get("id", "Unavailable")))]}


def _render_saved_action(payload):
    """Present file/inspection receipts; never invoke tools or read artifact files."""
    import streamlit as st
    action = payload["action"]
    summary = (creation_summary(payload) if action == "create_project" else
               file_action_summary(payload) if action in FILE_ACTIONS else inspection_summary(payload))
    st.markdown("**Project result**" if action == "create_project" else "**File result**" if action in FILE_ACTIONS else "**Browser inspection**")
    getattr(st, summary["severity"])(summary["status"])
    if action == "create_project":
        st.text("Reviewed destination: " + str(summary["destination"]))
        st.dataframe(summary["files"], hide_index=True, width="stretch")
    elif action in FILE_ACTIONS:
        if summary["file"]:
            st.text("File: " + summary["file"])
        if summary["size_bytes"] is not None:
            st.caption("Recorded size: " + str(summary["size_bytes"]) + " bytes")
        if summary["diff"]:
            with st.expander("Applied change", expanded=False):
                st.code(summary["diff"], language="diff", wrap_lines=True)
        if summary["download_hint"]:
            st.caption("Download: Conversation → Files created by approved actions → Prepare download.")
    else:
        if summary["url"]:
            st.text("Approved URL: " + str(summary["url"]))
        if summary["captured_at"]:
            st.text("Captured: " + str(summary["captured_at"]))
        if summary["fields"]:
            st.dataframe(summary["fields"], hide_index=True, width="stretch")
        else:
            st.caption("No usable field observations are displayed.")
    st.markdown("**Evidence**")
    st.text("Project: " + payload["project_root"])
    st.caption("Receipt: " + payload["receipt_id"])
    for label, value in summary["evidence"]:
        st.text(label + ": " + value)
    st.markdown("**Limitations**")
    for limit in summary["limits"]:
        st.text("• " + limit)
    with st.expander("Raw receipt and logs", expanded=False):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json", wrap_lines=True)
    return True


def render_execution_result(backend, session, *, turn=None, token=None):
    """Render owned stored action results; ordinary chat remains unchanged."""
    import streamlit as st
    if not hasattr(backend, "execution_result"):
        return False
    if token is None:
        match = re.fullmatch(r"Approved exact local action ([0-9a-f]{32})", (turn or {}).get("question", ""))
        if not match:
            return False
        token = match.group(1)
    try:
        payload = backend.execution_result(session, token)
        if payload is None:
            return False
        if payload["action"] in FILE_ACTIONS or payload["action"] in {"inspect_browser_page", "create_project"}:
            return _render_saved_action(payload)
        if payload["action"] not in EXECUTION_ACTIONS:
            return False
        summary = execution_summary(payload)
    except (ValueError, KeyError, TypeError, OSError):
        return False
    st.markdown("**Execution result**")
    if summary["command_status"].startswith("Failed"):
        st.error("Command: " + summary["command_status"])
    elif summary["command_status"] in {"Timed out", "Uncertain", "Outcome unavailable"}:
        st.warning("Command: " + summary["command_status"])
    else:
        st.success("Command: " + summary["command_status"])
    if summary["command"]:
        st.code(json.dumps(summary["command"], ensure_ascii=False), language="text", wrap_lines=True)
    st.write("**Tests:** " + summary["tests"])
    for report in summary["reports"]:
        with st.container(border=True):
            st.text(report["file"])
            st.write(report["status"])
            counts = report["counts"]
            if counts is not None:
                st.caption(" · ".join(key.capitalize() + ": " + str(value) for key, value in counts.items()))
    st.markdown("**Evidence**")
    st.text("Project: " + payload["project_root"])
    st.caption("Receipt: " + payload["receipt_id"])
    for label, path in summary["evidence"]:
        st.text(label + ": " + path)
    if not summary["evidence"]:
        st.caption("Only the saved process receipt/output is available; no native report is attached.")
    st.markdown("**Limitations**")
    for limit in summary["limits"]:
        st.write("• " + limit)
    review = payload["result"].get("post_run_review")
    if isinstance(review, dict) and review.get("version") == 1:
        with st.expander("Post-run review", expanded=bool(review.get("findings"))):
            st.caption("Local static review · advisory findings; execution results above are unchanged.")
            if review.get("reviewed_at"):
                st.text("Reviewed: " + str(review["reviewed_at"]))
            for finding in review.get("findings", [])[:40]:
                st.warning(finding["title"])
                evidence = finding["evidence"]
                line = evidence.get("line", evidence.get("captured_line"))
                st.text("Evidence: " + str(evidence.get("file", evidence.get("report_file") or evidence.get("field", "saved result")))
                        + (":" + str(line) if line else ""))
                if evidence.get("sha256"):
                    st.caption("Source SHA256: " + evidence["sha256"])
                st.write(finding["next_check"])
            if review.get("status") == "unavailable":
                st.warning("Post-run review is unavailable; the execution outcome above is retained.")
            elif not review.get("findings"):
                st.write("No warning was detected by these bounded checks. Test correctness is not certified.")
            for source in review.get("source_checks", [])[:20]:
                st.text(str(source.get("case", "Test")) + ": " + source["status"])
            for limit in review.get("limits", []):
                st.caption(limit)
    with st.expander("Raw receipt and logs", expanded=False):
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json", wrap_lines=True)
    return True
