# Named conversations and shared facts

Start normally to preserve the original default history and facts:

`python -m agent.langgraph.langgraph_agent`

Within the running agent, submit `SESSION learning` followed by END to switch or create a named conversation. `SESSION CURRENT` displays the active name and scope. `SESSION default` returns to the original conversation. Session names are case-sensitive. Switching does not delete anything. Resume a named session on startup with `--session learning`.

Conversations have separate checkpoint history. REMEMBER/SHOW MEMORY facts are shared by sessions using the same user and memory space. Existing facts remain in the default space `project` for user `local-user`.

To isolate another project's facts and histories, start with `--memory-space another-project --session learning`. This changes the memory scope, NOT AI_PROJECT_ROOT or Jira configuration. The seed file is imported for each new user/memory space; customize it if it should not apply there.

Jira proposals and receipts remain scoped to the configured Jira site/project/root, shared across conversation sessions. This is local organization, not authentication or a multi-user security boundary. Do not run simultaneous interactive processes against the same checkpoint thread.
