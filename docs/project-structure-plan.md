# Project structure milestone

Status I for read-only inventory; migration remains X. Requested by the user on 18 October 2026. Schedule after Workstream 8, before UI expansion and Workstream 9 framework work. This document records the task; no Python files are moved and no imports or runtime behavior change now.

## Purpose

Organize the existing agent into meaningful parent/child Python packages with clear responsibilities, usable entry points, configuration and tests. Preserve existing working behavior. Some packages already exist under agent/langgraph, agent/memory and agent/tools; extend or consolidate these based on actual dependencies rather than creating empty layers or copying another organization's layout.

## Candidate responsibilities

| Area | Responsibility | Migration principle |
|---|---|---|
| Entry points and interfaces | Console and Streamlit presentation | Preserve python -m agent.langgraph.langgraph_agent and streamlit_app.py compatibility |
| Runtime and orchestration | Turn execution, routing, bounded loops, task state and locking | Keep decisions separate from UI and persistence |
| Providers | Adapters, errors, retry policy and model budgets | Preserve all four provider settings and schemas |
| Memory and storage | Facts, chats, summaries, checkpoints and receipts | Preserve existing database paths, schemas, identities and scope |
| Knowledge and retrieval | Document ingestion, structured tables, search and citations | Preserve core/optional-RAG dependency separation |
| Actions and tools | Validation, exact approvals, tool registries and replay controls | Preserve existing permissions and uncertain receipts |
| Integrations | Existing Jira/MCP and later framework adapters | Keep optional dependencies and external effects separate |
| Configuration | Environment validation, paths and settings | No hardcoded user/project roots; avoid import-time side effects |
| Tests and evaluations | Offline regressions, integration fixtures and acceptance evidence | Distinguish automated fixtures from live provider evidence |

Final folder names and whether to adopt a src layout will be decided after an import/dependency audit. Do not force a src migration if it breaks existing module startup. Parent packages and child packages should represent cohesive responsibilities; a small useful module can remain small.

## Completion checklist

- I: static inventory created in project-structure-audit.md; caller tracing, public-interface/path mapping and runtime-cycle analysis remain pending.
- Y: private pre-migration backup at D:\JeshlaAutoAI_Backups\before-structure-20261018-175619. All 928 backup and restored-file hashes matched; six copied SQLite databases passed integrity checks. No agent writers detected. Virtual environment/caches excluded as rebuildable; no restored application launched.
- X: establish the current regression and sampled console/browser/provider behavior baseline before moving files.
- X: propose the package map and clear dependency direction; add packaging metadata where useful, preserving core/RAG optional profiles.
- X: move a small coherent group at a time; retain compatibility wrappers/re-exports for existing entry points and imports. Do not mix behavior redesign with relocation.
- X: remove avoidable import-time state creation and define explicit initialization where justified, with compatibility acceptance.
- I: affected/full suites passed after each group (latest full 359); fresh editable-core startup and 86 selected core tests passed after current moves. Repeat affected acceptance if remaining CLI/interface changes alter the layout.
- X: verify saved facts, chat reopen/switch, checkpoint summaries, both-interface approvals, completed replay and uncertain blocking against preserved data or safe restored fixtures.
- X: update README, diagrams, import examples and roadmap; document developer responsibilities and package boundaries.
- X: retain the original backup through final acceptance. Remove only the specifically verified backup directory after successful migration and validation; never treat backup deletion as part of moving source files.

## Safeguards

Do not remove existing state to make imports work. Do not rewrite receipt fingerprints or reauthorize old actions. Do not reset .env or silently change providers. Do not remove historical diagrams or existing working features. A failed migration step must be reversible without replaying external effects. If the active application must stop for backup or final smoke acceptance, coordinate that short pause with the user at that time.

The goal is maintainability through cohesive packages, tests, repeatable setup and clear ownership; folder names alone do not establish production readiness.

## Closing status

Code migration Y for the agreed incremental scope: policies, stable config path anchor, providers, runtime, storage/actions, lazy graph lifecycle, browser and console adapters, packaging metadata and legacy compatibility. Node assembly remains in the existing LangGraph package; no further moves planned.

P: final post-console full regression and isolated browser acceptance, after unusually slow timed attempts. Earlier full359 and fresh-core86 precede console extraction; focused31 passed after it.
Y: package map and Word content/diagram synchronization. P: Word page-layout visual QA, renderer unavailable. Backup retained. Full release and optional RAG/semantic/summary/relevance quality remain separate pending gates. Do not remove the private backup until final verification is accepted.
