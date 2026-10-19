"""Run: python -m streamlit run streamlit_app.py --server.address 127.0.0.1"""
import json
import time
import streamlit as st
from agent.browser_backend import make_browser_backend
from agent.user_errors import user_error_message
from agent.browser_activity import log_browser_event

st.set_page_config(page_title="JeshlaAutoAI",page_icon=":material/smart_toy:",layout="centered")
st.title("JeshlaAutoAI")
st.caption("Your project assistant · Memory, documents, local source and web search")

@st.cache_resource
def get_backend():
    backend=make_browser_backend()
    return backend

try:
    backend=get_backend()
except Exception as error:
    log_browser_event("error",error=error)
    st.error(user_error_message(error))
    st.stop()

st.session_state.setdefault("active_chat","default")
log_browser_event("page_render",session=st.session_state.active_chat,provider=backend.provider)
with st.sidebar:
    st.header("Conversations")
    with st.form("new_chat",clear_on_submit=True):
        title=st.text_input("New chat title",max_chars=80,placeholder="Leave blank for an automatic title")
        create=st.form_submit_button("New chat",icon=":material/add:",width="stretch")
    if create:
        try:
            chat=backend.create_chat(title)
            log_browser_event("chat_created",session=chat,provider=backend.provider)
            st.session_state.active_chat=chat
            st.session_state.chat_picker=chat
            st.session_state.pop("chat_notices",None)
        except ValueError as error:
            log_browser_event("error",error=error)
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
    if st.session_state.get("chat_picker") not in ids:
        st.session_state.chat_picker=active
    selected=st.selectbox("Saved chats",ids,format_func=lambda key:by_id[key]["title"],key="chat_picker")
    if selected!=st.session_state.active_chat:
        log_browser_event("chat_switched",session=selected,provider=backend.provider)
        st.session_state.active_chat=selected
        st.session_state.pop("chat_notices",None)
        st.rerun()
    if st.button("Refresh chats",icon=":material/refresh:",width="stretch"):
        log_browser_event("chats_refreshed",session=st.session_state.active_chat)
        st.rerun()
    with st.expander("Shared project memory"):
        if st.button("Show saved facts",key="show_facts"):
            try:
                st.session_state.saved_facts=backend.memory()
                log_browser_event("memory_viewed",session=st.session_state.active_chat)
            except Exception as error:
                log_browser_event("error",session=st.session_state.active_chat,error=error)
                st.error(user_error_message(error))
        if "saved_facts" in st.session_state:
            st.text(st.session_state.saved_facts or "No saved facts.")
        st.caption("REMEMBER key = fact saves; FORGET key removes. These facts are shared across your chats.")
    st.caption("Provider: "+backend.provider)
    st.caption("Saved facts and selected evidence are included in hosted-model requests.")

session=st.session_state.active_chat
chat=backend.get_chat(session)
st.subheader(chat["title"] if chat else "Conversation")
turns=backend.turns(session)
if turns:
    if st.download_button("Download conversation",json.dumps(turns,ensure_ascii=False,indent=2),file_name="conversation.json",mime="application/json",icon=":material/download:"):
        log_browser_event("download_clicked",session=session,turns=len(turns))
    if len(turns)>100:st.caption("Showing the latest 100 turns. The download includes the full archived conversation.")
    for turn in turns[-100:]:
        with st.chat_message("user"):st.markdown(turn["question"])
        with st.chat_message("assistant"):st.markdown(turn["answer"])
else:
    st.info("Ask about your saved project facts, inspect source files, or search the web. Earlier console history may exist in checkpoints even if it predates transcript archiving.")
for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
st.caption("Enter to send · Shift+Enter for a new line · Edit or paste multiple lines before sending")

from agent.browser_action_ui import render_pending_actions
render_pending_actions(backend,session)

prompt=st.chat_input("Message JeshlaAutoAI",key="message",height=100,submit_mode="disable")
if prompt and prompt.strip():
    with st.chat_message("user"):st.markdown(prompt)
    with st.chat_message("assistant"):
        start=time.perf_counter()
        result={}
        log_browser_event("message_started",session=session,provider=backend.provider)
        try:
            with st.spinner("Working on your request…"):
                result=backend.submit(session,prompt)
            log_browser_event("message_finished",session=session,provider=backend.provider,duration=time.perf_counter()-start)
            st.markdown(result["answer"])
            st.caption(f"Completed in {time.perf_counter()-start:.1f}s")
            st.session_state.chat_notices=result.get("notices",[])
            st.session_state.pop("saved_facts",None)
        except Exception as error:
            log_browser_event("error",session=session,provider=backend.provider,duration=time.perf_counter()-start,error=error)
            st.error(user_error_message(error))
    for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
    if result.get("task_status")=="awaiting_input":st.rerun()
