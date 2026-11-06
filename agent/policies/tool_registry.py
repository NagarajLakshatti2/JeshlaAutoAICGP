"""Explicit core project-tool policy; new tools require classification before exposure."""
READ_ONLY_PROJECT_ACTIONS=frozenset({"list_files","read_file","read_files","search_text","parse_test_results","investigate_test_failure","prepare_test_repair","compare_test_rerun","build_test_report","prepare_test_report_export","discover_feature_mappings","discover_jira_traceability","validate_test_plan","draft_test_observations","prepare_project"})
CONTROLLED_PROJECT_ACTIONS=frozenset({"create_file","replace_text","run_command","run_python_file","run_tests_and_parse","inspect_browser_page","apply_test_repair","rerun_test_repair","create_project"})
WORKSPACE_CONTROLLED_ACTIONS=frozenset({"git_commit","git_push","git_branch","terminal_start","terminal_input","terminal_stop"})
PROJECT_ACTIONS=READ_ONLY_PROJECT_ACTIONS|CONTROLLED_PROJECT_ACTIONS

READ_ONLY_CONVERSATION_ACTIONS=frozenset({"fetch_web_page","review_memory","search_chats","web_search","search_documents","search_memory","list_tables","search_table","list_files","read_file","search_text","validate_test_plan","draft_test_observations"})
MEMORY_PROPOSAL_ACTIONS=frozenset({"suggest_memory"})
CONVERSATION_ACTIONS=READ_ONLY_CONVERSATION_ACTIONS|MEMORY_PROPOSAL_ACTIONS

def validate_conversation_registry(specs):
    names=[item.get("function",{}).get("name") for item in specs]
    if len(names)!=len(set(names)) or set(names)!=CONVERSATION_ACTIONS:
        raise ValueError("Conversation tools must match the classified core policy before model access.")
