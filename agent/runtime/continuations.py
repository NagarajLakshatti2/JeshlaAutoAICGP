"""Text-only continuation state and controls shared by console/browser turns."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
import re
from uuid import uuid4

from agent.providers.errors import ProviderError
from agent.policies.answer_quality import syntax_issue, needs_reference_review, automatic_verification
from agent.policies.citations import citation_issue

_writer = ContextVar("answer_progress_writer", default=None)
_origin = ContextVar("answer_progress_origin", default="")


def command(question):
    text = " ".join(question.strip().casefold().rstrip(".!?").split())
    if text in {"continue", "/continue", "continue answer", "/continue answer", "resume answer"}: return "continue"
    if text in {"full answer", "show full answer", "consolidate answer"}: return "full"
    if text == "cancel answer": return "cancel"
    return None


def explicit_command(question):
    return command(question) is not None and question.strip().casefold().rstrip(".!?") != "continue"


@contextmanager
def progress_scope(question, writer):
    previous = _writer.set(writer); origin = _origin.set(question)
    try: yield
    finally:
        _origin.reset(origin); _writer.reset(previous)


def plain_context(messages):
    return (isinstance(messages, list) and 0 < len(messages) <= 64 and all(
        isinstance(item, dict) and set(item) == {"role", "content"}
        and item["role"] in {"system", "user", "assistant"}
        and isinstance(item["content"], str) for item in messages))


def section_issue(content, question):
    if not isinstance(content, str) or not content.strip(): return "Section is empty."
    opened = None
    for line in content.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if not match: continue
        fence, rest = match.groups()
        if opened is None: opened = fence
        elif fence[0] == opened[0] and len(fence) >= len(opened) and not rest.strip(): opened = None
    if opened is not None: return "Section contains an unfinished code fence."
    issue = syntax_issue(content) or citation_issue(content, set())
    if issue: return issue
    if needs_reference_review(question, content) or (automatic_verification() and re.search(r"(?m)^ {0,3}(?:`{3,}|~{3,})",content)):
        return "This section requires technical source review; text continuation cannot bypass it."
    return None


def content_identity(content):
    # Code case, indentation and blank lines can be significant.
    return content.strip() if "```" in content or "~~~" in content else " ".join(content.split()).casefold()


def validate_ledger(value):
    keys = {"version", "id", "origin_question", "outline", "messages", "completed", "status", "published"}
    if not isinstance(value, dict) or set(value) != keys or type(value["version"]) is not int or value["version"] != 1: raise ValueError("Invalid answer continuation version.")
    if not isinstance(value["id"], str) or not re.fullmatch(r"[a-f0-9]{32}", value["id"]): raise ValueError("Invalid continuation identity.")
    if not isinstance(value["origin_question"], str) or not value["origin_question"].strip(): raise ValueError("Missing original question.")
    if not plain_context(value["messages"]): raise ValueError("Continuation is not a plain text context.")
    if sum(len(item["content"]) for item in value["messages"]) > 200000: raise ValueError("Continuation context exceeds its bound.")
    plan = value["outline"]
    if not isinstance(plan, dict) or set(plan) != {"mode", "title", "scope", "sections"} or plan["mode"] != "answer": raise ValueError("Invalid text outline.")
    if not all(isinstance(plan[key], str) and 0 < len(plan[key].strip()) <= 240 for key in ("title", "scope")): raise ValueError("Invalid outline title/scope.")
    if not isinstance(plan["sections"], list) or not 2 <= len(plan["sections"]) <= 6: raise ValueError("Invalid section count.")
    names = set()
    for part in plan["sections"]:
        if not isinstance(part, dict) or set(part) != {"title", "purpose"} or not all(isinstance(text, str) and 0 < len(text.strip()) <= 240 for text in part.values()): raise ValueError("Invalid section outline.")
        title = " ".join(part["title"].split()).casefold()
        if title in names or "\n" in part["title"] or "\r" in part["title"]: raise ValueError("Repeated/invalid section title.")
        names.add(title)
    completed = value["completed"]
    if not isinstance(completed, list) or len(completed) > len(plan["sections"]): raise ValueError("Invalid completed cursor.")
    bodies = set()
    for index, section in enumerate(completed, 1):
        if (not isinstance(section, dict) or set(section) != {"section_id", "content", "covered_points", "complete"}
                or section["section_id"] != "section-" + str(index) or section["complete"] is not True): raise ValueError("Noncontiguous or incomplete section.")
        if not isinstance(section["content"], str) or len(section["content"]) > 200000 or section_issue(section["content"], value["origin_question"]): raise ValueError("Unvalidated section content.")
        body = content_identity(section["content"])
        if body in bodies: raise ValueError("Duplicate completed section.")
        bodies.add(body)
        points = section["covered_points"]
        if not isinstance(points, list) or len(points) > 8 or any(not isinstance(item, str) or not item.strip() or len(item) > 240 for item in points): raise ValueError("Invalid covered points.")
    if sum(len(section["content"]) for section in completed) > 200000: raise ValueError("Completed text exceeds its bound.")
    if type(value["published"]) is not int or not 0 <= value["published"] <= len(completed): raise ValueError("Invalid publication cursor.")
    expected = "complete" if len(completed) == len(plan["sections"]) else "pending"
    if value["status"] != expected: raise ValueError("Continuation status disagrees with its cursor.")
    return value


def make_ledger(messages, plan, completed=None, *, identity=None, question=None, published=0):
    origin = question or _origin.get() or next((item["content"] for item in reversed(messages) if item["role"] == "user"), "")
    completed = deepcopy(completed or [])
    value = {"version": 1, "id": identity or uuid4().hex, "origin_question": origin,
             "outline": deepcopy(plan), "messages": deepcopy(messages), "completed": completed, "published": published,
             "status": "complete" if len(completed) == len(plan["sections"]) else "pending"}
    return validate_ledger(value)


def save_progress(value):
    validate_ledger(value)
    writer = _writer.get()
    if writer is None: return False
    try: writer(deepcopy(value))
    except Exception:
        raise ProviderError("model", "CONTINUATION_SAVE", "Completed-answer progress could not be saved. The uncommitted section was held back; no action was replayed.") from None
    return True


def full_result(ledger):
    from agent.runtime.long_answers import render_answer
    validate_ledger(ledger)
    content = render_answer(ledger["outline"], ledger["completed"])
    pending = ledger["status"] == "pending"
    if not ledger["completed"]: content = "The outline is saved, but no complete answer section is available yet."
    if pending: content += "\n\nPartial answer: remaining sections are not complete."
    return {"answer": content, "route": "direct", "task_status": "incomplete" if pending else "completed",
            "answer_available": bool(ledger["completed"]), "execution_outcome": "partial" if pending and ledger["completed"] else "blocked" if pending else "completed"}


def resume_result(ledger, model):
    from agent.runtime.long_answers import compose_long_answer
    validate_ledger(ledger)
    if ledger["status"] == "complete":
        if ledger["published"] < len(ledger["completed"]):
            from agent.runtime.long_answers import render_answer
            return {"answer": render_answer(ledger["outline"], ledger["completed"], start=ledger["published"]),
                    "route": "direct", "execution_outcome": "completed", "task_status": "completed", "answer_available": True}
        return {"answer": "This answer is already complete. Type FULL ANSWER to view the consolidated result.", "route": "direct", "execution_outcome": "completed", "task_status": "completed"}
    reply = compose_long_answer(ledger["messages"], model, failed_provider="", allow_partial=True, resume=ledger)
    partial = bool(reply.get("composition", {}).get("partial"))
    return {"answer": reply["content"], "route": "direct", "task_status": "incomplete" if partial else "completed",
            "answer_available": bool(reply.get("composition", {}).get("new_sections")),
            "execution_outcome": "partial" if partial else "completed"}
