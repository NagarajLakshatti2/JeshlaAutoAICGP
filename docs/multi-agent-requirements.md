# T31 — proposed specialist categories and naming

Recorded from the user's screenshot/reference on **3 November 2026**.

**Status: P — architecture plan prepared, 5 November 2026.** The user resumed T31 planning. AutoGen remains the default mode and LangGraph remains selectable. Implementation, live acceptance and renaming are pending. This extends existing T31, not a new task number.

## Proposed capability categories

| Category / proposed role | Planned responsibility | Existing foundation / limitation |
| --- | --- | --- |
| Browser Automation Agent | Inspect web pages and perform approved browser/testing work. | Reuse existing inspection and web-test tools; no separate specialist agent is enabled. |
| Database Agent | Reviewed database queries and data management. | New database-agent scope; local application SQLite storage is not this capability. Define connections, read/write limits and approvals first. |
| API Agent | API inspection, testing and integration. | Reuse existing selected API adapters and saved native evidence; define the specialist role later. |
| Jira Agent | Jira reads, planning and reviewed project-management actions. | Align with parked T27/T28 and project-scoped MCP connections; do not resume them from this note. |
| File System Agent | Project browsing, scoped file reads and reviewed file operations. | Reuse existing selected-project tools and exact-action approvals. |
| Excel / Spreadsheet Agent | Spreadsheet reading and approved manipulation. | Existing upload extraction does not imply general spreadsheet automation. Define supported formats and edits before implementation. |

These labels are proposals. A category or menu item must not claim a working specialist until its actual tools, permissions and acceptance are implemented.

## Collaboration concepts to plan

- A coordinator/selector that routes the user's goal to the appropriate specialist and combines evidence into one final answer.
- Optional visual/multimodal browser specialist, inspired by the screenshot's visual web-navigation example.
- Explicit project/owner scope, bounded concurrency/cancellation and shared budgets. Provider fallback remains separate from multi-agent collaboration.
- Centralized approval enforcement: specialist messages, delegated plans and handoffs cannot approve file changes, commands, Jira/Git writes or other controlled actions.
- Clear visible progress and no duplicate or overlapping final explanations.

## Deferred naming review

Review capability categories, role names, UI labels and package/subpackage placement together. Map current functionality before proposing renames. Keep the JeshlaAutoAI project name and current imports/entry points unchanged until an explicit naming decision and implementation scope are agreed. Any later relocation must preserve existing behavior and compatibility.

No files/classes/packages/UI labels were renamed, no new specialist or coordinator was enabled, and no service or MCP connection was configured while recording this requirement. No extra task ID or status-count change is introduced.

## AutoGen implementation plan — 5 November 2026

Use the existing isolated AutoGen worker as the orchestration foundation. Add a coordinator that selects specialists from an explicit capability registry. Start with sequential delegation; enable parallel read-only work only after scope, cancellation and budget checks pass. Keep LangGraph's current execution path selectable and reuse the shared host tool registry.

| Subtask | Status | Acceptance boundary |
| --- | --- | --- |
| T31.1 Architecture and capability mapping | Y — plan only | Existing project tools mapped to Browser, API, Jira and File System roles; Database and Spreadsheet execution remain future capabilities. |
| T31.2 Coordinator and specialist dispatch | X | Coordinator selects supported roles, preserves the user's goal and returns an explicit unsupported result for unavailable capabilities. |
| T31.3 Scoped handoff and evidence state | X | Every handoff carries trusted owner/project/chat identity, task ID, allowed capabilities, remaining budget and evidence references. Specialists cannot replace scope with model text. |
| T31.4 Budget, cancellation and approval enforcement | X | One shared provider/token/tool/time budget, bounded delegation depth, cancellation of child work and host-only action approval. Retries cannot replay completed controlled actions. |
| T31.5 Consolidated result and acceptance | X | One final answer ties claims to tool evidence, reports incomplete branches and avoids duplicate explanations. Verify both modes and project isolation before enabling the feature by default. |

Proposed package placement: coordinator, role registry and handoff contracts belong in a new `agent/orchestration` package when implementation starts. Keep provider transports in `agent/providers`, existing isolated worker code in its current package, domain tools in `agent/tools`, external clients in `integrations`, and UI rendering in `agent/interfaces`. Inspect existing package contents before creating files; do not relocate working modules as part of this task.

First implementation slice: a read-only File System specialist plus coordinator, using existing project listing/reading tools. Follow with API and Browser roles, then the existing read-only Jira capability. Database connections, spreadsheet edits and GitHub MCP remain separately gated; T29 is explicitly parked by the user. Specialist roles must not independently execute commands, approve changes or access unrelated projects.

The host validates each proposed tool call against the selected project and existing approval controls. A specialist returns findings and proposed actions; its messages never constitute approval. Provider fallback stays inside the existing provider layer and does not create additional specialist agents.

No application code, agent defaults, provider settings or project data changed while preparing this plan. Architecture preparation is complete; T31 overall remains P until implementation and acceptance finish.

## T31 status update — 6 November 2026

| Subtask | Status | Current implementation state |
| --- | --- | --- |
| T31.1 Architecture and capability mapping | Y — plan only | Capability mapping and architecture plan are recorded above. |
| T31.2 Coordinator and specialist dispatch | P — partial | Coordinator and scoped File System dispatch scaffolding exist; chat execution is not connected. |
| T31.3 Scoped handoff and evidence state | P — partial | Trusted handoff fields and validated request-scope construction exist; live specialist evidence flow is not connected. |
| T31.4 Budget, cancellation and approval enforcement | P — partial | Shared delegation and file-tool-call budgets plus cooperative cancellation checks exist in the scoped dispatch path; provider/token/time budgets, child-process cancellation and controlled-action retry enforcement remain outstanding. |
| T31.5 Consolidated result and acceptance | P — partial | Result consolidation contract exists; end-to-end acceptance across AutoGen, LangGraph and project isolation remains outstanding. |

## T31 item-by-item completion review — 6 November 2026

| Subtask | Status | Completion decision |
| --- | --- | --- |
| T31.1 Architecture and capability mapping | Y — plan complete | Role mapping, boundaries, package placement and staged implementation plan are recorded. |
| T31.2 Coordinator and specialist dispatch | Y — complete for initial File System slice | Selected-project `list_files` and `read_file` calls in the shared conversation runtime dispatch through the File System coordinator. The original goal and host-validated project scope are preserved; unavailable capabilities return unsupported. |
| T31.3 Scoped handoff and evidence state | Y — complete for initial File System slice | Host-validated owner/project identity, chat/task IDs, capability and budget travel with dispatch. The host records task-scoped SHA-256 references for actual list/read results and returns them with tool results. |
| T31.4 Budget, cancellation and approval enforcement | Y — complete for initial read-only slice | One per-turn shared budget charges provider calls, estimated tokens, file-tool calls, delegations and elapsed time. Cancellation checks surround bounded reads. Specialist scope contains no controlled actions; approval remains host-only. Token accounting is an estimate and cannot interrupt an in-flight synchronous read. |
| T31.5 Consolidated result and acceptance | Y — accepted for initial File System slice | Final selected-project answers use host evidence references, deduplicate claims and expose incomplete branches. Focused acceptance covers both mode selections and project path isolation. |

T31.1–T31.5 are Y for the accepted initial read-only File System slice. T31 overall remains P while the planned API, Browser and Jira specialist slices are implemented and accepted. AutoGen remains the default mode and LangGraph remains selectable. Database and Spreadsheet execution remain separately deferred; T29 remains parked.

### Acceptance attempt — 6 November 2026

- `tests/test_conversation_sources.py`: 25 passed, 11 subtests passed.
- `tests/test_autogen_mode.py` excluding the worker JSON-mode and console-default cases: 8 passed, 2 deselected. The worker JSON-mode case stalled in this environment; the broader conversation workflow run also stalled and was stopped.
- `tests/test_orchestration_dispatch.py`, `tests/test_conversation_sources.py`, and `tests/test_autogen_mode.py` excluding its isolated AutoGen worker JSON-mode case: 42 passed, 17 subtests passed, 1 deselected. Coverage includes chat-level dispatch under both modes, API read-only search, project isolation, evidence consolidation, cancellation, budgets, unsupported capability results, and default-mode selection.
- The isolated AutoGen worker JSON-mode test and the broader conversation-workflow run stalled in this environment; focused coordination and mode-selection acceptance passed. Token use is estimated, and in-flight synchronous reads are not interruptible.

### Next capability rollout — API

The API capability is registered for explicit API-related project requests. It is limited to selected-project `list_files`, `read_file` and `search_text` calls and uses the same host evidence and budget controls. API requests, test execution, integrations and writes are not exposed through this specialist; those remain under their existing reviewed workflows. API source-inspection slice status is Y, including chat routing in both modes and scoped-search acceptance; API execution/integration remain deferred.

### Next capability rollout — Browser

Existing browser inspection runs in an isolated worker and writes inspection artifacts. It must go through the existing exact-action approval path before navigation or artifact creation; it is not exposed to the coordinator yet. Browser specialist status is X pending that approval-bound adapter and acceptance.

## Final T31 acceptance — 6 November 2026

| Requested item | Status | Accepted scope |
| --- | --- | --- |
| API specialist | Y | Selected-project API source listing, reading and search |
| Browser specialist | Y | Browser inspection proposal routed through the project host for approval of the exact navigation and artifact creation |
| Jira specialist and project scope | Y | Read-only traceability for the selected project's assigned, verified profile and Jira project key |
| Final cross-mode acceptance and status update | Y | Automated fixtures covered specialist proposals in both mode selections, project isolation, inspection worker behavior, approval receipts and Jira profile binding |

T31 is Y for this rollout. The project environment passed 66 focused tests, including the previously stalled worker JSON-mode fixture. Browser and Jira service behavior was exercised with fixtures. AutoGen is the default and LangGraph is selectable. T29 is parked.
