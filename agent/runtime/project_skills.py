"""Bounded project-owned skill discovery."""
from pathlib import Path


def project_skills(root):
    root = Path(root).resolve()
    folder = root / ".agents" / "skills"
    if any(p.is_symlink() for p in (root / ".agents", folder)) or not folder.is_dir():
        return []
    rows = []
    for index, directory in enumerate(folder.iterdir()):
        if index >= 200:
            break
        if directory.is_symlink() or not directory.is_dir():
            continue
        path = directory / "SKILL.md"
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16000:
            continue
        content = path.read_text(encoding="utf-8-sig")
        rows.append({"name": directory.name, "path": path.relative_to(root).as_posix(),
                     "content": content})
        if len(rows) >= 50:
            break
    return sorted(rows, key=lambda row: row["name"].casefold())
