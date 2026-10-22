"""Public-only live recovery/follow-up probe; no saved chats or project files."""
import json
import os
from pathlib import Path
import sys
import time
from contextlib import redirect_stdout,redirect_stderr
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--explicit",action="store_true")
    parser.add_argument("--primary-only",action="store_true",help="Do not spend another provider call on topic-list follow-up.")
    parser.add_argument("--single-provider",action="store_true",help="Measure one selected provider and stop on quota/service failure.")
    parser.add_argument("--max-model-calls",type=int,default=16)
    parser.add_argument("--source-first",action="store_true",help="Opt into experimental source-first documentation acceptance.")
    parser.add_argument("--simulate-search-outage",action="store_true")
    parser.add_argument("--provider",choices=["openrouter","groq","gemini"],default="openrouter")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"outputs/acceptance/verification-recovery-20261022")
    args=parser.parse_args()
    if not 1<=args.max_model_calls<=20:parser.error("max-model-calls must be from 1 to 20")
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env")
    if args.source_first:os.environ["AI_SOURCE_FIRST_DOCUMENTATION"]="true"
    if args.single_provider:os.environ["LLM_FALLBACK_ENABLED"]="false"
    # Process-only diagnostic timeout; never edit user settings.
    for prefix in ("OPENROUTER","GROQ","GEMINI"):
        os.environ[prefix+"_TIMEOUT"]="25"
        os.environ[prefix+"_CONNECT_ATTEMPTS"]="1"
    os.environ["AI_TECHNICAL_VERIFICATION"]="auto"
    from agent.runtime.conversation import answer_question,web_search
    from agent.providers.tools import call_tool_messages
    from agent.providers.fallback import fallback_scope
    from agent.providers.selection import provider_selection
    from agent.providers.errors import ProviderError
    directory=args.output_dir
    directory.mkdir(parents=True,exist_ok=True)
    tools=SimpleNamespace(root="public-synthetic-fixture",list_files=lambda **k:{},read_file=lambda **k:{},search_text=lambda **k:{})
    question="Explain Java inheritance from basic to advanced concepts, with examples and common pitfalls. Avoid repeating points."
    if args.explicit:
        question="Explain Java inheritance using Java 17 as the baseline, with examples and common pitfalls. Verify important rules against official documentation. Include one complete code example, and distinguish expected output from actual execution."
    report={"scope":"Public synthetic question only; no user checkpoint, memory or project files","question":question,"selected_provider":args.provider,"injected_search_outage":args.simulate_search_outage,"single_provider":args.single_provider,"primary_only":args.primary_only,"max_model_calls":args.max_model_calls,"output_budget_override":False}
    calls=[]
    def model(messages,specs):
        if len(calls)>=args.max_model_calls:raise RuntimeError("Owned evaluation model-call ceiling reached")
        started=time.perf_counter()
        item={"offered":[spec["function"]["name"] for spec in specs]}
        calls.append(item)
        if any(name in {"submit_documentation_plan", "submit_grounded_sections", "submit_grounding_findings", "submit_answer_review"} for name in item["offered"]):
            # This evaluator uses a synthetic public question only; preserve
            # actual source excerpts for manual coverage/quality assessment.
            item["public_source_input"] = json.loads(messages[1]["content"])
        try:
            reply=call_tool_messages(messages,specs)
            item["requested"]=[call["function"]["name"] for call in reply.get("tool_calls",[])]
            item["public_draft"]=reply.get("content","")
            item["public_calls"]=[{"id":call.get("id"),"function":call.get("function",{})} for call in reply.get("tool_calls",[])]
            return reply
        finally:item["seconds"]=round(time.perf_counter()-started,2)
    start=time.perf_counter()
    with (directory/"live.log").open("w",encoding="utf-8") as log,redirect_stdout(log),redirect_stderr(log),fallback_scope(),provider_selection(args.provider):
        try:
            response=answer_question({"question":question,"route":"direct"},model=model,tools=tools,project_root=".",document_search=lambda **k:{},
                **({"web":lambda **k:{"error":"Synthetic acceptance fixture: search unavailable; no live search attempted."}} if args.simulate_search_outage else {}))
            answer=response["answer"]
            report.update(response=response,verification_fallback="uses general knowledge" in answer,
                substantive=len(answer)>1000 and "```java" in answer)
            if args.primary_only:
                report["workflow_passed"]=response.get("execution_outcome")=="completed" and report["substantive"]
                report["quality_status"]="pending_manual_source_and_factual_review"
            elif response.get("execution_outcome")=="completed":
                followup="List the topics covered in your previous answer, in the same order. Give topic names only, without examples or duplicates."
                result=answer_question({"question":followup,"route":"direct","previous_exchange":{"question":question,"answer":answer},
                    "previous_response_status":{"task_status":"completed","execution_outcome":"completed"}},
                    model=model,tools=tools,project_root=".",document_search=lambda **k:{})
                report["followup"]=result
                report["workflow_passed"]=report["substantive"] and result.get("execution_outcome")=="completed"
                report["quality_status"]="not_established_by_workflow_check"
            else:report["workflow_passed"]=False
        except ProviderError as error:report.update(workflow_passed=False,provider=error.provider,category=error.category,http_status=error.status,attempts=error.attempts)
        except Exception as error:report.update(workflow_passed=False,error_type=type(error).__name__)
    report.update(calls=calls,seconds=round(time.perf_counter()-start,2))
    (directory/"live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in {"response","followup","question","calls"}}))
    return 0 if report.get("workflow_passed") else 1


if __name__=="__main__":
    raise SystemExit(main())
