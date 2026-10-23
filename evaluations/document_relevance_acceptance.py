"""Explicit local BM25 relevance check with independently supplied source labels.

No model/API calls or index changes. Expectations are validated against current
source files before searching, never inferred or corrected from retrieved hits.
Reports omit queries and excerpts; this is retrieval coverage, not entailment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalized(value):
    return " ".join(value.casefold().split())


def score_case(case, result):
    sources = result.get("sources", [])
    if case["source"] is None:
        checks = {"no_keyword_candidates": not sources}
    else:
        matches = [row for row in sources if row.get("source") == case["source"] and str(row.get("location")) == case["location"]]
        text = normalized(" ".join(row.get("text", "") for row in matches))
        checks = {"expected_source_and_location": bool(matches), "expected_visible_fragments": bool(matches) and all(normalized(part) in text for part in case["expected_fragments"]),
                  "valid_structured_references": bool(matches) and all(re.fullmatch(r"DOC-[0-9a-f]{16}", row.get("ref", "")) is not None for row in matches)}
    return {"id": case["id"], "passed": all(checks.values()), "checks": checks,
            "retrieved": [{"source": row.get("source"), "location": row.get("location"), "truncated": row.get("truncated")} for row in sources]}


def artifact_hashes(paths):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from tests.run_offline import offline_guard
    from rag import retrieval
    from rag.paths import DATA_FOLDER
    from rag.source_audit import read_locations
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases or len(cases) > 100:
        raise ValueError("Provide 1 to 100 explicit benchmark cases.")
    cache = {}; labels = []
    for case in cases:
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError("Every case needs a question.")
        source = case["source"]
        if source is None:
            if case["expected_fragments"] or case["location"] is not None:
                raise ValueError("Absent-keyword case labels must have no source/location/fragments.")
            continue
        if not isinstance(source, str) or source.startswith(".") or "/" in source or "\\" in source:
            raise ValueError("Use a single supported source filename.")
        path = DATA_FOLDER / source
        if path.is_symlink() or not path.resolve().is_relative_to(DATA_FOLDER.resolve()) or not path.is_file() or path.stat().st_size > 20000000:
            raise ValueError("Source must be a bounded existing file inside the corpus.")
        if source not in cache:
            locations, partial = read_locations(path)
            if partial:
                raise ValueError("Partial source reads cannot certify labels.")
            cache[source] = locations
        body = normalized(cache[source].get(case["location"], ""))
        fragments = case["expected_fragments"]
        valid = bool(body) and bool(fragments) and all(isinstance(part, str) and part.strip() and normalized(part) in body for part in fragments)
        labels.append({"id": case["id"], "matches_current_source": valid})
        if not valid:
            raise ValueError("A benchmark label does not match its declared current source/location; labels were not changed.")
    paths = [DATA_FOLDER / name for name in cache] + [retrieval.DATA_DIR / "bm25.pkl", retrieval.DATA_DIR / "chunks.pkl"]
    before = artifact_hashes(paths)
    start = time.monotonic(); rows = []
    with offline_guard():
        for case in cases:
            result = retrieval.execute_search_documents(case["question"], structured=True, retrieval_mode="keyword")
            rows.append(score_case(case, result))
    report = {"status": "Y" if all(row["passed"] for row in rows) else "P", "total": len(rows), "passed": sum(row["passed"] for row in rows), "cases": rows,
              "source_label_checks": labels, "labels_inferred_from_retrieval": False, "source_and_index_files_unchanged": artifact_hashes(paths) == before,
              "provider_requests": 0, "model_loads": 0, "network": "blocked", "mode": "keyword", "seconds": round(time.monotonic() - start, 2),
              "scope": "New finite source/location/visible-fragment coverage across explicit local documents, plus out-of-corpus keyword queries. Not hybrid ranking, answer entailment, semantic paraphrase or general abstention acceptance."}
    if not report["source_and_index_files_unchanged"]:
        report["status"] = "P"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "Y" else 1


if __name__ == "__main__":
    raise SystemExit(main())
