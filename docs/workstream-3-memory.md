# Workstream 3 — Useful long-term memory

Status: I. First milestone: Y for provenance metadata, additive migration and integration. This is not completion of conflict resolution, semantic retrieval or general archived-chat search.

## Implemented

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

## Next

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
