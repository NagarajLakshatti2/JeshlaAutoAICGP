"""Download only explicit snapshots of unchanged, approved file creations."""
import streamlit as st
from agent.user_errors import user_error_message
from agent.actions.receipts import ActionBlocked


def render_generated_files(backend,session):
    if not hasattr(backend,"generated_files"):return
    with st.expander("Files created by approved actions",icon=":material/download:"):
        st.caption("Up to 20 recent completed actions in this chat. Only unchanged approved text-file creations, up to 1 MB. Prepare a snapshot before downloading; no action is rerun.")
        try:files=backend.generated_files(session)
        except Exception as error:st.error(user_error_message(error));return
        if not files:st.caption("No completed approved file creations in this chat.")
        for item in files:
            st.text(item["path"])
            if st.button("Prepare download",key="prepare_generated_"+item["id"]):
                # A failed recheck must withdraw the previously prepared button.
                st.session_state.setdefault("generated_downloads",{}).pop((session,item["id"]),None)
                try:
                    snapshot=backend.generated_file(session,item["id"])
                    st.session_state.setdefault("generated_downloads",{})[(session,item["id"])]=snapshot
                except ActionBlocked as error:st.warning(str(error))
                except Exception as error:st.error(user_error_message(error))
            snapshot=st.session_state.get("generated_downloads",{}).get((session,item["id"]))
            if snapshot:st.download_button("Download "+snapshot["name"],snapshot["data"],file_name=snapshot["name"],mime=snapshot["mime"],key="generated_download_"+item["id"],width="stretch")
