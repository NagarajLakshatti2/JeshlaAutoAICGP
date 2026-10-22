"""Local bounded browser activity logs; never record messages or exception text."""
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from agent.config.paths import DATA_ROOT as ROOT
EVENTS={"action_approved","action_declined","page_render","chat_created","chat_switched","chats_refreshed","memory_viewed","download_clicked","message_started","message_finished","error"}

class QuietHandler(RotatingFileHandler):
    def handleError(self,record):
        # A diagnostic log failure must not interrupt the agent or echo its record.
        pass

@lru_cache(maxsize=8)
def _logger(root):
    path=Path(root)/"outputs/logs/browser-activity.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger("jeshla.browser."+hashlib.sha256(str(path).encode()).hexdigest())
    logger.setLevel(logging.INFO);logger.propagate=False
    if not logger.handlers:
        handler=QuietHandler(path,maxBytes=1048576,backupCount=3,encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"));logger.addHandler(handler)
    return logger

def log_browser_event(event, *, session=None, provider=None, duration=None, turns=None, error=None, root=None, route=None):
    """Allowlisted metadata only. Chat references are stable hashes, not titles."""
    if event not in EVENTS:return False
    record={"time":datetime.now(timezone.utc).isoformat(),"event":event}
    if isinstance(session,str):record["chat_ref"]=hashlib.sha256(session.encode()).hexdigest()[:16]
    if provider in {"groq","openrouter","ollama","gemini"}:record["provider"]=provider
    if isinstance(duration,(float,int)) and 0<=duration<86400:record["duration_seconds"]=round(duration,3)
    if type(turns) is int and 0<=turns:record["turn_count"]=turns
    if route in {"direct","web","rag","memory","memory_command","project","jira","jira_workflow","clarify"}:record["route"]=route
    if error is not None:
        from agent.providers.errors import ProviderError
        record["error_type"]="provider_error" if isinstance(error,ProviderError) else "application_error"
        if isinstance(error,ProviderError):
            if type(error.status) is int and 100<=error.status<=599:record["http_status"]=error.status
            categories={"TOOL_OUTPUT","CONFIGURATION","QUOTA_EXHAUSTED","RATE_LIMIT","AUTHENTICATION","CONNECTION","RESPONSE_TIMEOUT","CONTEXT_PREFLIGHT","OUTPUT_LIMIT"}
            if error.category in categories:record["category"]=error.category
    try:
        _logger(str(Path(root) if root is not None else ROOT)).info(json.dumps(record,separators=(",",":")))
        return True
    except Exception:
        return False
