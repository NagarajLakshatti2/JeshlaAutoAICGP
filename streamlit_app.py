"""Run: python -m streamlit run streamlit_app.py --server.address 127.0.0.1"""
import json
import time
import streamlit as st
from agent.browser_backend import make_browser_backend

st.set_page_config(page_title="JeshlaAutoAI",page_icon=":material/smart_toy:",layout="centered")
st.title("JeshlaAutoAI")
st.caption("Your project assistant · Memory, documents, local source and web search")

@st.cache_resource
def get_backend():
    return make_browser_backend()

try:
    backend=get_backend()
except Exception:
    st.error("The agent could not start. Check the terminal for startup errors and your local configuration.")
    st.stop()

st.session_state.setdefault("active_chat","default")
with st.sidebar:
    st.header("Conversations")
    with st.form("new_chat",clear_on_submit=True):
        title=st.text_input("New chat title",max_chars=80,placeholder="Leave blank for an automatic title")
        create=st.form_submit_button("New chat",icon=":material/add:",width="stretch")
    if create:
        try:
            chat=backend.create_chat(title)
            st.session_state.active_chat=chat
            st.session_state.chat_picker=chat
            st.session_state.pop("chat_notices",None)
        except ValueError:
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
        st.session_state.active_chat=selected
        st.session_state.pop("chat_notices",None)
        st.rerun()
    if st.button("Refresh chats",icon=":material/refresh:",width="stretch"):
        st.rerun()
    with st.expander("Shared project memory"):
        if st.button("Show saved facts",key="show_facts"):
            st.session_state.saved_facts=backend.memory()
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
    st.download_button("Download conversation",json.dumps(turns,ensure_ascii=False,indent=2),file_name="conversation.json",mime="application/json",icon=":material/download:")
    if len(turns)>100:st.caption("Showing the latest 100 turns. The download includes the full archived conversation.")
    for turn in turns[-100:]:
        with st.chat_message("user"):st.markdown(turn["question"])
        with st.chat_message("assistant"):st.markdown(turn["answer"])
else:
    st.info("Ask about your saved project facts, inspect source files, or search the web. Earlier console history may exist in checkpoints even if it predates transcript archiving.")
for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
st.caption("Enter to send · Shift+Enter for a new line · Edit or paste multiple lines before sending")

prompt=st.chat_input("Message JeshlaAutoAI",key="message",height=100,submit_mode="disable")
if prompt and prompt.strip():
    with st.chat_message("user"):st.markdown(prompt)
    with st.chat_message("assistant"):
        start=time.perf_counter()
        try:
            with st.spinner("Working on your request…"):
                result=backend.submit(session,prompt)
            st.markdown(result["answer"])
            st.caption(f"Completed in {time.perf_counter()-start:.1f}s")
            st.session_state.chat_notices=result.get("notices",[])
            st.session_state.pop("saved_facts",None)
        except RuntimeError as error:
            # Only the local busy error is safe to show verbatim; provider text stays private.
            if str(error).startswith("This chat is busy"):
                st.error("This chat is busy in another window. Try again when it finishes.")
            else:st.error("The request failed. Check provider configuration, quota and connectivity in the terminal.")
        except Exception:
            st.error("The request could not complete. Your existing saved chats remain available.")
    for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
