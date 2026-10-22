"""Read source features and Jira subtasks; suggest mappings without writing either."""
import argparse
import asyncio
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from agent.tools.feature_mapping import discover_feature_mappings


def normalize_title(value):
    return " ".join(str(value or "").casefold().split())


def subtask_verified(issue, query_verified_keys=()):
    raw_type = (issue.get("fields") or {}).get("issuetype")
    flag = raw_type.get("subtask") if isinstance(raw_type, dict) else None
    return flag is True or (flag is None and issue.get("key") in query_verified_keys)


def build_mapping_report(inventory, issues, query_verified_keys=()):
    """Exact normalized titles are suggestions only; only explicit tags map."""
    by_key = {issue["key"]: issue for issue in issues}
    by_title = {}
    for issue in issues:
        fields = issue.get("fields") or {}
        if subtask_verified(issue, query_verified_keys):
            title = normalize_title(fields.get("summary"))
            if title:
                by_title.setdefault(title, []).append(issue)

    def brief(issue):
        fields = issue.get("fields") or {}
        return {
            "key": issue["key"], "summary": fields.get("summary"),
            "parent_key": (fields.get("parent") or {}).get("key"),
            "status": (fields.get("status") or {}).get("name"),
            "issue_type": (fields.get("issuetype") or {}).get("name"),
            "subtask_verification_source": (
                "jira_jql_subtask_filter" if issue["key"] in query_verified_keys
                else "jira_issue_type_metadata"
            ),
        }

    rows = []
    for scenario in inventory["scenarios"]:
        row = dict(scenario)
        row.update(jira_subtask_verified=False, candidates=[], verification="unmapped")
        keys = row.get("jira_keys", [])
        if len(keys) > 1:
            row["verification"] = "ambiguous_tags"
        elif len(keys) == 1:
            issue = by_key.get(keys[0])
            if issue is None:
                row["verification"] = "not_found_in_eligible_scope"
            else:
                flag = ((issue.get("fields") or {}).get("issuetype") or {}).get("subtask")
                row["verification"] = (
                    "verified_subtask" if subtask_verified(issue, query_verified_keys) else
                    "not_a_subtask" if flag is False else "issue_type_unverified"
                )
                row["jira_subtask_verified"] = subtask_verified(issue, query_verified_keys)
                row["jira_issue"] = brief(issue)
        else:
            candidates = by_title.get(normalize_title(row["scenario"]), [])
            row["candidates"] = [brief(issue) for issue in candidates]
            if candidates:
                row["verification"] = (
                    "suggestion_needs_review" if len(candidates) == 1
                    else "ambiguous_candidates"
                )
        rows.append(row)
    return {
        "project_root": inventory["project_root"],
        "feature_files_scanned": inventory["feature_files_scanned"],
        "scenario_definitions": inventory["scenario_definitions"],
        "verified_tag_mappings": sum(r["jira_subtask_verified"] for r in rows),
        "scenarios_with_suggestions": sum(bool(r["candidates"]) for r in rows),
        "unresolved": sum(not r["jira_subtask_verified"] for r in rows),
        "scenarios": rows,
        "note": (
            "Read-only. Titles produce review suggestions, never automatic mappings. "
            "Verified means an explicit tag identifies an existing subtask; it does not "
            "prove scenario coverage or execution. No Jira or feature files were changed."
        ),
    }


def classify_issues(issues, work_status, query_verified_keys=()):
    """Keep unknown metadata distinct from false; never infer type from names."""
    eligible, excluded, blocked, summaries = [], [], [], []
    for issue in issues:
        fields = issue.get("fields") or {}
        raw_type = fields.get("issuetype")
        raw_status = fields.get("status")
        raw_parent = fields.get("parent")
        issue_type = raw_type if isinstance(raw_type, dict) else {}
        status = raw_status.get("name") if isinstance(raw_status, dict) else None
        flag = issue_type.get("subtask")
        flag = flag if type(flag) is bool else None
        summaries.append({
            "key": issue.get("key"), "summary": fields.get("summary"),
            "status": status, "issue_type": issue_type.get("name"),
            "is_subtask": flag,
            "subtask_verified": subtask_verified(issue, query_verified_keys),
            "subtask_verification_source": (
                "jira_jql_subtask_filter" if issue.get("key") in query_verified_keys
                else "jira_issue_type_metadata" if flag is True else None
            ),
            "parent_key": raw_parent.get("key") if isinstance(raw_parent, dict) else None,
        })
        reason = None
        if not isinstance(status, str) or not status.strip():
            reason = "Status metadata missing or unsupported"
        elif normalize_title(status) != normalize_title(work_status):
            excluded.append({"key": issue["key"], "reason": "Outside configured work status", "status": status})
            continue
        elif flag is False and issue["key"] in query_verified_keys:
            reason = "Jira subtask-filter membership conflicts with returned issue-type metadata"
        elif flag is False:
            excluded.append({"key": issue["key"], "reason": "Not a subtask", "status": status})
            continue
        elif not subtask_verified(issue, query_verified_keys):
            reason = "No verified Jira subtask evidence"
        elif not isinstance(fields.get("summary"), str) or not fields["summary"].strip():
            reason = "Summary missing or unsupported"
        if reason:
            blocked.append({
                "key": issue["key"], "reason": reason,
                "returned_field_names": sorted(fields),
                "issue_type_field_names": sorted(issue_type),
                "issue_type_value_type": type(raw_type).__name__,
                "status_value_type": type(raw_status).__name__,
            })
        else:
            eligible.append(issue)
    return eligible, excluded, blocked, summaries


async def discover_jira_mappings(project_root, project_key, max_pages=100):
    from integrations.jira.jira_mcp_client import (
        jira_session, get_cloud_id, search_jira_issues, get_jira_issue,
    )
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", project_key or ""):
        raise ValueError("JIRA_PROJECT_KEY must be a project key, not a URL or issue key.")
    work_status = os.getenv("JIRA_WORK_STATUS", "").strip()
    if not work_status:
        raise ValueError("Set JIRA_WORK_STATUS in .env to the exact Jira status name.")
    inventory = discover_feature_mappings(project_root, limit=5000)
    if inventory["errors"] or inventory["details_truncated"]:
        raise ValueError("Feature inventory is incomplete: " + json.dumps(inventory["errors"]))
    jql = (
        f'project = "{project_key}" '
        f'AND status = {json.dumps(work_status, ensure_ascii=False)} '
        f'AND workType IN subtaskWorkTypes() '
        f'ORDER BY key ASC'
    )
    print("Subtask verification: Jira JQL subtaskWorkTypes()")
    requested_fields = ["summary", "issuetype", "parent", "status"]
    async with jira_session() as session:
        cloud_id = await get_cloud_id(session)
        issues = await search_jira_issues(
            session, cloud_id, jql, max_pages=max_pages, fields=requested_fields,
        )
        # Evidence is scoped to keys returned by this exact completed Jira query.
        # It is not derived from names, local files, or model output.
        query_verified_keys = frozenset(issue["key"] for issue in issues)
        for index, issue in enumerate(issues):
            fields = issue.get("fields") or {}
            issue_type = fields.get("issuetype")
            status = fields.get("status")
            metadata_complete = (
                isinstance(status, dict)
                and isinstance(status.get("name"), str)
                and bool(status["name"].strip())
                and isinstance(fields.get("summary"), str)
                and bool(fields["summary"].strip())
            )
            if not metadata_complete:
                print(f"Reading requested metadata for {issue['key']}...")
                # Replace search data; do not fill absent fields with stale data.
                issues[index] = await get_jira_issue(
                    session, cloud_id, issue["key"], fields=requested_fields,
                )

    eligible, excluded, blocked, summaries = classify_issues(issues, work_status, query_verified_keys)
    if eligible:
        report = build_mapping_report(inventory, eligible, query_verified_keys)
        discovery_status = "partial_metadata" if blocked else "ready_for_mapping_review"
    else:
        # Inventory is discovery evidence, not an automation backlog.
        report = build_mapping_report({**inventory, "scenarios": []}, [])
        discovery_status = "blocked_metadata" if blocked else "no_eligible_work"
    report.update(
        discovery_status=discovery_status,
        mapping_evaluated=bool(eligible),
        work_status=work_status,
        eligible_issue_count=len(eligible),
        excluded_issues=excluded,
        metadata_blocked_issues=blocked,
        jira_issue_inventory=summaries,
        jira_project_key=project_key,
        jira_issues_read=len(issues),
        jql=jql,
        subtask_verification_source="jira_jql_subtask_filter",
        coverage_note=(
            "Search covers all reported pages of visible issues in the selected project "
            "and configured work status, filtered by Jira subtaskWorkTypes(). "
            "Subtask evidence comes from membership in that server-filtered result, not "
            "an invented metadata flag. Missing display type/parent remains null. Status "
            "is rechecked; conflicting issue-type metadata blocks eligibility. "
            "Absent keys may exist outside this scope. Local unmapped scenarios do not "
            "authorize automation. No Jira, source, or status changes were made."
        ),
    )
    return report


def main():
    from agent.config.paths import DATA_ROOT
    load_dotenv(DATA_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.getenv("AI_PROJECT_ROOT"))
    parser.add_argument("--project", default=os.getenv("JIRA_PROJECT_KEY"))
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    if not args.root or not args.project:
        parser.error("Set AI_PROJECT_ROOT and JIRA_PROJECT_KEY in .env, or use --root and --project.")
    try:
        result = asyncio.run(discover_jira_mappings(args.root, args.project, args.max_pages))
    except Exception as error:
        # Avoid dumping OAuth callback URLs or credentials from nested exceptions.
        print(f"Jira discovery did not complete ({type(error).__name__}). No mapping result was confirmed.")
        raise SystemExit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
