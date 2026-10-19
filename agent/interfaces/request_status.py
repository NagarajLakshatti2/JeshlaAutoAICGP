"""Browser-session request status, kept separate for each conversation."""
import streamlit as st


def status_label(result):
    status=result.get("task_status")
    outcome=result.get("execution_outcome")
    if status=="awaiting_input":return "Waiting for your input or approval"
    if status=="incomplete" or outcome in {"partial","blocked"}:return "Incomplete"
    if status=="failed":return "Failed"
    if status=="completed" or outcome=="completed":return "Completed"
    return "Response returned"


def remember_status(session,label,duration=None,persistence=None):
    record={"label":label,"duration":duration,"persistence":persistence}
    st.session_state.setdefault("request_status_by_chat",{})[session]=record
    return record


def render_status(record):
    if not record:return
    label=record["label"]
    text="Last request: "+label
    if record.get("duration") is not None:text+=f" · {record['duration']:.1f}s"
    if label in {"Failed","Incomplete"}:st.warning(text)
    elif label=="Completed":st.caption(text)
    else:st.caption(text)
    persistence=record.get("persistence")
    if isinstance(persistence,dict) and (persistence.get("archive_saved") is False or persistence.get("checkpoint_saved") is False):
        st.warning("Conversation saving was incomplete. Check the notices and action receipts before repeating any action.")

