"""Bounded public snippet search with one changed-engine recovery attempt."""
from urllib.parse import urlparse
from agent.runtime.timing import timed


@timed("Web search")
def web_search(query):
    try:
        from ddgs import DDGS
    except ImportError:
        return {"error":"Web search dependency missing. Run python -m pip install ddgs in your agent environment.","task_status":"incomplete"}
    attempts=[]
    for backend in ("duckduckgo","brave"):
        try:
            # Each engine is selected explicitly. DDGS auto can silently fan
            # out across many engines; its timeout is not a global deadline.
            rows=DDGS(timeout=5).text(query,max_results=5,backend=backend)
            results=[]
            for row in rows:
                if not isinstance(row,dict):continue
                url=str(row.get("href") or row.get("url") or "")
                parts=urlparse(url)
                if parts.scheme not in {"http","https"} or not parts.hostname or parts.username is not None or parts.password is not None:continue
                results.append({"title":str(row.get("title",""))[:300],"url":url,"snippet":str(row.get("body",""))[:1200]})
            attempts.append({"backend":backend,"status":"results" if results else "empty"})
            if results:
                return {"results":results,"attempts":attempts,"note":"Search snippets only; full pages have not been read."}
        except Exception:
            attempts.append({"backend":backend,"status":"unavailable"})
    return {"error":"Both bounded search backends returned no usable links or were unavailable. Try a shorter official-domain query or provide the documentation URL.","attempts":attempts,"task_status":"incomplete"}
