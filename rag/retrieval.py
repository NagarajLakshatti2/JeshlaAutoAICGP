"""Shared FAISS + BM25 retrieval with BGE reranking."""

from functools import lru_cache
from pathlib import Path
import pickle


FAISS_TOP_K = 10
BM25_TOP_K = 15
RERANK_TOP_K = 3

RERANK_MODEL = "BAAI/bge-reranker-base"

# Always resolve indexes relative to this file.
DATA_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _load_resources():
    """Load resources once and reuse them for later queries."""

    required_files = [
        DATA_DIR / "faiss_db" / "index.faiss",
        DATA_DIR / "faiss_db" / "index.pkl",
        DATA_DIR / "bm25.pkl",
        DATA_DIR / "chunks.pkl",
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing RAG indexes: "
            + ", ".join(missing_files)
            + ". Run your ingestion workflow first."
        )

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from sentence_transformers import CrossEncoder

    print("\nLoading embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    print("\nLoading FAISS index...")

    # Load only indexes produced by your own trusted ingestion.
    vectorstore = FAISS.load_local(
        str(DATA_DIR / "faiss_db"),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    print("\nLoading BM25 and chunks...")

    with (DATA_DIR / "bm25.pkl").open("rb") as file:
        bm25 = pickle.load(file)

    with (DATA_DIR / "chunks.pkl").open("rb") as file:
        chunks = pickle.load(file)

    if not chunks:
        raise ValueError(
            "The RAG index contains no document chunks."
        )

    print("\nLoading BGE reranker...")

    reranker = CrossEncoder(RERANK_MODEL)

    print("\nRAG resources loaded successfully.")

    return vectorstore, bm25, chunks, reranker


def bm25_search(query, top_k=BM25_TOP_K):
    """Search indexed chunks using keywords."""

    _, bm25, chunks, _ = _load_resources()

    tokenized_query = query.lower().split()

    scores = bm25.get_scores(tokenized_query)

    top_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )[:top_k]

    return [
        (chunks[index], float(scores[index]))
        for index in top_indexes
    ]


def execute_search_documents(query: str) -> str:
    """Return retrieved context with source and page details."""

    if not query or not query.strip():
        return ""

    vectorstore, _, _, reranker = _load_resources()

    # 1. Semantic retrieval.
    faiss_results = vectorstore.similarity_search_with_score(
        query,
        k=FAISS_TOP_K,
    )

    # 2. Keyword retrieval.
    bm25_results = bm25_search(
        query,
        top_k=BM25_TOP_K,
    )

    # 3. Combine and remove duplicate chunks.
    seen = {}

    for search_type, results in [
        ("FAISS", faiss_results),
        ("BM25", bm25_results),
    ]:
        for document, score in results:
            key = (
                document.metadata.get("source", ""),
                document.metadata.get("page", ""),
                document.page_content,
            )

            if key not in seen:
                seen[key] = (
                    document,
                    float(score),
                    search_type,
                )

    unique_results = list(seen.values())

    if not unique_results:
        return ""

    # 4. Score each chunk against the query.
    pairs = [
        (query, document.page_content)
        for document, _, _ in unique_results
    ]

    rerank_scores = reranker.predict(pairs)

    # 5. Sort by reranker score.
    reranked_results = sorted(
        zip(unique_results, rerank_scores),
        key=lambda item: item[1],
        reverse=True,
    )

    top_results = reranked_results[:RERANK_TOP_K]

    # 6. Build context for the LangGraph answer node.
    context_parts = []

    for index, (
        (document, original_score, search_type),
        rerank_score,
    ) in enumerate(top_results, start=1):

        context_parts.append(
            f"\nSOURCE {index}\n"
            f"File: {document.metadata.get('source', 'Unknown')}\n"
            f"Page: {document.metadata.get('page', 'Unknown')}\n"
            f"Retrieved By: {search_type}\n"
            f"Reranker Score: {float(rerank_score):.4f}\n"
            f"Content:\n{document.page_content}"
        )

    print(
        f"\nRetrieved {len(unique_results)} unique chunks; "
        f"selected {len(top_results)} after reranking."
    )

    return "\n".join(context_parts)