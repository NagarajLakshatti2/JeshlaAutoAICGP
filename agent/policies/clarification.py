"""Bounded structural checks for explicit JSON conflict answers; not semantic truth."""
import json

def conflict_clarification_issue(content, known_refs):
    if not known_refs:
        return None
    try:
        answer=json.loads(content)
    except (ValueError,TypeError):
        return None
    if not isinstance(answer,dict) or answer.get("status")!="conflict":
        return None
    text=answer.get("answer")
    sources=answer.get("sources")
    if not isinstance(text,str) or not isinstance(sources,list):
        return "The JSON conflict answer needs an answer string and a sources array."
    refs={ref for ref in sources if isinstance(ref,str) and ref.startswith("[DOC-") and ref.endswith("]") and ref[1:-1] in known_refs}
    if len(refs)<2 or "?" not in text or any(ref not in text for ref in refs):
        return ("Revise the JSON conflict answer: name the different conflicting values from the returned excerpts, "
                "put each value beside its exact [DOC-id] in the answer string, and ask a focused question ending in ?. "
                "Keep the requested JSON fields and do not choose a winner. A generic conflict label is insufficient.")
    return None
