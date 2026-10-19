"""Sidebar navigation for existing chat and memory capabilities."""
import streamlit as st
from agent import browser_activity
from agent.user_errors import user_error_message


def render_sidebar(backend):
    with st.sidebar:
        st.header("Conversations")
        with st.form("new_chat",clear_on_submit=True):
            title=st.text_input("New chat title",max_chars=80,placeholder="Leave blank for an automatic title")
            create=st.form_submit_button("New chat",key="create_new_chat",icon=":material/add:",width="stretch")
        if create:
            try:
                chat=backend.create_chat(title)
                browser_activity.log_browser_event("chat_created",session=chat,provider=backend.provider)
                st.session_state.active_chat=chat
                st.session_state.chat_picker=chat
                st.session_state.pop("chat_notices",None)
                st.session_state.chat_title_filter=""
            except ValueError as error:
                browser_activity.log_browser_event("error",error=error)
                st.error("Use a title of at most 80 characters.")
        rows=backend.list_chats()
        by_id={row["session"]:row for row in rows}
        active=st.session_state.active_chat
        if active not in by_id:
            row=backend.get_chat(active)
            if row:by_id[active]=row
            else:
                active="default";st.session_state.active_chat=active
                by_id[active]=backend.get_chat(active)
        ids=list(by_id)
        query=st.text_input("Filter recent chat titles",key="chat_title_filter",placeholder="Find a recent conversation",max_chars=100)
        matching=[key for key in ids if query.strip().casefold() in by_id[key]["title"].casefold()]
        st.caption(":material/history: Recent conversations")
        if not matching:st.caption("No recent titles match. Your current chat is still open.")
        for key in matching[:8]:
            current=key==st.session_state.active_chat
            if st.button(by_id[key]["title"],key="open_chat_"+key,icon=":material/chat_bubble:",type="primary" if current else "secondary",width="stretch") and not current:
                browser_activity.log_browser_event("chat_switched",session=key,provider=backend.provider)
                st.session_state.active_chat=key
                st.session_state.chat_picker=key
                st.session_state.pop("chat_notices",None)
                st.rerun()
        st.caption("Titles from up to 30 recent chats.")
        if hasattr(backend,"search_chats"):
            from agent.interfaces.chat_search import render_chat_search
            render_chat_search(backend)
        if st.session_state.get("chat_picker") not in ids:
            st.session_state.chat_picker=active
        with st.expander("Open a saved chat",icon=":material/forum:"):
            selected=st.selectbox("Saved chats",ids,format_func=lambda key:by_id[key]["title"],key="chat_picker")
        if selected!=st.session_state.active_chat:
            browser_activity.log_browser_event("chat_switched",session=selected,provider=backend.provider)
            st.session_state.active_chat=selected
            st.session_state.pop("chat_notices",None)
            st.rerun()
        if st.button("Refresh chats",icon=":material/refresh:",width="stretch"):
            browser_activity.log_browser_event("chats_refreshed",session=st.session_state.active_chat)
            st.rerun()
        with st.expander("Shared project memory",icon=":material/memory:"):
            if st.button("Show saved facts",key="show_facts"):
                try:
                    st.session_state.saved_facts=backend.memory_records() if hasattr(backend,"memory_records") else backend.memory()
                    browser_activity.log_browser_event("memory_viewed",session=st.session_state.active_chat)
                except Exception as error:
                    browser_activity.log_browser_event("error",session=st.session_state.active_chat,error=error)
                    st.error(user_error_message(error))
            if "saved_facts" in st.session_state:
                from agent.interfaces.memory_panel import render_memory
                render_memory(st.session_state.saved_facts)
            st.caption("REMEMBER key = fact saves; FORGET key removes. These facts are shared across your chats.")
            if hasattr(backend,"edit_memory"):
                from agent.interfaces.memory_editor import render_memory_editor
                render_memory_editor(backend)
        if hasattr(backend,"provider_info"):
            from agent.interfaces.provider_panel import render_provider_panel
            render_provider_panel(backend)
        st.caption("Provider: "+backend.provider)
        st.caption("Saved facts and selected evidence are included in hosted-model requests.")
