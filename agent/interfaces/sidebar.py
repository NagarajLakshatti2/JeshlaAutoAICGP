"""Compact chat navigation; memory and settings live in separate dialogs."""
import uuid
import streamlit as st
from agent import browser_activity


def start_chat_draft():
    """Keep the welcome composer separate from every saved conversation."""
    previous=st.session_state.get("active_chat")
    if st.session_state.get("chat_draft"):
        for name in ("attachment_collections","attachments_by_chat"):
            st.session_state.get(name,{}).pop(previous,None)
    st.session_state.active_chat="draft-"+uuid.uuid4().hex
    st.session_state.chat_draft=True
    st.session_state.chat_opened=False
    st.session_state.ui_dialog=None
    st.session_state.chat_page_offset=0
    st.session_state.chat_title_filter=""
    for name in ("chat_picker","pending_chat_picker","chat_notices","archive_results","upload_notice"):
        st.session_state.pop(name,None)


def initialize_chat():
    if "active_chat" not in st.session_state:start_chat_draft()
    else:
        # Preserve an already selected chat when code reloads in an open browser.
        st.session_state.setdefault("chat_draft",False)
        st.session_state.setdefault("chat_opened",False)


def ensure_message_chat(backend,question):
    """Save a draft once, on an explicit message or confirmed memory action."""
    session=st.session_state.active_chat
    if not st.session_state.get("chat_draft"):return session
    from agent.storage.chats import TITLE_LIMIT
    title=" ".join(question.split())[:TITLE_LIMIT]
    saved=backend.create_chat(title)
    for name in ("attachment_collections","attachments_by_chat"):
        data=st.session_state.get(name,{})
        if session in data:data[saved]=data.pop(session)
    st.session_state.active_chat=saved
    st.session_state.chat_draft=False
    st.session_state.chat_opened=True
    # The picker has already rendered during message handling; update next rerun.
    st.session_state.pending_chat_picker=saved
    st.session_state.chat_page_offset=0
    browser_activity.log_browser_event("chat_created",session=saved,provider=backend.provider)
    return saved


def open_chat(backend,session):
    st.session_state.active_chat=session
    st.session_state.chat_draft=False
    st.session_state.pop("pending_chat_picker",None)
    if st.session_state.get("chat_picker")!=session:st.session_state.chat_picker=session
    st.session_state.chat_opened=True
    st.session_state.ui_dialog=None
    st.session_state.pop("chat_notices",None)
    browser_activity.log_browser_event("chat_switched",session=session,provider=backend.provider)


def change_chat_page(offset):
    st.session_state.chat_page_offset=offset
    st.session_state.pop("chat_picker",None)


def open_picker_chat(backend):
    open_chat(backend,st.session_state.chat_picker)


def display_title(row):return "General chat" if row["session"]=="default" and row["title"]=="default" else row["title"]


def render_sidebar(backend):
    pending=st.session_state.pop("pending_chat_picker",None)
    if pending:
        st.session_state.chat_picker=pending
        st.session_state.chat_title_filter=""
    with st.sidebar:
        st.header("JeshlaAutoAI",anchor=False)
        if st.button("New chat",key="create_new_chat",icon=":material/add:",width="stretch"):
            start_chat_draft()
            st.rerun()
        with st.popover("Search chats",icon=":material/search:",type="tertiary",width="stretch"):
            st.text_input("Filter recent chat titles",key="chat_title_filter",placeholder="Search titles",max_chars=100,label_visibility="collapsed")
            if hasattr(backend,"search_chats"):
                from agent.interfaces.chat_search import render_chat_search
                render_chat_search(backend)
        st.space("small")
        st.caption("Chats and tasks")
        rows=backend.list_chats();by_id={row["session"]:row for row in rows}
        active=st.session_state.active_chat
        if active not in by_id:
            row=backend.get_chat(active)
            if row:by_id[active]=row
        if not by_id:
            st.caption("No saved chats yet.")
        query=st.session_state.get("chat_title_filter","").strip().casefold()
        matching=[key for key,row in by_id.items() if query in display_title(row).casefold()]
        if not matching:st.caption("No recent titles match. Your current chat is still open.")
        for key in matching[:10]:
            current=key==st.session_state.active_chat and st.session_state.get("chat_opened",False)
            if st.button(display_title(by_id[key]),key="open_chat_"+key,type="secondary" if current else "tertiary",width="content",wrap=False):
                open_chat(backend,key);st.rerun()
        if by_id:
            with st.popover("View all",type="tertiary",width="stretch"):
                offset=st.session_state.get("chat_page_offset",0)
                page=backend.list_chat_page(offset) if hasattr(backend,"list_chat_page") else list(by_id.values())
                page_by_id={row["session"]:row for row in page[:30]}
                # Retain an explicitly opened older chat on the initial page.
                if offset==0 and active not in page_by_id and active in by_id:page_by_id[active]=by_id[active]
                ids=list(page_by_id)
                if ids:
                    if st.session_state.get("chat_picker") not in ids:st.session_state.chat_picker=active if active in ids else ids[0]
                    selected=st.selectbox("Saved chats",ids,format_func=lambda key:display_title(page_by_id[key]),key="chat_picker",on_change=open_picker_chat,args=(backend,))
                    if st.button("Open selected chat",key="open_selected_chat",width="stretch"):
                        open_chat(backend,selected);st.rerun()
                else:st.caption("No chats on this page.")
                if hasattr(backend,"list_chat_page"):
                    st.caption("Page "+str(offset//30+1)+" · newest chats first")
                    with st.container(horizontal=True):
                        st.button("Newer",key="newer_chat_page",disabled=offset==0,on_click=change_chat_page,args=(max(0,offset-30),))
                        st.button("Older",key="older_chat_page",disabled=len(page)<=30,on_click=change_chat_page,args=(offset+30,))
                if st.button("Refresh chats",icon=":material/refresh:",width="stretch"):st.rerun()
        st.space("large")
        st.divider()
        if st.button("Memory",icon=":material/memory:",key="open_memory",type="tertiary",width="content"):
            st.session_state.ui_dialog="memory"
        if st.button("Settings",icon=":material/settings:",key="open_settings",type="tertiary",width="content"):
            st.session_state.ui_dialog="settings"
    if st.session_state.get("ui_dialog")=="memory":
        from agent.interfaces.dialogs import memory_dialog
        memory_dialog(backend)
    elif st.session_state.get("ui_dialog")=="settings":
        from agent.interfaces.dialogs import settings_dialog
        settings_dialog(backend)
