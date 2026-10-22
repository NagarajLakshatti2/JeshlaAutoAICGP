"""Bound memory-review evidence without cutting facts or JSON mid-record."""
import json


def bound_review_evidence(result, *, max_chars=8000):
    """Keep complete visible facts/pairs and explicit coverage limits.

    This shapes one tool response only. Stored facts, revisions and the input
    result are unchanged. Omitted records cannot establish absence or agreement.
    """
    if type(max_chars) is not int or max_chars < 256:
        raise ValueError("Evidence budget must be an integer of at least 256 characters.")

    def size(value):
        return len(json.dumps(value, ensure_ascii=False, default=str))

    if size(result) <= max_chars:
        return result
    failure = {
        "error": "Memory review could not fit complete evidence. Narrow the topic or select a specific saved fact before drawing conclusions.",
        "truncated": True,
    }
    if not isinstance(result, dict) or not isinstance(result.get("facts"), list):
        return failure
    payload = {
        **result,
        "facts": list(result["facts"]),
        "truncated": True,
        "note": str(result.get("note", "")) + " Some review results were omitted to fit this response. Narrow the query before drawing conclusions about missing facts or conflicts.",
    }
    pairs = result.get("candidate_pairs", [])
    if not isinstance(pairs, list):
        return failure
    while size(payload) > max_chars and payload["facts"]:
        payload["facts"].pop()
        visible = {
            fact["key"] for fact in payload["facts"]
            if isinstance(fact, dict) and isinstance(fact.get("key"), str)
        }
        payload["candidate_pairs"] = [
            pair for pair in pairs
            if isinstance(pair, dict) and isinstance(pair.get("keys"), list)
            and all(isinstance(key, str) and key in visible for key in pair["keys"])
        ]
    return payload if size(payload) <= max_chars else failure


def memory_key_issue(question, answer, visible_keys):
    """Check requested exact fact IDs; provenance references remain separate data.

    Only explicit exact-key requests with a structured sources field are in
    scope. Ordinary prose/source references and unrelated JSON are unchanged.
    Never guess a key by removing prefixes or rewriting model output.
    """
    import re
    if not visible_keys or not re.search(r"\bexact\s+(?:(?:saved|fact|memory)\s+){0,3}keys\b", question, re.I):
        return None
    text = answer.strip()
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip() in {"```json", "```"} and lines[-1].strip() == "```":
        text = "\n".join(lines[1:-1])
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or "sources" not in value:
        return None
    sources = value["sources"]
    if isinstance(sources, list) and all(isinstance(key, str) and key in visible_keys for key in sources):
        return None
    return ("The requested exact saved fact keys must come verbatim from the visible memory facts' key fields. "
            "metadata.source_ref identifies provenance, not a saved fact key; do not substitute it or construct namespace/key strings. "
            "Return the corrected response in the requested format using only visible fact keys. Do not change saved memory.")
