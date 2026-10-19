# Use-case audit — 19 October 2026

**Y — tested scope passed.** Final uninterrupted guarded offline run: **414 tests, zero failures/errors, 110.290 seconds**. Ten new regression tests cover reproduced boundary failures. This validates supported paths under the listed fixtures; it does not mean every possible natural-language input, external account or browser has been tested.

## Bugs reproduced and fixed

| Wrong behavior | Corrected behavior | Implementation |
| --- | --- | --- |
| Saving a hosted model could leave a conflicting model-specific budget and fail on the next request. | Reject incompatible budget/model settings before writing; explain which local budget configuration needs review. Check environment overrides too; existing keys and settings remain intact on rejection. | `agent/config/ui_settings.py` |
| Removing the first attachment could show its old text as the next document's preview. | Preview/download/remove controls follow document identity and content rather than list position. | `agent/interfaces/attachments.py` |
| Same-named, identical files from separate uploaded folders could create duplicate widget keys. | Include the existing upload identity as well as content in control identity. | `agent/interfaces/attachments.py` |
| Reading a Jira reference from an attached document, or explicitly declining a Jira connection, could still route to Jira. | Document-source read requests and explicit Jira negation remain conversational; explicit external Jira operations remain available. | `agent/runtime/input_evidence.py` |
| Refreshing an existing saved fact could retain the old displayed value. | Memory preview identity includes the refreshed fact/metadata, so the displayed value updates. | `agent/interfaces/memory_panel.py` |
| A failed generated-file revalidation left a previous prepared download available. | Clear the prepared snapshot before rechecking; a failed check withdraws the download control. | `agent/interfaces/generated_files.py` |
| View all only exposed the latest thirty chats. | Bounded, scoped Older/Newer pages reach older chats without silently changing the active chat. Page browsing does not call the model. | `agent/storage/chats.py`, `agent/interfaces/browser.py`, `agent/interfaces/sidebar.py` |

## Verification

- Offline suite covers chat/console paths, session and user isolation, archive/checkpoint/recovery behavior, explicit memory commands and provenance, tool policies, approvals/declines/receipts, generated files, provider transport/error/context budgets and supported document extraction.
- All four provider paths are exercised with mocked transport. Real OpenRouter graph acceptance used synthetic document text, returned the document's status color, routed direct and did not call Jira; 19.52 seconds. No saved private history/facts were submitted for acceptance.
- Chrome and Edge passed eight browser flows at widths 360, 390, 768 and 1440. Final-code recheck repeated Chrome 360 and Edge 1440 after the last identity fix. Checks include landing visibility, provider information, two-file upload, removal preview correctness, chat, Memory/Settings, chat isolation and no page-wide horizontal overflow. These use a synthetic backend, not hosted requests.
- Earlier bulk attempts timed out; two initial browser cases also timed out while interacting with uploads. Browser checks now wait for upload/rerun completion. Recorded partial results were preserved. The final uninterrupted suite and final browser recheck passed.
- All test browser/server processes started by the acceptance runner were stopped. Existing user interfaces were not stopped. Test settings, memories, chats and action files use temporary fixtures; the real `.env`, saved chats and facts were not intentionally modified.

## Package placement

New regression code is in `tests/test_use_case_audit.py`; acceptance code remains in `evaluations/`. Production changes are within the existing config/interfaces/runtime/storage child packages. No new production module was placed directly at the project root or directly under `agent/` during this audit.

**P — further structural cleanup.** The top-level `agent/` directory still contains compatibility aliases (for example `browser_backend.py`, `llm_client.py`) AND active implementation helpers (for example `project_context.py`, `project_decisions.py`, `web_pages.py`, `terminal_input.py`, `browser_action_ui.py`). The aliases preserve old callers; the remaining helpers need a separate bounded refactor with import compatibility. Therefore package organization is partially complete, not fully complete. No bulk moves were mixed into this audit.

## Remaining limits

Physical mobile devices, Firefox/Safari, current live health/quotas for Groq/Gemini/Ollama, live Jira/GitHub connections and parked Cowork project setup were not certified by this audit. Unsupported formats/OCR and unrestricted project-folder connection remain outside current upload functionality. Restart the console/Streamlit process and reload the browser to load these fixes.

## Evidence

- `outputs/acceptance/use-case-audit-summary.json`
- `outputs/acceptance/use-case-audit-final-offline.log`
- `outputs/acceptance/use-case-audit-before.log`
- `outputs/acceptance/use-case-audit-preview-before.log`
- `outputs/acceptance/folder-upload-audit-before.log`
- `outputs/acceptance/ui-redesign-browser/results-eight-viewports.json`
- `outputs/acceptance/ui-redesign-browser/results.json`
- `outputs/acceptance/use-case-audit-live.json`
