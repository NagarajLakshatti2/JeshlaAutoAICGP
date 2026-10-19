"""Audit trusted existing index excerpts against local sources without exporting text."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rag.retrieval import _load_keyword_resources
from rag.paths import DATA_FOLDER
from rag.source_audit import audit_sources

def main():
 started=time.perf_counter();_,chunks=_load_keyword_resources();report=audit_sources(chunks,DATA_FOLDER)
 report.update(seconds=round(time.perf_counter()-started,2),api_calls=0,source_files_modified=False,indexes_modified=False)
 (ROOT/'outputs/acceptance/document-source-consistency.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in {'cases','supported_files_without_indexed_chunks'}},indent=2))
 print('Supported source files without indexed chunks:',len(report['supported_files_without_indexed_chunks']))
if __name__=='__main__':main()
