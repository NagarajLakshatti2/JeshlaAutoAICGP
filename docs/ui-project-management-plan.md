# Projects — multi-project workspace plan

## Smart Projects implementation — 24 October 2026

This checkpoint supersedes the older sidebar/General selector design. The user approved one Projects menu beside Chat, removed Recent projects/General/View all, and subsequently required free-only operation. New MCP functionality is explicitly parked.

| Status | Scope |
| --- | --- |
| **Y** | One composer Projects picker with All/Local/Git filters, clickable saved names, active project context/path, separate Add project setup, and a full-width mobile sheet. No Recent projects section or General selector. |
| **Y** | New chat and Search chats share one sidebar row; the common chat list scrolls independently of fixed Memory/Settings. First load and project switching show an empty conversation; old chats open only by explicit selection. |
| **Y** | Local folder browser navigates folders/drives on the server computer; selecting a folder preserves setup fields. Existing local folders are registered without copying or modifying source. |
| **Y — scoped** | GitHub.com/GitLab.com HTTPS clone or attach-existing-checkout setup. Git account choice is separate from project selection. Anonymous public sample clone passed without any account, registry insertion or push. |
| **Y — scoped** | Explicit sync is fast-forward only and refuses local changes or changed repository identity. A real temporary local bare-repository test verifies clone, update and dirty-worktree protection. No automatic sync/push on selection. |
| **Y — scoped** | Git account configuration supports environment credentials and Windows user-bound encrypted access tokens; explicit account test/disconnect and per-repository account replacement. Tests verify encryption, ownership and absence of tokens from process arguments/public metadata. |
| **P** | Actual private GitHub/GitLab authentication and the user's own browser/project acceptance need their credentials/environment. No real account was connected by the agent. |
| **P — PARKED** | Jira MCP, GitHub MCP, custom MCP servers and MCP project assignments are disabled design controls under Settings → Connections. Free access is unconfirmed. New MCP service entry points reject calls; no MCP test or paid service was activated. Existing console/Jira integration and model-provider configuration were left unchanged. |

Verification: **44 focused offline tests passed**, plus actual desktop/mobile Chromium layout and click checks. Tests cover chats, attachments, memory, settings, scoped approvals/downloads, project isolation, empty-start/switch behavior, folder browsing, additive migration, credentials and Git. Syntax and whitespace checks passed. This is scoped UI/workspace acceptance, not full WS8/WS9 or all-provider/browser-engine acceptance.

Evidence/backups: `outputs/acceptance/projects-smart-ui-20261024/`. Initial fixture assertion/Windows cleanup failures and intermediate logs are retained. Final Git operations disable background monitoring/maintenance; fixture SQLite handles are explicitly closed. No user project was registered, no user account authenticated, no model-provider request made, and no remote push performed.

To use: restart Streamlit once with the existing base path, then Projects → Add project → Local or Git repositories. Private repositories use Settings → Connections → Add Git account first. Local folders belong to the machine running the server. MCP stays parked.


Status **P — local foundation implemented; live acceptance and broader UI/integrations pending**. Requirements originally captured 18 October; expanded 24 October 2026. The design preview and scoped implementation checkpoint below supersede the earlier planning-only record. No real project was automatically registered; no account connection, clone or repository write was performed.

## Required user flows

- X: add an existing local project folder through the UI, validate access and display the active inspection boundary.
- X: configure project settings and switch projects deliberately, keeping project-specific context and permissions distinguishable from shared user memory.
- X: create a new project from the agent after reviewing its location, structure and proposed files; use existing exact-action approval controls.
- X: configure access to a GitHub repository for the selected project, including choosing an existing local checkout or planning a clone workflow.
- X: display local folder and repository identity, access status and available read/write capabilities clearly.

## Design constraints for later implementation

Project context must come from explicit user selection and validated configuration, not hardcoded folders or unverified memory. Define project identity and memory/chat scope before enabling switching; never imply that existing shared facts are automatically isolated per repository. Store credentials through an appropriate local/host secret mechanism, never in chat transcripts or logs. Separate read access from explicit authorized write/push/PR actions. Do not silently publish local state or reuse action approval across a different project root. New-project creation must respect path validation, overwrite protection and existing receipt controls.

Local folder access belongs to the machine running the agent; a hosted browser cannot directly browse an arbitrary D drive on another computer. Choose appropriate folder-selection, upload or checkout flows for the deployment environment. Exact GitHub capabilities and authentication must be designed and verified later; this requirement does not authorize connecting accounts or writing to GitHub now.

## Relationship to existing work

Current code supports an explicitly supplied inspection root, validated local tools and exact-action approval. A full Projects UI, reusable per-project configuration, new-project workflow and GitHub repository management are not claimed implemented. This plan extends the screenshot-inspired Projects navigation and is scheduled after the initial UI work, before any scope expansion is declared complete. Selected Workstream 9 API/web work now has its own scoped acceptance; its mobile/repair/report-export/full-release limitations remain tracked in the existing roadmap. Project management is a separate capability and does not turn those P statuses into Y.


## Multi-project behavior requested 24 October 2026

Recommended navigation name: **Projects**. Keep Chat as the conversation mode. Replace the Cowork placeholder with project selection/navigation when this capability is implemented; selecting a project chooses a context and action boundary, not a different response model. Existing app branding stays independent.

A project has a stable generated ID, display name, validated local working folder, optional GitHub repository/branch and settings. D:/PlayWrightDemoGradle is the user's proposed first registration, not a default baked into source. Multiple projects may be registered, renamed and selected. A GitHub-backed project may also have a local checkout; repository identity and actual action folder are shown separately. Local folders belong to the machine running the server.

### Required selection and conversation behavior

- X: sidebar Projects list with Add local project, New project and Connect GitHub entries as each capability becomes available. Show the selected project near the composer.
- X: each project has multiple named chats, project facts, summary/checkpoint context, document/evidence index and outputs associated with its stable ID and user scope.
- X: selecting project B lists/restores B chats and excludes A conversation, project memory and retrieval data. Selecting A again restores A chats. Existing chats never silently change their owning project because the selector changed.
- X: retain a General chat area and existing legacy transcripts/facts without deleting, relabelling or automatically assigning them to a repository. Cross-project/global personal preferences must be explicit; current shared namespace is not proof of per-project isolation.
- X: all file reads, test runs, exports and pending approval forms use the chat's validated project binding. Bind actions to project ID and exact working root; switching project cannot apply an old project's approval to the newly selected project. Browser sessions must not mutate process-wide configuration to switch identity.
- X: model provider selection remains independent of project identity. A provider failure does not erase local project configuration or make a failed task complete.

### Delivery order

1. **X — local project foundation:** project registry, validated Add local folder, deliberate selection, separate project chat/context/memory/evidence scopes, restart restoration and approval boundaries. Test two local projects before marking isolation Y. Preserve console behavior and legacy data; add code within existing storage/runtime/interface packages or a focused subpackage when ownership requires one.
2. **X — GitHub project attachment:** connect a repository and choose its branch/working copy; begin with inspection/read access. Design authentication and supported deployment behavior before implementation. No account connection is authorized merely by this planning record.
3. **X — project creation and controlled changes:** review generated structure/files in a chosen destination; preserve overwrite protection, existing action receipts and deliberate write/push/PR approvals. Never silently publish a project.

The local-project foundation can start independently of hosted-provider quota/output limitations. AI analysis and model-driven actions still require a provider capable of completing the request; project selection does not provide extra tokens.

### Current prerequisite and parked evidence

The 24 October report-export request now reached the project route, but no complete model response was available: OpenRouter OUTPUT_LIMIT, Groq RATE_LIMIT, Gemini OUTPUT_LIMIT. Actual three-case API execution remains Y; actual report export/download remains P. Do not rerun the accepted API tests to address provider availability. A later improvement should let approved exports reference a verified stored report instead of requiring the model to regenerate its full Markdown in a tool argument; implementation and acceptance are not claimed here.


## Local foundation checkpoint — 24 October 2026

| Status | Item |
| --- | --- |
| **Y — scoped** | Validated local project registry with generated IDs, user ownership, restart persistence and duplicate-path handling. |
| **Y — scoped** | Separate project chats, memory and checkpoint identity, tested with two folders and actual temporary LangGraph/SQLite checkpoints. Existing General data retained without migration. |
| **Y — scoped** | Selected-root validation and project-owned pending approvals/downloads; cross-project declarations/actions and evidence-folder reads rejected. |
| **Y — scoped** | Projects selector, Add local project form and restoration of per-project chat view in offline AppTest; Chat remains enabled and Cowork placeholder removed. |
| **P** | Actual user browser/provider acceptance after restarting the server and registering projects deliberately. No real project was auto-added. |
| **P** | Broader dark-theme redesign: desktop/mobile preview prepared from the user's reference, not deployed. |
| **X** | GitHub/clone/SSH, project generation, skills, interactive terminal and slash-command menus. Preview marks unavailable items Planned. |
| **X** | Per-project indexed-document collections and Jira connections. These paths currently fail closed and do not use General indexes/authentication. |

Validation evidence: outputs/acceptance/projects-foundation-20261024. Broad run: 151 passed out of 152 with one 15-second UI-harness timeout, retained. Latest 11 Projects checks passed; final two UI checks passed with a bounded 30-second cold-start allowance. All changed Python files parse and whitespace checks pass. This is not all-provider, device, full-suite or WS9 release acceptance. Earlier planning X bullets are historical scope; the component table above is current.
