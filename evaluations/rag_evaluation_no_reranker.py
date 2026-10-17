import json
import os
import pickle
import requests

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


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
FINAL_TOP_K = 8

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

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
    raise ValueError(
        "OPENROUTER_API_KEY not found in .env file."
    )


# ============================================================
# LOAD BM25
# ============================================================

print("\nLoading BM25 database...")

with open("../rag/bm25.pkl", "rb") as file:
    bm25 = pickle.load(file)


# ============================================================
# LOAD CHUNKS
# ============================================================

print("Loading chunks...")

with open("../rag/chunks.pkl", "rb") as file:
    chunks = pickle.load(file)


# ============================================================
# LOAD FAISS
# ============================================================

print("Loading FAISS database...")

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

    faiss_results = vectorstore.similarity_search_with_score(
        query,
        k=faiss_k
    )

    bm25_results = bm25_search(
        query,
        top_k=bm25_k
    )

    combined_results = []

    # FAISS results

    for doc, faiss_score in faiss_results:

        combined_results.append(
            (
                doc,
                float(faiss_score),
                "FAISS"
            )
        )

    # BM25 results

    for doc, bm25_score in bm25_results:

        combined_results.append(
            (
                doc,
                float(bm25_score),
                "BM25"
            )
        )

    # Remove duplicates

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
        "page"
    )

    return str(actual_page) == str(expected_page)


# ============================================================
# FIND EXPECTED DOCUMENT
# ============================================================

def find_expected_document(
    results,
    expected_source,
    expected_page
):

    for rank, (doc, score, search_type) in enumerate(
        results,
        start=1
    ):

        if (
            source_matches(doc, expected_source)
            and
            page_matches(doc, expected_page)
        ):

            return rank, doc

    return None, None


# ============================================================
# GENERATE ANSWER USING OPENROUTER
# ============================================================

def generate_answer(
    question,
    retrieved_documents
):

    context_parts = []

    for index, (doc, score, search_type) in enumerate(
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
Document {index}

Source: {source}
Page: {page}
Search Type: {search_type}

Content:
{doc.page_content}
"""
        )

    context = "\n".join(context_parts)

    prompt = f"""
You are answering a question using retrieved documents.

Question:
{question}

Retrieved Context:
{context}

Instructions:

1. Answer only using the retrieved context.
2. Do not invent information.
3. Give a concise factual answer.
4. If the information is not available, say so.
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

    answer = result[
        "choices"
    ][0][
        "message"
    ][
        "content"
    ]

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

    return (
        matched_keywords,
        missing_keywords,
        score
    )


# ============================================================
# EVALUATE ONE QUESTION
# ============================================================

def evaluate_question(question_data):

    question = question_data["question"]

    expected_source = question_data[
        "expected_source"
    ]

    expected_page = question_data[
        "expected_page"
    ]

    expected_keywords = question_data[
        "expected_keywords"
    ]

    print("\n")
    print("=" * 70)

    print(
        f"Test {question_data['id']}"
    )

    print(
        f"Question: {question}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # HYBRID RETRIEVAL
    # --------------------------------------------------------

    results = hybrid_search(
        question,
        faiss_k=FAISS_TOP_K,
        bm25_k=BM25_TOP_K
    )

    print(
        f"\nHybrid results: {len(results)}"
    )

    # --------------------------------------------------------
    # FINAL TOP K
    # --------------------------------------------------------

    final_results = results[
        :FINAL_TOP_K
    ]

    print(
        f"Using top {len(final_results)} documents."
    )

    # --------------------------------------------------------
    # DISPLAY RETRIEVAL
    # --------------------------------------------------------

    for rank, (
        doc,
        score,
        search_type
    ) in enumerate(
        final_results,
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
            f"{source} | "
            f"Page {page} | "
            f"{search_type}"
        )

    # --------------------------------------------------------
    # EXPECTED DOCUMENT
    # --------------------------------------------------------

    expected_rank, expected_doc = find_expected_document(
        results,
        expected_source,
        expected_page
    )

    hit1 = expected_rank is not None and expected_rank <= 1
    hit3 = expected_rank is not None and expected_rank <= 3
    hit5 = expected_rank is not None and expected_rank <= 5
    hit8 = expected_rank is not None and expected_rank <= 8

    source_found = expected_rank is not None

    page_found = expected_rank is not None

    retrieval_pass = (
        source_found
        and
        page_found
    )

    print(
        f"\nExpected Source: {expected_source}"
    )

    print(
        f"Expected Page: {expected_page}"
    )

    print(
        f"Expected Rank: {expected_rank}"
    )

    print(
        f"Hit@1: {hit1}"
    )

    print(
        f"Hit@3: {hit3}"
    )

    print(
        f"Hit@5: {hit5}"
    )

    print(
        f"Hit@8: {hit8}"
    )

    # --------------------------------------------------------
    # ANSWER GENERATION
    # --------------------------------------------------------

    print(
        "\nGenerating answer with OpenRouter..."
    )

    answer, used_model = generate_answer(
        question,
        final_results
    )

    print(
        f"Model: {used_model}"
    )

    print("\nAnswer:")
    print(answer)

    # --------------------------------------------------------
    # KEYWORD EVALUATION
    # --------------------------------------------------------

    (
        matched_keywords,
        missing_keywords,
        keyword_score
    ) = evaluate_keywords(
        answer,
        expected_keywords
    )

    print(
        "\nMatched Keywords:"
    )

    print(
        matched_keywords
    )

    print(
        "\nMissing Keywords:"
    )

    print(
        missing_keywords
    )

    print(
        f"\nKeyword Score: "
        f"{keyword_score:.2%}"
    )

    return {
        "id": question_data["id"],
        "question": question,
        "expected_source": expected_source,
        "expected_page": expected_page,
        "expected_rank": expected_rank,

        "hit_at_1": hit1,
        "hit_at_3": hit3,
        "hit_at_5": hit5,
        "hit_at_8": hit8,

        "source_match": source_found,
        "page_match": page_found,
        "retrieval_pass": retrieval_pass,

        "answer": answer,
        "model": used_model,

        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "keyword_score": keyword_score
    }


# ============================================================
# RUN EVALUATION
# ============================================================

def run_evaluation():

    print("\n")
    print("=" * 70)
    print("rag EVALUATION")
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD QUESTIONS
    # --------------------------------------------------------

    with open(
        EVALUATION_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        questions = json.load(file)

    print(
        f"\nEvaluation questions: "
        f"{len(questions)}"
    )

    # --------------------------------------------------------
    # RUN TESTS
    # --------------------------------------------------------

    results = []

    for question_data in questions:

        result = evaluate_question(
            question_data
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    total = len(results)

    retrieval_passed = sum(
        r["retrieval_pass"]
        for r in results
    )

    hit1 = sum(
        r["hit_at_1"]
        for r in results
    )

    hit3 = sum(
        r["hit_at_3"]
        for r in results
    )

    hit5 = sum(
        r["hit_at_5"]
        for r in results
    )

    hit8 = sum(
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

    average_keyword_score = sum(
        r["keyword_score"]
        for r in results
    ) / total

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FINAL rag EVALUATION REPORT")
    print("=" * 70)

    print(
        f"\nTotal Tests       : {total}"
    )

    print(
        f"Retrieval Passed  : "
        f"{retrieval_passed}/{total}"
    )

    print(
        f"Retrieval Failed  : "
        f"{total - retrieval_passed}/{total}"
    )

    print(
        f"\nHit@1             : "
        f"{hit1}/{total} "
        f"({hit1 / total:.2%})"
    )

    print(
        f"Hit@3             : "
        f"{hit3}/{total} "
        f"({hit3 / total:.2%})"
    )

    print(
        f"Hit@5             : "
        f"{hit5}/{total} "
        f"({hit5 / total:.2%})"
    )

    print(
        f"Hit@8             : "
        f"{hit8}/{total} "
        f"({hit8 / total:.2%})"
    )

    print(
        f"\nSource Accuracy   : "
        f"{source_matches_count}/{total} "
        f"({source_matches_count / total:.2%})"
    )

    print(
        f"Page Accuracy     : "
        f"{page_matches_count}/{total} "
        f"({page_matches_count / total:.2%})"
    )

    print(
        f"\nAverage Keyword Score : "
        f"{average_keyword_score:.2%}"
    )

    print(
        "\n" + "=" * 70
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_evaluation()