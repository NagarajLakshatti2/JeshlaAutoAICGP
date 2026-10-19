"""Local indexed-text consistency checks; no model calls and no source text in reports."""
import csv
from pathlib import Path
import zipfile

SUPPORTED={'.pdf','.txt','.docx','.csv'}

def normalize(text):
    return ' '.join(str(text).casefold().split())

def read_locations(path):
    suffix=path.suffix.casefold()
    if suffix=='.txt':return {'1':path.read_text(encoding='utf-8',errors='ignore')},False
    if suffix=='.pdf':
        from pypdf import PdfReader
        with path.open('rb') as handle:
            reader=PdfReader(handle)
            if len(reader.pages)>200:raise ValueError('page_limit')
            return {str(i):page.extract_text() or '' for i,page in enumerate(reader.pages,1)},False
    if suffix=='.docx':
        with zipfile.ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist())>50_000_000:raise ValueError('expanded_size_limit')
        from docx import Document
        document=Document(path)
        return {'1':'\n'.join(p.text for p in document.paragraphs if p.text.strip())},False
    if suffix=='.csv':
        locations={}
        with path.open(encoding='utf-8-sig',newline='') as handle:
            for i,row in enumerate(csv.DictReader(handle),2):
                if i>20001:return locations,True
                locations[str(i)]='\n'.join(f'{column}: {value}' for column,value in row.items() if value is not None and str(value).strip())
        return locations,False
    raise ValueError('unsupported_format')

def audit_sources(chunks,data_folder,*,max_chunks=1000,max_file_bytes=5_000_000):
    root=Path(data_folder).resolve();cache={};rows=[]
    for chunk in chunks[:max_chunks]:
        meta=chunk.metadata;source=meta.get('source');location=str(meta.get('page','1'));status='unverified';reason=None
        if not isinstance(source,str) or not source or len(source)>256 or '/' in source or '\\' in source or source.startswith('.'):
            reason='invalid_source_name';source='[invalid source]'
        elif Path(source).suffix.casefold() not in SUPPORTED:reason='unsupported_format'
        else:
            if source not in cache:
                path=root/source
                try:
                    if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('source_outside_corpus')
                    if not path.is_file():raise ValueError('source_missing')
                    if path.stat().st_size>max_file_bytes:raise ValueError('file_size_limit')
                    texts,partial=read_locations(path);cache[source]=(texts,partial,None)
                except ValueError as error:
                    allowed={'source_outside_corpus','source_missing','file_size_limit','page_limit','expanded_size_limit','unsupported_format'}
                    cache[source]=({},False,str(error) if str(error) in allowed else 'source_read_failed')
                except Exception:cache[source]=({},False,'source_read_failed')
            texts,partial,reason=cache[source]
            if not reason:
                excerpt=normalize(chunk.page_content)
                if not excerpt:reason='empty_indexed_excerpt'
                elif location not in texts:reason='location_outside_scan' if partial else 'location_missing'
                elif excerpt in normalize(texts[location]):status='matches_current_text'
                else:status='text_mismatch';reason='indexed_excerpt_not_in_current_location'
        rows.append({'source':source,'location':location[:40],'status':status,'reason':reason})
    counts={key:sum(row['status']==key for row in rows) for key in ['matches_current_text','text_mismatch','unverified']}
    indexed={row['source'] for row in rows}
    unindexed=[]
    if root.is_dir():unindexed=sorted(p.name for p in root.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.casefold() in SUPPORTED and not p.name.startswith('.') and p.name not in indexed)
    return {'status':'Y - indexed excerpt consistency only' if rows and not counts['text_mismatch'] and not counts['unverified'] and len(chunks)<=max_chunks else 'P','indexed_chunks':len(chunks),'checked_chunks':len(rows),'coverage_truncated':len(chunks)>max_chunks,'counts':counts,'cases':rows,'supported_files_without_indexed_chunks':unindexed,'note':'Whitespace/case-normalized excerpt containment at the indexed location. Not a full-file hash, semantic relevance, external freshness or proof that all current source content is indexed. DOCX paragraphs only; CSV record numbers including the header. XLSX is served separately by table tools.'}
