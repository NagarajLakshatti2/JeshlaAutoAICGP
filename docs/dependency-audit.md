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

## WS8 current-source build/install follow-up — 21 October 2026

Y for an offline prepared-source sdist/wheel build and audit: current helpers/aliases and entry point are included, declared dependency profiles match metadata, and synthetic private-data canaries are excluded. P for the latest-source fresh editable install: build-dependency acquisition timed out before install/startup/tests. Earlier core-install evidence retains its historical scope. Working packages/provider settings are unchanged and disposable fixtures/processes were cleaned up. This is not wheel-runtime, full/RAG, Git-publication or full-release acceptance. See workstream-8-release.md and outputs/acceptance/ws8-source-build-current/result.json; the failed install is recorded separately under ws8-core-fresh-20261020. The reusable runner lives in evaluations/core_install_acceptance.py. Next prerequisite is reliable package access or a prepared local wheelhouse, not another unchanged download attempt.


## WS8 local-wheelhouse recovery — 21 October 2026

Y for latest-source fresh core editable installation and selected acceptance. Public package access recovered: two build-tool wheels downloaded in 2.90 seconds and core dependencies in 45.17 seconds (74 wheels total). A new Windows Python 3.14.0 environment, with no system-site-packages, installed exclusively from these wheels with build isolation enabled and the package index disabled. Pip check, the legacy module --help and installed jeshla-auto-ai --help passed. All 222 selected offline regressions passed in 68.679 seconds, and the actual Streamlit AppTest initial screen rendered without errors with newly resolved Streamlit 1.66.0. Total successful rehearsal: 257.26 seconds, including setup and cleanup. This is selected synthetic core acceptance, not the entire project suite, real-browser/provider acceptance, optional RAG installation or fresh GitHub-clone acceptance.

The first wheelhouse rehearsal passed installation and entry points, then exposed a runner-only metadata lookup error: editable source egg-info shadowed installed dist-info. The runner now checks the fresh environment's installed metadata and exact editable source URL. That earlier report is retained under ws8-core-wheelhouse-20261021; the corrected successful run is ws8-core-wheelhouse-fixed-20261021/result.json. No application implementation was changed. Working package and .env fingerprints remained unchanged, no real settings or persistent user data were copied, and disposable fixtures and owned processes were cleaned up. No provider/model requests ran; tests blocked external requests in their Python process.

The reusable runner remains evaluations/core_install_acceptance.py; --wheelhouse selects downloaded wheels and --output-dir preserves previous reports. Wheel filenames and SHA-256 hashes are recorded in the successful report. The wheelhouse is a local Windows/Python-specific acceptance cache, not a universal dependency lock or publishing artifact. The earlier timeout is historical and no longer blocks scoped core editable setup. Full/RAG setup, broader WS2/WS3/WS4 quality, non-editable wheel runtime/data roots, release scope and general release completion remain pending. Workstream 8 stays I; Word synchronization is not claimed.

## Optional profile acceptance and remaining gates on 21 October 2026

Y for fresh RAG plus integration package installation, dependency consistency and both console entry points. Public resolution selected 129 distributions; the local cache contains 131 wheel files including the earlier build tools. The first installation reached its 300-second cap while installing packages. Deferring install-time bytecode compilation with --no-compile then passed installation in 72.80 seconds. A further fresh run with separately bounded ML import repeated installation successfully in 142.54 seconds. These timings are observations, not a guaranteed speedup. Python may compile bytecode on first use; no working environment or dependency versions were changed to obtain these results.

Y for 246 selected offline regressions (88.051 seconds), zero failures/errors, and actual Streamlit AppTest initial rendering in the fresh Python 3.14.0 / Streamlit 1.66.0 environment. The 246 include the earlier 222 selected core checks; do not add these counts. Eleven optional imports passed, including openpyxl, pypdf, docx, FAISS, LangChain adapters, MCP, httpx2 and the actual Jira client module. No authentication or live Jira session was started. Real temporary TXT/DOCX/CSV ingestion produced three chunks, saved/reopened FAISS and BM25 indexes and returned the expected synthetic sources. A blank generated PDF was opened successfully; this does not certify arbitrary PDF extraction. The vector smoke deliberately uses fixture embeddings, not a pretrained model or a semantic-quality benchmark.

P for the optional ML runtime/import gate: direct sentence_transformers import did not finish within 180 seconds in the first runtime attempt. The evaluator now isolates that import in an owned child with a 45-second cap, allowing unrelated parser/index and regression checks to finish. That child timed out at 45.60 seconds and stopped. The final report is intentionally pending/nonzero despite all 246 regressions passing. Its worker status reflects the incomplete optional runtime gate, not a failed regression. Total final rehearsal 388.01 seconds, including setup and cleanup. No model downloads occurred. Working package/.env fingerprints remained unchanged; disposable environments and owned processes were removed.

Evidence: outputs/acceptance/ws8-rag-resolution-20261021, ws8-rag-fresh-20261021, ws8-rag-no-compile-20261021 and ws8-rag-bounded-import-20261021/result.json. Existing evaluations/core_install_acceptance.py gained --profile rag and --no-compile, scoped optional imports and synthetic parser/index checks; no application implementation or flat agent module was added. The Windows/Python-specific wheel cache and exact resolution list are acceptance evidence, not a universal lock file. Full learning-profile installation, non-editable wheel runtime, GitHub-clone acceptance and broad WS2/WS3/WS4 quality remain unaccepted. Word synchronization is not claimed.

A separate live synthetic Groq memory review passed three cases: equal-authority conflict with both values and clarification, different projects, and different years. The fourth case hit HTTP 429 and the run stopped; five of eight cases remain unfinished. The evaluator previously rejected a complete JSON Markdown code block. It now accepts only a single complete JSON fence or plain JSON for semantic scoring and records plain-JSON request compliance separately. The three semantic passes used fences and do not establish plain-JSON compliance. Seven positive/negative parser checks and the eight scripted offline fixtures passed; these validate the harness, not additional live model cases. No private user histories or real project facts were sent, and temporary databases were unchanged and removed. Evidence: outputs/acceptance/ws3-memory-review-groq-all.json and ws8-memory-quality-probe-20261021. Groq quota remains the observed live-evaluation blocker; no persistent provider switch or blocked fallback retry was made.

Workstream 8 remains I. Setup is no longer the unresolved core/RAG installation issue: remaining work is optional ML runtime and broader quality/release gates. Keep existing Y scope and parked P items distinct; do not rerun the same heavy import or rate-limited requests without a changed prerequisite or a targeted diagnostic.

## Follow-up on 21 October 2026

OpenRouter synthetic connectivity verified; one-model baseline 7/8, then live follow-up blocked by exact-source formatting and HTTP 429 quota exhaustion. Generic scope guidance passed 61 focused and 246 fresh offline tests; its targeted live role acceptance is unfinished. Cached real MiniLM sample passed 8/8 locally. Fresh RAG runtime still has a 60-second cold sentence-transformers import timeout; its 246 tests, other imports, parser/index smoke and UI startup passed. Working packages and .env stayed unchanged. Workstream 8 remains I; details and evidence are in workstream-8-release.md and workstream-3-memory.md. Word is not synchronized by this update.
