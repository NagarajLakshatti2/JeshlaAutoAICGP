"""Best-effort bounded stage logs without prompts, answers or raw errors."""
import json,os,threading
from datetime import datetime,timezone
from pathlib import Path
from agent.config.paths import APPLICATION_ROOT
_lock=threading.RLock()
_stages={'Router node','Project node','Complete agent workflow','LLM request','LLM tool request'}

def log_execution(event,name,*,span,status=None,duration=None,error=None):
    try:
        if event not in {'stage_started','stage_finished'}:return False
        record={'time':datetime.now(timezone.utc).isoformat(),'event':event,'pid':os.getpid(),'span':span,'stage':name if name in _stages else 'other','mode':'offline' if os.getenv('JESHLA_EXECUTION_MODE')=='offline' else 'runtime'}
        if status in {'SUCCESS','INCOMPLETE','FAILED','WAITING FOR INPUT','FAILED / INTERRUPTED'}:record['status']=status
        if isinstance(duration,(int,float)) and 0<=duration<86400:record['duration_seconds']=round(duration,3)
        if error is not None:
            record['error_kind']='application_error'
            categories={'CONFIGURATION','AUTHENTICATION','RATE_LIMIT','QUOTA_EXHAUSTED','TOOL_OUTPUT','OUTPUT_LIMIT','CONNECTION','CONNECT_TIMEOUT','RESPONSE_TIMEOUT','CONTEXT_PREFLIGHT','CONTEXT_LIMIT','INVALID_RESPONSE','PROVIDER_TEMPORARY'}
            category=getattr(error,'category',None)
            if category in categories:record.update(error_kind='provider_error',category=category)
            provider=getattr(error,'provider',None)
            if provider in {'groq','openrouter','ollama','gemini'}:record['provider']=provider
            status_code=getattr(error,'status',None)
            if type(status_code) is int and 100<=status_code<=599:record['http_status']=status_code
        directory=APPLICATION_ROOT/'outputs/logs';directory.mkdir(parents=True,exist_ok=True)
        path=directory/('execution-'+str(os.getpid())+'.jsonl')
        with _lock:
            if path.exists() and path.stat().st_size>2*1024*1024:
                old=path.with_suffix('.jsonl.1')
                if old.exists():os.replace(old,path.with_suffix('.jsonl.2'))
                os.replace(path,old)
            with path.open('a',encoding='utf-8') as handle:handle.write(json.dumps(record)+'\n')
        return True
    except Exception:return False
