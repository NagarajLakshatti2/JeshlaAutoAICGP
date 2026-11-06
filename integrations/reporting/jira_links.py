"""Join saved execution cases to explicitly tagged, verified Jira subtasks."""


def resolve_case_jira_link(case, mapping_report, mapping_evidence_id):
    """Resolve an explicit case→scenario→Jira link; never infer by title.

    The Jira mapping report is loaded from a hash-checked saved evidence ref by
    the caller. Its explicit feature tag and verified-subtask flag are required.
    """
    jira_key = case.get("jira_key")
    scenario = case.get("jira_scenario")
    if not jira_key and not scenario:
        return {"status": "missing", "jira_key": None, "scenario": None,
                "mapping_evidence_id": mapping_evidence_id, "issue": None}
    if not isinstance(jira_key, str) or not isinstance(scenario, str):
        raise ValueError("A Jira link requires both jira_key and jira_scenario text.")
    import re
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*-[1-9][0-9]*", jira_key) or not scenario.strip() or len(scenario) > 200:
        raise ValueError("Use a valid Jira issue key and a bounded exact scenario title.")

    matches = [row for row in mapping_report["scenarios"]
               if row.get("scenario") == scenario and row.get("jira_keys") == [jira_key]]
    verified = [row for row in matches
                if row.get("verification") == "verified_subtask"
                and row.get("jira_subtask_verified") is True
                and (row.get("jira_issue") or {}).get("key") == jira_key]
    if len(verified) == 1:
        issue = verified[0]["jira_issue"]
        return {"status": "verified_explicit_tag", "jira_key": jira_key,
                "scenario": scenario, "mapping_evidence_id": mapping_evidence_id,
                "issue": {"key": issue.get("key"), "summary": issue.get("summary"),
                          "status": issue.get("status")}}
    return {"status": "unverified", "jira_key": jira_key, "scenario": scenario,
            "mapping_evidence_id": mapping_evidence_id, "issue": None}
