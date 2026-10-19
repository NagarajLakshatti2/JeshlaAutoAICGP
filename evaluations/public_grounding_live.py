"""Live configured-model grounding on public documentation only."""
import json,sys,tempfile,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from agent.tool_llm import call_tool_messages
from agent.llm_client import LLM_PROVIDER
from agent.conversation import answer_question,web_search
from agent.web_pages import fetch_web_page
from agent.tools.project_tools import ProjectTools
from agent.user_errors import user_error_message

def main():
    started=time.perf_counter();activity=[];pages=[]
    def search(query):
        activity.append('web_search');result=web_search(query)
        if result.get('error'):return result
        return {'results':[row for row in result.get('results',[]) if urlsplit(row.get('url','')).hostname=='playwright.dev'],'note':'Official Playwright documentation results only for this acceptance check.'}
    def page(url):
        activity.append('fetch_web_page');result=fetch_web_page(url)
        if not result.get('error'):pages.append({'url':result.get('url'),'title':result.get('title'),'text':result.get('text','')})
        return result
    try:
        with tempfile.TemporaryDirectory() as folder:
            result=answer_question({'question':'Search for Playwright Java installation documentation. Fetch the official Java installation page. Answer only its page title and whether it is Java documentation, with the returned page URL as a Markdown link. Use search terms Playwright Java installation documentation. Do not inspect local files or saved facts.','route':'web'},model=call_tool_messages,project_root=folder,tools=ProjectTools(folder),document_search=lambda **kwargs:{'error':'No private documents in this public acceptance check.'},web=search,page_fetch=page)
        answer=result['answer'];matched=[p for p in pages if '/java/' in (p['url'] or '')]
        checks={'searched_and_read':{'web_search','fetch_web_page'}<=set(activity),'java_page_read':bool(matched),'page_title_retained':any(p['title'] and p['title'].casefold() in answer.casefold() for p in matched),'returned_page_cited':any(p['url'] in answer for p in matched),'not_incomplete':result.get('task_status')!='incomplete'}
        report={'provider':LLM_PROVIDER,'status':'Y - sampled public tool/answer acceptance' if all(checks.values()) else 'P','checks':checks,'tool_activity':activity,'answer':answer,'page_sources':[{'url':p['url'],'title':p['title']} for p in pages]}
    except Exception as error:report={'provider':LLM_PROVIDER,'status':'P','error':user_error_message(error),'tool_activity':activity}
    report.update(seconds=round(time.perf_counter()-started,2),scope='Configured hosted/local model selects actual public search/page tools. Temporary empty source root; no private facts/history/documents. Title/source checks only, not general factual entailment.')
    (ROOT/'outputs/acceptance/public-grounding-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
