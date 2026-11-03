"""Read-only, selected-project folder browsing; no recursive scan or models."""
from pathlib import Path, PureWindowsPath
import os
from itertools import islice

from agent.runtime.project_scope import validate_request_scope
from agent.tools.project_tools import ProjectTools, SKIP_DIRS, SKIP_FILES, TEXT_EXTENSIONS

VISIBLE_LIMIT = 200
SCAN_LIMIT = 1000
PRIVATE_DIRS = {".aws", ".ssh", ".azure", ".codex", ".agents"}
PRIVATE_FILES = {"credentials", "secrets", "id_rsa", "id_ed25519", ".netrc", ".git-credentials"}
EXCLUDED = {part.casefold() for part in SKIP_DIRS | SKIP_FILES} | PRIVATE_DIRS | PRIVATE_FILES


def _private(part):
    part = part.casefold()
    return (part in EXCLUDED or
            part.startswith((".env", "credentials.", "secrets.")))


def _link(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _root(backend):
    """The backend checks current project ownership/configuration on every call."""
    if not callable(getattr(backend, "request_scope", None)):
        raise ValueError("Select a saved project before browsing files.")
    scope = validate_request_scope(backend.request_scope())
    if not scope.get("project_id") or not scope.get("bound_project_root"):
        raise ValueError("Select a saved project before browsing files.")
    root = Path(scope["bound_project_root"])
    if _link(root):
        raise ValueError("Project links and junctions cannot be browsed.")
    return root


def _path(root, relative_path, *, allow_root=False):
    if (not isinstance(relative_path, str) or not relative_path.strip() or len(relative_path) > 1000 or
            any(char in relative_path for char in ":\r\n\0")):
        raise ValueError("Use a relative path inside the selected project.")
    win = PureWindowsPath(relative_path)
    parts = relative_path.replace("\\", "/").split("/")
    if allow_root and relative_path == ".":
        return root, "."
    if win.drive or win.root or any(part in {"", ".", ".."} or _private(part) for part in parts):
        raise ValueError("Private paths and paths outside the selected project are excluded.")
    path = root
    for part in parts:
        path = path / part
        if _link(path):
            raise ValueError("Links and junctions cannot be browsed.")
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Path must stay inside the selected project.")
    if any(_private(part) for part in resolved.relative_to(root).parts):
        raise ValueError("Private project paths are excluded.")
    return resolved, resolved.relative_to(root).as_posix()


def list_project_folder(backend, relative_folder="."):
    """List one folder; bounds describe scanned entries, not a complete inventory."""
    root = _root(backend)
    folder, relative = _path(root, relative_folder, allow_root=True)
    if not folder.is_dir():
        raise ValueError("Choose an existing project folder.")
    entries, scanned, truncated = [], 0, False
    # Do not sort an unbounded directory before enforcing the read limit.
    with os.scandir(folder) as iterator:
        for child in islice(iterator, SCAN_LIMIT):
            scanned += 1
            if _private(child.name):
                continue
            candidate = folder / child.name
            try:
                if _link(candidate):
                    continue
                path, rel = _path(root, candidate.relative_to(root).as_posix())
                is_folder = path.is_dir()
                if not is_folder and not path.is_file():
                    continue
            except (OSError, ValueError):
                continue
            if len(entries) == VISIBLE_LIMIT:
                truncated = True
                break
            entries.append({"name":child.name, "path":rel, "kind":"folder" if is_folder else "file",
                            "previewable":not is_folder and path.suffix.lower() in TEXT_EXTENSIONS})
        if scanned == SCAN_LIMIT:
            # At the cap the inventory is conservatively incomplete; do not
            # inspect one more entry just to determine whether it was the last.
            truncated = True
    entries.sort(key=lambda item:(item["kind"] != "folder", item["name"].casefold(), item["name"]))
    return {"folder":relative, "entries":entries, "truncated":truncated, "scan_limit":SCAN_LIMIT,
            "visible_limit":VISIBLE_LIMIT, "scanned_entries":min(scanned, SCAN_LIMIT),
            "scope":"Selected folder only; hidden/private entries and links are excluded."}


def preview_project_file(backend, relative_path):
    """Use the existing text-reader limits; content remains inert UI data."""
    root = _root(backend)
    path, relative = _path(root, relative_path)
    if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError("Preview supports existing project text/source files only.")
    if path.stat().st_size > 1_000_000:
        raise ValueError("File exceeds the 1 MB preview limit.")
    result = ProjectTools(root).read_file(relative, start_line=1, max_lines=80)
    # Detect a link inserted during the read; never publish its text.
    after, _ = _path(root, relative)
    if after != path:
        raise ValueError("The project file changed during preview. Select it again.")
    return result
