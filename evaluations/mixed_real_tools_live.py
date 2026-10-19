"""Mixed live acceptance: temporary SQLite/doc index plus actual public web tools."""
import json,pickle,secrets,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from agent.llm_client import LLM_PROVIDER
from agent.tool_llm import call_tool_messages
from agent.conversation import answer_question,web_search
from agent.web_pages import fetch_web_page
from agent.memory.long_term_memory import LongTermMemory
from agent.tools.project_tools import ProjectTools
from agent.user_errors import user_error_message
from rank_bm25 import BM25Okapi
import rag.retrieval as retrieval

def main():
    started=time.perf_counter();used=[];refs=set();pages=[];name='SampleProject'+secrets.token_hex(3)
    original_dir=retrieval.DATA_DIR
    try:
        with tempfile.TemporaryDirectory() as folder,LongTermMemory(':memory:') as memory:
            root=Path(folder);data=root/'index';data.mkdir()
            texts={'report_notes.txt':'The selected report format for this sample project is Markdown.','garden.txt':'The garden contains violets and roses.','bicycle.txt':'The bicycle has steel wheels and a bell.'}
            chunks=[]
            for source,text in texts.items():
                (root/source).write_text(text,encoding='utf-8')
                chunks.append(SimpleNamespace(page_content=text,metadata={'source':source,'page':1,'file_type':'txt'}))
            with (data/'chunks.pkl').open('wb') as f:pickle.dump(chunks,f)
            with (data/'bm25.pkl').open('wb') as f:pickle.dump(BM25Okapi([c.page_content.lower().split() for c in chunks]),f)
            retrieval.DATA_DIR=data;retrieval._load_keyword_resources.cache_clear();retrieval._normalized_keyword_resources.cache_clear()
            memory.save('acceptance','sample','project_name',name,source_kind='user_statement',source_ref='Temporary acceptance fixture')
            memory.save('other-user','sample','project_name','UnrelatedPrivateProject',source_kind='user_statement')
            def saved(query,mode='lexical',limit=10):
                used.append('search_memory')
                if mode!='lexical':return {'error':'Use lexical memory in this sample acceptance.'}
                return {'facts':memory.search('acceptance','sample',query,limit)}
            def docs(query,mode='hybrid'):
                used.append('search_documents')
                if mode!='keyword':return {'error':'Use keyword mode for this temporary index; no embedding download is allowed.'}
                result=retrieval.execute_search_documents(query,structured=True,retrieval_mode=mode)
                refs.update(row['ref'] for row in result.get('sources',[]));return result
            def search(query):
                used.append('web_search');result=web_search(query)
                if result.get('error'):return result
                return {'results':[row for row in result.get('results',[]) if urlsplit(row.get('url','')).hostname=='playwright.dev'],'note':'Public official Playwright documentation only in this acceptance scenario.'}
            def page(url):
                used.append('fetch_web_page');result=fetch_web_page(url)
                if not result.get('error'):pages.append({'url':result.get('url'),'title':result.get('title')})
                return result
            result=answer_question({'question':'Use search_memory (query project name) to find the sample project name, and search_documents with mode keyword (query report format) for its report format. Separately web_search for Playwright Java installation documentation and fetch_web_page on the official Java page. Give a concise combined answer with the saved project name, the document report format and exact fetched page title. Cite the returned [DOC-id] and page URL. Keep the saved user statement separate from document/public evidence. Do not put sample facts into the public search query or inspect unrelated local files.'},model=call_tool_messages,project_root=root,tools=ProjectTools(root),document_search=docs,memory_search=saved,web=search,page_fetch=page)
            answer=result['answer']
            checks={'all_four_tools_used':{'search_memory','search_documents','web_search','fetch_web_page'}<=set(used),'scoped_name_retained':name in answer,'other_user_excluded':'UnrelatedPrivateProject' not in answer,'document_format_retained':'markdown' in answer.casefold(),'returned_document_cited':any('['+ref+']' in answer for ref in refs),'read_page_cited':any(p['url'] in answer for p in pages),'exact_page_title_retained':any(p['title'] and p['title'].casefold() in answer.casefold() for p in pages),'not_incomplete':result.get('task_status')!='incomplete'}
            report={'provider':LLM_PROVIDER,'status':'Y - sampled real-tool mixed acceptance' if all(checks.values()) else 'P','checks':checks,'tool_activity':used,'answer':answer,'page_sources':pages}
    except Exception as error:report={'provider':LLM_PROVIDER,'status':'P','error':user_error_message(error),'tool_activity':used}
    finally:
        retrieval.DATA_DIR=original_dir;retrieval._load_keyword_resources.cache_clear();retrieval._normalized_keyword_resources.cache_clear()
    report.update(seconds=round(time.perf_counter()-started,2),scope='Live configured model; real temporary scoped SQLite and BM25 retrieval plus actual public search/page tools. No private project/history export; no embeddings or production index change. Sample facts/title/source checks only.')
    (ROOT/'outputs/acceptance/mixed-real-tools-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
