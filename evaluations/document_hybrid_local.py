"""Cached-only hybrid retrieval benchmark; no hosted calls or model downloads."""
import json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
for key in ['HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']:os.environ[key]='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
OUTPUT=ROOT/'outputs/acceptance/document-hybrid-local.json'
PROGRESS=ROOT/'outputs/acceptance/document-hybrid-progress.json'

def stage(name):
 progress=json.loads(PROGRESS.read_text(encoding='utf-8')) if PROGRESS.exists() else {}
 progress['stage']=name
 PROGRESS.write_text(json.dumps(progress),encoding='utf-8');print(name,flush=True)
def normalized(text):return ' '.join(text.casefold().split())

def main():
 started=time.perf_counter();rows=[]
 PROGRESS.write_text(json.dumps({'stage':'Starting bounded run','completed':0,'cases':[]}),encoding='utf-8')
 try:
  from tests.run_offline import offline_guard
  with offline_guard():
   stage('Loading local ML dependencies')
   import torch
   torch.set_num_threads(2)
   from langchain_huggingface import HuggingFaceEmbeddings
   from sentence_transformers import CrossEncoder
   import langchain_huggingface as hf
   import sentence_transformers as st
   from unittest.mock import patch
   def embeddings(**kwargs):
    kwargs['model_kwargs']={**kwargs.get('model_kwargs',{}),'local_files_only':True,'trust_remote_code':False,'device':'cpu'}
    return HuggingFaceEmbeddings(**kwargs)
   def reranker(*args,**kwargs):
    return CrossEncoder(*args,**{**kwargs,'local_files_only':True,'trust_remote_code':False,'device':'cpu'})
   from rag.retrieval import execute_search_documents
   cases=json.loads((ROOT/'rag/evaluation_questions.json').read_text(encoding='utf-8'))
   audited={row['id']:row['audited_page'] for row in json.loads((ROOT/'outputs/acceptance/document-keyword-normalized.json').read_text(encoding='utf-8'))['cases']}
   with patch.object(hf,'HuggingFaceEmbeddings',embeddings),patch.object(st,'CrossEncoder',reranker):
    for case in cases:
     stage('Retrieving benchmark case '+str(case['id']))
     result=execute_search_documents(case['question'],structured=True,retrieval_mode='hybrid')
     expected=audited.get(case['id'],str(case['expected_page']))
     def passed(location):
      matches=[s for s in result['sources'] if s['source']==case['expected_source'] and s['location']==location]
      text=normalized(' '.join(s['text'] for s in matches))
      return bool(matches) and all(normalized(word) in text for word in case['expected_keywords'])
     rows.append({'id':case['id'],'original_pass':passed(str(case['expected_page'])),'audited_pass':passed(expected),'source_count':len(result['sources'])})
     PROGRESS.write_text(json.dumps({'stage':'Completed benchmark case '+str(case['id']),'completed':len(rows),'cases':rows}),encoding='utf-8')
   report={'status':'Y - sampled hybrid source/keyword coverage' if all(row['audited_pass'] for row in rows) else 'P','total':len(cases),'completed':len(rows),'audited_passed':sum(row['audited_pass'] for row in rows),'original_passed':sum(row['original_pass'] for row in rows),'cases':rows}
 except Exception as error:
  report={'status':'P','error_category':type(error).__name__,'explanation':'Cached-only hybrid resources could not complete. No download/network retry or provider fallback performed.','completed':len(rows),'cases':rows}
 report.update(seconds=round(time.perf_counter()-started,2),api_calls=0,downloads_allowed=False,network_guard=True,production_indexes_modified=False,scope='Existing eight-query corpus; original and previously audited labels retained. Source/keyword coverage only, not general answer entailment or broad novel-query relevance.')
 OUTPUT.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
