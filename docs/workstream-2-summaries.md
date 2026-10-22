# Workstream 2 summary reliability

Updated 17 October 2026. Workstream 2 remains I. The new summary path is implemented and verified for the stated synthetic/offline cases; full user-chat and live browser acceptance remain pending.

## Change

Previously summaries used the text client's JSON-only response mode, separate from the registered tool path. Earlier user runs reported Groq HTTP 400, but the old raw rejection payload is not available; its exact invalid field was not established. The new path registers a data-only submit_conversation_summary function and validates facts, decisions and open_questions before replacing any context. It cannot execute project actions or grant permissions.

Each list is limited to 10 nonempty strings, each string to 300 characters, and encoded JSON to 5000 characters. The summary output budget is 4096 tokens, subject to provider preflight. Plain JSON summary text remains compatible. Invalid format gets one correction attempt; a provider failure or repeated invalid format preserves prior context and archives, with the existing five-minute retry cooldown. Diagnostics now use safe provider categories.

## Verified evidence

- 189 guarded offline tests passed in 5.879 seconds.
- Registered summary replies, plain-JSON compatibility, one format correction, rejection of historical action calls and safe error reasons are tested.
- Real SQLite checkpoint and transcript tests summarize two separate chats, reopen storage, switch sessions and verify each history/summary stays separate and all original turns remain archived. The answering/summarizing model is mocked in this storage test.
- Live Groq summary on synthetic long chat: Y, 2.11 seconds.
- Live OpenRouter summary on synthetic long chat: Y, 11.11 seconds.
- Both live cases retained a corrected project name, an unanswered question and a complete recent-turn boundary within the summary-size limit. No private project content was sent; selected provider remains OpenRouter.
- Reports: outputs/acceptance/summary-groq.json and summary-openrouter.json. Reproduce deliberately with evaluations/summary_live_acceptance.py --provider openrouter or groq; this consumes provider quota.

## Files

agent/summary_model.py, agent/context_summary.py and agent/chat_runtime.py; tests/test_summary_model.py and tests/test_summary_sessions.py; evaluations/summary_live_acceptance.py.

## Still pending

Actual user-history summary evaluation, live restart/switch validation in the client and a complete live browser create/chat/reopen/memory/download pass. Synthetic cases do not prove every long chat's factual quality. Local Ollama summary generation was not live-tested in this step; its context preflight may safely reject a large summary request. No model context was increased automatically. Semantic summary quality and historical-turn-boundary ambiguity remain explicit acceptance concerns.

Restart the agent to load the change. Continue a saved chat normally; when enough old context accumulates, the summary-success notice should appear. Failure should preserve the archive and give a specific safe reason instead of claiming success.


## Item 1 acceptance review — 17 October 2026

**P — not complete.** User-provided OpenRouter execution confirms an actual chat summarized successfully, followed by restart recall of HashMapDemo and its insertion, lookup, existence, update, deletion, iteration and null-handling examples. This verifies that recent example, not the factual coverage of every older summarized turn.

The explicit synthetic long-chat runner now accepts --provider ollama. Its configured-model check returned CONTEXT_PREFLIGHT: estimated input 4952 tokens plus 256 reserve exceeds the configured 4096-token context before output space. Attempts: 0; no inference request sent. Report: outputs/acceptance/summary-ollama.json. Provider selection and context configuration were not changed. This is a verified safe rejection, not successful Ollama summary acceptance.

Remaining: inspect representative actual older-turn summaries for retained corrections, decisions, paths and unanswered questions; and obtain a successful local summary with a model/context that fits, or explicitly agree to a hosted-only summary scope. No automatic context increase or model download was performed.


## Local actual-history audit — 17 October 2026

Read-only review of the current saved summary, 322 historical checkpoints in the default thread, and archived user questions. No API calls or conversation edits.

- Y for sampled retention: Java preference matches an explicit user statement; PayWrightWorkSpaceGradle matches earlier assistant reports identifying settings.gradle. Framework/version entries also occur in earlier assistant answers; this comparison does not independently verify those files.
- P for provenance: summarized framework/version claims are presented without retaining that their available source is an assistant answer. A past assistant assertion is not independently verified tool evidence.
- P for unresolved-question fidelity: browser-version and test-data questions appear in the saved summary but corresponding wording was not found in available checkpoint histories. This is an unsupported addition concern, not proof that no missing historical source ever existed.
- HashMap restart recall does not independently prove older-summary quality: the example may remain in recent context.

Item 1 remains P. Next repair should require source attribution and retain only explicitly unresolved questions, followed by regression tests and another live summary accuracy evaluation. Saved user data was not rewritten.


## Grounding hardening — 17 October 2026

Updated agent/context_summary.py source-attribution and unresolved-question instructions and the summary_model.py correction prompt. tests/test_context_summary.py verifies policy delivery and conservative unsupported-question rejection. 192 guarded offline tests pass in 3.221 seconds.

Live synthetic OpenRouter evaluation took 18.90 seconds: corrected identity, Java preference, assistant attribution, answered-question removal and report-question retention passed. Unsupported prior browser/test-data questions were still repeated, so semantic acceptance FAILED (P); see outputs/acceptance/summary-grounding-openrouter.json. This report precedes the conservative validation guard.

The subsequent guard rejects an exact normalized prior-question carryover if it lacks matching text anywhere in available history. Caller failure handling preserves context/archive and applies cooldown. It is not semantic verification: paraphrases can escape detection, and legitimate prior-only unresolved questions may be rejected when their original turns are unavailable. No stored summaries were rewritten. Supporting archived-turn evidence retrieval and a successful post-guard live accuracy evaluation remain pending. Item 1 and Workstream 2 remain P and I respectively.


## Scoped archive evidence and successful retest — 17 October 2026

Y for the tested grounding fix. ChatCatalog.summary_question_evidence searches only the selected user/memory-space/session, at most 10000 newest archived turns, 10 candidate questions and 4000 evidence characters. Exact normalized matches in user text include a bounded adjacent answer. compact_context removes unsupported prior questions from the summary request and retains supported ones with archive evidence; run_turn connects this lookup for console and browser. Stored conversations are not rewritten. An archive-read failure preserves the existing context through the normal summary failure path.

194 guarded offline tests pass in 4.982 seconds, covering scoped evidence lookup, bounded output, support outside recent context, and unsupported carryover rejection. The reproducible evaluations/summary_grounding_acceptance.py uses temporary synthetic archives and the configured provider. OpenRouter passed all seven checks in 17.32 seconds: Java preference, corrected project, archived unanswered report question, removal of unsupported browser/test-data questions, removal of an answered question, source attribution and successful summary creation. Report: outputs/acceptance/summary-grounding-current.json.

Limits: exact wording is a conservative baseline, not semantic retrieval; paraphrased valid questions may be omitted. An archived question being asked does not prove it remains unanswered; adjacent answers aid model reasoning, but later resolutions outside the supplied evidence are not exhaustively searched. Oversized/missing/legacy unarchived sources may yield no evidence. The prior full-turn delimiter ambiguity remains. Synthetic success is not universal actual-history acceptance. Item 1 remains P until broader actual-history accuracy and the Ollama context limitation are resolved or scope is explicitly revised.


## Preference tool-use correction — 17 October 2026

Updated agent/conversation.py instructions: the current request defines the task; preference statements/corrections receive acknowledgement rather than resuming old project inspection. User-only recall must use user context and leave undecided choices undecided. Acknowledgement does not claim reusable memory storage. No keyword-based fixed answers or provider settings were added.

The synthetic live acknowledgement check was rejected by OpenRouter with HTTP 429 QUOTA_EXHAUSTED, attempts 1. No automatic retry or provider switch; live behavior remains P. Evidence: outputs/acceptance/preference-tool-use.json. User's previous actual correction/recall was correct, but the first statement caused unnecessary tool use. Post-change user verification remains pending after quota becomes available.


## Groq retest after user provider change — 17 October 2026

.env now selects Groq with its existing key (key not printed or changed). Live synthetic summary grounding passed all seven checks in 3.42 seconds, including one bounded format correction. Live preference acknowledgement passed in 1.10 seconds with zero tool calls. Reports: outputs/acceptance/summary-grounding-groq.json and preference-tool-use-groq.json. No runtime code changed in this retest; the latest offline baseline remains 194 passing tests.

These verify synthetic Groq behavior, not full actual-user-history summary/restart acceptance. Item 1 remains P for that broader acceptance and successful Ollama context-fit summary verification; Workstream 2 remains I. Restart a running agent after provider changes.


## Ollama live grounding evaluation — 17 October 2026

Ran qwen2.5-coder:7b locally with process-only OLLAMA_NUM_CTX=8192 and timeout 600 seconds. Saved .env provider/context values were not changed; Ollama loaded an 8192-token context for this evaluation and used about 5.5 GB on CPU. Preflight estimated 5384 input tokens and reduced requested output from 4096 to 2552 tokens. Input was not silently truncated.

Model request completed in 275.75 seconds; total evaluation 275.79 seconds. Six of seven checks passed: summary generation, Java preference, corrected NewDemo project name, archived report question, unsupported-question removal and answered-question removal. Source attribution FAILED: Gradle was retained as an unqualified fact rather than assistant-reported. Report: outputs/acceptance/summary-grounding-ollama.json.

Y for successful local context-fit inference and six scoped behavior checks. P for full Ollama summary accuracy/source attribution; larger context alone does not solve model grounding. Default 4096-token configuration still cannot fit this fixture. Item 1 remains P. The synthetic Groq evaluation previously passed all seven checks in 3.42 seconds. No further Ollama retry was performed.


## Provider-side format correction — 17 October 2026

User forced compaction (threshold 3000, recent 2000) and Groq rejected generated summary format; answer recall still correctly reported PDF/folder undecided, and the runtime retained its previous summary and applied cooldown. summary_model.py previously corrected only locally validated bad responses. It now also handles ProviderError TOOL_OUTPUT with one changed data-only summary request, sharing the existing two-call ceiling. No failed generation is executed or consumed, no quota/auth retries or provider switching are added. Tests cover correction, bounded repeated failure and immediate quota propagation.

197 guarded offline tests passed in 8.384 seconds. Synthetic Groq grounding recheck passed all seven checks in 1.79 seconds. Real saved-history API recheck was blocked by automatic approval review because explicit authorization for exporting that historical context to Groq was unclear. Approval was requested; no private-history API call ran from that rejected action. Item 1 remains P pending actual-history verification and Ollama attribution acceptance. Restart is required to load the fix; existing five-minute summary retry cooldown remains.


## Authorized actual-history check — 17 October 2026

User authorized the recommended real-history Groq test. Read the default checkpoint without modifying it and ran forced compaction (3000/2000). The first reply did not pass local summary validation; the single corrected request received Groq TOOL_OUTPUT HTTP 400. Report: outputs/acceptance/summary-actual-groq.json. No new summary was committed.

A structural-only diagnostic attempt again received a first reply requiring correction, then HTTP 429 QUOTA_EXHAUSTED. No raw conversation, provider message or failed generation was printed. Structural report outputs/acceptance/summary-rejection-shape.json contains only the quota response metadata. The precise local validation defect and HTTP 400 generated-output defect were not established; do not claim the format fix is fully accepted. No further requests were made after quota exhaustion. Real-history summary acceptance remains P; saved checkpoints unchanged. Existing synthetic tests remain passing evidence only for their stated fixtures.


## Parked by user — 17 October 2026

P — PARKED. User requested moving on rather than spending more time on blocked summary acceptance. No more summary API calls now. Resume format diagnosis/actual-history accuracy and Ollama attribution later. Next: live chat-switch isolation (Workstream 2 item 2). Overall Workstream 2 remains I.


## Browser transcript acceptance evidence — 17 October 2026

User opened localhost:8501 and confirmed opening default chat. Inspected user-supplied downloaded JSON locally: conversation (1).json and (2).json each contain the same single browser-test turn (Browser acceptance def); conversation (3).json contains 24 default-chat turns, including HashMap and HTML-to-PDF report preference discussion plus the latest clarification interaction. All 24 entries contain question, answer and created_at. The browser-test question is absent from default's export.

Y for these observed chat-specific transcript downloads, restored default conversation and tested transcript separation. This verifies the sampled exports, not exhaustive isolation across every chat. Saved-memory display, switching back/reopening the browser-test chat and browser restart acceptance still require explicit user confirmation. Full browser acceptance and overall Workstream 2 remain pending; summary item 1 is parked.


## WS2 summary format and scoped restart verification - 20 October 2026

Y for the reproduced Groq response-name defect. The actual default-chat snapshot repeatedly produced valid facts/decisions/open_questions arguments under functions.submit_conversation_summary. The previous exact-name guard correctly rejected the unrecognized name. Production agent/runtime/summary_model.py now recognizes only that exact Groq-qualified alias as summary data, then performs the existing summary validation. Unknown functions/actions, extra fields, malformed values and repeated invalid output still fail. Request-scoped browser provider selection is respected. Other providers and their transport/request options remain unchanged; the forced-function experiment was removed after inconsistent live behavior. No content-specific answers or credentials were added.

Y for a sampled redacted actual default-history check: 6,192 history characters summarized in one Groq request in 9.88 seconds. The saved checkpoint was read through a read-only/in-memory snapshot and was never replaced. Local review found retained project paths, PDF preference and historical action requests, with framework/version claims labelled assistant-reported. This is sampled retention/attribution evidence, not proof of every summary claim or every user history. Only structural metadata was saved in the report; generated actual summary text was not written to acceptance files.

Y for scoped fresh-process backend summary restart/switch acceptance. Two synthetic chats generated real Groq summaries into temporary SQLite stores. A separate process reopened them, switched alpha -> beta -> alpha, used the restored summaries, retained their different report formats/reference markers, excluded the other chat/user, and preserved all original transcript turns. Reopening made zero summary calls. Temporary fixtures were removed. This covers the shared console/browser backend; it is not a fresh live UI click/relaunch test for every browser/provider. Earlier user console/browser separation evidence retains its stated scope.

74 focused offline tests passed in 9.522 seconds on final code (six new namespace/provider-scope regressions). Checks include summary validation/failure cooldown, real SQLite session isolation, transport compatibility, CLI commands and legacy module identity. Prior 428-test package acceptance predates this change; no fresh 434-test full-suite claim is made. Earlier rate-limit and output-limit attempts remain recorded and do not count as passes. No retries of unchanged exhausted-quota requests or long Ollama runs were made.

Overall Workstream 2 remains P. Remaining: broader representative actual-history accuracy and Ollama attribution/context-fit acceptance. Groq's reproduced namespace-format defect is fixed for the observed scope. Full live UI summary restart/switch remains outside this backend acceptance and must be checked before any broader claim. Restart running console/Streamlit processes to load the fix. Existing user chats, facts, action receipts and .env remain unchanged by this WS2 work.

Evidence: outputs/acceptance/ws2-progress-20261020.json; ws2-diagnosis-saved-default-current.json; ws2-restart-groq.json; ws2-summary-focused-final-20261020.log. Diagnostic/acceptance runners are evaluations/summary_history_acceptance.py and evaluations/summary_restart_acceptance.py. Source backup retained at outputs/ws2-summary-before-20261020-210502.

## WS2 isolated browser summary acceptance - 20 October 2026

Y for the measured Chrome desktop scenario: the actual Streamlit entry point and BrowserBackend generated Groq summaries for two synthetic chats in temporary SQLite stores. Browser clicks and page reload retained each chat's reference marker and distinct PDF/HTML preference. After stopping the test server and browser, new processes reopened alpha -> beta -> alpha, used unchanged persisted summaries and preserved all original/full transcript turns. Other-chat/user data stayed excluded. Reopening made zero summary-generation invocations. The test server and browser drivers stopped; temporary stores were removed. User chats, facts, receipts and provider settings were not changed.

The fixture's normal answers are deterministic acknowledgements/probes; only summary generation is live. Graph dependencies are preloaded before Streamlit watchers, so this is not production cold-start or normal model-answer-quality acceptance. One offline browser fixture passed. Initial offline/live startup attempts timed out; a stack sample showed LangGraph/LangSmith import work. The isolated harness now prepares those imports before serving the UI and tracks/cleans its owned browser process tree. Earlier failures remain recorded and are not passes. No application module changed in this step.

Overall WS2 remains P for broader representative actual-history accuracy, Ollama attribution/context-fit acceptance and wider actual-chat/provider UI coverage. The synthetic Chrome browser restart gate is Y for its stated scope only.

Evidence: outputs/acceptance/ws2-browser-groq/result.json and ws2-browser-offline/result.json. Initial timeout evidence: ws2-browser-initial-timeout.json and ws2-browser-groq/initial-result.json. Reusable runners are evaluations/summary_browser_acceptance.py and evaluations/summary_browser.cjs. New acceptance code belongs in the existing evaluations area; application changes should reuse the appropriate agent subpackage, with new subpackages only when necessary.



## WS2 targeted attribution guard — 22 October 2026

User resumed WS2 after the actual-project status audit. Addressed a specific new-summary validation gap: the recorded Ollama output's unlabelled Gradle claim passed schema validation despite losing assistant attribution. New generation through runtime/summary_model.py now validates every fact/decision prefix as user-stated:, assistant-reported: or tool-verified:, with nonempty claim text. Questions retain their existing form. Missing/unknown labels receive only the existing single changed correction; rejected summaries do not replace checkpoint context. The application does not guess or automatically assign a source label. Existing saved-summary schema reading is unchanged, so legacy strings remain readable without a database migration. Instructions/schema descriptions now explicitly request the same contract.

Y for this scoped validation/correction/preservation change: 132 affected offline checks pass, including eight new cases and real SQLite rejection/cooldown/reopen/other-chat preservation. This is an affected-path regression set, not a new full-project pass. Existing provider choice, aliases, budgets, action registries, approvals and .env remain unchanged. Canonical files: agent/runtime/summaries.py and agent/runtime/summary_model.py; tests reused existing summary modules. The existing synthetic evaluator gained --provider, --output and --max-tokens for isolated evidence without overwriting older results.

Y for one new public synthetic Groq acceptance: all 7 checks passed in 1.71s at an evaluator-only 1024-token output budget, with automatic provider fallback disabled for the probe. The summary retained Java, the explicit project correction, the archived report-folder question, removed unsupported/answered questions and labelled Gradle assistant-reported without file evidence. Private history/checkpoints were not read or sent; only a temporary synthetic catalog was used. No further provider or slow Ollama retry was made.

This guard validates attribution presence/encoding, not factual truth or whether a model chose the correct source role for every claim. Broad semantic summary accuracy and the changed path's Ollama live acceptance remain P. Existing completed restart/isolation, chat controls, summary batching and Continue implementations are not reopened. Evidence, original-source backups and exact diffs: outputs/acceptance/ws2-attribution-20261022. Restart console/Streamlit processes to load imported runtime changes. Word synchronization is separate.


## WS2 actual-default snapshot retention and recall — 22 October 2026

Y for one bounded redacted real default-chat sample on Groq. Read the current checkpoint through read-only SQLite into an in-memory snapshot (4,392 history characters and 771 prior-summary characters). Actual archived user statements independently establish the correction from HTML to PDF and the undecided report folder. One new summary request retained those facts and kept the surviving build-tool claim assistant-reported. No unsupported open questions or new current-approval decision appeared. A subsequent read-only recall request from the exact captured generated summary and the same recent context returned PDF and an undecided folder. The captured summary was replayed in memory with its recorded 639-character encoded size checked; it was not regenerated or committed.

The initial evaluator had a false positive: it classified user-provided project paths containing PlayWright/Gradle substrings as technology claims. Manual source-role review and a corrected clause-prefix check resolved this evaluator defect without changing the generated answer, source expectations, or application. The original pending report remains before-evaluator-correction.json. The final structural report does not persist private source/summary/recall text.

The new summary call took 2.56s (3.04s for the first diagnostic phase); the recall phase took 0.79s. Saved checkpoint summary/history matched the original snapshot on read-only recheck. No user database commit, new summary migration, provider-setting change, application edit, extra summary generation or regression rerun occurred. Existing 132 affected offline-test evidence is retained rather than repeated.

This is sampled actual-history retention/attribution and recall acceptance, not universal summary truth, lossless retention, a fresh actual-chat browser restart, or all-provider acceptance. The summary remained within the ten-fact bound and compressed some older stack/version details. Prior scoped restart/isolation checks remain independently Y. Remaining WS2: broader selected actual-chat/provider quality, changed-path Ollama attribution/context fit, and hosted-provider continuation acceptance. No WS4 Java-grounding pass is implied. Evidence: outputs/acceptance/ws2-real-history-20261022/result.json. Word synchronization is separate.


## WS2 scoped live Groq Continue acceptance — 22 October 2026

Y for synthetic general-text continuation through the existing shared turn backend using actual Groq section generation and temporary SQLite stores. Three independent processes passed partial -> restart/CONTINUE -> restart/FULL ANSWER. Section 1 was durably published before an injected pause; restart requested only section-2 and section-3, without replanning or replaying the graph. Final consolidation contained each planned heading once, and repeating CONTINUE after completion made no model request. All checkpoint/archive writes succeeded. Three actual hosted requests generated the three completed section bodies, at an evaluator-only 1536-token output budget. Exact duplicate section replay was absent; universal semantic deduplication is not established.

The initial output-limit trigger, three-part outline and later quota pause were scripted. This tests real hosted section compatibility and durable resumption, not naturally exhausted quotas, full multi-provider failover, UI clicks or factual truth. The initial evaluator attempt failed before network access because its book-club prompt entered source-sensitive routing; the fixture was corrected to a fictional discussion club. No production policy was relaxed to make it pass. The existing evaluator now has explicit --live-provider groq opt-in; its default remains network-blocked. An offline three-process check also passed. Only the evaluator and these records changed; user chats, settings and application code remained untouched. Temporary stores were removed.

Evidence: outputs/acceptance/ws2-live-continue-20261022/summary.json and groq-scope-corrected/process-restart.json; per-phase logs retained. Reproduce with python evaluations/answer_continuation_acceptance.py --live-provider groq --output-dir outputs/acceptance/continue-groq-new-run (consumes provider quota). Earlier offline-only and queued notes retain historical scope and are superseded for this sampled hosted Continue gate. Overall WS2 remains P for broader actual-history/provider quality and Ollama attribution/context fit. The separate WS4 Java factual-review problem remains P. Word synchronization is separate.
