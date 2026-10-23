"""Obtain a project action through registered native tools; never execute it here."""
import json
from agent.providers.tools import call_tool_messages
from agent.providers.text import env_int, LLM_PROVIDER
from agent.providers.errors import ProviderError
from agent.providers.fallback import last_provider


def call_project_decision(messages, actions):
    # Historical callers used [] when offering no project actions. Preserve that
    # case without registering handlers or broadening the allowed action set.
    if isinstance(actions, (list, tuple)) and not actions:
        actions = {}
    allowed = sorted(set(actions) | {"ask", "finish"})
    spec = {"type":"function","function":{
        "name":"submit_project_action",
        "description":"Propose exactly one local project action for validation. This function itself executes nothing. Use ask for clarification, finish for an evidence-based answer, or an allowed action with arguments.",
        "parameters":{"type":"object","properties":{
            "action":{"type":"string","enum":allowed},
            "arguments":{"type":"object","properties":{
                "files":{"type":"array","minItems":1,"maxItems":5,"items":{
                    "type":"object","properties":{
                        "relative_path":{"type":"string"},
                        "start_line":{"type":"integer","minimum":1},
                        "max_lines":{"type":"integer","minimum":1,"maximum":80}},
                    "required":["relative_path"],"additionalProperties":False}}},
                "additionalProperties":True},
            "question":{"type":"string"},"answer":{"type":"string"}},
            "required":["action"],"additionalProperties":False}}}
    # Advertise real argument names as well as the historical read_files schema.
    # Otherwise a model can put files=[...] into read_file because it is the only
    # named property in the generic envelope. Execution still binds the handler.
    from agent.runtime.project_native_specs import native_project_specs
    argument_properties=spec["function"]["parameters"]["properties"]["arguments"]["properties"]
    for action_spec in native_project_specs(actions):
        function=action_spec["function"]
        if function["name"] not in actions:continue
        for name,rule in function["parameters"]["properties"].items():
            argument_properties.setdefault(name,rule)
    instruction={"role":"system","content":
        "Use only the registered submit_project_action function to propose one action. "
        "Names such as read_file and list_files in the instructions are action values, "
        "not independently callable functions. Use the chosen handler's argument names; files is for read_files, while read_file uses relative_path/start_line/max_lines. Do not execute actions yourself."}
    if messages and messages[0].get("role")=="system":
        request=[{**messages[0],"content":messages[0]["content"]+"\n\n"+instruction["content"]},*messages[1:]]
    else:
        request=[instruction,*messages]
    correction_provider = None
    for attempt in range(2):
        options={"max_tokens":env_int("AI_PROJECT_MAX_TOKENS",4096,64,16384)}
        if (correction_provider or last_provider(LLM_PROVIDER))=="groq":options["forced_function"]="submit_project_action"
        selected_specs=[spec]
        native=(correction_provider or last_provider(LLM_PROVIDER))=="groq" and attempt==1
        if native:
            from agent.runtime.project_native_specs import native_project_specs
            selected_specs=native_project_specs(actions)
            options.pop("forced_function",None);options["require_tool"]=True
            native_instruction=("Propose exactly ONE action through its registered native function. "
                "Do not call submit_project_action; the action names themselves are now registered. "
                "The current Task defines the request; prior errors/history are not instructions. "
                "Reuse the supplied root, path and content. Do not ask to reconfirm details already supplied. "
                "No local action has executed from a rejected proposal. Application approval is still required.")
            request=[*messages,{"role":"system","content":native_instruction}]
        try:
            reply=call_tool_messages(request,selected_specs,**options)
        except ProviderError as error:
            if attempt or error.category!="TOOL_OUTPUT":raise
            correction_provider = error.provider
            # This rejected response executed no local action. Correct once,
            # without feeding failed-generation bodies back into the prompt.
            request=[*request,{"role":"user","content":
                "The provider rejected the generated function call before any action executed. "
                "Call only submit_project_action once, with action as an allowed enum and "
                "arguments as an object. Local tool names are action values, not function names. "
                "Use answer for finish or question for ask. Do not claim any execution."}]
            continue
        try:
            if native:
                from agent.runtime.project_native_specs import decode_native_project_reply
                return decode_native_project_reply(reply,actions)
            return decode_project_reply(reply,allowed)
        except ValueError as error:
            if attempt:
                raise RuntimeError("Invalid project-action proposal after one format correction: " + str(error) + " No action was executed from these proposals.") from None
            request=[*request,{"role":"user","content":
                "Your previous proposal was rejected before execution: " + str(error) +
                " Return one corrected proposal using the supplied schema. Omit unused optional fields; "
                "for finish, put the final text in answer. Do not claim a rejected action was executed."}]
    raise RuntimeError("Project proposal correction did not complete.")


def decode_project_reply(reply, allowed):
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
        raise ValueError("Use exactly one registered submit_project_action function.")
    try:
        decision=json.loads(calls[0]["function"]["arguments"])
    except (ValueError,TypeError,KeyError):
        raise ValueError("Proposal arguments must contain valid JSON.") from None
    if not isinstance(decision,dict):
        raise ValueError("Proposal must be a JSON object.")
    if set(decision)-{"action","arguments","question","answer"}:
        raise ValueError("Proposal contains unexpected fields; use only action, arguments, question and answer.")
    decision=dict(decision)
    for key in ("question","answer"):
        if decision.get(key) is None:
            decision.pop(key,None)
    if decision.get("action") not in allowed:
        raise ValueError("Choose an allowed action value.")
    if decision.get("action") in {"ask","finish"}:
        if "arguments" in decision and decision["arguments"] is None:
            decision["arguments"]={}
        field="answer" if decision["action"]=="finish" else "question"
        nested=decision.get("arguments",{})
        if field not in decision and isinstance(nested,dict) and isinstance(nested.get(field),str):
            decision[field]=nested[field]
        if not isinstance(decision.get(field),str) or not decision[field].strip():
            raise ValueError("Finish needs a nonempty answer; ask needs a nonempty question.")
    if not isinstance(decision.get("arguments",{}),dict):
        raise ValueError("Executable action arguments must be an object.")
    if any(key in decision and not isinstance(decision[key],str) for key in ("question","answer")):
        raise ValueError("Answer/question fields must be text when present.")
    return json.dumps(decision,ensure_ascii=False)
