# JeshlaAutoAI UI implementation

Status Y for the agreed chat UI redesign, implemented and verified 19 October 2026. Cowork/project configuration and GitHub remain P (parked). Native Streamlit controls follow the approved mockup; this is not a pixel-identical replacement of another product. Earlier sections below record the implementation history; the latest scope is in the final redesign section.

## Implemented first slice

- Y: visible recent-chat buttons, current-chat highlighting and original saved-chat picker retained in an expander.
- Y: case-insensitive recent-title filtering; no-match state preserves the active chat. Scope is the catalog's up to 30 recent chats, not all archived transcript content.
- Y: existing optional-title New chat form, memory viewer and conversation download preserved.
- Y: native navigation/memory icons, product description and a simpler empty-chat message.
- Y: sidebar extracted into agent/interfaces/sidebar.py. No custom CSS, provider/model changes or storage migration.

## Verified

12 focused UI/approval tests passed in 12.026 seconds with the outer offline guard. Tests cover filtering without model calls or chat switching, restoring the selected chat history, new/multiline chats, memory viewing, provider error recovery and exact-action approve/decline/rerender protections. Initial logger-binding regression was fixed before the accepted run. Logs: outputs/acceptance/ui-sidebar-final.log and ui-sidebar-summary.json. Visual user acceptance remains pending.

## Next UI capabilities

- Y: local archived-message search, scoped to current chat or user/memory space; excerpts and explicit open-chat navigation.
- Y: readable memory presentation with expandable metadata.
- Y: explicitly confirmed memory save/update/forget UI controls using existing memory commands.
- Y: read-only provider/model information, key-presence indication and restart guidance.
- Y: confirmed next-start provider/model editing with syntax/key-presence validation; API keys preserved and restart required.
- Y: browser-session request status per chat distinguishes completed, incomplete, waiting and failed; save failures remain separate warnings.
- Y: bounded document previews, text/answer downloads and receipt-scoped unchanged approved text-file downloads.
- P: additional formats, arbitrary binary-generated-file downloads and project management parked at user request.
- P: local/GitHub project management and new-project workflow remain planning-only and parked in ui-project-management-plan.md.

Current approval review and multiline composition remain working features; they are not replaced by cosmetic controls. Future voice/subscription/Cowork controls are outside the initial scope. Keep current console, logs, receipts and backup. Refresh the running browser to load UI changes; only restart Streamlit if the page does not reload.

## Readable memory and responsive layout acceptance

Added agent/interfaces/memory_panel.py: saved names/values displayed separately from provenance/timestamps in Details, using native full-width controls. BrowserBackend.memory_records reads structured facts for its explicit user/namespace without a model request; old memory output and command behavior remain. Legacy text is supported for existing adapters. First 50 structured facts are displayed with an explicit count; stored values are unchanged.

14 focused memory/sidebar/approval checks passed with the outer offline guard in 52.753 seconds. Report ui-memory-responsive-summary.json.

Eight real browser layout checks passed using installed desktop Chrome and Edge at emulated widths 360, 390, 768 and 1440, height900. Synthetic long answer/URL and pending action fixtures were used. No page horizontal overflow; visible memory controls fit and wrap; sidebar fits. Chrome phone/desktop screenshots were inspected. This checks the current chat/sidebar/memory/approval fixture page, not every possible page/content. Physical phones/tablets, iOS Safari/WebKit and Firefox remain unverified because those engines/devices were unavailable. No browser engine was downloaded.

Local fixture server and test browsers were stopped; no provider calls, user files, credentials or state were used. Native Streamlit layout and sidebar collapse are retained. No custom CSS, fixed page widths, LAN binding or public hosting added. Refresh/restart the user's app for visual acceptance. Access from a separate physical phone needs a separately configured reachable host; 127.0.0.1 refers to that phone itself.

## Archived conversation search — 18 October 2026

Y: Search conversation text in the sidebar uses the existing bounded local catalog search without an LLM. Choose Current chat only or search within the configured user/memory space. Results show title, time and plain-text question/answer excerpts. Opening is explicit and restores a chat even outside the 30 recent titles. Search does not submit an agent turn or approve an action. It uses whole-word matching with all words required; up to 10 results, 10,000 turns and the first 8,000 characters of each question/answer. Older checkpoint-only history may be absent. No-match text states the limit; truncation is visible.

16 guarded UI/memory/approval tests passed in 18.709 seconds, including archive content matching, user scope, current-chat scope, old-chat navigation, and preserved approval behavior. Evidence: outputs/acceptance/ui-archive-search.log. This is functional headless acceptance; real mobile/browser visual acceptance for the added search controls remains pending. Refresh the running browser to load the feature.

## Provider/model panel — 18 October 2026

Y: Model settings shows the configured provider/model and a key-presence boolean for hosted providers; Ollama needs no API key. No credentials, endpoint URLs or environment contents are displayed. It does not call a provider, validate credentials, measure quota or change settings. Provider changes still require local .env configuration and restarting running interfaces.

18 guarded provider/sidebar/search/memory/approval tests passed in 50.684 seconds. Evidence: outputs/acceptance/ui-provider-panel.log. Four providers and Gemini's existing key alias are covered; missing configuration is distinguished from connection acceptance. Real-browser visual acceptance for this new popover remains pending.

## Shared-memory editor — 18 October 2026

Y: Shared project memory now offers Save / update and Forget, exact fact name/value fields, and a required shared-memory confirmation. Confirmation resets after successful submission; rerenders do not repeat writes. Save/update uses REMEMBER, forget uses FORGET through BrowserBackend.submit, retaining existing command routing, provenance/revision policy, same-chat locking and transcript behavior. Fact names are validated against the existing 1–64 character rule; nonblank values are limited to 2,000 characters. No separate model request is introduced. Forget removes shared memory and its stored revisions, not archived conversations; this is explained before submission. Refresh Show saved facts after changing memory.

20 guarded memory/provider/sidebar/search/approval checks passed in 70.567 seconds. Evidence: outputs/acceptance/ui-memory-editor.log. Tests cover command validation, required confirmation, reset, forget selection and no rerender replay. New controls still need live user/browser visual acceptance; current tests use isolated fixtures and do not modify user facts.

## Request status — 18 October 2026

Y: Each chat retains its latest request status across rerenders and switching within the browser session. Unknown completion is labelled Response returned; incomplete/blocked/partial outcomes are not labelled Completed. Awaiting input includes approval; failed requests show Failed. Duration is displayed alongside status, and failed archive/checkpoint writes have a separate warning. Action approval/decline updates the status without claiming the whole original task is completed. New browser sessions may not retain this UI-only status; no new durable storage was introduced.

22 guarded status/sidebar/search/memory/provider/approval tests passed in 51.854 seconds. Evidence: outputs/acceptance/ui-request-status.log. Tests cover status precedence and chat isolation/rerender behavior; real browser visual acceptance remains pending. Upload/download UI and validated settings editing remain unfinished, and project management is planning-only.

## Document attachments and answer downloads — 18 October 2026

Y: Attach a document offers an explicit prepare/preview step. UTF-8 TXT/MD/CSV/JSON work without optional RAG packages; PDF uses optional pypdf, DOCX optional python-docx, with missing-reader guidance. Up to 1 MB per upload, first 10 PDF pages and 12,000 extracted characters; limited extraction is labelled. Blank/image-only PDFs are rejected; no OCR. DOCX paragraphs/tables are read, with bounded ZIP expanded size/count. This is limited text extraction, not full-document interpretation or automatic RAG indexing.

Prepared evidence remains scoped to one chat in browser session state, removable explicitly; other chats do not receive it. Preparing does not call a model or write the original file to disk. Sending a message appends the preview as labelled untrusted document evidence in the existing request/transcript path. Preview is disclosed as sent to the selected provider and stored with the transcript. Extracted text and latest response can be downloaded as TXT/Markdown. These downloads do not yet expose arbitrary generated project files; spreadsheet/presentation/image formats remain pending.

28 guarded extraction/sidebar/search/memory/provider/status/approval tests passed in 39.019 seconds. Evidence: outputs/acceptance/ui-attachments-final.log. Includes actual installed DOCX paragraph/table and blank-PDF fixtures, upload type/size/UTF-8 validation, attachment chat isolation and answer-download state. The initial run exposed a position-dependent new-chat test; New chat now has an explicit stable widget key and the test uses it. Live upload-widget, browser download and mobile visual acceptance remain pending.

## Enhanced browser acceptance — 18 October 2026

Y: Eight real browser cases passed using installed Chrome/Edge at widths 360, 390, 768 and 1440 (height 900). Synthetic local fixtures verified actual file upload/preview, downloaded answer contents, model settings, memory field fit/wrapping, explicit save with confirmation reset, archived-text search and no page-wide horizontal overflow. Screenshots for phone Chrome and desktop Edge inspected. Evidence: outputs/acceptance/ui-enhanced-browser/results.json and screenshots. Reusable runners: evaluations/run_ui_enhanced.py and ui_enhanced_browser.cjs. Fixture server and browsers stopped; user state/credentials/providers were not used. Selector and acknowledgement timing fixes applied only to the acceptance harness.

Current UI slice is implemented and verified within that scope. Remaining: arbitrary generated-project-file downloads, additional document formats, validated settings editing, planned local/GitHub project management, and physical-device/Safari/Firefox acceptance. No claim of full UI enhancement completion. User requested winding down due Codex usage quota; no new feature started.

## Requested UI completion block — 19 October 2026

Y: Files created by approved actions offers prepare/download for up to 20 recent completed actions in the current user/memory-space/chat. Only completed create_file proposals with matching durable receipt identity are eligible. Reads stay in the approved root, exclude symlinks/credential files, cap at 1 MB and compare file bytes with approved content. Changed files are blocked; a prepared download is the checked snapshot, not a rerun or an unrestricted file browser. Approved text/code/JSON exports supported by create_file are covered; arbitrary binary outputs remain parked.

Y: Model settings now explicitly saves the selected provider/model for the next restart. Validates supported provider, model-ID syntax and hosted key presence; does not claim key validity, quota or model availability. Atomic UTF-8 .env replacement preserves other entries, API keys, multiline values and existing newline/BOM conventions; invalid syntax or a detected concurrent edit blocks save. No hot switch, no key editing/display. Restart both Streamlit and console; external environment overrides may take precedence. Production .env was not modified during development/acceptance.

Y: XLSX uploads use optional openpyxl with cached values, first three sheets/100 rows/30 columns and existing character/ZIP limits. No macros or formula calculation; formula-only uploads without cached values are rejected. Explicit memory/chat commands exclude attachments, preventing document evidence from becoming part of REMEMBER values.

Verification: 32 guarded settings/download/sidebar/approval/attachment tests pass in 11.760 seconds (ui-settings-downloads.log); preceding Excel/control block 26 pass in 41.797 seconds (ui-excel-controls.log). Real Chrome 360px and Edge 1440px passed approved-download contents and settings save, alongside existing upload/search/memory controls without page overflow (ui-settings-downloads-browser/results.json). These settings writes/actions used synthetic temporary fixtures only; original user files/providers/state were untouched. Browser/server test processes stopped. Previous eight-size acceptance remains in ui-enhanced-browser/results.json. No fresh broad-suite claim.

P: Rest parked at user's explicit request: local/GitHub/new-project management, additional formats/arbitrary binary exports, physical phones/Safari/Firefox. Both specifically requested UI items are completed within the scopes above. User acceptance in the running real app may follow after quota reset. Last Codex usage check: 3% primary remaining; no new feature is started merely to consume quota.

## Agreed clean chat redesign — 19 October 2026

Y: Replaced the crowded Conversations layout with a JeshlaAutoAI sidebar, New chat, Search chats, title-only Chats and tasks, View all, Memory and Settings. Default history stays saved but the landing view is blank until a chat is explicitly opened; default is labelled General chat in navigation. Memory/settings forms are in dismissible dialogs. Main view has the agreed greeting, rounded responsive composer, plus upload menu, Chat/Cowork switch and provider-only dropdown. Cowork is labelled Soon and shows a project-configuration placeholder; it does not connect a project or GitHub.

Y: Top-right paperclip opens the current chat's document list. Previews/removal/extracted downloads are available inside that list; no document chip is shown under the composer. Plus offers Upload documents, Upload files and Upload folder. Up to five supported documents are extracted per chat; 1 MB each and a combined 12,000-character model excerpt. Folder upload is a limited document batch, not a project-root connection or unrestricted file access. Original files are not persisted by this feature. Related generated-file downloads remain in the top attachment panel, backed by scoped approvals. Evidence stays in the archive/model request but its technical envelope is hidden from the user message bubble.

Y: Provider dropdown shows only Ollama/OpenRouter/Groq/Gemini, with no model identifier or radio/checkbox selection. Top-right info reports the selected provider and its configured default model. Selected provider applies only within that request using ContextVar; text/tool calls use it without changing global environment/default provider, other browser sessions or console processes. Existing configured keys/models/budgets still apply; invalid configuration blocks the request, with no silent fallback. Persistent .env settings editing remains explicit and separate in Settings. No live external model calls were made during acceptance.

Y: Working safeguards retained: graph/console entrypoint, scoped chats/memory, transcript download, exact-action approval/decline, receipt-based file downloads and failure reporting. Existing source copied before edits to outputs/ui-redesign-before-20261019-090100 (eight source/test files; this is a UI source snapshot, not the private full-project backup). Original private full-project backup remains separate. No credentials or user databases were intentionally edited by this UI work.

Evidence: 72 focused UI/provider/error checks passed in 16.991 seconds (ui-redesign-regression.log). Full guarded offline suite: 399 tests passed in 40.480 seconds (ui-redesign-full-offline.log), including the new request-provider test. All eight Chrome/Edge cases at widths 360, 390, 768 and 1440 passed: landing/history visibility, provider-only picker, two-document attachment list/preview, chat response, Memory/Settings dialogs, new-chat attachment isolation, Cowork placeholder, matching provider info and no page-wide horizontal overflow. Results/screenshots in outputs/acceptance/ui-redesign-browser. Desktop Edge and phone-width Chrome screenshots inspected. Desktop engines at emulated widths do not certify physical phones or Safari/Firefox; those remain parked. Test servers/browsers stopped.

First verification found dialog rerender and selected-widget navigation defects; fixed before acceptance. Provider transport fixtures were isolated from inherited model-budget binding, without changing production budget policy. Browser harness now waits for visible icon controls and dialog contents and closes the mobile sidebar before composer actions. User should restart Streamlit to load the layout and theme, then review in the real local app. GitHub/account connection, project creation and full Cowork setup remain parked as explicitly instructed.

## Attachment routing correction — 19 October 2026

User report confirmed from saved transcript: asking whether the uploaded file could be read returned a Jira workflow response. Cause: attachment evidence was appended to the request string and the router's workflow detector scanned document wording as user intent. The upload document did not need to contain the literal word Jira; generic test-case wording could satisfy the legacy workflow matcher.

Fixed by agent/runtime/input_evidence.py: split explicit question and bounded uploaded documents before routing. Attachment questions use the conversational route unless the user explicitly requests a Jira action or a project-file action. Jira issue/workflow nodes independently refuse attachment-triggered calls and inspect only the explicit request. The LLM receives question and uploaded_documents as separate fields and is told to use the supplied excerpt; project-root declarations and saved-memory lookup also use the explicit question only. Existing plain Jira workflow commands and exact-action approvals are preserved. Browser completion logs now include only an allowlisted route name, never prompts, document contents or authentication URLs.

A separate provider CONFIGURATION error was found: OPENROUTER_MODEL had been set to 00077 while its model-bound budget referenced nvidia/nemotron-3-super-120b-a12b:free. User chose restoration of the previous model. Restored only the approved provider/model using the key-preserving settings editor; API keys retained. Restart the running app because existing processes may still hold the old model/configuration or wait on the unwanted login. Cancel the unexpected Jira authentication; attachment questions require no Jira login.

Verification: 70 focused upload/Jira/conversation/root/format checks passed (upload-routing-fix-final.log). Full guarded offline suite: 404 tests passed in 46.781 seconds (upload-routing-full-offline.log). Real OpenRouter full-graph synthetic-upload acceptance passed in 3.89 seconds, route direct, Jira not called, answer grounded in the document (upload-routing-live.json). No actual user upload, saved facts/history or OAuth values were used in live acceptance. Fallback to another configured hosted provider was authorized if a real rate/quota limit blocked verification; none occurred.


## Use-case audit complete — 19 October 2026

Seven reproduced defects fixed: model/budget consistency before settings writes; stale attachment previews after removal; duplicate identities for same-named folder uploads; document-source/negated Jira routing; stale memory previews; stale download buttons after failed revalidation; and older-chat pagination. New tests remain under tests/, production fixes in existing child packages, acceptance code in evaluations/.

Final uninterrupted guarded offline run: 414 passed, 110.290 seconds. Eight Chrome/Edge viewport flows passed; Chrome 360/Edge 1440 repeated successfully on final code. Real OpenRouter synthetic-document graph check passed, direct route, no Jira call. See [use-case-audit.md](use-case-audit.md) and outputs/acceptance/use-case-audit-summary.json. Earlier timeouts are preserved and superseded by the final passing run. Test servers/browsers stopped; user state/configuration not intentionally changed. Restart running interfaces to load fixes.

Package organization is partially complete: top-level agent/ still contains necessary compatibility aliases and some active implementation helpers. Further helper moves remain P for a separate refactor; do not remove aliases or claim full package cleanup. Physical-device/Firefox/Safari acceptance, live health of other providers, GitHub and Cowork project configuration remain unverified/parked. Canonical Word roadmap was not modified by this audit.


## Welcome chat, automatic titles and top-right controls — 19 October 2026

Y — The welcome screen now uses an unsaved, browser-local draft instead of silently addressing General chat. First nonblank send creates one saved chat. Its title comes from the normalized first message, up to 100 characters; longer message bodies are saved in full. General chat opens through explicit sidebar selection. New chat starts another draft without creating timestamp-named empty rows. Draft attachments move to the saved chat, failures/retries keep the same saved chat, and committing a new chat clears a stale title filter so the new title is visible. Existing saved conversations/titles are retained. Confirmed memory edits from the welcome screen also acquire a valid chat scope.

Y — Shared title validation and console help now use TITLE_LIMIT=100. The console's explicit startup/session-choice behavior is retained; this automatic first-message naming change targets the browser flow.

Y — Existing native attachment and selected-provider Info popovers now appear beside the native three-dot menu. New helper agent/interfaces/header_actions.py uses a scoped positioning rule on its own keyed container; the existing theme/colors remain in config.toml. Initial header acceptance used viewer mode with source watching disabled. Superseded by the header overlap/menu follow-up below: developer mode and automatic source watching now retain native Rerun and Auto rerun in the options menu. Do not hide the entire native header/menu or move document/provider logic into styling code.

Verification: 56 focused guarded regressions passed in 78.718 seconds, including ten new landing/title cases and existing saved-chat, memory, attachment, download, approval and CLI title checks. Phone-width Chrome (360px) and desktop Edge (1440px) flows passed on final code: first-message isolation, explicit General selection, 100-character title saved, no sidebar/page overflow, header-control position, visible options menu, hidden developer prompts and functioning attachment/provider popovers. Screenshots inspected. Test browsers/server stopped. This is focused follow-up acceptance; the earlier 414-test full-suite baseline predates these changes.

Evidence: outputs/acceptance/chat-header-final-regression.log, chat-header-browser.json and chat-header-summary.json; reproduction at chat-landing-before.log. Changes stay in existing interfaces/storage packages; new regression code is tests/test_chat_landing.py. Restart Streamlit and reload the browser to apply server/toolbar settings and start a fresh draft. No .env/provider key or saved user history/facts were intentionally modified. Canonical Word roadmap was not changed.


## Header overlap and rerun menu completed - 19 October 2026

Y - Attachment and selected-provider Info popovers reserve space for Streamlit's native running/connection indicator and Stop control. The idle toolbar position now shifts left while those controls are present. Stop, Info, attachment and options controls remain clickable without overlapping at the accepted widths.

Y - The native three-dot menu now contains Rerun and Auto rerun. Current configuration: client.toolbarMode="developer" and server.fileWatcherType="auto". Auto rerun starts disabled unless enabled by the browser user. The separate File change/Rerun/Always rerun prompt and Deploy header button are hidden; native Stop and connection status are preserved. File change is a notification; its actions are available through the menu. Restart Streamlit and reload the page to apply these configuration changes.

Verification: two real Chrome browser cases passed at emulated widths 320 and 1440 with a synthetic six-second response. Checks covered busy-state spacing and click targets, attachment/Info popovers, menu availability and no page-wide overflow. The 320px case additionally changed only a temporary fixture source and verified both manual Rerun and automatic rerun. The running-state screenshot was visually inspected. Physical devices and other browser engines were not reaccepted by this focused follow-up.

Evidence: outputs/acceptance/header-busy-final.log, header-busy-browser/results.json and header-overlap-summary.json. Fixture process metadata confirms its server stopped. No real provider requests, user conversations, facts or .env changes were used for these checks. Prior 56-test focused and 414-test broad baselines are unchanged historical results, not fresh runs of this header-only follow-up. Production changes remain in agent/interfaces/header_actions.py and .streamlit/config.toml; acceptance helpers remain in evaluations/. Canonical Word roadmap unchanged.
