"""Explicit shared-fact editing through the existing memory command adapter."""
import streamlit as st
from agent.user_errors import user_error_message


def render_memory_editor(backend):
    if st.session_state.pop("memory_reset_confirmation",False):
        st.session_state.memory_confirm=False
    st.caption("Save/update replaces the value under the same name. Forget removes the fact and its revision history from shared memory; archived conversations remain.")
    with st.form("memory_editor"):
        operation=st.radio("Memory action",["Save / update","Forget"],key="memory_operation")
        key=st.text_input("Fact name",max_chars=64,key="memory_key",placeholder="report_format")
        value=st.text_area("Fact value (for save/update)",max_chars=2000,key="memory_edit_value",height=100)
        confirmed=st.checkbox("I confirm this change to memory shared across my chats",key="memory_confirm")
        apply=st.form_submit_button("Apply memory change",width="stretch")
    if apply:
        if not confirmed:
            st.warning("Confirm the shared-memory change before applying it.")
        else:
            try:
                from agent.interfaces.sidebar import ensure_message_chat
                session=ensure_message_chat(backend,"Memory: "+key)
                result=backend.edit_memory(session,"forget" if operation=="Forget" else "save",key,value)
                st.session_state.memory_edit_result=result["answer"]
                st.session_state.memory_reset_confirmation=True
                st.session_state.pop("saved_facts",None)
                st.session_state.chat_notices=result.get("notices",[])
                st.rerun()
            except ValueError as error:st.warning(str(error))
            except Exception as error:st.error(user_error_message(error))
    if st.session_state.get("memory_edit_result"):
        st.info(st.session_state.memory_edit_result)
