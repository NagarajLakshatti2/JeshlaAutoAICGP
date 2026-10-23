"""Identify conversation-history requests without treating recency as news."""
import re


def is_history_request(question):
    text=question.lower()
    # Explicit external searches still take their normal route.
    if re.search(r"\b(?:search (?:the web|online)|internet search|online|news|documentation)\b",text):
        return False
    scope=re.search(r"\b(?:this|our|my|previous|last|current) (?:chat|conversation|session)\b",text)
    personal=re.search(r"\b(?:my (?:latest|last|previous) (?:message|question|request)|(?:did|have) i (?:ask|say|request|tell|mention))\b",text)
    recall=re.search(r"\b(?:message|question|request|asked|said|discussed|told|remember|recall|summary|summarize)\b",text)
    return bool(personal or (scope and recall))


def is_local_observation_request(question):
    """Saved observation analysis does not authorize an authenticated Jira workflow."""
    from agent.runtime.input_evidence import explicit_jira_request
    if explicit_jira_request(question):
        return False
    if re.search(r"\bdraft_test_observations\b", question, re.I):
        return True
    analysis = re.match(r"^(?:please\s+)?(?:read|review|inspect|compare|analy[sz]e|summari[sz]e|draft|prepare|report|explain)\b", question.strip(), re.I)
    return bool(analysis and re.search(r"\bobservations?\b|\b(?:actual|observed) results?\b|\bdefect drafts?\b", question, re.I))
