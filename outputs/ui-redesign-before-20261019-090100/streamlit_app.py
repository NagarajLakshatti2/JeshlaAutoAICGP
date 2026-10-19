"""Run: python -m streamlit run streamlit_app.py --server.address 127.0.0.1"""
import json
import time
import streamlit as st
from agent.browser_backend import make_browser_backend
from agent.user_errors import user_error_message
from agent.browser_activity import log_browser_event

st.set_page_config(page_title="JeshlaAutoAI",page_icon=":material/smart_toy:",layout="centered")
st.title("JeshlaAutoAI")
st.caption("Your AI assistant for projects and automation.")

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
from agent.interfaces.sidebar import render_sidebar
render_sidebar(backend)

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
    st.info("Ask a question, use your saved facts, or inspect a project folder you provide. Choose a saved chat from the sidebar to continue.")
for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
st.caption("Enter to send · Shift+Enter for a new line · Edit or paste multiple lines before sending")

from agent.interfaces.request_status import status_label,remember_status,render_status
status_area=st.empty()
with status_area.container():
    render_status(st.session_state.get("request_status_by_chat",{}).get(session))

from agent.browser_action_ui import render_pending_actions
render_pending_actions(backend,session)

from agent.interfaces.attachments import render_attachments,attachment_question
attachment=render_attachments(session)
from agent.interfaces.generated_files import render_generated_files
render_generated_files(backend,session)
latest=st.session_state.get("answer_downloads",{}).get(session)
if latest:
    st.download_button("Download latest answer",latest,file_name="answer.md",mime="text/markdown",key="download_answer_"+session)

prompt=st.chat_input("Message JeshlaAutoAI",key="message",height=100,submit_mode="disable")
if prompt and prompt.strip():
    with st.chat_message("user"):st.markdown(prompt)
    with st.chat_message("assistant"):
        start=time.perf_counter()
        result={}
        log_browser_event("message_started",session=session,provider=backend.provider)
        try:
            with st.spinner("Working on your request…"):
                result=backend.submit(session,attachment_question(prompt,attachment))
            log_browser_event("message_finished",session=session,provider=backend.provider,duration=time.perf_counter()-start)
            st.markdown(result["answer"])
            st.session_state.setdefault("answer_downloads",{})[session]=result["answer"]
            st.download_button("Download this answer",result["answer"],file_name="answer.md",mime="text/markdown",key="download_current_answer_"+session)
            record=remember_status(session,status_label(result),time.perf_counter()-start,result.get("persistence_status"))
            with status_area.container():render_status(record)
            st.session_state.chat_notices=result.get("notices",[])
            st.session_state.pop("saved_facts",None)
        except Exception as error:
            log_browser_event("error",session=session,provider=backend.provider,duration=time.perf_counter()-start,error=error)
            st.error(user_error_message(error))
            record=remember_status(session,"Failed",time.perf_counter()-start)
            with status_area.container():render_status(record)
    for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
    if result.get("task_status")=="awaiting_input":st.rerun()
