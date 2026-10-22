# Developer installation and package boundaries

The supported restructuring workflow uses an editable source checkout on Windows Python 3.14, keeping APPLICATION_ROOT anchored to the checkout. Existing python -m agent.langgraph.langgraph_agent and python -m streamlit run streamlit_app.py commands remain supported. The new console entry point is jeshla-auto-ai after editable installation.

```powershell
python -m pip install -e .
```

Optional profiles: `python -m pip install -e ".[rag]"` for document/retrieval packages, `[learning]` for retained learning adapters, `[integrations]` for existing Jira/MCP adapters. Requirements files remain supported; base package dependencies read requirements-core.txt. No credential, database, receipt, generated output or user document should be packaged as application data.

## Settings and data locations — 23 October 2026

`APPLICATION_ROOT` locates installed Python code. `DATA_ROOT` locates `.env`, saved chats, checkpoints, memory, action receipts, logs, RAG data/indexes and generated exports. The supported interfaces, RAG defaults and integrated Jira helpers share that data root. Code imports and the public-page worker continue to use the code location.

| Startup mode | Default data location |
|---|---|
| Source checkout containing this project's `pyproject.toml` and `agent/config/paths.py` | Existing checkout root; current commands and saved data stay in place |
| Installed wheel on Windows | `%LOCALAPPDATA%\JeshlaAutoAI` (home/AppData/Local fallback) |
| Installed wheel on other platforms | `$XDG_DATA_HOME/jeshlaautoai`, or `~/.local/share/jeshlaautoai` |
| Explicit `JESHLA_HOME` environment setting | The absolute directory selected before process startup |

The inspected repository is still configured independently with `AI_PROJECT_ROOT` or the user's project declaration. It never implicitly changes the application's settings/data folder. The shell's current directory also does not select a settings file or persistent store. Importing the path resolver creates no directories or databases; explicit first store use creates its parent folders.

Existing source users do not need to set `JESHLA_HOME`. To deliberately select another store, set it in the launching process, for example:

```powershell
$env:JESHLA_HOME = Join-Path $env:LOCALAPPDATA "JeshlaAutoAI"
python -m agent.langgraph.langgraph_agent
```

Create/configure `.env` inside the chosen folder when needed. `JESHLA_HOME` is read before `.env` is loaded, so putting it only inside `.env` cannot relocate that same file. Relative overrides are rejected. Changing the data folder selects a different store; existing files are not moved, copied, merged or deleted. Do not use the inspected project's path as a data-root setting by implication.

The non-editable wheel/data-root behavior now has an offline installed-artifact smoke using the existing working dependencies, both default and explicit-home scenarios, real console memory commands and the browser backend. Dependency-isolated fresh core-wheel installation now also passes, including pip check, both console entry points, actual memory persistence and an initial Streamlit AppTest render. Actual UI clicks, optional ML loading, fresh GitHub-clone setup and full release acceptance remain separate. See outputs/acceptance/ws8-fresh-wheel-20261023/result.json. Earlier editable-install and archive-only milestones below retain their historical scopes. See `outputs/acceptance/ws8-data-roots-20261023/wheel/result.json` and `evaluations/wheel_runtime_acceptance.py`.


Package boundaries: interfaces adapt user input/output; runtime coordinates turns/graph lifecycle; providers perform bounded model requests; storage persists chats; actions validate/propose/execute approved operations; memory stores scoped facts; policies apply deterministic rules; config anchors current application paths. Existing tools, RAG and integrations retain their roles. Compatibility aliases keep old imports working; avoid duplicating implementations in wrappers.

Backup remains private outside the active checkout. Do not commit .env, checkpoints, user chats or receipts. Repository tracked-state cleanup is a separate pending task; adding packaging exclusions does not untrack files or sanitize Git history.


## Remaining top-level helper cleanup - 19 October 2026

Y for the bounded implementation relocation: all 13 remaining active top-level helpers now live in existing child packages. No additional package layer was needed. Top-level agent/*.py files, apart from __init__.py, are compatibility forwarders only; they intentionally remain so existing imports and patches continue to work. New code should import the canonical modules below. Never duplicate implementation inside a wrapper or delete a wrapper without separately checking its external callers.

| Previous import (retained) | Canonical implementation |
|---|---|
| `agent.browser_action_ui` | `agent.interfaces.action_approval` |
| `agent.browser_activity` | `agent.interfaces.activity` |
| `agent.citation_guard` | `agent.policies.citations` |
| `agent.clarification_guard` | `agent.policies.clarification` |
| `agent.project_budget` | `agent.runtime.project_budget` |
| `agent.project_context` | `agent.runtime.project_context` |
| `agent.project_decisions` | `agent.runtime.project_decisions` |
| `agent.project_native_specs` | `agent.runtime.project_native_specs` |
| `agent.terminal_input` | `agent.interfaces.terminal_input` |
| `agent.timing` | `agent.runtime.timing` |
| `agent.user_errors` | `agent.interfaces.errors` |
| `agent.web_page_worker` | `agent.tools.web_page_worker` |
| `agent.web_pages` | `agent.tools.web_pages` |

Project orchestration/context/budgets and timing belong in runtime; frontend presentation, terminal input and browser activity belong in interfaces; deterministic citation/clarification rules belong in policies; public-page reading and its bounded worker belong in tools. Existing providers, actions, storage, memory, config and LangGraph packages retain their responsibilities. Tests belong under tests/, acceptance runners under evaluations/. Entry points remain streamlit_app.py and python -m agent.langgraph.langgraph_agent.

Final verification reviewed on 20 October 2026: all 428 unique offline tests passed across two nonoverlapping batches (324 before the full-run 300-second cap, then the remaining 104 in 38.747 seconds). This is complete suite coverage across batches, not one uninterrupted full-suite run. Both batches used the offline guard. The 97 focused checks also passed. Source equivalence was rechecked for all 13 moves; agent/ now contains 29 compatibility modules plus __init__.py, with no active top-level function/class implementations. Evidence: outputs/acceptance/package-helpers-summary.json, package-helpers-full.log and package-helpers-remainder.log. The original timeout remains honestly recorded. Existing imports, module commands and working behavior are preserved within the tested scope. No new live provider/browser acceptance or full core release is claimed.

Backups: outputs/package-helpers-before-20261019-151846 contains pre-change sources; the earlier full private backup remains retained. No .env, saved chats, facts, receipts or data-root settings are intentionally changed. Restart running interfaces after acceptance to load the relocated code.

## WS8 current-source build/install follow-up — 21 October 2026

Y for an offline prepared-source sdist/wheel build and audit: current helpers/aliases and entry point are included, declared dependency profiles match metadata, and synthetic private-data canaries are excluded. P for the latest-source fresh editable install: build-dependency acquisition timed out before install/startup/tests. Earlier core-install evidence retains its historical scope. Working packages/provider settings are unchanged and disposable fixtures/processes were cleaned up. This is not wheel-runtime, full/RAG, Git-publication or full-release acceptance. See workstream-8-release.md and outputs/acceptance/ws8-source-build-current/result.json; the failed install is recorded separately under ws8-core-fresh-20261020. The reusable runner lives in evaluations/core_install_acceptance.py. Next prerequisite is reliable package access or a prepared local wheelhouse, not another unchanged download attempt.


## WS8 local-wheelhouse recovery — 21 October 2026

Y for latest-source fresh core editable installation and selected acceptance. Public package access recovered: two build-tool wheels downloaded in 2.90 seconds and core dependencies in 45.17 seconds (74 wheels total). A new Windows Python 3.14.0 environment, with no system-site-packages, installed exclusively from these wheels with build isolation enabled and the package index disabled. Pip check, the legacy module --help and installed jeshla-auto-ai --help passed. All 222 selected offline regressions passed in 68.679 seconds, and the actual Streamlit AppTest initial screen rendered without errors with newly resolved Streamlit 1.66.0. Total successful rehearsal: 257.26 seconds, including setup and cleanup. This is selected synthetic core acceptance, not the entire project suite, real-browser/provider acceptance, optional RAG installation or fresh GitHub-clone acceptance.

The first wheelhouse rehearsal passed installation and entry points, then exposed a runner-only metadata lookup error: editable source egg-info shadowed installed dist-info. The runner now checks the fresh environment's installed metadata and exact editable source URL. That earlier report is retained under ws8-core-wheelhouse-20261021; the corrected successful run is ws8-core-wheelhouse-fixed-20261021/result.json. No application implementation was changed. Working package and .env fingerprints remained unchanged, no real settings or persistent user data were copied, and disposable fixtures and owned processes were cleaned up. No provider/model requests ran; tests blocked external requests in their Python process.

The reusable runner remains evaluations/core_install_acceptance.py; --wheelhouse selects downloaded wheels and --output-dir preserves previous reports. Wheel filenames and SHA-256 hashes are recorded in the successful report. The wheelhouse is a local Windows/Python-specific acceptance cache, not a universal dependency lock or publishing artifact. The earlier timeout is historical and no longer blocks scoped core editable setup. Full/RAG setup, broader WS2/WS3/WS4 quality, non-editable wheel runtime/data roots, release scope and general release completion remain pending. Workstream 8 stays I; Word synchronization is not claimed.

To repeat this scoped acceptance from the project root while the existing wheelhouse is available:

```powershell
python evaluations/core_install_acceptance.py --wheelhouse outputs/acceptance/ws8-package-access-20261021/wheelhouse --output-dir outputs/acceptance/ws8-core-repeat
```

This prepares a disposable source copy and environment; it does not install into the active environment. Use a new report directory to retain prior evidence. Optional RAG models and real provider calls are excluded.

## Optional profile acceptance and remaining gates on 21 October 2026

Y for fresh RAG plus integration package installation, dependency consistency and both console entry points. Public resolution selected 129 distributions; the local cache contains 131 wheel files including the earlier build tools. The first installation reached its 300-second cap while installing packages. Deferring install-time bytecode compilation with --no-compile then passed installation in 72.80 seconds. A further fresh run with separately bounded ML import repeated installation successfully in 142.54 seconds. These timings are observations, not a guaranteed speedup. Python may compile bytecode on first use; no working environment or dependency versions were changed to obtain these results.

Y for 246 selected offline regressions (88.051 seconds), zero failures/errors, and actual Streamlit AppTest initial rendering in the fresh Python 3.14.0 / Streamlit 1.66.0 environment. The 246 include the earlier 222 selected core checks; do not add these counts. Eleven optional imports passed, including openpyxl, pypdf, docx, FAISS, LangChain adapters, MCP, httpx2 and the actual Jira client module. No authentication or live Jira session was started. Real temporary TXT/DOCX/CSV ingestion produced three chunks, saved/reopened FAISS and BM25 indexes and returned the expected synthetic sources. A blank generated PDF was opened successfully; this does not certify arbitrary PDF extraction. The vector smoke deliberately uses fixture embeddings, not a pretrained model or a semantic-quality benchmark.

P for the optional ML runtime/import gate: direct sentence_transformers import did not finish within 180 seconds in the first runtime attempt. The evaluator now isolates that import in an owned child with a 45-second cap, allowing unrelated parser/index and regression checks to finish. That child timed out at 45.60 seconds and stopped. The final report is intentionally pending/nonzero despite all 246 regressions passing. Its worker status reflects the incomplete optional runtime gate, not a failed regression. Total final rehearsal 388.01 seconds, including setup and cleanup. No model downloads occurred. Working package/.env fingerprints remained unchanged; disposable environments and owned processes were removed.

Evidence: outputs/acceptance/ws8-rag-resolution-20261021, ws8-rag-fresh-20261021, ws8-rag-no-compile-20261021 and ws8-rag-bounded-import-20261021/result.json. Existing evaluations/core_install_acceptance.py gained --profile rag and --no-compile, scoped optional imports and synthetic parser/index checks; no application implementation or flat agent module was added. The Windows/Python-specific wheel cache and exact resolution list are acceptance evidence, not a universal lock file. Full learning-profile installation, non-editable wheel runtime, GitHub-clone acceptance and broad WS2/WS3/WS4 quality remain unaccepted. Word synchronization is not claimed.

A separate live synthetic Groq memory review passed three cases: equal-authority conflict with both values and clarification, different projects, and different years. The fourth case hit HTTP 429 and the run stopped; five of eight cases remain unfinished. The evaluator previously rejected a complete JSON Markdown code block. It now accepts only a single complete JSON fence or plain JSON for semantic scoring and records plain-JSON request compliance separately. The three semantic passes used fences and do not establish plain-JSON compliance. Seven positive/negative parser checks and the eight scripted offline fixtures passed; these validate the harness, not additional live model cases. No private user histories or real project facts were sent, and temporary databases were unchanged and removed. Evidence: outputs/acceptance/ws3-memory-review-groq-all.json and ws8-memory-quality-probe-20261021. Groq quota remains the observed live-evaluation blocker; no persistent provider switch or blocked fallback retry was made.

Workstream 8 remains I. Setup is no longer the unresolved core/RAG installation issue: remaining work is optional ML runtime and broader quality/release gates. Keep existing Y scope and parked P items distinct; do not rerun the same heavy import or rate-limited requests without a changed prerequisite or a targeted diagnostic.

Repeat optional-profile acceptance from the project root using a new output directory:

```powershell
python evaluations/core_install_acceptance.py --profile rag --no-compile --wheelhouse outputs/acceptance/ws8-package-access-20261021/wheelhouse --output-dir outputs/acceptance/ws8-rag-repeat
```

This can return nonzero when optional ML import is incomplete even if all regressions pass; inspect worker.optional_profile and the individual test counts. It uses synthetic source/state copies and never installs into the active environment.

## Follow-up on 21 October 2026

OpenRouter synthetic connectivity verified; one-model baseline 7/8, then live follow-up blocked by exact-source formatting and HTTP 429 quota exhaustion. Generic scope guidance passed 61 focused and 246 fresh offline tests; its targeted live role acceptance is unfinished. Cached real MiniLM sample passed 8/8 locally. Fresh RAG runtime still has a 60-second cold sentence-transformers import timeout; its 246 tests, other imports, parser/index smoke and UI startup passed. Working packages and .env stayed unchanged. Workstream 8 remains I; details and evidence are in workstream-8-release.md and workstream-3-memory.md. Word is not synchronized by this update.


## Repeat the offline fresh core-wheel check

Run from the source checkout, with an existing compatible public-wheel cache:

```powershell
python evaluations/wheel_runtime_acceptance.py --fresh --wheelhouse outputs/acceptance/ws8-package-access-20261021/wheelhouse --output-dir outputs/acceptance/ws8-fresh-wheel-next
```

The runner builds a prepared-source wheel, installs it and core dependencies into an owned temporary venv, blocks provider calls, checks synthetic state and removes the fixture. It never installs into the working venv. Cached wheels must match the selected Python/platform; missing wheels fail explicitly without a package-index fallback. This does not install optional profiles or start the user's browser/server.


## Offline CI startup verification - 23 October 2026

The GitHub workflow uses core-only startup jobs and a separate RAG/core offline-test job. Startup checks need no real API key and do not start a browser/server. Run them separately from the source checkout:

```powershell
python -m evaluations.ci_smoke --interface console
python -m evaluations.ci_smoke --interface browser
```

Each worker gets private fixture settings and temporary state; outputs/ci receives its JSON/log. Console must prove save/show and checkpoint reopen; browser must render the initial page with one composer and no error/exception. A 120-second process deadline fails rather than declaring startup success. These are source checks with the current environment, not clean installs, all live actions or DOM/CSS tests. Five focused CI-runner regressions and both startup scenarios passed locally; actual GitHub/Ubuntu jobs remain unverified. See github-readiness.md for exact evidence, the earlier harness failure and candidate revision.
