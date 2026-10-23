# WS9 9.8 — Scoped CI and release acceptance

**Overall: P. Y for local CI preparation/validation; P for publication, actual remote execution and release acceptance.** Updated 24 October 2026.

This is the last numbered WS9 stage (9.0–9.8). Preparing a workflow is not a successful CI run. Existing agent CI and target-application CI are different evidence scopes.

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
| **P** | Publish the reviewed target files, including the previously untracked selected web class, on the workflow/default branch. No commit or push was performed. |
| **P** | Run the new target workflow once and obtain same-commit API and web job results, native XML, response captures, screenshots/trace and acceptance metadata. No dispatch/remote run was performed. |
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
4. Existing selected source `D:/PlayWrightDemoGradle/src/test/java/tests/web/TextInputAgentPilotTest.java` was still untracked locally during this inspection and must be included for a fresh checkout to work.

The API pilot class was already tracked. Existing target `build.gradle`, ConfigReader, both selected Java sources, `testng.xml` and the original Playwright workflow were checked before/after and remained byte-identical. Build cache files are not part of the reviewed publication set. The new mobile source tree is outside this API/web workflow.

## What the prepared workflow does

- Manual `workflow_dispatch` only, read-only repository contents, checkout credentials not persisted, two separate Ubuntu jobs (`api`, `web`), explicit job/test deadlines and artifact upload on completion/failure.
- Reuses target dependency-version declarations and Java 17 bytecode. Dedicated source sets compile the selected API/ConfigReader or web class. It does not invoke the default broad TestNG/Cucumber suite, ReportPortal listeners, Jira/Confluence, mobile, GitHub writes, Ollama or hosted AI providers.
- Checks the four reviewed source/build text digests. UTF-8 BOM stripping and LF normalization allow Windows/Linux checkout differences without permitting source-text changes. Raw artifact/profile digests remain separate. A real source change requires a newly reviewed profile; the workflow does not auto-update expected hashes or weaken assertions.
- Installs only the matching Playwright Chromium runtime and OS dependencies for the web job. Resolves its reviewed HTTPS host to public addresses and pins one public IPv4 address. Local/private/nonpublic resolution fails explicitly. The fixed web locator/data are the previously inspected and accepted pilot inputs; uniqueness/type/value assertions remain intact.
- Runs exactly the three accepted API methods or one accepted web method. Prevents cached/stale test-result reuse, checks one exact native class XML inventory with zero skips/failures, and requires the selected response/browser artifacts.
- Writes per-lane source/profile/commit/run metadata and scoped acceptance/summary files. A task failure, missing report, timeout or incomplete evidence cannot produce Y. Missing evidence on an interrupted runner remains unaccepted; artifact upload alone is not a pass.

The browser/OS dependency setup follows [Playwright Java CI guidance](https://playwright.dev/java/docs/ci) and the [Chromium installation documentation](https://playwright.dev/java/docs/browsers). Workflow permissions and manual dispatch follow [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Next user action — publish and run once

1. Review the four target files listed above and publish them through your normal Git workflow to the target repository. Keep unrelated `.gradle` cache changes and private local output out of this review. The prepared three-file bundle is also retained under `outputs/acceptance/ws9-ci-release-20261024/bundle/` in the AI project.
2. Ensure the new workflow is present on the repository's default branch. GitHub requires that for the manual workflow entry; see [manual workflow instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). Local `origin/HEAD` pointed to master during inspection; that cached local reference is not independent verification of the current server default branch.
3. Open [target repository Actions](https://github.com/NagarajLakshatti2/PlayWrightDemoGradle/actions), select **WS9 selected API and web pilots**, and choose **Run workflow** once for the reviewed commit. Do not choose the separate Jira/Confluence workflow.
4. Review both jobs and download `ws9-api-<run-id>-<attempt>` / `ws9-web-<run-id>-<attempt>`. Provide the workflow-run URL and those actual results for acceptance review. A green agent-unit workflow, skipped job or absent artifact does not close this gate.

The target's existing broader Playwright workflow already reacts to pushes/pull requests, and Qodana reacts to master pushes/pull requests. Those existing triggers were left intact, so publication may also start those independent checks. The separate Jira/Confluence workflow is manual; this new workflow does not call it. The selected pilot needs no model-provider or Jira secrets.

No new application run or CI publication was performed locally just to refresh already accepted API/web results. Their earlier local Y scope and the honest 9.7 report (4 passed, 11 not run, 1 incomplete Android command) remain unchanged.

## Local evidence and remaining release boundaries

Evidence root: `outputs/acceptance/ws9-ci-release-20261024/`.

- `prepared-bundle.json`, `bundle/`, `target-before.json`, `target-after.json` and `acceptance.json`: reviewed files, source preservation and pending release gates.
- `configuration.log`, `native-fixtures.log`, `native-fixtures/result.json`: actual Gradle configuration and synthetic parser checks. The initial Gradle closure compatibility failure and PowerShell fixture-argument failure are retained separately; neither executed an application test.
- `initial-tests.json`/`.log` and final `tests.json`/`.log`: the original 110-test run had one legacy compatibility error; final expanded 133-test run passed after correction. Do not pool these as independent passes.
- `wheel-final/`, `wheel-final-check.json`, `wheel-final-import.log`: final package/template verification, including the compatibility correction. Earlier wheel evidence remains historical.

**9.8 stays P** until actual target CI evidence and release scope are reviewed. Mobile/iOS and reviewed-repair blockers are not silently waived. Optional Jira remains parked. No further numbered WS9 stage is invented; the next task is to obtain and review this stage's actual CI results.
