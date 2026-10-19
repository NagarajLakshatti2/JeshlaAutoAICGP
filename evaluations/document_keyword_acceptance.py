"""Local keyword relevance baseline; preserves original and audited label results."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rag.retrieval import execute_search_documents,_load_keyword_resources

def normalized(text):return " ".join(text.casefold().split())
def main():
    start=time.perf_counter();cases=json.loads((ROOT/"rag/evaluation_questions.json").read_text(encoding="utf-8"));_,chunks=_load_keyword_resources()
    rows=[]
    for case in cases:
        pages={}
        for document in chunks:
            if document.metadata.get("source")==case["expected_source"]:pages.setdefault(str(document.metadata.get("page")),[]).append(document.page_content)
        supported=[page for page,texts in pages.items() if all(normalized(word) in normalized(" ".join(texts)) for word in case["expected_keywords"])]
        original=str(case["expected_page"])
        audited=supported[0] if original not in supported and len(supported)==1 else original
        result=execute_search_documents(case["question"],structured=True,retrieval_mode="keyword")
        def check(page):
            matching=[source for source in result["sources"] if source["source"]==case["expected_source"] and source["location"]==page]
            text=normalized(" ".join(source["text"] for source in matching))
            return bool(matching) and all(normalized(word) in text for word in case["expected_keywords"])
        rows.append({"id":case["id"],"original_expected_page":original,"audited_page":audited,"label_corrected":original!=audited,"original_pass":check(original),"audited_pass":check(audited),"retrieved_locations":[{"source":s["source"],"location":s["location"]} for s in result["sources"]]})
    report={"mode":"normalized_keyword","original_passed":sum(row["original_pass"] for row in rows),"audited_passed":sum(row["audited_pass"] for row in rows),"total":len(rows),"cases":rows,"seconds":round(time.perf_counter()-start,2),"api_calls":0,"note":"Page-label auditing uses existing indexed corpus, not a source-file reread. Original benchmark file is unchanged. Source/keyword coverage is not claim entailment."}
    report["status"]="Y" if report["audited_passed"]==len(rows) else "P"
    output=ROOT/"outputs/acceptance/document-keyword-normalized.json";output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
