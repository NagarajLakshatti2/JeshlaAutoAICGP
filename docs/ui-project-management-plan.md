# Future Projects UI requirements

Status X. Captured 18 October 2026. User explicitly requested planning only; no UI, GitHub connection, repository operation or project creation now.

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

Current code supports an explicitly supplied inspection root, validated local tools and exact-action approval. A full Projects UI, reusable per-project configuration, new-project workflow and GitHub repository management are not claimed implemented. This plan extends the screenshot-inspired Projects navigation and is scheduled after the initial UI work, before any scope expansion is declared complete. Existing automation-framework Workstream 9 remains separately deferred.
