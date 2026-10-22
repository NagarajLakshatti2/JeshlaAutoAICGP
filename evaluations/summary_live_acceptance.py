"""Explicit synthetic long-chat summary acceptance, with no project data."""
import argparse,json,os,secrets,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser();parser.add_argument("--provider",required=True,choices=["openrouter","groq","gemini","ollama"]);args=parser.parse_args()
from dotenv import load_dotenv
load_dotenv(ROOT/".env");os.environ["LLM_PROVIDER"]=args.provider;os.environ["LLM_FALLBACK_ENABLED"]="false"
from agent.context_summary import compact_context
from agent.summary_model import call_summary_messages
from agent.user_errors import user_error_message
current="Project"+secrets.token_hex(4)
turns=["User corrected the project name from OldProject to "+current+". This is the current project name.","User asks where the final report should be saved; this question remains unanswered."]
turns+=['Neutral conversation entry '+str(i)+' '+('example data '*65) for i in range(18)]
history=''.join('\nUser: '+text+'\nAssistant: Noted.' for text in turns)
start=time.perf_counter()
try:
 summary,recent,changed=compact_context('',history,call_summary_messages)
 value=json.loads(summary)
 checks={"summary_created":changed,"corrected_name_retained":current in summary,"open_question_retained":bool(value['open_questions']),"recent_turn_boundary":recent.startswith('\nUser: '),"summary_within_limit":len(summary)<=5000}
 report={"provider":args.provider,"fixture":"synthetic long chat; no user project content","checks":checks,"status":"Y" if all(checks.values()) else "P","seconds":round(time.perf_counter()-start,2)}
except Exception as error:
 report={"provider":args.provider,"status":"P","error":user_error_message(error),"seconds":round(time.perf_counter()-start,2)}
output=ROOT/'outputs/acceptance'/('summary-'+args.provider+'.json');output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='Y' else 1)
