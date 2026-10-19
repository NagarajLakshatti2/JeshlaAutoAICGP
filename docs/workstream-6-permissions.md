# Workstream 6 Core tool permissions

Scope: the current single-user local console and Streamlit agent. This is an application approval boundary, not an operating-system sandbox or a multi-user authentication system. Final test evidence is recorded in workstream-6-actions.md.

## Project tools

| Tool | Class | Required control | Scope and practical limit |
|---|---|---|---|
| list_files | Read | Relative folder validation | Configured project root; excluded directories and symlinks skipped |
| read_file and read_files | Read | Relative path, extension and read bounds | Resolved path stays inside root; known environment/credential paths excluded |
| search_text | Read | Scoped traversal and result bounds | Allowed project text files; not a universal secret scanner |
| parse_test_results | Read | Report path and format validation | Report under configured root; reading a report does not execute tests |
| discover_feature_mappings | Read | Root-scoped source discovery | Reads features/tags; does not write Jira |
| create_file | Controlled write | Exact root/action/arguments approval and durable receipt | Relative allowed text path; exclusive create; existing file is not overwritten |
| replace_text | Controlled write | Current-file read in project loop, exact approval, target hash and receipt | One exact match; root/path checks; hash checks do not eliminate every OS race |
| run_python_file | Controlled execution | Current-file read, exact approval, target hash and receipt | Python source inside root; process has normal OS permissions |
| run_command | Controlled execution | Exact command/root/defaults approval and receipt | Executable allowlist, argv validation, shell=False, timeouts; cwd is not OS containment |
| run_tests_and_parse | Controlled execution | Exact command/report-folder/defaults approval and receipt | Validated report folder; fresh-report association; command exit and report results remain separate evidence |

The project registry and controlled-action set share agent/tool_policy.py. New project tools must be explicitly classified before the project loop exposes them. Low-level ProjectTools library methods are not independently an approval service; the console and browser agent entry points enforce the boundary.

## Conversation and memory tools

| Group | Class | Boundary |
|---|---|---|
| list_files, read_file, search_text | Read | Configured root and normal source-tool validation |
| list_tables, search_table | Read | Root-scoped CSV/XLSX with sheet/header/row/output bounds |
| search_documents | Read | Selected local index and bounded returned references; index freshness is not guaranteed |
| web_search, fetch_web_page | Public read | Static public-source retrieval and URL/IP safeguards; not approval for arbitrary code |
| search_memory, review_memory | Read/advisory | Configured user/namespace; candidates do not automatically correct saved facts |
| search_chats | Read | Current-chat scope by default; other-chat requests stay within configured user/space |
| suggest_memory | Proposal queue only | Candidate is not a saved fact; separate explicit user acceptance is required |
| REMEMBER/FORGET and memory acceptance/revision commands | Explicit user command | Scoped memory mutation; model tools cannot accept their own proposal |

Conversation tool names must match the classified registry before any model request. Unclassified or duplicate tools fail closed. Write/command execution is not exposed in the ordinary conversation tool list.

## Browser approvals and replay

Proposals are bound to user, memory space, chat, root, action and default-expanded arguments. Review displays the stored action. Approval consumes that proposal before executing it directly; no LLM regeneration occurs. Decline cannot execute. Expiry, changed file targets, stored-argument tampering and scope mismatch reject approval. A repeated completed receipt returns its stored result; running/uncertain receipts block execution. Fresh explicit approval can intentionally repeat an already completed operation.

Hard process exits and failed completion-record writes preserve a running claim. They do not prove which effects completed, and they never authorize automatic replay. Review the actual effects and receipt; deleting a journal is not a recovery procedure. These controls cannot undo effects, guarantee process-tree termination, or contain arbitrary approved Python/build code.

The app is intended to bind to 127.0.0.1 for the trusted local user. Namespace separation is not login authentication. Do not describe this local configuration as a public multi-user service. Jira's separate exact-plan approval and uncertainty receipts remain legacy framework functionality; these browser action buttons do not grant Jira approval or complete framework integration.

## Acceptance scope

Existing regressions cover web URL/IP guards, table/source paths, memory/chat namespaces and exact approval. New matrix tests cover all five controlled kinds for decline, cancellation, stored-result replay, fresh-process completion and hard-exit blocking; browser dispatch and duplicate approval are checked for each kind. Browser fresh-process tests cover completed/declined states and a hard exit. Harmless real Python script/command tests verify command receipt integration. Simulated handlers test the permission/receipt boundary; they do not certify every Gradle/Maven/npm command or external side effect.
