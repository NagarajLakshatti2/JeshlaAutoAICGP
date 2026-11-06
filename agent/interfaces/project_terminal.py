"""Project command panel using the existing exact-action approvals."""
import json
import streamlit as st
from agent.interfaces.dialogs import dismiss_dialog
from agent.interfaces.projects import selected_backend
from agent.interfaces.sidebar import ensure_message_chat


def cancel_queued_command(backend, session, root, token):
    scope = backend.request_scope()
    if not scope or scope["bound_project_root"] != root:
        return
    if st.session_state.get("active_chat") != session:
        return
    actions = backend.actions()
    rows = actions.command_history(backend.user, backend.space, session, root)
    if any(row["id"] == token and row["status"] == "pending" for row in rows):
        actions.decline(backend.user, backend.space, session, token)
    elif any(row["id"] == token and row["status"] == "running" for row in rows):
        actions.cancel_command(backend.user, backend.space, session, token, root)


@st.dialog("Project terminal", on_dismiss=dismiss_dialog, width="large")
def render_project_terminal(manager):
    backend = selected_backend(manager)
    scope = backend.request_scope()
    if not scope:
        st.info("Select a saved project first.")
        return
    st.text(scope["bound_project_root"])
    st.caption("Review a command, approve it in chat, then inspect its saved output.")
    session = st.session_state.get("active_chat")
    if session and not st.session_state.get("chat_draft"):
        history = backend.actions().command_history(backend.user, backend.space, session,
                                                    scope["bound_project_root"])
        for item in history:
            st.code(json.dumps(item["command"]), language="json")
            st.caption(item["status"])
            if item["status"] in {"pending", "running"}:
                st.button("Stop command", key="terminal_cancel_" + item["id"],
                          on_click=cancel_queued_command,
                          args=(backend, session, scope["bound_project_root"], item["id"]))
            result = item["result"]
            if result:
                st.text("Exit code " + str(result.get("exit_code")))
                st.code(str(result.get("stdout", ""))[-12000:], language="text")
                if result.get("stderr"):
                    st.code(str(result["stderr"])[-12000:], language="text")

    from agent.actions.terminal_sessions import list_sessions
    if session and not st.session_state.get("chat_draft"):
        identity = (backend.user, backend.space, session, scope["bound_project_root"])
        for running in list_sessions(identity):
            token = running["terminal_id"]
            st.text("Session " + token[:8])
            st.code(running["stdout"] + running["stderr"], language="text")
            if running["running"]:
                text = st.text_area("Input to session", key="terminal_input_" + token)
                for label, action in (("Request input approval", "terminal_input"),
                                      ("Request session stop approval", "terminal_stop")):
                    if st.button(label, key=action + token):
                        args = {"chat_id": session, "terminal_id": token, "revision": running["revision"]}
                        if action == "terminal_input":
                            args["text"] = text
                        backend.actions().propose(backend.user, backend.space, session, action,
                            {"project_root": scope["bound_project_root"], "action": action, "arguments": args})
                        st.success("Review the exact action in chat.")
    interactive = st.checkbox("Start a persistent input session", key="terminal_interactive")
    st.button("Refresh command history", key="terminal_refresh")
    command_text = st.text_area("Command arguments (JSON)", value='["python", "--version"]',
                                key="terminal_command_" + scope["project_id"])
    timeout = st.number_input("Time limit in seconds", min_value=1, max_value=300, value=60,
                              key="terminal_timeout_" + scope["project_id"])
    if st.button("Request command approval", key="terminal_request"):
        try:
            command = json.loads(command_text)
            from agent.tools.project_tools import ProjectTools
            ProjectTools(scope["bound_project_root"])._command_argv(command, int(timeout))
            session = ensure_message_chat(backend, "Project terminal command")
            action = "terminal_start" if interactive else "run_command"
            args = ({"command": command, "lifetime": int(timeout), "chat_id": session}
                    if interactive else {"command": command, "timeout": int(timeout)})
            proposal = {"project_root": scope["bound_project_root"], "action": action, "arguments": args}
            backend.actions().propose(backend.user, backend.space, session, action, proposal)
            st.session_state.ui_dialog = None
            st.rerun()
        except (ValueError, OSError) as error:
            st.warning(str(error))
