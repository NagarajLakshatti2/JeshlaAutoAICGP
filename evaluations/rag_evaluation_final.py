import json
import pickle
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = PROJECT_ROOT / "rag"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

with open(RAG_DIR / "bm25.pkl", "rb") as file:
    bm25 = pickle.load(file)

with open(RAG_DIR / "chunks.pkl", "rb") as file:
    chunks = pickle.load(file)

# ============================================================
# CONFIGURATION
# ============================================================

EVALUATION_FILE = RAG_DIR / "evaluation_questions.json"

BM25_TOP_K = 15
ANSWER_TOP_K = 8

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FREE_MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-30b-a3b:free"
]


OUTPUT_FILE = OUTPUT_DIR / "rag_evaluation_final_results.json"
REPORT_FILE = OUTPUT_DIR / "rag_evaluation_final_report.txt"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOAD EVALUATION QUESTIONS
# ============================================================

print("\nLoading evaluation questions...")

with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
    evaluation_questions = json.load(file)

print(
    f"Evaluation questions loaded: "
    f"{len(evaluation_questions)}"
)


# ============================================================
# LOAD BM25
# ============================================================

print("\nLoading BM25 database...")

with open("../rag/bm25.pkl", "rb") as file:
    bm25 = pickle.load(file)

print("BM25 database loaded successfully.")


# ============================================================
# LOAD CHUNKS
# ============================================================

print("\nLoading chunks...")

with open("../rag/chunks.pkl", "rb") as file:
    chunks = pickle.load(file)

print(f"Chunks loaded: {len(chunks)}")


# ============================================================
# BM25 SEARCH
# ============================================================

def bm25_search(query, top_k=BM25_TOP_K):

    tokenized_query = query.lower().split()

    scores = bm25.get_scores(tokenized_query)

    top_indexes = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = []

    for index in top_indexes:

        results.append(
            {
                "doc": chunks[index],
                "score": float(scores[index]),
                "rank": len(results) + 1
            }
        )

    return results


# ============================================================
# SOURCE MATCH
# ============================================================

def source_matches(doc, expected_source):

    actual_source = doc.metadata.get(
        "source",
        ""
    )

    return (
        actual_source.lower()
        ==
        expected_source.lower()
    )


# ============================================================
# PAGE MATCH
# ============================================================

def page_matches(doc, expected_page):

    actual_page = doc.metadata.get(
        "page"
    )

    return (
        str(actual_page)
        ==
        str(expected_page)
    )


# ============================================================
# FIND EXPECTED DOCUMENT
# ============================================================

def find_expected_document(
    results,
    expected_source,
    expected_page
):

    for item in results:

        doc = item["doc"]

        if (
            source_matches(
                doc,
                expected_source
            )
            and
            page_matches(
                doc,
                expected_page
            )
        ):

            return item

    return None


# ============================================================
# 15.6 — llm ANSWER GENERATION
# ============================================================

def generate_answer(
    question,
    retrieved_documents
):

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        print(
            "\nERROR: "
            "OPENROUTER_API_KEY not found."
        )

        return {
            "answer": "",
            "model": "Unknown",
            "success": False,
            "error": "OPENROUTER_API_KEY not found"
        }

    context_parts = []

    for item in retrieved_documents:

        doc = item["doc"]
        rank = item["rank"]
        score = item["score"]

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        page = doc.metadata.get(
            "page",
            "Unknown"
        )

        context_parts.append(
            f"""
--- Retrieved Chunk {rank} ---
Source: {source}
Page: {page}
BM25 Score: {score:.4f}

{doc.page_content}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are an evaluation assistant for a Retrieval-Augmented
Generation system.

Answer the user's question using ONLY the retrieved context.

Rules:
1. Do not invent information.
2. Do not use outside knowledge.
3. If the answer is not available in the context,
   clearly say that it is not available.
4. Give a concise factual answer.
5. Include relevant dates, company names, roles,
   technologies, or clients when present.

User Question:
{question}

Retrieved Context:
{context}

Answer:
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "models": FREE_MODELS,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=data,
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        answer = (
            result
            ["choices"]
            [0]
            ["message"]
            ["content"]
        )

        used_model = result.get(
            "model",
            "Unknown"
        )

        return {
            "answer": answer.strip(),
            "model": used_model,
            "success": True,
            "error": None
        }

    except Exception as e:

        print(
            f"\nOpenRouter error: {e}"
        )

        return {
            "answer": "",
            "model": "Unknown",
            "success": False,
            "error": str(e)
        }


# ============================================================
# 15.7 — KEYWORD EVALUATION
# ============================================================

def evaluate_keywords(
    answer,
    expected_keywords
):

    answer_lower = answer.lower()

    matched_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:

        if keyword.lower() in answer_lower:

            matched_keywords.append(
                keyword
            )

        else:

            missing_keywords.append(
                keyword
            )

    total_keywords = len(
        expected_keywords
    )

    if total_keywords == 0:

        score = 0.0

    else:

        score = (
            len(matched_keywords)
            /
            total_keywords
        )

    return {
        "matched": matched_keywords,
        "missing": missing_keywords,
        "score": score
    }


# ============================================================
# RETRIEVAL METRICS
# ============================================================

def calculate_retrieval_metrics(
    results,
    expected_source,
    expected_page
):

    expected_item = find_expected_document(
        results,
        expected_source,
        expected_page
    )

    if expected_item is None:

        rank = None

    else:

        rank = expected_item["rank"]

    return {
        "expected_rank": rank,
        "hit_at_1": (
            rank is not None
            and rank <= 1
        ),
        "hit_at_3": (
            rank is not None
            and rank <= 3
        ),
        "hit_at_5": (
            rank is not None
            and rank <= 5
        ),
        "hit_at_8": (
            rank is not None
            and rank <= 8
        ),
        "source_match": (
            expected_item is not None
        ),
        "page_match": (
            expected_item is not None
        )
    }


# ============================================================
# 15.6 + 15.7 — EVALUATE ONE QUESTION
# ============================================================

def evaluate_question(
    question_data
):

    question_id = question_data["id"]

    question = question_data["question"]

    expected_source = (
        question_data["expected_source"]
    )

    expected_page = (
        question_data["expected_page"]
    )

    expected_keywords = (
        question_data["expected_keywords"]
    )

    print("\n")
    print("=" * 80)
    print(f"TEST {question_id}")
    print("=" * 80)

    print(
        f"Question: {question}"
    )

    # --------------------------------------------------------
    # BM25
    # --------------------------------------------------------

    print("\nRunning BM25 retrieval...")

    results = bm25_search(
        question,
        BM25_TOP_K
    )

    print("\nTop BM25 Results:")

    for item in results:

        doc = item["doc"]

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        page = doc.metadata.get(
            "page",
            "Unknown"
        )

        print(
            f'{item["rank"]}. '
            f'{source} '
            f'(page {page}) '
            f'score={item["score"]:.4f}'
        )

    # --------------------------------------------------------
    # RETRIEVAL METRICS
    # --------------------------------------------------------

    retrieval = calculate_retrieval_metrics(
        results,
        expected_source,
        expected_page
    )

    # --------------------------------------------------------
    # ANSWER GENERATION
    # --------------------------------------------------------

    print(
        "\n15.6 — Generating llm answer..."
    )

    answer_result = generate_answer(
        question,
        results[:ANSWER_TOP_K]
    )

    answer = answer_result["answer"]

    # --------------------------------------------------------
    # KEYWORD EVALUATION
    # --------------------------------------------------------

    print(
        "\n15.7 — Evaluating answer keywords..."
    )

    keyword_result = evaluate_keywords(
        answer,
        expected_keywords
    )

    # --------------------------------------------------------
    # PRINT ANSWER
    # --------------------------------------------------------

    print("\n" + "-" * 80)
    print("GENERATED ANSWER")
    print("-" * 80)

    if answer:

        print(answer)

    else:

        print(
            "No answer generated."
        )

    # --------------------------------------------------------
    # PRINT ANSWER METRICS
    # --------------------------------------------------------

    print("\n" + "-" * 80)
    print("ANSWER EVALUATION")
    print("-" * 80)

    print(
        f"Model: "
        f'{answer_result["model"]}'
    )

    print(
        f'Keyword Score: '
        f'{keyword_result["score"]:.2%}'
    )

    print(
        f'Matched Keywords: '
        f'{keyword_result["matched"]}'
    )

    print(
        f'Missing Keywords: '
        f'{keyword_result["missing"]}'
    )

    answer_pass = (
        answer_result["success"]
        and
        keyword_result["score"] >= 0.70
    )

    print(
        f"Answer Result: "
        f"{'PASS' if answer_pass else 'FAIL'}"
    )

    # --------------------------------------------------------
    # FINAL TEST RESULT
    # --------------------------------------------------------

    retrieval_pass = (
        retrieval["expected_rank"]
        is not None
    )

    print("\n" + "-" * 80)
    print("TEST SUMMARY")
    print("-" * 80)

    print(
        f"Retrieval: "
        f"{'PASS' if retrieval_pass else 'FAIL'}"
    )

    print(
        f"Answer: "
        f"{'PASS' if answer_pass else 'FAIL'}"
    )

    return {
        "id": question_id,
        "question": question,

        "retrieval": retrieval,

        "answer": {
            "text": answer,
            "model": answer_result["model"],
            "success": answer_result["success"],
            "error": answer_result["error"]
        },

        "keywords": {
            "expected": expected_keywords,
            "matched": keyword_result["matched"],
            "missing": keyword_result["missing"],
            "score": keyword_result["score"]
        },

        "retrieval_pass": retrieval_pass,
        "answer_pass": answer_pass
    }


# ============================================================
# 15.8 — HYBRID BASELINE
# ============================================================

def get_previous_hybrid_baseline():

    return {
        "name": "Hybrid + BGE Reranker",

        "total_tests": 8,

        "hit_at_1": 5,
        "hit_at_3": 8,
        "hit_at_5": 8,
        "hit_at_8": 8,

        "source_accuracy": 8,
        "page_accuracy": 8,

        "retrieval_passed": 8,

        "retrieval_failed": 0
    }


# ============================================================
# 15.8 — COMPARE BM25 VS HYBRID
# ============================================================

def compare_bm25_hybrid(
    results
):

    hybrid = get_previous_hybrid_baseline()

    total = len(results)

    bm25_hit1 = sum(
        r["retrieval"]["hit_at_1"]
        for r in results
    )

    bm25_hit3 = sum(
        r["retrieval"]["hit_at_3"]
        for r in results
    )

    bm25_hit5 = sum(
        r["retrieval"]["hit_at_5"]
        for r in results
    )

    bm25_hit8 = sum(
        r["retrieval"]["hit_at_8"]
        for r in results
    )

    bm25_source = sum(
        r["retrieval"]["source_match"]
        for r in results
    )

    bm25_page = sum(
        r["retrieval"]["page_match"]
        for r in results
    )

    comparison = {

        "bm25": {
            "hit_at_1": bm25_hit1,
            "hit_at_3": bm25_hit3,
            "hit_at_5": bm25_hit5,
            "hit_at_8": bm25_hit8,
            "source_accuracy": bm25_source,
            "page_accuracy": bm25_page
        },

        "hybrid": hybrid
    }

    return comparison


# ============================================================
# 15.9 — FINAL REPORT
# ============================================================

def generate_final_report(
    results,
    comparison
):

    total = len(results)

    retrieval_passed = sum(
        r["retrieval_pass"]
        for r in results
    )

    answer_passed = sum(
        r["answer_pass"]
        for r in results
    )

    answer_scores = [
        r["keywords"]["score"]
        for r in results
        if r["answer"]["success"]
    ]

    if answer_scores:

        average_keyword_score = (
            sum(answer_scores)
            /
            len(answer_scores)
        )

    else:

        average_keyword_score = 0.0

    bm25 = comparison["bm25"]
    hybrid = comparison["hybrid"]

    lines = []

    lines.append(
        "=" * 80
    )

    lines.append(
        "FINAL rag EVALUATION REPORT"
    )

    lines.append(
        "=" * 80
    )

    lines.append("")

    lines.append(
        "15.6 llm ANSWER GENERATION"
    )

    lines.append(
        "-" * 80
    )

    lines.append(
        f"Tests with successful llm answer: "
        f"{len(answer_scores)}/{total}"
    )

    lines.append(
        f"Tests with failed llm answer: "
        f"{total - len(answer_scores)}/{total}"
    )

    lines.append(
        f"Average Keyword Score: "
        f"{average_keyword_score:.2%}"
    )

    lines.append("")

    lines.append(
        "15.7 KEYWORD EVALUATION"
    )

    lines.append(
        "-" * 80
    )

    lines.append(
        f"Answer Passed: "
        f"{answer_passed}/{total}"
    )

    lines.append(
        f"Answer Failed: "
        f"{total - answer_passed}/{total}"
    )

    lines.append("")

    lines.append(
        "15.8 BM25 VS HYBRID + BGE"
    )

    lines.append(
        "-" * 80
    )

    lines.append(
        f"{'Metric':<20}"
        f"{'BM25':<15}"
        f"{'Hybrid+BGE':<15}"
    )

    lines.append(
        f"{'Hit@1':<20}"
        f"{bm25['hit_at_1']}/{total} "
        f"({bm25['hit_at_1']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_1']}/{total} "
        f"({hybrid['hit_at_1']/total:.1%})"
    )

    lines.append(
        f"{'Hit@3':<20}"
        f"{bm25['hit_at_3']}/{total} "
        f"({bm25['hit_at_3']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_3']}/{total} "
        f"({hybrid['hit_at_3']/total:.1%})"
    )

    lines.append(
        f"{'Hit@5':<20}"
        f"{bm25['hit_at_5']}/{total} "
        f"({bm25['hit_at_5']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_5']}/{total} "
        f"({hybrid['hit_at_5']/total:.1%})"
    )

    lines.append(
        f"{'Hit@8':<20}"
        f"{bm25['hit_at_8']}/{total} "
        f"({bm25['hit_at_8']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_8']}/{total} "
        f"({hybrid['hit_at_8']/total:.1%})"
    )

    lines.append(
        f"{'Source Accuracy':<20}"
        f"{bm25['source_accuracy']}/{total} "
        f"({bm25['source_accuracy']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['source_accuracy']}/{total} "
        f"({hybrid['source_accuracy']/total:.1%})"
    )

    lines.append(
        f"{'Page Accuracy':<20}"
        f"{bm25['page_accuracy']}/{total} "
        f"({bm25['page_accuracy']/total:.1%})"
        f"{'':<5}"
        f"{hybrid['page_accuracy']}/{total} "
        f"({hybrid['page_accuracy']/total:.1%})"
    )

    lines.append("")

    lines.append(
        "15.9 FINAL EVALUATION"
    )

    lines.append(
        "-" * 80
    )

    lines.append(
        f"BM25 Retrieval Passed: "
        f"{retrieval_passed}/{total}"
    )

    lines.append(
        f"llm Answer Passed: "
        f"{answer_passed}/{total}"
    )

    lines.append("")

    lines.append(
        "Important:"
    )

    lines.append(
        "Hybrid+BGE metrics are the previously "
        "validated retrieval baseline."
    )

    lines.append(
        "The current Windows environment cannot "
        "execute PyTorch because Windows Code "
        "Integrity blocks c10.dll."
    )

    lines.append(
        "Therefore BM25 is being used as the "
        "temporary executable evaluation path."
    )

    lines.append("")

    lines.append(
        "Evaluation pipeline:"
    )

    lines.append(
        "Evaluation Questions"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "BM25 Retrieval"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "Top 8 Context"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "OpenRouter llm"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "Generated Answer"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "Keyword Evaluation"
    )

    lines.append(
        "        ↓"
    )

    lines.append(
        "Final Metrics"
    )

    lines.append(
        "=" * 80
    )

    report = "\n".join(lines)

    return report


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    results,
    comparison
):

    output = {
        "evaluation": {
            "total_tests": len(results),
            "retrieval_results": results
        },

        "comparison": comparison
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nJSON results saved: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 80)
    print("rag EVALUATION — STAGE 15.6 → 15.9")
    print("=" * 80)

    results = []

    # --------------------------------------------------------
    # RUN ALL TESTS
    # --------------------------------------------------------

    for question_data in evaluation_questions:

        result = evaluate_question(
            question_data
        )

        results.append(result)

    # --------------------------------------------------------
    # 15.8
    # --------------------------------------------------------

    print("\n")
    print("=" * 80)
    print("15.8 — BM25 VS HYBRID COMPARISON")
    print("=" * 80)

    comparison = compare_bm25_hybrid(
        results
    )

    bm25 = comparison["bm25"]
    hybrid = comparison["hybrid"]

    print(
        f"\n{'Metric':<20}"
        f"{'BM25':<20}"
        f"{'Hybrid+BGE':<20}"
    )

    print(
        f"{'Hit@1':<20}"
        f"{bm25['hit_at_1']}/8 "
        f"({bm25['hit_at_1']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_1']}/8 "
        f"({hybrid['hit_at_1']/8:.1%})"
    )

    print(
        f"{'Hit@3':<20}"
        f"{bm25['hit_at_3']}/8 "
        f"({bm25['hit_at_3']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_3']}/8 "
        f"({hybrid['hit_at_3']/8:.1%})"
    )

    print(
        f"{'Hit@5':<20}"
        f"{bm25['hit_at_5']}/8 "
        f"({bm25['hit_at_5']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_5']}/8 "
        f"({hybrid['hit_at_5']/8:.1%})"
    )

    print(
        f"{'Hit@8':<20}"
        f"{bm25['hit_at_8']}/8 "
        f"({bm25['hit_at_8']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['hit_at_8']}/8 "
        f"({hybrid['hit_at_8']/8:.1%})"
    )

    print(
        f"{'Source Accuracy':<20}"
        f"{bm25['source_accuracy']}/8 "
        f"({bm25['source_accuracy']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['source_accuracy']}/8 "
        f"({hybrid['source_accuracy']/8:.1%})"
    )

    print(
        f"{'Page Accuracy':<20}"
        f"{bm25['page_accuracy']}/8 "
        f"({bm25['page_accuracy']/8:.1%})"
        f"{'':<5}"
        f"{hybrid['page_accuracy']}/8 "
        f"({hybrid['page_accuracy']/8:.1%})"
    )

    # --------------------------------------------------------
    # 15.9
    # --------------------------------------------------------

    report = generate_final_report(
        results,
        comparison
    )

    print("\n")
    print(report)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_json(
        results,
        comparison
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(report)

    print(
        f"\nFinal report saved: "
        f"{REPORT_FILE}"
    )

    print("\n")
    print("=" * 80)
    print("STAGE 15.6 → 15.9 COMPLETED")
    print("=" * 80)


if __name__ == "__main__":

    main()