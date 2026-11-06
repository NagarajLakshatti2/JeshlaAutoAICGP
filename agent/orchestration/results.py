"""Consolidate specialist outcomes into one evidence-linked coordinator result."""


def consolidate(branches, *, evidence_by_capability=None):
    """Return one answer envelope; unsupported and incomplete branches stay visible.

    Completed branches provide claims as strings. Evidence references are
    supplied separately by the host, keyed by capability; specialists cannot
    establish evidence provenance by returning arbitrary strings.
    """
    if not isinstance(branches, (list, tuple)):
        raise ValueError("Coordinator branches must be a list.")
    evidence_by_capability = evidence_by_capability or {}
    if not isinstance(evidence_by_capability, dict):
        raise ValueError("Host evidence must be mapped by capability.")
    claims = []
    incomplete = []
    seen = set()
    for index, branch in enumerate(branches):
        if not isinstance(branch, dict):
            raise ValueError("Each coordinator branch must be an object.")
        status = branch.get("status")
        capability = branch.get("capability", "unknown")
        if status != "completed":
            incomplete.append({"capability": capability, "status": status or "incomplete",
                               "message": branch.get("message", "Branch did not complete.")})
            continue
        branch_claims = branch.get("claims", [])
        refs = evidence_by_capability.get(capability, [])
        if not isinstance(branch_claims, list) or not isinstance(refs, (list, tuple)):
            raise ValueError("Claims and host evidence references must be lists.")
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError("Evidence references must be non-empty strings.")
        refs = list(dict.fromkeys(refs))
        for claim in branch_claims:
            if not isinstance(claim, str) or not claim.strip():
                raise ValueError("Claims must be non-empty strings.")
            key = claim.strip()
            if not refs:
                incomplete.append({"capability": capability, "status": "missing_evidence",
                                   "message": "A specialist claim had no host-recorded evidence reference."})
                continue
            if key in seen:
                continue
            seen.add(key)
            claims.append({"text": key, "capability": capability,
                           "evidence_refs": refs})
    answer = "\n".join(item["text"] for item in claims)
    return {"status": "incomplete" if incomplete else "completed",
            "answer": answer, "claims": claims, "incomplete_branches": incomplete}
