# Workstream 7 — Reliability

Status: I. Updated 18 October 2026.

## Verified save-failure handling

`agent/chat_runtime.py` preserves the generated answer when the final checkpoint update raises an exception. It returns separate archive/checkpoint persistence flags and a warning to check the stored action receipt rather than repeat an action. Archive failures skip summarization. Raw filesystem errors are not displayed.

`tests/test_chat_runtime.py` covers archive-only failure, checkpoint-only failure, both failures, one invocation only, lock release and existing normal behavior. Four focused tests passed; the whole suite was not rerun for this change.

## Remaining

- Y: scoped SQLite transaction crash rollback and crash lock recovery verified; see limits below.
- P: provider/network/quota/truncation checks through supported interfaces.
- P: larger-task context budgets and relevant evidence selection.

This handles caught save exceptions. It does not claim crash recovery or atomic archive/checkpoint transactions. The existing Word roadmap has not been updated for this slice.

## Crash-safe chat locks — 18 October 2026

The shared console/browser runtime uses a persistent `.guard` file with an OS byte-range lock on Windows (flock on other platforms). A running owner blocks another process; process exit releases ownership automatically. Guard files must not be removed or replaced while clients run. Their presence does not mean the chat is busy.

Old `.lock` files remain blockers, are never automatically removed, and require inspection after stopping old clients. Restart console/browser processes together when adopting this runtime; mixed old/new clients are not supported.

Six focused runtime tests passed, including a real child process exiting with code 73 while holding the lock, contention before exit, and successful acquisition afterward. Legacy-file preservation also passed. No real user locks were removed. Full-suite verification and crash-during-checkpoint persistence are still pending.

## Interrupted checkpoint transaction acceptance

Seven focused runtime/recovery tests passed. A fresh child process builds a real LangGraph SqliteSaver checkpoint and commits a transcript, holds the chat lock, mutates checkpoint bytes inside an uncommitted SQLite transaction, then exits with code 73. Another process verifies SQLite integrity, the prior committed graph state, the single archived turn, and lock acquisition. All data is synthetic and temporary; no provider calls or user database changes.

This tests SQLite rollback around the actual checkpoint table, not interruption at every internal SqliteSaver instruction. Archive and checkpoint databases remain separate; no automatic reconciliation or action replay is performed. Existing action-receipt restart tests cover duplicate-action protection independently. Whole-suite rerun remains pending.

Remaining Workstream 7 checklist items: 2 P, 0 I, 0 X; overall I. Word roadmap remains unchanged for these reliability slices.

## Provider failure interfaces — 18 October 2026

32 focused tests passed across test_provider_errors, test_foundation_errors, test_streamlit_ui and test_gemini_provider. The new matrix injects ProviderError at the browser backend boundary for four provider labels and six categories: authentication, rate limit, quota, response timeout, tool output and output limit. Each failure appears without an uncaught UI exception or failed transcript insert; a subsequent fake successful request saves normally in the same chat. The console formatter is checked for the same 24 cases. Existing mocked HTTP/transport tests cover classification, bounded retries, malformed JSON and redaction.

Scope: simulated interface errors plus existing mocked client diagnostics, not 24 live provider requests or comprehensive provider-adapter fault coverage. No API quota used. Production code was unchanged for this slice.

Remaining: 1 P (larger-task context budgets/evidence selection), 0 I checklist items, 0 X; overall I. Word document has not been synchronized for these reliability slices.

## Context budgets and final scoped acceptance

AI_CHAT_MAX_CONVERSATION_CHARS configures the conversation envelope, default 36,000 and allowed 4,000–200,000. It is distinct from model output limits and provider context configuration. Existing project evidence budgets preserve the exact task; memory retrieval ranks scoped lexical matches. New tests reject oversized exact tasks before calling a model and exercise Unicode/schema preflight for all four providers without mutating input. 25 focused checks passed.

Final full offline regression: 343 tests passed in 45.360 seconds. Log: outputs/acceptance/workstream-7-offline-final.log. Workstream 7 scoped checklist: Y, 0 P / 0 I / 0 X. Next: Workstream 8 release gate. Token estimates, unknown hosted context limits, non-atomic archive/checkpoint databases, legacy-lock inspection and parked broader retrieval quality remain explicit limitations. The Word roadmap still needs synchronization and visual verification.
