# JeshlaAutoAI — full-project progress audit

Audit date: 17 October 2026

## Corrected conclusion

**You are beyond Phase 1.** Your original Phase 1 foundations and Phase 2 RAG implementation exist. You are currently in Phase 3: stateful conversational agents, persistent memory, sessions and integration hardening. There are also planning/ReAct/guardrail prototypes and Jira/QA integration work beyond the initial foundation.

The numbered workstreams in the newer roadmap are a completion/quality plan, not a reset of your learning progress. Existing functionality must be credited before listing remaining integration and acceptance work.

## Scope and limits

Read and parsed all 94 first-party Python files in the project tree, including examples and tests; 74 are nonempty and 20 are empty package markers. No Python syntax errors were found. Dependency/environment folders, cache files and historical backup copies were excluded from source counts. Inspected implementation details in the main RAG, memory, orchestration, integration and evaluation modules, plus stored index/report artifacts. Reviewed folder contents without opening private document contents or printing credential values.

This is a static implementation audit plus the test result below, not a claim that every module was executed successfully. Source inventory alone does not demonstrate runtime quality or correctness.

## Original phases versus release readiness

| Original milestone | Build status | Current readiness | Evidence |
|---|---|---|---|
| Phase 1: LLM foundation and basic agents | Y | P for remaining provider/configuration acceptance | Provider modules, real Groq responses, Ollama/OpenRouter experiments and single-agent examples |
| Phase 2: RAG and knowledge implementation | Y | P for current runtime validation, quality and integration | Ingestion, chunking, FAISS/BM25, hybrid retrieval, BGE reranking, structured search, saved indexes and evaluation reports |
| Phase 3: state, memory and conversational agent integration | I | P for summaries, selective recall and consolidated acceptance | LangGraph, SQLite facts/checkpoints, chat catalog/archive, native tool loop, terminal and Streamlit |
| Planning, ReAct and guardrail concepts | Y for examples | P for converting simulations into verified operational behavior | examples/agents subfolders; some tools deliberately return simulated results |
| Jira/QA integration | P | P; uncertain receipt and MCP-server gap remain | Jira MCP client, draft/approve/create workflow, mappings and execution evidence |
| Automation-framework expansion | P: parked | Deferred by user decision | Existing modules preserved; new framework development waits for core-agent acceptance |

Y = completed for the stated scope; X = not completed/not started; I = in progress; P = worked on but pending or parked.

## Implemented RAG work that must be credited

- Y: PDF/TXT/DOCX/CSV ingestion with source metadata in rag/ingest.py.
- Y: Recursive text chunking and persisted BM25/chunk artifacts.
- Y: FAISS embedding/index construction and stored indexes.
- Y: Combined FAISS semantic search and BM25 keyword search.
- Y: Duplicate-chunk removal, BGE cross-encoder reranking and source/page context.
- Y: Query rewriting, career-query handling and PDF answer export in rag/query.py.
- Y: CSV/Excel loaders, header detection, schema grouping, dataset/query routing and structured filters.
- Y: Document/structured-data tool-calling and web-plus-RAG agent scripts.
- Y: Separate hybrid, BM25, no-reranker and final evaluation implementations and saved reports.
- P: Wire existing structured-data and relevant-memory capabilities into the current native agent loop.
- P: Consolidate older OpenRouter-specific RAG entry points with the shared provider adapter where appropriate.
- P: Normalize working-directory-sensitive paths/imports so launch location does not silently change datasets/index locations.
- P: Re-evaluate the active retrieval path in the current Windows environment. A historical report records a c10.dll/PyTorch restriction; this audit did not re-test that restriction.

## Evaluation evidence and limits

The stored final RAG report records BM25 retrieval passing 7/8 and generated-answer keyword checks passing 2/8, with average keyword score 43.75%. It lists a historical Hybrid+BGE Hit@3 baseline of 8/8. The report explicitly says the hybrid numbers are a previously validated baseline, not a fresh run in the report's Windows environment. These metrics credit evaluation work while identifying quality gaps; eight questions are not a comprehensive acceptance set.

The current broad tests/ discovery ran 116 tests with 6 errors and no reported assertion failures (110 completed without errors). Several older Jira tests conflict with current creation gates or workflow behavior. One test also attempted real provider/authentication work despite an offline label. The authentication callback ended on EOF and visible creation attempts were blocked. Treat broad discovery as NOT reliably offline-isolated until fixtures are repaired. Do not weaken production Jira gates to make those tests pass. Earlier targeted tests remain useful but do not establish that this whole suite is clean.

## Important distinctions

- Planning/guarded examples contain simulated tool results, so their code demonstrates the concepts without proving real code generation, PR creation or test execution.
- agent/memory/agent_memory.py already contains embedding-based memory search. Selective semantic recall is not wholly absent; integration with the current SQLite/native-tool path remains pending.
- rag/query.py uses the shared LLM client; rag/rag_agent.py, rag/tool_calling.py and rag/web_search_agent.py still have their own OpenRouter-oriented clients.
- The active conversation tool registry includes document search and web/local-source tools, but not the existing CSV/Excel structured-search function or semantic-memory demo.
- integrations/qa_mcp/qa_mcp_server.py is only a commented import. A client script does not make that server operational.
- Root main.py is still a PyCharm greeting example; the real console entry point is agent.langgraph.langgraph_agent.
- Old backup/example modules should not be confused with the active implementation.

## Recommended next action

Continue Phase 3 integration and hardening. Preserve completed RAG modules; connect and verify them rather than rewrite them. First repair summary failures and test isolation, then source grounding, relevant-memory/archive retrieval, structured-data integration and a fresh RAG evaluation. Automation-framework expansion stays parked.

## Reviewed Python inventory

All files below were read and parsed. Lists show top-level definitions, not a line-by-line runtime proof.

| File | Lines | Definitions / role |
|---|---:|---|
| `agent/__init__.py` | 0 | Empty package marker |
| `agent/browser_backend.py` | 47 | classes: BrowserBackend; functions: make_browser_backend |
| `agent/chat_catalog.py` | 128 | classes: ChatCatalog; functions: clean_title, choose_chat, validate_chat_command |
| `agent/chat_runtime.py` | 57 | functions: session_turn_lock, run_turn |
| `agent/context_summary.py` | 63 | functions: compact_context, summary_failure_reason |
| `agent/conversation.py` | 131 | functions: web_search, tool_spec, validate_tool_arguments, answer_question |
| `agent/langgraph/__init__.py` | 0 | Empty package marker |
| `agent/langgraph/jira_workflow_node.py` | 618 | classes: Store; functions: workflow_intent, binding, exclusive, help_text, render, parse_model_json, build_request, read_story_source, draft_from_story, draft, import_draft, plan_connected, approve_connected, run_qa, review_receipts, discuss_or_revise, handle, jira_workflow_node, explain_error |
| `agent/langgraph/langgraph_agent.py` | 1050 | classes: AgentState; functions: load_long_term_memory_node, memory_command_node, show_memory_node, extract_requested_paths, parse_route_response, router_clarification_node, fast_request_route, clarify_node, feature_search_queries, router_node, route_question, prepare_prompt_node, conversational_answer_node, llm_node, search_documents, rag_node, rag_answer_node, web_node, jira_node, approve_local_action, project_node, format_result_node, session_config, restore_session, main |
| `agent/langgraph/langgraph_agent_review_fix.py` | 671 | classes: AgentState; functions: router_node, route_question, prepare_prompt_node, llm_node, search_documents, rag_node, rag_answer_node, web_node, jira_node, project_node, format_result_node, main |
| `agent/llm_client.py` | 232 | functions: validate_messages, prepare_messages, env_int, call_ollama, error_message, retry_delay, call_openrouter, call_groq, call_llm_messages, call_llm |
| `agent/memory/__init__.py` | 0 | Empty package marker |
| `agent/memory/agent_memory.py` | 177 | functions: load_memory, save_memory, write_memory, search_memory, create_state, main |
| `agent/memory/long_term_memory.py` | 196 | classes: LongTermMemory;  |
| `agent/runtime_context.py` | 11 | functions: local_action_handler |
| `agent/terminal_input.py` | 78 | functions: configure_input, make_bindings, create_editor, read_message, read_confirmation |
| `agent/timing.py` | 47 | functions: timestamp, timer, timed |
| `agent/tool_llm.py` | 85 | functions: call_tool_messages |
| `agent/tools/__init__.py` | 0 | Empty package marker |
| `agent/tools/feature_mapping.py` | 97 | functions: discover_feature_mappings, main |
| `agent/tools/project_tools.py` | 526 | classes: ProjectTools;  |
| `agent/tools/test_results.py` | 191 | functions: parse_test_results, run_tests_and_parse |
| `evaluations/__init__.py` | 0 | Empty package marker |
| `evaluations/rag_evaluation.py` | 995 | functions: bm25_search, hybrid_search, rerank_documents, source_matches, page_matches, find_expected_document, generate_answer, evaluate_keywords, evaluate_question, run_evaluation |
| `evaluations/rag_evaluation_bm25.py` | 711 | functions: bm25_search, source_matches, page_matches, find_expected_document, evaluate_keywords, generate_answer, evaluate_question, run_evaluation |
| `evaluations/rag_evaluation_final.py` | 1186 | functions: bm25_search, source_matches, page_matches, find_expected_document, generate_answer, evaluate_keywords, calculate_retrieval_metrics, evaluate_question, get_previous_hybrid_baseline, compare_bm25_hybrid, generate_final_report, save_json, main |
| `evaluations/rag_evaluation_no_reranker.py` | 782 | functions: bm25_search, hybrid_search, source_matches, page_matches, find_expected_document, generate_answer, evaluate_keywords, evaluate_question, run_evaluation |
| `examples/__init__.py` | 0 | Empty package marker |
| `examples/agents/__init__.py` | 0 | Empty package marker |
| `examples/agents/guarded/__init__.py` | 0 | Empty package marker |
| `examples/agents/guarded/guarded_agent.py` | 599 | functions: create_state, search_repository, generate_code, run_tests, fix_code, create_pr, merge_pr, validate_action, execute_tool, execute_action, approve_pending_action, run_guarded_agent |
| `examples/agents/planning/__init__.py` | 0 | Empty package marker |
| `examples/agents/planning/planning_agent.py` | 423 | functions: create_state, print_plan, get_jira_issue, inspect_repository, generate_component, run_tests, analyze_failure, fix_code, replan_after_test_failure, execute_step, run_planning_agent |
| `examples/agents/react/__init__.py` | 0 | Empty package marker |
| `examples/agents/react/react_agent.py` | 228 | functions: search_memory, web_search, execute_tool, llm_decision, run_agent |
| `examples/agents/single_agent.py` | 875 | functions: create_state, search_memory, save_memory, create_plan, print_plan, get_jira_issue, inspect_repository, generate_code, run_tests, fix_code, validate_action, execute_tool, update_state, replan_after_test_failure, process_action, decide_next_action, run_agent |
| `examples/editing/__init__.py` | 0 | Empty package marker |
| `examples/editing/check_edit_demo.py` | 22 | Top-level script or placeholder; review its folder context |
| `examples/editing/edit_demo.py` | 3 | functions: add |
| `examples/editing/generated_demo.py` | 2 | functions: multiply |
| `examples/jira/__init__.py` | 0 | Empty package marker |
| `examples/llm/__init__.py` | 0 | Empty package marker |
| `examples/llm/api/__init__.py` | 0 | Empty package marker |
| `examples/llm/api/openrouterSite/__init__.py` | 0 | Empty package marker |
| `examples/llm/api/openrouterSite/openrouterai.py` | 49 | Top-level script or placeholder; review its folder context |
| `examples/llm/api/openrouterSite/openrouteraifree.py` | 28 | Top-level script or placeholder; review its folder context |
| `examples/llm/api/openrouterSite/openrouterfree2.py` | 46 | Top-level script or placeholder; review its folder context |
| `examples/llm/api/openrouterSite/openrouterfree3.py` | 53 | Top-level script or placeholder; review its folder context |
| `examples/llm/transformersai/__init__.py` | 0 | Empty package marker |
| `examples/llm/transformersai/transformerspr.py` | 170 | Top-level script or placeholder; review its folder context |
| `integrations/__init__.py` | 0 | Empty package marker |
| `integrations/jira/__init__.py` | 0 | Empty package marker |
| `integrations/jira/feature_jira_mapping.py` | 240 | functions: normalize_title, subtask_verified, build_mapping_report, classify_issues, discover_jira_mappings, main |
| `integrations/jira/jira_mcp_client.py` | 401 | classes: InMemoryTokenStorage; functions: validate_issue_key, extract_issue_key, get_result_text, response_payloads, merge_issue_fields, decode_result, read_tool, handle_callback, jira_session, get_cloud_id, get_jira_issue, search_jira_issues, get_child_issues, fetch_jira_issue, main, handle_redirect, read_issue_hierarchy |
| `integrations/jira/qa_workflow.py` | 230 | functions: utc_now, select_mapping, assess_execution, source_hashes, save_evidence, main |
| `integrations/jira/test_case_agent.py` | 472 | classes: Blocked, JiraGateway; functions: norm, fingerprint, save, text, creation_enabled, unresolved_receipts, validate_request, validate_node, description, similar_candidates, prepare_plan, apply_plan, draft_cases, connected, main |
| `integrations/qa_mcp/__init__.py` | 2 | functions: client |
| `integrations/qa_mcp/qa_mcp_client.py` | 120 | functions: main |
| `integrations/qa_mcp/qa_mcp_server.py` | 1 | Top-level script or placeholder; review its folder context |
| `main.py` | 16 | functions: print_hi |
| `rag/__init__.py` | 0 | Empty package marker |
| `rag/chat_memory.py` | 92 | functions: load_chat_history, save_chat_history, add_chat |
| `rag/csv_search.py` | 90 | functions: load_csv_files, load_structured_data, search_csv, format_csv_results, get_structured_datasets |
| `rag/dataset_registry.py` | 572 | functions: normalize_columns, detect_dataset_type, group_datasets, detect_query_dataset |
| `rag/ingest.py` | 293 | functions: create_vector_db |
| `rag/inspect_xlsx_schemas.py` | 61 | Top-level script or placeholder; review its folder context |
| `rag/main.py` | 7 | Top-level script or placeholder; review its folder context |
| `rag/query.py` | 535 | functions: load_resources, is_career_query, rewrite_query, bm25_search, hybrid_search, rerank_documents, build_context, save_pdf, run_query, main |
| `rag/rag_agent.py` | 627 | functions: bm25_search, execute_search_documents, execute_search_structured_data, execute_tool, call_openrouter, run_agent, main |
| `rag/retrieval.py` | 189 | functions: _load_resources, bm25_search, execute_search_documents |
| `rag/structured_search.py` | 216 | functions: normalize, filter_by_skill, filter_by_experience, filter_by_role, filter_by_project, structured_search |
| `rag/test_csv_search.py` | 21 | Top-level script or placeholder; review its folder context |
| `rag/test_dataset_registry.py` | 27 | Top-level script or placeholder; review its folder context |
| `rag/test_query_routing.py` | 42 | Top-level script or placeholder; review its folder context |
| `rag/test_structured_search.py` | 42 | Top-level script or placeholder; review its folder context |
| `rag/test_xlsx.py` | 23 | Top-level script or placeholder; review its folder context |
| `rag/test_xlsx_header_detection.py` | 56 | Top-level script or placeholder; review its folder context |
| `rag/tool_calling.py` | 639 | functions: bm25_search, execute_search_documents, execute_search_structured_data, execute_tool, call_openrouter, run_query_with_tools, main |
| `rag/web_search_agent.py` | 873 | functions: execute_web_search, bm25_search, execute_search_documents, execute_search_structured_data, execute_tool, call_openrouter, run_web_agent, main |
| `rag/xlsx_search.py` | 226 | functions: clean_header, is_valid_header_row, find_header_row, load_xlsx_files |
| `streamlit_app.py` | 97 | functions: get_backend |
| `tests/__init__.py` | 0 | Empty package marker |
| `tests/test_chat_catalog.py` | 60 | classes: ChatTests;  |
| `tests/test_chat_commands.py` | 49 | classes: CommandTests;  |
| `tests/test_chat_runtime.py` | 42 | classes: RuntimeTests;  |
| `tests/test_context_summary.py` | 65 | classes: SummaryTests;  |
| `tests/test_conversation_sources.py` | 99 | classes: ConversationTests;  |
| `tests/test_conversation_workflow.py` | 222 | classes: Gateway, WorkflowTests;  |
| `tests/test_jira_creation.py` | 73 | classes: G, T; functions: req |
| `tests/test_named_sessions.py` | 66 | classes: State, SessionTests; functions: build |
| `tests/test_prompt_workflow.py` | 209 | classes: WorkflowTests; functions: proposal |
| `tests/test_streamlit_ui.py` | 59 | classes: FakeBackend, BrowserTests;  |
| `tests/test_terminal_input.py` | 62 | classes: InputTests;  |
| `tests/test_tool_llm.py` | 49 | classes: AdapterTests;  |

Folder counts: (root): 2, agent: 22, evaluations: 5, examples: 23, integrations: 9, rag: 20, tests: 13.


## Offline test baseline completed - 17 October 2026

**Y - scoped completion:** repaired stale test fixtures and verified 120 tests passing in 3.704 seconds using the offline guard. This supersedes the earlier 116-test/six-error baseline for these fixtures; it does not establish live API, RAG answer-quality or production acceptance.

Run from the project root:

```powershell
python tests/run_offline.py
```

Changes:
- tests/test_jira_creation.py: enable creation only within fake-gateway test fixtures; add a regression proving disabled creation blocks writes.
- tests/test_prompt_workflow.py: mock proposal discussion instead of calling the real model; explicitly enable the fake approval workflow in its test scope.
- tests/run_offline.py: guard discovery and execution against external sockets, unmocked requests HTTP calls and browser launches. Loopback sockets remain for asyncio/framework internals. This is a process-level test guard, not a subprocess sandbox.
- tests/test_offline_runner.py: verify socket/HTTP/browser blocking and loopback classification.

The verified run used the project's virtual environment and required Windows file permissions. Real Jira permission gates, provider settings and runtime agent behavior were not changed. Full agent reliability remains P; next is memory and structured retrieval integration.


## Shared table and memory tool integration - 17 October 2026

**Y - implementation and offline integration:** CSV/XLSX discovery/filtering with source rows and scoped lexical saved-memory search are connected to the shared conversation. 129 guarded offline tests pass. See [table-memory-tools.md](table-memory-tools.md) for files, limits and trial prompts. **P - broader acceptance:** live model behavior, semantic-memory retrieval, complex-table queries and grounding remain pending.
