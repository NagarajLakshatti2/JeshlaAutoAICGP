# WS9 9.7 — Traceable reporting and optional Jira links

**Y — selected local reporting pilot. P — live model/interface export acceptance and optional Jira integration.**

Implemented on 24 October 2026 in the new `integrations/reporting` package, exposed through the existing `ProjectTools` class and read-only project-agent registry. Existing API, web and mobile packages remain in place. No provider settings or test execution flow changed.

## Completion checklist

| Status | Work and evidence |
| --- | --- |
| **Y** | Build a report that links selected case IDs to exact requirement/design spans, current generated source revisions, saved execution metadata, native results and supporting artifacts. |
| **Y** | Keep native observations separate from effective execution outcomes. Timeout/unknown exit, stale/mismatched metadata, configuration failure and missing reports cannot turn into accepted passes. |
| **Y** | Preserve failed, skipped, incomplete, blocked and not-run outcomes. Reject duplicate logical IDs/native method mappings rather than add overlapping reports or repeated attempts. |
| **Y** | Verify relative scopes, SHA256 revisions, source quotes and bounded input sizes. Reject credential/private paths, traversal, alternate streams, changed evidence, invented manifest outcomes and unsupported fields. |
| **Y** | Return reviewable Markdown through `build_test_report`; the tool does not save/export a file or start an action. Export continues through existing approved file actions. |
| **Y** | Actual saved-evidence report built: 16 selected cases, 27 artifact references; three API passes, one web pass, eleven web cases not run, one Android command incomplete with a failed native test report. |
| **Y** | 179 focused offline checks passed with no failures, errors or skips, including real local project dispatch with scripted model decisions, approval/receipt controls, existing pilots and provider fallback regressions. |
| **P** | Live hosted-model console/Streamlit use and approval-click/download export acceptance for this new report. No new UI control was added or certified. |
| **P** | Optional Jira linking or reviewed issue update: parked. No authentication, network operation or external write was performed. |

The report matrix has **status P** because application coverage/execution is partial. This does not prevent the **selected reporting capability** from being Y: accurately reporting missing/failed/uncertain evidence is the accepted behavior. It does not complete WS9 application testing or general release acceptance.

## Actual selected report

[Open the case/evidence report](../outputs/acceptance/ws9-reporting-20261024/report.md).

| Slice | Native observation | Effective outcome |
| --- | --- | --- |
| API-TC-001 through API-TC-003 | 3 passed | 3 passed, linked to the original target reports and saved command snapshots |
| TI-TC-001 | 1 passed | 1 passed, linked to requirement span, source, command, observations, screenshot files and trace |
| TI-TC-002 through TI-TC-012 | No native results in this pilot | 11 not run; accepted design titles are linked without inventing generated code or execution |
| ANDROID-SMOKE-001 | 1 failed native report during session startup | Incomplete command / blocked scope; saved timeout has null exit code. 9.6 investigation is linked, no receipt replay |

The selected inventory excludes iOS, which still lacks a compatible prepared execution environment. The earlier successful direct native Android smoke remains separate; it is not combined with the failed Java run. Earlier failed attempts are not counted again.

## Reusable tool

`build_test_report(manifest_file, evidence_folder="")`

The manifest is JSON with `version: 1`, `title`, and 1–24 unique `cases`. Normally it is read from the selected project. An explicit `evidence_folder` may select one dedicated directory under this agent checkout's `outputs/acceptance`; arbitrary external evidence roots are rejected.

References have exactly `scope`, `file` and `sha256`. `project` means the currently selected project root; `evidence` means the chosen evidence folder. Paths remain relative to their scope. This separates target source/native reports from the agent's archived captures without hardcoding a user's project directory.

Each case may include:

- `id`, `test_name`, `test_class`, `scope_state` (`included`, `blocked` or `deferred`) and a bounded explanatory `note`.
- `requirement_refs`: up to three exact line spans with a reference, start/end line and quote. Design/contract snapshots are identified as such; membership does not prove business-rule completeness.
- `generated_ref`, `run_ref`, `report_ref`: current generated source and saved execution/native report references.
- `artifact_refs`: up to six labelled response, observation, screenshot, trace, log, investigation or source-provenance references.

The returned Markdown identifies each link's role and uses a shared evidence index with absolute local file links/digests. The richer local report JSON preserves requirement spans, source/run/report relationships and separate counts. The production tool only returns reviewable content and enforces a bounded response size; it never auto-exports or runs commands. The saved `manifest.json` is a complete example.

## What the checks establish

The original target native report must match the saved command's report snapshot: exact path, format, case inventory, counts, configuration failures, timestamp and execution window. That is recorded metadata evidence, not an independent execution attestation. A source hash verifies current file bytes; it does not establish that the same bytes executed historically. Binary file hashes establish presence/revision only, not screenshot or trace-content review.

Inputs and tool outputs remain untrusted data. Report text cannot approve a patch, trigger a test, authenticate Jira or file an issue. Missing links remain visible; no application defect or complete requirement coverage is inferred from an assertion, report title or status field.

## Artifacts and next gate

Evidence is under `outputs/acceptance/ws9-reporting-20261024/`: `manifest.json`, `copy-provenance.json`, `report.json`, `report.md`, `agent-result.json`, `tests.json`, `tests.log`, `acceptance.json` and selected copied captures. Copies retain their original digests; target source and native reports were only read.

**9.8 handoff:** isolated manual API/web CI is now prepared and locally checked; actual publication/run/release gates remain P. See [current CI handoff](workstream-9-ci-release.md). Keep mobile/iOS blockers and missing live interface gates explicit. Do not rerun accepted pilots merely to refresh a checklist or claim existing agent-unit CI proves target-application tests ran.
