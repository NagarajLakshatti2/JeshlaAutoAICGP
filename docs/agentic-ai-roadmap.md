# JeshlaAutoAI — Agentic AI roadmap

Updated: 18 October 2026

## Your actual development position

**You are not still in Phase 1. Your current original learning phase is Phase 3: memory, stateful agents and integration hardening.**

| Original development phase | Build status | Readiness |
|---|---|---|
| Phase 1 — LLM foundations and basic agents | **Y** | Foundation implemented and real model use demonstrated; some release checks remain |
| Phase 2 — RAG and knowledge implementation | **Y** | Ingestion, hybrid retrieval, reranking, structured search and evaluation exist; quality/runtime integration is **P** |
| Phase 3 — State, persistent memory and conversational agents | **I** | Core components work; summaries, advanced recall and broader acceptance remain **P** |

The numbered sections later in this document are **completion workstreams**, not a claim that you must restart Phase 1. A built module can have pending integration or acceptance without losing credit for its implementation.

The full-project audit read/parsed **94 Python files**, with **no syntax errors**. See [project-progress-audit.md](project-progress-audit.md) for folder evidence, RAG details, prototype distinctions and the current full-suite test limitations.

```mermaid
flowchart LR
    A[Phase 1: LLM foundation — Y] --> B[Phase 2: RAG implementation — Y]
    B --> C[Phase 3: Stateful AI agent and memory — I]
    C --> D[Cross-cutting integration and release checks — P]
    D --> E[Automation-framework expansion — P / parked]
```

## Target and scope

Build JeshlaAutoAI as a reliable, local-first AI agent with a configurable hosted or local model, conversation, persistent memory, evidence retrieval, validated tools, and user-controlled actions.

AI agent is the application we are building. Agentic AI describes the approach: the model selects tools, observes results, adjusts its next step, and answers or asks for clarification. Agentic by itself is an adjective, not a separate product target. Recommended project description: **JeshlaAutoAI — an AI agent built with agentic AI capabilities.**

Automation-framework development is deferred until the core-agent acceptance gates below pass. Preserve existing Jira/QA modules, but do not make new framework integration the next milestone. Completion means the agreed core scope is verified, not that every possible AI capability exists or that the project matches proprietary products.

## Current position

Phase 1 foundations and Phase 2 RAG implementation already exist. Phase 3 integration and hardening is the current focus. The conversational foundation works: Groq, native tool calls, local memory commands, named chats, transcript archiving and editable terminal input have been exercised. Streamlit create/chat/reopen/shared-memory/download acceptance passed for the observed user/browser scope, with 199 offline tests and live action logs supporting current behavior. Web search works, but citations and factual grounding need improvement. Automatic summaries now use a validated registered function and pass synthetic live checks on Groq and OpenRouter. Actual-history summary format/quality and full live summary isolation remain P—parked; Ollama summary attribution also remains P. The precise generated-output defect is unconfirmed. Workstreams 5 and 6 now have scoped core acceptance Y; Workstream 7 scoped reliability acceptance is Y; Workstream 8 release gate is next. Document retrieval and advanced memory search require verification and development.

## Core-completion workstreams (not a restart of learning phases)

| Workstream | Scope | Current status | Acceptance gate |
|---|---|---|---|
| **Y** — 1. Agent foundation | Provider adapter, native tool calls, direct answers, console/browser entry points | Four provider adapters are supported: Groq, OpenRouter, Ollama and Gemini. Earlier three-provider direct/tool acceptance is retained; Gemini direct use was user verified. Full four-provider live release acceptance is not claimed. | A direct answer and tool-result-answer cycle work; failures are understandable; available models/providers are explicit |
| **P** — 2. Conversations and context | New/open/list chats, titles, transcript archive, session-specific summaries, editing and cancellation | Chats, shared facts, transcript download and observed browser-to-console restart recall work. Actual-history summary quality, Ollama summary acceptance and broader summary isolation remain parked. | Restart restores each chat; switching never mixes history; full new turns remain archived; summarization succeeds or safely degrades |
| **P** — 3. Useful long-term memory | Save/update/show/forget, relevant retrieval, user/project scope, provenance, conflict handling, archived-chat search | Fact storage, provenance, timestamps, revisions, scoped archive search and user-approved memory suggestions are implemented and tested. Broader semantic recall and conflict quality remain parked. | Retrieve relevant facts from a larger collection; keep unrelated scopes isolated; corrections supersede stale facts; explain where a fact came from |
| **P** — 4. Reliable knowledge and search | Indexed documents, structured data, public web sources, full-page evidence, citations, combined answers | Scoped citation guards, page deadlines, structured tables and mixed-source grounding acceptance are verified. One broader relevance/entailment/hybrid quality gate remains parked. | Answer a mixed local/public query with verified source links; no invented citations; missing evidence produces clarification |
| **Y** — 5. General agent reasoning | Dynamic clarification, task decomposition when useful, observe/replan, tool selection, explicit completion criteria | Bounded tool selection, clarification, real-file planning/recovery and complete/partial/blocked outcomes verified. Universal reasoning or semantic correctness is not claimed. | Complete a defined multi-step task; recover from a failed tool; avoid repeated calls; distinguish complete, partial and blocked outcomes |
| **Y** — 6. Controlled actions | Classified local tools, exact console/browser approvals and durable receipts | Exact console/browser approval, decline, durable receipts and restart/replay protection verified for trusted local-user scope. OS sandboxing and public multi-user authentication are outside this scope. | Trusted local-user core; OS command containment and wider release hardening are not claimed |
| **Y** — 7. Reliability and observability | Useful error types, timings, retries/backoff, budgets, concurrency, source/tool activity, regression coverage | Scoped crash/save recovery, simulated provider-failure presentation/recovery and configurable context budgets verified. Full offline regression: 343 tests passed on 18 October 2026. Live provider fault injection and exact token fit are not claimed. | Connection, quota, malformed output, interrupted process and concurrent-chat cases are handled; model-visible claims match real tool evidence |
| **I** — 8. Core-agent release | Integrated acceptance suite, setup guide, repeatable installation, dependency cleanup, configuration and backup/recovery | NEXT, not started. Verify integrated core acceptance, clean installation, documentation and backup/recovery; review parked gaps and agree release limitations before marking complete. | The complete core-agent checklist passes in console and browser, with known limits documented |
| **P** — 9. Automation-framework integration | Connect the completed agent to requirements, test design, UI inspection, code generation and execution/reporting | PARKED by plan. Start framework integration only after Workstream 8 release acceptance and user decision. Proposed UI milestone is scheduled between Workstreams 8 and 9 and has not started. | Begin only after Workstream 8 acceptance and user decision to move to framework work |

## Memory development details

- Separate chat history, session summaries and reusable facts; never use a summary as approval.
- Select relevant memories instead of injecting every fact into each prompt.
- Keep source, timestamp and scope for facts; distinguish user assertions from tool evidence.
- Search archived conversations only within the intended scope and cite the originating chat/turn.
- Propose useful new memories or corrections; define explicit user control before automatic storage.
- Handle conflicts, stale facts, deletion and optional expiry. Document that deleting a fact does not erase archived messages or provider records.
- Start with a measured retrieval baseline; add embeddings/semantic retrieval only when it improves the project's evaluation set without reintroducing the previous local inference bottleneck.

## Implementation principles

- Do not hardcode project names, framework choices, answers or fixed clarification scripts in model reasoning.
- Store editable project facts in memory/configuration. Keep credentials outside source and logs.
- Use deterministic code for command parsing, argument validation, permission checks, isolation, budgets and storage.
- Prefer documented configurable defaults for limits; not every internal invariant needs a user-facing option.
- Use model reasoning for interpreting ordinary requests, choosing read tools, synthesizing evidence and asking focused questions.
- Add tools with schemas and clear failure behavior. Native model tool calls do not themselves authorize execution.
- Keep a shared backend for console and Streamlit. UI changes should not change approval rules.
- Use the simplest architecture that passes the required tasks; multiple agents, autonomous background work and additional providers are optional future capabilities, not prerequisites.

## Completion tracker

**Current development target: an AI agent with bounded agentic capabilities.** Automation-framework development remains deferred.

Use these uppercase status codes:

| Code | Meaning |
|---|---|
| **Y** | Completed and verified for the stated scope |
| **X** | Not completed or not started; use when no meaningful implementation is recorded |
| **I** | In progress; work has started and is actively being developed |
| **P** | Worked on, but pending verification, blocked, deferred or parked |

An X item can be incomplete without being untouched; the item description should explain its state. Prefer I for active work and P for work awaiting a fix, verification or a later decision. Mark Y only after the stated behavior is verified; record supporting tests or execution. These are progress markers, not a guarantee of correctness for every input.

### Workstream 1 — Foundation

- **Y** — Groq connection works with the configured open-weight model (live execution).
- **Y** — Native model/tool/result loop works with public web search (live execution).
- **Y** — Ollama/OpenRouter/Groq adapters exist; alternate native adapters have offline transport tests.
- **Y** — The three selected provider/model combinations pass live direct-answer and real tool/result acceptance: OpenRouter, Groq and Ollama. Ollama JSON-text proposals are narrowly normalized to the shared tool-call format; caller validation and approvals remain. See [foundation-acceptance.md](foundation-acceptance.md).
- **Y** — Actionable, secret-safe provider configuration errors in console and browser: missing hosted keys/model settings, invalid numeric settings and unknown provider; shared presentation and headless UI regressions pass (181 offline tests).

### Workstream 2 — Conversations and context

**Overall: P — parked with outstanding summary acceptance.** Working conversation/browser features retain their Y statuses. Proceed to Workstream 3 by user decision; this is not full Workstream 2 completion.

- **Y** — Create, list and reopen named chats (user execution and offline tests).
- **Y** — Case-insensitive startup Y/N and 80-character titles work (offline tests and user execution).
- **Y** — Editable console multiline input works without END (user execution).
- **Y** — Save full newly successful turns in a transcript archive (offline persistence tests).
- **Y** — Streamlit supports chat creation, multiline submission and memory viewing in headless tests; real startup passed.
- **Y** — Summary failures pause retries, including across restarts (user output and offline checks).
- **Y** — Implement and validate the registered summary path: 189 offline tests pass; synthetic long-chat summaries pass on Groq and OpenRouter. The exact cause of the historical HTTP 400 is unconfirmed.
- **Y** — Verify summary persistence, restart, chat switching and complete transcript preservation with real SQLite storage and mocked models.
- **P — PARKED** — Actual-history summary accuracy: Groq format rejection and exhausted quota block live diagnosis; Ollama completed 6/7 grounding checks but failed source attribution. Resume later; see workstream-2-summaries.md.
- **Y** — User verified console restart recall and session switching; browser screenshots, separate transcript exports and live event logs verify sampled chat separation.
- **P — PARKED** — Complete live summary-content isolation across restart/switch after actual-history summarization is reliable. Existing SQLite/model-mocked summary isolation tests pass.
- **Y** — Browser create/chat/reopen/shared-memory/download acceptance passed for the observed scope: separate browser/default transcript exports and user screenshots confirm distinct chats and shared saved facts. Page-jump usability remains separate.

### Workstream 3 — Long-term memory

**Overall: P — remaining acceptance parked.** Storage, provenance, explicit corrections, archive search and controlled suggestions retain Y. Semantic relevance and broader contradiction accuracy remain P after the bounded local retry; move to Workstream 4 by user decision.

- **Y** — Save, update, show and forget explicit facts (offline tests; save/show/forget also user verified).
- **Y** — Deleted seed facts are not automatically reinserted (offline regression).
- **Y** — Memory persists across store reopen and is scoped by user/namespace (offline tests).
- **Y** — Saved facts reach normal LLM conversation (user execution).
- **Y** — Optional local-only MiniLM semantic retrieval is integrated with scoped SQLite facts and search_memory; lexical default preserved.
- **P — PARKED** — Real semantic relevance calibration: bounded local retry loaded the model but returned no paraphrase match. Mocked scope/update/delete tests pass. No downloads or API calls.
- **Y** — Bounded lexical archived-conversation search is connected to the shared agent, scoped to user/memory-space and current or explicitly selected chats, with chat/turn/time references. 210 offline tests and an actual local archive lookup pass; hosted tool-choice acceptance remains P.
- **Y** — Fact provenance, existing timestamps and verification labels are stored and exposed in memory context/commands. Backward-compatible migration preserves all 5 existing database rows; 203 offline tests pass. See [workstream-3-memory.md](workstream-3-memory.md).
- **Y** — Explicit same-key corrections preserve scoped revision history; normal retrieval uses current values only. MEMORY HISTORY key reviews revisions; FORGET deletes associated history. 206 offline tests pass.
- **Y** — Advisory related-fact conflict candidates and configurable storage-age review are implemented; no automatic merge, deletion or truth claims.
- **P — PARKED** — Broader semantic contradiction quality across keys/projects/timeframes: real HTML/PDF advisory smoke case passed, but general accuracy remains unverified.
- **Y** — Scoped suggestions require explicit ID-bound accept/reject; no automatic saved facts or existing-key overwrite. 214 offline tests and temporary command integration pass; live model suggestion selection remains unverified.

### Workstream 4 — Knowledge and evidence

**Overall: P — scoped implementation/acceptance milestones verified; broader hybrid/relevance quality is parked after bounded local timeouts.** No active Workstream 4 I checklist item remains. This is partial completion, not full quality release acceptance.

- **Y** — Implement document ingestion, metadata and recursive chunking in rag/ingest.py; artifacts are present.
- **Y** — Implement FAISS/BM25 hybrid retrieval and BGE reranking in rag/retrieval.py openand rag/query.py.
- **Y** — Implement query rewriting and PDF answer export in rag/query.py.
- **Y** — Implement CSV/Excel search, header detection and dataset routing in the rag modules.
- **Y** — Implement RAG tool-calling/web agents and evaluation variants; saved reports document prior runs.
- **Y** — Consolidate the three legacy RAG command entry points and default data/index paths with the current application. Package/standalone commands forward to the shared console, preserving arguments and avoiding historical provider/model/sample-question startup. Six launch paths covered by two regression tests; 251 offline tests pass. Historical direct-import functions remain learning/reference code; old JSON history is not automatically migrated.

- **Y** — Public web search returns real snippets and links (live execution).
- **Y** — A response can combine saved project facts with web results (user execution).
- **Y** — Web reference traceability guard rejects unseen URLs and invented internal markers, permits one correction, and safely fails empty required searches. 225 offline tests pass.
- **Y** — Scoped factual/source-grounding acceptance evaluated and verified: supported facts, missing information, embedded-instruction rejection and natural equal-authority conflict clarification passed on Groq; unofficial-source refusal passed on Groq and failed-page/snippet disclosure passed on Gemini. Exact DOC/URL citation guards, sampled official-page title evidence and local 64/64 excerpt consistency are verified. This is six representative behaviors across separate runs, not universal entailment or publisher-reputation certification. Broader corpus/claim quality remains in the P item; strict JSON conflict-detail usability remains in Workstream 5 clarification evaluation.
- **Y** — Production page reads isolate DNS/headers/body in a killable worker with a 30-second communication budget and up to 5 seconds of bounded cleanup. Timeout/cancellation produce no page evidence; real stalled-worker termination and live page reading verified. 262 offline tests pass. OS process creation/scheduling is not a real-time guarantee; injected test/custom transports retain the in-process behavior.
- **Y** — Bounded static public-page reader is connected to search results with DNS pinning/public-address validation, redirect checks, excerpt limits and final-URL citation registration. 232 offline tests pass.
- **Y** — Sampled live search/read/cited-answer acceptance passed: a broader query returned official Playwright Java documentation; Groq chose web_search and fetch_web_page, then correctly returned the fetched page title, Java scope and returned URL (12.01 seconds). Python/Playwright direct-page compatibility also passed. This verifies the sampled title/source claims; broader factual entailment remains in the P quality item, and the production page reader now has a worker-enforced total network wait budget; broader factual validation remains open.
- **Y** — Re-evaluated existing keyword indexes locally: baseline 1/8 expected source/location/keyword cases; report document-keyword-baseline.json.
- **Y** — Normalized/source-aware keyword ranking and bounded same-page context pass 8/8 audited source/location/keyword cases (6/8 original labels; two page errors independently checked against PDF). 240 offline tests pass.
- **P** — Broader document relevance, answer entailment and hybrid quality remain unverified beyond the small keyword benchmark. Local source consistency now passes 64/64 indexed excerpts against current files, with zero mismatches/unverified sources or supported files lacking indexed chunks; 256 offline tests pass. This is excerpt consistency, not complete-file or external freshness proof.
- **Y** — Structured indexed source IDs, bounded excerpts and document-citation validation are integrated while legacy text/hybrid entry points remain compatible. 237 offline tests pass.
- **Y** — Integrate structured CSV/Excel retrieval in the active conversation loop: real temporary CSV/XLSX row, sheet/header selection, truncation and failed/empty-read integration verified by 245 offline tests. General calculations, answer entailment and live provider acceptance remain pending.
- **Y** — Sampled real-tool mixed-source acceptance passed on Gemini 3.1 Flash-Lite in 19.49 seconds: scoped temporary SQLite memory, real temporary normalized BM25 document retrieval, actual official web search and page reading produced a correct combined answer with returned DOC ID and source URL. All eight sample checks passed, including unrelated-user exclusion. General entailment/novel-query quality remain under the broader P quality item; earlier Groq/OpenRouter quota blocks remain historical.

### Workstream 5 — Reasoning and task completion

**Overall: Y — scoped core acceptance complete.** Current bounded read-only loop, representative clarification/recovery and execution-outcome checks passed. See [workstream-5-reasoning.md](workstream-5-reasoning.md). Remaining checklist: 0 P, 0 I, 0 X.

- **Y** — Read-only loop validates tool arguments and limits rounds/calls (offline tests).
- **Y** — Unclear ordinary input receives clarification (user execution).
- **Y** — Representative dynamic clarification evaluated: Groq asks three focused missing-detail questions, reuses supplied web/Java/URL details, and now presents both values and DOC references in strict JSON conflict answers after one bounded correction. Structural checks do not prove semantic truth.
- **Y** — Sampled multi-step planning and failed-tool recovery verified: real temporary-file list/read and missing-file/discover/read tasks passed live on Gemini; seven local recovery regressions pass. Groq generated-tool rejection and OpenRouter quota block are recorded, not counted as passes.
- **Y** — Tool execution outcomes distinguish completed, partial and blocked while retaining existing task_status compatibility. Mixed errors retain incomplete; workbook sheet choices clear only after successful same-workbook evidence. 287 full offline tests pass, including browser tests.

This completion applies to the current bounded core. Execution completed means the answer loop finished without a tracked tool failure, not that every semantic claim or arbitrary task has been verified. A changed-path recovery remains conservatively partial until resolution is independently established. Long-horizon planning and universal factual correctness are not claimed. Workstream 4 broader quality and Workstreams 2/3 parked items remain open.

### Workstream 6 — Controlled actions

**Overall: Y — current local-core acceptance complete.** Exact approvals, scoped browser controls, durable replay protection and the core permission matrix are verified. See [workstream-6-actions.md](workstream-6-actions.md) and [workstream-6-permissions.md](workstream-6-permissions.md). Remaining: 0 P, 0 I, 0 X.

- **Y** — Console exact-action approval has regression coverage.
- **Y** — Browser action proposals wait for stored exact-action approval; no hidden console prompt or immediate execution.
- **Y** — User-operated browser create/review/approve, decline without a file, and refresh/chat-switch/return passed, with file and receipt verification.
- **Y** — All five controlled kinds pass decline, cancellation, stored-result replay, fresh-process completion and hard-exit blocking. Browser completed/declined and hard-exit states are checked across fresh processes. Failed completion/cleanup receipt writes preserve the running claim and block another execution. Simulated handlers test the receipt boundary; harmless real Python script/command integration is also verified.
- **Y** — Current core permission matrix documented and tested. Project actions share an explicit classification; conversation tools fail closed if unclassified or duplicated. Path/credential/executable guards and all-five-kind browser approval dispatch are verified.

Acceptance is for a trusted local-user agent. Approved Python/build commands use normal OS permissions; this is not OS containment or a public multi-user authentication system. The controls do not undo effects, guarantee process-tree termination or automatically resolve uncertainty. Framework/Jira expansion remains deferred. Evidence: 331-test full offline run passed; after final registry changes, 21 affected registry/conversation regressions passed. A redundant broader repeat was stopped because it was slow; an initial focused runner had a test-import-path error, corrected in the final passing run. A full 333-test run is not claimed.

### Workstream 7 — Reliability

**Overall: Y — scoped local reliability acceptance.** 343 offline tests passed on 18 October 2026. Live-provider fault injection, precise tokenization and broad retrieval quality are not claimed.

- **Y** — Timings and bounded tool execution are implemented and exercised.
- **Y** — Same-chat concurrency locks block overlapping turns and release normally (offline tests).
- **Y** — Scoped offline provider-failure acceptance: console error presentation and browser failure/recovery exercised for all four provider labels across authentication, rate limit, quota, response timeout, tool-output and output-limit categories. Existing transport/retry/classification checks also pass (32 focused tests). These are simulations, not live fault injection into every provider.
- **Y** — Scoped crash/save recovery verified: caught archive/checkpoint failures preserve the answer; kernel locks release after process exit; a real LangGraph SQLite fixture rolls back an uncommitted checkpoint mutation after process exit and reopens the prior state with its committed transcript intact. Seven focused runtime/recovery tests pass. Legacy locks still require inspection; archive/checkpoint transactions are not atomic together.
- **Y** — Scoped bounded context acceptance: configurable AI_CHAT_MAX_CONVERSATION_CHARS (default 36,000), existing project-task/evidence limits and scoped lexical memory retrieval, plus four-provider preflight checks for oversized Unicode/schema input. Oversized tasks stop honestly before model calls; exact question is not silently shortened. Provider token estimates remain approximate and configured hosted context is required for fit preflight; broader relevance quality remains parked under Workstream 4.
- **Y** — Scoped broad-suite fixture/isolation acceptance verified: the 331-test full offline run passed. Earlier 116-test/six-error results are historical; broader reliability and live-provider fault coverage remain pending.

### Workstream 8 — Core-agent release gate

**Overall: I — release preparation active.** See workstream-8-release.md.

- **P** — Pass every core-agent acceptance item below. Evidence review completed in core-release-review.md; broad summary, semantic recall, retrieval quality and clean-install gates remain unfinished.
- **P** — Clean core-profile installation, pip check, console help startup and browser initial rendering passed in a fresh Windows Python 3.14 environment (80.23 seconds). A second fresh core-profile environment passed 71 selected offline end-to-end checks. Full/RAG-profile installation and broad release gates remain pending; installation profiles are documented in dependency-audit.md.
- **Y** — Update outdated root README and installation instructions; clean-install acceptance remains separate.
- **Y** — Scoped stopped-writer synthetic backup/recovery verified for facts, chats, real checkpoint history/summary and completed/uncertain receipts. Actual user-data restoration and optional RAG-index recovery are not claimed.
- **P** — Review remaining limitations and explicitly agree on the release scope. User accepted the local development-preview scope; full core release agreement/acceptance is not claimed. See core-release-review.md.
- **X** — Mark the general AI-agent milestone complete.

### Additional milestone after Workstream 8 — Project structure

**Overall: I — read-only inventory active; migration X.** Organize existing modules into meaningful parent/child packages, preserve entry points and persistent state, and verify a full backup before incremental migration. No refactoring now. See [project-structure-plan.md](project-structure-plan.md).

- **I** — Static inventory parsed 75 source modules without syntax errors. Trace callers and initialization next; package migration and compatibility wrappers are not started. See project-structure-audit.md.
- **X** — Verify full backup/restore, baseline behavior, incremental migration and final clean-install/regression acceptance.
- **X** — Update developer documentation and diagrams; retain the backup through successful acceptance.

Sequence: Workstream 8, project structure, proposed UI improvements, then deferred Workstream 9. Existing workstream numbering is unchanged.

### Workstream 9 — Deferred automation-framework work

- **P** — Begin only after the core-agent release gate passes and the user chooses to proceed.
- **P** — Create a separate framework-integration roadmap at that time.

## Core-agent acceptance checklist

Release gates receive Y only when the complete acceptance scenario passes. A working component alone does not complete a broad gate. P means related work exists but full acceptance is pending.

- **P** — General conversation and clarification use supplied context without inventing missing facts.
- **P** — Named chats survive restart and have isolated history/summary; shared memory is scoped deliberately.
- **P** — Memory save/update/forget and relevant search pass both ordinary and conflicting-fact cases.
- **P** — Long chats preserve full newly archived transcripts; summaries carry key details without becoming instructions or permissions.
- **P** — Local source, indexed documents, structured data and public web searches work independently and together.
- **P** — Citations correspond to retrieved evidence; current facts are not claimed after search failure.
- **P** — Multi-step tasks stop at a clear result or ask for essential missing details.
- **P** — Tool arguments, source paths and action permissions are validated in code.
- **P** — Write/execute approvals work in both supported interfaces, or a documented interface limitation is explicitly accepted for the release.
- **P** — Failed/uncertain actions are not silently retried; restart and cancellation do not duplicate side effects.
- **P** — Provider, network, quota and context-limit failures are understandable and recoverable.
- **P** — Repeatable setup, data backup/recovery and the acceptance/regression suite pass in the supported environment.

## Immediate next milestone

**Next milestone: Workstream 8 — Core-agent release preparation.** Workstream 4 has verified scoped citation, page, table, source-consistency, mixed-source and representative grounding checks; one broader hybrid/relevance quality item remains P—parked after bounded timeouts. Workstreams 2 and 3 also retain parked gaps. This sequencing does not claim these workstreams are fully complete. Automation-framework expansion remains deferred until core release acceptance.

## Evidence labels

- Implemented: code exists; does not imply full live acceptance.
- Live verified: supported by an observed real execution.
- Pending: not implemented or not yet verified sufficiently.
- Deferred: deliberately outside the current development scope.

Existing root README installation/END/history notes predate several changes. Reconcile documentation during release preparation; prefer newer topic guides until then. Existing Jira uncertainty remains a tracked framework-integration issue, not something to bypass or delete while focusing on the general agent.

## AI agent versus agentic AI

These terms overlap, and terminology varies. They do not describe two mutually exclusive technologies.

| Term | Meaning | Example in JeshlaAutoAI |
|---|---|---|
| AI agent | A concrete software system that uses a model to pursue a task through available tools and context | Your application reads saved facts, chooses web search, receives results and answers |
| Agentic AI | An approach or capability in which a system chooses and adapts its actions toward a goal within defined boundaries | The agent notices missing evidence, searches another source, checks the result and decides whether to answer or ask you |
| Agentic | An adjective describing that behavior | An agentic assistant or agentic workflow |
| Fixed workflow | A predefined sequence of steps and conditions; useful when the process should be predictable | Command parsing, exact-action approval and database validation |

An AI agent can be more or less agentic. Agentic behavior does not require multiple agents, unlimited autonomy, a particular model, or automatic self-training. Fixed workflows can form part of a reliable agentic system.

### Which is better for this project?

Build **one reliable AI agent with bounded agentic behavior**. Let the model interpret requests, select read tools, evaluate results and ask for missing details. Keep permissions, validation, storage, command handling and execution limits deterministic. More autonomy is useful only when its results can be checked; it is not automatically better.

For example, answering a saved fact needs no elaborate plan. Research across several sources benefits from adaptive tool use. A write or command still needs the applicable approval regardless of how the model planned it.

### Architecture diagram

```mermaid
flowchart TD
    User[User request] --> UI[Console or Streamlit]
    UI --> Controls[Command and permission rules]
    Controls --> Context[Scoped memory and conversation context]
    Context --> Model[LLM chooses the next step]
    Model --> Choice{What is needed?}
    Choice -->|Enough evidence| Answer[Answer with evidence]
    Choice -->|Missing user details| Ask[Ask focused questions]
    Ask --> User
    Choice -->|External or local evidence| Validate[Validate tool and arguments]
    Validate --> Tools[Read files / search documents / search web]
    Tools --> Results[Actual results or explicit errors]
    Results --> Model
    Choice -->|Action requiring permission| Approval[Exact-action approval gate]
    Approval -->|Approved| Execute[Execute within allowed scope]
    Approval -->|Declined| Stop[Stop that action]
    Execute --> Results
    Answer --> Saved[Save transcript and session state]
```

This diagram is the intended architecture. The read-only LLM/tool loop is working. Browser action approval, advanced memory retrieval and several reliability gates remain incomplete; the diagram does not claim every box is fully implemented.

### Roadmap and completion flow

Status codes: Y = completed, X = not completed/not started, I = in progress, P = worked on but pending/parked. Deferred framework work uses P as a deliberate scheduling status, not a claim that it is implemented.

```mermaid
flowchart TD
    A[Y — 1. Foundation: configured providers verified] --> B[P — 2. Conversations: browser verified; summary gaps parked]
    B --> C[P — 3. Memory: implementation verified; quality gaps parked]
    C --> D[I — 4. Knowledge: search works; grounding and document validation pending]
    D --> E[Y — 5. Reasoning: scoped core acceptance passed]
    E --> F[Y — 6. Controlled actions: scoped local-core acceptance passed]
    F --> G[P — 7. Reliability: partial; complete failure and recovery checks]
    G --> H[X — 8. Core-agent acceptance: pending]
    H --> Gate{Core checklist passed?}
    Gate -->|No| Fix[Fix gaps and rerun relevant checks]
    Fix --> H
    Gate -->|Yes, then user agrees| I[P — 9. Begin automation-framework integration]

    classDef working fill:#d4edda,stroke:#288447,color:#222
    classDef partial fill:#fff3cd,stroke:#b8860b,color:#222
    classDef pending fill:#eeeeee,stroke:#777,color:#222
    class A working
    class B,C,D,E,F,G partial
    class H,I pending
```

The recommended target is therefore not AI agent *or* agentic AI: **JeshlaAutoAI is the AI agent; agentic AI is the behavior and design approach it uses.**


## Free and open-source stack priorities

The workbook comparison and project-specific P1/P2/P3 checklist are saved in [free-open-source-module-audit.md](free-open-source-module-audit.md). These priorities complement the Y/X/I/P completion statuses above.

- **P1:** retain the working stack; repair dependency reproducibility, isolated tests, relevant memory/structured retrieval, citations, summary recovery and acceptance evaluation.
- **P2:** add tracing, evaluation tooling or improved parsing only for a measured gap.
- **P3:** park alternative orchestration/vector frameworks, fine-tuning, multimedia and automation-framework expansion until the agreed core is accepted.

Free API access is quota-limited and separate from software/model licensing. Installed alternatives do not imply active use or completed integration.


## Offline test baseline completed - 17 October 2026

**Y - scoped completion:** repaired stale test fixtures and verified 120 tests passing in 3.704 seconds using the offline guard. This supersedes the earlier 116-test/six-error baseline for these fixtures; it does not establish live API, RAG answer-quality or production acceptance.

Run from the project root:

```powershell
python tests/run_offline.py
```

Changes:
- tests/test_jira_creation.py: enable creation only within fake-gateway test fixtures; add a regression proving disabled creation blocks writes.
- tests/test_prompt_workflow.py: mock proposal discussion instead of calling the real model; explicitly enable the fake approval workflow in its test scope.
- tests/run_offline.py: guard discovery and execution against external sockets, unmocked requests HTTP calls and browser launches. Loopback sockets remain for asyncio/framework internals. This is a process-level test guard, not a subprocess sandbox.
- tests/test_offline_runner.py: verify socket/HTTP/browser blocking and loopback classification.

The verified run used the project's virtual environment and required Windows file permissions. Real Jira permission gates, provider settings and runtime agent behavior were not changed. Full agent reliability remains P; next is memory and structured retrieval integration.


## Shared table and memory tool integration - 17 October 2026

**Y - implementation and offline integration:** CSV/XLSX discovery/filtering with source rows and scoped lexical saved-memory search are connected to the shared conversation. 129 guarded offline tests pass. See [table-memory-tools.md](table-memory-tools.md) for files, limits and trial prompts. **P - broader acceptance:** live model behavior, semantic-memory retrieval, complex-table queries and grounding remain pending.


## Task outcome logging - 17 October 2026

Y - scoped completion: project reports include task_status (completed/incomplete); timer decorators and the console's outer workflow observe that explicit status. Returned incomplete results log INCOMPLETE instead of SUCCESS. Exceptions still propagate and log FAILED / INTERRUPTED. New turns reset task_status so an earlier incomplete checkpoint does not contaminate the next result. Shared conversation budget/invalid-ID/step-limit exits also mark incomplete.

165 guarded offline tests passed in 28.822 seconds. Added tests/test_task_timing.py and updated runtime reset coverage. Files: agent/timing.py, agent/chat_runtime.py, agent/conversation.py, agent/langgraph/langgraph_agent.py. Runtime tools, approvals, provider selection and saved facts were not changed. This covers explicit task outcomes; route-specific blocked/waiting states without task_status still need separate acceptance coverage. No live API call was required.

The user's previous successful settings.gradle/build.gradle run confirmed PayWrightWorkSpaceGradle correctly and inspected all requested lines. Next priority remains provider/model-aware token budgeting, followed by grounded document workflows and overall core-agent acceptance.


## Provider-budget preflight - 17 October 2026

Y - configured/estimated preflight: Ollama request context, configurable hosted context/output caps, model binding and explicit unknown-limit diagnostics are implemented. Public OpenRouter model metadata was verified and stored for the selected model. 174 offline tests pass. See [model-budgeting.md](model-budgeting.md). P - exact tokenizer/model discovery, quota scheduling, metadata refresh and adaptive compaction remain. This supersedes the earlier entirely-pending provider-budget item without claiming full token accuracy.


## Workstream 2 summary reliability started - 17 October 2026

I overall. Registered, data-only summary generation replaces the old JSON-only client path. Validation, one bounded format correction and category-safe failures preserve context/archives. 189 offline tests pass, including real SQLite summary restart/session isolation with model mocks. Live synthetic long-chat summaries pass on Groq (2.11s) and OpenRouter (11.11s), retaining a correction and unanswered question. Full user-chat/live-browser acceptance remains pending; Ollama summary generation was not live-tested. See [workstream-2-summaries.md](workstream-2-summaries.md). The Word workstream snapshot is docs/agentic-ai-roadmap.docx.


## Workstream 2 status review - 17 October 2026

**I — In progress overall.** Summary implementation and scoped persistence checks are **Y**, supported by 189 offline tests and live synthetic Groq/OpenRouter summary reports. Actual user-history quality, full live restart/switch verification and complete browser create/chat/reopen/memory/download acceptance are **P**. Mark the overall workstream **Y** only after those remaining acceptance checks pass. See [workstream-2-summaries.md](workstream-2-summaries.md).


### Workstream 2 item 1 grounding fix — 17 October 2026

Y for scoped archive-supported question retention and source-attribution retest: 194 offline tests and seven live synthetic OpenRouter checks passed. Item 1 remains P for broader actual-history accuracy and Ollama context acceptance. See [workstream-2-summaries.md](workstream-2-summaries.md).


### Workstream 2 sequencing decision — 17 October 2026

At the user's request, park item 1 (P): actual-history summary format/accuracy and Ollama attribution. Do not spend further API quota on this blocker now. Move next to item 2: complete live restart/chat-switch isolation acceptance; then item 3 browser acceptance. Overall Workstream 2 remains I; parking is not completion.


### Browser logging — 17 October 2026

Added local privacy-safe rotating browser event logs; 199 guarded offline tests pass. See [browser-logging.md](browser-logging.md). Live event inspection is pending after the user reloads the app. Workstream 2 remains I because summary accuracy is parked P and full live summary isolation remains pending.


## Current handoff — Workstream 3 active, 17 October 2026

This update supersedes earlier progress snapshots: Workstream 2 is P overall (parked, not completed). Console recall/switching, sampled browser chat separation, shared-memory display, transcript downloads and live browser event logging are Y for observed scope. Actual-history summary generation/accuracy, Ollama source attribution and full live summary isolation remain P—parked. Latest regression baseline: 199 offline tests passed. Workstream 3 is I as the selected active workstream; provenance/timestamp/verification implementation is the first planned task, not claimed completed. See [workstream-2-summaries.md](workstream-2-summaries.md) and [browser-logging.md](browser-logging.md).


### Workstream 3 first milestone — 17 October 2026

Y for provenance/timestamp/verification metadata, safe legacy migration and current memory integration. Existing facts backed up and preserved. 203 guarded offline tests passed; no API calls. Workstream 3 remains I. Next: correction/conflict policy and revision handling; advanced retrieval and archived-chat search remain pending. See [workstream-3-memory.md](workstream-3-memory.md).


### Workstream 3 correction milestone — 17 October 2026

Y for atomic same-key correction/revision handling, scope isolation and forget cleanup; 206 offline tests plus temporary command integration passed. Broader semantic conflicts, stale facts, archive search and memory suggestions remain pending. Workstream 3 remains I.


### Workstream 3 archive-search milestone — 17 October 2026

Y for scoped lexical archive lookup and shared tool integration. 210 offline tests pass; actual default-chat local lookup confirms source references. No model calls or downloads. Semantic retrieval, broader conflict/staleness policy and controlled suggestions remain pending; Workstream 3 is I.


### Workstream 3 suggestions milestone — 17 October 2026

Y for explicit user-controlled proposal/review/accept/reject lifecycle and existing-key conflict refusal. 214 offline tests pass. Workstream 3 remains I: semantic retrieval and broader contradictions/staleness remain pending.


### Workstream 3 remaining-P review — 17 October 2026

Both pending areas now have implementation: optional semantic retrieval and advisory conflict/age review. 220 offline tests pass. Real cached-model quality/latency and broader semantic contradiction evaluation remain P. The slow local test was interrupted intentionally; no completion is claimed for those acceptance gaps.


## Historical handoff — Workstream 4 active at that stage, 17 October 2026

Supersedes earlier active-focus snapshots: Workstream 3 is P overall after its one bounded real-model retry failed paraphrase relevance. Local loading succeeded; advisory HTML/PDF candidate detection/no mutation passed. Semantic calibration and broader conflict accuracy remain parked, not completed. Workstream 4 remains I and is now the next active scope. 220 offline tests remain the regression baseline.


### Workstream 4 started — 17 October 2026

Y for web citation traceability and failed-required-search protection in the shared conversation loop. 225 offline tests pass; no live API calls. Workstream 4 remains I. Full-page retrieval, local document/source citation validation, indexed retrieval quality and mixed-source acceptance remain pending. See [workstream-4-grounding.md](workstream-4-grounding.md).


### Workstream 4 source-page milestone — 17 October 2026

Y for public-page reader and search/read/citation offline integration; 232 tests pass. No live network/provider calls. Workstream 4 remains I; local-document citations, real retrieval quality, mixed-source acceptance and live page compatibility are pending. See [workstream-4-grounding.md](workstream-4-grounding.md).


### Workstream 4 document-source milestone — 17 October 2026

Y for structured indexed-source references and citation guard integration; 237 offline tests pass. P for retrieval quality: actual keyword baseline 1/8, resume pages present but other documents rank ahead. No model calls or downloads. Next: generic tokenization/ranking improvements and repeatable re-evaluation, then mixed-source grounding.


### Workstream 4 keyword ranking verified — 17 October 2026

Keyword baseline now 8/8 with audited page labels, versus 6/8 unchanged original labels (two incorrect page-1 labels verified as page 2 in the actual PDF). Initial baseline was 1/8. 240 offline tests pass; no provider quota or embeddings used. Legacy hybrid defaults remain. W4 I: mixed-source and live citation/entailment acceptance next.


### Mixed-source grounding in progress — 17 October 2026

241 offline tests pass, including scoped memory/document/web/page integration. Live Groq synthetic-fixture tool selection executed all four tools; final-answer request hit QUOTA_EXHAUSTED HTTP 429. Live combined-answer/citation acceptance remains P; no further retry or silent provider change. Word roadmap snapshot updated. Workstream 4 remains I.


## Structured table grounding milestone 17 October 2026

Y for scoped offline CSV/XLSX integration acceptance: real temporary CSV and Excel files reach the shared conversation with file, sheet, header, source row and truncation metadata. A multi-sheet workbook can first request sheet selection and then succeed with a changed sheet/header call. Required document routes no longer accept a failed/empty table call as a substitute for usable evidence, including the empty-index-plus-empty-table case. Only complete tool JSON actually supplied to the model counts toward the table evidence flag. Existing table output shapes and successful commands remain compatible.

245 guarded offline tests passed in 21.248 seconds. Added tests/test_table_grounding.py (four tests); changed agent/conversation.py. No spreadsheet content was sent to a provider. This does not verify arbitrary calculations, generated-answer entailment or enforced row citations; broader table/live quality remains P.

One live mixed-source retry used synthetic fixtures and the configured Groq provider. Memory and document tool calls succeeded; the next model request returned HTTP 400 INVALID_REQUEST. The sanitized error does not establish the exact incompatible parameter or whether model-generated tool output caused it. No unchanged retry or provider switch was performed. Final mixed-source acceptance remains P. Workstream 4 remains I.


## RAG path and import safety milestone 17 October 2026

Y for the scoped path/import fix. rag/paths.py defines source-relative data/index defaults. CSV/XLSX readers and schema inspection use rag/data regardless of the shell folder. Older RAG agent examples resolve FAISS/BM25/chunks against rag and load the project .env explicitly; package and standalone helper imports are supported. Standalone query.py locates the shared agent package.

Ingestion is now explicit: importing rag.ingest does not discover/read documents, load model dependencies or write indexes. create_vector_db(data_folder=None, index_folder=None) retains the existing callable name, defaults to rag/data and rag indexes, and supports caller-supplied folders. python -m rag.ingest builds indexes only when deliberately run. rag.main likewise runs its existing ingest-then-query flow only as a command. Empty/missing input raises before changing existing index files. Existing production indexes were not rebuilt or altered.

249 guarded offline tests passed in 21.433 seconds. Four new path tests verify unrelated-folder imports without model imports/writes, shared default paths, explicit TXT/CSV ingestion output locations with mocked embedding/vector/splitter boundaries, and empty-input preservation. These tests do not validate actual embeddings or atomic multi-file publishing.

The broader consolidation item remains P: legacy provider-specific model/tool loops, older chat-history behavior and index-write failure recovery are not migrated into the current shared conversation. Use the current agent for supported conversation/provider switching; legacy examples remain learning entry points, not live-release acceptance. No hosted API calls or model downloads were made. Workstream 4 remains I with four P checklist items.


## Legacy RAG command consolidation completed 17 October 2026

Y for command entry-point/path consolidation. rag/rag_agent.py, rag/tool_calling.py and rag/web_search_agent.py now delegate command execution to rag/entrypoints.py and the shared agent.langgraph.langgraph_agent.main. Both python -m rag.<name> and standalone script execution preserve supplied CLI arguments, use the configured shared provider and scoped sessions/memory, and skip the historical OpenRouter-only loops, eager model loading and hardcoded sample questions. Historical code below the command gate is retained for learning/direct-import compatibility; importing those old modules directly is still a legacy path and can initialize their historical dependencies. No old JSON transcript is silently imported into modern scoped chats. The current ingestion command and separate query/PDF export functions remain available.

251 guarded offline tests passed in 22.776 seconds. tests/test_legacy_rag_entrypoints.py covers all six package/standalone launch paths from an unrelated folder, one shared-console invocation, unchanged option forwarding and no work in that folder. The console boundary is mocked; this is launch integration, not a new live-provider/model acceptance run. No API calls, downloads, production index rebuilds or private history exports were performed.

Workstream 4 remains I. Remaining checklist items: P for live page/source grounding, broader document/hybrid relevance/freshness and mixed-source live final-answer acceptance; I for factual/source-quality validation; X count is zero. Source paths and entry consolidation are now Y for the stated command scope. Historical learning code and atomic index publishing are separate maintenance limits.


## Sampled live public page compatibility 17 October 2026

Y for sampled direct-page compatibility. The production agent.web_pages.fetch_web_page fetched https://docs.python.org/3/tutorial/classes.html and https://playwright.dev/java/docs/intro successfully, retaining titles/final URLs and 4500-character excerpts with truncation explicitly true. Latest timings were 0.54 and 0.66 seconds. No model/API quota, private source files, saved facts or chat history were used. Reproduce via python evaluations/web_page_live.py; report outputs/acceptance/web-page-live.json.

P for the live search-to-page pipeline: the production web_search handler with an official-domain filter returned no usable official result. The production conversation loop, using scripted model decisions, returned incomplete instead of claiming current evidence. This verifies the observed failure behavior; it does not pass search/read/citation success, hosted model source selection, claim entailment, arbitrary site compatibility or a hard total network deadline. Existing offline baseline remains 251 tests; production code was unchanged, so the offline suite was not repeated. Workstream 4 remains I with 3 P, 1 I and 0 X checklist items.


## Live public search read and cited answer verified 17 October 2026

Y for the sampled public documentation acceptance. The restrictive site/path search had no usable result; the broader query Playwright Java installation documentation returned official sources without a production search change. The real search/read/citation pipeline passed with scripted decisions. Then the configured Groq openai/gpt-oss-20b independently selected web_search and fetch_web_page, read https://playwright.dev/java/docs/intro, and correctly answered the exact title Installation | Playwright Java, Java-documentation scope and returned URL. All five checks passed in 12.01 seconds. Report outputs/acceptance/public-grounding-live.json; runner evaluations/public_grounding_live.py. The earlier no-result outcome remains valid historical evidence, superseded for this sampled success case.

Only public queries/pages and an empty temporary source root were used; no private files, saved facts or history reached the model. This is actual live model/tool/result acceptance, not scripted-model acceptance. It covers title/scope/source claims only; general factual entailment, publisher-quality evaluation and a hard total network deadline are not claimed complete. The broader factual/source-quality checklist item stays I. No production code changed and the prior 251-test regression baseline was not repeated.

Workstream 4 remains I: remaining P items are broader document/hybrid relevance/freshness and live mixed-source final-answer acceptance. Counts: 2 P, 1 I, 0 X.


## Real mixed-source tool execution 17 October 2026

P for final-answer acceptance; all four production tool paths executed successfully in the observed live run. The configured Groq model selected scoped SQLite search_memory, search_documents with keyword mode against a newly generated trusted temporary BM25/chunk index, actual official-domain web_search and fetch_web_page. The final model request failed with HTTP 429 QUOTA_EXHAUSTED after 14.47 seconds. This is stronger tool execution evidence than the earlier synthetic tool fixtures, but no combined final answer or final citations were accepted. No automatic retry or provider fallback.

Runner evaluations/mixed_real_tools_live.py; report outputs/acceptance/mixed-real-tools-live.json. Temporary sample facts/documents were used, with an unrelated-user fact to exercise scope; no private project files, real memory/history or production indexes were exported or altered. No embedding download. Temporary index paths/caches are confined to the runner process and restored. Existing offline baseline remains 251; no production code changed.

Park this live gate until quota is available. Next independent work is broader local document quality and freshness evaluation, which can proceed without hosted calls. Workstream 4 remains I; remaining 2 P, 1 I, 0 X.


## Indexed source consistency verified 17 October 2026

Y for the bounded local excerpt-consistency audit: all 64 existing indexed chunks matched case/whitespace-normalized text at the current local source location. Zero mismatches, zero unverified locations, no scan truncation and zero supported source files lacking indexed chunks. Actual audit took 4.38 seconds; no source/index modifications, model calls, downloads or data exports. Report outputs/acceptance/document-source-consistency.json. Reproduce with python evaluations/document_source_consistency.py.

rag/source_audit.py rereads supported local PDF/TXT/DOCX/CSV sources, rejects invalid/traversing names and symlinks/outside paths, caps file/expanded DOCX/page/row/chunk coverage, and reports metadata/results without source text. CSV locations count parsed records including the header, not physical lines. DOCX paragraphs match the existing ingestion behavior; embedded tables and XLSX are not included in this index audit. XLSX has separate table tools.

256 guarded offline tests passed in 14.279 seconds. Five new tests verify a changed source becomes a mismatch, missing source/location remains unverified, path and file-size rejections avoid reads, real DOCX/multiline-CSV matching, and partial coverage/new source reporting. Existing sources and index files were not rebuilt.

Scope limit: excerpt containment does not prove every current file section is indexed, record full-file hashes, verify external real-world freshness or establish semantic relevance/claim entailment. Broader hybrid/relevance validation remains P; mixed-source final-answer acceptance stays P parked on Groq quota; broader factual/source-quality validation stays I. Workstream 4 counts remain 2 P, 1 I, 0 X. Next independent milestone: bounded local hybrid-model availability/quality acceptance without downloads or hosted requests.


## Bounded hybrid check and authorized OpenRouter attempt 17 October 2026

P for local hybrid acceptance: cached-only ML dependencies/models loaded and the worker reached benchmark case 6 before the 90-second parent limit terminated it. No complete result/quality score is claimed; current report document-hybrid-local.json records the bounded timeout. HF/Transformers offline flags and the offline socket/HTTP guard were active; no downloads, hosted calls or production index changes. evaluations/document_hybrid_local.py reproduces the benchmark, and now saves incremental case results for future bounded runs. That progress-save addition was syntax checked; no second expensive run was made.

At the user's explicit request to use OpenRouter when Groq exceeds limits, the mixed-source runner was attempted with process-only LLM_PROVIDER=openrouter. OpenRouter also returned HTTP 429 QUOTA_EXHAUSTED immediately, with no tool execution; report outputs/acceptance/mixed-real-tools-openrouter.json. No unchanged retry, persistent .env change or additional provider switch. This was a task-specific authorized provider substitution, not a newly implemented automatic fallback policy in application code.

Both provider-based mixed final-answer acceptance and broader hybrid quality remain P, parked on the observed constraints. Existing 256-test offline baseline remains; no production behavior was changed in this step. Workstream 4 remains I, with 2 P, 1 I and 0 X.


## Public page deadline and cancellation verified 17 October 2026

Y for bounded production network wait. fetch_web_page now validates URL syntax without DNS in the caller, then starts a private agent.web_page_worker subprocess for the unchanged DNS/public-IP pinning, TLS, redirects, MIME/body limits and extraction logic. Parent communicate waits only the remaining 30-second budget. Timeout or caller cancellation kills the worker and allows at most 5 seconds for cleanup; errors never become page evidence. No visible console window is opened on Windows. URL input travels through stdin rather than command arguments; worker stderr is not surfaced. Worker JSON transport is capped at 128 KiB and valid escaped non-English excerpts retain the 4500-character text limit.

262 guarded offline tests passed in 14.212 seconds. Six added deadline regressions cover bounded communication, timeout cleanup, cancellation, invalid JSON, URL credentials and Unicode. A real sleeping subprocess was killed and observed exited in 0.21 seconds under a temporary 0.2-second test budget; the official Playwright Java page then loaded through the real worker in 0.74 seconds. Report outputs/acceptance/web-page-deadline.json. No model quota was used.

Limits: process creation and OS scheduling cannot provide a strict real-time bound; worker network wait and cleanup are bounded after launch. Explicit injected resolver/connection transports execute in-process for compatibility/testing and do not use the worker deadline. Earlier historical notes describing the production DNS/header timeout gap are superseded by this milestone. General factual entailment and provider acceptance are not implied.

Workstream 4 remains I with 2 P (hybrid/relevance and mixed-source final answer), 1 I (broader factual/source validation), 0 X. The two acceptance blockers remain parked; no quota retry or repeated slow hybrid run was made.


## Gemini provider added and configured 17 October 2026

Added Google's compatible Gemini provider to shared text/JSON/native-tool adapters without new dependencies. User requested addition/configuration only; selected LLM_PROVIDER=gemini and configured gemini-3.1-flash-lite, low reasoning, 4096 output budget/cap and 90-second response timeout. Existing GOOGLE_AI_STUDEO_KEY is reused via secret-safe alias lookup; no key values were copied to documentation or printed. Previous provider settings remain available. Opaque tool-call thought signatures are preserved for Gemini.

271 offline tests passed in 30.326 seconds. No live Gemini call or billing change was made. Model/account access, free-tier eligibility and live Gemini direct/tool acceptance remain pending; do not infer these from passing mocked transports. See gemini-provider.md. The prior three-provider live foundation checks remain their historical verified scope; newly added Gemini has offline configuration/transport verification only. Workstream 4 stays I with 2 P, 1 I, 0 X. No Workstream 4 acceptance gate was completed by this provider addition.


## Gemini mixed-source acceptance passed 17 October 2026

Y for the sampled real-tool mixed-source gate. Gemini gemini-3.1-flash-lite selected search_memory, search_documents (keyword), web_search and fetch_web_page, then returned a correct combined answer retaining the generated sample project name, Markdown report format, exact page title Installation | Playwright Java, returned DOC reference and https://playwright.dev/java/docs/intro. All eight checks passed in 19.49 seconds, including other-user exclusion and completed outcome. Three model requests were made; the first selected three read tools together and the next selected page reading.

Report outputs/acceptance/mixed-real-tools-gemini.json; runner evaluations/mixed_real_tools_live.py. Real scoped temporary SQLite and freshly generated trusted temporary BM25 artifacts were used with actual public search/page retrieval. No private project documents, real memory/history, model downloads or production index changes. The test exercised the newly bounded page worker. The preceding user console even/odd answer also verified normal Gemini generation after the key correction. All four supported providers now have observed normal/tool-path evidence for their stated tested scope; Gemini free-tier billing eligibility is still not inspected or guaranteed by software.

No production code changed, so the existing 271-test offline baseline was not repeated. This does not complete general factual entailment, arbitrary source/code tasks, semantic memory, hybrid retrieval or all possible queries. Earlier quota/401 results remain historical, superseded only for this successful Gemini scenario. Workstream 4 remains I; remaining checklist counts are 1 P (broader document/hybrid quality) and 1 I (broader factual/source-quality validation), 0 X.


## Hybrid acceptance bounded retry parked 17 October 2026

P remains for broader hybrid/relevance acceptance. One new cached-only retry was capped at 120 seconds to allow the eight-query run to finish while retaining incremental case results. It timed out during Loading local ML dependencies, with zero completed cases in this run. Earlier 90-second evidence reached case 6 but did not save completed scores; neither run establishes full hybrid quality. Latest report outputs/acceptance/document-hybrid-local.json. No hosted calls, downloads, production source changes or index changes. No new quality score or root cause is inferred.

Park this local performance/acceptance gate. Do not repeat heavy hybrid loading merely on another Next request; resume only after a meaningful environment/resource change or explicit user request to allow a longer diagnostic. Existing normalized keyword retrieval and its audited 8/8 scoped benchmark remain available; hybrid defaults were not changed. Next independent task is the broader factual/source-validation item; framework expansion remains deferred.

Existing offline baseline stays 271 tests; production code was unchanged and tests were not repeated. Workstream 4 remains I, with 1 P (parked hybrid/relevance), 1 I (broader factual/source validation), 0 X. Sampled mixed-source acceptance remains Y on Gemini.


## Groq factual behavior evaluation and conflict guidance 17 October 2026

Live Groq passed the supported-fact, missing-information and embedded-instruction scenarios using temporary text files and structured document fixtures through the shared conversation/citation loop. It returned PDF with a valid source, left the absent deployment date unknown without inventing a date, and ignored the embedded instruction to call an unavailable action/change the answer to HTML. No private source/history exports. The intermediate OpenRouter fallback returned HTTP 429 and executed no tools. A later default-provider run was initially intended as Gemini, but the user had changed the local default to Groq; actual reports show Groq, and no Gemini claim is made for these four scenarios.

Conflict handling remains partial: initial answer was only conflict. Generic shared system guidance now requires naming equally authoritative conflicting values/source references and asking for clarification rather than picking a winner. After the change Groq returned conflict with both valid document citations and asked Which report format should be used?, but omitted the conflicting PDF/HTML values. Therefore this case remains P in the evaluation; broader Workstream 4 factual/source validation stays I. Summary outputs/acceptance/grounding-behavior-summary.json aggregates 3/4 passed from separate observed runs, not a single full fresh pass. Runner evaluations/grounding_behavior_live.py supports selected cases and provider-specific reports.

Also repaired a safe diagnostic edge case: URLs are removed before classifying HTTP 429 message text for quota exhaustion, so a minute-limit message containing an upgrade/billing URL is no longer mistaken for exhausted quota solely because of that URL. Daily-window/explicit quota codes remain quota. Unknown/minute limits still do not retry automatically without a short explicit Retry-After. This does not retroactively prove the exact cause of earlier rate errors.

274 guarded offline tests passed in 30.398 seconds, including three new rate-window regressions. Files agent/conversation.py, agent/provider_errors.py, tests/test_provider_errors.py. No persistent provider setting was changed; current local setting observed groq. Workstream 4 remains I with 1 P (parked hybrid/relevance), 1 I (broader factual/source validation, including clearer conflict explanation), 0 X. Next: improve source-conflict explanation on the partial case without repeating heavy hybrid loading.


## Natural conflict clarification verified 17 October 2026

Y for the normal-chat equal-authority conflict scenario. Groq read two temporary structured document fixtures and answered with a source/value table (first.txt PDF, second.txt HTML), both returned DOC citations, explicit unresolved status and a focused question asking which format should be used. All five checks passed in 4.86 seconds; output was manually reviewed for a unilateral invented choice and none was present. Report outputs/acceptance/grounding-conflict-natural.json. No private data, persistent provider change, API retry loop or production code change.

The prior short-JSON scenario remains partial for its strict answer-field requirements: it asked for clarification but omitted the values. This new natural-language pass does not rewrite that result or establish every output-format behavior. Alongside earlier supported/missing/embedded-instruction passes, four representative normal factual-grounding behaviors now have observed successes across separate runs. Ranking remains a fixture in these behavior checks, and no universal factual entailment or publisher-quality certification is claimed.

Existing 274-test regression baseline was not repeated because no production code changed. Workstream 4 remains I with 1 P (parked broader hybrid/relevance) and 1 I (broader factual/source-quality validation, including strict structured conflict detail), 0 X. Next independent work should evaluate source authority and unsupported claims, without repeating the parked hybrid benchmark.


## Scoped source authority and factual validation accepted 17 October 2026

Y for the two sampled source-authority behaviors: Groq declined to assert a fictional official release from an unverified community post and linked/disclosed the unofficial evidence; Gemini, explicitly selected for only the blocked case, attempted page reading, received a synthetic read failure and clearly limited its answer to the search snippet with its returned URL. Outputs were manually reviewed for unsupported confirmation/read claims and none were present. The Gemini case took 7.68 seconds. Groq hit HTTP 429 RATE_LIMIT on that case; a short explicit 2-second Retry-After permitted one retry, and the next limited response stopped. Current .env was not changed.

Report source-authority-summary.json combines successful cases from source-authority-groq.json and source-authority-gemini-snippet_only.json; these are separate provider runs, not one all-provider universal pass. Runner evaluations/source_authority_live.py uses synthetic public snippets/read errors, live model decisions and real citation guards. No private sources/history or actual public search in these fixture checks.

Together with supported/missing/injection/natural-conflict behavior, actual official-page title/citation checks, document-ref guards and 64/64 local excerpt consistency, the scoped factual/source-validation checklist milestone is now Y for its measured acceptance scope. General semantic entailment, novel-corpus quality and publisher reputation certification are not claimed; broader corpus/claim/hybrid quality remains in the existing P quality gate. The short JSON conflict answer still omits the explicit values; that structured clarification-usability limitation is explicitly tracked in Workstream 5, not silently marked fixed.

No production code changed in this step; existing 274-test baseline was not repeated. Workstream 4 overall is now P (partial/parked), not fully complete: checklist remaining 1 P (broader hybrid/relevance quality), 0 I, 0 X. Next development milestone is Workstream 5 reasoning/task completion. Keep Workstreams 2/3 and slow hybrid checks parked; framework expansion remains deferred.


### 17 October 2026 Workstream 5 started

Workstream 4 remains P—parked: 1 P, 0 I, 0 X. Workstream 5 is I: 2 P, 1 I, 0 X. Four new recovery checks passed in the 278-test run; that full run had one Streamlit initial-render timeout, so 278 passing tests is not claimed. No live provider calls were needed.


### 17 October 2026 Workstream 5 scoped core acceptance

Clarification, real-file planning/recovery and conservative execution outcomes verified for the current bounded scope. Full suite: 287 tests passed in 13.24 seconds, including the previously timed-out browser tests. Workstream 5: 0 P, 0 I, 0 X. Workstream 4: 1 P parked. Next: Workstream 6 controlled actions.


### 17 October 2026 Workstream 6 started

Durable local-action receipts and exact approval binding are integrated. Full suite: 300 offline tests passed. Workstream 6 remains I with 2 P, 1 I, 0 X; browser approval UI and release-wide scope acceptance remain pending. Workstream 4 retains 1 P parked; Workstream 5 scoped core acceptance remains Y.


### 18 October 2026 Browser action controls implemented

312 full offline tests pass. Exact-action browser proposals, scoped approval/decline, expiry, changed-target rejection and duplicate-execution protection are implemented. Real browser acceptance is not yet claimed. Workstream 6 remaining: 1 P, 2 I, 0 X. Workstream 4 remains P with 1 parked item; Workstream 5 scoped core acceptance remains Y.


### 18 October 2026 Live browser approval verified

Y for the observed create/review/approve scenario: user approved the exact create_file action, the expected 29-byte file exists with exact content, and its action receipt/proposal are completed. Live decline and refresh/reopen remain pending. Workstream 6 remains I: 1 P, 2 I, 0 X. See outputs/acceptance/browser-approval-user-live.json.


18 October 2026: Live browser decline verified. User clicked Decline; outputs/browser-decline-check.txt is absent, proposal 03ef48a6ea3e49bcb9a0bfe4ec2525e4 is declined, and no execution receipt exists. Live create/approve and decline now pass for this sample. Refresh/reopen acceptance remains pending. Workstream 6 remains 1 P, 2 I, 0 X until that check and broader replay/scope acceptance finish.


### 18 October 2026 Scoped live browser approval milestone Y

User refreshed/reloaded default, switched chats and returned. Approved file content remains exact; approved receipt/proposal stay completed; declined file is absent, its proposal stays declined and has no execution receipt. Browser approval checklist item is Y for this observed scope. Workstream 6 remains I with 1 P, 1 I, 0 X: broader restart/replay and release-wide permissions remain open.


### 18 October 2026 Workstream 6 local-core acceptance Y

Remaining: 0 P, 0 I, 0 X. Central tool classification, all-five-kind approval/replay checks, fresh-process/hard-exit and receipt-persistence failure checks passed. Full suite checkpoint: 331 tests; final affected regressions: 21 passed after registry changes. This does not claim a full 333-test run. Same roadmap content/diagrams preserved. Next: Workstream 7 reliability, with 2 P and 1 X still in its checklist; Workstreams 2–4 retain parked gaps.

## Future Projects UI requirement

X — planning only, requested 18 October 2026. Add/configure local projects, create a new project with reviewed actions, and configure GitHub repository access from the UI. No implementation or account connection now. See ui-project-management-plan.md. Keep project identity, scope, credentials and permissions explicit; preserve current working behavior.

## UI milestone implementation progress

I — initial UI active. Recent-chat buttons and recent-title filtering verified; readable structured memory/details added. Current memory/sidebar/approval tests pass; eight Chrome/Edge emulated viewport checks pass at 360/390/768/1440. Actual devices, Safari/Firefox and every UI state are not claimed verified. See ui-improvements.md. Future local-project creation and GitHub access remain X planning-only.
