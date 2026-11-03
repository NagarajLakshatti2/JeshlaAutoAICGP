"""Draft-only shortcut menu inside the existing composer add popover."""
import streamlit as st


def prefill_shortcut(name, session, project_id):
    if (st.session_state.get("active_chat") != session or
            st.session_state.get("selected_project_id", "") != project_id):
        return
    if name not in {"help", "memory", "read", "results"}:
        return
    st.session_state.message = "/" + name + (" " if name in {"read", "results"} else "")


def render_shortcut_menu(session, project_selected=False):
    project_id = st.session_state.get("selected_project_id", "")
    with st.expander("Commands", icon=":material/terminal:"):
        st.caption("Choose a shortcut, edit its draft and press Send.")
        for name, label, icon in [("read", "Read project file", "description"),
                                  ("results", "Saved test results", "fact_check"),
                                  ("memory", "Show saved memory", "memory"),
                                  ("help", "Shortcut help", "help")]:
            st.button(label, key="shortcut_" + name, icon=":material/" + icon + ":",
                      width="stretch", type="tertiary", disabled=name in {"read", "results"} and not project_selected,
                      on_click=prefill_shortcut, args=(name, session, project_id))
        if not project_selected:
            st.caption("Select a saved project to read its files or saved results.")
