"""Review durable pending actions; rerenders never grant approval."""
import json
import streamlit as st
from agent.actions.receipts import ActionBlocked
from agent.interfaces.errors import user_error_message
from agent.interfaces.activity import log_browser_event

def approval_answer_for_display(answer):
    """Label the historical approval stage without rewriting saved transcripts."""
    prefix="Action is waiting for your browser approval."
    if not answer.startswith(prefix):return answer
    shown=answer.replace(prefix,"Approval requested at this stage of the conversation.",1)
    return shown.replace("\n\nTask status: incomplete.","",1)


def render_pending_actions(backend,session,turns=()):
    # Older adapter fakes remain usable for existing chat-only tests.
    if not hasattr(backend,"pending_actions"):return
    try:pending=backend.pending_actions(session)
    except Exception as error:
        st.error(user_error_message(error));return
    last=st.session_state.get("last_action_result")
    if last and last["session"]==session:
        # The transcript is the primary display. Keep a fallback when saving
        # the action exchange failed; never execute or hide a missing receipt.
        if not any(turn.get("answer")==last["answer"] for turn in turns):
            st.info(last["answer"])
    if not pending:return
    st.subheader("Actions waiting for your approval")
    st.caption("Review the exact project and arguments. Approval runs only this action. Proposals expire after ten minutes; changed file targets require a fresh proposal.")
    for item in pending:
        token=item["id"];proposal=item["proposal"]
        with st.form("action_"+token):
            st.write("**"+proposal["action"]+"**")
            st.code(json.dumps(proposal,ensure_ascii=False,indent=2),language="json")
            left,right=st.columns(2)
            approve=left.form_submit_button("Approve exact action",type="primary",key="approve_"+token)
            decline=right.form_submit_button("Decline",key="decline_"+token)
        if approve or decline:
            try:
                with st.spinner("Applying your decision…"):
                    result=backend.decide_action(session,token,bool(approve))
                st.session_state.last_action_result={"session":session,"answer":result["answer"],"decision":"approved" if approve else "declined"}
                from agent.interfaces.request_status import remember_status
                remember_status(session,"Action returned" if approve else "Action declined")
                st.session_state.chat_notices=result.get("notices",[])
                log_browser_event("action_approved" if approve else "action_declined",session=session,provider=backend.provider)
            except ActionBlocked as error:
                from agent.interfaces.request_status import remember_status
                remember_status(session,"Incomplete")
                st.session_state.last_action_result={"session":session,"answer":str(error)}
            except Exception as error:
                st.error(user_error_message(error));return
            st.rerun()
