# Installation dependency audit

Updated 18 October 2026. Source-based declaration audit completed for current core startup, supported table/document ingestion and existing FAISS/BM25 retrieval. This is not clean-install or all-feature certification.

| Import | Distribution | Existing use |
|---|---|---|
| requests | requests | Provider HTTP calls |
| dotenv | python-dotenv | Local provider settings |
| langgraph | langgraph | Agent graph |
| langgraph.checkpoint.sqlite | langgraph-checkpoint-sqlite | Persistent checkpoints |
| prompt_toolkit | prompt_toolkit | Editable console input |
| streamlit | streamlit | Browser interface |
| ddgs | ddgs | Public search |
| openpyxl | openpyxl | XLSX tables |
| pypdf | pypdf | PDF ingestion and source audit |
| docx | python-docx | Word ingestion and source audit |
| langchain_huggingface | langchain-huggingface | Embedding adapter |
| langchain_core | langchain-core | Document records |
| langchain_text_splitters | langchain-text-splitters | Chunking |
| faiss | faiss-cpu | Vector index |
| rank_bm25 | rank-bm25 | Keyword index |
| sentence_transformers | sentence-transformers | Embeddings/reranker |

Existing langchain/community/Ollama and Chroma declarations remain intact for examples and prototypes. No environment packages were added or upgraded. Optional Jira/MCP imports mcp, httpx2 and pydantic are declared in requirements-integrations.txt; their integration/API compatibility is not accepted by this audit.

## Clean-install rehearsal procedure

Use a separate empty directory and fresh virtual environment, without system-site-packages. Install the current requirements from a package index or a prepared wheelhouse, run pip check, then run the offline suite against an isolated project copy that excludes real .env, user databases and action receipts. Use synthetic configuration and no provider calls. Confirm imports, console startup and Streamlit startup before any live provider acceptance. Do not build indexes or download embedding models as an import smoke check.

The current no-index dry-run has no available langchain distribution and therefore cannot verify installation. A connected installation may download large ML dependencies and requires a bounded separate run. Do not relabel this as an incompatibility, an actual installation attempt, or a passed release gate. Exact version locking and fresh Python/platform compatibility remain pending until the clean install is exercised.

Stored local indexes use trusted application-generated pickle files; package installation does not validate index compatibility or corpus quality. Preserve source documents and existing indexes before rebuilding.

## Installation profiles and clean core acceptance

requirements-core.txt provides console/browser, provider HTTP, state, public search and editable input. requirements-rag.txt includes core plus document/table parsers, embeddings and FAISS/BM25. requirements.txt includes RAG and retains langchain, langchain-ollama and chromadb for existing examples. requirements-integrations.txt remains separate for optional Jira/MCP. All previously declared full-profile packages are retained. The working environment was not modified.

A fresh isolated Windows Python 3.14.0 core install passed in 80.23 seconds: pip install, pip check, console --help startup, and Streamlit AppTest initial rendering without errors. Source-only copies excluded real .env, databases, indexes, uploads and receipts. Offline guards blocked provider requests during startup checks. Report outputs/acceptance/workstream-8-core-install.json; log workstream-8-core-install.log. The temporary environment was removed after acceptance.

This verifies dependencies and startup for the core profile only; it is not a full fresh-environment regression run, live provider task, browser action workflow or optional RAG install/model-load acceptance. Version pinning remains pending; fresh resolution may differ on later dates.
