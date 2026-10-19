# Workstream 8 core agent release

Overall I. Started 18 October 2026. This prepares a trusted local-user release; it does not start automation-framework development.

- Y: root README refreshed for current interfaces, providers, persistent state and startup. Original retained under docs/history.
- P: clean installation parked after a network-free dry-run found no local langchain distribution. Installed pip check passes, but fresh install is unverified. No dependency downloads or environment changes performed. Source-based core/document/RAG declarations audited in dependency-audit.md; optional integration compatibility and version locking remain unverified.
- Y: scoped synthetic stopped-writer core-store recovery rehearsal passes: facts, chats, history/summary and action receipts; actual user-data and optional RAG-index restore are not claimed.
- Y: reviewed integrated core acceptance against evidence and parked gaps; see core-release-review.md. This completes the review, not every acceptance gate.
- P: concrete proposed preview scope and limitations prepared in core-release-review.md; user agreement and fresh-install evidence remain pending.
- X: mark general AI-agent release complete only after required gates pass.

Known parked gaps: Workstream 2 actual-history summary quality/isolation; Workstream 3 broader semantic recall/conflict quality; Workstream 4 broader retrieval relevance/entailment/hybrid quality. Workstream 7 has scoped acceptance, not universal live-provider reliability. UI improvements are proposed for after the release gate and before Workstream 9. Word status synchronization remains pending for this release-preparation slice.

Evidence: tests/test_backup_recovery.py passed (1 scenario with all core stores). Offline install availability probe: outputs/acceptance/workstream-8-offline-install-probe.log. A missing package in no-index mode is not evidence of package incompatibility; it means this probe cannot perform clean-install acceptance. Receipt identities remain bound to the original project root after relocation; never rewrite them to bypass that check.

## Dependency declaration milestone

Added the eight missing document/table/vector/keyword adapter distributions without changing installed packages. Optional existing Jira/MCP imports have a separate requirements-integrations.txt. Installed metadata confirms 16/16 audited distributions present, and pip check reports no broken requirements. Evidence: outputs/acceptance/workstream-8-dependency-audit.json. These checks do not replace the parked clean-install acceptance or validate model/index loading.

## Connected clean-install attempt on 18 October 2026

Created a fresh disposable Windows Python 3.14.0 environment without system-site-packages and attempted current requirements from the package index. Resolution/download progressed to package installation, but the pip attempt reached the explicit 180-second cap (187.88 seconds including environment creation). Fresh-environment pip check and import smoke did not run. No package compatibility error was established, and installation acceptance remains P. The disposable environment was cleaned up; working environment and user state were unchanged. Download cache may have changed; no embedding model ingestion was run.

Reports: outputs/acceptance/workstream-8-clean-install.json and workstream-8-clean-install.log. Do not automatically repeat this full install. Next choose a longer explicitly bounded clean-install run or prepare a smaller core installation profile while retaining optional RAG dependencies. Neither option changes the parked full-release quality gates.

## Core setup separation and acceptance

Y for profile separation and scoped clean core setup. All four isolated steps passed in 80.23 seconds on Windows Python 3.14.0: requirements-core installation, pip check, console --help and browser initial rendering. RAG/document/index features are optional through requirements-rag; requirements.txt retains the full previous dependency set. Full-profile installation remains P after its timeout; fresh-core end-to-end task/regression acceptance is still pending. Evidence workstream-8-core-install.json. No existing environment/state was changed and no provider calls ran.

## Fresh core end-to-end acceptance

18 October 2026: a new disposable core-only environment installed successfully, passed pip check and passed 71 selected offline tests in 12.872 seconds (117.7 seconds total setup/run). Modules: chat_catalog, chat_runtime, local_action_receipts, browser_actions, browser_action_ui, streamlit_ui, foundation_errors, backup_recovery, conversation_sources and model_budget. Only Python source was copied; no real configuration, state, indexes or user receipts. Provider requests were blocked/mocked. Reports: outputs/acceptance/workstream-8-core-e2e.json and workstream-8-core-e2e.log.

Y for this synthetic core-profile acceptance; not the whole full-profile regression, real provider task or RAG ingestion. Proposed local development-preview scope is ready for user review. Full release and Workstream 9 remain pending. Preview excludes optional RAG acceptance and parked summary/semantic/grounding quality; these retain P rather than being marked completed.

## User scope agreement

18 October 2026: user agreed to the local trusted-user development-preview scope. This is not full release acceptance, public deployment approval or permission to publish user state. Workstreams 2/3/4 quality gaps, optional RAG acceptance and full release remain pending.

Git remote is configured for NagarajLakshatti2/JeshlaAutoAICGP. Local source setup was verified; a fresh GitHub clone has not been accepted or pushed in this work. Read-only audit found 59 tracked outputs/database-state paths and no tracked non-example .env files. Repository publication needs a tracked-file review before pushing; contents were not exported by this audit. A repository is not a running Python host, and local project access is limited to the machine executing the app.
