"""Opt-in T22 saved-packet check through real console/browser backend adapters.

Run one mode only after explicit payload authorization. This never runs tests or
opens the target website. Runtime chat/fact stores are isolated before imports.
"""
import argparse
from contextlib import ExitStack
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "outputs/acceptance/t22-live-review-20261101"
PACKET_SHA = "24dc8f9327486b85fdfb1d3d182d6f8e55f7ceaa8d0c643cb39144ae159e20e5"
PROMPT_SHA = "17312319bd870e6aed77b45c12914ad30096ed9f890d7ebcd92cd55418451a9e"
HOSTS = {"openrouter.ai", "api.groq.com", "generativelanguage.googleapis.com"}


def preflight(verification=False):
    review = json.loads((FOLDER / "payload-review.json").read_text(encoding="utf-8"))
    packet = Path(review["packet_file"])
    prompt = Path(review["prompt_file"])
    if (hashlib.sha256(packet.read_bytes()).hexdigest() != PACKET_SHA or
            hashlib.sha256(prompt.read_text(encoding="utf-8").encode("utf-8")).hexdigest() != PROMPT_SHA):
        raise ValueError("Authorized packet or prompt changed; do not send it.")
    if list(packet.parent.iterdir()) != [packet] or len(packet.read_text(encoding="utf-8").splitlines()) != 48:
        raise ValueError("Evidence-only project changed.")
    authorization = json.loads((FOLDER / ("authorization-verification.json" if verification else "authorization.json")).read_text(encoding="utf-8"))
    if verification and (authorization.get("questions") != 1 or authorization.get("mode") != "console"):
        raise ValueError("Final verification needs its one-console-question authorization.")
    if authorization.get("packet_sha256") != PACKET_SHA or authorization.get("prompt_sha256") != PROMPT_SHA:
        raise ValueError("No matching payload authorization.")
    return packet, prompt.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["console", "browser"], required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--attempt", type=int, choices=[1,2], default=1)
    parser.add_argument("--verification", action="store_true")
    args = parser.parse_args()
    if args.verification and args.mode != "console":
        raise ValueError("This final verification is console-only.")
    packet, question = preflight(args.verification)
    if args.preflight_only:
        print(json.dumps({"preflight":"passed", "provider_requests":0}));return 0
    stem = args.mode + ("-verification" if args.verification else "-attempt2" if args.attempt == 2 else "")
    runtime = FOLDER / ("runtime-" + stem)
    if runtime.exists():
        raise ValueError("This mode already has an attempt; inspect it, do not replay.")
    runtime.mkdir()
    # Load existing configured keys locally, never print them or copy them into evidence.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    os.environ.update({"JESHLA_HOME":str(runtime), "AI_PROJECT_ROOT":str(packet.parent),
        "AI_MEMORY_USER_ID":"t22-acceptance", "AI_MEMORY_NAMESPACE":"saved-review-"+args.mode,
        "LLM_PROVIDER":"openrouter", "LLM_FALLBACK_ENABLED":"true",
        "LLM_FALLBACK_ORDER":"openrouter,groq,gemini", "LLM_ALLOW_LOCAL_OLLAMA":"false",
        "AI_MAX_STEPS":"4", "AI_PROJECT_MAX_TOKENS":"2048", "AI_TECHNICAL_VERIFICATION":"off",
        "AI_SUMMARY_MIN_TURNS":"100", "AI_SUMMARY_THRESHOLD_CHARS":"16000"})
    for provider in ("OPENROUTER", "GROQ", "GEMINI"):
        os.environ[provider+"_TIMEOUT"]="20"
        os.environ[provider+"_CONNECT_ATTEMPTS"]="1"
    from agent.config.paths import DATA_ROOT
    if DATA_ROOT != runtime:
        raise ValueError("Runtime imports occurred before isolation.")
    import requests
    from agent.langgraph import langgraph_agent as agent
    from agent.interfaces.browser import BrowserBackend
    from agent.interfaces.console import run_console
    from agent.policies.tool_registry import PROJECT_ACTIONS
    from agent.runtime import turns
    from agent.tools.project_tools import ProjectTools
    from agent.user_errors import user_error_message
    record={"mode":args.mode, "attempt":args.attempt, "status":"P", "packet_sha256":PACKET_SHA,
            "prompt_sha256":PROMPT_SHA,"runtime":str(runtime),"tool_calls":[],
            "provider_requests":[],"policy_violations":[],"turns":[]}
    original_request=requests.sessions.Session.request
    original_read=ProjectTools.read_file
    original_turn=turns.run_turn
    coverage=set()

    def reject(label):
        record["policy_violations"].append(label)
        raise RuntimeError("Acceptance blocks activity outside the authorized saved-packet review: "+label)

    def request(session, method, url, **kwargs):
        host=urlsplit(url).hostname
        if host not in HOSTS or urlsplit(url).scheme != "https":reject("unapproved network destination")
        if len(record["provider_requests"]) >= 10:reject("provider request cap")
        body=kwargs.get("json")
        if not isinstance(body,dict):
            try:body=json.loads(kwargs.get("data") or "{}")
            except (ValueError,TypeError):body={}
        model=body.get("model") if isinstance(body,dict) else None
        if host=="openrouter.ai" and (not isinstance(model,str) or not (model.endswith(":free") or model=="openrouter/free")):
            reject("non-free OpenRouter model")
        record["provider_requests"].append({"host":host,"model":model})
        return original_request(session,method,url,**kwargs)

    @wraps(original_read)
    def read(tools, relative_path, start_line=1, max_lines=40):
        if (tools.root != packet.parent.resolve() or relative_path != packet.name
                or type(start_line) is not int or not 1 <= start_line <= 48
                or type(max_lines) is not int or not 1 <= max_lines <= 80):reject("unauthorized file read")
        if hashlib.sha256(packet.read_bytes()).hexdigest()!=PACKET_SHA:reject("changed packet")
        value=original_read(tools,relative_path,start_line,max_lines)
        record["tool_calls"].append({"action":"read_file","file":relative_path,
            "start_line":value["start_line"],"end_line":value["end_line"]})
        coverage.update(range(value["start_line"],value["end_line"]+1))
        return value

    def forbidden(name, original):
        @wraps(original)
        def call(*positional, **keyword):return reject(name)
        return call

    @wraps(original_turn)
    def turn(graph,config,catalog,session,question,root,**kwargs):
        initial=graph.get_state(config).values or {}
        if initial.get("history") or initial.get("summary"):reject("nonempty initial chat")
        result=original_turn(graph,config,catalog,session,question,root,**kwargs)
        record["turns"].append({key:result.get(key) for key in
            ("answer","final_answer","route","task_status","execution_outcome","notices","persistence_status")})
        return result

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(requests.sessions.Session,"request",request))
            stack.enter_context(patch.object(ProjectTools,"read_file",read))
            for name in sorted(PROJECT_ACTIONS-{"read_file","read_files"}):
                original=getattr(ProjectTools,name)
                stack.enter_context(patch.object(ProjectTools,name,forbidden(name,original)))
            for name in ("web_node","jira_node","jira_workflow_node","conversational_answer_node"):
                stack.enter_context(patch.object(agent,name,forbidden(name,getattr(agent,name))))
            stack.enter_context(patch.object(turns,"run_turn",turn))
            stack.enter_context(patch("builtins.input",side_effect=lambda *a:reject("interactive approval/authentication")))
            for name in ("open","open_new","open_new_tab"):
                stack.enter_context(patch("webbrowser."+name,side_effect=lambda *a,**k:reject("browser navigation")))
            if args.mode=="console":
                messages=iter([question,"EXIT"])
                stack.enter_context(patch("sys.argv",["saved-review","--session","t22-saved-review","--user","t22-acceptance","--memory-space","saved-review-console"]))
                stack.enter_context(patch("agent.interfaces.terminal_input.configure_input"))
                stack.enter_context(patch("agent.interfaces.terminal_input.read_message",side_effect=lambda:next(messages)))
                run_console(graph=agent.graph,project_root=DATA_ROOT,provider=agent.LLM_PROVIDER,
                            session_config=agent.session_config,restore_session=agent.restore_session)
            else:
                backend=BrowserBackend()
                session=backend.create_chat("T22 saved review acceptance")
                backend.submit(session,question)
        record["full_packet_read"]=coverage==set(range(1,49))
        record["single_turn"]=len(record["turns"])==1
        if record["single_turn"]:
            answer=record["turns"][0].get("answer") or ""
            current=record["turns"][0]
            record["checks"]={"full_packet_read":record["full_packet_read"],
                "project_route":current.get("route")=="project",
                "not_incomplete":current.get("task_status")!="incomplete",
                "all_case_ids":all(identity in answer for identity in ("QPH-010","QPH-011","QPH-012")),
                "source_files":all(name in answer for name in ("Login Pilot.feature","LoginPilotPage.java","LoginPilotSteps.java")),
                "no_policy_violation":not record["policy_violations"]}
            record["status"]="P — answer awaits semantic review" if all(record["checks"].values()) else "P — incomplete/failed integration check"
    except Exception as error:
        record["error"]=user_error_message(error)
        record["error_type"]=type(error).__name__
    record["packet_unchanged"]=hashlib.sha256(packet.read_bytes()).hexdigest()==PACKET_SHA
    (FOLDER/(stem+"-result.json")).write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({key:record.get(key) for key in ("mode","status","checks","error","provider_requests")},ensure_ascii=True))
    return 0 if record.get("checks") and all(record["checks"].values()) else 1


if __name__=="__main__":raise SystemExit(main())
