"""Validate web reference traceability, not claim entailment or page contents."""
import re
from urllib.parse import urlsplit

def visible_web_urls(result,visible_text):
    urls=set()
    if not isinstance(result,dict) or result.get("error"):return urls
    rows=result.get("results",[])
    if not isinstance(rows,list):return urls
    for row in rows:
        url=row.get("url") if isinstance(row,dict) else None
        if not isinstance(url,str) or url not in visible_text:continue
        try:
            parts=urlsplit(url)
            if parts.scheme in {"http","https"} and parts.hostname and not parts.username and not parts.password:urls.add(url)
        except ValueError:continue
    return urls

def citation_issue(content,urls,*,enforce_web=False):
    # Example URLs inside code blocks are not prose citations.
    text=re.sub(r"```.*?```","",content,flags=re.S)
    if re.search(r"【[^】]*(?:functions\.|commentary:|web_search|turn\d+)[^】]*】",text):
        return "Invented internal citation markers are not usable sources."
    cited=set()
    for match in re.finditer(r"https?://[^\s<>\]\"']+",text):
        url=match.group(0).rstrip(".,;!?")
        # Markdown closes a link with a right parenthesis; preserve any that
        # belong to a balanced URL path.
        while url.endswith(")") and url.count(")")>url.count("("):url=url[:-1]
        cited.add(url)
    if (urls or enforce_web) and cited-urls:return "Answer contains a URL not returned in the visible web evidence."
    if urls and not cited:return "Answer uses web evidence without a source URL."
    return None


def visible_document_refs(result,visible_text):
    if not isinstance(result,dict) or result.get("error"):return set()
    import json
    refs=set()
    for row in result.get("sources",[]) if isinstance(result.get("sources"),list) else []:
        if not isinstance(row,dict):continue
        ref=row.get("ref");text=row.get("text")
        if isinstance(ref,str) and re.fullmatch(r"DOC-[a-f0-9]{16}",ref) and isinstance(text,str) and text.strip() and ref in visible_text and json.dumps(text[:64],ensure_ascii=False)[1:-1] in visible_text:refs.add(ref)
    return refs

def document_citation_issue(content,refs):
    text=re.sub(r"```.*?```","",content,flags=re.S)
    cited=set(re.findall(r"\[(DOC-[A-Za-z0-9_-]+)\]",text))
    if cited-refs:return "Document reference was not returned in visible indexed evidence."
    if refs and not cited:return "Indexed-document answer needs a returned [DOC-id] reference."
    return None


def append_read_sources(content,urls):
    """Supply absent source labels from actual read evidence, without rewriting prose.

    This does not verify claims. Unknown citations still require correction and
    technical review remains mandatory after this deterministic formatting step.
    """
    if citation_issue(content,urls)!="Answer uses web evidence without a source URL.":return content
    links="\n".join("- [Page read "+str(index)+"]("+url+")" for index,url in enumerate(sorted(urls),1))
    return content+"\n\nSources read (bounded excerpts):\n"+links
