# Developer installation and package boundaries

The supported restructuring workflow uses an editable source checkout on Windows Python 3.14, keeping APPLICATION_ROOT anchored to the checkout. Existing python -m agent.langgraph.langgraph_agent and python -m streamlit run streamlit_app.py commands remain supported. The new console entry point is jeshla-auto-ai after editable installation.

```powershell
python -m pip install -e .
```

Optional profiles: `python -m pip install -e ".[rag]"` for document/retrieval packages, `[learning]` for retained learning adapters, `[integrations]` for existing Jira/MCP adapters. Requirements files remain supported; base package dependencies read requirements-core.txt. No credential, database, receipt, generated output or user document should be packaged as application data.

The current packaging milestone verifies editable installation and metadata only; it is not a new all-dependency clean-install acceptance. Core startup and regression evidence retains its stated environment/scope. A normal non-editable wheel has a different source anchor; relocated production data-root configuration and wheel deployment are not accepted by this milestone. Use editable source installation until that behavior is explicitly designed and verified.

Package boundaries: interfaces adapt user input/output; runtime coordinates turns/graph lifecycle; providers perform bounded model requests; storage persists chats; actions validate/propose/execute approved operations; memory stores scoped facts; policies apply deterministic rules; config anchors current application paths. Existing tools, RAG and integrations retain their roles. Compatibility aliases keep old imports working; avoid duplicating implementations in wrappers.

Backup remains private outside the active checkout. Do not commit .env, checkpoints, user chats or receipts. Repository tracked-state cleanup is a separate pending task; adding packaging exclusions does not untrack files or sanitize Git history.
