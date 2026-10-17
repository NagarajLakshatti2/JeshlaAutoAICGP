import json
import os
import pickle
import requests

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = PROJECT_ROOT / "rag"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CONFIGURATION
# ============================================================

EVALUATION_FILE = "../rag/evaluation_questions.json"

FAISS_TOP_K = 15
BM25_TOP_K = 15
RERANK_TOP_K = 8

RERANK_MODEL = "BAAI/bge-reranker-base"

# OpenRouter
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Reuse the same FREE_MODELS list from your query.py
FREE_MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-30b-a3b:free"
]


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    print("\nWARNING: OPENROUTER_API_KEY not found in .env")


# ============================================================
# LOAD EVALUATION QUESTIONS
# ============================================================

with open(EVALUATION_FILE, "r", encoding="utf-8") as file:
    evaluation_questions = json.load(file)

print("\n========================================")
print("rag EVALUATION")
print("========================================")

print(f"Evaluation questions : {len(evaluation_questions)}")


# ============================================================
# LOAD BM25
# ============================================================

print("\nLoading BM25...")

with open("../rag/bm25.pkl", "rb") as file:
    bm25 = pickle.load(file)

print("BM25 loaded successfully.")


# ============================================================
# LOAD CHUNKS
# ============================================================

print("\nLoading chunks...")

with open("../rag/chunks.pkl", "rb") as file:
    chunks = pickle.load(file)

print(f"Chunks loaded : {len(chunks)}")


# ============================================================
# LOAD FAISS
# ============================================================

print("\nLoading FAISS...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vectorstore = FAISS.load_local(
    "../rag/faiss_db",
    embeddings,
    allow_dangerous_deserialization=True
)

print("FAISS loaded successfully.")


# ============================================================
# LOAD BGE RERANKER
# ============================================================

print("\nLoading BGE reranker...")

reranker = CrossEncoder(RERANK_MODEL)

print("BGE reranker loaded successfully.")


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
# HYBRID SEARCH
# ============================================================

def hybrid_search(
    query,
    faiss_k=FAISS_TOP_K,
    bm25_k=BM25_TOP_K
):

    # --------------------------------------------------------
    # FAISS
    # --------------------------------------------------------

    faiss_results = vectorstore.similarity_search_with_score(
        query,
        k=faiss_k
    )

    # --------------------------------------------------------
    # BM25
    # --------------------------------------------------------

    bm25_results = bm25_search(
        query,
        top_k=bm25_k
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    combined_results = []

    for doc, faiss_score in faiss_results:

        combined_results.append(
            (
                doc,
                float(faiss_score),
                "FAISS"
            )
        )

    for doc, bm25_score in bm25_results:

        combined_results.append(
            (
                doc,
                float(bm25_score),
                "BM25"
            )
        )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    unique_results = {}

    for doc, score, search_type in combined_results:

        key = (
            doc.metadata.get("source", ""),
            doc.metadata.get("page", ""),
            doc.page_content
        )

        if key not in unique_results:

            unique_results[key] = (
                doc,
                score,
                search_type
            )

    return list(unique_results.values())


# ============================================================
# BGE RERANKING
# ============================================================

def rerank_documents(query, results):

    if not results:
        return []

    pairs = [
        (query, doc.page_content)
        for doc, score, search_type in results
    ]

    rerank_scores = reranker.predict(pairs)

    reranked_results = []

    for (
        (doc, original_score, search_type),
        rerank_score
    ) in zip(results, rerank_scores):

        reranked_results.append(
            (
                doc,
                original_score,
                float(rerank_score),
                search_type
            )
        )

    reranked_results.sort(
        key=lambda x: x[2],
        reverse=True
    )

    return reranked_results


# ============================================================
# SOURCE MATCH
# ============================================================

def source_matches(doc, expected_source):

    actual_source = doc.metadata.get(
        "source",
        ""
    )

    return actual_source.lower() == expected_source.lower()


# ============================================================
# PAGE MATCH
# ============================================================

def page_matches(doc, expected_page):

    actual_page = doc.metadata.get(
        "page",
        ""
    )

    try:
        return int(actual_page) == int(expected_page)

    except (ValueError, TypeError):

        return str(actual_page) == str(expected_page)


# ============================================================
# FIND EXPECTED DOCUMENT
# ============================================================

def find_expected_document(
    results,
    expected_source,
    expected_page
):

    for rank, item in enumerate(results, start=1):

        doc = item[0]

        if (
            source_matches(doc, expected_source)
            and
            page_matches(doc, expected_page)
        ):

            return rank

    return None


# ============================================================
# OPENROUTER ANSWER GENERATION
# ============================================================

def generate_answer(
    question,
    retrieved_documents
):

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    context_parts = []

    for (
        doc,
        original_score,
        rerank_score,
        search_type
    ) in retrieved_documents:

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
Source: {source}
Page: {page}
Search Type: {search_type}

Content:
{doc.page_content}
"""
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are evaluating a Retrieval-Augmented Generation system.

Answer the user's question using ONLY the retrieved context.

Rules:
1. Do not invent information.
2. Do not use outside knowledge.
3. If the information is not available in the context,
   clearly say that it is not available.
4. Give a concise and factual answer.
5. Do not mention these evaluation instructions.

Question:
{question}

Retrieved Context:
{context}

Answer:
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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


# ============================================================
# KEYWORD EVALUATION
# ============================================================

def evaluate_keywords(
    answer,
    expected_keywords
):

    answer_lower = answer.lower()

    matched_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:

        keyword_lower = keyword.lower()

        if keyword_lower in answer_lower:

            matched_keywords.append(keyword)

        else:

            missing_keywords.append(keyword)

    total_keywords = len(expected_keywords)

    if total_keywords == 0:

        score = 0.0

    else:

        score = (
            len(matched_keywords)
            / total_keywords
        )

    return (
        matched_keywords,
        missing_keywords,
        score
    )


# ============================================================
# EVALUATE ONE QUESTION
# ============================================================

def evaluate_question(test_case):

    question = test_case["question"]

    expected_source = test_case[
        "expected_source"
    ]

    expected_page = test_case[
        "expected_page"
    ]

    expected_keywords = test_case.get(
        "expected_keywords",
        []
    )

    print("\n")
    print("=" * 70)
    print(
        f"TEST {test_case['id']}: {question}"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # HYBRID SEARCH
    # --------------------------------------------------------

    hybrid_results = hybrid_search(
        question,
        faiss_k=FAISS_TOP_K,
        bm25_k=BM25_TOP_K
    )

    print(
        f"\nHybrid Results : "
        f"{len(hybrid_results)}"
    )

    # --------------------------------------------------------
    # RERANK
    # --------------------------------------------------------

    reranked_results = rerank_documents(
        question,
        hybrid_results
    )

    top_results = reranked_results[
        :RERANK_TOP_K
    ]

    # --------------------------------------------------------
    # PRINT RERANKED RESULTS
    # --------------------------------------------------------

    print("\nTop Reranked Results:")

    for rank, item in enumerate(
        top_results,
        start=1
    ):

        (
            doc,
            original_score,
            rerank_score,
            search_type
        ) = item

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        page = doc.metadata.get(
            "page",
            "Unknown"
        )

        print(
            f"\nRank {rank}"
        )

        print(
            f"Source      : {source}"
        )

        print(
            f"Page        : {page}"
        )

        print(
            f"Search Type : {search_type}"
        )

        print(
            f"Original    : {original_score:.6f}"
        )

        print(
            f"BGE Score   : {rerank_score:.6f}"
        )

    # --------------------------------------------------------
    # EXPECTED DOCUMENT RANK
    # --------------------------------------------------------

    expected_rank = find_expected_document(
        top_results,
        expected_source,
        expected_page
    )

    if expected_rank is None:

        print(
            "\nExpected document/page "
            "was NOT found in Top 8."
        )

    else:

        print(
            f"\nExpected document/page "
            f"found at rank: {expected_rank}"
        )

    # --------------------------------------------------------
    # HIT @ K
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

    if top_results:

        top_doc = top_results[0][0]

        source_match = source_matches(
            top_doc,
            expected_source
        )

        page_match = page_matches(
            top_doc,
            expected_page
        )

    # --------------------------------------------------------
    # RETRIEVAL PASS
    # --------------------------------------------------------

    retrieval_pass = (
        expected_rank is not None
    )

    print("\nRetrieval Evaluation:")

    print(
        f"Expected Rank : {expected_rank}"
    )

    print(
        f"Hit@1         : "
        f"{'PASS' if hit_at_1 else 'FAIL'}"
    )

    print(
        f"Hit@3         : "
        f"{'PASS' if hit_at_3 else 'FAIL'}"
    )

    print(
        f"Hit@5         : "
        f"{'PASS' if hit_at_5 else 'FAIL'}"
    )

    print(
        f"Hit@8         : "
        f"{'PASS' if hit_at_8 else 'FAIL'}"
    )

    print(
        f"Source Match  : "
        f"{'PASS' if source_match else 'FAIL'}"
    )

    print(
        f"Page Match    : "
        f"{'PASS' if page_match else 'FAIL'}"
    )

    print(
        f"Retrieval     : "
        f"{'PASS' if retrieval_pass else 'FAIL'}"
    )

    # ========================================================
    # ANSWER GENERATION
    # ========================================================

    print("\nGenerating answer with OpenRouter...")

    try:

        answer, used_model = generate_answer(
            question,
            top_results
        )

        print(
            f"\nLLM Model: {used_model}"
        )

        print("\nGenerated Answer:")
        print("-" * 70)
        print(answer)
        print("-" * 70)

    except Exception as e:

        print(
            f"\nLLM answer generation failed:"
        )

        print(e)

        answer = ""
        used_model = "ERROR"

    # ========================================================
    # KEYWORD EVALUATION
    # ========================================================

    (
        matched_keywords,
        missing_keywords,
        keyword_score
    ) = evaluate_keywords(
        answer,
        expected_keywords
    )

    keyword_pass = (
        keyword_score == 1.0
    )

    print("\nAnswer Keyword Evaluation:")

    print(
        f"Expected Keywords : "
        f"{expected_keywords}"
    )

    print(
        f"Matched Keywords   : "
        f"{matched_keywords}"
    )

    print(
        f"Missing Keywords   : "
        f"{missing_keywords}"
    )

    print(
        f"Keyword Score      : "
        f"{len(matched_keywords)}/"
        f"{len(expected_keywords)}"
    )

    print(
        f"Keyword Accuracy   : "
        f"{keyword_score * 100:.2f}%"
    )

    print(
        f"Keyword Evaluation: "
        f"{'PASS' if keyword_pass else 'FAIL'}"
    )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {

        "id": test_case["id"],

        "question": question,

        # Retrieval
        "retrieval_pass": retrieval_pass,

        "expected_rank": expected_rank,

        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "hit_at_8": hit_at_8,

        "source_match": source_match,
        "page_match": page_match,

        # Answer
        "answer": answer,

        "model": used_model,

        "expected_keywords": expected_keywords,

        "matched_keywords": matched_keywords,

        "missing_keywords": missing_keywords,

        "keyword_score": keyword_score,

        "keyword_pass": keyword_pass
    }


# ============================================================
# RUN COMPLETE EVALUATION
# ============================================================

def run_evaluation():

    total_tests = len(
        evaluation_questions
    )

    retrieval_passed = 0

    hit_at_1_count = 0
    hit_at_3_count = 0
    hit_at_5_count = 0
    hit_at_8_count = 0

    source_match_count = 0
    page_match_count = 0

    keyword_passed = 0
    total_keyword_score = 0.0

    results = []

    # --------------------------------------------------------
    # RUN TESTS
    # --------------------------------------------------------

    for test_case in evaluation_questions:

        result = evaluate_question(
            test_case
        )

        results.append(result)

        # Retrieval
        if result["retrieval_pass"]:
            retrieval_passed += 1

        if result["hit_at_1"]:
            hit_at_1_count += 1

        if result["hit_at_3"]:
            hit_at_3_count += 1

        if result["hit_at_5"]:
            hit_at_5_count += 1

        if result["hit_at_8"]:
            hit_at_8_count += 1

        if result["source_match"]:
            source_match_count += 1

        if result["page_match"]:
            page_match_count += 1

        # Answer
        if result["keyword_pass"]:
            keyword_passed += 1

        total_keyword_score += (
            result["keyword_score"]
        )

    # --------------------------------------------------------
    # AVERAGE KEYWORD SCORE
    # --------------------------------------------------------

    if total_tests > 0:

        average_keyword_score = (
            total_keyword_score
            / total_tests
        )

    else:

        average_keyword_score = 0.0

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n\n")
    print("=" * 70)
    print("                 rag EVALUATION SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal Tests       : "
        f"{total_tests}"
    )

    print("\nRetrieval Metrics")
    print("-" * 70)

    print(
        f"Retrieval Passed  : "
        f"{retrieval_passed}/{total_tests}"
    )

    print(
        f"Retrieval Failed  : "
        f"{total_tests - retrieval_passed}/{total_tests}"
    )

    print(
        f"Hit@1             : "
        f"{hit_at_1_count}/{total_tests}"
    )

    print(
        f"Hit@3             : "
        f"{hit_at_3_count}/{total_tests}"
    )

    print(
        f"Hit@5             : "
        f"{hit_at_5_count}/{total_tests}"
    )

    print(
        f"Hit@8             : "
        f"{hit_at_8_count}/{total_tests}"
    )

    print(
        f"Source Accuracy   : "
        f"{source_match_count}/{total_tests}"
    )

    print(
        f"Page Accuracy     : "
        f"{page_match_count}/{total_tests}"
    )

    print("\nAnswer Metrics")
    print("-" * 70)

    print(
        f"Keyword Evaluation: "
        f"{keyword_passed}/{total_tests}"
    )

    print(
        f"Average Keyword Score : "
        f"{average_keyword_score * 100:.2f}%"
    )

    print("\n")
    print("=" * 70)
    print("rag EVALUATION COMPLETED")
    print("=" * 70)

    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_evaluation()