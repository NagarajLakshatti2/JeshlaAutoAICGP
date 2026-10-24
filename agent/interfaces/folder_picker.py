"""Bounded, explicit folder browsing on the machine running the agent."""
import os
from pathlib import Path
import streamlit as st
from agent.interfaces.dialogs import dismiss_dialog
from agent.storage.projects import ProjectConfigurationError,validate_local_folder


def open_folder_picker(target,*,clone_parent=False):
    existing=st.session_state.get(target,"")
    path=Path(existing).expanduser() if existing else Path.home()
    if not path.is_dir():path=path.parent
    st.session_state.folder_browser_path=str(path if path.is_dir() else Path.home())
    st.session_state.folder_browser_target=target
    st.session_state.folder_browser_clone_parent=clone_parent
    st.session_state.ui_dialog="folder_picker"


def folder_entries(folder,limit=150):
    root=Path(validate_local_folder(folder));rows=[];limited=False
    try:
        with os.scandir(root) as entries:
            for index,item in enumerate(entries):
                if index>=2000:limited=True;break
                if item.is_dir(follow_symlinks=False):
                    rows.append(item.name)
                    if len(rows)>=limit:limited=True;break
    except OSError:raise ProjectConfigurationError("This folder cannot be browsed by the server.") from None
    return root,sorted(rows,key=str.casefold),limited


@st.dialog("Choose project folder",width="medium",on_dismiss=dismiss_dialog,icon=":material/folder_open:")
def folder_dialog():
    st.caption("Folders belong to the computer running JeshlaAutoAI. Select a folder; its files are not uploaded.")
    path=st.session_state.get("folder_browser_path",str(Path.home()))
    with st.form("folder_path_form"):
        entered=st.text_input("Folder path",value=path,key="folder_browser_entered")
        navigate=st.form_submit_button("Go to folder")
    if navigate:
        try:st.session_state.folder_browser_path=validate_local_folder(entered)
        except ProjectConfigurationError as error:st.warning(str(error));return
        st.session_state.pop("folder_browser_entered",None);st.rerun()
    try:root,names,limited=folder_entries(path)
    except ProjectConfigurationError as error:st.warning(str(error));return
    if os.name=="nt":
        import ctypes
        mask=ctypes.windll.kernel32.GetLogicalDrives()
        drives=[chr(65+i)+":\\" for i in range(26) if mask&(1<<i)]
        with st.container(horizontal=True):
            for drive in drives:
                if st.button(drive,key="browse_drive_"+drive[:1]):
                    st.session_state.folder_browser_path=drive;st.session_state.pop("folder_browser_entered",None);st.rerun()
    st.caption(str(root))
    with st.container(height=240,border=True):
        if root.parent!=root and st.button("Parent folder",icon=":material/arrow_upward:",width="stretch"):
            st.session_state.folder_browser_path=str(root.parent);st.session_state.pop("folder_browser_entered",None);st.rerun()
        for name in names:
            if st.button(name,key="folder_child_"+name,icon=":material/folder:",width="stretch"):
                st.session_state.folder_browser_path=str(root/name);st.session_state.pop("folder_browser_entered",None);st.rerun()
        if not names:st.caption("No subfolders.")
        if limited:st.caption("List is limited. Enter a full folder path to navigate directly.")
    with st.container(horizontal=True):
        if st.button("Use this folder",type="primary",key="use_browsed_folder"):
            selected=root
            if st.session_state.get("folder_browser_clone_parent"):
                from urllib.parse import urlsplit
                name=Path(urlsplit(st.session_state.get("git_repository_url","")).path).name.removesuffix(".git") or "repository"
                selected=root/name
            st.session_state[st.session_state.folder_browser_target]=str(selected)
            st.session_state.ui_dialog="project_setup";st.rerun()
        if st.button("Cancel",key="cancel_folder_browser"):
            st.session_state.ui_dialog="project_setup";st.rerun()
