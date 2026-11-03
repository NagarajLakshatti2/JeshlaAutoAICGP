# T31 — proposed specialist categories and naming

Recorded from the user's screenshot/reference on **3 November 2026**.

**Status: X — deferred requirement/design only. Do not implement or rename now.** This extends existing T31, not a new task number. The course screenshot is an organizational example, not an instruction to adopt its framework, class names or implementation claims.

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
