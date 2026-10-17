"""Parse existing test reports. Reading a report does not run tests."""
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

STATUSES = ("passed", "failed", "skipped", "incomplete")


def parse_test_results(project_root, relative_path, limit=100):
    """Return counts from one existing report, not inferred from a build exit code."""
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500.")
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("relative_path must be non-empty.")
    requested = Path(relative_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("Use a relative path without '..'.")
    root = Path(project_root).resolve()
    path = (root / requested).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Report must be inside the project root.")
    if any(part in {".git", ".venv", "venv", "node_modules"} for part in requested.parts):
        raise ValueError("Excluded report directory.")
    if not path.is_file():
        raise FileNotFoundError(f"Report not found: {relative_path}")
    if path.suffix.lower() not in {".xml", ".json"}:
        raise ValueError("Supported reports: TestNG XML, JUnit XML, Cucumber JSON.")
    before = path.stat()
    if before.st_size > 20_000_000:
        raise ValueError("Report exceeds 20 MB.")
    text = path.read_text(encoding="utf-8-sig")
    records = []
    configuration_failures = []
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, list) or not all(isinstance(f, dict) and isinstance(f.get("elements"), list) for f in data):
            raise ValueError("Expected classic Cucumber JSON: a feature list with elements.")
        report_format = "cucumber-json"
        for feature in data:
            for scenario in feature["elements"]:
                if scenario.get("type") == "background":
                    continue
                if scenario.get("type") not in {None, "scenario", "scenario_outline"}:
                    continue
                outcomes, errors = [], []
                for group in ("before", "steps", "after"):
                    for item in scenario.get(group, []):
                        result = item.get("result", {})
                        outcomes.append(str(result.get("status", "unknown")).lower())
                        if result.get("error_message"):
                            errors.append(str(result["error_message"])[:2000])
                if "failed" in outcomes:
                    status = "failed"
                elif not scenario.get("steps") or not outcomes or any(s not in {"passed", "skipped"} for s in outcomes):
                    status = "incomplete"
                elif "skipped" in outcomes:
                    status = "skipped"
                else:
                    status = "passed"
                records.append({"name": scenario.get("name", "Unnamed scenario"),
                                "status": status, "feature": feature.get("uri", feature.get("name", "")),
                                "line": scenario.get("line"),
                                "tags": [t.get("name") for t in scenario.get("tags", []) if isinstance(t, dict)],
                                "errors": errors})
    else:
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise ValueError("Report XML containing DTD/entity declarations is unsupported.")
        xml = ET.fromstring(text)
        # Support namespaces without changing the report file.
        for element in xml.iter():
            element.tag = element.tag.rsplit("}", 1)[-1]
        if xml.tag == "testng-results":
            report_format = "testng-xml"
            for cls in xml.iter("class"):
                for method in cls.findall("test-method"):
                    if method.get("is-config", "false").lower() == "true":
                        if method.get("status", "").upper() == "FAIL":
                            configuration_failures.append({"name": method.get("name", "Configuration method"), "class": cls.get("name", "")})
                        continue
                    raw = method.get("status", "").upper()
                    status = {"PASS": "passed", "FAIL": "failed", "SKIP": "skipped"}.get(raw, "incomplete")
                    errors = [e.text.strip()[:2000] for e in method.findall(".//exception/message") if e.text and e.text.strip()]
                    records.append({"name": method.get("name", "Unnamed method"), "class": cls.get("name", ""),
                                    "status": status, "errors": errors})
        elif xml.tag in {"testsuite", "testsuites"}:
            report_format = "junit-xml"
            for case in xml.iter("testcase"):
                issues = case.findall("failure") + case.findall("error")
                status = "failed" if issues else "skipped" if case.find("skipped") is not None else "passed"
                records.append({"name": case.get("name", "Unnamed test"), "class": case.get("classname", ""),
                                "status": status,
                                "errors": [(i.get("message", "") + "\n" + (i.text or "")).strip()[:2000] for i in issues]})
            # Suite-level failures with no testcase must not look like an empty successful run.
            for suite in xml.iter("testsuite"):
                for issue in list(suite):
                    if issue.tag in {"error", "failure"}:
                        records.append({"name": suite.get("name", "Suite error"), "status": "failed",
                                        "errors": [(issue.get("message", "") + "\n" + (issue.text or "")).strip()[:2000]]})
        else:
            raise ValueError("Not a TestNG or JUnit results document. Suite configuration XML is not a test report.")
    after = path.stat()
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise ValueError("Report changed during reading; retry after the test run finishes.")
    counts = {status: sum(r["status"] == status for r in records) for status in STATUSES}
    overall = ("failed" if configuration_failures else "no_test_results" if not records else "failed" if counts["failed"]
               else "incomplete" if counts["incomplete"] else "skipped" if counts["skipped"] else "passed")
    return {"file": path.relative_to(root).as_posix(), "format": report_format,
            "modified_at": datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat(),
            "freshness": "unverified: this report has not been linked to a specific execution",
            "overall_status": overall, "total": len(records), **counts,
            "configuration_failure_count": len(configuration_failures),
            "configuration_failures": configuration_failures[:limit],
            "tests": records[:limit], "details_truncated": len(records) > limit,
            "note": "Counts cover this report only. Multiple files may overlap; do not add them blindly."}


def run_tests_and_parse(tools, command, relative_report_folder, timeout=300):
    """Run a requested command and associate changed XML reports with its time window.

    File metadata provides evidence of freshness, not an embedded run identifier.
    The caller should avoid simultaneous runs writing into the same report folder.
    """
    import time
    import hashlib
    if not isinstance(relative_report_folder, str) or not relative_report_folder.strip():
        raise ValueError("relative_report_folder must be a non-empty string.")
    requested = Path(relative_report_folder)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("Use a relative report folder without '..'.")
    folder = (tools.root / requested).resolve()
    if not folder.is_relative_to(tools.root):
        raise ValueError("Report folder must be inside the project root.")
    if any(part in {".git", ".venv", "venv", "node_modules"} for part in requested.parts):
        raise ValueError("Excluded report directory.")

    def snapshot():
        if not folder.exists():
            return {}
        if not folder.is_dir():
            raise ValueError("Report folder is not a directory.")
        files = sorted(folder.rglob("TEST-*.xml"))
        files += sorted(folder.rglob("testng-results.xml"))
        if len(files) > 200:
            raise ValueError("Too many reports; choose a focused report folder (at most 200).")
        result = {}
        for path in files:
            resolved = path.resolve()
            if not resolved.is_relative_to(folder) or path.is_symlink():
                continue
            stat = path.stat()
            if stat.st_size > 20_000_000:
                raise ValueError(f"Report exceeds 20 MB: {path.name}")
            result[path.relative_to(tools.root).as_posix()] = (
                stat.st_mtime_ns, stat.st_size, hashlib.sha256(path.read_bytes()).hexdigest()
            )
        return result

    before = snapshot()
    started_ns = time.time_ns()
    execution = tools.run_command(command, timeout=timeout)
    finished_ns = time.time_ns()
    after = snapshot()
    fresh, unchanged, outside_window = [], [], []
    for path, signature in after.items():
        if signature == before.get(path):
            unchanged.append(path)
        elif not started_ns - 2_000_000_000 <= signature[0] <= finished_ns + 2_000_000_000:
            outside_window.append(path)
        else:
            fresh.append(path)
    reports, errors = [], []
    for path in fresh:
        try:
            report = parse_test_results(tools.root, path)
            report["freshness"] = "associated with this command by changed content/metadata and execution time window"
            reports.append(report)
        except (ValueError, OSError, ET.ParseError) as error:
            errors.append({"file": path, "error": str(error)})
    return {
        **execution,
        "started_at": datetime.fromtimestamp(started_ns / 1e9, timezone.utc).isoformat(),
        "finished_at": datetime.fromtimestamp(finished_ns / 1e9, timezone.utc).isoformat(),
        "report_folder": requested.as_posix(),
        "reports": reports,
        "report_errors": errors,
        "unchanged_reports_ignored": unchanged,
        "outside_execution_window_ignored": outside_window,
        "report_status": "fresh_reports_found" if reports else "no_fresh_results",
        "note": "Reports may overlap; counts are not combined. Freshness uses file evidence, not a run ID. Avoid concurrent writers. A timeout or nonzero exit means execution was unsuccessful even if a report contains passed tests.",
    }
