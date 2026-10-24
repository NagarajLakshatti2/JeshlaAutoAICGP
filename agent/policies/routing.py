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


def explicit_project_actions(question):
    """Recognize named project-only tools in the user's active request.

    Uploaded text is removed by the router first. A prohibition is not a request
    to execute the mentioned tool; the action still needs its normal approval.
    """
    from agent.policies.tool_registry import PROJECT_ACTIONS,CONVERSATION_ACTIONS
    active=re.sub(r"\b(?:do not|don't|never|without)\b[^.!?\n]*(?:[.!?\n]|$)"," ",question.casefold())
    return {name for name in PROJECT_ACTIONS-CONVERSATION_ACTIONS
            if re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",active)}


def is_saved_result_followup(question):
    """Discuss an existing result without mistaking prohibitions for new work.

    Positive requests to read, browse, edit or execute retain their normal
    routes. This only selects conversation; historical data grants no action.
    """
    if explicit_project_actions(question):return False
    text=question.casefold()
    active=re.sub(r"\b(?:do not|don't|never|without)\b[^.!?\n]*(?:[.!?\n]|$)"," ",text)
    if re.search(r"\b(?:online|internet|news|documentation|official|verify|validate|download)\b",active):
        return False
    if re.search(r"\b(?:run|execute|rerun|inspect|reinspect|reopen|open|visit|browse|search|fetch|read|create|write|edit|modify|replace|delete|connect|authenticate|install|upload|submit|approve|decline|fix|debug|repair)\b",active):
        return False
    return bool(re.search(
        r"\b(?:saved|previous|earlier|last|returned|completed|existing)\s+(?:(?:tool|browser|action|test)\s+)?(?:inspection|results?|reports?|output|observations?)\b"
        r"|\b(?:inspection|results?|reports?|output|observations?)\s+(?:you|we)\s+(?:just\s+)?(?:completed|returned|collected|produced)\b",
        active))
