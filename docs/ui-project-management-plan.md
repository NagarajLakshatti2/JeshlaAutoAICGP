# Projects — multi-project workspace plan

## GitHub push parked by user — 25 October 2026

**P — PARKED BY USER.** The user explicitly stopped this task after another repository-access rejection, including an attempt with a newly selected account. Live GitHub publication is not accepted or complete. The last read-only verification observed local HEAD 5c0d28d and remote main fff508f; the user subsequently reported another failed push. These are historical observations, not a fresh remote check.

Do not retry pushes, test credentials, change permissions or continue Git push diagnostics until the user explicitly resumes this item. Preserve both local commits, the configured accounts, existing code, receipts and reconciliation history. Clone/read and local-commit acceptance retain their earlier scope. New Jira/GitHub MCP remains separately parked. No Git, network or credential operation was performed while recording this parked status.

## Audited failed-push recovery — 25 October 2026

**Y — receipt recovery; P — GitHub write permission remains blocked.** Receipt 1b58a66bf5c2477aac6299ef31315cd2 became uncertain after a rejected push. A later approval was blocked by that same fingerprint before its handler started. Read-only checks confirmed remote main still fff508f and local HEAD 5c0d28d; the reviewed commits were not currently published. The selected credential's Git write-handshake request still returned HTTP 403.

Prepare push review now reconciles only an exactly matching, owned uncertain Git push, after another authenticated read of its registered remote branch and an unchanged local-state check. It preserves the old action/fingerprint, records timestamped remote evidence in git_push_reconciliations, and labels the old proposal reconciled_not_applied. A duplicate display proposal with no durable action claim is likewise audited. Running claims, different owners/identities and changed remote/local targets are not released. Private/public repository reads use only the selected credential at the transport boundary; no token enters the audit.

Old approvals remain unusable. Only a new proposal and exact-action approval can run a later push. Other action kinds retain their existing no-replay policy. This observation establishes that the reviewed commit was absent at reconciliation time; it does not claim knowledge of every historical remote change.

**30 guarded tests passed**, including recovery without automatic publication, old-token rejection, fresh-approval execution, owner/running/changed-remote guards and existing generic receipt behavior. The real local-actions database was backed up, then the tested recovery reconciled the two affected proposal records. No user commit/push was executed and no new approval was queued. The backup and observed SHA evidence are in outputs/acceptance/git-push-recovery-20261025/.

Remaining user step: correct the GitHub fine-grained token's resource owner, selected repository and Contents read/write permission (or configure/select a corrected token); restart Streamlit and prepare a fresh Push review before approval. Disabling commit GPG signing cannot change GitHub push authorization. Existing commits remain intact. Other workstream/MCP statuses are unchanged.

## Git publication status and account selection — 25 October 2026

**Y — diagnosis, receipt-backed replies and scoped UI correction; P — hosted publication awaiting explicit account assignment/review/approval.** At diagnosis, local main had commits d7057b5 (nagatest.py) and 5c0d28d (test2.py), while a read-only public Git lookup returned remote main fff508f. No git_push proposal existed. The saved GitHub account was verified but the selected project's account_id remained empty. An earlier model answer falsely said approval would run a queued push; the receipts did not support that claim.

Push review now includes the selected provider's saved accounts and an explicit Save repository account button. Selection is persisted only for that project, clears cached review data, does not auto-select credentials and does not publish. Git status/approval follow-ups use user/project/chat-scoped action receipts: pending, expired, uncertain and confirmed states remain distinct; chat text grants no approval. A confirmed historical receipt is labelled as execution-time evidence, not a fresh remote-state check. Questions such as How does git push work? retain their explanatory route.

**30 focused guarded tests passed**, including the actual account-selection UI, two-project isolation, no-model approval follow-ups, truthful pending/uncertain/completed receipt states, normal chat/explanations, prior routing and approval behavior. Chromium desktop 1440×900 and mobile 390×844 checks passed and screenshots were inspected. Initial fixture mistakes and a status/command priority defect were corrected; intermediate logs remain in the evidence folder.

No production Git code contains this user's repository name, owner or local root. It resolves the selected project's registered URL, account, branch and reviewed commit. The existing first-slice limits still apply: GitHub.com/GitLab.com HTTPS, authorized account, conventional checkout, existing same-named branch and bounded reviewable non-merge changes; protected-branch rules still apply. This is reusable project handling, not universal support for every Git hosting/deployment/workflow variant.

Next: restart Streamlit, select the target project, request Push this branch, select NagarajLakshatti2 in Push review and Save repository account, then Prepare push review → Request exact-action approval → Approve exact action for git_push. The existing local commits need no new commit. No real user commit/push or account assignment was performed by these fixes; parked MCP and other workstream gates remain unchanged.

Evidence/backups: outputs/acceptance/git-push-status-account-20261025/. All Python changes extend existing appropriate interface/runtime/test packages; no new Python module was introduced.

## Copied Git push request correction — 25 October 2026

**Y — reproduced and fixed; P — hosted push awaiting account configuration and user approval.** Read-only receipt/repository checks confirm the user's approved local commit succeeded: d7057b5d0427d290e826fb9f15cc3ca56de2a637, message test commit, clean local working tree. The subsequent request included author/message metadata followed by quoted “Push this branch.” The previous matcher missed that positive instruction, and the model proposed run_command(command=["git","push"]). The generic runner intentionally excludes Git, but the old adapter displayed approval before command validation and then reduced the validation error to a generic provider/configuration error.

The active-text Git intent parser now recognizes copied quoted instructions, including the observed metadata-leading request, and chooses Push from actual positive commands rather than the incidental words “commit message.” Explanations, prohibitions, attached document content and file-creation-first requests keep their existing treatment. Browser Git review opens without an LLM call.

The existing command parser is shared between execution and pre-approval validation. Unsupported commands are rejected before persistence/display; legacy invalid pending approvals are blocked before receipt execution/subprocess creation, with actionable Git-review guidance. Valid Python/Gradle/test commands preserve their existing arguments and approval behavior. No unsupported Git command was enabled in the generic runner.

**42 focused guarded tests passed**, including the exact copied request through AppTest, correct Push mode, missing-account guidance, no model call, invalid proposal rejection, legacy pending proposal blocking, valid preview without execution, existing approvals/replay and project/upload routing. No visual layout changed in this fix; previous desktop/mobile layout acceptance remains scoped to its original checks.

Actual app metadata currently contains no Git accounts and the target project has no selected repository account. Restart Streamlit, configure/test a repository-authorized GitHub account in Settings → Connections → Add Git account, then select/save it in the target Project details → Repository account. Request Push this branch, prepare the review and approve the actual git_push action. Do not recommit the already committed file or retry the failed run_command action. No real commit or push was executed by this correction, no user credential was read, and existing failed/uncertain receipts were retained.

Evidence/backups: outputs/acceptance/git-push-routing-fix-20261025/. Hosted publication remains P; other workstream and parked MCP statuses are unchanged.

## Approved Git commit and push — 25 October 2026

**Y — bounded implementation and isolated acceptance; P — actual hosted GitHub/GitLab publication.** The user changed Automataion_AI_Agent_Framework from private to public and reported successful clone/local file creation. The earlier anonymous/private-clone diagnosis is retained below as history. Public visibility allows anonymous reading; publication still requires an explicitly selected account with repository write permission. This checkpoint supersedes the earlier next-step guidance for this now-public repository.

The prior request to create nagatest.py and commit/push was incorrectly answered as ordinary chat. Natural file-creation requests now route to project actions, including the observed “reate” typo. Commit/push requests for a selected saved Git project open a deterministic Git review panel without a model call. File creation, local commit and remote push remain distinct approved actions; a created file is not a published commit.

Use the browser after restarting Streamlit:
1. Select the saved Git project in Projects. Ask **Commit these changes**, or open Project details → **Review commit / push**.
2. Select only intended files, enter a commit message and your chosen author name/email, then **Prepare commit review**. Inspect the exact diff and request the actual action-approval form. **Approve exact action** performs that local commit once.
3. Configure a repository-authorized GitHub/GitLab account in Settings → Connections, then select that account in the project's details. Ask **Push this branch**, or select **Push** in the review panel.
4. **Prepare push review** reads the actual remote branch and shows all pending commits and changes. Request and approve the separate exact push action. No force-push or automatic publication is performed. Never paste a token into chat.

This first slice supports conventional local checkouts of configured GitHub.com/GitLab.com HTTPS projects, existing same-named local/remote branches, up to eight bounded UTF-8/source files per commit and up to twenty bounded, non-merge pending commits per push. Pre-staged changes, credential/generated paths, symlinks, oversized reviews, binary changes and unsupported repository states are rejected. SSH/worktrees, initial branch publication and merges are outside this slice. Commit identity is explicitly supplied; hooks/filters are not run by the commit writer. Existing generic command execution does not gain arbitrary Git access. Console publication is not enabled by this browser feature.

Exact approvals are user/project/chat scoped, expire, bind the selected content/HEAD/index/project/account, reject changed reviews and keep durable receipts. Remote state is rechecked before a non-force push and confirmed afterward. Failed/interrupted publication is reported as uncertain and is not automatically replayed. Tokens are resolved locally only at the selected-account transport boundary and do not enter review arguments or model prompts.

Validation: the 64-test regression checkpoint and five final focused checks passed. All ten final transport/guard tests also passed. Real Chromium preview checks passed at **1440×900 and 390×844**; one project panel, readable diff, contained mobile scrolling and missing-write-account guidance were verified and screenshots inspected. AppTest exercised the actual approval form and a one-time local commit. All write tests used owned temporary repositories and local bare remotes; no user repository was committed or pushed. Initial fixture/selector failures and corrections remain in the logs.

Evidence/backups: outputs/acceptance/git-approved-writes-20261025/. This is scoped Git workflow acceptance, not full WS8/WS9 release acceptance. Automatic post-run diagnosis and new Jira/GitHub MCP remain separate pending work; MCP stays parked/free-only. Existing provider configuration, user credentials and Word roadmap were not changed.

## Private Git access checkpoint — 25 October 2026

**Y — diagnosis/error-guidance correction; P — actual private clone awaiting user configuration.** The user confirmed a private repository while the form selected Public repository and the app had no Git accounts. Anonymous public clone+save and attach-existing UI checks passed in an isolated temporary workspace. New error messages distinguish anonymous/private access, rejected selected credentials and network failures without echoing remote text/secrets. The anonymous choice now reads Public repository (no account).

Next user step: save/test a GitHub account in Settings → Connections, then choose it under Repository access before one private clone to a new folder. IDE/Codex login is separate from app authentication. No real credential was requested in chat or configured by the agent.

24 focused guarded tests pass, including explicit credential propagation and project UI/isolation. Initial transient Windows fixture-cleanup error retained; the bounded owned-folder cleanup fix preserves assertions. MCP remains P — PARKED/free-only. Existing roadmap now contains the consolidated pending-enhancement audit; no Word synchronization is claimed.

Evidence/backups: `outputs/acceptance/git-private-access-20261025/`.

## Chat return and Gradle wrapper correction — 24 October 2026

**Y — scoped fixes.** Chat beside Projects is now a working button. From a selected project it restores the earlier, unscoped chat list; it leaves the main conversation empty until the user selects a saved session. Project sessions remain separate and return when that project is selected again. Clicking Chat while already in Chat does not reset an open conversation. Same-named saved projects show their folder paths to prevent selecting the wrong root.

Read-only diagnosis found 65 earlier chats in the base space, one chat in the PlayWrightDemoGradle project scope, and no chats in the separately configured LeetCode folder. Both saved projects had the same display name. No chats were deleted, migrated or assigned to a project automatically.

Windows run_command now accepts gradlew.bat and the explicit current-folder Gradle wrapper spellings as aliases for the selected project's wrapper. Approved arguments and receipt identity stay unchanged; arbitrary batch paths remain rejected. The actual saved successful execution used **-Dheadless=true** (exit 0). That hides the test browser. The target build separately opens the HTML report after tests. A later headed request used gradlew.bat and was still pending when inspected; it was not executed by this correction.

To request a visible browser in the project's normal Playwright test configuration, use **-Dheadless=false**, review a fresh exact action and approve it once. The agent does not silently flip this setting. The separate WS9 inspection/pilot code has its own headless behavior; this change does not alter those profiles or the target project.

Validation: **35 focused guarded offline tests passed**, including earlier-chat return/open behavior, separate project sessions, unchanged arguments for both headless values, wrapper/path restrictions, approvals, attachments, memory/settings and downloads. Chromium checks passed at 1440×900 and 390×844, including the restored chat list being on screen. Evidence/backups: `outputs/acceptance/chat-navigation-runner-20261024/`. No target Gradle suite, account connection or model-provider request was run.


## Saved projects panel correction — 24 October 2026

**Y — scoped UI acceptance.** Projects beside Chat opens one **Saved projects** panel containing local folders and Git repositories together. Folder/Git icons identify the source; clicking a name activates it and closes the panel, including when the same project is already active. The All/Local/Git list filters were removed.

Add project, folder browsing, project details and explicit Git sync now replace content inside that same panel. Back to saved projects returns to the list without discarding setup fields. Local/Git source choice belongs only to setup. Desktop width is compact; taller forms scroll inside the mobile viewport.

The left sidebar remains present after selection and displays only the selected project's saved sessions, identified by project name. A new project shows **No chats yet. Start with New chat.** New chat, Search chats, Memory and Settings remain available. Switching does not automatically open a conversation or delete another project's sessions.

Validation: **27 focused offline tests passed** (project switching, setup/folder navigation, chat, attachments, memory/settings, approvals and downloads). Actual Chromium checks passed at **1440×900 and 390×844**, verifying one visible dialog, no overlapping project popover, mixed saved sources, field retention, selection/close behavior and the scoped sidebar. Screenshots inspected. Evidence/backups: `outputs/acceptance/saved-projects-panel-20261024/`. Initial browser timing/height failures are retained; final visual acceptance passes.

Private-account live acceptance remains P. New MCP functionality remains **P — PARKED** under the free-only instruction. This correction makes no provider, Git service, registry schema or user-project changes, and does not change WS8/WS9 release status.


## Smart Projects implementation — 24 October 2026

This checkpoint supersedes the older sidebar/General selector design. The user approved one Projects menu beside Chat, removed Recent projects/General/View all, and subsequently required free-only operation. New MCP functionality is explicitly parked.

| Status | Scope |
| --- | --- |
| **Y** | One Saved projects panel beside Chat with a combined icon-labelled local/Git list and clickable names. Setup/folder/details/sync are views inside that same panel; no stacked picker/dialog or All/Local/Git list filters. See the correction checkpoint above. |
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
