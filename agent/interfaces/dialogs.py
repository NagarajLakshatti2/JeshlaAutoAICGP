"""Keep advanced controls out of the everyday conversation view."""
import streamlit as st
from agent import browser_activity
from agent.interfaces.errors import user_error_message


def dismiss_dialog():st.session_state.ui_dialog=None


@st.dialog("Memory",on_dismiss=dismiss_dialog,width="medium",icon=":material/memory:")
def memory_dialog(backend):
    st.caption("Saved facts are shared across your chats in the selected memory space.")
    if st.button("Show saved facts",key="show_facts"):
        try:
            st.session_state.saved_facts=backend.memory_records() if hasattr(backend,"memory_records") else backend.memory()
            browser_activity.log_browser_event("memory_viewed",session=st.session_state.active_chat)
        except Exception as error:st.error(user_error_message(error))
    if "saved_facts" in st.session_state:
        from agent.interfaces.memory_panel import render_memory
        render_memory(st.session_state.saved_facts)
    if hasattr(backend,"edit_memory"):
        from agent.interfaces.memory_editor import render_memory_editor
        render_memory_editor(backend)


@st.dialog("Settings",on_dismiss=dismiss_dialog,width="medium",icon=":material/settings:")
def settings_dialog(backend):
    from agent.interfaces.provider_panel import render_provider_panel
    render_provider_panel(backend,inline=True)
