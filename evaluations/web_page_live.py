"""Live static-page compatibility on public official documentation; no LLM/private data."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent.web_pages import fetch_web_page
from agent.conversation import answer_question,web_search
from urllib.parse import urlsplit
from types import SimpleNamespace

CASES=[('python-docs','https://docs.python.org/3/tutorial/classes.html','class'),('playwright-java','https://playwright.dev/java/docs/intro','playwright')]

def main():
    rows=[]
    for name,url,term in CASES:
        started=time.perf_counter()
        result=fetch_web_page(url)
        text=result.get('text','')
        checks={'successful_text':not result.get('error') and bool(text.strip()),'bounded_text':len(text)<=4500,'expected_topic_visible':term in text.casefold(),'source_url_retained':isinstance(result.get('url'),str) and result['url'].startswith('https://')}
        rows.append({'case':name,'requested_url':url,'final_url':result.get('url'),'title':result.get('title'),'text_chars':len(text),'truncated':result.get('truncated'),'checks':checks,'status':'Y' if all(checks.values()) else 'P','error':result.get('error'),'http_status':result.get('http_status'),'seconds':round(time.perf_counter()-started,2)})
    # Real production search/page handlers; model decisions are scripted, not hosted.
    activity=[];step=0;selected=None;page_ok=False
    def public_search(query):
        activity.append('web_search')
        result=web_search(query)
        if result.get('error'):return result
        return {'results':[row for row in result.get('results',[]) if urlsplit(row.get('url','')).hostname=='playwright.dev'],'note':'Official Playwright domain only for this acceptance scenario.'}
    def page_read(url):
        nonlocal page_ok
        activity.append('fetch_web_page')
        result=fetch_web_page(url)
        page_ok=not result.get('error') and bool(result.get('text','').strip())
        return result
    def call(name,args):
        return {'role':'assistant','content':'','tool_calls':[{'id':'live-'+str(step),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
    def scripted(messages,tools):
        nonlocal step,selected
        step+=1
        if step==1:return call('web_search',{'query':'Playwright Java installation documentation'})
        result=json.loads(messages[-1]['content']) if messages[-1].get('role')=='tool' else {}
        if step==2:
            matches=result.get('results',[])
            if matches:
                selected=matches[0]['url']
                return call('fetch_web_page',{'url':selected})
            return {'role':'assistant','content':'No usable official search result was returned.'}
        if page_ok:return {'role':'assistant','content':'Read the bounded static excerpt from ['+result.get('title','Official documentation')+']('+result.get('url',selected)+'). The excerpt may omit relevant sections; no full-page factual verification is claimed.'}
        return {'role':'assistant','content':'The page could not be read; only search snippets are available. [Search source]('+str(selected)+').'}
    local=SimpleNamespace(root=ROOT,list_files=lambda **kwargs:{},read_file=lambda **kwargs:{},search_text=lambda **kwargs:{})
    result=answer_question({'question':'Find and read official Playwright Java documentation.','route':'web'},model=scripted,project_root=ROOT,tools=local,document_search=lambda **kwargs:{},web=public_search,page_fetch=page_read)
    pipeline={'status':'Y - live tools, scripted decisions' if page_ok and result.get('task_status')!='incomplete' else 'P','tool_activity':activity,'source_url':selected,'page_read_success':page_ok,'task_status':result.get('task_status','completed'),'answer':result['answer'],'scope':'Real web search and page read through production tool/citation loop; model decisions scripted. No hosted-model selection or factual entailment acceptance.'}
    report={'status':'Y - sampled page compatibility' if all(row['status']=='Y' for row in rows) else 'P','cases':rows,'search_read_citation_pipeline':pipeline,'scope':'Actual production page reader against two public official documentation pages; no LLM or private data. Checks text availability, topic and bounds, not factual entailment or arbitrary-site compatibility.','remaining':['Hosted-model source selection and claim entailment','Hard end-to-end network deadline']}
    path=ROOT/'outputs/acceptance/web-page-live.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

