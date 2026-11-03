"""Prepare exact historical-report file proposals without writing or executing."""
import hashlib
from pathlib import Path, PureWindowsPath
import re

from integrations.reporting.evidence import resolve_evidence


def prepare_report_export(tools, manifest_file, relative_path, evidence_folder=""):
    """Build once locally; the caller must obtain separate create_file approval.

    Evidence is checked at preparation. The reviewed content is a historical
    snapshot, not a promise that its source files stay unchanged afterward.
    """
    from agent.tools.project_tools import SKIP_DIRS, SKIP_FILES

    path = resolve_evidence(tools.root, relative_path)
    requested = Path(relative_path.replace("\\", "/"))
    if path.suffix.lower() != ".md" or PureWindowsPath(relative_path).drive:
        raise ValueError("Choose a new project-relative Markdown (.md) report file.")
    excluded = {name.casefold() for name in SKIP_DIRS | SKIP_FILES}
    current = tools.root
    for part in requested.parts:
        if (part.casefold() in excluded or part.endswith((".", " "))
                or re.search(r'[<>:"|?*\x00-\x1f]', part)
                or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)):
            raise ValueError("Unsupported or excluded report destination.")
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink report paths are excluded.")
        if current.exists() and current != path and not current.is_dir():
            raise ValueError("A report parent path is not a folder.")
    if path.exists():
        raise ValueError("Report destination already exists; choose a new filename.")
    # Delegate through this scoped instance so selected-project evidence limits
    # stay identical to build_test_report, including its response-size bound.
    built = tools.build_test_report(manifest_file, evidence_folder)
    content = built["markdown"]
    raw = content.encode("utf-8")
    return {
        "proposal": {"project_root": str(tools.root), "action": "create_file",
                     "arguments": {"relative_path": path.relative_to(tools.root).as_posix(),
                                   "content": content}},
        "summary": built["summary"], "report_status": built["status"],
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
        "note": "Historical saved-evidence snapshot checked at preparation; approval saves only these exact bytes. No tests, commands, Jira or Git operations are requested."
    }
