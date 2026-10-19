"""Finite synthetic live planning/clarification acceptance; no private histories."""
import sys,json,tempfile,time,argparse,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/".env")
from agent.conversation import answer_question
from agent.tool_llm import call_tool_messages
from agent.llm_client import LLM_PROVIDER
from agent.tools.project_tools import ProjectTools
from agent.user_errors import user_error_message
cases=[
("missing_details","Help me automate an application. I have not supplied its details. Ask at most three focused questions; do not guess any application details."),
("reuse_details","The application is web, tests use Java and Playwright, and its URL is https://example.invalid. I have not specified the workflow or expected result. Ask only about essential missing details; do not ask again for the language, application type or URL."),
("plan_read","Inspect the project files using list_files and read_file. Find the report format in the configuration file. Cite its filename and do not modify files."),
("recover_read","First attempt read_file on missing.txt. If it fails, use list_files to discover the existing configuration and read it. Explain its report format and disclose the initial failure. Do not modify files.")]
parser=argparse.ArgumentParser();parser.add_argument("--cases",nargs="*");args=parser.parse_args()
if args.cases:cases=[c for c in cases if c[0] in args.cases]
rows=[];start=time.perf_counter()
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);(root/"settings.txt").write_text("report_format=Markdown",encoding="utf-8")
 for name,question in cases:
  calls=[]
  def model(messages,tools):
   reply=call_tool_messages(messages,tools)
   for call in reply.get("tool_calls",[]):calls.append({"name":call["function"]["name"],"args":json.loads(call["function"]["arguments"])})
   return reply
  try:
   result=answer_question({"question":question},model=model,project_root=root,tools=ProjectTools(root),document_search=lambda **kw:{"sources":[]})
   text=result["answer"]
   if name in {"missing_details","reuse_details"}:checks={"asks_question":"?" in text,"no_tools":not calls,"focused":len(re.findall(r"(?m)^\s*\d+[.)]",text))<=3 if re.search(r"(?m)^\s*\d+[.)]",text) else text.count("?")<=3}
   else:
    checks={"list_then_read":any(c["name"]=="list_files" for c in calls) and any(c["name"]=="read_file" and c["args"].get("relative_path")=="settings.txt" for c in calls),"correct_value":"markdown" in text.casefold(),"cites_file":"settings.txt" in text,"file_unchanged":(root/"settings.txt").read_text()=="report_format=Markdown"}
    if name=="recover_read":checks.update({"missing_attempted":any(c["name"]=="read_file" and c["args"].get("relative_path")=="missing.txt" for c in calls),"conservative_outcome":result.get("task_status")=="incomplete"})
   rows.append({"case":name,"checks":checks,"answer":text,"task_status":result.get("task_status","normal_answer"),"execution_outcome":result.get("execution_outcome"),"calls":calls})
  except Exception as error:
   rows.append({"case":name,"error":user_error_message(error)});break
report={"provider":LLM_PROVIDER,"cases":rows,"seconds":round(time.perf_counter()-start,2),"scope":"Finite synthetic cases with real local temporary files; clarification wording requires manual review, no universal planning or semantic truth guarantee."}
(ROOT/("outputs/acceptance/workstream5-live-"+LLM_PROVIDER+".json")).write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report,indent=2))
