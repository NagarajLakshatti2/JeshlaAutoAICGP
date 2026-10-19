"""Live configured-model acceptance on synthetic local/public tool fixtures only."""
import json,secrets,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/".env")
from agent.llm_client import LLM_PROVIDER
from agent.tool_llm import call_tool_messages
from agent.conversation import answer_question
from agent.memory.long_term_memory import LongTermMemory
from agent.tools.project_tools import ProjectTools
from agent.user_errors import user_error_message
from rag.retrieval import document_sources
from types import SimpleNamespace

def main():
 start=time.perf_counter();used=[];name="Project"+secrets.token_hex(3)
 try:
  with tempfile.TemporaryDirectory() as folder,LongTermMemory(":memory:") as memory:
   root=Path(folder);file=root/"project_notes.txt";file.write_text("The chosen report format is Markdown.",encoding="utf-8")
   memory.save("eval","project","project_name",name,source_kind="user_statement")
   evidence=document_sources([((SimpleNamespace(page_content=file.read_text(),metadata={"source":file.name,"page":1,"file_type":"txt"}),1.,"synthetic-index"),1.)]);ref=evidence["sources"][0]["ref"]
   def saved(query,**kwargs):used.append("search_memory");return {"facts":memory.search("eval","project",query)}
   def docs(**kwargs):used.append("search_documents");return evidence
   def web(**kwargs):used.append("web_search");return {"results":[{"url":"https://example.org/docs","snippet":"Synthetic public-source fixture: use stable selectors."}],"note":"Test fixture, not a real web search."}
   def page(url):used.append("fetch_web_page");return {"url":url,"text":"Synthetic fetched-page fixture: use stable selectors for reliable tests."}
   result=answer_question({"question":"Acceptance test with synthetic tool fixtures: use search_memory for project name; search_documents with mode keyword for report format; web_search then fetch_web_page for page advice. Summarize all three with a returned document reference and web URL. Keep source assertions distinct. Do not inspect unrelated local files."},model=call_tool_messages,project_root=root,tools=ProjectTools(root),document_search=docs,memory_search=saved,web=web,page_fetch=page)
   answer=result["answer"]
   checks={"all_four_sources_used":set(used)>={"search_memory","search_documents","web_search","fetch_web_page"},"saved_name_retained":name in answer,"document_fact_retained":"markdown" in answer.casefold(),"document_reference_retained":ref in answer,"web_reference_retained":"https://example.org/docs" in answer,"page_advice_retained":"selector" in answer.casefold(),"not_incomplete":result.get("task_status")!="incomplete"}
   report={"provider":LLM_PROVIDER,"status":"Y" if all(checks.values()) else "P","checks":checks,"tool_activity":used,"answer":answer,"seconds":round(time.perf_counter()-start,2),"scope":"Live configured model with synthetic memory/document/web/page fixtures; not real browsing or private data"}
 except Exception as error:report={"provider":LLM_PROVIDER,"status":"P","error":user_error_message(error),"scope":"Synthetic fixtures only","tool_activity":used,"seconds":round(time.perf_counter()-start,2)}
 (ROOT/"outputs/acceptance/mixed-grounding-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=True,indent=2))
if __name__=="__main__":main()
