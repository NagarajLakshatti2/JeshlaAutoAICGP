"""Explicit project document previews, local indexing and scoped search."""
import hashlib
import streamlit as st
from agent.interfaces.attachments import EXTENSIONS, extract_attachment


def render_project_knowledge(backend):
    if not hasattr(backend, "project_documents"):
        return
    key = "project_knowledge_" + backend.project_id + "_"
    with st.expander("Project documents", icon=":material/library_books:"):
        st.caption("Saved text snapshots are shared across chats in this project only. Keyword search runs locally; no embedding download or paid service is used. Relevant excerpts may be sent to the selected provider when you ask about these documents.")
        try:
            documents = backend.project_documents().list()
        except ValueError as error:
            st.warning(str(error)); return
        st.caption(str(len(documents)) + "/20 saved documents. Matching filenames replace their saved snapshot. Original files and ordinary chat attachments are unchanged.")
        uploads = st.file_uploader("Add project documents", type=list(EXTENSIONS), accept_multiple_files=True,
                                   max_upload_size=1, key=key + "uploads")
        if st.button("Preview project documents", key=key + "preview"):
            st.session_state.pop(key + "draft", None)
            try:
                if not uploads or len(uploads) > 5:
                    raise ValueError("Choose one to five supported documents, up to 1 MB each.")
                st.session_state[key + "draft"] = [extract_attachment(item.name, item.getvalue()) for item in uploads]
            except ValueError as error:
                st.warning(str(error))
        staged = st.session_state.get(key + "draft")
        if staged:
            for item in staged:
                st.text(item["name"] + " · " + str(len(item["text"])) + " extracted characters")
                if item["truncated"]:
                    st.warning("This document has a limited extraction; only that excerpt will be indexed.")
            chosen = st.selectbox("Preview extracted document", range(len(staged)), format_func=lambda i: staged[i]["name"], key=key + "choice")
            st.text_area("Extracted text", staged[chosen]["text"], disabled=True, height=150, key=key + "text_" + hashlib.sha256(staged[chosen]["text"].encode()).hexdigest()[:16])
            st.caption("Extraction limits: 12,000 characters per file; PDF first 10 pages; XLSX first 3 sheets/100 rows/30 columns. No OCR or formula recalculation. Citations identify extracted-character ranges.")
            if st.button("Save documents to this project", key=key + "save", type="primary"):
                try:
                    backend.project_documents().save(staged)
                    st.session_state.pop(key + "draft", None)
                    st.session_state.pop(key + "results", None)
                    st.rerun()
                except ValueError as error:
                    st.warning(str(error))
        for item in documents:
            with st.container(horizontal=True, vertical_alignment="center"):
                st.text(item["name"] + " · " + str(item["characters"]) + " characters")
                if st.button(":material/delete:", key=key + "remove_" + item["id"], help="Remove this saved snapshot from project search; original file is unchanged"):
                    try:
                        backend.project_documents().remove(item["id"], item["sha256"])
                        st.session_state.pop(key + "results", None)
                        st.rerun()
                    except ValueError as error:
                        st.warning(str(error))
        query = st.text_input("Search saved project documents", key=key + "query")
        if st.button("Search project documents", key=key + "search", disabled=not bool(documents)):
            try:
                st.session_state[key + "results"] = backend.search_project_documents(query)
            except ValueError as error:
                st.warning(str(error))
        results = st.session_state.get(key + "results")
        if results is not None:
            if not results["sources"]:
                st.info("No matching excerpt in this project's saved documents.")
            for source in results["sources"]:
                st.text(source["source"] + " · " + source["location"] + " · [" + source["ref"] + "]")
                st.text(source["text"])
            st.caption(results["note"])
