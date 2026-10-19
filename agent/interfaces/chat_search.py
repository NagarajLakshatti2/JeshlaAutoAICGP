"""Explicit, bounded navigation through locally archived conversation text."""
import streamlit as st
from agent import browser_activity
from agent.user_errors import user_error_message


def render_chat_search(backend):
    with st.expander("Search conversation text",icon=":material/search:"):
        with st.form("archive_search"):
            query=st.text_input("Words in messages",max_chars=1500,key="archive_query")
            current_only=st.checkbox("Current chat only",key="archive_current_only")
            submitted=st.form_submit_button("Search saved messages",width="stretch")
        if submitted:
            st.session_state.pop("archive_results",None)
            try:
                result=backend.search_chats(query,st.session_state.active_chat if current_only else None)
                st.session_state.archive_results={"result":result,"session":st.session_state.active_chat if current_only else None}
            except ValueError:
                st.warning("Enter 1 to 20 words to search (up to 1,500 characters).")
            except Exception as error:
                st.error(user_error_message(error))
        saved=st.session_state.get("archive_results")
        if not saved:return
        result=saved["result"]
        st.caption("Results for "+("chat "+saved["session"] if saved["session"] else "your saved chats")+". Search does not call an LLM.")
        st.caption("All words must match. Newest first; up to 10 results, 10,000 archived turns and the first 8,000 characters of each message. Older console-only history may not be archived.")
        if not result["matches"]:st.info("No matches in the searched archive. This does not prove the topic was never discussed.")
        if result["truncated"]:st.warning("Search results are limited. Narrow the words or search one chat.")
        for match in result["matches"]:
            st.caption(match["title"]+" · "+match["created_at"])
            st.text("You: "+match["question_excerpt"])
            st.text("Assistant: "+match["answer_excerpt"])
            if st.button("Open chat: "+match["title"],key="archive_open_"+str(match["turn_id"]),width="stretch"):
                chat=match["chat_id"]
                if not backend.get_chat(chat):
                    st.warning("This saved chat is no longer available.")
                    continue
                st.session_state.chat_opened=True
                st.session_state.active_chat=chat
                st.session_state.chat_picker=chat
                st.session_state.pop("chat_notices",None)
                browser_activity.log_browser_event("chat_switched",session=chat,provider=backend.provider)
                st.rerun()
