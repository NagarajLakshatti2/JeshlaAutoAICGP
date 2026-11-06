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
    selected=st.session_state.get("chat_picker")
    # A stale widget value must never become the active conversation.
    if isinstance(selected,str) and backend.get_chat(selected):
        open_chat(backend,selected)


def display_title(row):return "Earlier chat" if row["session"]=="default" and row["title"]=="default" else row["title"]


def chat_picker_labels(rows):
    """Keep Streamlit's serialized option labels distinct for same-titled chats."""
    keys=list(rows)
    labels={}
    for key in keys:
        width=min(8,len(key))
        while any(other!=key and other.endswith(key[-width:]) for other in keys) and width<len(key):
            width+=1
        # Include a stable reference even for unique titles: recency and title
        # duplication must not change a widget option's identity on rerun.
        labels[key]=f"{display_title(rows[key])} · {key[-width:]}"
    return labels


def render_sidebar_style():
    # Native containers keep the controls accessible; only our chat list scrolls.
    # Streamlit has no public sidebar header/footer slots, so scope layout rules
    # to this sidebar and our keyed containers. Preserve its collapse button.
    st.html("""<style>
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        position: relative; overflow: hidden; padding: 0;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
        height: 3.25rem; min-height: 3.25rem; padding: .5rem 1rem; margin: 0; width: 100%;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding: 0 1rem .75rem; width: 100%; box-sizing: border-box;
    }
    [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_brand) {
        display: contents;
    }
    [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_shell) {
        height: calc(100dvh - 4rem); min-height: 0;
    }
    [data-testid="stSidebar"] .st-key-sidebar_brand {
        position: absolute; top: .65rem; left: 1rem;
        width: calc(100% - 4.5rem); z-index: 1;
    }
    [data-testid="stSidebar"] .st-key-sidebar_brand h2 {
        font-size: 1.15rem; line-height: 1.5; padding: 0; margin: 0;
    }
    [data-testid="stSidebar"] .st-key-sidebar_shell {
        height: 100%; min-height: 0; gap: .5rem;
    }
    [data-testid="stSidebar"] .st-key-sidebar_shell > [data-testid="stLayoutWrapper"] {
        flex: 0 0 auto;
    }
    [data-testid="stSidebar"] .st-key-sidebar_shell > [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_chats) {
        flex: 1 1 0; min-height: 0; overflow: hidden;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chats > [data-testid="stElementContainer"] {
        flex-shrink: 0;
    }
    [data-testid="stSidebar"] .st-key-sidebar_controls { gap: .5rem; flex-shrink: 0; }
    .st-key-sidebar_chat_actions button { padding: .35rem .4rem; gap: .3rem; }
    .st-key-sidebar_chat_actions button p { font-size: .875rem; }
    .st-key-sidebar_chat_actions [data-testid="stIconMaterial"] { font-size: 1rem; }
    [data-testid="stSidebar"] .st-key-sidebar_chats {
        height: 100%; min-height: 0; overflow-y: auto; overflow-x: hidden;
        overscroll-behavior: contain; scrollbar-width: thin; gap: .125rem;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chats [data-testid="stButton"] button {
        justify-content: flex-start; text-align: left; min-height: 2.5rem;
    }
    [data-testid="stSidebar"] .st-key-sidebar_chats [data-testid="stButton"] button p {
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    [data-testid="stSidebar"] .st-key-sidebar_footer {
        flex-shrink: 0; border-top: 1px solid var(--st-border-color, #dce2e8);
        padding-top: .5rem; gap: .25rem;
    }
    @media (max-height: 540px) {
        [data-testid="stSidebar"] .st-key-sidebar_controls { gap: .25rem; }
    }
    </style>""")


def render_chat_list(backend):
    """One stable list, extended in place when the user requests older chats."""
    offset=st.session_state.get("chat_page_offset",0)
    by_id={};has_more=False
    if hasattr(backend,"list_chat_page"):
        for start in range(0,offset+1,30):
            page=backend.list_chat_page(start)
            by_id.update((row["session"],row) for row in page[:30])
            has_more=len(page)>30
            if not has_more:break
    else:by_id={row["session"]:row for row in backend.list_chats()}
    active=st.session_state.active_chat
    if active not in by_id:
        row=backend.get_chat(active)
        if row:by_id[active]=row
    query=st.session_state.get("chat_title_filter","").strip().casefold()
    matching=[key for key,row in by_id.items() if query in display_title(row).casefold()]
    if not by_id:st.caption("No chats yet. Start with New chat.")
    elif not matching:st.caption("No loaded titles match. Search saved messages or load older chats.")
    for key in matching:
        current=key==active and st.session_state.get("chat_opened",False)
        if st.button(display_title(by_id[key]),key="open_chat_"+key,
                     type="secondary" if current else "tertiary",width="stretch",wrap=False):
            open_chat(backend,key);st.rerun()
    if has_more:
        st.button("Load older chats",key="load_older_chats",type="tertiary",width="stretch",
                  on_click=change_chat_page,args=(offset+30,))


def render_sidebar(backend,project_manager=None):
    pending=st.session_state.pop("pending_chat_picker",None)
    if pending:
        st.session_state.chat_picker=pending
        st.session_state.chat_title_filter=""
    render_sidebar_style()
    with st.sidebar:
        with st.container(key="sidebar_brand"):
            st.header("JeshlaAutoAI",anchor=False)
        with st.container(key="sidebar_shell"):
            with st.container(key="sidebar_controls"):
                with st.container(key="sidebar_chat_actions",horizontal=True,wrap=False,gap="xsmall"):
                    if st.button("New chat",key="create_new_chat",icon=":material/add:",width="stretch"):
                        start_chat_draft();st.rerun()
                    with st.popover("Search chats",icon=":material/search:",width="stretch"):
                        st.text_input("Filter loaded chat titles",key="chat_title_filter",placeholder="Search titles",max_chars=100,label_visibility="collapsed")
                        if hasattr(backend,"search_chats"):
                            from agent.interfaces.chat_search import render_chat_search
                            render_chat_search(backend)
                project=getattr(backend,"project",None)
                st.caption("Chats and tasks · "+project["name"] if project else "Chats and tasks")
            with st.container(key="sidebar_chats"):
                render_chat_list(backend)
            with st.container(key="sidebar_footer",horizontal=True,wrap=False):
                if st.button("Memory",icon=":material/memory:",key="open_memory",type="tertiary",width="stretch"):
                    st.session_state.ui_dialog="memory"
                if st.button("Settings",icon=":material/settings:",key="open_settings",type="tertiary",width="stretch"):
                    st.session_state.ui_dialog="settings";st.session_state.settings_section="Providers"
    if st.session_state.get("ui_dialog")=="memory":
        from agent.interfaces.dialogs import memory_dialog
        memory_dialog(backend)
    elif st.session_state.get("ui_dialog")=="settings":
        from agent.interfaces.dialogs import settings_dialog
        settings_dialog(backend)
