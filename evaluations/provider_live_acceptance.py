"""Explicit live provider acceptance; excluded from offline test discovery.
Run: python evaluations/provider_live_acceptance.py --provider groq
Uses existing credentials/model, never changes .env or sends project files.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider",required=True,choices=["openrouter","groq","gemini","ollama"])
    parser.add_argument("--check",choices=["all","direct_answer","native_tool_result_answer"],default="all")
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env")
    os.environ["LLM_PROVIDER"]=args.provider
    os.environ["LLM_FALLBACK_ENABLED"]="false"
    from agent.llm_client import call_llm_messages,OLLAMA_MODEL,OPENROUTER_MODEL
    from agent.tool_llm import call_tool_messages
    from agent.user_errors import user_error_message
    budget=256 if args.provider=="ollama" else 4096
    model={"ollama":OLLAMA_MODEL,"openrouter":OPENROUTER_MODEL,"groq":os.getenv("GROQ_MODEL",""),"gemini":os.getenv("GEMINI_MODEL","")}[args.provider]
    report={"provider":args.provider,"model":model,"scope":"direct answer and real temporary-file native tool/result cycle","checks":{}}
    def check(name,function):
        start=time.perf_counter()
        try:
            passed=bool(function())
            result={"status":"Y" if passed else "P"}
            if not passed:result["error"]="Acceptance output did not match actual verification evidence."
        except Exception as error:
            result={"status":"P","error":user_error_message(error)}
        result["seconds"]=round(time.perf_counter()-start,2)
        report["checks"][name]=result
        print(name+": "+result["status"],flush=True)
    def direct():
        nonce=secrets.token_hex(6)
        answer=call_llm_messages([{"role":"user","content":"Reply with exactly this verification code and no other text: "+nonce}],max_tokens=budget)
        return nonce in answer
    def tools():
        spec={"type":"function","function":{"name":"read_acceptance_fact","description":"An available read-only tool executed by the application. Takes no arguments. Returns the actual local verification code; never guess.","parameters":{"type":"object","properties":{},"required":[],"additionalProperties":False}}}
        messages=[{"role":"system","content":"The application provides read_acceptance_fact and will execute it for you. Call it once with an empty argument object, then report the code from its real result. Never invent a code or claim the provided tool is unavailable."},{"role":"user","content":"Call read_acceptance_fact with no arguments now, then tell me the verification code from its result."}]
        reply=call_tool_messages(messages,[spec],max_tokens=budget)
        calls=reply.get("tool_calls") or []
        if len(calls)!=1 or calls[0]["function"]["name"]!="read_acceptance_fact" or json.loads(calls[0]["function"]["arguments"])!={}:return False
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"verification.txt";code=secrets.token_hex(8)
            path.write_text(code,encoding="utf-8")
            result={"verification_code":path.read_text(encoding="utf-8"),"source":"temporary verification file"}
        messages.extend([reply,{"role":"tool","tool_call_id":calls[0]["id"],"name":"read_acceptance_fact","content":json.dumps(result)}])
        final=call_tool_messages(messages,[spec],max_tokens=budget)
        return not final.get("tool_calls") and code in final.get("content","")
    if args.check in {"all","direct_answer"}:check("direct_answer",direct)
    if args.check in {"all","native_tool_result_answer"}:check("native_tool_result_answer",tools)
    report["status"]="Y" if all(row["status"]=="Y" for row in report["checks"].values()) else "P"
    output=ROOT/"outputs"/"acceptance"/f"provider-{args.provider}.json"
    if args.check!="all" and output.is_file():
        previous=json.loads(output.read_text(encoding="utf-8"))
        if previous.get("model")==model:
            report["checks"]={**previous.get("checks",{}),**report["checks"]}
    report["status"]="Y" if set(report["checks"])=={"direct_answer","native_tool_result_answer"} and all(row["status"]=="Y" for row in report["checks"].values()) else "P"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    return 0 if report["status"]=="Y" else 1


if __name__=="__main__":raise SystemExit(main())
