"""Conservative tool-free teaching scope; no topic-specific canned answers."""
import re

_SOURCE = re.compile(
    r"\b(?:my|our|project|repository|repo|codebase|files?|folders?|paths?|documents?|docs|sources?|"
    r"web|online|internet|search|browse|documentation|official|cite|citations?|references?|links?|articles?|papers?|books?|handbook|evidence|latest|current|today|live|verify|check|saved|memory|"
    r"remember|history|previous|earlier|archive|chat|uploads?|uploaded|attachments?|indexed)\b"
    r"|https?://|[A-Za-z]:[\\/]|\b[\w-]+\.(?:java|py|pdf|docx?|xlsx?|csv|md)\b", re.I)
_LEARNING = re.compile(
    r"\b(?:explain|define|definition|concepts?|examples?|tutorial|learn|learning|teach|"
    r"advantages?|disadvantages?|limitations?|differences?)\b"
    r"|\bwhat\s+(?:is|are)\b|\b(?:list|cover|include)\b.*\b(?:points|topics|rules|concepts|checklist)\b", re.I | re.S)

def knowledge_only(state, question, *, has_upload=False):
    """Unknown/ambiguous requests retain tools; explicit evidence always wins.

    Follow-up context is checked conservatively so an earlier source task cannot
    silently turn into an unsupported general answer. No language/topic names
    or answer values are hardcoded.
    """
    if has_upload or state.get("route", "direct") != "direct" or _SOURCE.search(question):
        return False
    history = state.get("history", "")[-4000:]
    user_turns = re.findall(r"(?:^|\n)User: (.*?)(?=\nAssistant:|$)", history, re.S)
    # Assistant errors such as "specify the source" are not user evidence
    # requests, and must not poison a retry of the same learning question.
    context = "\n".join(user_turns[-2:]) if user_turns else history
    previous = state.get("previous_exchange")
    if isinstance(previous, dict) and isinstance(previous.get("question"), str):
        context += "\n" + previous["question"]
    context += "\n" + state.get("summary", "")[-5000:]
    learning = bool(_LEARNING.search(question))
    return learning and not _SOURCE.search(context)


_FOLLOWUP = re.compile(r"\b(?:this|that|these|those|it|same|again|above|below|continue|previous|earlier)\b", re.I)


def standalone_learning_request(question):
    """Recognize an explicit public learning request without borrowing source scope.

    Earlier private/source tasks must not turn a fresh general explanation into
    a repository inspection. Deictic follow-ups retain their scoped context.
    """
    return bool(_LEARNING.search(question) and not _SOURCE.search(question) and not _FOLLOWUP.search(question))


_PRIVATE_SCOPE = re.compile(r"\b(?:my|our|project|repository|repo|codebase|files?|folders?|paths?|saved|memory|chat|uploads?|uploaded|attachments?|indexed)\b|https?://|[A-Za-z]:[\\/]|\b[\w-]+\.(?:java|py|pdf|docx?|xlsx?|csv|md)\b", re.I)
_EXPLICIT_REFERENCE = re.compile(r"\b(?:verify|verified|verification|official|documentation|sources?|citations?|cite|references?|search|browse|online|web|internet|latest|current|today|live)\b", re.I)
_PREVIOUS_RESPONSE = re.compile(r"\b(?:previous|last|preceding|above)\s+(?:answer|reply|response|explanation)\b|\byour\s+(?:answer|reply|response)\b", re.I)


def public_learning_request(question):
    """Include explicit public documentation tasks; exclude private/source files."""
    return bool(_LEARNING.search(question) and not _PRIVATE_SCOPE.search(question) and not _FOLLOWUP.search(question))


def explicit_reference_request(question):
    return bool(_EXPLICIT_REFERENCE.search(question))


def previous_response_request(question):
    return bool(_PREVIOUS_RESPONSE.search(question))
