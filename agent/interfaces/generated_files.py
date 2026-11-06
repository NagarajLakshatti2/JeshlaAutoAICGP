"""Download only explicit snapshots of unchanged, approved file creations."""
import streamlit as st
from agent.interfaces.errors import user_error_message


def _download_payload(generator,session,token):
    """Defer the approved-file integrity check and packaging until clicked."""
    import io
    def load():
        snapshot=generator(session,token)
        return io.BytesIO(snapshot["data"])
    return load


def render_generated_files(backend,session,*,key_prefix=""):
    if not hasattr(backend,"generated_files"):return
    with st.expander("Files created by approved actions",icon=":material/download:"):
        st.caption("Choose a filename to download the approved original or a ZIP copy. Files are checked when downloaded; actions are never rerun.")
        try:files=backend.generated_files(session)
        except Exception as error:st.error(user_error_message(error));return
        if not files:st.caption("No completed approved file creations in this chat.")
        for item in files:
            file_name=str(item["path"]).replace("\\","/").rsplit("/",1)[-1] or "Approved file"
            with st.container(horizontal=True,wrap=True,vertical_alignment="center",gap="small"):
                st.text(file_name)
                st.download_button(
                    "Original",
                    data=_download_payload(backend.generated_file,session,item["id"]),
                    file_name=file_name,
                    mime="application/octet-stream",
                    key=key_prefix+"generated_original_"+item["id"],
                    width="content",
                    icon=":material/download:",
                    help="Download "+file_name+".",
                )
                if hasattr(backend,"generated_zip_file"):
                    st.download_button(
                        file_name+".zip",
                        data=_download_payload(backend.generated_zip_file,session,item["id"]),
                        file_name=file_name+".zip",
                        mime="application/zip",
                        key=key_prefix+"generated_zip_"+item["id"],
                        width="content",
                        icon=":material/download:",
                        help="Download a ZIP copy of "+file_name+".",
                    )
