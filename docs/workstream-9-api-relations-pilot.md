# T22 — user/post/comment relationship pilot

1 November 2026. Y for selected API-TC-004/005 scope: approved source applied and one actual native run passed 2/2. Full T22 remains P.

This expands the existing read-only user pilot without repeating API-TC-001/002/003 or modifying its Java source/CI profile. The two selected cases compare documented nested/filter relationships and validate returned parent IDs/data. User 1 is the documented positive fixture; the post ID is derived from its actual posts. No guessed 404/authentication/write/persistence contract is introduced.

One new Java class is proposed in the existing tests.api package. The current integrations.api.gradle recipe and native-report validator are reused unchanged; no new Python file or module is needed. Java 17 compilation, 15 loopback fixture checks and 10 offline adapter regressions passed. None is a live public API acceptance result.

Exact contract, source, candidate hash, protected baseline and execution recipe are in outputs/acceptance/t22-api-relations-review-20261101/review.md, contract.json, exact-source-action.json, proposed.diff and focused-run-review.md/json. Source approval and conditional one-run approval are separate. Live scope: one class, two methods, six GETs, 150-second outer deadline, isolated reports and disabled external reporting integration. No automatic retry, accepted-scope replay, model/Jira/Git call or installation.

Existing login acceptance remains 2/3 and its empty-field application mismatch is unrelated. Full T22 and broader API/site/physical-interface/quality scopes remain P. Word is unchanged.

## Actual completion — 1 November 2026

Both approvals were granted separately. Source creation and one isolated run completed through durable receipts. Exactly API_TC_004_userPostsMatchFilter and API_TC_005_postCommentsMatchFilter passed, exit 0, no timeout/failures/skips/incomplete/configuration failures. Six saved HTTP 200 JSON responses confirmed 10 user-post records and 5 comment records for derived post 1; array ordering was not assumed. Source, recipe and 15 protected existing file hashes remained unchanged.

See outputs/acceptance/t22-api-relations-review-20261101/completion.md/json and retained native XML/responses for exact evidence. This selected slice is closed Y and must not be repeated unchanged. Earlier staged/not-run descriptions are historical. Existing accepted cases were not replayed; no model/Git/Jira/CI publication, install or Word update occurred. Broader T22 and the unrelated QPH-012 app mismatch retain P.

## Milestone reconciliation — 1 November 2026

T22 is now Y under the explicitly accepted finite scope, after QPH-020/021/022 passed 3/3 and all selected evidence reconciled. Earlier full-T22 P references are historical. This does not change the existing case results: API relationship scopes remain accepted and QPH-012 remains failed/open externally, with login native acceptance 2/3. Broader controls/sites/devices/quality are separate future work. See outputs/acceptance/t22-milestone-completion-20261101/completion.md/json. No accepted case was replayed during reconciliation.
