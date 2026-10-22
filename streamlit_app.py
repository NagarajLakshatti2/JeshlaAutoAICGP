"""JeshlaAutoAI browser chat; run with python -m streamlit run streamlit_app.py."""
import json,time
import streamlit as st
from agent.interfaces.browser import make_browser_backend
from agent.interfaces.errors import user_error_message
from agent.interfaces.activity import log_browser_event
from agent.interfaces.sidebar import initialize_chat,ensure_message_chat,render_sidebar
from agent.interfaces.attachments import chat_attachments,attachment_question,render_upload_menu
from agent.interfaces.chat_toolbar import provider_options,render_provider_picker
from agent.interfaces.header_actions import render_header_actions
from agent.interfaces.request_status import status_label,remember_status,render_status

st.set_page_config(page_title="JeshlaAutoAI",page_icon=":material/smart_toy:",layout="wide")

@st.cache_resource
def get_backend():return make_browser_backend()

try:backend=get_backend()
except Exception as error:
    log_browser_event("error",error=error);st.error(user_error_message(error));st.stop()

initialize_chat()
provider_options(backend)
render_sidebar(backend)
session=st.session_state.active_chat
log_browser_event("page_render",session=session,provider=st.session_state.browser_provider)
render_header_actions(backend,session)

with st.container(horizontal=True,horizontal_alignment="center"):
    with st.container(width=960):
        # History and notices grow between reruns. Keep them in one stable
        # sibling slot so an old composer cannot linger between chat messages.
        with st.container(key="conversation_content"):
            opened=st.session_state.chat_opened
            turns=backend.turns(session) if opened else []
            if not opened:
                st.space("large");st.space("large")
                st.title("What would you like to build?",text_alignment="center",anchor=False)
                st.caption("Ask, explore, and work with your agent.",text_alignment="center")
                st.space("large")
            else:
                if len(turns)>100:st.caption("Showing the latest 100 turns. The conversation download includes the full archive.")
                for turn in turns[-100:]:
                    with st.chat_message("user"):st.markdown(turn["question"].split("\n\nUploaded document evidence (",1)[0])
                    with st.chat_message("assistant"):st.markdown(turn["answer"])
                unsaved=st.session_state.get("unsaved_response",{}).get(session)
                if unsaved:
                    with st.chat_message("user"):st.markdown(unsaved["question"].split("\n\nUploaded document evidence (",1)[0])
                    with st.chat_message("assistant"):st.markdown(unsaved["answer"])
                with st.popover("Conversation",icon=":material/more_horiz:",type="tertiary"):
                    if turns:
                        if st.download_button("Download conversation",json.dumps(turns,ensure_ascii=False,indent=2),file_name="conversation.json",mime="application/json"):
                            log_browser_event("download_clicked",session=session,turns=len(turns))
                    latest=st.session_state.get("answer_downloads",{}).get(session)
                    if latest:st.download_button("Download latest answer",latest,file_name="answer.md",mime="text/markdown",key="download_answer_"+session)

            for notice in st.session_state.get("chat_notices",[]):st.warning(notice)
            if opened:render_status(st.session_state.get("request_status_by_chat",{}).get(session))
            from agent.interfaces.action_approval import render_pending_actions
            render_pending_actions(backend,session)

        with st.container(border=True,key="message_composer"):
            prompt=st.chat_input("Message JeshlaAutoAI…",key="message",height=100,submit_mode="disable",disabled=st.session_state.get("work_mode","Chat")=="Cowork")
            with st.container(horizontal=True,horizontal_alignment="distribute",vertical_alignment="center"):
                with st.container(horizontal=True,width="content",vertical_alignment="center"):
                    render_upload_menu(session)
                    mode=st.segmented_control("Work mode",["Chat","Cowork"],default="Chat",required=True,format_func=lambda value:"Cowork · Soon" if value=="Cowork" else value,key="work_mode",label_visibility="collapsed")
                render_provider_picker(backend)
        if mode=="Cowork":st.info("Cowork will be the place to configure a project for your agent. Project connection is planned; use Chat for the current agent. GitHub remains parked.")

        if prompt and prompt.strip():
            selected=st.session_state.browser_provider
            start=time.perf_counter()
            try:
                session=ensure_message_chat(backend,prompt)
                log_browser_event("message_started",session=session,provider=selected)
                with st.spinner("Working on your request…"):
                    question=attachment_question(prompt,chat_attachments(session))
                    result=backend.submit_selected(session,question,selected) if hasattr(backend,"submit_selected") else backend.submit(session,question)
                log_browser_event("message_finished",session=session,provider=selected,duration=time.perf_counter()-start,route=result.get("route"))
                remember_status(session,status_label(result),time.perf_counter()-start,result.get("persistence_status"))
                st.session_state.setdefault("answer_downloads",{})[session]=result["answer"]
                st.session_state.chat_notices=result.get("notices",[])
                st.session_state.chat_opened=True
                st.session_state.pop("saved_facts",None)
                if result.get("persistence_status",{}).get("archive_saved") is False:
                    st.session_state.setdefault("unsaved_response",{})[session]={"question":question,"answer":result["answer"]}
                else:st.session_state.setdefault("unsaved_response",{}).pop(session,None)
                st.rerun()
            except Exception as error:
                log_browser_event("error",session=session,provider=selected,duration=time.perf_counter()-start,error=error)
                remember_status(session,"Failed",time.perf_counter()-start)
                st.error(user_error_message(error))
