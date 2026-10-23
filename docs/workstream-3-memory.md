# Workstream 3 — Useful long-term memory

Status: P - BLOCKED — Windows Application Control blocks the SciPy native component needed for expanded local semantic calibration. An approved compatible native runtime is required; device policy is not bypassed. Y: Gemini completed the full finite eight-case post-fix hosted review in one coherent run, including the corrected role-clarification behavior. Storage, provenance, explicit corrections, archive search and controlled suggestions retain their verified scope. Historical milestones below retain their stated scope.

## First milestone implementation — 17 October 2026

- Existing created_at and updated_at storage timestamps are retained; they do not prove when a real-world fact became true.
- Added source_kind, source_ref and verification_status. Old facts migrate as legacy_unknown/unverified, with no guessed source.
- REMEMBER saves user_statement / REMEMBER command / unverified. Seed imports label future imports seed_import; existing seed values are not reimported or relabelled by guessing.
- Existing save/get/list/search/delete signatures remain compatible; save accepts optional keyword metadata. Replacement preserves creation time, changes update time and resets verification unless explicitly supplied by a trusted evidence-producing caller.
- SHOW MEMORY, browser saved facts and LLM memory context expose metadata. Search results include the same fields. Existing key/value prefixes remain.
- Verified status is accepted only for tool_evidence with a nonempty reference. This is a caller contract, not automatic truth verification; no LLM tool can set those metadata fields. Ordinary REMEMBER cannot mark a fact verified.

## Evidence

203 guarded offline tests passed in 11.436 seconds. Migration/reopen tests retain old values and dates; scope isolation, invalid metadata rejection, replacement verification reset, old API compatibility and source display are covered. Real database backup and migration preserve all 5 existing rows, values and timestamps; report outputs/acceptance/memory-provenance-migration.json includes the backup path. No hosted API calls were needed.

Files: agent/memory/long_term_memory.py, agent/langgraph/langgraph_agent.py, agent/conversation.py, tests/test_memory_provenance.py.

## Try it

Restart the console agent or Streamlit server. Existing REMEMBER key = fact, SHOW MEMORY and FORGET key commands still work. SHOW MEMORY now includes source, verification and timestamp metadata. legacy_unknown means historical provenance was not recorded, not that the fact is false. Do not put credentials in facts or source references. The database backup contains private memory; keep it local.

## Historical next step — 17 October 2026

Implement explicit correction/conflict policy and test it without silently merging unrelated keys/projects. Same-key overwrite already works, but revision history, contradictions across different keys, stale facts and semantic conflicts remain pending. General archived-conversation search and user-controlled memory suggestions remain pending. Browser live metadata-display confirmation remains pending; headless shared UI tests passed. Workstream 2 summary issues stay parked.


## Explicit corrections and revision history — 17 October 2026

Y for same-key corrections with scoped revision history. save() uses one SQLite write transaction for prior-version capture and current-value replacement. A changed value or provenance stores the prior record; an identical re-save creates no duplicate revision. Current retrieval/search never includes superseded values. Existing verification-reset rules remain. Different keys, users and namespaces are not merged.

MEMORY HISTORY key shows the current value and up to 20 newest superseded versions without an LLM. History is explicitly labelled historical data, not current facts or permissions. FORGET cascades removal of that fact's revisions; delete_user also cascades. Archives, existing backups and provider records are not erased by FORGET.

206 guarded offline tests passed in 36.271 seconds. Added restart, user/namespace/key isolation, duplicate suppression, deletion and rollback tests. Actual memory command functions also passed save/correct/history/forget integration in a temporary database with no API calls or changes to user facts. Files: agent/memory/long_term_memory.py, agent/langgraph/langgraph_agent.py, tests/test_memory_revisions.py.

P remains for semantic contradictions across different keys, stale-fact policy and suggestions requiring user confirmation. Revisions grow with changed saves until deletion; no expiry or pruning is claimed. Raw legacy values are preserved, not retroactively repaired. Workstream 3 remains I. Restart the agent to use MEMORY HISTORY key.


## Scoped archive search — 17 October 2026

Y for implementation and offline integration: ChatCatalog.search_turns reuses existing SQLite transcripts; returns chat ID/title, turn ID, timestamp and question/answer excerpts. All query tokens must match (lexical, newest first). Fixed caller user/space scope, parameterized session selection and a current-chat default prevent default cross-chat retrieval. Native search_chats supports explicit all-chat scope within that user/space when requested. New conversation_session state is supplied by shared run_turn for console/browser.

Limits: query 1500 characters/20 terms, up to 20 matches, newest 10000 scanned turns, first 8000 characters per question and answer, 600-character excerpts and 7000-character match budget. Returned coverage warnings prevent claiming full-archive absence. Historical answers are labelled assertions, not verified current facts or permissions. This does not index old checkpoint-only history or provide semantic search.

210 guarded offline tests passed in 5.653 seconds: scope isolation, restart, SQL-like literal parameters, output bounds and a fake model receiving real archive results. A local read-only PDF search in the actual default archive returned three cited matches; report outputs/acceptance/archive-search-local.json. No API calls or downloads. Live hosted model tool choice remains pending; do not equate offline integration with all-provider acceptance.

Files: agent/chat_catalog.py, agent/conversation.py, agent/chat_runtime.py, agent/langgraph/langgraph_agent.py, tests/test_archive_search.py.

Restart the agent, then ask: Search this chat's archive for my earlier PDF report discussion and cite the chat and turn. That conversational request uses the configured LLM; archive lookup itself is local.


## User-controlled suggestions — 17 October 2026

Y for implementation and offline acceptance. SUGGEST MEMORY key = fact queues a proposal; SHOW SUGGESTIONS reviews pending candidates; ACCEPT MEMORY suggest-ID or REJECT MEMORY suggest-ID makes an explicit ID-bound decision. The model has a suggest_memory tool for requested proposals but no acceptance tool. Pending proposals are not saved facts and never appear in fact retrieval.

Acceptance inserts a new fact and marks the proposal accepted atomically. Existing keys are not overwritten: use explicit REMEMBER correction or reject. Accepted facts retain user_statement or assistant_report provenance and remain unverified. Repeated decisions do not replay writes; rejected proposals cannot later be accepted. FORGET removes associated suggestions and revisions; delete_user also clears suggestions. Archives/backups/provider records remain outside this deletion scope.

20 pending proposals maximum per user/space; values up to 2000 characters. Accepted/rejected proposal records persist until corresponding FORGET/delete_user. No expiry or automatic conflict inference is claimed. Commands work through the shared agent; no dedicated browser approval buttons were added.

214 guarded offline tests passed in 5.534 seconds. Actual command functions also passed propose/review/accept/show-memory/forget integration using temporary SQLite storage. No API calls, downloads or changes to existing user facts. Live model suggestion choice remains unverified. Files: agent/memory/long_term_memory.py, agent/langgraph/langgraph_agent.py, agent/conversation.py, tests/test_memory_suggestions.py. Restart clients to load changes.

Workstream 3 remains I: semantic retrieval and broader contradiction/staleness policy remain pending.


## Semantic retrieval and advisory conflict/age review — 17 October 2026

Y for implementation/offline integration, P for real local model acceptance. memory.semantic_search uses the existing MiniLM family through SentenceTransformer with local_files_only=True, trust_remote_code=False and CPU. No implicit model download/provider switch. search_memory adds optional mode=semantic; lexical remains the default and selected prompt memory still uses lexical search. The model object is cached; fact vectors are rebuilt from current scoped rows, so updates/deletions cannot leave a stale vector index.

Semantic lookup considers the newest 200 scoped facts, embeds at most 2000 characters per value, returns cosine-ranked results at score >=0.35, with limit/coverage metadata. Scores are relevance, not truth. Encoder selection is configurable via AI_MEMORY_EMBEDDING_MODEL; dependency/model absence fails explicitly. First model load can be slow and is not bounded by the existing hosted-request timeout.

Added review_memory: lexical or semantic candidates, age review with configurable request stale_days (default 90), source metadata and at most ten candidate pairs. Differing related values are flagged potential_conflict_requires_review, not asserted to be contradictory; project/source/time must be checked. Old storage timestamps trigger review, never deletion or automatic loss of verification. No automatic merge/correction/expiry is performed. REMEMBER/FORGET remain explicit controls.

220 guarded offline tests passed in 5.621 seconds. Tests cover scoped semantic ranking with injected vectors, fresh-value/delete handling, coverage limits, invalid vectors, age flags, equal-value handling and no mutation. The real cached MiniLM smoke check produced no result during prolonged loading and was deliberately interrupted to avoid wasting user time. outputs/acceptance/semantic-memory-local.json is P; no real semantic quality/latency pass is claimed. Hosted model review/tool-choice quality is also unverified.

Files: agent/memory/semantic_search.py, agent/memory/long_term_memory.py, agent/conversation.py, agent/langgraph/langgraph_agent.py, tests/test_semantic_memory.py, tests/test_memory_review.py.

Remaining: diagnose local embedding startup/measure a real semantic retrieval baseline; evaluate broader contradiction detection using representative same-topic/different-project cases. Workstream 3 remains I. These findings do not supersede the parked Workstream 2 summary blockers.


## Bounded retry and parking decision — 17 October 2026

One user-authorized retry used a local worker with a 90-second timeout, HF/Transformers offline mode and two CPU threads; no API calls or downloads. It finished in 43.69 seconds total (29.55 after imports). Paraphrase query How do I get to work? returned no fact for I travel to my office by train under the configured 0.35 threshold. Thus semantic retrieval acceptance is P; model loading itself now succeeded. Empty results alone are not strong scope-isolation evidence; earlier offline scope tests remain relevant.

The real embedding advisory review flagged the synthetic HTML/PDF report pair and left values unchanged. This passes that smoke case, not general contradiction accuracy across projects or timeframes. Report: outputs/acceptance/semantic-memory-bounded-retry.json.

Per the user's instruction to park and move on if this retry did not pass, Workstream 3 is now P overall: real semantic retrieval calibration/quality and broader contradiction acceptance are PARKED. Implementation and previously verified items retain Y. No further model retries now. Workstream 4 — Reliable knowledge and search — is the active next focus. Latest regression baseline remains 220 offline tests; this retry changed no runtime code or user facts.

## WS3 bounded memory-review evidence - 20 October 2026

Y for a reproduced shared-conversation defect and its fix. Six synthetic long facts produced an 8,012-character tool message cut mid-JSON; the advisory note was missing. agent/memory/evidence.py now bounds review_memory responses by omitting whole trailing facts and their unmatched candidate pairs, retaining complete values/metadata and explicit coverage warnings. Small responses keep their existing contract. An oversized envelope fails with a bounded structured error. The shared conversation applies this before tracking tool success/failure. No facts, revisions, verification labels or other tool outputs are rewritten.

The exact reproduction now delivers valid JSON of 7,915 characters with four complete facts, the review guidance and truncated=true. Stored facts are unchanged. All 89 focused offline checks pass in 4.82 seconds, including four new whole-record/metadata/pair/loop regressions, memory provenance/revisions/suggestions, existing conversation/grounding guards and package compatibility. Initial runner selection/import-path errors were corrected; they are retained in diagnostic logs and are not passing application results. No fresh full-suite release pass is claimed.

P for live contextual conflict quality. The first three Groq review cycles did not yield accepted evaluation records; the initial collector retained only generic exceptions, so their precise failure reason and semantic accuracy are not established. The fourth case stopped on HTTP 429 RATE_LIMIT. The configured Gemini fallback encountered a temporary 503 followed by TLS_CERTIFICATE failure on its bounded retry. No certificate checks were disabled, no further blocked requests were made and the saved default provider stayed unchanged. The evaluator now records safe error kinds and synthetic response diagnostics, with explicit array types in its output contract.

The eight-case evaluator fixture passed offline with scripted replies, real temporary SQLite reviews, scope canaries and database no-mutation checks. This validates the harness only, not live semantic quality. Cases cover unresolved equal-authority values, different projects/years/roles, explicit correction, equal values, storage age and instructions embedded in a saved value. Only the registered review_memory schema is exposed for focused quality evaluation; broad tool selection is outside that scope. Existing real embedding calibration and broader live contradiction acceptance remain P. No local model was loaded or downloaded.

Implementation: agent/memory/evidence.py and agent/runtime/conversation.py. Regressions extend tests/test_memory_review.py. The new acceptance runner is evaluations/memory_review_acceptance.py; no extra package or active top-level agent module was added. Evidence: outputs/acceptance/ws3-review-truncation-before.json, ws3-review-truncation-after.json, ws3-review-focused.json/.log, ws3-memory-review-groq-all.json, ws3-memory-review-gemini-same_scope_conflict.json and ws3-memory-review-offline-all.json. Backups are under outputs/ws3-review-before-20261020. Temporary stores were removed; user facts, chats, receipts and .env were not changed. Restart console/Streamlit processes to load the shared-conversation fix.


## Partial live conflict review on 21 October 2026

A separate live synthetic Groq memory review passed three cases: equal-authority conflict with both values and clarification, different projects, and different years. The fourth case hit HTTP 429 and the run stopped; five of eight cases remain unfinished. The evaluator previously rejected a complete JSON Markdown code block. It now accepts only a single complete JSON fence or plain JSON for semantic scoring and records plain-JSON request compliance separately. The three semantic passes used fences and do not establish plain-JSON compliance. Seven positive/negative parser checks and the eight scripted offline fixtures passed; these validate the harness, not additional live model cases. No private user histories or real project facts were sent, and temporary databases were unchanged and removed. Evidence: outputs/acceptance/ws3-memory-review-groq-all.json and ws8-memory-quality-probe-20261021. Groq quota remains the observed live-evaluation blocker; no persistent provider switch or blocked fallback retry was made.

The contradiction gate remains P with three sampled live passes and five unfinished cases. Real embedding calibration is still P; the fresh optional profile also exposed a separately bounded sentence-transformers import timeout. No application memory policy changed in this follow-up.

## OpenRouter fallback and cached semantic baseline on 21 October 2026

OpenRouter live connectivity is Y for synthetic memory review. Public endpoint inspection reported zero recent uptime for the saved nvidia/nemotron-3-super-120b-a12b:free endpoint, while minimax/minimax-m3.1-flash:free and nvidia/nemotron-3.5-lightning:free had healthy endpoints at inspection time. Tests used process-only model and matching budget overrides; .env, its API keys and the saved provider choice were unchanged. The first override correctly stopped at the model/budget mismatch preflight before HTTP; historical model_calls/hosted_requests fields are adapter-invocation counters, not exact transport counts. Future reports distinguish these explicitly.

The five unfinished cases obtained sampled passes across two OpenRouter models. A full eight-case run on nvidia/nemotron-3.5-lightning:free with a 4096-token budget passed 7/8 in 89.66 seconds; all replies were plain JSON. Its role-distinction case unnecessarily requested confirmation despite the role difference being explicit. Shared conversational guidance now explains that candidate flags are advisory, compares subject/project/time/role and avoids inventing overlaps or reconfirming explicit distinctions. No expected test answers, thresholds or tool permissions changed. All 61 focused offline checks passed, followed by 246 selected checks in a fresh RAG environment.

Live verification of the guidance remains P: the next run completed seven cases, with five passes, one incorrect exact source key (a constructed namespace/key rather than the returned key), and an OpenRouter HTTP 429 QUOTA_EXHAUSTED during the role case. The eighth case did not run. Do not claim the role fix is live accepted or combine separate model/prompt runs into a single 8/8 pass. No further hosted requests were made after quota exhaustion. The earlier 1024-token attempt also reached OUTPUT_LIMIT; the evaluator now has --max-tokens with the same default and unchanged three-call-per-case cap. The tested endpoint publishes a 65536-token maximum output; 4096 was used for this finite evaluation. Provider availability and quotas can change.

Y for a working-environment cached real-encoder baseline: sentence-transformers 6.1.0 imported in 40.25 seconds with process-only single-thread settings; the whole import diagnostic took 42.45 seconds. Then eight fixed semantic tests passed in 21.52 seconds total: four paraphrase top-one matches, two unrelated queries with no results, correction and deletion. Real MiniLM and SQLite scope isolation were used with the unchanged 0.35 threshold; no model download or provider request occurred. This is a small sampled baseline, not broad-domain precision/recall or a causal proof that thread limits alone fixed loading. File/bytecode cache warming and differing dependency environments were not controlled separately.

P for cold fresh-environment ML loading. The further fresh RAG run installed in 49.18 seconds, passed pip check, both entry points, eleven optional/API imports, synthetic parser/index operations, all 246 selected tests (zero failures/errors) and Streamlit initial rendering. Its separately bounded sentence_transformers child still timed out at 60.32 seconds despite process-only thread limits. Total rehearsal 180.34 seconds; report intentionally remains pending because this optional runtime check is incomplete. Do not substitute the working-environment sample for fresh-runtime acceptance. All owned fixtures/processes were removed and working packages/provider settings stayed unchanged. Future optional-import timeouts now retain stack snapshots; that instrumentation has syntax validation but has not triggered another cold-start attempt.

Existing evaluators remain under evaluations; new evaluations/semantic_memory_local.py is inside that existing package and owns its synthetic fixture parent for timeout cleanup. No active flat agent module was added. Application change: generic guidance in agent/runtime/conversation.py only. Backups, reports and logs are under outputs/acceptance/ws8-openrouter-memory-20261021, ws8-ml-import-trace-20261021, ws8-semantic-memory-20261021 and ws8-rag-thread-limited-20261021. Workstream 8 remains I; broader WS2 summaries, WS3 calibration/live review, WS4 hybrid relevance, full learning-profile setup and release scope remain pending. Word synchronization is not claimed.


## WS3 exact memory keys versus provenance — 22 October 2026

One finite Groq synthetic review run took 14.01s. Same-scope conflict and different-timeframe distinction passed. The different-project case correctly identified separate projects/formats but returned fixture#report_atlas/fixture#report_boreal provenance references in the sources field instead of the requested exact saved fact keys. The fourth case stopped on HTTP 429 RATE_LIMIT; four later cases did not run. Temporary fact databases were unchanged and removed. No further hosted request followed quota exhaustion. Do not combine separate old/new runs into a complete acceptance pass.

Y for a focused implementation fix: agent/memory/evidence.py distinguishes exact saved keys from provenance for explicitly requested exact-key responses containing a structured sources field. agent/runtime/conversation.py records only keys in successful memory-review evidence actually delivered to the model, gives one changed correction for unknown/substituted keys, and reports incomplete after repeated failure. It does not strip prefixes, invent a key mapping, rewrite facts or weaken evaluation expectations. Ordinary prose, non-key provenance requests, unrelated JSON and absent memory evidence retain their prior behavior. This is an identifier-membership check, not proof that a cited fact supports the answer, that every relevant key was listed, or that natural-language factual reasoning is correct.

145 affected offline checks passed in 10.88s across memory, shared conversation, provider fallback, Continue and package compatibility. Six new regressions exercise valid keys/fences, substituted provenance/namespaced IDs, scope exclusions, successful bounded correction without tool replay, repeated-failure refusal and unchanged ordinary provenance references. The existing acceptance evaluator gained --output to preserve older reports. All new code reused appropriate existing packages; no flat agent helper, dependency, .env/provider change or user-memory mutation was added. Source backups and exact evidence: outputs/acceptance/ws3-review-20261022. Live post-fix acceptance remains P after quota exhaustion, so overall WS3 remains P.

WS2 Ollama readiness was checked read-only: local server/model are available, but no model is loaded. Saved context is 4096. The earlier expanded-8192 fixture took 275.79s and failed source attribution. No fresh slow generation or model download was attempted; changed-path Ollama attribution/context-fit remains parked. Other completed WS2/WS3 results retain their stated scope. Restart the actual console and Streamlit server processes to load this shared backend fix. Word synchronization is separate.


## WS3 post-fix hosted acceptance checkpoint - 23 October 2026

Y for two measured post-fix Groq synthetic cases: same-scope equal-authority disagreement required clarification, and different projects were correctly kept separate with the exact returned saved keys report_atlas/report_boreal. Each passed all nine checks, including source keys, scoped evidence, completed result and unchanged temporary fact database. This provides live evidence for the previously reproduced exact-key case; it is not full eight-case or all-provider acceptance. Existing implementation/offline Y evidence remains unchanged and was not repeated.

P for the complete finite eight-case quality gate. Three independent named-provider attempts used the same evaluator with fallback disabled and synthetic temporary SQLite facts only. OpenRouter (4096 output budget) passed same_scope_conflict, then stopped at different_projects with INVALID_RESPONSE after 30.62s. Groq (2048) passed same_scope_conflict and different_projects, then stopped at different_timeframes with HTTP 429 RATE_LIMIT after 5.65s. Gemini (4096) timed out on its first case with RESPONSE_TIMEOUT, attempts 1, after 1000.31s. No results from separate providers/runs are combined into a complete pass. The output budgets were evaluator-only; .env/provider settings were not edited. No historical user memory was sent.

The Gemini controller's intended 150-second process wait and 30-second provider timeout did not produce a strict elapsed bound: it recorded 1001.53s before the owned child had stopped. Its returned timeout flag was false because the child had completed when observed, while provider diagnostics recorded a response timeout. The observed elapsed time takes precedence over any intended-bound claim. No further generation or unchanged retry followed this failure. The controller and all evaluator temporary fact directories report stopped/removed. No source/application code was changed to hide the failures or weaken expected answers.

Broader semantic calibration and the previously bounded fresh-environment ML import remain parked; this checkpoint did not retry the unchanged slow import or repeat the cached 8/8 sample. Archived-tool choice and suggestion selection retain their earlier limited/offline scope. Remaining next prerequisite for hosted review: one provider must have capacity/connectivity and return valid output for a complete coherent eight-case run. Repeating exhausted or timed-out calls immediately is not a solution. A provider-capacity problem does not invalidate the independently passing storage, provenance, corrections, review guards and scope tests.

Overall WS3 stays P. Evidence: outputs/acceptance/ws3-completion-20261023/summary.json, the three separate *-live.json reports and controller/log files. No application, dependency, .env, saved fact, user database, commit/push or Word synchronization changed. Documentation was updated in place; no new application Python module was created.


## WS3 expanded local semantic calibration - 23 October 2026

P for actual semantic acceptance; the new run completed zero of 16 planned cases because an import failed before the first encoder result. This is not 0/16 semantic failures and does not invalidate the historical cached 8/8 baseline. A separate bounded import-only diagnostic identified the exact cause: ImportError: DLL load failed while importing _traversal: An Application Control policy has blocked this file. The failing chain is sentence-transformers -> scikit-learn -> scipy.stats -> scipy.sparse.csgraph._traversal. This is a native-library execution-policy blocker, not a hosted quota error, a measured matching-quality failure or a demonstrated threshold defect. The calibration exited in 38.26s; the import-only diagnostic exited in 8.81s. Both owned child processes stopped normally; temporary facts were removed and saved .env stayed unchanged.

Y for adding a new finite calibration harness under the existing evaluations package and its fail-closed metric checks under tests. evaluations/semantic_memory_calibration.py declares 16 expectations before encoding: six new clear paraphrases requiring correct top-one retrieval; four unrelated queries requiring abstention; four project/year/report-role candidates requiring recall in the top three; one corrected-current-value check and one deleted-key check. Reads must not mutate facts or expose other user/namespace canaries. The unchanged 0.35 threshold and cached MiniLM configuration are preserved. Context candidate retrieval is not asserted to establish truth, resolve contradictions or select a final answer. The original eight-case evaluator/baseline remains untouched.

Seven focused offline tests passed in 0.20s, including three new evaluator checks that reject a wrong top-ranked answer, an unrelated-query false positive, or a correct-looking answer accompanied by foreign scope/mutation. They also distinguish contextual recall-at-three from strict top-one scoring. Existing injected-vector scope/update/delete/coverage checks passed. These tests do not load the real encoder and are not real-ML acceptance. The new evaluator now logs local exception tracebacks for future diagnostics; that diagnostic-only adjustment was syntax-checked without another blocked ML attempt.

No application implementation, dependency installation, matching threshold, user fact, model download, provider setting, device security policy or user database was changed. An administrator-approved SciPy native component/build or an approved runtime environment is required before this real-encoder check can proceed. No relocation, policy bypass or automatic download/reinstall was attempted. The separate fresh-install import timeout was not repeated or reclassified by this working-environment result. Hosted eight-case review remains independently P after the provider failures recorded above.

Overall WS3 stays P for two explicit gates: complete hosted review and expanded local semantic quality. Evidence: outputs/acceptance/ws3-semantic-calibration-20261023/{summary.json,result.json,worker-result.json,import-diagnostic.log,offline-tests.json}. New code is in the appropriate existing evaluations/tests packages. No commit/push or Word synchronization occurred.


## Memory role-clarification correction and quota checkpoint - 23 October 2026

Reproduced one remaining answer-quality defect in a complete OpenRouter run: seven of eight synthetic cases passed; different_roles correctly named both roles but unnecessarily asked the user to reconfirm whether they were separate. The system guidance already respected explicit roles, while the review_memory description/result note still directed unconditional clarification. Updated only those conflicting tool instructions in agent/memory/long_term_memory.py and agent/runtime/conversation.py. Candidate detection, fact storage, retrieval, permissions, the evaluator and expected answers were unchanged; no case-specific answer was added.

Y for the changed role case: one fresh OpenRouter check passed all nine expectations, returned status=separate and needs_clarification=false, retained exact source keys, excluded foreign scopes and left its temporary fact database unchanged. All 85 focused memory/conversation offline tests pass. This is finite sampled behavior, not universal contradiction accuracy or all-provider acceptance.

P for full eight-case post-fix acceptance. A separate coherent OpenRouter run passed same_scope_conflict, different_projects and different_timeframes, then stopped at corrected_current on HTTP 429 QUOTA_EXHAUSTED. Its controller finished in 50.81s; no exhausted-provider retry followed. The earlier seven-pass run and separate role check are not combined into a post-fix 8/8 result. Provider quota is now the observed gate for this attempt. Expanded local semantic calibration remains separately blocked by the previously diagnosed Windows native-library policy; it was not retried.

Existing credentials were used only for synthetic temporary facts. Process-only timeout/output controls applied; fallback was disabled to measure a single provider. Saved .env hashes matched before/after, all temporary runtime/fact directories were removed and owned children stopped. User memories, conversations, indexes, dependency installations and the running user server were untouched. No commit/push, security-policy change or Word synchronization occurred. Evidence: outputs/acceptance/ws3-review-followup-20261023-035750/{openrouter.json,role-after.json,all-after.json,all-after-controller.json,focused-tests.json}.

Verification limit: the subsequent full offline run was stopped at its 240-second process deadline. Its progress log records 681 completed tests (681 passed), then interruption during test_use_case_audit.AuditUiTests.test_failed_download_revalidation_clears_previous_snapshot. No fresh complete-suite pass is claimed for this guidance edit. The independently completed 85 focused tests remain passing; the earlier 706-test full pass preceded this edit. See outputs/acceptance/ws3-review-followup-20261023-035750/full-offline.json and final-summary.json. Do not retry an unchanged slow broad run or exhausted provider merely to change a status.


## Complete hosted memory review accepted on Gemini - 23 October 2026

Y for the finite post-fix eight-case hosted review. Gemini gemini-3.1-flash-lite completed all eight cases in one coherent evaluator run (90.06s; controller 90.60s). Every case passed all nine declared checks: real review tool use, expected status/values/exact source keys, clarification decision, explanation presence, exclusion of other scopes, completed outcome and unchanged database. Every response used plain JSON. The actual synthetic assessments were also inspected: unresolved equal-authority conflict asks for clarification; different projects/years/roles stay separate; explicit correction uses the current value; equal values agree; storage age does not authorize deletion; instructions embedded in a saved value remain data. This finite pass does not establish universal answer accuracy, broad tool selection, embeddings or all-provider acceptance.

The authorized sequence followed OpenRouter -> Groq -> Gemini, starting each provider with a fresh complete eight-case evaluation and fallback disabled within that evaluator. OpenRouter stopped on its first case with HTTP 429 QUOTA_EXHAUSTED; Groq passed two cases then stopped on HTTP 429 RATE_LIMIT; Gemini independently passed all eight. No provider results were pooled. The complete sequence finished in 99.76s within the 180-second test budget. No exhausted-provider retries followed.

No application, evaluator, expected-answer, model-selection or saved configuration edit was needed for this acceptance. The earlier role-guidance correction was retained. All facts were synthetic in temporary SQLite stores, saved .env hashes matched, all owned children stopped, and temporary fact/runtime directories were removed. User facts, histories, indexes and the running user server were untouched. No new Python module, dependency install, commit/push or Word synchronization occurred. No broad offline suite was repeated because this turn changed no application code; the preceding 85 focused passes and 240-second broad-run interruption remain separate historical evidence.

Overall WS3 remains P solely for expanded local semantic calibration under the existing Windows Application Control block. Do not retry that unchanged native-library import or reopen the accepted hosted gate merely because the semantic gate is parked. This milestone supersedes earlier full-hosted-review P statements; it does not erase their provider-specific failure evidence. Evidence: outputs/acceptance/ws3-bounded-review-20261023-042338/{gemini.json,summary.json,openrouter.json,groq.json}.
