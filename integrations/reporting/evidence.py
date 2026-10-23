"""Bounded artifact references across an explicit project and evidence folder."""
import hashlib
import json
from pathlib import Path, PureWindowsPath

TEXT_LIMIT = 5_000_000
BINARY_LIMIT = 50_000_000
PRIVATE = {".git", ".venv", "venv", "node_modules", ".ssh", ".aws", ".azure", ".codex", ".agents"}
TEXT = {".json", ".xml", ".md", ".txt", ".log", ".java", ".py", ".feature", ".gradle", ".kts", ".js", ".ts"}
BINARY = {".png", ".jpg", ".jpeg", ".webp", ".zip", ".pdf", ".docx"}


def resolve_evidence(root, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Use a nonempty relative artifact path.")
    requested = Path(relative.replace("\\", "/"))
    if requested.is_absolute() or PureWindowsPath(relative).drive or any(p == ".." or ":" in p for p in requested.parts):
        raise ValueError("Artifact paths must be relative without traversal or alternate streams.")
    root = Path(root).resolve()
    path = (root / requested).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Artifact escapes its selected root.")
    parts = (*requested.parts, *path.relative_to(root).parts)
    if any(p.lower() in PRIVATE or p.lower().startswith(".env") or p.lower() in
           {".npmrc", ".pypirc", "credentials", "credentials.json", "secrets.json"} for p in parts):
        raise ValueError("Private/credential artifacts are excluded.")
    if path.suffix.lower() not in TEXT | BINARY:
        raise ValueError("Unsupported artifact type.")
    return path


class EvidenceStore:
    def __init__(self, project_root, evidence_root):
        self.roots = {"project": Path(project_root).resolve(), "evidence": Path(evidence_root).resolve()}
        self.records = []
        self.loaded = {}

    def read(self, ref, *, text=False):
        if not isinstance(ref, dict) or set(ref) != {"scope", "file", "sha256"}:
            raise ValueError("Each reference requires exactly scope, file and sha256.")
        if ref["scope"] not in self.roots or not isinstance(ref["sha256"], str) or len(ref["sha256"]) != 64:
            raise ValueError("Use project/evidence scope and a complete SHA256.")
        path = resolve_evidence(self.roots[ref["scope"]], ref["file"])
        key = (ref["scope"], path)
        if key in self.loaded:
            record, content = self.loaded[key]
            if record["sha256"] != ref["sha256"]:
                raise ValueError("Conflicting artifact revisions in one manifest.")
            if text and content is None:
                raise ValueError("Binary artifacts are linked, not read as text.")
            return record, content, path
        is_text = path.suffix.lower() in TEXT
        if text and not is_text:
            raise ValueError("Text evidence is required here.")
        limit = TEXT_LIMIT if is_text else BINARY_LIMIT
        before = path.stat()
        if before.st_size > limit:
            raise ValueError("Artifact exceeds its reporting size limit.")
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
        after = path.stat()
        if len(raw) > limit or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Artifact changed during reading.")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != ref["sha256"]:
            raise ValueError("Artifact SHA256 differs from the requested revision.")
        content = raw.decode("utf-8-sig") if is_text else None
        record = {"id": f"E{len(self.records)+1:03d}", "scope": ref["scope"],
                  "file": path.relative_to(self.roots[ref["scope"]]).as_posix(),
                  "path": path.as_posix(), "sha256": digest, "size_bytes": len(raw),
                  "modified_at_ns": after.st_mtime_ns,
                  "inspection": "text loaded" if is_text else "bytes verified only; no visual/trace-content review"}
        self.records.append(record)
        self.loaded[key] = (record, content)
        return record, content, path

    def json(self, ref):
        record, content, path = self.read(ref, text=True)
        if path.suffix.lower() != ".json":
            raise ValueError("Expected a saved JSON artifact.")
        return record, json.loads(content)

    def verify_unchanged(self):
        for (_, path), (record, _) in self.loaded.items():
            if not path.is_file() or path.stat().st_size > (TEXT_LIMIT if path.suffix.lower() in TEXT else BINARY_LIMIT):
                raise ValueError("Artifact changed before report publication.")
            limit = TEXT_LIMIT if path.suffix.lower() in TEXT else BINARY_LIMIT
            with path.open("rb") as handle:
                raw = handle.read(limit + 1)
            if len(raw) > limit or path.stat().st_mtime_ns != record["modified_at_ns"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
                raise ValueError("Artifact changed before report publication.")
