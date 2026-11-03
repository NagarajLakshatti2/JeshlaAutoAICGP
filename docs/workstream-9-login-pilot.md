# T22 — requirement-linked login pilot

Status: P — started 31 October 2026. Current actual target login acceptance: 2/3 (1 November).

The first bounded expansion selects the existing QA Practice Hub login requirements in D:\PlayWrightDemoGradle\qapracticehub-test-cases.md. It does not repeat T21, change the default suite or claim general authentication support.

| Case | Requirement | Current acceptance |
| --- | --- | --- |
| QPH-010 | Valid demo credentials produce successful login | Y — actual native case passed, 1 November |
| QPH-011 | Invalid demo credentials produce an appropriate error | Y — actual native case passed, 1 November |
| QPH-012 | Empty login fields are rejected by form validation | P — actual case failed; generic credentials error observed for empty fields, 1 November |

The exact demo data and expected-result quotes are revision-bound in outputs/acceptance/t22-login-binding-20261031/login-cases-draft.json. Canonical source membership checks passed. Source membership does not establish correctness or human approval, and an exact success/error message has not been invented.

## Completed foundation

The existing integrations.web package now contains form_plans.py for local login draft validation. Inspection adds form ownership, unique-ID evidence, submit-button type, effective disabling and explicit truncation flags. Username, password and submit must belong to the same inspected form, with bounded source-backed data. Existing text-only plan validation/generation and the global model tool registry are unchanged. No new service or dependency was introduced.

29 focused offline tests passed, including existing inspection/text-pilot regressions. A cached Chromium local-HTML probe passed 14 checks with zero page network requests: real form ownership including external form attributes, separate registration form, orphan fields, hidden duplicate IDs/buttons, protected controls, truncation and no input-value capture. These are implementation checks, not live target or browser-UI acceptance.

## Next gates

1. Y — one separately approved public Forms inspection completed: receipt t22-login-inspection-20261031; complete saved controls and screenshot reviewed. Do not repeat it without a specific reason.
2. Same-form/source binding Y for all three cases: login-form, login-username, login-password and login-submit. Actual outcome assertions remain P. The older saved script may treat empty fields as generic invalid credentials; do not weaken QPH-012 required-field validation. No current login failure was reproduced.
3. Prepare project-aligned Java page/step/opt-in feature changes in the existing target packages; obtain exact source-edit approval.
4. Obtain separate selected-case execution approval, collect fresh native results, and reconcile each case. No automatic retries or full-suite run.
5. Verify the selected agent-chat flow in console/browser before claiming that integration. Broader APIs, controls and additional sites remain independent T22 scope.

One approved read-only public inspection is completed. No target edits, form submissions, hosted model requests, installations or Git/Jira operations occurred. A deterministic validator is not a newly exposed agent-chat tool; no global registry or provider fallback behavior was changed. Word snapshot is unchanged.

Current inspection evidence: outputs/acceptance/t22-login-binding-20261031/inspection-acceptance.md and inspection-acceptance.json. Actual login acceptance remains 0/3.

## 1 November — source candidates ready; application/run approval pending

Four new Java/Cucumber files are staged under outputs/acceptance/t22-login-source-review-20261101/candidate in existing page/step/runner packages and an opt-in login feature folder. No target source is applied. Java 17 compilation passed and 13 local fixture outcomes matched, with no page network request. Current live login acceptance remains 0/3.

See review.md/proposed.diff/exact-actions.json for exact source creations and focused-run-review.md for the separate conditional 300-second three-case run. Required-field validation explicitly rejects generic invalid-credentials errors, even if the saved site script behaves that way. The two earlier Y foundations are not repeated. Agent-chat integration and broader T22 scope remain P. Word remains unchanged.

## Current actual run — 1 November 2026

Both exact approvals were granted. The four new source files were applied through completed receipts and verified against reviewed hashes; protected existing source/configuration remained unchanged. The one selected run completed (no command timeout) in 188.724 seconds, exit 1: two passed, one failed, zero skipped/incomplete/configuration failures. QPH-010/011 are accepted Y for their selected scopes. Do not replay them unchanged.

QPH-012 remains P: saved trace values are empty and login-message visibly shows a generic invalid-credentials error. The assertion timed out at the existing project 90-second default waiting for genuine required-field validation. This is now a reproduced application/requirement mismatch, finding T22-LOGIN-DEFECT-001; no weaker assertion, public-site repair or retry occurred. It does not prevent independent T22 expansion, but cannot be called Y without a legitimate application fix or requirement decision.

Evidence: outputs/acceptance/t22-login-source-review-20261101/results.md, case-acceptance.json, native-login-three-cases.xml, native-empty-login-failed-trace.zip and empty-login-observed.jpeg. Earlier source/run-pending and 0/3 descriptions are historical. Current selected acceptance is 2/3; full T22 and agent-chat interface integration remain P. No provider/Git/Jira operation, install or Word update occurred.

## 1 November — bounded saved failure review Y; live interface gate P

The existing post-run reviewer now cites explicit failed feature/Java frames for delegated Cucumber runs. Reusing the saved QPH-012 result produced exact hashed citations at feature line 29, page line 56 and step line 58, without another run or target edit. Shared source limits and conservative unsupported/ambiguous handling remain enforced. Latest focused coverage: 63 checks pass, one existing Windows symlink skip; all 13 new tests pass. See outputs/acceptance/t22-cucumber-review-20261101/review.md and acceptance.json for exact runs/limits.

This is advisory source navigation, not causal proof, a repair or live agent-chat acceptance. Earlier stored receipts are unchanged; future execution review callbacks use the extension. Live login acceptance remains 2/3 and the required-field application mismatch stays open. Actual console/browser saved-evidence explanation and broader controls/APIs remain P. No hosted payload was sent. Word remains unchanged.

## 1 November — real saved-evidence questions and local corrections

The user approved the exact 48-line packet for two hosted questions. Actual console and browser backend both read it completely and explained the case results and failure source locations correctly. Initial local Jira misrouting was blocked before any provider call, then fixed offline. A malformed terminal-JSON presentation and typographic source-identifier substitutions were also found; the decoder/presentation corrections pass 69 focused offline checks. Captured browser answer replay now preserves exact IDs without more model calls.

Selected retrieval/explanation semantics are Y. Final live formatting after the identifier correction, requested brevity and physical browser interaction remain P; no extra model question was sent. All six actual requests used the configured free OpenRouter model, not a forced fallback test. Native login acceptance remains 2/3; original receipts, accepted cases and target source remain unchanged. See outputs/acceptance/t22-live-review-20261101/review-results.md and acceptance.json. Both app processes need restart to load module changes. Word is unchanged.

## 1 November — final console core formatting Y

The one newly authorized console question completed successfully with exact source identifiers/paths, correct saved case outcomes and explicit saved-evidence scope. All 48 packet lines were read; no native test, controlled action or extra hosted question occurred. Target hashes remain unchanged. See outputs/acceptance/t22-live-review-20261101/verification-completion.md/json. Selected core formatting is now closed Y and should not be repeated unchanged. Brevity and nuanced next-step wording remain P; physical browser and broader T22 scope are not certified. Native login acceptance remains 2/3 and QPH-012 stays open. Word is unchanged.

## Milestone reconciliation — 1 November 2026

T22 is now Y under the explicitly accepted finite scope, after QPH-020/021/022 passed 3/3 and all selected evidence reconciled. Earlier full-T22 P references are historical. This does not change the existing case results: API relationship scopes remain accepted and QPH-012 remains failed/open externally, with login native acceptance 2/3. Broader controls/sites/devices/quality are separate future work. See outputs/acceptance/t22-milestone-completion-20261101/completion.md/json. No accepted case was replayed during reconciliation.
