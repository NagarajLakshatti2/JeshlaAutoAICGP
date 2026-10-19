"""Explicit core project-tool policy; new tools require classification before exposure."""
READ_ONLY_PROJECT_ACTIONS=frozenset({"list_files","read_file","read_files","search_text","parse_test_results","discover_feature_mappings"})
CONTROLLED_PROJECT_ACTIONS=frozenset({"create_file","replace_text","run_command","run_python_file","run_tests_and_parse"})
PROJECT_ACTIONS=READ_ONLY_PROJECT_ACTIONS|CONTROLLED_PROJECT_ACTIONS

READ_ONLY_CONVERSATION_ACTIONS=frozenset({"fetch_web_page","review_memory","search_chats","web_search","search_documents","search_memory","list_tables","search_table","list_files","read_file","search_text"})
MEMORY_PROPOSAL_ACTIONS=frozenset({"suggest_memory"})
CONVERSATION_ACTIONS=READ_ONLY_CONVERSATION_ACTIONS|MEMORY_PROPOSAL_ACTIONS

def validate_conversation_registry(specs):
    names=[item.get("function",{}).get("name") for item in specs]
    if len(names)!=len(set(names)) or set(names)!=CONVERSATION_ACTIONS:
        raise ValueError("Conversation tools must match the classified core policy before model access.")
