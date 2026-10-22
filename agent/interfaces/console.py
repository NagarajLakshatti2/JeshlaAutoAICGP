"""Console interaction adapter, independent of graph construction and data defaults."""
import argparse
import os
import re
from agent.runtime.timing import timer


def run_console(*, graph, project_root, provider, session_config, restore_session, timer_factory=None):
    """Run the existing console with explicit runtime and session dependencies."""
    if timer_factory is None:timer_factory=timer
    parser = argparse.ArgumentParser(description="JeshlaAutoAI conversational agent")
    parser.add_argument("--input-mode", choices=["editor", "end"], default="editor", help="Editable Enter-to-send input, or legacy END submission")
    parser.add_argument("--session", default=None, help="Resume a named conversation without a startup question")
    parser.add_argument("--user", default=os.getenv("AI_MEMORY_USER_ID", "local-user"))
    parser.add_argument("--memory-space", default=os.getenv("AI_MEMORY_NAMESPACE", "project"),
                        help="Shared long-term fact namespace, for example JeshlaAutoAI")
    args = parser.parse_args()
    from agent.interfaces.terminal_input import configure_input, read_message
    configure_input(args.input_mode)
    try:
        session_config(args.session or "default", args.user, args.memory_space)
    except ValueError as error:
        parser.error(str(error))
    os.environ["AI_MEMORY_USER_ID"] = args.user
    os.environ["AI_MEMORY_NAMESPACE"] = args.memory_space
    from agent.chat_catalog import ChatCatalog, choose_chat, validate_chat_command, TITLE_LIMIT
    catalog = ChatCatalog(project_root / "outputs" / "memory" / "chats.sqlite3", args.user, args.memory_space)
    session_name = args.session
    print("\n================================")
    print("LANGGRAPH AI AGENT")
    print("================================")
    print("Model provider:", provider)
    print("Legacy input: END submits, EXIT quits." if args.input_mode == "end" else "Enter sends; Alt+Enter/Ctrl+J/F2 adds a line. Ctrl+C clears. Ctrl+D exits an empty draft. EXIT quits.")
    print("REMEMBER key = fact saves; FORGET key removes; SHOW MEMORY lists facts. WORKFLOW HELP explains Jira prompts.")

    print("SESSION name switches chat history; SESSION CURRENT shows the active session.")
    print("Saved facts are shared within the selected user/memory space. Jira plans remain scoped to their configured Jira project.")
    print(f"NEW CHAT [title] / NEW SESSION [title]; LIST CHATS; OPEN CHAT id. Titles: max {TITLE_LIMIT} characters.")
    try:
        if session_name is None:
            session_name = choose_chat(catalog)
        else:
            catalog.register(session_name)
    except (EOFError, KeyboardInterrupt):
        print("Session closed.")
        return
    config, history, previous_route, summary = restore_session(session_name, args.user, args.memory_space)

    while True:
        try:
            question = read_message().strip()
        except EOFError:
            print("Session closed. Your saved chats remain available.")
            return
        except KeyboardInterrupt:
            print("Draft cancelled.")
            continue
        if question.upper() in {"EXIT", "QUIT"}:
            return
        if question.upper() == "END":
            print("END is not needed in editor mode. Press Enter to send your message.")
            continue
        if not question:
            continue
        question, command_error = validate_chat_command(question)
        if command_error:
            print(command_error)
            continue
        if question.upper() == "LIST CHATS":
            for row in catalog.list():
                print(f"{row['session']} | {row['title']}")
            continue
        new_chat = re.fullmatch(r"NEW (?:CHAT|SESSION)(?:\s+(.*))?", question, re.I | re.S)
        open_chat = re.fullmatch(r"OPEN CHAT\s+(\S+)", question, re.I)
        if new_chat or open_chat:
            try:
                if new_chat:
                    requested = choose_chat(catalog, (new_chat.group(1) or "").strip())
                else:
                    requested = open_chat.group(1)
                    if not catalog.get(requested):
                        print("Chat not found in this user/memory space. Use LIST CHATS.")
                        continue
                config, history, previous_route, summary = restore_session(requested, args.user, args.memory_space)
                session_name = requested
            except (EOFError, KeyboardInterrupt):
                print("Session closed.")
                return
            continue
        if question.upper() == "SESSION CURRENT":
            print(f"Conversation session: {session_name} | User: {args.user} | Shared memory space: {args.memory_space}")
            continue
        switch = re.fullmatch(r"SESSION(?:\s+(.*))?", question, re.I | re.S)
        if switch:
            requested = (switch.group(1) or "").strip()
            try:
                new_config, new_history, new_route, new_summary = restore_session(requested, args.user, args.memory_space)
            except ValueError as error:
                print(str(error))
                continue
            catalog.register(requested)
            session_name = requested
            config, history, previous_route, summary = new_config, new_history, new_route, new_summary
            continue
        try:
            from agent.chat_runtime import run_turn
            with timer_factory("Complete agent workflow") as outcome:
                result = run_turn(graph, config, catalog, session_name, question, project_root)
                outcome.observe(result)
            print("\n========== FINAL ANSWER ==========\n")
            print(result["final_answer"])
            previous_route = result["route"]
            history, summary = result["history"], result["summary"]
            for notice in result.get("notices", []):
                print(notice)


        except Exception as error:
            from agent.interfaces.errors import print_agent_error
            print_agent_error(error)

