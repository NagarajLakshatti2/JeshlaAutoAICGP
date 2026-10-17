import json
import pickle
import requests
import os


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = PROJECT_ROOT / "rag"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONFIGURATION
# ============================================================

EVALUATION_FILE = "../rag/evaluation_questions.json"

BM25_TOP_K = 15

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FREE_MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-30b-a3b:free"
]


# ============================================================
# LOAD EVALUATION QUESTIONS
# ============================================================

print("\nLoading evaluation questions...")

with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
    evaluation_questions = json.load(file)

print(f"Evaluation questions loaded: {len(evaluation_questions)}")


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
            (
                chunks[index],
                float(scores[index])
            )
        )

    return results


# ============================================================
# SOURCE MATCH
# ============================================================

def source_matches(doc, expected_source):

    actual_source = doc.metadata.get("source", "")

    return actual_source.lower() == expected_source.lower()


# ============================================================
# PAGE MATCH
# ============================================================

def page_matches(doc, expected_page):

    actual_page = doc.metadata.get("page")

    return str(actual_page) == str(expected_page)


# ============================================================
# FIND EXPECTED DOCUMENT
# ============================================================

def find_expected_document(
    results,
    expected_source,
    expected_page
):

    for rank, (doc, score) in enumerate(results, start=1):

        if (
            source_matches(doc, expected_source)
            and
            page_matches(doc, expected_page)
        ):

            return rank, doc, score

    return None, None, None


# ============================================================
# KEYWORD EVALUATION
# ============================================================

def evaluate_keywords(answer, expected_keywords):

    answer_lower = answer.lower()

    matched_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:

        if keyword.lower() in answer_lower:

            matched_keywords.append(keyword)

        else:

            missing_keywords.append(keyword)

    total_keywords = len(expected_keywords)

    if total_keywords == 0:

        score = 0.0

    else:

        score = len(matched_keywords) / total_keywords

    return (
        matched_keywords,
        missing_keywords,
        score
    )


# ============================================================
# OPENROUTER ANSWER GENERATION
# ============================================================

def generate_answer(question, retrieved_documents):

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:

        print("\nWARNING: OPENROUTER_API_KEY not found.")

        return (
            "OpenRouter API key not configured.",
            "Unknown"
        )

    context_parts = []

    for rank, (doc, score) in enumerate(
        retrieved_documents,
        start=1
    ):

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
--- Retrieved Document {rank} ---
Source: {source}
Page: {page}

{doc.page_content}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are a rag evaluation assistant.

Answer the user's question using ONLY the retrieved context.

If the answer is not available in the context,
say that the information is not available.

Do not invent information.

User Question:
{question}

Retrieved Context:
{context}

Provide a clear and concise answer.
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

        answer = result["choices"][0]["message"]["content"]

        used_model = result.get(
            "model",
            "Unknown"
        )

        return answer, used_model

    except Exception as e:

        print(f"OpenRouter error: {e}")

        return (
            "Unable to generate answer.",
            "Unknown"
        )


# ============================================================
# EVALUATE ONE QUESTION
# ============================================================

def evaluate_question(question_data):

    question_id = question_data["id"]

    question = question_data["question"]

    expected_source = question_data["expected_source"]

    expected_page = question_data["expected_page"]

    expected_keywords = question_data["expected_keywords"]

    print("\n")
    print("=" * 80)

    print(f"TEST {question_id}")

    print("=" * 80)

    print(f"Question: {question}")

    print("\nSearching BM25...")

    results = bm25_search(
        question,
        BM25_TOP_K
    )

    # --------------------------------------------------------
    # PRINT TOP RESULTS
    # --------------------------------------------------------

    print("\nTop BM25 Results:")

    for rank, (doc, score) in enumerate(
        results,
        start=1
    ):

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        page = doc.metadata.get(
            "page",
            "Unknown"
        )

        print(
            f"{rank}. "
            f"{source} "
            f"(page {page}) "
            f"score={score:.4f}"
        )

    # --------------------------------------------------------
    # FIND EXPECTED DOCUMENT
    # --------------------------------------------------------

    expected_rank, expected_doc, expected_score = (
        find_expected_document(
            results,
            expected_source,
            expected_page
        )
    )

    # --------------------------------------------------------
    # HIT@K
    # --------------------------------------------------------

    hit_at_1 = (
        expected_rank is not None
        and expected_rank <= 1
    )

    hit_at_3 = (
        expected_rank is not None
        and expected_rank <= 3
    )

    hit_at_5 = (
        expected_rank is not None
        and expected_rank <= 5
    )

    hit_at_8 = (
        expected_rank is not None
        and expected_rank <= 8
    )

    # --------------------------------------------------------
    # SOURCE / PAGE
    # --------------------------------------------------------

    source_match = False
    page_match = False

    if expected_doc is not None:

        source_match = source_matches(
            expected_doc,
            expected_source
        )

        page_match = page_matches(
            expected_doc,
            expected_page
        )

    # --------------------------------------------------------
    # RETRIEVED DOCUMENTS FOR llm
    # --------------------------------------------------------

    # Use top 8 BM25 results for answer generation
    answer_documents = results[:8]

    print("\nGenerating answer using OpenRouter...")

    answer, used_model = generate_answer(
        question,
        answer_documents
    )

    # --------------------------------------------------------
    # KEYWORD EVALUATION
    # --------------------------------------------------------

    matched_keywords, missing_keywords, keyword_score = (
        evaluate_keywords(
            answer,
            expected_keywords
        )
    )

    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print("\n----------------------------------------")
    print("RETRIEVAL RESULT")
    print("----------------------------------------")

    if expected_rank is not None:

        print(
            f"Expected document rank: "
            f"{expected_rank}"
        )

        print(
            f"Expected score: "
            f"{expected_score:.4f}"
        )

    else:

        print(
            "Expected document was NOT found "
            "in Top 15."
        )

    print(
        f"Hit@1: {'PASS' if hit_at_1 else 'FAIL'}"
    )

    print(
        f"Hit@3: {'PASS' if hit_at_3 else 'FAIL'}"
    )

    print(
        f"Hit@5: {'PASS' if hit_at_5 else 'FAIL'}"
    )

    print(
        f"Hit@8: {'PASS' if hit_at_8 else 'FAIL'}"
    )

    print(
        f"Source Match: "
        f"{'PASS' if source_match else 'FAIL'}"
    )

    print(
        f"Page Match: "
        f"{'PASS' if page_match else 'FAIL'}"
    )

    print("\n----------------------------------------")
    print("GENERATED ANSWER")
    print("----------------------------------------")

    print(answer)

    print("\n----------------------------------------")
    print("ANSWER EVALUATION")
    print("----------------------------------------")

    print(
        f"Model: {used_model}"
    )

    print(
        f"Keyword Score: "
        f"{keyword_score:.2%}"
    )

    print(
        f"Matched Keywords: "
        f"{matched_keywords}"
    )

    print(
        f"Missing Keywords: "
        f"{missing_keywords}"
    )

    retrieval_pass = (
        expected_rank is not None
    )

    answer_pass = (
        keyword_score >= 0.70
    )

    print("\n----------------------------------------")
    print("TEST SUMMARY")
    print("----------------------------------------")

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
        "rank": expected_rank,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "hit_at_8": hit_at_8,
        "source_match": source_match,
        "page_match": page_match,
        "retrieval_pass": retrieval_pass,
        "keyword_score": keyword_score,
        "answer_pass": answer_pass,
        "model": used_model
    }


# ============================================================
# RUN FULL EVALUATION
# ============================================================

def run_evaluation():

    print("\n")
    print("=" * 80)
    print("BM25 rag EVALUATION")
    print("=" * 80)

    results = []

    for question_data in evaluation_questions:

        result = evaluate_question(
            question_data
        )

        results.append(result)

    # ========================================================
    # FINAL METRICS
    # ========================================================

    total = len(results)

    retrieval_passed = sum(
        r["retrieval_pass"]
        for r in results
    )

    answer_passed = sum(
        r["answer_pass"]
        for r in results
    )

    hit_at_1 = sum(
        r["hit_at_1"]
        for r in results
    )

    hit_at_3 = sum(
        r["hit_at_3"]
        for r in results
    )

    hit_at_5 = sum(
        r["hit_at_5"]
        for r in results
    )

    hit_at_8 = sum(
        r["hit_at_8"]
        for r in results
    )

    source_matches_count = sum(
        r["source_match"]
        for r in results
    )

    page_matches_count = sum(
        r["page_match"]
        for r in results
    )

    average_keyword_score = (
        sum(
            r["keyword_score"]
            for r in results
        ) / total
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print("\n\n")
    print("=" * 80)
    print("FINAL BM25 rag EVALUATION REPORT")
    print("=" * 80)

    print(f"\nTotal Tests       : {total}")

    print(
        f"Retrieval Passed  : "
        f"{retrieval_passed}/{total}"
    )

    print(
        f"Retrieval Failed  : "
        f"{total - retrieval_passed}/{total}"
    )

    print(
        f"Answer Passed     : "
        f"{answer_passed}/{total}"
    )

    print(
        f"Answer Failed     : "
        f"{total - answer_passed}/{total}"
    )

    print(
        f"\nHit@1             : "
        f"{hit_at_1}/{total} "
        f"({hit_at_1 / total:.1%})"
    )

    print(
        f"Hit@3             : "
        f"{hit_at_3}/{total} "
        f"({hit_at_3 / total:.1%})"
    )

    print(
        f"Hit@5             : "
        f"{hit_at_5}/{total} "
        f"({hit_at_5 / total:.1%})"
    )

    print(
        f"Hit@8             : "
        f"{hit_at_8}/{total} "
        f"({hit_at_8 / total:.1%})"
    )

    print(
        f"\nSource Accuracy   : "
        f"{source_matches_count}/{total} "
        f"({source_matches_count / total:.1%})"
    )

    print(
        f"Page Accuracy     : "
        f"{page_matches_count}/{total} "
        f"({page_matches_count / total:.1%})"
    )

    print(
        f"\nAverage Keyword Score : "
        f"{average_keyword_score:.2%}"
    )

    print("\n")
    print("=" * 80)
    print("EVALUATION COMPLETED")
    print("=" * 80)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_evaluation()