"""Read-only project file dialog; paths and previews stay in the selected scope."""
import hashlib
import json
from pathlib import PurePosixPath
import re

import streamlit as st

from agent.interfaces.dialogs import dismiss_dialog
from agent.interfaces.projects import selected_backend
from agent.tools.project_browsing import list_project_folder, preview_project_file


def project_view_key(backend, scope):
    identity = [backend.user, backend.space, backend.project_id, scope["bound_project_root"]]
    return "project_files_" + hashlib.sha256(json.dumps(identity).encode("utf-8")).hexdigest()[:24]


def entry_key(prefix, path):
    return prefix + "_entry_" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:20]


def _label(name):
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~])", r"\\\1", name)


def _close():
    dismiss_dialog()
    st.rerun()


@st.dialog("Project files", width="large", on_dismiss=dismiss_dialog, icon=":material/folder_open:")
def render_project_files(manager):
    try:
        backend = selected_backend(manager)
        if not getattr(backend, "project", None):
            st.info("Select a saved project to browse its files.")
            if st.button("Close", key="close_project_files"):
                _close()
            return
        scope = backend.request_scope()
        if not scope:
            raise ValueError("A selected project is required.")
        prefix = project_view_key(backend, scope)
    except Exception:
        st.warning("The selected project is unavailable or its configuration changed. Select it again in Projects.")
        if st.button("Close", key="close_project_files"):
            _close()
        return

    st.text(backend.project["name"])
    st.caption("Browse local project files. Supported text previews show the first 80 lines; other files are listed by name only.")
    views = st.session_state.setdefault("project_files_views", {})
    view = views.setdefault(prefix, {"folder": ".", "selected": None})
    folder = view.get("folder", ".")
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Project root", icon=":material/home:", key=prefix + "_root", disabled=folder == "."):
            view.update(folder=".", selected=None)
            st.rerun()
        if st.button("Up", icon=":material/arrow_upward:", key=prefix + "_up", disabled=folder == "."):
            view.update(folder=str(PurePosixPath(folder).parent), selected=None)
            st.rerun()
        if st.button("Close", key="close_project_files"):
            _close()
    st.caption("Project /" if folder == "." else "Project / " + folder)

    try:
        listing = list_project_folder(backend, folder)
    except Exception:
        view.update(folder=".", selected=None)
        st.warning("This folder is unavailable or excluded. Return to the project root to continue.")
        return
    if listing.get("truncated"):
        st.warning("This is a bounded folder listing. Additional entries may exist; no full-project inventory is claimed.")
    entries = listing.get("entries", [])
    if not entries:
        st.caption("No visible project files or folders here.")
    with st.container(key=prefix + "_list", height=340):
        for item in entries:
            directory = item["kind"] == "folder"
            previewable = bool(item.get("previewable"))
            if st.button(_label(item["name"]), key=entry_key(prefix, item["path"]),
                         icon=":material/folder:" if directory else ":material/description:",
                         disabled=not directory and not previewable, type="tertiary", width="stretch",
                         help="Open folder" if directory else "Preview text" if previewable else "Listed by name; text preview is unavailable"):
                if directory:
                    view.update(folder=item["path"], selected=None)
                else:
                    view["selected"] = item["path"]
                st.rerun()

    selected = view.get("selected")
    if selected:
        st.divider()
        st.text(selected)
        try:
            # No cached content: every render revalidates project scope and bytes.
            preview = preview_project_file(backend, selected)
        except Exception:
            view["selected"] = None
            st.warning("This file is unavailable, excluded or no longer supports text preview.")
            return
        st.caption("Lines " + str(preview["start_line"]) + "–" + str(preview["end_line"]) + " of " + str(preview["total_lines"]))
        with st.container(key=prefix + "_preview", height=300):
            st.code(preview["content"], language=None, wrap_lines=True)
        if preview.get("truncated"):
            st.caption("More lines exist. This preview covers only the displayed excerpt.")
