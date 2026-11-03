"""Bounded, local post-run warnings; never execute, repair or certify test quality."""
import ast
import json
from urllib.parse import unquote, urlsplit
from datetime import datetime, timezone
from pathlib import Path
import re

FRESH_PREFIX = "associated with this command by changed content/metadata"
MAX_REPORTS = 20
MAX_CASES = 20
MAX_SOURCE_FILES = 10
MAX_SOURCE_BYTES = 256_000
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
JAVA_TOKEN = re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
ASSERT_CALL = re.compile(r"\b(?:assert\w*|verify|expect)\s*\(|\bassert\s+")


def _masked_java(text):
    return JAVA_TOKEN.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text)


def _method(text, name, class_name, suffix, module_level=False):
    """Return a unique bounded test body, not a whole-file assertion guess."""
    if suffix == ".py":
        tree = ast.parse(text)
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name]
        pool = classes[0].body if len(classes) == 1 else tree.body if not classes and module_level else []
        matches = [node for node in pool if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
        if len(matches) != 1:
            return None
        node = matches[0]
        lines = text.splitlines()
        body = "\n".join(lines[node.lineno - 1:node.end_lineno])
        nodes = []
        pending = list(node.body)
        while pending:
            current = pending.pop()
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            nodes.append(current)
            pending.extend(ast.iter_child_nodes(current))
        checks = [n for n in nodes if isinstance(n, ast.Assert) or
                  (isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute)) and
                   re.fullmatch(r"assert\w*|expect|verify", getattr(n.func, "id", getattr(n.func, "attr", ""))))]
        weak = [n for n in checks if
                (isinstance(n, ast.Assert) and isinstance(n.test, ast.Constant) and n.test.value is True) or
                (isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) == "assertTrue"
                 and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value is True)]
        return node.lineno, body, len(checks), bool(weak), False
    masked = _masked_java(text)
    if len(re.findall(r"\bclass\s+" + re.escape(class_name) + r"\b", masked)) != 1:
        return None
    pattern = re.compile(r"\bvoid\s+" + re.escape(name) + r"\s*\([^;{}]*\)\s*(?:throws\s+[\w.,\s]+)?\{")
    matches = list(pattern.finditer(masked))
    if len(matches) != 1:
        return None
    start = matches[0].start()
    opening = matches[0].end() - 1
    depth = 1
    end = opening + 1
    while end < len(masked) and depth:
        depth += (masked[end] == "{") - (masked[end] == "}")
        end += 1
    if depth:
        return None
    body = masked[opening + 1:end - 1]
    raw = text[opening + 1:end - 1]
    commented = any(m[0].startswith(("//", "/*")) and ASSERT_CALL.search(m[0]) for m in JAVA_TOKEN.finditer(raw))
    weak = bool(re.search(r"\bassertTrue\s*\(\s*true\s*\)|\bassert\s+true\s*;", body))
    return text.count("\n", 0, start) + 1, body, len(ASSERT_CALL.findall(body)), weak, commented


def _candidates(case):
    cls = case.get("class", "")
    name = re.split(r"[\[(]", str(case.get("name", "")), maxsplit=1)[0].strip()
    if not isinstance(cls, str) or len(cls) > 240 or not IDENTIFIER.fullmatch(name):
        return [], name, ""
    parts = cls.split(".")
    if not parts or not all(IDENTIFIER.fullmatch(part) for part in parts):
        return [], name, ""
    java = "/".join(parts) + ".java"
    candidates = ["src/test/java/" + java, "src/main/java/" + java]
    # JUnit producers use either module.Class or module for Python cases.
    candidates += ["/".join(parts[:-1]) + ".py"] if len(parts) > 1 else []
    candidates += ["/".join(parts) + ".py"]
    return candidates, name, parts[-1]



def _failure_locations(case, root, load_source):
    """Cite reported locations only; never infer a cause or run another action."""
    if case.get("status") != "failed" or not isinstance(case.get("errors"), list):
        return []
    errors = "\n".join(item[:8000] for item in case["errors"][:4] if isinstance(item, str))[:8000]
    locations, seen = [], set()
    name, scenario = case.get("name", ""), None
    if isinstance(name, str) and len(name) <= 500:
        match = re.match(r'runScenario(?:\[\d+\])?\(("(?:\\.|[^"\\])*")\s*,', name)
        if match:
            try: scenario = json.loads(match[1])
            except ValueError: pass
    for match in list(re.finditer(r'\((file:///[^\r\n)]+\.feature):([1-9]\d{0,6})\)', errors))[:3]:
        if scenario is None: break
        try:
            uri = urlsplit(match[1])
            if uri.netloc or uri.query or uri.fragment: continue
            raw_path = unquote(uri.path)
            if re.match(r'^/[A-Za-z]:/', raw_path): raw_path = raw_path[1:]
            candidate = Path(raw_path)
            relative = candidate.relative_to(root).as_posix()
            if '..' in Path(relative).parts or not candidate.resolve().is_relative_to(root): continue
            if not relative.startswith('src/test/resources/features/'): continue
            ref, source = load_source(relative)
            lines = source.splitlines(); number = int(match[2])
            if number > len(lines): continue
            heading, in_string, at_string, unsupported = None, None, False, False
            for raw_line in lines[:number]:
                line = raw_line.strip(); at_string = bool(in_string)
                if in_string:
                    if line.startswith(in_string): in_string = None
                    continue
                if line.startswith(('"""', '```')):
                    in_string = line[:3]; at_string = True; continue
                if line.startswith('# language:') and line.split(':',1)[1].strip() != 'en': unsupported = True
                if line.startswith(('Scenario:', 'Example:')): heading = line.split(':',1)[1].strip()
                elif line.startswith(('Scenario Outline:', 'Scenario Template:', 'Background:', 'Examples:', 'Scenarios:')): heading = None
            if (unsupported or at_string or heading != scenario or
                    not re.match(r'^(Given|When|Then|And|But|\*)\s+', lines[number-1].strip())): continue
            identity = (relative, number)
            if identity in seen: continue
            seen.add(identity)
            locations.append({**ref, 'line': number, 'role': 'reported_feature_step',
                              'scenario': scenario, 'quote': lines[number-1].strip()[:240]})
        except (ValueError, OSError, UnicodeError): continue
    pattern = re.compile(r'^\s*at\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\.([A-Za-z_]\w*)\(([A-Za-z_]\w*\.java):([1-9]\d{0,6})\)\s*$', re.MULTILINE)
    for match in list(pattern.finditer(errors))[:16]:
        if len(locations) >= 3: break
        cls, method, filename, line_text = match.groups()
        if len(cls) > 240 or cls.rsplit('.',1)[-1] + '.java' != filename: continue
        found = []
        for prefix in ('src/test/java/', 'src/main/java/'):
            relative = prefix + cls.replace('.','/') + '.java'
            try: found.append((relative, *load_source(relative)))
            except (ValueError, OSError, UnicodeError): pass
        if len(found) != 1: continue
        relative, ref, source = found[0]
        try: body = _method(source, method, cls.rsplit('.',1)[-1], '.java')
        except (ValueError, SyntaxError): continue
        lines = source.splitlines(); number = int(line_text)
        if body is None or number > len(lines): continue
        # Multiline signatures are left for explicit review, not guessed ranges.
        declaration = _masked_java(source).splitlines()[body[0]-1]
        if '{' not in declaration or not body[0] <= number <= body[0] + body[1].count('\n'): continue
        identity = (relative, number)
        if identity in seen: continue
        seen.add(identity)
        locations.append({**ref, 'line': number, 'role': 'reported_java_frame',
                          'method': method, 'method_line': body[0], 'quote': lines[number-1].strip()[:240]})
    return locations


def review_execution(result, project_root=None):
    """Inspect captured evidence and at most ten exact conventional source paths.

    Source is the revision read AFTER execution, not a proven executed revision.
    Missing/ambiguous source or unrecognized assertion syntax is never a defect.
    """
    findings, sources, limits = [], [], [
        "Static review warnings are not a correctness verdict or a proven root cause.",
        "Requirements, helper/inherited assertions, expected-exception behavior and application behavior are not fully evaluated.",
        "Direct assertion review supports conventional Java void methods/Python functions. Reported failure locations additionally support simple English Gherkin steps and uniquely matched single-line Java void declarations; outlines/other layouts need explicit review.",
        "Source hashes identify the revision read after execution; they do not prove it was the executed revision.",
        "Source reads are capped at ten files, 256 KB per file and 1 MB total; at most 20 case records are inspected.",
        "No repair, command, rerun, network request or hosted-model upload is performed by this review.",
    ]

    def add(kind, title, evidence, next_check):
        if len(findings) < 40:
            findings.append({"kind": kind, "title": title, "evidence": evidence, "next_check": next_check})

    if result.get("timed_out") is True:
        add("uncertain", "Execution timed out; do not automatically retry.", {"field": "timed_out"},
            "Reconcile the saved receipt and any remaining processes before a separately approved rerun.")
    code = result.get("exit_code")
    if type(code) is not int:
        limits.append("The captured result has no confirmed integer exit code.")
    for stream in ("stdout", "stderr"):
        text = result.get(stream, "")
        if not isinstance(text, str):
            continue
        for number, line in enumerate(text[-12000:].splitlines(), 1):
            signal = re.search(r"Traceback \(most recent call last\)|\bAssertionError\b|\bBUILD FAILED\b", line)
            if signal:
                add("log_signal", "Captured output contains " + signal[0] + ".", {"field": stream, "captured_line": number},
                    "Inspect the captured log context. This may be handled/quoted output; it does not alone prove a failed test.")
                break
    if result.get("output_truncated"):
        limits.append("Captured logs were truncated; line references refer only to the saved tail.")
    reports = result.get("reports", [])
    if not isinstance(reports, list):
        reports = []
    if not reports:
        limits.append("No attached native test report: assertions and test outcomes are not verified.")
    if result.get("report_errors"):
        add("report_parse", "Some native reports could not be parsed.", {"field": "report_errors"},
            "Inspect the saved parser errors before treating the report set as complete.")
    if result.get("unchanged_reports_ignored") or result.get("outside_execution_window_ignored"):
        limits.append("Excluded old/out-of-window reports are not evidence of this run.")
    root = Path(project_root).resolve() if project_root is not None else None
    cache, checked = {}, set()
    cases_seen = 0
    total_bytes = 0

    def load_source(relative):
        nonlocal total_bytes
        path = root / relative
        if any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction())
               for part in [path, *path.parents] if part != root):
            raise ValueError("Source links/junctions are not reviewed.")
        if relative not in cache:
            if len(cache) >= MAX_SOURCE_FILES: raise ValueError("Ten-file source review limit reached.")
            size = path.stat().st_size
            if size > MAX_SOURCE_BYTES or total_bytes + size > 1_000_000:
                raise ValueError("Bounded source review limit reached.")
            from agent.tools.test_failures import _load
            ref, text, _ = _load(root, relative, max_bytes=min(MAX_SOURCE_BYTES, 1_000_000-total_bytes))
            total_bytes += ref["size_bytes"]
            if total_bytes > 1_000_000: raise ValueError("Total source review exceeds 1 MB.")
            cache[relative] = (ref, text)
        return cache[relative]
    for report_index, report in enumerate(reports[:MAX_REPORTS]):
        if not isinstance(report, dict):
            continue
        counts = [report.get(k) for k in ("passed", "failed", "skipped", "incomplete", "total")]
        valid = all(type(n) is int and n >= 0 for n in counts) and sum(counts[:4]) == counts[4]
        field = "reports[" + str(report_index) + "]"
        fresh = (result.get("report_status") == "fresh_reports_found" and
                 str(report.get("freshness", "")).startswith(FRESH_PREFIX) and
                 report.get("format") in {"junit-xml", "testng-xml", "cucumber-json"})
        if not fresh or not valid:
            add("unverified_report", "Report association or counts are unverified.", {"field": field, "report_file": str(report.get("file", ""))},
                "Use a fresh valid native report; do not infer success from log text.")
            continue
        passed, failed, skipped, incomplete, total = counts
        if (code == 0 and (failed or report.get("configuration_failure_count"))) or (type(code) is int and code != 0 and passed):
            add("outcome_conflict", "Command status and native test results need separate interpretation.", {"field": field, "report_file": str(report.get("file", ""))},
                "Inspect both the exit code and native failures/configuration; passing cases do not make a failed command successful.")
        if failed or report.get("configuration_failure_count"):
            add("native_failure", "Native report contains test/configuration failures.", {"field": field, "report_file": str(report.get("file", ""))},
                "Review the exact failed case and matching logs/source before proposing a repair.")
        if skipped or incomplete or not total:
            add("coverage_gap", "Skipped, incomplete or empty results limit acceptance.", {"field": field, "report_file": str(report.get("file", ""))},
                "Confirm which selected cases actually ran; skipped cases are not passes.")
        if report.get("details_truncated"):
            limits.append("Per-case details were truncated; source review cannot cover every reported test.")
        cases = report.get("tests", [])
        if not isinstance(cases, list):
            continue
        for index, case in enumerate(cases):
            if cases_seen >= MAX_CASES:
                limits.append("Source review is limited to the first 20 case records.")
                break
            cases_seen += 1
            if not isinstance(case, dict):
                continue
            key = (case.get("class"), case.get("name"))
            if key in checked:
                continue
            checked.add(key)
            evidence = {"field": field + ".tests[" + str(index) + "]", "case": str(case.get("name", ""))[:300]}
            if root is None:
                sources.append({**evidence, "status": "not reviewed: no source snapshot attached"})
                continue
            for location in _failure_locations(case, root, load_source):
                citation = {**evidence, **location}
                add("reported_failure_location", "Failed report points to " + location["role"].replace("reported_", "").replace("_", " ") + ".",
                    citation, "Inspect this reported step/helper and its requirement before proposing any change. This is a source citation, not a proven cause or permission to rerun.")
            paths, name, cls = _candidates(case)
            existing = []
            for relative in paths:
                p = root / relative
                # Do not follow even in-project source links or junctions.
                chain = [p, *p.parents]
                if any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()) for part in chain if part != root):
                    continue
                if p.is_file():
                    existing.append(relative)
            if len(existing) != 1:
                sources.append({**evidence, "status": "not reviewed: source missing or ambiguous"})
                continue
            relative = existing[0]
            try:
                ref, text = load_source(relative)
                method = _method(text, name, cls, Path(relative).suffix, module_level=Path(relative).stem == cls)
                if method is None:
                    sources.append({**evidence, **ref, "status": "not reviewed: unique test method not identified"})
                    continue
                line, _, assertions, weak, commented = method
                citation = {**evidence, **ref, "line": line}
                sources.append({**citation, "status": "bounded static review", "recognized_direct_checks": assertions})
                if not assertions:
                    add("assertion_review", "No direct assertion recognized in the matched test method.", citation,
                        "Check helper/inherited assertions and framework expectations before deciding whether an assertion is missing.")
                if weak:
                    add("weak_assertion", "An always-true assertion needs review.", citation,
                        "Compare against the requirement; an always-true check does not validate application behavior.")
                if commented:
                    add("commented_assertion", "A commented assertion was found in the matched test method.", citation,
                        "Confirm whether the intended requirement is still checked by live code.")
            except (ValueError, OSError, SyntaxError, UnicodeError):
                sources.append({**evidence, "status": "not reviewed: source unavailable, unsupported or over the bounded limit"})
    if len(reports) > MAX_REPORTS:
        limits.append("Only the first 20 reports were reviewed.")
    if len(reports) > 1:
        limits.append("Reports may overlap; counts are not combined.")
    return {"version": 1, "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "status": "review_needed" if findings else "limited_review",
            "mode": "local static review", "findings": findings, "source_checks": sources,
            "limits": list(dict.fromkeys(limits))}


def attach_review(result, project_root):
    """A review failure must never change the saved execution outcome."""
    try:
        review = review_execution(result, project_root)
    except Exception:
        review = {"version": 1, "status": "unavailable", "mode": "local static review",
                  "findings": [], "source_checks": [],
                  "limits": ["Review unavailable; the execution result is retained. Do not rerun to repair the review."]}
    return {**result, "post_run_review": review}
