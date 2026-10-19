# Project structure audit

Status I. Read-only source audit started 18 October 2026; no source files moved.

## Inventory

Parsed 75 Python files across agent (43), rag (23) and integrations (9); parse failures: 0. AST import inventory: outputs/acceptance/project-structure-inventory.json. This is a static inventory, not proof that dynamic imports or runtime dependency cycles are absent.

| Module | Lines |
|---|---:|
| agent/langgraph/langgraph_agent.py | 1114 |
| rag/web_search_agent.py | 889 |
| agent/langgraph/langgraph_agent_review_fix.py | 671 |
| rag/tool_calling.py | 655 |
| rag/rag_agent.py | 643 |
| agent/langgraph/jira_workflow_node.py | 618 |
| rag/dataset_registry.py | 572 |
| rag/query.py | 539 |

## Observed boundaries and migration priorities

Existing agent/langgraph, agent/memory and agent/tools packages already provide useful grouping. Preserve their APIs until each caller is audited. The main langgraph_agent module combines graph assembly, routing, nodes, CLI behavior and checkpoint initialization; browser_backend imports the graph from it. Its module-level SQLite connection creates runtime state on import. This is a priority boundary for later explicit initialization, not permission to rewrite it now.

Provider concerns currently span llm_client, tool_llm, provider_errors, model_budget and provider-specific helpers. Group these only after preserving existing import names and configured behavior. Runtime and persistence are split across chat_runtime, chat_catalog, context summary and memory/receipt stores. Keep memory facts, conversation summaries and action permissions conceptually separate even if package names are consolidated.

rag contains current retrieval/ingestion and standalone learning entry points. Distinguish active integrations from examples before moving or deprecating anything. integrations holds existing Jira/MCP/QA adapters with optional dependencies and external side effects; retain deferred status.

## Next safe step

Audit callers and the graph initialization path, then produce a concrete old-path/new-package map with compatibility wrappers. No file moves until the full stopped-writer backup is verified. Preserve database locations and receipt root bindings; packaging layout must not silently relocate state. Keep the existing console/browser launch commands. Avoid mixing refactoring with feature or behavior changes.

## Verification limits

No migration tests were necessary because only documentation and an AST inventory were produced. Existing regression results retain their original scope. Word content is synchronized, but visual layout verification remains unavailable because LibreOffice is missing. Current full release remains pending; read-only audit does not bypass release gates or authorize public deployment.

## Caller map prepared

See package-migration-map.md for the proposed package map and outputs/acceptance/project-package-callers.json for static absolute imports and dotted string references. Configuration capture, module-level checkpoint creation, root-path derivation and monkeypatch compatibility are explicit migration risks. Next is full stopped-writer backup preparation; no source changes have been made.

## Pre-migration backup verified

Private backup: D:\JeshlaAutoAI_Backups\before-structure-20261018-175619. All 928 backup/restore hashes matched; six copied SQLite integrity checks passed. Inspection changed a backup SHM sidecar; it was recopied from the unchanged original and all hashes were reverified. Original user state unchanged. No running agent writers were detected or terminated. Virtual environment/caches excluded as rebuildable; application-level recovery and migration acceptance remain separate. Backup contains private settings and data and must not be published.

## First technical migration verified

Created agent/policies as the parent for deterministic rules. history_intent implementation is now policies/routing.py; tool_policy implementation is now policies/tool_registry.py. Existing agent.history_intent and agent.tool_policy module paths alias the canonical modules, preserving callable/global identity and old-path monkeypatch behavior. Existing callers and entry points were not rewritten.

Full offline regression: 346 tests passed in 26.441 seconds, including two new compatibility cases and the previously added recovery rehearsal. Log: outputs/acceptance/project-structure-policy-regressions.log. No database/provider/UI configuration changes. Pre-migration backup retained. Next: audit and centralize stable project-path resolution before relocating modules that derive paths from __file__. Broader migration and final clean-install acceptance remain pending.

## Stable application paths verified

Added agent/config/paths.py as the pure source-root anchor. Core provider configuration, browser backend/activity, graph checkpoint root, project-context comparison, default fact-store root and page-worker cwd now reference APPLICATION_ROOT. The constant preserves current paths and does not read environment files, create directories or open databases on import. AI_PROJECT_ROOT and user-declared inspection roots remain separate and cannot redirect application state through this anchor.

348 full offline tests passed in 27.987 seconds, including fresh-process different-working-directory import and external-inspection-root isolation. Log: outputs/acceptance/project-structure-path-regressions.log. Existing state schemas and paths unchanged. Legacy review_fix/Jira/feature-mapping and RAG source anchors were not relocated in this slice. Next: move provider modules incrementally using compatibility aliases, preserving configuration capture and existing defaults.

## Provider package migration verified

Grouped provider_errors, model_budget, llm_client, tool_llm and gemini_config implementations under agent/providers as errors, budget, text, tools and gemini. Internal provider imports use canonical package paths. Legacy agent module paths remain aliases to the same module objects, preserving function globals, configured constants, exception class identity and patch targets. APPLICATION_ROOT preserves .env lookup. No key/model/provider value or API behavior changed.

350 full offline tests passed in 41.860 seconds. New compatibility cases verify all five aliases and an old budget patch affecting canonical transport before network access. Existing four-provider adapter/error tests remain included. Log outputs/acceptance/project-structure-provider-regressions.log. No live provider acceptance or post-migration clean installation is claimed. Backup retained. Next: group runtime helpers and storage/action modules incrementally before changing graph lifecycle.

## Runtime helper package verified

Grouped chat_runtime, context_summary, summary_model, runtime_context and conversation implementations under agent/runtime as turns, summaries, summary_model, context and conversation. Legacy paths alias canonical module objects. Runtime-internal imports use canonical provider/runtime paths. Graph assembly, CLI/browser entry points and persistent schemas/locations unchanged.

352 full offline tests passed in 26.718 seconds, including new module/shared-object identity and cross-import approval-scope checks. Shared process lock and ContextVar identity are preserved. Log outputs/acceptance/project-structure-runtime-regressions.log. No live provider calls or user data migration. Next: storage/action grouping, followed by graph lifecycle separation and final clean-core startup acceptance. Original private backup retained.

## Storage and action packages verified

ChatCatalog now lives in agent/storage/chats.py. LocalActionReceipts and action exceptions live in agent/actions/receipts.py; scoped browser proposals live in agent/actions/browser.py. Existing module paths remain aliases, preserving class and exception identity and patch targets. Constructors still receive the same paths; no schema migration, database copy, receipt identity change or permission change occurred.

354 full offline tests passed in 21.151 seconds. Coverage includes new alias/exception checks plus existing fresh-process crash/replay, browser approval/decline, scoped proposals and backup restoration. Log outputs/acceptance/project-structure-storage-action-regressions.log. Private backup retained. Next: separate graph construction/lifecycle from console and browser initialization carefully; final fresh-core startup acceptance remains pending.

## Graph lifecycle migration verified

18 October 2026: existing graph wiring is wrapped by build_graph(checkpointer). agent.runtime.graph.LazyGraph defers SQLite connection and compilation until actual graph use; graph.invoke/get_state/update_state remain synchronous-compatible and serialized with the lifecycle lock. Explicit close releases the connection; reopening preserves committed checkpoints. Do not close while interfaces are still using the graph; async/streaming lifecycle behavior is outside this measured scope. No paths/schemas/provider defaults changed.

358 full offline tests passed in 22.807 seconds (outputs/acceptance/project-structure-graph-final.log). Tests cover no initial database creation, checkpoint persistence across close/reopen, build-failure connection cleanup, concurrent first initialization once, and subprocess console import/help with sqlite3.connect forbidden. The first 357-test run had one temporary-fixture cleanup error; corrected by closing the reopened fixture before TemporaryDirectory cleanup. No production database failure was observed.

Current task complete; broader package migration remains I. Original private backup is retained. Next: final isolated console/browser startup and packaging verification, then remaining interface/documentation cleanup. Do not start another structural change before recording its scope.

## Browser interface group verified

18 October 2026: browser_backend implementation moved to agent/interfaces/browser.py; agent.browser_backend remains an alias to the same module. Canonical imports reference runtime/storage/actions packages. Existing ROOT, backend factory, classes and old patch targets are preserved. streamlit_app.py and its launch command remain unchanged; no UI redesign or data-path/schema change.

359 full offline tests passed in 26.357 seconds, including browser factory compatibility and existing Streamlit/approval cases. Evidence outputs/acceptance/project-structure-browser-regressions.log. No live API requests. Original private backup retained. One requested refactor completed; stop here.

## Editable packaging accepted

Added pyproject.toml for jeshla-auto-ai 0.1.0.dev0, verified Windows Python 3.14 baseline, console entry point and core dependencies from requirements-core.txt. Optional rag/learning/integrations extras preserve existing dependency profiles. Package data excludes user state; legacy launch commands remain. Developer instructions in developer-setup.md require editable source installation to preserve current APPLICATION_ROOT semantics.

Disposable source-only editable installation passed in 13.32 seconds: new environment, build tools, editable --no-deps install, entry-point/dependency metadata and source-root checks from a different working directory. No user .env/state copied; no application graph or model invoked; original environment unchanged. Report outputs/acceptance/project-structure-package-install.json and matching log. This is packaging acceptance, not a fresh all-dependency runtime regression. Prior 359-test full suite remains the code baseline; no runtime code changed in this slice. Normal wheel/data-root relocation is not certified.

Remaining: final isolated post-refactor console/browser and core task acceptance; remaining CLI/node responsibility split if justified; Word/diagram synchronization. Full release/RAG quality remains pending. Backup retained.

## Post-refactor isolated core acceptance passed

Fresh source-only editable core environment passed all six stages: virtual environment, editable core install, pip check, console help with database connection forbidden, real BrowserBackend Streamlit initial rendering, and 86 selected offline core tests. Total 159.99 seconds; tests 25.605 seconds. Report outputs/acceptance/project-structure-final-core.json and matching log. This validates the refactored core packages in an isolated install with synthetic data; no live provider requests, RAG model/index loading or user data mutation.

The prior full working-environment code regression remains 359 tests passed. These 86 tests are a selected fresh-environment suite, not a second full 359-test run. Private backup retained. Remaining organization scope: decide and perform the final console/node responsibility split only where justified, then synchronize developer/Word diagrams and final checklist. Full release and parked quality gates remain pending.

## Console interface separation verified for affected scope

Console input/command/session loop moved to agent/interfaces/console.py as run_console with explicit graph, project root, provider, session callbacks and timer dependencies. Legacy langgraph main delegates without changing python -m startup or packaged entry point. Graph/node orchestration remains in its existing package; no state paths or schemas changed. Removed an unused state draft; run_turn remains responsible for actual turn state.

31 focused checks passed in 7.309 seconds: chat commands, context-summary CLI handling, graph lifecycle and compatibility. New delegation test verifies the exact runtime dependencies passed through legacy main. Evidence project-structure-console-focused.json. Full suite ran slowly and was stopped before its final result; its log contains progress but is not a pass. Only identified agent-started Python PID 25968 (matching test command/parent) was stopped. Prior full code baseline remains 359 passed before this console change. Final bounded full verification remains pending.

Two overall steps remain: final full/package/interface checks, then roadmap/diagram/checklist synchronization. Backup retained; no live provider calls or user-state changes.

## Closing verification outcome

Code moves completed for the stated scope; final acceptance P. Post-console full suite hit 120 seconds, then the single serial retry hit 300 seconds before a final result. Progress included temporary index fixtures; neither timeout is a pass. Actual isolated console save/show/exit succeeded. The isolated browser attempt timed out during initial AppTest rendering and is unverified. Prior full359 and fresh-core86 remain historical evidence; post-console focused31 passed.

Word content and package diagram synchronized; standalone diagram visually inspected. Word page-layout render failed because LibreOffice is unavailable. No further automatic test retries. Next user test: run python tests/run_offline.py to completion on the user's machine and provide its final Ran/OK or failure lines; restart console/Streamlit and verify memory/session/action behavior. Backup remains private and retained. Do not declare full release or remove backup yet. Closing summary outputs/acceptance/project-structure-closing-status.json.

## User full regression passed

18 October 2026: inspected outputs/acceptance/user-test-run.log. Direct verbose unittest discovery completed 365 tests in 35.087 seconds with OK. This supersedes the earlier six-timeout run for this completed run; the cause of prior slowness remains unconfirmed. The command did not enable the outer offline_guard; do not label it a guarded run. Core code regression is now verified after console extraction and logging changes. Live model/API behavior, optional RAG model loading and manual browser acceptance retain their separate scopes. Backup retained; Word visual QA remains pending.

## User console and browser live verification

18 October 2026: supplied console transcript confirms restored default, existing facts, an OpenRouter answer (10.49-second workflow), switch to refactor_check, and explicit memory save/show. Screenshot and launch output confirm the named /JeshlaAutoAI URL, default history and a live OpenRouter answer in Streamlit. This supersedes the automated browser timeout for these observed manual behaviors. Console restart persistence and browser visibility of the new fact are not yet shown. Controlled-action post-refactor manual acceptance remains pending; earlier offline checks retain their scope. Backup retained. Report outputs/acceptance/refactor-user-console-browser.json.

## Memory-control summary delay fixed

18 October 2026 user restart transcript verifies refactor_check persisted. Runtime logs show local SHOW MEMORY routing completed, then automatic summarization held the turn for 121.63 seconds and failed; the workflow returned success because summary failure is handled. Browser application error at 22:32:53 occurred during this wait and is consistent with same-chat busy protection, but its exact error text was not supplied.

Runtime now skips automatic compaction for explicit memory/memory_command routes while preserving transcript/checkpoint writes. Normal conversation still compacts; summary state is retained. 23 affected runtime/summary/logging tests passed in 1.846 seconds. Full365 pass predates this fix; no new full-suite claim. Restart both interfaces to load the fix and check SHOW MEMORY sequentially. Backup retained.

## Memory delay fix user verified

Supplied restarted-console transcript confirms persisted refactor_check, restored named-session history, explicit remember in 0.04 seconds and show in 0.03–0.04 seconds without a model request. Normal OpenRouter answer completed in 3.44 seconds. Browser visibility of the new fact and post-refactor manual action checks remain pending.

## Post-refactor live browser approval passed

User approved proposal 03ce876bed30401ca4dade7a73b71a7e. Read-only verification confirms outputs/refactor-approval-check.txt exists with exact requested content, 30 bytes, completed browser proposal and completed durable action receipt. No bypass file creation or additional commands were run. Evidence refactor-browser-approval-live.json. Core manual console/browser checks and exact create approval now have observed successes. Full365 user regression precedes the memory-summary fix; 23 affected checks plus fast console memory verification cover that fix. Word visual layout and broader full-release/RAG gates remain separate pending limitations. Backup retained.
