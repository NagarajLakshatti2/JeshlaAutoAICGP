"""Explicit live synthetic summary accuracy check; consumes configured API quota."""
import json,os,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/".env")
from agent.context_summary import compact_context
from agent.summary_model import call_summary_messages
from agent.chat_catalog import ChatCatalog
from agent.user_errors import user_error_message

def main():
    prior=json.dumps({"facts":[],"decisions":[],"open_questions":["Where should the final report be saved?","Which browser versions should be targeted?","How should test data be managed?"]})
    turns=[("My favorite language is Java.","Noted."),("The project is OldDemo.","Noted."),("Correction: the project is NewDemo.","Noted."),("Which build tool is used?","Gradle, according to my earlier answer; no file tool evidence is available.")]
    turns += [("Neutral filler "+str(i)+" "+("example "*110),"Noted.") for i in range(18)]
    history="".join("\nUser: "+q+"\nAssistant: "+a for q,a in turns)
    start=time.perf_counter()
    try:
        with tempfile.TemporaryDirectory() as directory:
            catalog=ChatCatalog(Path(directory)/"chats.sqlite3","test-user","test-space")
            catalog.register("test-chat")
            catalog.append("test-chat","Where should the final report be saved?","Not decided yet.")
            summary,recent,changed=compact_context(prior,history,call_summary_messages,question_lookup=lambda questions:catalog.summary_question_evidence("test-chat",questions))
        value=json.loads(summary);questions=" ".join(value["open_questions"]).lower();facts=" ".join(value["facts"]).lower()
        checks={"summary_created":changed,"language_retained":"java" in facts,"correction_retained":"NewDemo" in summary,"archived_question_retained":"report" in questions,"invented_questions_removed":"browser" not in questions and "test data" not in questions,"answered_question_removed":"build tool" not in questions,"assistant_source_retained":any("gradle" in x.lower() and "assistant" in x.lower() for x in value["facts"])}
        report={"status":"Y" if all(checks.values()) else "P","provider":os.getenv("LLM_PROVIDER"),"fixture":"synthetic source attribution and scoped archived-question evidence","checks":checks,"summary":value,"seconds":round(time.perf_counter()-start,2)}
    except Exception as error:
        report={"status":"P","provider":os.getenv("LLM_PROVIDER"),"error":user_error_message(error)}
    output=ROOT/"outputs/acceptance/summary-grounding-current.json";output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 0 if report["status"]=="Y" else 1

if __name__=="__main__":raise SystemExit(main())
