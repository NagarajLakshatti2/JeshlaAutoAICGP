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

def git_write_mode(question):
    """Find an explicit publication instruction in the user's active text."""
    from agent.runtime.input_evidence import split_uploaded_input
    text=split_uploaded_input(question)[0].strip().casefold()
    normalized=text.lstrip(" \t\n“”‘’'\"`-*•")
    if re.match(r"^(?:why|what|how|explain|can i|could i|did you|have you)\b",normalized):return None
    active=re.sub(r"\b(?:do not|don't|never|without)\b[^.!?\n]*(?:[.!?\n]|$)"," ",text)
    # File creation is a preceding action, with a separate review for publication.
    if re.search(r"\b(?:create|reate|add|write|save)\b",active) and re.search(r"\b(?:file|script)\b|\.\w{1,8}\b",active):return None
    pattern=r"(?:^|[\n.!?;“”‘’'\"`])\s*(?:(?:please|can you|could you|would you)\s+)?(?:git\s+)?(commit|push)\b"
    actions={match.group(1) for match in re.finditer(pattern,active)}
    actions.update(re.findall(r"\bgit\s+(commit|push)\b",active))
    if "commit" in actions:return "Commit"
    if "push" in actions:return "Push"
    return None


def is_git_write_request(question):
    return git_write_mode(question) is not None


def is_project_change_request(question):
    from agent.runtime.input_evidence import split_uploaded_input
    text=split_uploaded_input(question)[0].strip().casefold()
    if re.match(r"^(?:why|what|how|explain|did you|have you)\b",text):return False
    active=re.sub(r"\b(?:do not|don't|never|without)\b[^.!?\n]*(?:[.!?\n]|$)"," ",text)
    write=re.search(r"\b(?:create|reate|add|write|save|edit|replace|modify)\b",active)
    file=re.search(r"\b(?:files?|scripts?|project root)\b|[\w-]+\.(?:py|java|js|ts|json|md|txt|feature)\b",active)
    return bool(write and file) or is_git_write_request(question)
