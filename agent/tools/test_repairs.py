"""Evidence-bound single-case repair handoff; planning/comparison never execute."""
from collections import Counter
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re

from agent.tools.test_failures import _load, investigate_test_failure
from agent.tools.test_results import parse_test_results

PLAN_KEYS = {"version", "project_root", "baseline", "requirements", "replacement", "diagnosis", "rerun", "id"}
REQUEST_KEYS = {"relative_path", "case_name", "case_class", "run_file", "source_file", "old_text", "new_text",
                "diagnosis", "requirements", "command", "relative_report_folder", "timeout", "cucumber"}
CASE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", re.ASCII)
LIMITS = [
    "The diagnosis is a review hypothesis, not an independently established cause.",
    "Saved run/report metadata is checked for consistency; it is not authenticated execution provenance.",
    "Static assertion preservation cannot prove unchanged control flow or requirement correctness.",
    "No automatic repair, rerun, Jira operation or publication is authorized by a plan or artifact.",
]


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()



def _relative(root, value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Use a forward-slash relative path inside the selected project.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not (root/path).resolve().is_relative_to(root):
        raise ValueError("Path must stay inside the selected project.")
    for part in (root/path, *(root/path).parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Repair evidence cannot use symlinks or junctions.")
    if any(p.lower() in {".git", ".venv", ".aws", ".ssh", ".codex", ".agents", "node_modules"} or p.lower().startswith(".env") for p in path.parts):
        raise ValueError("Private repair paths are excluded.")
    return path.as_posix()


def _read(root, path, expected=None):
    path = _relative(root, path)
    return _load(root, path, expected, max_bytes=256_000)


def _checks(text, suffix):
    """Preserve recognized checks exactly; this does not establish semantic equivalence."""
    if suffix == ".py":
        tree = ast.parse(text)
        checks = [ast.dump(n, include_attributes=False) for n in ast.walk(tree)
                  if isinstance(n, ast.Assert) or isinstance(n, ast.Call) and
                  re.fullmatch(r"assert\w*|expect|verify", getattr(n.func, "id", getattr(n.func, "attr", "")))]
        return Counter(checks)
    from agent.tools.execution_review import _masked_java
    masked = _masked_java(text)
    checks = []
    for match in re.finditer(r"\b(?:assert\w*|verify|expect)\s*\(|\bassert\s+", masked):
        start = match.start()
        if masked[match.end()-1] == "(":
            end, depth = match.end(), 1
            while end < len(masked) and depth:
                depth += (masked[end] == "(") - (masked[end] == ")")
                end += 1
            if depth:
                raise ValueError("Unbalanced assertion; use explicit source review.")
        else:
            end = masked.find(";", match.end())
            if end < 0:
                raise ValueError("Unterminated assertion.")
        checks.append(text[start:end].replace("\r\n", "\n"))
    return Counter(checks)


def _skip_markers(text, suffix):
    if suffix == ".py":
        tree = ast.parse(text)
        markers = []
        names = {"skip", "skipIf", "skipUnless", "SkipTest", "xfail", "expectedFailure"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in names:
                markers.append(ast.dump(node, include_attributes=False))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, (ast.Name, ast.Attribute)) and getattr(decorator, "attr", getattr(decorator, "id", "")) in names:
                        markers.append(ast.dump(decorator, include_attributes=False))
        return Counter(markers)
    from agent.tools.execution_review import _masked_java
    return Counter(re.findall(r"@(?:Disabled|Ignore)\b|\benabled\s*=\s*false\b|\bnew\s+SkipException\b", _masked_java(text)))


def _replacement(tools, request):
    name = _relative(tools.root, request["source_file"])
    tools._resolve_file(name)
    ref, original, path = _read(tools.root, name)
    if path.suffix not in {".py", ".java"}:
        raise ValueError("This repair slice supports Java/Python source only.")
    old, new = request["old_text"], request["new_text"]
    if not all(isinstance(v, str) and 0 < len(v) <= 4000 and v.count("\n") < 40 for v in (old, new)) or old == new:
        raise ValueError("Use distinct, nonempty old/new text of at most 40 lines and 4000 characters.")
    original = original.replace("\r\n", "\n")
    old, new = old.replace("\r\n", "\n"), new.replace("\r\n", "\n")
    if original.count(old) != 1:
        raise ValueError("Repair old_text must identify exactly one current source location.")
    changed = original.replace(old, new, 1)
    if _checks(original, path.suffix) - _checks(changed, path.suffix):
        raise ValueError("Repair removes or changes a recognized assertion; preserve intended assertions.")
    if _skip_markers(changed, path.suffix) - _skip_markers(original, path.suffix):
        raise ValueError("Repair introduces a disabled/ignored/skipped test marker requiring manual review.")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ValueError("Source changed during planning.")
    bom = raw.startswith(b"\xef\xbb\xbf")
    output = changed.replace("\n", "\r\n") if b"\r\n" in raw else changed
    after = hashlib.sha256(output.encode("utf-8-sig" if bom else "utf-8")).hexdigest()
    return {**ref, "old_text": old, "new_text": new, "after_sha256": after,
            "diff": "".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                                fromfile=name, tofile=name))}


def _focused_command(tools, command, case, folder, timeout):
    if not isinstance(command, list) or len(command) > 16 or not all(isinstance(v, str) for v in command):
        raise ValueError("Supply one bounded command list.")
    cls, name = case.get("class", ""), case["name"]
    if not CASE.fullmatch(cls) or not re.fullmatch(r"[A-Za-z_]\w*", name, re.ASCII):
        raise ValueError("Choose one exact nonparameterized case/class for this first repair slice.")
    if not command or command[0] != "gradlew" or command.count("test") != 1 or command.count("--tests") != 1:
        raise ValueError("Use gradlew test --tests exact.Class.method; broad suites and other runners are outside this slice.")
    index = command.index("--tests")
    if index+1 >= len(command) or command[index+1] != cls+"."+name:
        raise ValueError("The Gradle --tests selector must name exactly the selected failed class/method.")
    allowed = {"test", "--no-daemon", "--offline", "--console=plain"}
    for i, value in enumerate(command[1:], 1):
        if i in {index, index+1}:
            continue
        if value not in allowed and not re.fullmatch(r"-D(?:env|browser|headless)=[A-Za-z0-9_-]{1,40}", value):
            raise ValueError("Unsupported rerun flag/task; keep the selected Gradle test scope.")
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ValueError("Rerun timeout must be an integer between 1 and 300.")
    tools._command_argv(command, timeout)
    return {"command": command, "relative_report_folder": _relative(tools.root, folder), "timeout": timeout}


def prepare_test_repair(tools, request):
    """Read-only: produce a revision-bound proposal, never approve or execute it."""
    required = REQUEST_KEYS - {"case_class", "timeout", "cucumber"}
    if not isinstance(request, dict) or set(request)-REQUEST_KEYS or required-set(request):
        raise ValueError("Supply the complete repair request with source, failed case, saved run, requirements and focused command.")
    if not isinstance(request["diagnosis"], str) or not 1 <= len(request["diagnosis"]) <= 1000:
        raise ValueError("Give one bounded diagnosis hypothesis supported by the selected evidence.")
    requirements = request["requirements"]
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 2:
        raise ValueError("Select one or two explicit requirement spans.")
    spans = []
    for span in requirements:
        if not isinstance(span, dict) or span.get("role", "requirement") != "requirement":
            raise ValueError("Repair requirements must be requirement spans.")
        spans.append({**span, "role": "requirement"})
    investigation = investigate_test_failure(tools.root, request["relative_path"], request["case_name"],
                                            request.get("case_class", ""), spans, request["run_file"])
    run_ref, content, _ = _read(tools.root, request["run_file"])
    run = json.loads(content)
    if investigation["execution"]["outcome_uncertain"]:
        raise ValueError("Reconcile the timed-out/unknown execution first; no repair/rerun plan is ready.")
    parsed = parse_test_results(tools.root, request["relative_path"])
    from integrations.reporting.traceability import _association
    if not _association(run, parsed, {"scope": "project"}):
        raise ValueError("Baseline native report does not match the saved run snapshot/time window.")
    replacement = _replacement(tools, request)
    selection = None
    if "cucumber" in request:
        from agent.tools.cucumber_repairs import prepare_selection, focused_command
        if investigation["report"]["format"] != "junit-xml":
            raise ValueError("Cucumber repair selection requires the Gradle JUnit XML with scenario titles.")
        selection = prepare_selection(tools, request["cucumber"], investigation["report"]["case"])
        if replacement["file"] in {ref["file"] for ref in [selection["runner"], selection["build"], *selection["features"]]}:
            raise ValueError("Repairing selection files requires a separate manual review.")
        rerun = focused_command(tools, request["command"], selection,
                                request["relative_report_folder"], request.get("timeout", 300))
    else:
        rerun = _focused_command(tools, request["command"], investigation["report"]["case"],
                                  request["relative_report_folder"], request.get("timeout", 300))
    plan = {"version": 1, "project_root": str(tools.root),
            "baseline": {"report": investigation["report"], "run": run_ref},
            "requirements": investigation["evidence_spans"], "replacement": replacement,
            "diagnosis": {"hypothesis": request["diagnosis"], "root_cause": "unconfirmed"},
            "rerun": rerun}
    if selection is not None:
        plan.update(version=2, cucumber=selection)
    plan["id"] = _hash(plan)
    if len(json.dumps(plan)) > 32_000:
        raise ValueError("Repair plan exceeds the 32000-character review limit; narrow the patch.")
    return {"plan": plan, "next_actions": ["apply_test_repair", "rerun_test_repair", "compare_test_rerun"],
            "handoff": "Pass the returned plan object unchanged as the plan argument; it is included once to avoid duplicate context.",
            "approval": "Separate exact-action approvals are required for the repair and the later rerun.",
            "actions_executed": [], "limits": LIMITS}


def validate_plan(tools, plan, stage, check_baseline=True):
    """Called again before approval and before execution; digest is integrity, not authority."""
    if (not isinstance(plan, dict) or type(plan.get("version")) is not int or
            (plan["version"] == 1 and set(plan) != PLAN_KEYS) or
            (plan["version"] == 2 and set(plan) != PLAN_KEYS | {"cucumber"}) or
            plan["version"] not in {1, 2}):
        raise ValueError("Invalid repair-plan structure.")
    if len(json.dumps(plan)) > 32_000 or plan["id"] != _hash({k:v for k,v in plan.items() if k != "id"}):
        raise ValueError("Repair plan changed or exceeds the review limit.")
    if plan["project_root"] != str(tools.root):
        raise ValueError("Repair plan belongs to another project.")
    if stage not in {"before", "after"} or not isinstance(plan.get("requirements"), list) or not 1 <= len(plan["requirements"]) <= 2:
        raise ValueError("Repair plan needs its original bounded requirements and a valid stage.")
    if set(plan["rerun"]) != {"command", "relative_report_folder", "timeout"}:
        raise ValueError("Unexpected rerun arguments.")
    case = plan["baseline"]["report"]["case"]
    if case.get("status") != "failed" or plan["diagnosis"].get("root_cause") != "unconfirmed":
        raise ValueError("Retain the selected failed baseline and unconfirmed causal status.")
    if plan["version"] == 2:
        from agent.tools.cucumber_repairs import prepare_selection, focused_command
        if plan["baseline"]["report"]["format"] != "junit-xml":
            raise ValueError("Cucumber repair selection requires the original Gradle JUnit XML.")
        selection = plan["cucumber"]
        current = prepare_selection(tools, {key:selection[key] for key in ("runner_file", "feature_file", "tag")}, case)
        if current != selection:
            raise ValueError("Cucumber selection source or feature inventory changed; prepare a fresh review.")
        if plan["replacement"]["file"] in {ref["file"] for ref in [selection["runner"], selection["build"], *selection["features"]]}:
            raise ValueError("Repairing selection files requires a separate manual review.")
        focused_command(tools, plan["rerun"]["command"], selection,
                        plan["rerun"]["relative_report_folder"], plan["rerun"]["timeout"])
    else:
        _focused_command(tools, **{"command":plan["rerun"]["command"], "case":case,
                                  "folder":plan["rerun"]["relative_report_folder"], "timeout":plan["rerun"]["timeout"]})
    for span in plan["requirements"]:
        _read(tools.root, span["file"], span["sha256"])
    _read(tools.root, plan["baseline"]["run"]["file"], plan["baseline"]["run"]["sha256"])
    if check_baseline:
        report = plan["baseline"]["report"]
        _read(tools.root, report["file"], report["sha256"])
        baseline = investigate_test_failure(tools.root, report["file"], case["name"], case.get("class", ""),
                                            run_file=plan["baseline"]["run"]["file"])
        if baseline["execution"]["outcome_uncertain"] or baseline["report"] != report:
            raise ValueError("The failed baseline changed or its outcome is uncertain.")
    change = plan["replacement"]
    ref, _, _ = _read(tools.root, change["file"], change["sha256"] if stage == "before" else change["after_sha256"])
    if stage == "before":
        report = plan["baseline"]["report"]
        request = {"relative_path":report["file"], "case_name":case["name"], "case_class":case.get("class", ""),
                   "run_file":plan["baseline"]["run"]["file"], "source_file":change["file"],
                   "old_text":change["old_text"], "new_text":change["new_text"],
                   "diagnosis":plan["diagnosis"]["hypothesis"],
                   "requirements":[{"relative_path":r["file"], "role":"requirement", "start_line":r["start_line"],
                                    "max_lines":r["end_line"]-r["start_line"]+1, "sha256":r["sha256"]} for r in plan["requirements"]],
                   **plan["rerun"]}
        if plan["version"] == 2:
            request["cucumber"] = {key:plan["cucumber"][key] for key in ("runner_file", "feature_file", "tag")}
        if prepare_test_repair(tools, request)["plan"] != plan:
            raise ValueError("Repair evidence no longer matches the reviewed plan.")
    return ref


def repair_version(root, action, plan):
    from agent.tools.project_tools import ProjectTools
    ref = validate_plan(ProjectTools(root), plan, "before" if action == "apply_test_repair" else "after")
    return _hash({"plan":plan["id"], "source":ref["sha256"]})


def apply_test_repair(tools, plan):
    validate_plan(tools, plan, "before")
    change = plan["replacement"]
    result = tools._replace_text(change["file"], change["old_text"], change["new_text"], expected_sha256=change["sha256"])
    ref, _, _ = _read(tools.root, change["file"], change["after_sha256"])
    return {**result, "repair_plan_id":plan["id"], "source_after":ref,
            "rerun_executed":False, "causal_repair_verified":False,
            "next":"Review and separately approve rerun_test_repair for the exact selected case."}


def rerun_test_repair(tools, plan):
    before = validate_plan(tools, plan, "after")
    result = tools.run_tests_and_parse(**plan["rerun"])
    try:
        after, _, _ = _read(tools.root, plan["replacement"]["file"], before["sha256"])
        source = {"before":before, "after":after, "unchanged":True}
    except (ValueError, OSError):
        source = {"before":before, "after":None, "unchanged":False}
    selection_result = {}
    if plan["version"] == 2:
        from agent.tools.cucumber_repairs import prepare_selection
        try:
            selected = plan["cucumber"]
            after = prepare_selection(tools, {key:selected[key] for key in ("runner_file", "feature_file", "tag")},
                                      plan["baseline"]["report"]["case"])
            selection_result = {"before":selected, "after":after, "unchanged":after == selected}
        except (ValueError, OSError):
            selection_result = {"before":plan["cucumber"], "after":None, "unchanged":False}
    return {**result, "repair_plan_id":plan["id"], "repair_source":source,
            **({"repair_selection":selection_result} if plan["version"] == 2 else {}),
            "source_note":"Observed source before/after execution; compiler/cache provenance is not independently verified."}


def compare_test_rerun(tools, plan, run_file):
    """Read saved native evidence; never run tests to fill gaps."""
    validate_plan(tools, plan, "after", check_baseline=False)
    run_ref, text, _ = _read(tools.root, run_file)
    if run_ref["file"] == plan["baseline"]["run"]["file"]:
        raise ValueError("Retain the original baseline run; use a distinct saved rerun file.")
    run = json.loads(text)
    gaps, rows = [], []
    if run.get("repair_plan_id") != plan["id"]:
        gaps.append("Saved rerun does not identify this repair plan.")
    if run.get("command") != plan["rerun"]["command"]:
        gaps.append("Saved command differs from the exact focused command.")
    if run.get("timed_out") is not False or type(run.get("exit_code")) is not int or run["exit_code"] != 0:
        gaps.append("Rerun failed, timed out or has an unknown exit; no success is claimed.")
    source = run.get("repair_source", {})
    if plan["version"] == 2:
        selection = run.get("repair_selection", {})
        if (selection.get("unchanged") is not True or
                any(selection.get(key) != plan["cucumber"] for key in ("before", "after"))):
            gaps.append("Cucumber selection revisions were not observed unchanged across the rerun.")
    expected = plan["replacement"]
    if (source.get("unchanged") is not True or
            any(not isinstance(source.get(k), dict) or source[k].get("file") != expected["file"] or
                source[k].get("sha256") != expected["after_sha256"] for k in ("before", "after"))):
        gaps.append("Repaired source revision was not observed unchanged across the rerun.")
    reports = run.get("reports", [])
    if not isinstance(reports, list) or not 1 <= len(reports) <= 20:
        gaps.append("Saved rerun needs between one and twenty fresh native reports.")
        reports = []
    from integrations.reporting.traceability import _association
    selected = plan["baseline"]["report"]["case"]
    for snapshot in reports:
        name = snapshot.get("file") if isinstance(snapshot, dict) else None
        ref, _, _ = _read(tools.root, name)
        parsed = parse_test_results(tools.root, name)
        if not _association(run, parsed, {"scope":"project"}) or parsed["details_truncated"]:
            gaps.append("Report/run association is unverified: " + name)
        if parsed["configuration_failure_count"]:
            gaps.append("Native configuration failure remains: " + name)
        for case in parsed["tests"]:
            if plan["version"] == 2:
                from agent.tools.cucumber_repairs import matches_case
                matches = matches_case(case, plan["cucumber"])
            else:
                matches = case.get("name") == selected["name"] and case.get("class", "") == selected.get("class", "")
            if not matches:
                gaps.append("Rerun includes a case outside the selected scope: " + name)
            else:
                rows.append({"report":ref, "case":case})
                if case["status"] != "passed":
                    gaps.append("Selected case is not reported passed: " + name)
        _read(tools.root, name, ref["sha256"])
    if not rows:
        gaps.append("No selected case result was found.")
    elif plan["version"] == 2 and len(rows) != 1:
        gaps.append("Cucumber selection needs exactly one native result; duplicate/overlapping reports are not acceptance.")
    return {"status":"selected_rerun_passed" if not gaps else "incomplete",
            "repair_plan_id":plan["id"], "baseline_status":"failed", "rerun_evidence":run_ref,
            "selected_results":rows, "gaps":list(dict.fromkeys(gaps)),
            "root_cause":"unconfirmed", "actions_executed":[], "limits":LIMITS}
