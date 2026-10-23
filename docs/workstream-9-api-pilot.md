# WS9 9.3 — native API pilot

Updated 23 October 2026. **Y for the selected three-case read-only API pilot.** Target project: D:/PlayWrightDemoGradle. This gate does not certify all APIs, the full target build, or a deployed agent-chat generation flow.

## Selected journey and actual results

| Case | Action and expected business result | Actual result |
|---|---|---|
| API-TC-001 | Read the selected existing user; HTTP 200 JSON, exact requested ID and nonblank identity data | Passed for user 1 |
| API-TC-002 | Filter users by that ID; exactly one record whose id/name/username/email agree with direct lookup | Passed; one matching record |
| API-TC-003 | Read the current collection, choose max ID + 1, confirm it is absent, then filter by that ID; HTTP 200 and an empty array | Passed; 10 collection entries, selected missing ID 11, zero filtered results |

The existing UserApiTest establishes user 1 as the selected positive fixture. The [official JSONPlaceholder guide](https://jsonplaceholder.typicode.com/) describes the resources and query filtering; its live user response provides the identity fields. The negative-data case tests a known absent filter value, not an invented 404/error-body contract. API base URL and selected existing user are per-run configuration; the absent ID is derived from data. There are no POST/PUT/PATCH/DELETE requests or persistence claims.

## Implementation and package ownership

- Target file added: src/test/java/tests/api/UserLookupPilotTest.java, package tests.api. Reuses config.ConfigReader, REST Assured RequestSpecification and TestNG assertions. Existing ApiClient/UserPayload placeholders and UserApiTest were not overwritten.
- AI integration: integrations/api/__init__.py and integrations/api/gradle.py. This focused subpackage owns the native API-run recipe; it does not introduce another provider, approval or report parser.
- prepare_api_pilot builds a configurable isolated Gradle source set for the selected API test plus the existing ConfigReader. It uses the target build's declared dependency versions: REST Assured 6.0.1, TestNG 7.12.0, Jackson 2.22.0. Java compilation uses release 17; actual installed runtime is JDK 25.0.1.
- Execution reuses LocalActionReceipts, ProjectTools.run_tests_and_parse and the existing fresh XML parser. Selection/recipe preparation is not approval. Exact command/root/arguments are bound to the execution receipt; no uncertain action is silently replayed.
- check_api_pilot_result requires a successful non-timeout command, a fresh complete report and exactly the selected method IDs, all passed. Exit zero, NO-SOURCE, stale/missing reports, failures, skips, truncated details or overlapping reports do not close the gate.
- tests/test_api_pilot.py verifies preparation, target preservation, bounds, report-path isolation and false-pass rejection. Combined adapter/action-policy/receipt regressions: **36 passed**, external networking blocked during these unit tests.

## Actual execution and preserved evidence

The final native run returned exit 0 and a fresh JUnit XML report containing exactly **three tests, three passed, zero failures/skips**. Five real GET response captures preserve case IDs, request paths/filter values, JSON body, HTTP status, response time and observation timestamps. The absent ID was selected from the actual collection rather than hardcoded.

Evidence: outputs/acceptance/ws9-api-pilot-20261023/completion.json; native-run-v2/{run.json,run.log,acceptance.json,responses/,TEST-tests.api.UserLookupPilotTest.xml}; action-receipts.sqlite3; authorization-scope.json; target-source-before.json; target-change.json; offline-tests.json/offline-tests.log. Original native XML is in the target project's build/ws9-api-pilot/native-run-v2/reports/xml. Future adapter runs use a digest of their evidence-folder path for isolated target report directories.

The first isolated run compiled but reported NO-SOURCE. Its zero-exit result was correctly rejected because there were no fresh tests. The cause was an output-directory binding in the generated Gradle task. The reusable adapter binds both compiled classes and source-set outputs explicitly; the corrected run then executed all three actual tests. The initial run.json/run.log and receipt remain historical, not a passing result. The later folder-digest improvement was verified offline without repeating the already-passing API requests.

## Preservation and limitations

The source hashes confirm that build.gradle, testng.xml, ConfigReader.java, UserApiTest.java and the inspected environment config are unchanged. Only one new target Java test source was added; normal Gradle cache/build outputs may change. Pre-existing target modifications/deletions were retained. No existing suite was run or changed. The isolated runtime excludes ReportPortal dependencies/listeners and passes rp.enable/rp.enabled false; it uses minimal generated resources and does not load the target's local property files as its working directory. Target reports and response captures stay in their selected evidence folders.

This is an actual native Java API test slice invoked by the current coding agent, not proof that the deployed LLM has dynamically generated the same source in a user chat. Existing controlled project execution remains reusable, but no new unattended model tool or UI feature was registered. Other endpoints, write operations, authorization, 404/error payload rules, performance contracts, full target compilation, browser/mobile workflows, CI and release acceptance remain separate. No hosted AI provider, Jira or Ollama call was made; provider configuration and Word snapshot remain unchanged.

**Next: 9.4 — the first agent-driven web workflow.** Reuse the accepted browser helper, inspect actual elements and requirement sources, preserve reviewed-change/approved-run boundaries, and verify real results. Do not repeat 9.1–9.3 acceptance without a relevant new failure.
