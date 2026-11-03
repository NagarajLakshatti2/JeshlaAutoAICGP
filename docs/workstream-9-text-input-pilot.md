# WS9 Text Input pilot test pack

<!-- current-task-progress:start -->
## Current task progress — 31 October 2026

**Latest completed task: T21 — Text Input acceptance (Y). Accepted checks: 12/12.**

| Check scope | Current status |
| --- | --- |
| TI-TC-001–006: text/clear, two email samples, password, two numeric checks | Y — accepted for recorded scopes; six logical checks in five native scenarios |
| TI-TC-007: date picker | Y — actual native picker selection and exact ISO date passed with the approved API strategy; prior failures retained |
| TI-TC-010: multiline textarea | Y — one actual selected scenario passed; full two-line retention and empty-after-clear verified |
| TI-TC-008, TI-TC-011/012: valid phone, read-only, disabled | Y — actual selected native scenarios passed; protections and exact values verified |
| TI-TC-009: short phone | Y — final approved unchanged-source retry passed India nine-digit invalid-state assertions after blur |

Current task outcome: T21 is completed and closed Y. All twelve logical checks map to retained passing evidence; the combined email scenario accounts for two logical checks. No next T-number has started.

T21 has now met its agreed selected-pilot acceptance scope and moves from P to Y. The twelve logical checks correspond to eleven accepted native scenarios across retained runs; they are not twelve new T-numbers or a new full-suite run.

Status reporting preference: include the current T-number, accepted/total subchecks and unresolved focus in updates; end with one line of overall Y/P/X counts.

**Overall task counts: Y 7 | P 22 | X 8 — total 37.**
<!-- current-task-progress:end -->

## T21 Y — selected Text Input pilot completed, 31 October 2026

**T21 is closed Y: 12/12 accepted logical checks, reconciled against 11 accepted native scenarios across seven completed execution receipts.** The valid/invalid email samples share one accepted native scenario, so twelve independent native tests are not claimed. Final TI-TC-009 passed its explicitly approved unchanged-source retry in 59.45 seconds, exit 0, with all four Cucumber steps, no timeout/failures/skips/configuration failures and unchanged source hashes. It verified India +91, exact nine-digit sample and a phone-specific invalid state after blur.

Every TI-TC-001–012 requirement scope is now mapped to a retained native pass, report hash and completed receipt. Earlier accepted cases were reconciled read-only and were not rerun. Prior date/network failures, the mixed five-case run's overall exit 1, and local verification timeouts remain preserved as historical evidence. Only four individually identified cases passed in that mixed run; its failed short-phone navigation was resolved for acceptance by the separately approved final retry. No failed history is rewritten as a success.

Evidence: outputs/acceptance/t21-remaining-inputs-review-20261031/completion.md and completion.json (complete mapping, source hashes, native scenario identities and seven receipt checks), final-case-acceptance.json and native-short-phone-final-passed.xml. Completed pilot scope is the accepted samples/rules on the selected QA Practice Hub environment in headless Chromium. This is not a newly executed all-case full suite or full WS9/WS8 release; cross-browser/mobile, pixel glyphs, security/backend storage and expanded inputs remain separate. No further code change, provider request, package install, Git/Jira operation or replay occurred during closure. Word snapshot is unchanged.

**Do not reopen T21 or its completed checks without a new documented regression or separately agreed scope.** No next T-number has started. Earlier progress entries below are historical; this completion and the current consolidated register supersede their pending statuses.

## T21 P — 11/12 accepted; only short-phone navigation retry remains, 31 October 2026

The three approved exact source edits were applied and hash-verified. The separately approved five-case run completed in 146.96 seconds with exit 1 overall, no timeout, zero skips/incomplete/configuration failures. Four fresh native cases passed: TI-TC-007 date with the explicit native-picker API strategy, TI-TC-008 valid India phone, TI-TC-011 read-only and TI-TC-012 disabled. Sixteen passed Cucumber step records and unchanged source hashes support those four individual scoped acceptances. The overall run is not called successful.

TI-TC-009 failed at initial homepage navigation with ERR_CONNECTION_CLOSED; its phone assertions did not execute. Other same-site navigations passed, including later cases. No phone code defect is established and no source repair is proposed. Receipt t21-remaining-cases-20261031 and its native partial report/failed-case trace are preserved. Prior date failures and the textarea DNS failure/pass remain retained.

Current T21 acceptance is **11/12 logical checks in ten accepted native scenarios**. Date/valid-phone/read-only/disabled join earlier accepted scopes and are now closed; do not repeat them. Only TI-TC-009 remains P. One unchanged-source run-only retry review selects @TI-TC-009 with the existing 300-second limit, requiring a fresh explicit execution approval. No automatic retry, new source change, provider request, installation or Jira/Git operation occurred. Full T21 remains P until the final case and evidence reconciliation complete. Word is unchanged.

Evidence: outputs/acceptance/t21-remaining-inputs-review-20261031/case-acceptance.json, native-five-case-partial.xml, target-run-summary.json and final-case-review.md. Earlier pending/source/failed-date entries below are historical.

## T21 P — all remaining five cases prepared and locally verified, 31 October 2026

The user requested completing all T21 items. Current work covers only unaccepted TI-TC-007/008/009/011/012. Four new phone/read-only/disabled scenarios and a different date strategy are staged in the existing page/step/feature packages. The date uses explicit native showPicker after a standard click, selection/confirmation and blur; no expected-date assignment or repeated Alt+ArrowDown/refocus strategy. Exact phone rules use real India selection and field-specific validation after blur. Protected fields use observed baselines and ordinary unforced interaction, preserving attributes.

Java 17 compilation and 13/13 local candidate checks passed with zero page network requests. All reviewed target hashes are unchanged. No live target case or source edit ran. Three exact source edits and one selected five-case @T21-REMAINING run (300 seconds) are ready for separate explicit approvals together; execution depends on successful approved edits and exact hashes. Accepted cases are excluded. Prior date failures and textarea DNS failure/pass remain preserved. Full T21 will be marked Y only if every pending case meets its agreed scope and native evidence is reconciled.

Evidence/reviews: outputs/acceptance/t21-remaining-inputs-review-20261031/review.md, exact-actions.json, focused-run-review.md, focused-run-review.json and probe/results.json. Current T21 stays P, 7/12 accepted. No provider request, installation, default suite/build/runner change or Jira/Git operation is introduced. Word remains unchanged.

## TI-TC-010 Y — actual textarea scenario passed; T21 7/12 accepted, 31 October 2026

The explicitly approved unchanged-source retry passed **1/1 actual native TI-TC-010 scenario** in 39.27 seconds: exit 0, no timeout, failures, skips, incomplete cases or configuration failures. Six native Cucumber step records confirm entry of First line + newline + Second line, exact complete multiline retention, clearing and an exactly empty result. Reviewed source hashes remained unchanged. Receipt: t21-textarea-navigation-retry-20261031. Native XML SHA256: 4bdd92b82ffbd5e067e0155bddbcae28604b24e0c4eb4c8b0918d068c0054e0b.

**TI-TC-010 is closed Y for this selected scope. Do not repeat it without a new reason.** The original attempt failed at homepage DNS before textarea assertions; it and its trace/XML are preserved. The later pass used unchanged source, so it is not claimed as a causal code repair of the DNS failure. Earlier missing local-fixture results are not counted as passing checks.

**Current T21 progress: 7/12 accepted logical checks in six accepted native scenarios.** Five remain: TI-TC-007 date (previous failures unresolved), TI-TC-008/009 phone, TI-TC-011 read-only and TI-TC-012 disabled. Next recommended single case is TI-TC-011 read-only. Existing accepted text/email/password/numeric cases and the date case were excluded from this run. No further source edit, provider request, installation or Jira/Git operation occurred. Word remains unchanged.

Evidence: outputs/acceptance/t21-textarea-pilot-review-20261031/case-acceptance.json, target-retry-summary.json, target-retry-result.json and native-textarea-scenario-passed.xml. The initial failure is retained as case-acceptance-initial-navigation-failed.json. Previous pending or blocked textarea entries below are historical.

## T21 P — textarea source applied; first live attempt blocked at DNS, 31 October 2026

The user separately approved all three exact source edits and one conditional live run. Edits are applied through completed receipts t21-textarea-edit-1-20261031 through t21-textarea-edit-3-20261031, with exact reviewed hashes. Existing package structure/methods/scenarios, runner and build remain unchanged. This source-approval gate is closed; do not reapply or request it again.

The selected TI-TC-010 run completed in 214.01 seconds, exit 1, no timeout: one fresh native scenario failed at initial homepage navigation with ERR_NAME_NOT_RESOLVED for qapracticehub.com. The textarea assertions were not reached. This is blocked live acceptance, not an established textarea code defect. Source hashes stayed unchanged. Original receipt: t21-textarea-scenario-20261031. Native XML and trace are preserved.

A single subsequent read-only system DNS lookup succeeded (75.2.60.5); the earlier browser DNS cause/recovery remains unconfirmed. No source, browser, DNS, network or certificate setting was changed, and no automatic live retry occurred. One unchanged-source run-only retry review is prepared for separate approval. Source approval is already complete. No passed cases, failed date, full suite, installation, provider request or Jira/Git operation ran. T21 remains P with 6/12 checks accepted. Word is unchanged.

Evidence: outputs/acceptance/t21-textarea-pilot-review-20261031/applied.json, case-acceptance.json, native-textarea-navigation-failed.xml, dns-followup.json and focused-retry-review.md. Earlier pending-source entries below are historical.

## T21 P — TI-TC-010 textarea prepared; compile passed, local browser timed out, 31 October 2026

Current work is one independent case: TI-TC-010 exact multiline retention and clearing. Three additive edits are staged in the existing page/step/feature packages, using the already-designed First line + newline + Second line sample. Full exact content and after-edit hashes are reviewed. All existing method bodies/scenarios and current target hashes remain unchanged. No target edit or actual test has run.

Java 17 compilation passed after correcting quoting in the isolated probe and excluding runtime-only archives from the compiler classpath. The subsequent local browser process timed out after 90 seconds without producing fixture results. No fixture pass is claimed and no further local retry is planned. Actual Cucumber/target acceptance remains pending. Source approval and single-run approval are presented together as separate questions to reduce round trips; execution is conditional on both explicit approvals, completed edit receipts and exact source hashes.

Review: outputs/acceptance/t21-textarea-pilot-review-20261031/review.md, exact-actions.json, focused-run-review.md and focused-run-review.json. The command selects only @T21-TEXTAREA with a 300-second limit. Completed cases and the failed date scenario are excluded. T21 remains P with 6/12 accepted checks; date is unresolved and TI-TC-008–012 remain unaccepted. No provider request, installation or Jira/Git action occurred. Word is unchanged.

## T21 P — date repair retry failed; stop repeating this strategy, 30 October 2026

The separately approved one-case retry completed in 94.55 seconds, exit 1, no timeout. Fresh native results show exactly one failed TI-TC-007 scenario and zero passes/skips/incomplete/configuration failures. It still expected 2026-09-25 and found the setup date 2026-09-24. All reviewed source hashes stayed unchanged. Receipt: t21-date-scroll-repair-retry-20261030. This execution approval is consumed; no automatic retry is permitted.

**The stable-click edit did not resolve the live failure.** It fixes the controlled smooth-scroll fixture, but that reproduction does not establish the complete live cause. Both failed native runs and their traces are retained; no live repair success, application defect or date-case Y is claimed. The one approved source edit remains applied in the existing page package; no further source change or rollback occurred. No passed case, full suite, installation, provider request or Jira/Git action ran.

**Current T21 progress remains 6/12 accepted.** TI-TC-007 stays P pending a different evidence-based native-picker strategy. The five independent phone/multiline/read-only/disabled checks can proceed without this date repair. Recommendation: complete those independent checks before another date attempt; do not repeat unchanged keyboard/stable-click retries. Any new target change and live execution still need their respective exact approvals. Evidence: outputs/acceptance/t21-date-scroll-repair-20261030/case-acceptance.json, target-retry-summary.json, native-date-retry-failed.xml and native-date-retry-failed-trace.zip. Earlier applied/pending entries are historical. Word remains unchanged.

## T21 P — approved date scroll repair applied; separate retry pending, 30 October 2026

The user approved the one exact source edit. The standard stable click before native picker opening is applied in existing TextInputPilotPage.java through completed receipt t21-date-scroll-repair-edit-20261030. Current bytes match candidate SHA256 763313617ee80907a64d64f7ab2760dccf6dd38e03bdc0fcd4e34ef7b0048874. Other reviewed source files remain unchanged. The source-edit approval is closed; do not reapply it.

The local smooth-scroll reproduction and 12 date/four scroll checks retain their fixture-only scope. A separately reviewed retry selects only @T21-DATE once, uses headless Chromium/offline Gradle with a 300-second limit, and reconciles fresh native results against the preserved original failure. The expected date/retention assertions are unchanged. No live retry, passed-case rerun, provider request, installation, Jira/Git operation or further source change occurred during application. T21 remains P with 6/12 checks accepted and six live checks pending.

Evidence: outputs/acceptance/t21-date-scroll-repair-20261030/applied.json, focused-retry-review.md and focused-retry-review.json. Original failed-run XML/trace and receipt remain preserved. Exact source approval and live execution approval remain separate; a pass is not yet claimed. Word is unchanged.

## T21 P — date scroll-interaction repair reproduced and staged, 30 October 2026

The saved failed-run stylesheet enables smooth scrolling. Adding this rule to a below-fold local fixture reproduces the exact September-24-instead-of-25 symptom; the otherwise matching control passes. The staged single-method correction adds a standard stable click before opening the native picker. Java 17 compilation, all 12 existing date fixture checks and four scroll checks (including three repetitions of the reproduced smooth-scroll condition) pass with zero page network requests. This supports a scroll/picker interaction explanation; the exact live cause/causal repair remains unconfirmed pending an approved live retry.

One exact source edit in the existing TextInputPilotPage package awaits user approval. No target source, assertion, date sample, build, runner or completed scenario was changed or rerun. No sleep, forced click, CSS override, direct expected-date fill, provider request, installation or Jira/Git operation is introduced. Review: outputs/acceptance/t21-date-scroll-repair-20261030/review.md, exact-action.json and probe/ result JSON files. The original live failure and baseline diagnostics remain preserved. After applying the approved edit, request a separate exact @T21-DATE retry approval. T21 remains P: 6/12 checks accepted, six live checks pending. Other independent input cases are not blocked. Word remains unchanged.

## T21 P — actual date run failed; no automatic retry, 30 October 2026

The approved single @T21-DATE run completed in 82.09 seconds, exit 1, no timeout. One fresh native TI-TC-007 scenario failed, with zero passes/skips/configuration failures: the final ISO-date assertion expected 2026-09-25 but found the setup date 2026-09-24. Reviewed source hashes remain unchanged. Receipt: t21-date-scenario-20261030. The source-edit gate and this one execution approval are closed; do not reapply or replay them.

**TI-TC-007 stays P.** Saved XML/trace confirm the keyboard actions were issued and the field retained the setup value; they do not prove the native popup opened/received navigation or establish an application defect. Twelve original local candidate fixtures passed. Three additional local tracing/viewport/scroll diagnostics also passed with zero page network requests, so a page-specific cause remains unconfirmed. No unproven source fix, direct fill of the expected date or automatic live retry was applied.

**T21 remains P with six checks pending:** date TI-TC-007 requires diagnosis/repair and separate reviewed retry; TI-TC-008/009 phone, TI-TC-010 multiline, TI-TC-011 read-only and TI-TC-012 disabled remain unexecuted. Accepted TI-TC-001–006 retain their recorded Y scopes and were not rerun. This date failure does not block preparing the other independent checks. Next date work must establish a scoped correction from evidence before fresh source-edit and execution approvals. Evidence: outputs/acceptance/t21-date-pilot-review-20261030/case-acceptance.json, diagnosis.json, native-date-scenario-failed.xml and native-date-failed-trace.zip. Previous applied/pending entries below are historical. Parked work and Word remain unchanged.

## T21 P — date source edits applied; single-scenario execution approval pending, 30 October 2026

The user approved the three exact TI-TC-007 source edits. They were applied through durable receipts t21-date-edit-1-20261030 through t21-date-edit-3-20261030, and current bytes match the reviewed candidate hashes. Other reviewed source files remain unchanged. Existing page/step/feature packages were extended; no unnecessary package or flat Python helper was created. The source-edit gate is closed; do not apply these edits again.

TI-TC-007 is implemented but not yet run against the target site. Java 17 compilation and 12 isolated local Chromium fixture checks remain candidate-only evidence. The next separate approval is one 300-second headless Chromium run selecting only @T21-DATE, followed by fresh native report and source-hash reconciliation. Passed password/numeric/text/email cases are excluded. T21 stays P with six live checks pending (TI-TC-007–012). No live test, provider request, installation, Jira/Git operation or automatic retry occurred during source application.

Evidence: outputs/acceptance/t21-date-pilot-review-20261030/applied.json, focused-run-review.md and focused-run-review.json. Completed Y scopes and parked work remain closed. Word is unchanged.

## T21 P — date-picker candidate verified; source approval pending, 30 October 2026

TI-TC-007 is prepared in the existing page/step/feature packages. It uses the saved native date locator, seeds only the preceding date for setup, selects the source sample 2026-09-25 through Chromium's native picker using keyboard interaction, then verifies visible native control, exact ISO value and matching UTC representation. Localized display is allowed; pixel glyphs are not inspected. A no-picker control leaves the preceding date unchanged, while opening the picker selects the next day. Blocked picker/unavailable samples fail rather than falling back to fill of the expected value.

Java 17 compilation and 12/12 isolated local Chromium fixture checks passed with zero page network requests. Target/source hashes remain unchanged; no target edit, site reinspection or live scenario ran. Three exact source edits await the user's required approval; one actual @T21-DATE run will require a subsequent separate command approval. Review/evidence: outputs/acceptance/t21-date-pilot-review-20261030/review.md, exact-actions.json and probe/results.json. T21 remains P with six live checks pending. Accepted text/email/password/numeric/export scopes remain closed; parked work and Word are unchanged.

## TI-TC-005/006 Y — actual numeric scenarios passed; T21 P with six checks remaining, 30 October 2026

The separately approved single selected run passed **2/2 actual native scenarios**, TI-TC-005 and TI-TC-006, in 72.68 seconds: exit 0, no timeout, failures, skips, incomplete cases or configuration failures. Fresh native report identity and eight captured Cucumber steps confirm exact `123` retention and initially empty `abc` rejection/ignore assertions executed. All reviewed source hashes remain unchanged. Receipt: t21-number-scenarios-20261030. Native XML SHA256: f8741eb2f3fc8f0dfbf9e2de250be2c6167b3e45f8a780bbbaeba8fe776d8cbd.

**Y — selected numeric scope closed.** Do not rerun these cases without a new documented reason. Password/text/email and report export remain closed; none were rerun. **T21 remains P with six live input checks:** TI-TC-007 date picker, TI-TC-008/009 phone, TI-TC-010 multiline textarea, TI-TC-011 read-only and TI-TC-012 disabled. Six logical input checks now have recorded evidence in five native scenarios (the two email samples share one scenario). No full-pack, cross-browser or release pass is claimed. Fourteen isolated fixtures remain separate candidate evidence.

Evidence: outputs/acceptance/t21-number-pilot-review-20261030/case-acceptance.json, target-run-summary.json, target-run-result.json and native-number-scenarios.xml. Prior source staging/application entries below are historical; their approval gates are closed. No provider request, Jira/Git operation, package installation, automatic retry or repair occurred. Word is unchanged.

## T21 P — numeric source edits applied; separate execution approval pending, 30 October 2026

The user approved only the three reviewed numeric source edits. All three were applied through durable exact-action receipts t21-number-edit-1-20261030 through t21-number-edit-3-20261030. Current bytes match the reviewed candidate hashes. Other reviewed sources, the existing password scenario, runner and build remain unchanged. The edits extend existing appropriate page/step/feature packages; no new flat helper or unnecessary package was created.

TI-TC-005 exact `123` retention and TI-TC-006 initially empty `abc` rejection/ignore are implemented but not yet run against the target site. The Java 17 compilation and 14 isolated fixture checks retain their candidate-only scope. T21 remains P with eight remaining live input checks. Three source-edit approvals are closed; do not apply them again. The next gate is one separate 300-second headless Chromium run selecting only @T21-NUMBER, with fresh native report/source-hash reconciliation. Passed password/text/email cases are excluded. No target test, provider request, Jira/Git operation or package install occurred while applying these edits.

Evidence: outputs/acceptance/t21-number-pilot-review-20261030/applied.json and focused-run-review.md (exact command, scope and source hashes). Existing completed Y scopes and parked tasks remain unchanged. Word is unchanged.

## T21 P — numeric candidate verified; exact edits awaiting approval, 30 October 2026

TI-TC-005/006 are staged in the existing page/step/feature packages: exact `123` retention and initially empty `abc` rejection/ignore using real keyboard entry. Both require an editable field. Java 17 compilation and 14/14 isolated local Chromium fixture probes passed with zero page network requests. The initial fixture key observer included clearing keys; only that observer was corrected, initial evidence retained, and candidate source unchanged. These are candidate checks, not current target-site acceptance. Target/source hashes and existing password bodies remain unchanged; no target edits or live target cases ran.

Review: outputs/acceptance/t21-number-pilot-review-20261030/review.md, exact-actions.json, preservation.json and probe/results.json. Three exact replace_text edits need the user's previously required source approval; actual execution will need a subsequent separate command approval for only @T21-NUMBER. T21 stays P with eight remaining live input checks. Completed Y scopes and parked work are not reopened. Word is unchanged.

## Current execution ledger — 30 October 2026

**Y — TI-TC-004 password case:** separately approved actual selected Cucumber run passed 1/1, with no failures/skips/configuration failures, exit 0, no timeout and unchanged source hashes. Both the native masked type and complete retained value assertion executed. Evidence: outputs/acceptance/t21-password-pilot-review-20261030/case-acceptance.json and native-password-scenario.xml. Backend storage/security and visual screenshot glyphs remain outside scope. This completed case should not be rerun without a new reason.

**T21 Y — no remaining checks in the agreed selected pilot.** TI-TC-001–012 have twelve accepted logical scopes in eleven native scenarios. Final TI-TC-009 retry passed; all retained reports/receipts/hashes reconcile in completion.json. Historical design JSON and original failed attempts remain unchanged. No new full-suite or release certification is claimed.

## TI-TC-004 source applied — 30 October 2026

**P — live password run awaits separate approval.** The reviewed four new page/step/runner/feature files are applied with exact hashes and durable creation receipts. Existing text/email code, default suite and build remain unchanged. The source staging CRLF/LF mismatch was caught before writing and normalized to unchanged approved action content. Java 17 compilation and nine synthetic assertion probes remain bounded candidate evidence, not actual application results. Exactly one selected-run proposal is prepared in outputs/acceptance/t21-password-pilot-review-20261030/focused-run-review.md (300 seconds, headless Chromium, @TI-TC-004). No target tests have run; all nine remaining case checks are still not run. The previous source-edit approval gate is closed; do not apply those files again.

## T21 implementation review — 30 October 2026

**P — TI-TC-004 source candidate staged only.** Existing source still contains two native scenarios. Four new opt-in password-pilot files are prepared in outputs/acceptance/t21-password-pilot-review-20261030/, with exact contents/hashes and edit review. Candidate Java 17 compilation and nine synthetic assertion probes for this ONE case passed; no target file was applied and no application test/browser was run. Source QPH-003 and agreed TI-D03 are preserved. All nine remaining input-case checks stay not run. Apply only after exact review approval, then request separate focused execution approval. Existing text/email acceptance and historical baseline records below are retained.

## Current execution update — selected text and combined email acceptance, 29 October 2026

**Y — T04 selected assertion scope.** The real Cucumber @QAP-3 text-entry/clear scenario passed separately, and the explicitly approved retry of Verify Email Input Validation passed one fresh native case with no failures/skips. Both supplied email samples and their after-blur assertions executed within that combined scenario. This exercises the TI-TC-002/003 requirement checks but is not two independently executed native tests. The earlier navigation-timeout attempt is retained, and the unchanged-code retry is not causal-repair evidence. Other nine designed input-case checks remain not run; WS9/release acceptance is separate.

Current evidence and source hashes: outputs/acceptance/t04-email-assertion-review-20261029/ (retry-run-summary.json, native-email-scenario-retry-passed.xml, applied.json and verification.json); real text result: outputs/acceptance/t04-text-assertion-review-20261029/. The original 23 October JSON design/source records are frozen historical baselines; later execution evidence does not retroactively change their not_run values. Current Markdown statuses below distinguish those baselines from observed results.


Updated 29 October 2026. Project: D:/PlayWrightDemoGradle. Feature selected by the user: Text Input module.

**Current status: 9.0 Y; 9.1 Y for the selected Text Input design pilot.** Revision 2 contains 12 not-run cases covering nine source stories with 35 step/result pairs and six recorded pilot decisions. The design is accepted by the assistant acting under the user's explicit choose-the-best delegation; independent human review is not claimed. Gemini completed one live source read -> rejected quote -> corrected draft -> final answer in four model calls (30.55 seconds). The saved answer clearly states that the test has not been run. The original design pack remains a not_run baseline; user notes and a later actual Chromium TI-TC-001 pass are recorded separately below. The later selected text and combined email execution updates below supersede execution counts; the other nine input-case checks remain not run, and wider WS9/release gates are separate.

The selected repository document is the planning source. Feature files and Java code supply implementation evidence, not independent proof that the business rules are correct. QPH case identifiers and the @QAP-3 source tag have not been verified against live Jira.

## Default selection under user delegation

The user asked the assistant to choose the best option and include all useful options where possible. Revision 2 remains the recommended default: all nine selected input types and 12 distinct requirement-backed cases. Preserve allowed alternatives (for example, reject or ignore alphabetic number input) instead of inventing one mandatory UI implementation. Additional input limits or formats remain deferred until specified. Routine technical choices can proceed under this delegation; it does not itself claim independent human review, external action approval or an observed test result.

## Current completion checklist

| Gate | Status | Evidence scope |
|---|---|---|
| 9.0 Project/requirement selection | **Y** | Selected Text Input sources and existing package conventions; read-only setup |
| Requirement clarification and source traceability | **Y** | Six decisions resolved; nine source stories / 12 cases / 35 step checks |
| Revision 2 design acceptance | **Y — delegated** | Accepted under the user's choose-the-best delegation; independent human review not performed |
| Reusable checker and bounded correction | **Y** | Native/legacy compatibility, precise source checks, one matching correction and conservative failure handling |
| Sampled live planning flow | **Y** | Gemini read/check/final, one quote correction; source QPH-001 maps to TI-TC-001 |
| **9.1 Selected Text Input design pilot** | **Y** | Required design and sampled live gates complete within this stated scope |
| 9.2 Observations and defect drafting | **Y — TI-TC-001 observation pilot** | Actual Chromium entry/clear passed after normal overlay dismissal and field click; values/screenshots/timestamps saved. Failure drafts tested offline; no actual defect or external filing |
| Application execution evidence | **Text and combined email passed; nine remaining input-case checks not run** | Actual selected Cucumber text and combined email scenarios passed in separate runs; no full suite or independently executed email case pair is claimed. |

The live checker still returns P for human/factual/execution checks on its generic draft result and approval_granted false. The scoped design-review decision is recorded separately with its authority; no tool output grants action approval. No claim is made that all 12 cases were generated live or that all three providers passed the live flow. Completion evidence is in outputs/acceptance/ws9-9-1-pilot-completion-20261023.

## Pilot scope and success criteria

- Read the selected project and requirement sources; preserve the target project and its existing uncommitted work.
- Preserve source references and hashes, cover every selected story, separate assumptions and unresolved expectations, and prevent duplicate cases or invented limits.
- Review expected versus actual behavior explicitly; begin every case as not run.
- The 12-case design review is complete under delegation. Review and approve separately scoped code changes/execution before carrying out any action.

## Verified project structure

Build files declare Java 17, Gradle, Playwright, Cucumber, TestNG, Spring and REST Assured. Versions are declarations, not a successful dependency-resolution/build claim. Existing web packages are src/main/java/web/pages and src/test/java/stepdefinitions; the selected runner is runners.QAPracticeHubTestRunner. The root testng.xml also selects API tests, so a default whole-suite invocation is not the selected pilot. The testsuites/testng-web.xml file is empty. No runner was invoked.

The README suggests Ollama, but the inspected WebHooks.java has its LlmGateway import and summarizeFailure call commented out. This read-only pilot has no model/Ollama dependency; no service was started. Existing local changes in the automation repository were retained.

## Source register

| ID | File relative to the selected project | Use |
|---|---|---|
| SPEC | qapracticehub-test-cases.md | Module lines 12-144 are the selected requirements/test expectations |
| FEATURE | src/test/resources/features/qapracticehub/Text Input Module.feature | Two existing Text Input scenarios; not execution evidence |
| STEPS | src/test/java/stepdefinitions/qapracticehub/InputValidationSteps.java | Actual current assertions |
| PAGE | src/main/java/web/pages/qapracticehub/QAPracticeHubHomePage.java | Current selectors and validation helpers |
| RUNNER | src/test/java/runners/QAPracticeHubTestRunner.java | Current feature/glue selection |
| BUILD | build.gradle | Declared stack and runner/tag configuration |
| SUITE | testng.xml | Default runner selection |
| NAV | src/test/java/stepdefinitions/qapracticehub/NavigationSteps.java | Configurable application URL loading |
| HOOKS | src/test/java/stepdefinitions/hooks/WebHooks.java | Current hook dependencies and disabled model call |
| README | README.md | Project overview; setup instructions may be stale |

Hashes and exact file/line references are retained in outputs/acceptance/ws9-text-input-pilot-20261023/sources.json and test-pack.json.

## Coverage matrix

| Requirement | Existing source case | Draft case IDs | State |
|---|---|---|---|
| TI-R01 Basic text entry and clearing | QPH-001 | TI-TC-001 | Passed in isolated Chromium and actual selected Cucumber scenario; see execution ledgers |
| TI-R02 Valid and invalid email handling | QPH-002 | TI-TC-002, TI-TC-003 | Supplied checks passed together in one native Cucumber scenario on 29 October; separate independent native cases not claimed |
| TI-R03 Password masking and retained input value | QPH-003 | TI-TC-004 | Passed in one actual selected Cucumber scenario on 30 October; native type and exact value only |
| TI-R04 Number input constraints | QPH-004 | TI-TC-005, TI-TC-006 | Y — 2/2 actual selected Cucumber scenarios passed on 30 October; exact 123 and empty-after-abc assertions |
| TI-R05 Date selection and display | QPH-005 | TI-TC-007 | Y — actual selected native-picker API strategy passed; original failed approaches retained |
| TI-R06 Phone input with country code | QPH-006 | TI-TC-008, TI-TC-009 | Y — separate actual valid/invalid India samples passed after blur; initial connection failure retained |
| TI-R07 Multiline textarea entry and clearing | QPH-007 | TI-TC-010 | Y — 1/1 actual selected unchanged-source retry passed exact two-line retention and clearing; initial DNS failure retained |
| TI-R08 Read-only input preserves existing value | QPH-008 | TI-TC-011 | Y — actual selected ordinary typing preserved observed baseline and protection |
| TI-R09 Disabled input prevents interaction | QPH-009 | TI-TC-012 | Y — actual selected unforced click/typing remained blocked and baseline/protection unchanged |


## Coverage by input type — revision 2

| Input type | In-scope cases | Requirement-based coverage | Extra rules outside the current scope |
|---|---|---|---|
| Basic text | 001 | Exact supplied text; clear to empty | Required/whitespace, Unicode and maximum length |
| Email | 002-003 | Valid/invalid source samples; blur; field-specific feedback | Extra address formats, empty/required and exact error text |
| Password | 004 | Display masking and field value retention | Password strength, minimum length, backend storage |
| Number | 005-006 | Accept 123; reject/ignore abc from empty state | Decimal, sign, exponent, min/max |
| Date | 007 | Select source sample; underlying ISO value; localized display allowed | Allowed ranges, impossible-date entry and other locales |
| Phone | 008-009 | India +91; ten-digit sample; nine-digit negative boundary after blur | More than ten digits, letters and other countries |
| Multiline | 010 | Retain both proposed lines and line break; clear to empty | Maximum length, long-line wrapping and normalization policies |
| Read-only | 011 | Observed original value remains after attempted user typing | Programmatic changes and unspecified paste/selection policies |
| Disabled | 012 | Disabled state/attribute; ordinary interaction blocked; value unchanged | Focus/accessibility behavior and dynamic enablement |

The additional rules listed above are not invented expected outcomes and are not claimed as tested. They can become extra cases once their requirements are supplied. The nine selected source stories are covered; this is not exhaustive coverage of every possible input value, security check, device or browser.

## Pilot decisions and remaining clarifications

The rules below are selected pilot requirements, not observations of the application. The user explicitly accepted the four proposed remaining rules on 23 October 2026. All six recorded questions are resolved; current application support remains unverified.

### TI-D01 Email validation trigger

Under the user's explicit delegation, validate when the email input loses focus (blur). A valid email retains the typed value and has no email-associated error or invalid state after blur. This resolves TI-Q01; it does not impose a rule on other applications.

### TI-D02 Invalid email outcome

The user explicitly chose mandatory email-specific validation. After blur, invalid-email must produce a message associated with that field or a verifiable invalid state of that field. A global unrelated error or checking the retained invalid string alone is insufficient. Exact message text remains unconstrained. This resolves TI-Q02 for the pilot.

### TI-D03

Password checks cover masking and retention of the supplied value in the input field only; backend persistence or credential storage is outside this pilot.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D04

The numeric input must reject or ignore alphabetic input. Starting from an empty field, attempting abc must not leave alphabetic text as an accepted field value.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D05

Compare the underlying selected date value in YYYY-MM-DD form. The visible display may follow the browser locale; do not assert one localized display string.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D06

For the selected India +91 phone field, accept ten digits and require a phone-field-specific invalid state for nine digits after blur. Application support and exact UI indicators remain unobserved.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-Q03

Does password stored correctly mean retaining the typed value in the input only? Backend persistence or credential storage is not specified.

**Y — Resolved by TI-D03 (explicit user acceptance).** Password checks cover masking and retention of the supplied value in the input field only; backend persistence or credential storage is outside this pilot. Application behavior has not been observed.

Affected cases: TI-TC-004. Sources: SPEC:54-58.

### TI-Q04

For abc in the numeric field, must the input ignore the characters, reject entry, or retain text and show validation? Confirm the required observable outcome.

**Y — Resolved by TI-D04 (explicit user acceptance).** The numeric input must reject or ignore alphabetic input. Starting from an empty field, attempting abc must not leave alphabetic text as an accepted field value. Application behavior has not been observed.

Affected cases: TI-TC-006. Sources: SPEC:69-73.

### TI-Q05

What date display format and locale should this test assert? The source says correct format without defining it.

**Y — Resolved by TI-D05 (explicit user acceptance).** Compare the underlying selected date value in YYYY-MM-DD form. The visible display may follow the browser locale; do not assert one localized display string. Application behavior has not been observed.

Affected cases: TI-TC-007. Sources: SPEC:83-87.

### TI-Q06

What indicates acceptance of the India +91 ten-digit phone value, and what must occur for nine digits? The shorter-value validation step is conditional and has no explicit expected rejection.

**Y — Resolved by TI-D06 (explicit user acceptance).** For the selected India +91 phone field, accept ten digits and require a phone-field-specific invalid state for nine digits after blur. Application support and exact UI indicators remain unobserved. Application behavior has not been observed.

Affected cases: TI-TC-008, TI-TC-009. Sources: SPEC:97-102.

## Detailed manual cases — revision 2

Revised at the user's request across all nine selected input types. Original case IDs, source priorities and six agreed decisions are preserved. Every row is a planned action and expected outcome; no row is an actual test result. **Design review Y — accepted under user delegation. Execution: not run.**

Reset editable fields as stated so cases are independent. For read-only and disabled controls, record the original value and retain their protections. Identify controls from the real application when execution is separately selected; no live locator or behavior is claimed here.

### TI-TC-001 Enter the specified text and clear the input

Requirement: TI-R01. Source: SPEC:15-29. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: exact text/clear checks passed in actual selected Cucumber and isolated browser runs.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "Hello World"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the basic text input and reset it to an empty starting value. | The intended editable text input is identified and the test starts without leftover text. | Test setup; no new business rule |
| 2 | Enter Hello World and inspect the complete input value. | The complete value equals Hello World; a merely nonempty or different value is insufficient. | SPEC:24-25 |
| 3 | Clear the same input and inspect its value. | The value is empty after clearing. | SPEC:26-28 |

Existing automation evidence: FEATURE lines 3-10 declare this scenario with tag @QAP-3. STEPS lines 32-33 only check non-null/nonempty; they do not assert exact equality. The tag is not verified against live Jira.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-002 Accept the supplied valid email

Requirement: TI-R02. Source: SPEC:31-44. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: supplied valid-email checks passed within the combined native email scenario on 29 October; separate independent case execution is not claimed.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"email": "test@example.com"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the email input, focus it and remove any previous value. | The intended email input is identified and ready for the supplied sample. | Test setup; no new business rule |
| 2 | Enter test@example.com, then move focus away without submitting the form. | The email field loses focus after the supplied sample is entered; validation is observed at blur. | SPEC:40-41; TI-D01 |
| 3 | Inspect the retained value and any validation signal associated with this email field. | The value remains test@example.com and there is no email-associated validation error or invalid state after blur. | SPEC:40-44; TI-D01 |

Historical implementation evidence (23 October baseline; superseded by the current execution update above): FEATURE lines 15-16 include valid email in a combined scenario; STEPS lines 59-60 check absence of a broadly located error. No run performed.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-003 Validate the supplied invalid email

Requirement: TI-R02. Source: SPEC:31-44. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: supplied invalid-email checks passed within the combined native email scenario on 29 October; separate independent case execution is not claimed.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"email": "invalid-email"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the email input and remove any previous value, including a valid email from another case. | The negative case starts independently; the supplied invalid email will replace rather than append to old data. | Test setup; no new business rule |
| 2 | Enter invalid-email, then move focus away without submitting the form. | Validation is observed after this email field loses focus. | SPEC:42-44; TI-D01; TI-D02 |
| 3 | Inspect a message or invalid-state indicator specifically associated with the email field. | An email-specific error message or verifiable field invalid state is present. An unrelated page error or retained text alone is insufficient; exact message wording is unconstrained. | SPEC:42-44; TI-D02 |

Historical implementation evidence (23 October baseline; superseded by the current execution update above): FEATURE lines 17-18 require a validation error. STEPS lines 75-78 assert only the invalid string value; the validation assertion is commented out.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-004 Mask the password input and verify intended value retention

Requirement: TI-R03. Source: SPEC:46-58. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: actual selected Cucumber scenario passed on 30 October 2026 (1 native pass); backend storage and visual glyph validation are outside scope.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"password_sample": "password123"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the password input, clear any existing value and enter the supplied password123 sample. | The supplied sample is entered into the intended password field independently of earlier cases. | SPEC:54-55 |
| 2 | Inspect the displayed password characters. | The displayed password is masked; the sample is not displayed as ordinary readable text. | SPEC:56-56 |
| 3 | Compare the retained input value with password123 through the field value check. | The input retains the supplied value. This checks the field only; backend persistence or credential storage is outside the pilot. | SPEC:57-58; TI-D03 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

Current implementation/execution: the separate opt-in Remaining Text Input Pilot.feature, TextInputPilotSteps/Page and TextInputPilotTestRunner implement this case. Native receipt t21-password-scenario-20261030 passed exactly one selected scenario; see the current execution ledger. The earlier baseline implementation note above is historical.

### TI-TC-005 Accept the supplied numeric input

Requirement: TI-R04. Source: SPEC:60-73. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected scenario passed, 30 October 2026. Actual result: The supplied value 123 was retained exactly after clearing.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Recorded execution used the selected QA Practice Hub environment and headless Chromium; this is one observed run, not future availability or cross-browser acceptance.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"number": "123"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the numeric input and clear any existing value. | The correct numeric field starts empty so prior data cannot satisfy this check. | Test setup; no new business rule |
| 2 | Enter 123 and inspect the resulting numeric value. | The numeric value 123 is accepted and retained; a different nonempty value does not satisfy the case. | SPEC:69-70 |

Current automation evidence: opt-in Remaining Text Input Pilot.feature and existing TextInputPilotSteps/Page packages implement this case. Receipt t21-number-scenarios-20261030 passed the two independently selected numeric scenarios; see case-acceptance.json. The original selected Text Input Module.feature remains unchanged.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-006 Handle the supplied alphabetic value in the number field

Requirement: TI-R04. Source: SPEC:60-73. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected scenario passed, 30 October 2026. Actual result: After real alphabetic abc entry from empty, the field remained empty.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Recorded execution used the selected QA Practice Hub environment and headless Chromium; this is one observed run, not future availability or cross-browser acceptance.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "abc"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the same numeric input and clear it to an empty value. | The invalid-input case starts empty and independently of the positive numeric case. | Test setup; no new business rule |
| 2 | Attempt ordinary user entry of abc and record whether entry is rejected or the letters are ignored. | The control rejects or ignores the alphabetic entry; the requirement permits either behavior. | SPEC:71-73; TI-D04 |
| 3 | Inspect the resulting field value after the attempted entry. | The initially empty field remains empty; alphabetic text is not retained as an accepted numeric value. No specific error message is required. | SPEC:71-73; TI-D04 |

Current automation evidence: opt-in Remaining Text Input Pilot.feature and existing TextInputPilotSteps/Page packages implement this case. Receipt t21-number-scenarios-20261030 passed the two independently selected numeric scenarios; see case-acceptance.json. The original selected Text Input Module.feature remains unchanged.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-007 Select the sample date and inspect its display

Requirement: TI-R05. Source: SPEC:75-87. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected native case passed on 31 October 2026; source hashes unchanged.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"date": "2026-09-25"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the date input and open its date picker. | The intended date control and picker are identified for the selected environment. | SPEC:83-84 |
| 2 | Select the supplied 2026-09-25 sample through the picker. | The sample date is selected. An unavailable sample or missing picker is recorded as an observation to review, not silently replaced by an invented date rule. | SPEC:85-85 |
| 3 | Inspect the selected value and the displayed date. | The underlying value is 2026-09-25 in YYYY-MM-DD form and the display represents that date. Localized display is allowed; no fixed locale-specific string is imposed. | SPEC:86-87; TI-D05 |

Current automation evidence: opt-in Remaining Text Input Pilot.feature and existing TextInputPilotSteps/Page implement this case. Actual receipt t21-date-scenario-20261030 failed the final date assertion; source hashes stayed unchanged. The separately approved stable-click retry t21-date-scroll-repair-retry-20261030 failed with the same value. No picker-selection acceptance, application defect or successful live repair is claimed. Stop repeating this strategy. The original Text Input Module.feature remains unchanged.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

Current accepted execution: receipt t21-remaining-cases-20261031 contains this independently identified native pass with all four Cucumber steps. The batch overall failed only at TI-TC-009 navigation. Prior stage notes above are historical; no full-run success is inferred.

### TI-TC-008 Accept a ten-digit phone value with the specified country code

Requirement: TI-R06. Source: SPEC:89-102. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected native case passed on 31 October 2026; source hashes unchanged.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"country_code": "+91", "phone": "9876543210"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the phone field, select or confirm India (+91), and clear any previous subscriber value. | The selected country is India (+91) and no previous number can satisfy the positive case. | SPEC:97-97 |
| 2 | Enter the supplied ten-digit subscriber value 9876543210 and move focus away. | The supplied ten-digit subscriber value is entered under the selected India country code. | SPEC:98-99; TI-D06 |
| 3 | Inspect the retained subscriber value and validation state associated with this phone field. | The supplied ten-digit value is accepted and retained, with no phone-field invalid state after blur. | SPEC:98-102; TI-D06 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

Current accepted execution: receipt t21-remaining-cases-20261031 contains this independently identified native pass with all four Cucumber steps. The batch overall failed only at TI-TC-009 navigation. Prior stage notes above are historical; no full-run success is inferred.

### TI-TC-009 Validate the nine-digit phone sample after blur

Requirement: TI-R06. Source: SPEC:89-102. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — final actual selected unchanged-source retry passed on 31 October 2026. Actual result: India +91, exact nine-digit sample and field-specific invalid state after blur verified.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"country_code": "+91", "phone": "987654321", "digits": 9}`. Origin: Proposed nine-digit data derived from the source ten-digit example; it is not a new business rule..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the India (+91) phone field and clear its current subscriber value. | The short-value case starts independently, without the previous ten-digit sample. | SPEC:97-97 |
| 2 | Enter the proposed nine-digit value 987654321 and move focus away. | The nine-digit sample is entered and this phone field loses focus before validation is checked. | SPEC:100-101; TI-D06 |
| 3 | Inspect the invalid state specifically associated with the phone field. | A phone-field-specific invalid state is present after blur. An unrelated page error or the retained short value alone does not satisfy validation; exact message text is unconstrained. | SPEC:100-102; TI-D06 |

Current automation evidence: approved opt-in Remaining Text Input Pilot.feature plus existing TextInputPilotSteps/Page. Receipt t21-short-phone-final-retry-20261031 passed one fresh native case with all four Cucumber steps; initial homepage connection failure remains preserved. Original selected Text Input Module.feature is unchanged.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-010 Enter two lines and clear the textarea

Requirement: TI-R07. Source: SPEC:104-116. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected unchanged-source retry passed on 31 October 2026. Actual result: both lines including their newline retained exactly; empty after clearing. The initial DNS failure is preserved.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "First line\nSecond line"}`. Origin: Proposed synthetic two-line data; the source specifies multiline entry and clearing but no literal sample..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the textarea and reset it to an empty value. | The intended multiline control starts empty. | Test setup; no new business rule |
| 2 | Enter the proposed two-line sample: First line followed by a line break and Second line. | Both sample lines appear in order with their separating line break; a single joined line or missing content is insufficient. | SPEC:113-114 |
| 3 | Clear the textarea and inspect its content. | The textarea is empty after clearing. | SPEC:115-116 |

Current automation evidence: the separately approved opt-in feature and existing TextInputPilotSteps/Page implement exact two-line retention and empty-after-clear checks. Java 17 compilation passed. The original receipt t21-textarea-scenario-20261031 failed before these steps at ERR_NAME_NOT_RESOLVED. Separately approved unchanged-source retry t21-textarea-navigation-retry-20261031 passed one fresh native scenario and all six Cucumber steps. No source repair of the DNS failure is claimed.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-011 Preserve the prefilled read-only value

Requirement: TI-R08. Source: SPEC:118-130. Priority: Low.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected native case passed on 31 October 2026; source hashes unchanged.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"replacement_attempt": "Changed value"}`. Origin: Proposed replacement text for an edit attempt; the starting value must be observed, not guessed..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the prefilled read-only input and record its exact original value. | The baseline is observed from the selected environment, not invented from a fixed example. | SPEC:126-129 |
| 2 | Attempt ordinary keyboard entry of the proposed Changed value text without removing read-only protection or changing DOM attributes. | Ordinary user typing does not edit the read-only control. | SPEC:127-128 |
| 3 | Compare the displayed/input value with the recorded baseline. | The original value remains unchanged and displayed; unrelated field values do not satisfy the assertion. | SPEC:128-130 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

Current accepted execution: receipt t21-remaining-cases-20261031 contains this independently identified native pass with all four Cucumber steps. The batch overall failed only at TI-TC-009 navigation. Prior stage notes above are historical; no full-run success is inferred.

### TI-TC-012 Prevent interaction with the disabled input

Requirement: TI-R09. Source: SPEC:132-144. Priority: Low.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: Y — actual selected native case passed on 31 October 2026; source hashes unchanged.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"typing_attempt": "New text"}`. Origin: Proposed synthetic typing-attempt data; no fixed initial field value is assumed..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the disabled input and record its initial value and disabled state. | The intended disabled control and its initial value are identified without assuming fixed content. | SPEC:140-143 |
| 2 | Attempt ordinary clicking and typing of the proposed New text sample, without force-enabling the control. | The disabled control is not available for ordinary user interaction; no forced interaction is used as a substitute. | SPEC:141-142 |
| 3 | Inspect the disabled attribute and compare the final value with the recorded initial value. | The disabled attribute is present and the attempted interaction has not changed the original value. | SPEC:142-144 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

Current accepted execution: receipt t21-remaining-cases-20261031 contains this independently identified native pass with all four Cucumber steps. The batch overall failed only at TI-TC-009 navigation. Prior stage notes above are historical; no full-run success is inferred.

## Static findings requiring a reviewed follow-up

These are source-inspection findings or risks. They are not reproduced application defects or results of a test run.

### TI-F01 Wrong nonempty text can satisfy the current text-entry check

Priority: High. Classification: static assertion gap. Source: SPEC:24-28, FEATURE:7-10, STEPS:28-34.

The expected input is Hello World, but the step asserts only non-null and length greater than zero.

Proposed next change: After review, retain the entered value in scenario-scoped state and assert exact equality. Do not hardcode Hello World into a reusable step.

Applied: no. Runtime reproduction: no.

### TI-F02 Invalid-email scenario does not assert a validation result

Priority: High. Classification: static assertion gap. Source: FEATURE:17-18, STEPS:63-78.

The step computes error/invalid-state flags and then asserts only the string value; the actual validation assertion is commented out.

Proposed next change: Resolve TI-Q01 and TI-Q02, then assert the confirmed field-specific validation outcome. Keeping the input string alone does not verify validation.

Applied: no. Runtime reproduction: no.

### TI-F03 Email validation lookup can match another visible error

Priority: Medium. Classification: potential false positive. Source: PAGE:26-28, PAGE:59-60.

The fallback selectors include generic visible error and invalid classes instead of restricting every fallback to the email field.

Proposed next change: Inspect the actual permitted application and scope the chosen validation signal to the intended field before using it as an oracle.

Applied: no. Runtime reproduction: no.

### TI-F04 Invalid-email outcome is conditional in steps and mandatory in expected results/Gherkin

Priority: High. Classification: requirement conflict. Source: SPEC:42-44, FEATURE:17-18.

The existing document says validation error if present, but its expected result and the Gherkin require validation.

Resolution: TI-D01 and TI-D02 settle this requirement conflict for the pilot. Mandatory email-field validation after blur is the selected requirement. The original document/feature and Java assertions remain unchanged.

Applied: no. Runtime reproduction: no.

## Deferred coverage

- Required/empty/whitespace rules for text and email are unspecified.
- Text/textarea maximum lengths are unspecified; confirm a limit before designing L-1/L/L+1 expected outcomes.
- Unicode/paste/trim/normalization rules are unspecified.
- Number min/max, sign, decimal and exponent rules are unspecified.
- Phone values above ten digits and international-country behavior need an agreed scope.
- Date minimum/maximum and supported locale policy are unspecified.
- Accessibility and browser/device matrix need separate acceptance criteria.

## Evidence history — earlier checkpoints

The sections below preserve their status at the time recorded. Their earlier P/blocked entries are superseded for the selected 9.1 pilot by the current completion checklist above. Broader WS1-WS8, factual-quality and execution limits retain their stated scope.

## Initial acceptance checkpoint

- Y Selected the actual project and feature with the user; inspected relevant source and package conventions.
- Y Produced a source-linked draft and checked complete story mapping, unique case IDs and unchanged inspected source hashes.
- Y Resolve TI-Q01 and TI-Q02 for the selected email pilot using explicit user/delegated decisions.
- Y Resolve all six recorded questions using the original email decisions and the four newly accepted pilot rules.
- P Complete human/semantic review of the 12 cases and accept the intended assertions.
- Y Implement the reusable read-only source-plan checker in agent/tools/test_plans.py, with existing ProjectTools, policy and shared runtime wiring; mocked agent integration and real-source checks pass.
- P Accept live AI-generated requirement-to-test-pack planning and human/factual review; offline integration does not close that gate.
- X Generate or change target automation code under the selected project packages.
- X Execute selected tests and collect fresh run evidence.

No application, Gradle suite, Jira authentication, provider request or Ollama request was performed. The automation project was not modified. All WS1-WS8 statuses retain their existing scope.

## Reusable source-plan checker checkpoint — 23 October 2026

| Item | Status | Evidence / remaining boundary |
|---|---|---|
| Correct package placement | **Y** | Implementation in existing agent/tools/test_plans.py; thin ProjectTools wrapper; tool classification in agent/policies/tool_registry.py; shared schema/handler in agent/runtime/conversation.py; project instructions in agent/langgraph/langgraph_agent.py. No new flat agent-root module or unnecessary subpackage |
| Bounded draft structure and local source checks | **Y** | Unique IDs, registered fields, required outcomes/questions, bounded case/source counts, project path restrictions, exact quoted spans, SHA256 revision checks and changed-source rejection |
| Draft-only result policy | **Y** | Structure/source-traceability can be Y; factual correctness, human review and execution stay P. All cases remain not_run, actual_result null and approval_granted false |
| Agent registration and compatibility | **Y** | New checker is read-only in both existing project and shared conversation registries. Mocked shared conversation reads requirements and checks a draft without provider/search/Jira/action execution |
| Current pilot source acceptance | **Y** | All 12 existing cases checked in three batches of four against the unchanged specification hash; each result remains a draft. Email decision provenance is preserved separately from repository quotes |
| Live AI-generated plan and semantic review | **P** | No live provider generation/selection acceptance in this milestone. Matching a quote does not prove an expected outcome follows from it or that the source is approved |
| Recorded requirement decisions | **Y** | All six original questions resolved with explicit decision provenance; all 12 cases ready for human review |
| Human acceptance | **P** | Test design is ready for review; no human/factual acceptance or actual application result is inferred |
| Target application tests and fresh run evidence | **P** | No target code edits, app/Gradle run or observed execution results in this step |

Acceptance evidence: outputs/acceptance/ws9-test-plan-tool-20261023. The focused suite ran 77 tests with no failures/errors and one Windows symlink-permission skip. The compatibility suite ran 50 tests: 49 passed and one Streamlit AppTest timed out at its existing 10-second limit. That exact decline test passed on one isolated rerun without changing the timeout or application code; retain the initial timeout as a repeatability observation. After adding the project-tool contract, all 43 final affected tests completed without failures/errors, with the same symlink-permission skip. These are focused results, not a full-suite/release pass.

The existing shared conversation tool-output limit still applies. The real pilot used small batches whose results fit that limit; the checker does not establish unlimited-size plan delivery. The existing pilot test-pack.json retains the original decision records and all cases as not run. Provider configuration, action approvals, Jira authentication, Ollama parking and WS1-WS8 statuses are unchanged. Markdown checkpoints were updated; the Word diagram remains its previous snapshot.



## Confirmed pilot rules checkpoint — 23 October 2026

- **Y** — User accepted TI-D03 through TI-D06: password field value/masking only; reject/ignore numeric letters; underlying ISO date comparison with localized display allowed; India phone ten-digit acceptance and nine-digit field validation after blur.
- **Y** — Updated exactly five affected cases; the other seven case records and source hashes are unchanged. All 12 passed bounded structure/source checks again and have no unresolved recorded questions.
- **P** — Human/semantic review of the completed draft and observed application behavior. Every case is still not run.
- **P** — Live AI-generated planning: the user subsequently approved this exact excerpt/path and generated draft/check results for all three hosted providers. The bounded check and one changed-path recheck ran; the latter reached OpenRouter, Groq and Gemini, but no validated plan completed within its four-call budget. The initial automatic-review rejection is historical; authorization is no longer the blocker.

The reusable live acceptance entry point is evaluations/test_plan_live.py in the existing evaluations area. It confines model tools to the selected source read and draft checker, caps model calls, disables local Ollama for the evaluation process, and uses an external 100-second controller deadline. No persistent provider setting or target code was changed. New verification: outputs/acceptance/ws9-pilot-rules-live-20261023/rule-verification.json. WS9 stage 9.1 remains P for its remaining review/live gates; the earlier checker milestone remains Y within its scope.


## Approved hosted check and fallback fix — 23 October 2026

- **Y** — The user explicitly authorized the reviewed 15-line text-entry excerpt, project path and generated draft/check results for OpenRouter, Groq and Gemini.
- **Y** — Reproduced and fixed a missing read-only fallback registration: agent/providers/tools.py now recognizes read_file and validate_test_plan for the existing bounded compatibility/failover mechanism. Mixed write/approval/memory-proposal registries remain excluded; no persistent provider configuration changed.
- **Y** — Affected offline suite: 94 run, 93 passed, one Windows symlink-permission skip, zero failures/errors. The new regression failed before the fix and passes afterward; it also checks that existing source evidence is preserved on provider switch.
- **Y** — Live fallback observed: OpenRouter quota -> Groq successful requirement read -> Groq quota -> Gemini response. The first run stopped at Groq TOOL_OUTPUT; both original and changed-path results are retained.
- **P** — Live planning completion: the changed-path run took 23.48 seconds and reached its four-model-call budget without an accepted checked draft. Tool names were recorded, but rejected argument/error details were not retained in that version, so the exact validation rejection cause is not established. No third hosted attempt was made.
- **Y** — Evaluation diagnostics now retain rejected checker arguments and their static validation errors. A synthetic offline check verified this logging and confirmed an invalid draft remains unaccepted. This diagnostic improvement is not a live-planning pass.
- **P** — Next technical gate: diagnose the rejected draft format from the new records in a separately bounded check, then verify one complete read -> checked draft -> final answer. Preserve the source checks and actual not-run labels. Human/semantic acceptance of all 12 cases and target execution remain pending.

Evidence: outputs/acceptance/ws9-pilot-rules-live-20261023/hosted-checkpoint.json, fallback-offline.json, live.json, after-fallback-fix/live.json and diagnostic-offline-check.json. The selected source hash is unchanged. No target file changes, test/application/Gradle execution, Jira authentication or Ollama request occurred. Stage 9.1 remains P; WS1-WS8 statuses and the earlier Word snapshot are unchanged.


## Bounded provider diagnostic and local design review — 23 October 2026

- **Y** — Ran the next requested diagnostic on the same explicitly approved excerpt; completed in 11.99 seconds (12.37 including controller). The source hash is unchanged.
- **P — BLOCKED** — Live planning: OpenRouter rate/quota limit, Groq TOOL_OUTPUT after its bounded recovery, then Gemini HTTP 503 PROVIDER_TEMPORARY. The run read the selected requirement but returned no new plan to the local checker. No draft-format cause was established; changing validation rules without that evidence would be speculative. No additional hosted attempt was made in this step.
- **Y** — Completed a local assistant design review of all 12 cases against all nine selected stories and the six explicit/delegated pilot decisions. The audit separates original requirement support from user decisions, confirms source sample/proposed test data provenance, and checks that invented limits/backend persistence/actual results were not added. This is an agent review, not user acceptance or application verification.
- **P** — User acceptance of the 12-case design is requested in this chat. Keep the existing pending_human_review state until an explicit reply; approving the case design does not authorize or claim test execution.

Evidence: outputs/acceptance/ws9-pilot-rules-live-20261023/diagnostic-with-rejections/{live.json,controller.json,checkpoint.json,local-design-review.json}. Stage 9.0 remains Y; stage 9.1 remains P for user design acceptance and a successful complete live planning flow. No production-code change was justified by this provider-blocked diagnostic. No automation-project file, app/test execution, Jira connection, Ollama setting or provider configuration was changed. Next: record the user's design decision, then make at most one unchanged live sample when hosted availability permits; avoid repeated broad tests or schema relaxation.


## All-input-types revision checkpoint — 23 October 2026

- **Y** — Implemented the user's request to revise all selected types according to requirements: 12 revised cases, nine input types, 35 action/expected-result pairs with source/decision/setup provenance.
- **Y** — Preserved all case IDs, original requirements, priorities, sample data, six prior decisions and deferred coverage. Every case has an independent starting state or an observed protected-field baseline; error checks are field-specific where required.
- **Y** — Validated the revised draft locally in four bounded batches. Exact cited source excerpts and hashes still match; all nine requirement IDs map to cases; original source and target project are unchanged.
- **P** — User re-review/acceptance of revision 2. The earlier request for changes has been implemented, not converted into approval. All cases remain pending_human_review and not_run; no actual result or receipt is fabricated.
- **P — BLOCKED** — Complete live AI planning remains at the last recorded provider blocker (OpenRouter quota, Groq tool-output rejection, Gemini HTTP 503). No hosted retry, application/Gradle run, Jira authentication or Ollama request occurred for this revision.

Structured case details remain in outputs/acceptance/ws9-text-input-pilot-20261023/test-pack.json (design_revision 2). Verification and the pre-revision backup are in outputs/acceptance/ws9-all-input-types-revision-20261023. No new Python module or runtime behavior was needed for this case-design revision. WS9 9.0 stays Y; 9.1 remains P for re-review/live acceptance. Word and WS1-WS8 statuses retain their prior scope.


## Bounded plan-correction task checkpoint — 23 October 2026

- **Y** — Implemented specific, trusted validation feedback in the existing tools/runtime packages. TestPlanValidationError retains ValueError compatibility; only validator-authored messages are exposed for correction. Arbitrary backend errors keep the generic safe response.
- **Y** — The shared conversation runtime permits one correction of a rejected draft, preserving case identities and source files. A matching complete visible checker result can resolve that draft rejection; a second invalid attempt stops with an incomplete result. Earlier unrelated tool failures are not erased.
- **Y** — Unrelated case IDs, changed source files, malformed original scope, truncated results and forged approvals cannot turn the pending draft into a completed check. Every accepted checked draft still has human/factual/execution P and cases not_run.
- **Y** — Reproduced two pre-fix failures, then ran the affected offline suite: 208 run, 207 passed, one Windows symlink-permission skip, zero failures/errors. This is focused compatibility coverage, not a full release pass.
- **Y** — Separate real-source/offline-model acceptance completed read -> deliberate quote rejection -> one matching correction -> final draft in four mocked model calls. The source hash is unchanged and no hosted request or application test ran.
- **P** — WS9 stage 9.1 live-provider planning and design acceptance keep their prior scope. The latest hosted blocker remains the last recorded provider/quota/format/503 result; it was not rechecked during this offline task. The new correction behavior has not been live-certified.

Package placement: agent/tools/test_plans.py holds the strict validator and typed error; the new helper agent/runtime/test_plan_feedback.py holds correction-state policy; agent/runtime/conversation.py wires it into the existing shared loop. Tests extend tests/test_test_plans.py. No new subpackage was necessary. Existing project-action tools and approvals retain their behavior; this correction component is scoped to shared conversation, not a rewrite of every project-action loop.

Evidence: outputs/acceptance/ws9-bounded-plan-correction-20261023/{affected-offline.json,affected-offline.log,pilot-correction-offline.json,before/}. Selection policy is recorded in the original test-pack.json. No provider order/settings, target project files, Jira connection, Ollama status or WS1-WS8/Word status changed.


## Structured plan input and wrapper fix — 23 October 2026

- **Y** — Captured the actual failures in the next live diagnostic: malformed JSON embedded in the plan_json string; expected_results supplied as a string instead of a list; source quotes copied with the reader's display line-number prefixes. The evaluation wrapper also parsed the string before canonical validation, bypassing the new typed correction feedback.
- **Y** — Added a preferred native plan object with nested field/array/reference schemas to the existing validate_test_plan tool. Legacy plan_json calls remain supported; exactly one input form is required. The same strict canonical source/identity/size checks apply. Quotes still must match source text; line-number prefixes are not silently stripped or accepted.
- **Y** — The existing evaluation wrapper now uses the canonical bounded decoder and safe typed validation for malformed/sample-scope inputs. Replaying the exact captured malformed input offline confirms useful feedback; the matching native draft is checkable. An unidentifiable malformed original still cannot be silently declared recovered.
- **Y** — Affected compatibility suite: 223 run, 222 passed, one Windows symlink-permission skip, zero failures/errors. All 12 current pilot cases produce identical results through the native and legacy inputs in four bounded batches. Source hashes remain unchanged and every case is still not run.
- **P — BLOCKED** — One changed-path hosted recheck completed its controller in 51.41 seconds (47.56 in the evaluator). OpenRouter reached quota; Groq then failed to connect, before any source read/draft returned. Gemini was not attempted after that connection error under the existing policy. No full live planning pass is claimed and no further hosted attempt followed.
- **Y** — Evaluation failure reporting now distinguishes a failed provider/category from an actual successful model response. An offline mocked connection error verifies that no successful provider is claimed when none returned. The original live record is retained unchanged; read its error/log alongside the corrected reporting behavior.

Code placement stayed in existing agent/tools, agent/runtime, agent/langgraph and evaluations areas; regressions extend existing tests/test_test_plans.py. No new package or dependency was needed. The automation project, provider order/persistent configuration, Jira/Ollama state and WS1-WS8 statuses are unchanged. Stage 9.0 remains Y; 9.1 remains P for design acceptance and a complete live planning flow. No target application or test suite was run.

Evidence: outputs/acceptance/ws9-structured-plan-input-20261023/{affected-offline.json,pilot-input-compatibility.json,wrapper-offline-check.json,failure-report-check.json,live/live.json,before/}. The pre-fix captured input is retained in outputs/acceptance/ws9-bounded-plan-correction-20261023/live-after-correction/live.json. This checkpoint supersedes the earlier statement that the draft-format cause was unknown; its compatibility checks are separate from the outstanding hosted gate. Markdown was updated; the Word diagram remains its earlier snapshot.


## 9.1 selected pilot completion record — 23 October 2026

**Y — complete within the selected Text Input manual-design/pilot scope.** Gemini completed the real read -> validate -> one quote correction -> final answer sequence in 30.55 seconds (36.81 including controller). The original evaluation result was a false negative only because it recognized not run but not this test has not been run. The evaluator now recognizes that equivalent narrative wording and excludes quoted/code-only disclaimers. Four targeted disclosure tests pass; the saved model response was reassessed without a model rerun and its original SHA256 is preserved.

Local answer review confirms source case QPH-001, supplied Hello World data, entry/clear steps, expected outcomes, exact source span and explicit unexecuted status. The original report/log and the reassessment remain separately available. Revision 2 design acceptance is recorded as a delegated decision under the user's choose-the-best instruction; this does not certify an independent human review, all-provider availability, actual application behavior, test execution, or the full WS8 release.

Evidence: outputs/acceptance/ws9-9-1-pilot-completion-20261023/{completion.json,live-reassessment.json,disclosure-tests.json,before/}; original live record: outputs/acceptance/ws9-structured-plan-input-20261023/gemini-isolated/live.json. All 12 cases are still not_run with no actual results. Next is 9.2: scoped observations and defect drafts using real evidence. No target files/commands, persistent provider order/settings, Jira authentication or Ollama requests changed. This update covers Markdown/JSON; the Word diagram remains its earlier snapshot.

## Historical — initial 9.2 observation and defect-draft checkpoint, 23 October 2026

**Component Y; stage acceptance P.** The read-only tool is implemented in the existing tools package, with wrappers/specifications in the existing project, conversation and policy packages. No new flat helper or duplicate provider/action stack was added. The shared backend is available to console/browser orchestration; a live user interface/model acceptance run has not been claimed here.

- **Y** — Read one exact case from either the canonical test_cases pack or the checker's cases output. Require paired steps/expected results and a report bound to the exact case-file SHA256.
- **Y** — Read saved observation notes inside the configured project root, check exact text spans/digests and require actual-result text in the cited note. Outcome/observer identity remain attributed claims, not independently verified behavior.
- **Y** — Keep missing steps not_run with null actual results. Distinguish reported pass, reported failure, blocked and partially observed states. Synthetic reports retain an explicit synthetic status and draft title.
- **Y** — Failed reported steps produce review-only drafts with case/step ID, prerequisites/test data where present, reproduction steps, expected/actual results and evidence. Cause/severity remain undecided; no application run, approval, write, Jira authentication or external issue is performed.
- **Y** — Reject conflicting duplicate steps, wrong IDs, stale revisions, mismatched quotes, self-citation, unknown action/approval fields, invalid timestamps/JSON, unsafe paths, oversized input/output and files changing during review.
- **Y** — Preserve ordinary file-action and explicit Jira routes; local observation analysis does not enter the generic test-case/Jira drafting route.
- **Y** — Offline regressions: 180 tests run, 179 passed, one existing Windows symlink permission skip. Original 12-case pack is unchanged and all cases remain not run. The selected real case-file format was exercised only with clearly synthetic notes.
- **P** — Check actual pilot observations and review a supported defect draft if a failure is observed. No actual observation, application result, reproduced bug or external filing is currently claimed.

### Next user input

For **TI-TC-001**, supply the actual environment/application URL or build, browser, observation time, and these three step results in plain language:

1. Which basic text field was selected and its starting value.
2. Its complete value after entering **Hello World**.
3. Its complete value after clearing the same field.

Include saved observation notes/log text if available. Unknown details stay unknown. You do not need to calculate hashes or hand-author the manifest: after actual notes are supplied, the assistant can prepare a source-linked observation report without inventing results. Application runs and external filing require their own scope. Screenshots can be reviewed separately; this first tool validates saved UTF-8 text evidence and does not claim image inspection.

### Tool contract and sample

`draft_test_observations(case_file, observations_file, case_id)` reads both JSON files within the configured project root and returns a draft; it does not save or execute anything. A report contains schema_version 1, case_pack_sha256, run metadata (id, timezone-aware observed_at, environment, observer, provenance), and up to 20 observations. Each observation identifies case_id, step_number, reported outcome (passed/failed/blocked), actual_result and exact local evidence references (file, start_line, end_line, quote, sha256). Provenance is user_report or synthetic_fixture; a file cannot certify connected-tool execution. Use separate reports for different runs. Underlying requirement references are copied from the case file and explicitly not re-verified by this observation tool.

Evidence and an explicitly synthetic example are in outputs/acceptance/ws9-observations-20261023: tests.json/tests.log, synthetic-notes.txt, synthetic-observations.json, synthetic-result.json and local-acceptance.json. These are fixture results, not test-application results. The exact canonical case pack remains outputs/acceptance/ws9-text-input-pilot-20261023/test-pack.json. Provider order/configuration, Ollama parking, target files and WS1–WS8 statuses are unchanged. Word remains the earlier snapshot.

## Historical — partial user observation intake, 23 October 2026

**9.2 P — actual partial notes received.** The user identified https://qapracticehub.com/#inputs and the Enter your name field, then reported that its placeholder disappears after typing, reappears after clearing, and Backspace removes the selected text. Preserve this as user-reported behavior, not independent agent execution or a complete TI-TC-001 pass. Exact Hello World retention has not been stated; browser and actual observation time are unknown. Receipt/storage time is recorded separately and is not substituted for observation time.

Evidence: outputs/acceptance/ws9-user-observations-20261023/user-notes.txt and partial-intake.json. No failure is reported and no defect draft or external issue is created. The original design pack remains unchanged. This is a partial intake record, not a fabricated complete manifest for the strict observation tool. Next confirmation: was the complete field text exactly Hello World before clearing?

## 9.2 selected observation pilot COMPLETE — 23 October 2026

**Y — TI-TC-001 observation pilot only.** The earlier manual-confirmation loop is superseded by actual isolated Playwright evidence. Windows Computer Use was unavailable, but installed Playwright/Chromium was usable; the earlier inference that this required user confirmation was too narrow. The coding agent inspected the actual page and identified the unique editable ordinary text input from its observed Enter your name placeholder. The first direct-value check passed; screenshot review revealed a cookie banner, so the final accepted check explicitly clicked its observed Decline button, then clicked the field normally before typing. No overlay or protected field was bypassed.

The accepted run observed input values **empty -> Hello World -> empty**, verified placeholder hidden after entry/visible after clearing, and used select-all/Backspace. Chromium 153.0.8010.12, isolated headless viewport 1280x900. Actual observation timestamps and three screenshots are linked to the exact unchanged case-pack hash. The case passed, so no actual defect is claimed or filed. The existing defect-draft failure path was tested offline with clearly synthetic evidence; it does not invent a live failure.

Current execution status is one passed case / 11 not run in outputs/acceptance/ws9-browser-input-20261023/execution-ledger.json. The original 12-case design artifact remains unchanged as a not-run baseline and is not the current execution ledger. Current evidence is entry-clear-with-consent/live-result.json plus initial.png, entered.png and cleared.png. The earlier entry-clear run and partial user intake are preserved separately as history. completion.json records the narrow acceptance scope.

Reusable implementation: agent/tools/browser_inputs.py accepts a selected page, targeting method (exact label/placeholder/role name), field description and required test value; no QA Practice Hub URL, element ID or per-site selector is hardcoded there. It stops for ambiguous/missing/protected/non-text controls and respects click actionability. evaluations/browser_input_acceptance.py is an explicit configurable CLI harness, not an unattended action exposed to the deployed agent. Tests in tests/test_browser_inputs.py plus existing saved-observation regressions: **37 passed** offline. Actual browser capture is not relabelled user_report or synthetic to force it through the saved-report contract.

This proves one reusable text-field capability and one real case. It does not prove every website, email/date/password/dropdown/button behavior, LLM-selected browser plans, automatic agent-chat browser tool use, all browsers, native mobile, target Gradle suites or WS9 release. Those later integrations remain pending. Do not repeat manual exact-value questions for this completed observation. Next planned stage is 9.3; full browser orchestration is 9.4. No target source, persistent provider configuration, Jira/Ollama state or Word snapshot changed.
