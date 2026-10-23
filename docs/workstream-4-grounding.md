# Workstream 4 — Reliable knowledge and search

## WS4 bounded negative-review routing check - 23 October 2026

**Y - conservative review routing; P - broader factual/source quality PARKED after one changed-path live check.** A valid review marked supported while listing concrete issues is now treated as revise, with every issue preserved and no asserted supported source. The existing shared answer flow gets one revision and a new review; repeated concerns still withhold the answer. Invalid negative-review format corrections still cannot erase earlier concerns. No action permissions, provider settings or module layout changed.

Three regressions reproduced the routing failure before the fix; all **287 affected offline tests pass** afterward. One isolated Gemini run finished in **30.08 seconds** (30.35 seconds including control/cleanup), eight model calls, and exercised concern-to-answer revision without a format-retry dead end. Manual review did **not** accept overall quality: the omitted-extends rule was overbroad and the retrieved section did not ground the example's method-dispatch/field-hiding claims. No Java was compiled or executed. No second live attempt is made. Hybrid remains policy-blocked; Ollama remains user-parked.

Evidence: `outputs/acceptance/ws4-negative-review-routing-20261023-123215/summary.json`, `after.json`, `live/live.json` and `manual-audit.json`. WS1-WS8 remains **7 P checklist rows and 1 X**. This is focused compatibility coverage, not a new full-suite or full-release pass.

Status P - BLOCKED / QUALITY PARKED. Hybrid/semantic validation is blocked by native-runtime policy. Factual/source-coverage acceptance remains an unfinished code/quality task, not an established external-only blocker. Exact passage selection and the concern-preserving format-correction guard pass 285 affected tests while preserving legacy replies and strict provenance checks. One live ID-format workflow completed, but manual source/factual review failed; the final local guard blocks its captured approval sequence. Hybrid/semantic quality and actual verified-answer acceptance remain pending.

## Web reference guard

The shared conversational loop registers only HTTP(S) URLs returned in successful web_search results and present in the tool text actually supplied to the model. URLs containing credentials are not registered. Prose citations after web search must match registered URLs; Markdown links or bare URLs are accepted. Example URLs inside fenced code blocks are ignored. Known fabricated internal markers such as commentary:functions.web_search references are rejected even without a web call.

One changed answer-correction request is allowed inside the existing six-round budget. Repeated invalid citations produce a static incomplete result without exposing the invalid draft. If a required web route retrieves no usable links, it returns incomplete rather than accepting a current-information answer. No additional execution permission is granted, and no provider settings are changed.

## Evidence and limits

225 guarded offline tests passed in 4.459 seconds. Tests verify unseen links, internal markers, successful correction, bounded repeated failure, visible-only URL registration and failed-search handling. No live provider/search calls, downloads or private-history exports were made.

This verifies reference traceability, not factual entailment, publisher authority or full-page contents. Exact URL matching can reject equivalent differently formatted links; a correction can reuse the returned spelling. An answer can still contain unsupported claims beside a valid citation. General answers without web searches are not forced to browse by this guard. Local file/document/table/archive citation validation and full-page retrieval remain pending. Generic tool-result truncation still has limitations and is not fixed by this change.

Files: agent/citation_guard.py, agent/conversation.py, tests/test_citation_guard.py. Restart console/Streamlit to load the change.

## Next

Add bounded full-page evidence retrieval with safe URL/network handling, validate local document source references, then test existing indexed retrieval quality and a mixed memory/document/web task. Keep Workstream 2 and 3 parked acceptance gaps parked; framework expansion remains deferred.


## Public-page text retrieval — 17 October 2026

Y for implementation and offline integration. fetch_web_page accepts only a URL already returned by visible web search evidence. It reads static HTML/plain text, removes script/style/SVG text, returns the title, final URL and a bounded excerpt. Redirected final URLs enter the citation registry only after a successful read. No JavaScript execution, cookies, credentials, uploads or local source access.

Network controls: HTTP/HTTPS standard ports only; reject URL credentials/control characters; resolve and validate all DNS answers as public addresses; pin the actual connection to a validated address while retaining the hostname for TLS verification. Each redirect is revalidated, with at most two redirects and no HTTPS downgrade. Compressed or nontext responses are declined. Response bytes cap 512 KiB and output text 4500 characters; truncation is explicit. Direct connections do not use environment proxies. Connect/read sockets have at most 10-second timeouts and the body loop checks a 30-second budget. OS DNS resolution/header processing are not a strict overall wall-clock deadline; a full end-to-end timeout remains a known limitation.

232 guarded offline tests passed in 11.691 seconds. Tests cover pinned targets, private/mixed DNS rejection, private redirects, credentials/ports, downgrade, compression, byte/text bounds, safe network errors, script removal and the search/read/final-citation loop. No live network or hosted model calls were made. Full-page static text may contain navigation or omit sections after truncation; it does not guarantee factual entailment or browser-rendered accuracy.

Files: agent/web_pages.py, agent/conversation.py, tests/test_web_pages.py. Live public-page compatibility and hosted-model use remain pending. Next: indexed-document source validation and retrieval quality, then mixed-source acceptance. Workstream 4 remains I.


## Indexed-document references and measured keyword baseline — 17 October 2026

Y for structured source-reference implementation/offline integration. execute_search_documents preserves legacy text and default hybrid retrieval, with optional structured=True and retrieval_mode=keyword. The shared agent now requests structured sources; mode=keyword is explicit, not a hidden replacement for hybrid. Keyword resources load separately without embeddings/reranker. Zero/nonpositive keyword scores are omitted and index/chunk count mismatch fails explicitly.

Each selected indexed excerpt has a stable DOC-content-hash reference, stored source name/location, location kind (PDF page, CSV row, other section), retrieval method, at most 1800 text characters and truncation flag. Metadata describes the index, not a reread of the current source file. The conversation registers only refs whose nonempty excerpt is visible in tool output. Invented or missing document references get one answer correction shared with the citation guard. Empty structured required-document evidence returns incomplete. Legacy string-producing adapters remain compatible but do not receive this structured-ID guarantee.

237 guarded offline tests passed in 39.902 seconds. Tests cover stable references, visible evidence, correction, empty evidence and keyword retrieval preserving the old text format without loading embeddings.

Actual project-generated keyword artifacts were checked against the existing eight-question evaluation set: 1/8 source/location/expected-keyword cases passed in 5.15 seconds. Report outputs/acceptance/document-keyword-baseline.json. Resume pages 1 and 2 are indexed; NTT DATA and Altimetrik queries rank cover letters/other documents above the expected resume. This suggests ranking/tokenization relevance issues, not simply a missing resume. The test is keyword-only; it does not establish hybrid/answer quality. No API calls, downloads or private data exports.

P remains for measured retrieval quality, source freshness/absolute path resolution, claim entailment and mixed-source acceptance. Next: inspect keyword tokenization/ranking against the existing corpus and improve the repeatable baseline without hardcoding evaluation answers. Files: rag/retrieval.py, agent/citation_guard.py, agent/conversation.py, agent/langgraph/langgraph_agent.py, tests/test_document_sources.py. Restart clients to load source-reference support.


## Keyword ranking improvement — 17 October 2026

Y for the measured keyword baseline scope. Normalized keyword mode now uses Unicode word tokenization, possessive/punctuation normalization, common function-word filtering and source-name terms. A BM25 index is rebuilt in memory from trusted existing chunks with the same tokenizer used for queries; disk indexes and legacy hybrid defaults are not replaced. Structured excerpts include at most two preceding/two following chunks from the same indexed file/page, still capped at 1800 characters. Neighbor ordering is center-first then distance order, not continuous source-page reading.

Result: baseline increased from 1/8 to 6/8 with original labels, or 8/8 with independently audited page locations. Original evaluation_questions.json remains unchanged. Cases 6 and 7 incorrectly expect page 1; the indexed corpus and an actual pypdf reread of resume page 2 confirm the SanDisk/iDisha date/location evidence there. Reports outputs/acceptance/document-keyword-normalized.json and document-label-page-audit.json. Benchmark took 2.38 seconds, no embeddings, reranker, API calls or downloads. Reproduce with python evaluations/document_keyword_acceptance.py (the separate PDF page-audit report is retained).

240 guarded offline tests passed in 31.400 seconds, including generic possessive/punctuation handling, source-name search and same-page/source neighbor boundaries. Files: rag/retrieval.py, evaluations/document_keyword_acceptance.py, tests/test_keyword_ranking.py, tests/test_document_sources.py.

This eight-case source/location/keyword result does not verify answer entailment, broad corpus quality, novel queries or hybrid-model behavior. Keyword mode must be requested explicitly; default hybrid behavior remains. Workstream 4 remains I. Next: mixed local-memory/indexed-document/web grounding and live model citation acceptance.


## Mixed-source grounding started — 17 October 2026

241 guarded offline tests passed in 35.648 seconds. New integration test uses scoped real temporary SQLite memory, a temporary document and synthetic indexed/web/page responses, validating a combined answer with document ID and web URL while excluding another user's fact.

Live Groq model check used synthetic data/tool fixtures only. It successfully selected search_memory, search_documents, web_search and fetch_web_page, then HTTP 429 QUOTA_EXHAUSTED blocked final answer generation. No automatic retry or provider switch. This is P for live final-answer/citation acceptance; tool-selection execution alone does not complete the gate. Report outputs/acceptance/mixed-grounding-live.json; runner evaluations/mixed_grounding_live.py. Fixtures are not real web search/page evidence and no private documents were sent.

Word roadmap snapshot updated in docs/agentic-ai-roadmap.docx with current overview/checklists/flow through the 241-test milestone. Workstream 4 remains I; actual mixed-source factual quality, live page compatibility and final citation acceptance remain pending. W2/W3 parked gaps remain.


## Word roadmap delivery

Reviewed all 14 pages of the corrected Word snapshot via page images from the installed Word PDF export. Latest artifact: docs\agentic-ai-roadmap-updated.docx. Original replacement remains blocked by a Word file lock; final reviewed copy is saved separately. No intermediate PDF/images are deliverables. Mixed-source final-answer acceptance remains P due Groq quota.


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


## WS4 execution-evidence presentation guard — 22 October 2026

Y for a focused fix to one reproduced defect in the saved Java response: an Actual Execution section presented a future prediction, although the read-only answer flow had not executed code. The captured supplied text now triggers a local issue before model source review. No generated example was run. This does not fix or establish acceptance of the separate inheritance-rule, source-version or factual-entailment errors in that response.

agent/policies/answer_quality.py now detects narrow positive code-run claims and undisclosed actual/observed-result headings independently of a model's supported verdict. The existing shared conversation applies one correction using the shared syntax/quality correction ceiling, then withholds a repeated unsupported draft with incomplete status. Direct technical review also returns revise without a model call for this defect. Predictions, instructions, properly fenced/quoted text, ordinary non-code conversation, explicit not-run disclosure and clearly attributed user-supplied logs remain valid. The guard never executes code, invents execution evidence or rewrites reported results. It is a bounded English presentation check, not universal semantic detection. Explicit attribution does not independently authenticate user-provided logs.

234 affected offline checks passed with external network blocked, zero failures/errors (4.69s including test loading). Eleven new regressions cover the captured presentation pattern, positive run claims, expected output, quotations/code, supplied logs, mixed user/assistant attribution, normal non-code language, bounded shared correction/refusal and reviewer bypass prevention. The initial new test fixture omitted its source-tool attributes; corrected in the test only. A later regression exposed an unsupported assistant-run claim following an attributed user result; fixed before the final passing run. Initial failures remain as evidence, not passing results. No hosted request followed the known quota blocker; no full factual-quality or browser/release pass is claimed.

Files reuse existing policies/runtime/test packages. No dependency, UI layout, provider/model/fallback order, .env, user checkpoint, chat, fact or approval record was changed. Source backups, diffs, saved-response digest and regression reports: outputs/acceptance/ws4-execution-evidence-20261022. Restart console and the actual Streamlit server process to load the shared runtime fix. Overall WS4 remains P for factual/source entailment, version-specific coverage and broader retrieval quality. Word synchronization is separate.


## WS4 bounded source-review evidence anchors — 22 October 2026

Y for strengthening the existing registered technical review, rather than enabling the parked source-first workflow or adding another review round. A supported verdict now needs bounded evidence anchors containing an exact draft claim, a source URL and a continuous 20-400-character quote from the supplied excerpt for that URL. Whitespace normalization is allowed; changed wording/case is not. At most eight anchors are accepted, at least one per cited source. Local validation rejects missing, invented, mismatched, duplicated or malformed anchors. A quote from another page cannot establish provenance for the cited page. One changed correction is shared with the existing format/provider-output correction ceiling. Unresolved format problems retain ANSWER_REVIEW_FORMAT; quota/auth behavior is unchanged. Valid insufficient-evidence/revise verdicts may provide empty anchors and must retain concrete issues.

The reviewer is instructed to assess important-rule coverage, exception/universal statements and version scope. Deterministic checks establish provenance/membership only: quote existence does not prove semantic support, publisher authority, version applicability or coverage of every important claim. Those assessments remain model-dependent and P for broad quality. The existing public caller contract remains status/issues/source_urls; anchors are validated inside the review and do not change stored chat/summary/memory schemas. General chat, actions, Jira, summary generation, Continue, source-first enablement, provider ordering and saved output budgets are unchanged. New code reused agent/runtime/answer_review.py and the existing tests; no new flat agent helper or dependency was added.

245 affected offline tests passed in 11.42s with external network blocked, including eleven new methods for anchor validation, bounded correction, native/JSON compatibility and the actual shared search/read/review contract. The initial case-sensitive quote test mutated a Python object after serializing its mock response; correcting the fixture resolved that test failure without relaxing validation. Initial evidence remains targeted.log; final evidence is targeted-final.log and regressions.json/log.

Three bounded live Groq synthetic checks each completed in one HTTP 200 request: a supported fictional rule at evaluator-only 1536 tokens (2.05s), a directly contradictory fictional draft rejected as revise (1.86s), and a supported fictional rule with no output override using the actual unchanged 1024-token default (1.43s). No real web retrieval or private context was part of these fixtures. No broad actual-Java retest, model pooling, long-response-budget acceptance or all-provider pass is implied. No generated code was compiled/executed. Evidence, source backups and exact diffs: outputs/acceptance/ws4-review-evidence-20261022/summary.json. Overall WS4 remains P for real-source factual/version review and broader retrieval quality. Restart console and the actual Streamlit server process to load this shared backend change. Word synchronization is separate.


## WS4 original Java request retest — 22 October 2026

P — one bounded retest of the exact original public Java 17 question stopped after 6.95s on Groq HTTP 429 RATE_LIMIT, attempts 1 for the terminal request. Real web_search completed and fetch_web_page was called for Oracle's legacy subclass tutorial. The report does not retain that reader's returned excerpt, so it does not independently establish a successful full-page read. The next adapter invocation encountered native TOOL_OUTPUT, entered the existing changed JSON encoding path, and that attempt hit the quota limit. The source-review stage was not reached; no completed explanation was published. Do not count the run as review/factual acceptance, claim the new evidence contract was exercised here, or attribute the result solely to a production code regression. Three adapter invocations are recorded; they are not an instrumented count of HTTP requests.

No further request followed the quota failure and no other provider was retried. The existing evaluator gained --primary-only, --single-provider and --max-model-calls so this check could stop without spending calls on the topic-list follow-up or the known fallback chain. This was a deliberately single-provider diagnostic with unchanged output budgets, not acceptance of the normal configured failover chain. Only the public question was sent; no user checkpoint, memory, uploaded file or project source was read/sent. No generated code was compiled/executed. Application code, .env and saved chats/facts/settings were unchanged. The previous 245 offline checks and three scoped Groq synthetic review passes retain their independent scope; unchanged tests were not repeated.

Evidence: outputs/acceptance/ws4-real-java-20261022/summary.json, live.json and live.log. Overall WS4 stays P; keep this live gate parked until provider capacity is available. No more unchanged broad-question retries. Independent WS8 clean-install/data-root work can proceed; optional slow ML loading remains its own parked item. Word synchronization is separate.


## WS4 extended local keyword relevance acceptance - 23 October 2026

Y for 18 new finite keyword cases against the current local corpus, without rerunning the earlier eight-query resume benchmark. Sixteen positive cases cover dependency versions/runtime scope in TXT, eight course-topic locations in DOCX, and four distinct CSV record locations. Two out-of-corpus technical keyword queries returned no candidates. All 18 passed in 0.34s. Expectations were declared before retrieval and independently checked against current source-file text/location; no label was inferred or adjusted from retrieved results. Original source and index hashes matched before/after. Every positive case returned the expected source/location and requested visible text fragments with correctly formed structured DOC references.

This is candidate-source coverage within the existing returned result window, not certification that every candidate is relevant. Additional unrelated documents sometimes appear among lower-ranked results. Matching multiple fragments across returned excerpts from the same source/location does not prove a generated claim, semantic paraphrase, global precision/recall, official-source authority or version-specific Java correctness. The course outline was tested as a local document, not promoted to an authoritative Java specification. Empty results on two absent-keyword queries do not establish general semantic abstention.

Y for 13 focused offline tests in 0.32s, including three new scoring checks that reject correct-looking fragments from a different source/page, missing visible fragments, malformed references, or nonempty candidates in an absent-keyword case. Existing document-citation and source-audit regressions also pass. These are targeted checks, not a new full-project suite. No application defect was reproduced, so production retrieval/ranking code, thresholds, models, provider settings and indexes were not changed.

Reusable code belongs to the existing evaluations package: evaluations/document_relevance_acceptance.py. Tests belong to tests/test_document_relevance_acceptance.py. Corpus-specific queries/expected fragments are stored only in the ignored local acceptance folder, not in the reusable Python module. The evaluator takes explicit --cases and --output arguments, reads bounded source files, blocks external network during keyword search and records no query/excerpt text in its results. No embedding model, native blocked SciPy component or hosted API was loaded/called.

Overall WS4 remains P for two separate wider gates: hybrid/semantic retrieval quality, and actual source-verified answer entailment/version accuracy. The former needs an approved embedding runtime following the WS3 Application Control diagnosis; it was not retried. The existing public Java acceptance was not repeated under the unchanged hosted-capacity failures observed during WS3. This local pass does not close those gates. Evidence: outputs/acceptance/ws4-relevance-20261023/{summary.json,before.json,offline-tests.json,cases.json}. No user file modification, dependency install, commit/push, new roadmap document or Word synchronization occurred.


## Original Java 17 Gemini check and bold execution-heading fix - 23 October 2026

P for the original public Java 17 explanation. One explicitly single-provider Gemini run finished in 28.23s (28.93s controller), with six model-adapter invocations. Actual public search ran and an Oracle Java 17 JLS 8.1.4 excerpt was supplied to the source reviewer. Both review replies requested revise but populated claim anchors with source text absent from the draft. Local replay of the exact validator reports: Claim must be an exact span of the draft. After one permitted format correction, the existing ANSWER_REVIEW_FORMAT error stopped publication. This is not a quota/connection failure or proof that the entire retrieved section supports all generated inheritance rules. No completed source-verified explanation is accepted, and the validator was not loosened.

Y for a separate narrow defect revealed in that unpublished draft: **Actual Execution:** used a colon inside bold markup and escaped the existing heading detector. The draft described predicted output as confirmed execution despite this read-only flow having no execution evidence. The existing answer-quality policy now recognizes colons inside or outside bold headings. Proper expected-output instructions, explicit not-run disclosures, attributed user results, quoted data and the bounded one-correction/withhold behavior remain covered by existing tests.

Two new regressions in tests/test_answer_quality.py reproduced the issue before editing (four failed formatting subcases plus a failed shared-flow check). After the one-line policy adjustment, all 175 affected answer-quality, source-review, citation, conversation, source-audit and continuation tests pass, zero failures/errors, with external network blocked and temporary state. Local replay of the captured public draft now returns revise before any reviewer/provider call. This is local guard acceptance, not a second live Java pass. No generated code was compiled or executed. The source-anchor validator, review schema and expected answers are unchanged. No unnecessary broad suite or provider retry followed.

Production changes remain in the existing agent/policies package; regression additions remain in the existing tests module. Public-only evaluation used an empty synthetic project interface and isolated runtime home; no saved chats, facts or project source was sent. Saved settings hashes matched, owned test children stopped and temporary directories were removed. User server/dependencies/stores were untouched. No commit/push or Word synchronization occurred.

Overall WS4 remains P for broader hybrid/semantic relevance and source-verified factual/version quality. The previously diagnosed Windows native-library block was not retried. Next source-quality prerequisite is a valid complete review tied to actual draft spans and retrieved excerpts; provider reachability alone is insufficient. Evidence: outputs/acceptance/ws4-gemini-public-20261023-043042/{controller.json,live.json,local-diagnosis.json,guard-before.log,guard-after.json,guard-after.log}. Earlier milestone evidence remains historical and is not overwritten.


## Reviewer field guidance and precise correction feedback - 23 October 2026

Y for implementation/offline behavior. The existing agent/runtime/answer_review.py now describes claim as an exact span of draft and quote as exact continuous text of its cited source excerpt. Every included anchor must follow that contract, regardless of verdict. A negative assessment may retain concrete issues with evidence=[]; it is not converted into supported to escape validation. Controlled local validation errors name an indexed field such as evidence[0].claim without echoing rejected source/model values. Arbitrary JSON/type/key errors use static schema feedback. The correction ceiling and public return shape remain unchanged. No source matching, case, punctuation, Markdown, quote-length, source-membership or supported-verdict requirement was relaxed.

Four new tests in the existing tests/test_answer_review.py cover repairing source text copied into claim, preserving a negative verdict while removing invalid optional anchors, repairing an invented quotation with safe diagnostics, and malformed-payload feedback without echo. Three failed before the change; all 179 affected offline tests pass afterward with temporary state and external network blocked. An independent deterministic comparison with the exact backed-up validator found identical accept/reject decisions in 302 combinations of verdicts, claim/quote values, case, whitespace, bounds, types, sources and evidence shapes. This sampled comparison does not prove semantic entailment or universal equivalence.

P for live source-quality acceptance. The authorized single Gemini run of the original public Java 17 question finished in 41.44s (42.06s controller), seven model-adapter invocations, no output-budget override or provider fallback. Actual search/read reached Oracle JLS 17 section 8.1.4. Both review replies offered supported but failed evidence[0].claim membership: the wording matches only after removing bold Markdown from the draft. The new precise feedback did not produce an exact anchor within the allowed correction. No answer was approved/published, no generated Java was compiled/executed, and no second live attempt followed. This is model-contract noncompliance, not a quota/network failure; the response is not promoted to a factual-quality pass just because its wording looks similar.

Next design candidate is selection of preassigned draft-span and source-passage IDs, with the application resolving exact originals rather than asking the model to recopy Markdown. That is not implemented or accepted here. Any redesign must preserve source scope, actual-read provenance, coverage/meaning review, unchanged negative decisions and bounded correction; selecting real IDs alone would not establish that a claim is true. Do not repeat prompt-only broad live requests unchanged.

Overall WS4 remains P for hybrid/semantic quality and actual source-verified answer quality. Ollama-related work remains explicitly user-parked and was not involved. Existing Windows-native policy restrictions were not retried. Production edits stay in the current runtime package; no new Python module/package, model/dependency download, saved-provider edit, user-memory/history access, process stop, commit/push or Word synchronization occurred. The owned test process stopped and temporary runtime was removed; .env hashes matched. This turn adds no full-project offline pass claim. Evidence: outputs/acceptance/ws4-review-feedback-20261023-045648/{before.log,offline-tests.json,validator-comparison.json,live/controller.json,live/live.json,live/local-diagnosis.json}.


## Exact passage selections and concern-preserving review correction - 23 October 2026

Y for the implemented selection/validation scope. The existing runtime reviewer supplies bounded exact draft spans and fetched-source passages with content-bound IDs. Native and JSON-mode models can return draft_id/source_id pairs; the application resolves exact original text and applies the existing case-sensitive, whitespace-normalized draft/source-membership checks. It does not strip Markdown, fabricate quotes or accept an unread page. Unknown/stale IDs, source changes, wrong-page assignments, duplicates, non-string IDs and mixed shapes are rejected. Legacy exact claim/source_url/quote anchors and the caller's status/issues/source_urls return shape remain supported. The schema advertises both families for compatibility; the application enforces the exact allowed shapes. IDs establish traceability, not truth or claim coverage.

Source passages are bounded to 20-400 characters and draft spans to 500, without combining separate passages into a quotation. A short source tail may overlap the preceding window to retain exact text. IDs are local to the exact draft/source catalogue and confer no action permission. Existing context-budget preflight and one-correction limits remain; catalogue metadata is included in that budget. All source/page content remains untrusted evidence.

Eight new selection tests failed before implementation. An additional observed live defect received two regressions: supported with unresolved issues must be corrected to a negative assessment; a format-only retry cannot simply erase those concerns and approve the unchanged draft. That approval-erasure case failed before the final guard. All 285 affected answer-review, source/citation, conversation, continuation and provider/JSON compatibility tests pass after final edits. This includes the existing strict legacy-anchor rejection checks. No new full-project suite result is claimed.

The one authorized Gemini live run completed the original public Java 17 workflow in 31.11s (31.66s controller), seven model-adapter invocations, using actual Oracle JLS 17 section 8.1.4 and passage IDs. That run preceded the final concern guard. Its first reviewer reply was contradictory (supported with concrete unresolved issues); the formatting correction removed the issues and approved the same answer. Manual audit therefore did not accept factual/source quality. In particular, the answer's unconditional requirement for every subclass constructor to call super directly omits legal this(...) delegation, documented by JLS 17 sections 8.8.7 and 8.8.7.1. The selected superclass excerpt did not cover all claimed constructor/method behavior. A structural workflow pass is not a quality pass.

The final guard rejects the exact captured two-reply sequence in an offline local replay using the captured passage catalogue. That replay makes no network/generation call and does not claim to reconstruct a fresh full source page. Catalogue construction and scope binding are independently covered by the tests. No second live run followed the manual failure or final guard. The original live report remains unchanged; manual-audit.json and postfix-replay.json record its limits rather than relabeling it as accepted. No generated Java was compiled or executed. Independent manual reference: [Java 17 JLS constructor invocations](https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.8.7.1). The separate OpenJDK JEP page returned HTTP 403 and is not used as fetched evidence.

Overall WS4 stays P for hybrid/semantic quality and actual factual/source-coverage acceptance. Ollama tasks remain explicitly user-parked; no Ollama or blocked native-library run occurred. All edits stay in agent/runtime/answer_review.py and tests/test_answer_review.py; no new Python module/package or dependency/model install. Saved .env hashes matched during the live check, temporary runtime was removed and owned test children stopped. No user facts/history/project files were sent or changed; no commit/push or Word synchronization occurred. Evidence: outputs/acceptance/ws4-passage-selection-20261023-052742/{before.log,final-tests.json,live/controller.json,live/live.json,manual-audit.json,postfix-replay.json}.
