"""Explicit public technical-answer acceptance; excluded from offline discovery.

Uses synthetic questions only. Optional Java compilation is confined to an owned
short-lived directory, disables annotation processors, and never executes code.
"""
import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider",choices=["openrouter","groq","gemini"],default="gemini")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"outputs/acceptance/answer-quality-summary-20261022")
    parser.add_argument("--timeout",type=int,default=30)
    parser.add_argument("--case",choices=["interfaces","inheritance"],default="interfaces")
    parser.add_argument("--source-first",action="store_true",help="Evaluate the existing opt-in public documentation path without changing saved settings")
    parser.add_argument("--production-budget",action="store_true",help="Use the unchanged provider output budgets instead of the evaluator 4096-token override")
    args=parser.parse_args()
    if not 10<=args.timeout<=180:parser.error("timeout must be from 10 to 180 seconds")
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env")
    os.environ["AI_TECHNICAL_VERIFICATION"]="auto"
    if args.source_first:os.environ["AI_SOURCE_FIRST_DOCUMENTATION"]="true"
    for prefix in ("OPENROUTER","GROQ","GEMINI"):
        os.environ[prefix+"_TIMEOUT"]=str(args.timeout)
        os.environ[prefix+"_CONNECT_ATTEMPTS"]="1"
    from agent.runtime.conversation import answer_question,web_search
    from agent.tools.web_pages import fetch_web_page
    from agent.providers.tools import call_tool_messages
    from agent.providers.selection import provider_selection
    from agent.providers.fallback import fallback_scope
    from agent.providers.errors import ProviderError
    question=("Explain advanced Java interface default-method conflicts and common pitfalls. "
              "Use Java 17 as the baseline and include one complete self-contained example in one Java code block.")
    if args.case=="inheritance":
        question=("Explain Java inheritance using Java 17 as the baseline, with examples and common pitfalls. "
                  "Verify important rules against official documentation. Include one complete code example, "
                  "and distinguish expected output from actual execution.")
    trace=[];sources=[]
    def model(messages,tools):
        trace.append({"offered":[spec["function"]["name"] for spec in tools]})
        checkpoint()
        reply=call_tool_messages(messages,tools,**({} if args.production_budget else {"max_tokens":4096}))
        trace[-1]["requested"]=[call["function"]["name"] for call in reply.get("tool_calls",[])]
        # This evaluator has only a synthetic public prompt and public pages.
        # Save returned data, never credentials, headers or hidden reasoning,
        # so factual/source assessment can inspect this exact run without replay.
        calls=reply.get("tool_calls") or []
        raw=calls[0].get("function",{}).get("arguments") if len(calls)==1 else reply.get("content")
        if isinstance(raw,str):
            trace[-1]["returned_data_characters"]=len(raw)
            try:trace[-1]["returned_data"]=json.loads(raw)
            except (ValueError,TypeError):pass
        checkpoint()
        return reply
    def web(query):
        result=web_search(query)
        sources.append({"tool":"web_search","result_urls":[row.get("url") for row in result.get("results",[])],"error":bool(result.get("error"))})
        checkpoint()
        return result
    def page(url):
        result=fetch_web_page(url)
        sources.append({"tool":"fetch_web_page","requested_url":url,"url":result.get("url"),"error":bool(result.get("error")),
                        "text_chars":len(result.get("text","")),"fragment_found":result.get("fragment_found"),
                        "title":result.get("title",""),"text":result.get("text",""),"truncated":result.get("truncated")})
        checkpoint()
        return result
    tools=SimpleNamespace(root="synthetic-public-fixture",list_files=lambda **k:{},read_file=lambda **k:{},search_text=lambda **k:{})
    report={"scope":"Synthetic public technical task with live provider/search/page reading; "+("unchanged provider output budgets" if args.production_budget else "explicit 4096 evaluation budget")+"; no saved chat or project files sent.","selected_provider":args.provider,
            "case":args.case,"source_first_opt_in":args.source_first,"output_budget_mode":"provider_defaults" if args.production_budget else "4096_evaluation_override","factual_quality_accepted":False,"question":question}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    def checkpoint():
        # Persist public evidence before the next network wait. An outer
        # process deadline can stop this evaluator before final report writing.
        target=args.output_dir/("live-progress-"+args.provider+".json")
        temporary=target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps({**report,"status":"in_progress","request_trace":trace,
            "sources":sources,"seconds":round(time.perf_counter()-start,2)},indent=2),encoding="utf-8")
        temporary.replace(target)
    with (args.output_dir/("live-final-"+args.provider+".log")).open("w",encoding="utf-8") as log,redirect_stdout(log),fallback_scope(),provider_selection(args.provider):
        try:
            result=answer_question({"question":question,"route":"direct"},model=model,tools=tools,project_root=".",document_search=lambda **k:{},web=web,page_fetch=page)
            answer=result.get("answer","")
            report.update(completed=result.get("execution_outcome")=="completed",answer=answer,
                          task_status=result.get("task_status","completed"),execution_outcome=result.get("execution_outcome"),
                          page_read=any(row["tool"]=="fetch_web_page" and row["text_chars"] for row in sources),
                          source_links=any(row.get("url") in re.sub(r"```.*?```","",answer,flags=re.S) for row in sources if row["tool"]=="fetch_web_page" and row.get("url") and not row["error"]),
                          inline_markdown_links=bool(re.search(r"\]\(https?://",answer)))
            blocks=re.findall(r"```java\s*\n(.*?)```",answer,re.S)
            compiler=shutil.which("javac")
            report["java_compile"]={"status":"not_attempted","compiler_available":bool(compiler)}
            if compiler and len(blocks)==1:
                match=re.search(r"public\s+(?:final\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)",blocks[0])
                if match:
                    with tempfile.TemporaryDirectory(prefix="jeshla-quality-") as directory:
                        source=Path(directory)/(match.group(1)+".java")
                        source.write_text(blocks[0],encoding="utf-8")
                        proc=subprocess.run([compiler,"--release","17","-proc:none","-encoding","UTF-8","-classpath",directory,"-d",directory,str(source)],
                            capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
                        report["java_compile"]={"status":"passed" if proc.returncode==0 else "failed","returncode":proc.returncode,
                            "generated_code_executed":False,"diagnostic":proc.stderr[:3000]}
            report["passed"]=report["completed"] and report["page_read"] and report["source_links"] and report["java_compile"].get("status")!="failed"
            report["workflow_passed"]=report["passed"]
        except ProviderError as error:
            report.update(passed=False,provider=error.provider,category=error.category)
        except Exception as error:
            report.update(passed=False,error_type=type(error).__name__)
    report.update(workflow_passed=bool(report.get("passed")),request_trace=trace,sources=sources,seconds=round(time.perf_counter()-start,2))
    output=args.output_dir/("live-final-"+args.provider+".json")
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({key:value for key,value in report.items() if key not in {"answer","sources","request_trace"}}))
    return 0 if report.get("passed") else 1


if __name__=="__main__":
    raise SystemExit(main())
