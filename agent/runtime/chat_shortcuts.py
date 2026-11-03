"""Explicit local shortcuts reuse existing scoped reads; no command execution."""
from pathlib import PureWindowsPath
import re

HELP = """Available shortcuts:

- `/help` — show this list.
- `/memory` — show saved facts using the existing memory command.
- `/read relative/path` — read the first 80 lines of a file in the selected project.
- `/results relative/report.xml` — inspect saved native XML/JSON test results.

Choose a saved project for `/read` and `/results`. Paths with spaces may be quoted.
The **+ → Commands** menu fills a draft; edit it and press Send.
These shortcuts do not edit files, run tests, connect to Jira/Git or grant approval.
"""


def is_shortcut(question):
    if not isinstance(question, str) or not re.match(r"^/[A-Za-z][A-Za-z0-9_-]*(?:\s|$)", question.strip()):
        return False
    from agent.runtime.continuations import command
    return command(question) is None


def parse_shortcut(question):
    if not is_shortcut(question):
        return None
    text = question.strip()
    if any(char in text for char in "\r\n\x00") or len(text) > 700:
        raise ValueError("Use one shortcut on one line, with a relative path up to 600 characters.")
    # Any whitespace may separate the command from its one literal path.
    parts = text.split(maxsplit=1)
    name = parts[0][1:].lower()
    argument = parts[1].strip() if len(parts) == 2 else ""
    if name not in {"help", "memory", "read", "results"}:
        raise ValueError("Unknown shortcut. Use /help to see the supported commands.")
    if name in {"help", "memory"}:
        if argument:
            raise ValueError("Use /" + name + " without arguments.")
        return {"name":name}
    if not argument:
        raise ValueError("Usage: /" + name + " relative/path" + (".xml" if name == "results" else ""))
    if argument[0] in {'"', "'"}:
        if len(argument) < 3 or argument[-1] != argument[0]:
            raise ValueError("Close the quoted relative path.")
        argument = argument[1:-1]
    path = PureWindowsPath(argument)
    parts = argument.replace("\\", "/").split("/")
    denied = {".git", ".venv", "venv", "node_modules", ".aws", ".ssh", ".azure", ".codex", ".agents", "__pycache__"}
    private = {".npmrc", ".pypirc", "credentials", "credentials.json", "secrets.json", "secrets.toml"}
    if (not argument.strip() or len(argument) > 600 or path.drive or path.root or
            any(char in argument for char in ':"\x00<>|') or
            any(part in {"", ".", ".."} for part in parts) or
            any(part.lower() in denied | private or part.lower().startswith(".env") for part in parts)):
        raise ValueError("Use a relative project path without traversal or credential/private folders.")
    if name == "results" and path.suffix.lower() not in {".xml", ".json"}:
        raise ValueError("Use an existing native XML or JSON results report.")
    return {"name":name, "path":"/".join(parts)}


def _reply(answer, *, incomplete=False):
    return {"answer":answer, "route":"shortcut", "task_status":"incomplete" if incomplete else "completed",
            "execution_outcome":"blocked" if incomplete else "completed", "answer_available":True}


def _code(content):
    fence = "`" * max(3, 1 + max((len(s) for s in re.findall(r"`+", content)), default=0))
    return fence + "\n" + content + "\n" + fence


def local_shortcut_reply(question, state):
    try:
        shortcut = parse_shortcut(question)
    except ValueError as error:
        return _reply(str(error), incomplete=True)
    if shortcut is None or shortcut["name"] == "memory":
        return None
    if shortcut["name"] == "help":
        return _reply(HELP)
    if not state.get("bound_project_root") or not state.get("project_id"):
        return _reply("Select a saved project in Projects before using /" + shortcut["name"] + ".", incomplete=True)
    try:
        from agent.tools.project_tools import ProjectTools
        tools = ProjectTools(state["bound_project_root"])
        if shortcut["name"] == "read":
            resolved = tools._resolve_file(shortcut["path"])
            parse_shortcut("/read " + resolved.relative_to(tools.root).as_posix())
            data = tools.read_file(shortcut["path"], start_line=1, max_lines=80)
            answer = "Project file: " + _code(data["file"]) + "\n\n" + _code(data["content"])
            answer += "\n\nInspected lines " + str(data["start_line"]) + "–" + str(data["end_line"]) + "."
            if data["truncated"]:
                answer += " More lines exist; this is a limited excerpt."
            return _reply(answer)
        # Use the investigation loader's private-path and bounded text checks
        # before the existing native parser, including for build report folders.
        from agent.tools.test_failures import _load
        from agent.tools.test_results import parse_test_results
        ref, _, _ = _load(tools.root, shortcut["path"], max_bytes=5_000_000)
        data = parse_test_results(tools.root, shortcut["path"], limit=40)
        _load(tools.root, shortcut["path"], ref["sha256"], max_bytes=5_000_000)
        answer = "Saved native results: " + _code(data["file"])
        answer += ("\n\nReported counts: passed {passed}, failed {failed}, skipped {skipped}, "
                   "incomplete {incomplete}; configuration failures {configuration_failure_count}.").format(**data)
        rows = [" | ".join((case.get("class", ""), case["name"], case["status"])) for case in data["tests"]]
        answer += "\n\n" + _code("\n".join(rows) if rows else "No native test cases found.")
        if data["details_truncated"]:
            answer += "\n\nShowing the first 40 cases; reported counts cover this report only."
        answer += "\n\nSaved observations only. Run association/freshness is unverified; no test was run and no repair or release acceptance is claimed."
        return _reply(answer)
    except Exception as error:
        # Do not include raw exceptions, which may contain resolved private paths.
        if isinstance(error, FileNotFoundError):
            message = "File not found in the selected project. Check its relative path."
        elif isinstance(error, PermissionError):
            message = "The selected project file could not be accessed. Check its local permissions."
        else:
            message = "Could not read that selected-project file. Check its path, supported format and size; results must be a valid native XML/JSON report."
        return _reply(message, incomplete=True)
