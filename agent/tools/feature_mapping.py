"""Discover source Gherkin scenarios and explicit Jira tags; never update Jira."""
import argparse
import json
import os
import re
from pathlib import Path
from agent.tools.project_tools import ProjectTools

DEFAULT_JIRA_TAG_PATTERN = r"@([A-Z][A-Z0-9_]*-\d+)"


def discover_feature_mappings(project_root, limit=500, jira_tag_pattern=None):
    if type(limit) is not int or not 1 <= limit <= 5000:
        raise ValueError("limit must be between 1 and 5000.")
    tools = ProjectTools(project_root)
    pattern = re.compile(jira_tag_pattern or os.getenv("JIRA_TAG_PATTERN", DEFAULT_JIRA_TAG_PATTERN))
    if pattern.groups != 1:
        raise ValueError("JIRA_TAG_PATTERN must have exactly one capturing group for the Jira key.")
    scenarios, errors = [], []
    files_scanned = 0
    for path in tools._files(tools.root):
        if path.suffix.lower() != ".feature":
            continue
        files_scanned += 1
        relative = path.relative_to(tools.root).as_posix()
        if path.stat().st_size > 1_000_000:
            errors.append({"file": relative, "error": "Feature exceeds 1 MB."})
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (UnicodeError, OSError) as error:
            errors.append({"file": relative, "error": str(error)})
            continue
        feature_name, feature_tags, rule_tags, pending = "", [], [], []
        in_docstring = None
        for line_number, raw in enumerate(lines, 1):
            line = raw.strip()
            if in_docstring:
                if line.startswith(in_docstring):
                    in_docstring = None
                continue
            if line.startswith(('"""', "```")):
                in_docstring = line[:3]
                continue
            if not line or line.startswith("#"):
                if line.startswith("# language:") and line.split(":", 1)[1].strip() != "en":
                    errors.append({"file": relative, "error": "Non-English Gherkin is not supported by this inventory."})
                    break
                continue
            if line.startswith("@"):
                pending.extend(token for token in line.split() if token.startswith("@"))
                continue
            if line.startswith("Feature:"):
                feature_name = line.split(":", 1)[1].strip()
                feature_tags, rule_tags = pending, []
                pending = []
                continue
            if line.startswith("Rule:"):
                rule_tags, pending = pending, []
                continue
            match = re.match(r"^(Scenario Outline|Scenario Template|Scenario|Example):\s*(.*)$", line)
            if match:
                tags = list(dict.fromkeys([*feature_tags, *rule_tags, *pending]))
                pending = []
                keys = sorted({m.group(1) for tag in tags if (m := pattern.fullmatch(tag))})
                status = "mapped" if len(keys) == 1 else "ambiguous" if keys else "unmapped"
                scenarios.append({"file": relative, "line": line_number, "feature": feature_name,
                                  "scenario": match.group(2), "kind": match.group(1), "tags": tags,
                                  "jira_keys": keys, "mapping_status": status,
                                  "jira_subtask_verified": False})
                continue
            if line.startswith(("Examples:", "Scenarios:")) and pending:
                errors.append({"file": relative, "line": line_number,
                               "error": "Examples-level tags require row-level mapping; not included in this scenario inventory."})
            pending = []
    counts = {status: sum(s["mapping_status"] == status for s in scenarios) for status in ("mapped", "unmapped", "ambiguous")}
    return {"project_root": str(tools.root), "feature_files_scanned": files_scanned,
            "scenario_definitions": len(scenarios), **counts, "scenarios": scenarios[:limit],
            "details_truncated": len(scenarios) > limit, "errors": errors,
            "note": "Mapping comes only from explicit tags. No title matching or guessed keys. Jira issue types are not verified and no issues are changed. Outlines count as definitions, not executed example rows. Feature/Rule tags are inherited; more than one distinct Jira key is ambiguous."}


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.getenv("AI_PROJECT_ROOT"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--jira-tag-pattern", default=None)
    args = parser.parse_args()
    if not args.root:
        parser.error("Set AI_PROJECT_ROOT or supply --root.")
    print(json.dumps(discover_feature_mappings(args.root, args.limit, args.jira_tag_pattern), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
