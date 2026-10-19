# Workstream 6 Controlled actions

Overall: Y — current local-core acceptance complete. Remaining: 0 P, 0 I, 0 X.

## Durable local receipts implemented

agent/local_action_receipts.py stores SQLite receipts under outputs/local_actions.sqlite3. The project node routes create_file, replace_text, run_command, run_python_file and run_tests_and_parse through this store. Read-only tools retain their previous flow. The console displays the exact resolved project root, action, and default-expanded arguments before approval. Browser requests now queue a durable proposal and stop with awaiting_input; no console approval is requested from the browser.

A durable running claim commits before the handler executes. Reusing a completed receipt returns its stored result without executing again. Running/uncertain receipts block replay, including after a store reopen. Cancellation, exceptions and timeouts retain an uncertain receipt. An uncertain identical request is rejected before another approval prompt. A changed argument/root cannot reuse an existing receipt. File targets are hashed before approval and checked again afterward; changed targets require fresh review.

Fresh explicit approval can intentionally repeat an already completed action. The graph currently requests a fresh receipt for each newly approved operation; it does not automatically resume an earlier receipt after restart. No automatic uncertain-receipt clearing or retry is provided. Review actual effects before resolving uncertainty; do not delete receipts merely to retry.

## Verified scope

300 full offline tests passed, including 13 new receipt and real project-loop tests: decline/no write, stored-result replay after reopen, changed arguments/root rejection, cancellation after a real temporary write, timeout, approval mutation, target mutation, concurrent same-token execution, excluded paths, fresh intentional repeat, approved project create/readback, browser-style decline, and changed-target project stop. No live commands, private project edits, hosted model requests or Jira writes were needed for this acceptance.

## Limits and next work

The ledger is execution control, not an operating-system sandbox. Approved Python/build commands can execute project code with the user's OS permissions; dependency or project changes are not fully snapshotted. File hashes do not eliminate every filesystem race. Uncertain-operation blocking matches the exact root/action/arguments; it is not semantic duplicate detection. A completed command receipt proves the command returned, not that its exit code or tests passed. Historical actions performed before these receipts existed are not retroactively journaled.

I: exact-action browser proposal/review/approve/decline UI implemented and AppTest verified; real browser acceptance remains pending.
I: broader replay, restart and uncertain-outcome coverage across all supported actions and interfaces; first local receipt milestone verified.
P: release-wide permission/scope matrix and enforcement acceptance.


## 18 October 2026 Browser approval controls

agent/browser_actions.py stores proposals by user, memory space and chat. agent/browser_action_ui.py displays the exact project root, action and default-expanded arguments, with Approve exact action and Decline controls. agent/browser_backend.py queues proposals from the project node, then executes stored approved actions directly through the receipt ledger without regenerating them through the model. The UI refreshes pending proposals without resubmitting the user message.

Proposals expire after ten minutes; expiration is also checked when consuming approval. A changed file target requires a fresh proposal. The decision is atomically consumed before execution. Duplicate approval returns the saved receipt without a second action or duplicate transcript append. Interrupted execution remains uncertain. Browser approval does not automatically continue a multi-action model plan: only the displayed action runs, then another message can continue the work.

312 full offline tests passed in 10.77 seconds. Twelve additional browser tests cover scoped isolation, store reopen, real temporary-file create/decline, repeated approval, expiry, changed target, stored-argument tamper, interruption, backend model-free execution, UI refresh/chat switching, explicit approval/decline, and new-message proposal display without resubmission. The new metadata-only action events contain no content or raw arguments. No hosted request or private-project action was needed for these tests.

Local server health was not confirmed reachable. Start from the project root with python -m streamlit run streamlit_app.py --server.address 127.0.0.1. Real browser create/review/approve/decline/reopen acceptance remains I, as does broader action-kind replay coverage. Release-wide permission/scope acceptance remains P. This does not change OS sandbox limitations or authorize actions from history/tool text.


## 18 October 2026 Groq project-proposal HTTP 400 correction

The browser create-file attempt failed with TOOL_OUTPUT HTTP 400 before an action/proposal executed. Project requests now explicitly select the registered submit_project_action function and disable parallel tool calls on Groq, using the provider-documented tool_choice control. Existing project system instructions and native-proposal guidance are combined. A rejected TOOL_OUTPUT response receives at most one format correction; raw failed-generation bodies are neither displayed nor used as executable proposals. Authentication and quota errors do not receive this correction. Other providers retain their previous request-selection behavior.

Two live Groq runs through the actual project node with synthetic temporary roots produced one correct create_file proposal each, returned awaiting_input, and left the requested file absent. This is sampled recovery evidence, not a guarantee every generated call will comply. 317 full offline tests pass, including five new format/transport regressions. Evidence: outputs/acceptance/groq-browser-proposal-fix.json and groq-proposal-fix-offline.log. Actual user-browser approval acceptance remains pending; Workstream 6 remains 1 P, 2 I, 0 X.

Official reference: https://console.groq.com/docs/tool-use/local-tool-calling


## 18 October 2026 Repeated Groq proposal-shape rejection

The user retry reached the updated parser but still failed its single registered-wrapper check. Saved-chat export to Groq for diagnosis was rejected by automatic approval review because it could contain private project details; that command did not run. Diagnosis continued with synthetic contexts only. The exact returned call shape from the real failed chat remains unconfirmed.

Groq-only bounded correction now switches from submit_project_action to native action functions derived from the registered ProjectTools handler signatures. The fallback requires a tool and disables parallel calls. Its returned name must be registered in that request; missing/extra argument keys, multiple calls and unknown functions are rejected. Existing project binding, file validation, receipt protection and exact browser approval still control execution. No rejected first response is executed or reinterpreted as an approved action. At most two proposal requests occur; quota/authentication behavior and other providers remain unchanged.

Two live fallback samples injected the initial wrapper rejection, then called real Groq with native schemas, once with synthetic previous-error history. Both returned one correct create_file proposal and awaiting_input; neither created the requested file. This verifies the correction path on synthetic data, not success in the user's browser. Full offline suite: 320 tests passed in 30.595 seconds. Evidence: outputs/acceptance/groq-native-fallback-live.json and groq-native-fallback-offline.log. Workstream 6 remains 1 P, 2 I, 0 X.


18 October 2026: User browser approval succeeded. Read-only verification confirms outputs/browser-approval-check.txt is exactly Browser approval test passed. (29 bytes); action receipt 62ae989f11b8428190856ab38bc5dcac and browser proposal both completed. This verifies live create/review/approve only, not decline or refresh/reopen. W6 remains 1 P/2 I/0 X. No repeated action or extra file write was performed for verification.


18 October 2026: Live browser decline verified. User clicked Decline; outputs/browser-decline-check.txt is absent, proposal 03ef48a6ea3e49bcb9a0bfe4ec2525e4 is declined, and no execution receipt exists. Live create/approve and decline now pass for this sample. Refresh/reopen acceptance remains pending. Workstream 6 remains 1 P, 2 I, 0 X until that check and broader replay/scope acceptance finish.


18 October 2026: Scoped live browser approval milestone Y. User refreshed/reloaded default, switched chats and returned; read-only verification shows approved content exact and receipt/proposal completed, declined file absent with declined proposal and no execution receipt. This is page refresh/chat switching, not server restart. W6 now 1 P/1 I/0 X; broader replay/restart and release-wide permissions remain pending. Evidence: outputs/acceptance/browser-actions-live-summary.json.


## 18 October 2026 Local-core acceptance completed

All Workstream 6 checklist items are Y within the trusted local-user scope. agent/tool_policy.py classifies six read-only project tools and five controlled actions, plus eleven read/advisory conversation tools and the memory-proposal queue. The project registry uses that policy; conversation registry drift fails before any model request. See workstream-6-permissions.md for the per-tool matrix and limits.

New tests cover all five action kinds for approval/decline, cancellation, saved-receipt replay, and new-process completion/hard-exit blocking. Browser dispatch is verified for all five kinds with simulated handlers; browser completed/declined and hard-exit cases are reopened in fresh processes. A receipt finalization/cleanup write failure leaves its committed running claim and blocks repeat execution. Harmless real Python script and command fixtures returned successfully and replayed from receipts without execution. User-operated browser create/approve, decline and page-refresh/chat switching remain the live UI evidence.

Validation: 331 full offline tests passed before the final conversation-registry check; 21 affected registry/conversation regressions passed afterward, including the two newly added policy cases. A broader repeat was interrupted due to machine slowness. The first focused invocation had a test import-path error; the corrected final run passed. No full 333-test run is claimed. Logs: workstream-6-core-acceptance.log and workstream-6-focused-registry-final.log under outputs/acceptance.

This verifies permission and receipt mechanisms, not arbitrary command semantics, OS containment, process-tree termination, rollback or semantic duplicate detection for changed arguments. Each genuinely new approved intent can run again. Uncertain identical intents remain blocked for review. Jira/framework integration, general reliability and core release acceptance remain outside this completion. Next: Workstream 7 reliability.
