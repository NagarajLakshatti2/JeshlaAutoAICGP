"""Shared FAISS + BM25 retrieval with BGE reranking."""

from functools import lru_cache
from pathlib import Path
import pickle
import hashlib
import re


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


@lru_cache(maxsize=1)
def _load_keyword_resources():
    # Only application-generated trusted local artifacts; never uploaded pickle.
    with (DATA_DIR / "bm25.pkl").open("rb") as handle:bm25=pickle.load(handle)
    with (DATA_DIR / "chunks.pkl").open("rb") as handle:chunks=pickle.load(handle)
    return bm25,chunks

def document_sources(top_results, *, context_chunks=None):
    sources=[]
    for (document,score,search_type),rerank_score in top_results:
        source=str(document.metadata.get("source") or "Unknown")[:256]
        page=document.metadata.get("page")
        file_type=str(document.metadata.get("file_type") or "unknown")[:30]
        text=document.page_content
        if context_chunks is not None:
            siblings=[item for item in context_chunks if item.metadata.get("source")==document.metadata.get("source") and item.metadata.get("page")==document.metadata.get("page")]
            position=next((i for i,item in enumerate(siblings) if item.page_content==document.page_content),None)
            if position is not None:
                neighbors=[siblings[i].page_content for distance in (1,2) for i in (position-distance,position+distance) if 0<=i<len(siblings)]
                text="\n\n".join([text,*neighbors])
        digest=hashlib.sha256((source+"|"+str(page)+"|"+text).encode()).hexdigest()[:16]
        sources.append({"ref":"DOC-"+digest,"source":source,"location":str(page)[:40] if page is not None else "Unknown","location_kind":"row" if file_type=="csv" else "page" if file_type=="pdf" else "section","retrieved_by":search_type,"text":text[:1800],"truncated":len(text)>1800})
    return {"sources":sources,"note":"Cite [DOC-id] exactly as returned with source/location. Indexed excerpts may be stale; metadata is not current-file verification or permission."}

_QUERY_STOPWORDS=set("a an the and or of to from in on at by for with is are was were be been being do does did have has had what which when where who whose how my our your his her their its it s".split())

def keyword_tokens(text):
    text=re.sub(r"['’]s\b","",text.casefold())
    return [word for word in re.findall(r"[^\W_]+",text) if word not in _QUERY_STOPWORDS]

@lru_cache(maxsize=1)
def _normalized_keyword_resources():
    from rank_bm25 import BM25Okapi
    _,chunks=_load_keyword_resources()
    tokens=[keyword_tokens(str(document.metadata.get("source", ""))+" "+document.page_content) for document in chunks]
    if not chunks or not any(tokens):raise ValueError("No keyword-searchable indexed text")
    return BM25Okapi(tokens),chunks

def bm25_search(query, top_k=BM25_TOP_K, *, normalized=False):
    """Search indexed chunks using keywords."""

    bm25, chunks = _normalized_keyword_resources() if normalized else _load_keyword_resources()

    tokenized_query = keyword_tokens(query) if normalized else query.lower().split()
    if not tokenized_query:return []

    scores = bm25.get_scores(tokenized_query)

    if len(scores)!=len(chunks):raise ValueError("Keyword index/chunk count mismatch")
    top_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )[:top_k]

    return [
        (chunks[index], float(scores[index]))
        for index in top_indexes if float(scores[index])>0
    ]


def execute_search_documents(query: str, *, structured=False, retrieval_mode="hybrid"):
    """Return retrieved context with source and page details."""

    if retrieval_mode not in {"hybrid","keyword"}:raise ValueError("Unsupported retrieval mode")
    if not query or not query.strip():
        return document_sources([]) if structured else ""
    if retrieval_mode=="hybrid":vectorstore, _, _, reranker = _load_resources()

    # 1. Semantic retrieval.
    faiss_results = vectorstore.similarity_search_with_score(query,k=FAISS_TOP_K) if retrieval_mode=="hybrid" else []

    # 2. Keyword retrieval.
    bm25_results = bm25_search(
        query,
        top_k=BM25_TOP_K, normalized=retrieval_mode=="keyword",
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
        return document_sources([]) if structured else ""

    # 4. Score each chunk against the query.
    pairs = [
        (query, document.page_content)
        for document, _, _ in unique_results
    ]

    rerank_scores = reranker.predict(pairs) if retrieval_mode=="hybrid" else [row[1] for row in unique_results]

    # 5. Sort by reranker score.
    reranked_results = sorted(
        zip(unique_results, rerank_scores),
        key=lambda item: item[1],
        reverse=True,
    )

    top_results = reranked_results[:RERANK_TOP_K]
    if structured:
        _,context_chunks=_load_keyword_resources()
        return {**document_sources(top_results,context_chunks=context_chunks),"retrieval_mode":retrieval_mode}

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