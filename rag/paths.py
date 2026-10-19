"""Default RAG locations anchored to the installed source, never the shell folder."""
from pathlib import Path
RAG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RAG_DIR.parent
DATA_FOLDER = RAG_DIR / "data"
FAISS_DB_FOLDER = RAG_DIR / "faiss_db"
BM25_FILE = RAG_DIR / "bm25.pkl"
CHUNKS_FILE = RAG_DIR / "chunks.pkl"
