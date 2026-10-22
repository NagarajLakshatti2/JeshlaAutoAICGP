"""Shared RAG data/index defaults; never write inside an installed wheel."""
from agent.config.paths import DATA_ROOT as PROJECT_ROOT
RAG_DIR = PROJECT_ROOT / "rag"
DATA_FOLDER = RAG_DIR / "data"
FAISS_DB_FOLDER = RAG_DIR / "faiss_db"
BM25_FILE = RAG_DIR / "bm25.pkl"
CHUNKS_FILE = RAG_DIR / "chunks.pkl"
