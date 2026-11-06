# WS9 9.8 — Scoped CI and release acceptance

**Overall: P for full release; Y for reviewed publication and actual selected API/web CI acceptance.** Updated 24 October 2026.

Published the five authorized files to target `master` in [commit 0cb2d5e](https://github.com/NagarajLakshatti2/PlayWrightDemoGradle/commit/0cb2d5e5c19f0c90f8b41938d7fac20ac2faeb86). The single [manual CI run](https://github.com/NagarajLakshatti2/PlayWrightDemoGradle/actions/runs/40018437976) passed **3 native API tests and 1 native web test**, with zero failures/errors/skips. Both lane artifacts were downloaded, hash checked and reviewed against the same commit. This supersedes earlier local-preparation-only statements; mobile/repair/interface and earlier core release gates remain P.

This is the last numbered WS9 stage (9.0–9.8). Preparing a workflow is not a successful CI run. Existing agent CI and target-application CI are different evidence scopes.

## Current browser execution acceptance — 24 October 2026

**Browser-approved native API execution — Y, 24 October:** receipt 78549e9f completed exactly once, command exit0, one fresh exact-method XML with **3 passed / 0 failed / 0 skipped**; native verifier/hash, four source revisions and five GET captures checked. Duplicate UI output came from transcript plus a second notice; fixed with 83 passing offline checks, actual refreshed UI recheck P. Historical approval-stage incomplete text is relabeled; saved transcripts preserved. Export/download, other interface/mobile/repair and full release gates remain P. Evidence outputs/acceptance/ws9-chat-api-execution-20261024 and ws9-action-display-20261024. Do not rerun the accepted cases.

## Completion checklist

| Status | Work and evidence |
| --- | --- |
| **Y** | Inspected the current agent workflow: offline agent tests and console/browser startup. Its existing file was retained. |
| **Y** | Inspected target Gradle, accepted API/web classes and existing target workflows. Added a separate manual-only selected-pilot workflow; original workflows/build/test sources remained byte-identical. |
| **Y** | Added a reusable preparation utility under `integrations/ci`, with packaged workflow/Gradle templates and explicit source-bound profile data. No flat agent helpers or private project paths are embedded in the templates. |
| **Y** | Actual offline Gradle configuration passed: exactly the accepted API class plus ConfigReader, and the accepted web class, in isolated source sets. No application tests or dependency/browser installations ran. |
| **Y** | Actual Gradle/JDK report verifier passed 10 explicitly synthetic checks: valid report, missing/duplicate cases, skips, failures, wrong class/count, suite error, DTD/entity declarations and stale timestamps. These are not API/web passes. |
| **Y** | Final 133 focused offline regressions passed with no failures/errors/skips. The first expanded run exposed an older legacy empty-action-list compatibility bug; the narrow fix and regression preserve ask/finish-only availability. |
| **Y** | Wheel builds include the CI templates; isolated extracted-wheel import/preparation uses a separate data root. This reuses the existing interpreter/dependencies and is not fresh-install acceptance. |
| **Y** | Published exactly five authorized files to verified default branch master in commit 0cb2d5e. Master lacked the locally tracked API pilot, so it was explicitly authorized as the fifth file. Existing build.gradle and the local feature checkout were retained. |
| **Y** | Dispatched once; run 40018437976 attempt 1 passed both jobs on commit 0cb2d5e. Native inventory: exactly three API methods and one web method, no failure/error/skip. Both uploaded artifact archives were downloaded and their GitHub SHA-256 digests verified. |
| **P** | Review actual downloaded CI artifacts and decide release scope. Full WS9 retains the Android Java/iOS runtime, 9.6 repair/rerun and unverified interface gates; this step does not waive them. Earlier WS1–WS8 limits remain separate. |

## Files and repository boundaries

The working AI agent remains at `D:/JeshlaAutoAI`. New Python code is in the appropriate existing integration hierarchy:

- `integrations/ci/gradle.py`: validates explicit reviewed pilot profiles and prepares three reviewable files under the agent's acceptance data directory. It performs no target installation, source generation, test execution, network operation or publication. This is a developer preparation utility, not an unattended registered model action.
- `integrations/ci/templates/ws9-ci.init.gradle` and `ws9-selected-pilots.yml`: package data included by `pyproject.toml`.
- `tests/test_ci_pilots.py`: preparation boundaries, scope, source revisions, line-ending portability and template packaging.

The **new application workflow belongs to the target repository** `NagarajLakshatti2/PlayWrightDemoGradle`, not the agent repository:

1. `D:/PlayWrightDemoGradle/.github/workflows/ws9-selected-pilots.yml`
2. `D:/PlayWrightDemoGradle/gradle/ws9-ci.init.gradle`
3. `D:/PlayWrightDemoGradle/ci/ws9/pilots.json`
4. `src/test/java/tests/web/TextInputAgentPilotTest.java`: existing selected web source, now published.
5. `src/test/java/tests/api/UserLookupPilotTest.java`: existing selected API source, tracked locally but absent on remote master; now published under the fifth-file authorization.

The API pilot was already tracked on the local feature branch but was absent on remote master. An isolated archived-master candidate passed configuration before publication. Its CI profile pins the existing master build.gradle digest; the local feature profile retains its different build.gradle digest. Neither build.gradle was replaced, and the local dirty feature checkout was not staged, committed, switched or reset. Final read-only inspection found the same feature branch at be6d2fd, with a separate local commit after the earlier fb6a25b checkpoint. This task did not create or reset that local commit; the remote CI evidence remains bound to 0cb2d5e. ConfigReader, existing workflows and unrelated target files were excluded from the five-file publication. Build caches and mobile sources are outside this CI slice.

## What the prepared workflow does

- Manual `workflow_dispatch` only, read-only repository contents, checkout credentials not persisted, two separate Ubuntu jobs (`api`, `web`), explicit job/test deadlines and artifact upload on completion/failure.
- Reuses target dependency-version declarations and Java 17 bytecode. Dedicated source sets compile the selected API/ConfigReader or web class. It does not invoke the default broad TestNG/Cucumber suite, ReportPortal listeners, Jira/Confluence, mobile, GitHub writes, Ollama or hosted AI providers.
- Checks the four reviewed source/build text digests. UTF-8 BOM stripping and LF normalization allow Windows/Linux checkout differences without permitting source-text changes. Raw artifact/profile digests remain separate. A real source change requires a newly reviewed profile; the workflow does not auto-update expected hashes or weaken assertions.
- Installs only the matching Playwright Chromium runtime and OS dependencies for the web job. Resolves its reviewed HTTPS host to public addresses and pins one public IPv4 address. Local/private/nonpublic resolution fails explicitly. The fixed web locator/data are the previously inspected and accepted pilot inputs; uniqueness/type/value assertions remain intact.
- Runs exactly the three accepted API methods or one accepted web method. Prevents cached/stale test-result reuse, checks one exact native class XML inventory with zero skips/failures, and requires the selected response/browser artifacts.
- Writes per-lane source/profile/commit/run metadata and scoped acceptance/summary files. A task failure, missing report, timeout or incomplete evidence cannot produce Y. Missing evidence on an interrupted runner remains unaccepted; artifact upload alone is not a pass.

The browser/OS dependency setup follows [Playwright Java CI guidance](https://playwright.dev/java/docs/ci) and the [Chromium installation documentation](https://playwright.dev/java/docs/browsers). Workflow permissions and manual dispatch follow [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Actual publication and CI acceptance — 24 October 2026

The user authorized publication to public master, then explicitly authorized the existing API source as the fifth file and the master-compatible profile. One fast-forward commit was created from the then-current master; the repository's existing build.gradle and the local feature branch were preserved. Cached repository authentication was used without exposing credentials.

- Published commit: [0cb2d5e](https://github.com/NagarajLakshatti2/PlayWrightDemoGradle/commit/0cb2d5e5c19f0c90f8b41938d7fac20ac2faeb86).
- Actual selected workflow: [run 40018437976, attempt 1](https://github.com/NagarajLakshatti2/PlayWrightDemoGradle/actions/runs/40018437976), manual workflow_dispatch on master, both jobs successful.
- API: API_TC_001_directLookupMatchesRequestedUser, API_TC_002_existingFilterMatchesDirectLookup and API_TC_003_absentIdFilterReturnsEmptyCollection all passed. Five captured GET/200 responses confirm requested identity, matching filter and a dynamically absent ID returning an empty collection.
- Web: TI_TC_001_textEntryAndClear passed; observations and three visually reviewed screenshots show empty → Hello World → empty and placeholder hidden/restored. Trace ZIP integrity passed; the trace was not replayed.
- Both native XML inventories, timestamps within their execution windows, report hashes and source/profile hashes match the reviewed published commit. Class-file major version 61 confirms the Java 17 target. Windows candidate CRLF versus published/runner LF explains the profile raw-byte hash difference; the runner profile hash matches actual published bytes.
- The isolated API run retained an optional config/dev.properties-not-found warning. The reviewed common.properties/system-property configuration was used; all three API assertions passed. No missing-test or skip was accepted.

Artifacts expire on 30 October 2026 on GitHub; verified ZIPs and extracted evidence are retained locally under outputs/acceptance/ws9-ci-publication-20261024/. No duplicate dispatch, unchanged rerun or application assertion relaxation was needed.

Publication also triggered existing independent workflows. Qodana passed; the broader Playwright Java Tests push run 40018268317 was still in progress at this review. Its outcome is separate from the selected 3+1 CI acceptance. The Jira/Confluence workflow was not invoked.

## Browser inspection interface — Y, 24 October 2026

User-approved receipt f84168fd returned the actual saved Text Input inspection. Original file hash and screenshot verified. This closes only browser inspection approval/result delivery; natural-language follow-up, console approval and chat-driven native test execution/export remain separate. See [browser acceptance details](workstream-9-web-pilot.md). Selected 3+1 native CI stays Y; full release remains P.

## Saved-result follow-up correction — 24 October 2026

**Local fix Y / live answer acceptance P:** the first follow-up lost the returned inspection context. Corrected structured approval checkpoints, latest-exchange preservation and conservative saved-result routing; 140 affected offline tests pass. Restart/recover the already-failed chat from its existing JSON before a live recheck. No target test or CI was repeated. See [browser correction details](workstream-9-web-pilot.md). Earlier approval/inspection and selected API/web CI Y retain their scope.

## Saved-file proposal compatibility — 24 October 2026

The next browser source-read stopped on malformed project function output. A bounded cross-provider native-registry correction now passes 143 affected offline checks and an actual OpenRouter synthetic/public-data planning check. This is not an actual project read or browser acceptance pass; restarting and reusing the same saved-file prompt remains P. No target website/test or CI was rerun. See [current browser handoff](workstream-9-web-pilot.md).

## Actual saved-file recovery — Y, 24 October 2026

User browser response successfully read/cited the existing inspection JSON lines 1–30 and correctly interpreted the Text Input field. This closes the actual saved-file read/recovery gate. Context-only follow-up without another read remains P; chat-driven native execution/export and remaining release gates are unchanged. See [saved-read acceptance](workstream-9-web-pilot.md). No target website/test or CI rerun occurred.

## Current sampled browser flow — Y, 24 October 2026

The actual saved-JSON read/answer and subsequent context-only follow-up passed: correct enabled/editable meanings and exactly one observed-ID locator, with latest route direct. This supersedes the earlier pending browser read/context statements for this sample. It follows explicit saved-file recovery, not a new uninterrupted post-fix approval run. Console/native-execution/export/mobile/repair and full-release gates stay P. No new application case, test or CI run was added. See [completed browser sample](workstream-9-web-pilot.md).

## Actual console saved-source/context sample — Y, 24 October 2026

The user console trace confirms one saved-file read on the project route and a correct direct-route context-only answer with no further tool step. This closes only the console saved-source/interpretation/follow-up sample, alongside the browser Y. Controlled native execution/export and remaining investigation/mobile/full-release gates stay P. See [console evidence and limits](workstream-9-web-pilot.md). Native case counts and selected CI remain unchanged.

## Next step — remaining scope, without repeating accepted CI

Selected API/web CI is Y. The controlled fault-injection/repair/rerun workflow is also Y in an isolated fixture; no natural target defect or target-project repair was found. Full 9.8 and WS9 remain P because Android Java/iOS runtime, Firefox/Safari and physical-mobile acceptance, natural target-defect repair when a suitable failure exists, and broader core-scope gates remain open. Optional Jira stays parked. A narrower desktop Chromium/API-web preview is a candidate scope, not an accepted deployment or full release.

The new CI run repeats the selected four cases in GitHub; it does not add new coverage cases or change the historical 9.7 matrix (4 passed, 11 not run, 1 incomplete Android command). Existing WS1–WS8 release limits retain their recorded status.

## Local evidence and remaining release boundaries

Evidence root: `outputs/acceptance/ws9-ci-release-20261024/`.

- `prepared-bundle.json`, `bundle/`, `target-before.json`, `target-after.json` and `acceptance.json`: reviewed files, source preservation and pending release gates.
- `configuration.log`, `native-fixtures.log`, `native-fixtures/result.json`: actual Gradle configuration and synthetic parser checks. The initial Gradle closure compatibility failure and PowerShell fixture-argument failure are retained separately; neither executed an application test.
- `initial-tests.json`/`.log` and final `tests.json`/`.log`: the original 110-test run had one legacy compatibility error; final expanded 133-test run passed after correction. Do not pool these as independent passes.
- `wheel-final/`, `wheel-final-check.json`, `wheel-final-import.log`: final package/template verification, including the compatibility correction. Earlier wheel evidence remains historical.

Current publication evidence: `outputs/acceptance/ws9-ci-publication-20261024/{candidate.json,publication.json,dispatch.json,run.json,jobs.json,artifacts.json,acceptance.json,review.md,evidence-manifest.json,published-source/}` plus both downloaded lane ZIPs and extracted folders. Earlier `ws9-ci-release-20261024/acceptance.json` remains historical local-preparation evidence.

**Selected actual API/web CI: Y. Controlled repair workflow: Y at isolated-fixture scope. Overall 9.8/full release: P** for remaining mobile/cross-browser and core scope gates; natural target-defect repair remains unverified because no suitable real failure was available. Optional Jira stays parked. WS9 ends at 9.8. Markdown is current; the Word snapshot was not changed in this task.
