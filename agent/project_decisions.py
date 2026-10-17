"""Obtain a project action through registered native tools; never execute it here."""
import json
from agent.tool_llm import call_tool_messages
from agent.llm_client import env_int


def call_project_decision(messages, actions):
    allowed = sorted(set(actions) | {"ask", "finish"})
    spec = {"type":"function","function":{
        "name":"submit_project_action",
        "description":"Propose exactly one local project action for validation. This function itself executes nothing. Use ask for clarification, finish for an evidence-based answer, or an allowed action with arguments.",
        "parameters":{"type":"object","properties":{
            "action":{"type":"string","enum":allowed},
            "arguments":{"type":"object","additionalProperties":True},
            "question":{"type":"string"},"answer":{"type":"string"}},
            "required":["action"],"additionalProperties":False}}}
    instruction={"role":"system","content":
        "Use only the registered submit_project_action function to propose one action. "
        "Names such as read_file and list_files in the instructions are action values, "
        "not independently callable functions. Do not execute actions yourself."}
    reply=call_tool_messages([instruction,*messages],[spec],
                             max_tokens=env_int("AI_PROJECT_MAX_TOKENS",4096,64,16384))
    calls=reply.get("tool_calls") or []
    if not calls and isinstance(reply.get("content"),str) and reply["content"].strip():
        # Final text is not an executable action. The project loop still verifies
        # inspected evidence and requested-file coverage before accepting finish.
        text=reply["content"].strip()
        try:
            proposal=json.loads(text)
        except ValueError:
            return json.dumps({"action":"finish","answer":text},ensure_ascii=False)
        if not isinstance(proposal,dict) or "action" not in proposal:
            return json.dumps({"action":"finish","answer":text},ensure_ascii=False)
        # Some providers return the requested action JSON as text instead of a
        # native call. Validate it below; never display an action as a final answer.
        calls=[{"function":{"name":"submit_project_action","arguments":text}}]
    if len(calls)!=1 or calls[0].get("function",{}).get("name")!="submit_project_action":
        raise RuntimeError("Expected one registered project-action proposal; no action was executed.")
    try:
        decision=json.loads(calls[0]["function"]["arguments"])
        if not isinstance(decision,dict) or set(decision)-{"action","arguments","question","answer"}:
            raise ValueError()
        if decision.get("action") not in allowed or not isinstance(decision.get("arguments",{}),dict):
            raise ValueError()
        if any(key in decision and not isinstance(decision[key],str) for key in ("question","answer")):
            raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise RuntimeError("Invalid project-action proposal; no action was executed.") from None
    return json.dumps(decision,ensure_ascii=False)
