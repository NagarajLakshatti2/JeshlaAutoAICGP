"""Download only explicit snapshots of unchanged, approved file creations."""
import streamlit as st
from agent.interfaces.errors import user_error_message
from agent.actions.receipts import ActionBlocked


def render_generated_files(backend,session,*,key_prefix=""):
    if not hasattr(backend,"generated_files"):return
    with st.expander("Files created by approved actions",icon=":material/download:"):
        st.caption("Up to 20 recent completed actions in this chat. Only unchanged approved text-file creations, up to 1 MB, and verified inspection PNG files, up to 5 MB. Prepare an original-file or ZIP snapshot before downloading; no action is rerun.")
        try:files=backend.generated_files(session)
        except Exception as error:st.error(user_error_message(error));return
        if not files:st.caption("No completed approved file creations in this chat.")
        for item in files:
            st.text(item["path"])
            download_format="Original file"
            if hasattr(backend,"generated_zip_file"):
                download_format=st.selectbox("Download format",["Original file","ZIP archive"],key=key_prefix+"generated_format_"+item["id"])
            # Preserve the original cache key for existing sessions. Keeping ZIP
            # snapshots separate also lets two panes select different formats.
            cache_key=(session,item["id"]) if download_format=="Original file" else (session,item["id"],download_format)
            if st.button("Prepare download",key=key_prefix+"prepare_generated_"+item["id"]):
                # A failed recheck must withdraw the previously prepared button.
                st.session_state.setdefault("generated_downloads",{}).pop(cache_key,None)
                try:
                    prepare=backend.generated_zip_file if download_format=="ZIP archive" else backend.generated_file
                    snapshot=prepare(session,item["id"])
                    st.session_state.setdefault("generated_downloads",{})[cache_key]=snapshot
                except ActionBlocked as error:st.warning(str(error))
                except Exception as error:st.error(user_error_message(error))
            snapshot=st.session_state.get("generated_downloads",{}).get(cache_key)
            if snapshot:st.download_button("Download "+snapshot["name"],snapshot["data"],file_name=snapshot["name"],mime=snapshot["mime"],key=key_prefix+"generated_download_"+item["id"],width="stretch")
