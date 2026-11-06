"""Project selection and saved-project rows shared by the workspace panel."""
import streamlit as st
from agent.interfaces.sidebar import start_chat_draft
from agent.storage.projects import ProjectConfigurationError

VIEW_KEYS=("chat_page_offset","chat_title_filter")


def switch_project(manager,project_id):
    if project_id and not manager.project_store().get(project_id):
        raise ProjectConfigurationError("Project not found in your workspace.")
    old=st.session_state.get("selected_project_id","")
    if old==project_id:return
    views=st.session_state.setdefault("project_views",{})
    views[old]={key:st.session_state[key] for key in VIEW_KEYS if key in st.session_state}
    st.session_state.selected_project_id=project_id
    # Scope the sidebar catalog without automatically opening a saved chat.
    for key in ("active_chat","chat_draft","chat_opened","chat_picker",*VIEW_KEYS):
        st.session_state.pop(key,None)
    for key in list(st.session_state):
        if key.startswith(("memory_","git_commit_","git_review_","project_knowledge_")) or key in {"git_write_review","saved_facts","chat_notices","last_action_result","archive_results","upload_notice","pending_chat_picker","ui_dialog"}:
            st.session_state.pop(key,None)
    start_chat_draft()
    for key,value in views.get(project_id,{}).items():st.session_state[key]=value


def select_project(manager):
    """Compatibility callback for older callers; no selector is rendered."""
    switch_project(manager,st.session_state.project_picker)


def selected_backend(manager):
    if not hasattr(manager,"for_project"):return manager
    return manager.for_project(st.session_state.get("selected_project_id",""))


def begin_project_setup():
    st.session_state.ui_dialog="project_setup"


def render_chat_mode(manager):
    """Return to saved chats outside a project without merging their scopes."""
    selected=bool(st.session_state.get("selected_project_id"))
    if st.button("Chat",key="chat_mode",type="tertiary" if selected else "secondary",
                 help="Show your chats without a selected project"):
        if selected:
            switch_project(manager,"")
            st.session_state.chat_title_filter=""
            st.rerun()


def render_projects(manager):
    """Open a single dialog; never stack a popover over project setup."""
    if not hasattr(manager,"project_store"):return
    if st.button("Projects",icon=":material/folder_open:",key="projects_menu"):
        st.session_state.ui_dialog="projects"


def render_saved_projects(manager):
    notice=st.session_state.pop("project_created_notice",None)
    if notice:st.success(notice)
    rows=manager.project_store().list()
    active=st.session_state.get("selected_project_id","")
    names=[row["name"].casefold() for row in rows]
    duplicate_names={name for name in names if names.count(name)>1}
    st.html("""<style>
    .st-key-saved_projects_list { gap: .35rem; }
    .st-key-saved_projects_list [class*="st-key-project_name_"] button {
        justify-content: flex-start; text-align: left;
    }
    .st-key-saved_projects_list [class*="st-key-project_name_"] button > div {
        justify-content: flex-start !important;
    }
    .st-key-saved_projects_list [class*="st-key-project_name_"] button [data-testid="stMarkdownContainer"] {
        flex: 1; text-align: left;
    }
    </style>""")
    with st.container(key="saved_projects_list",height="content"):
        if not rows:st.caption("No saved projects yet. Add a local folder or Git repository.")
        for row in rows:
            key=row["id"];is_git=row.get("source")=="git"
            with st.container(horizontal=True,vertical_alignment="center",wrap=False,gap="xsmall"):
                label=row["name"]+(" · Active" if key==active else "")
                with st.container(key="project_name_"+key):
                    if st.button(label,key="choose_project_"+key,icon=":material/account_tree:" if is_git else ":material/folder:",
                                 type="secondary" if key==active else "tertiary",help=row["root"],width="stretch",wrap=False):
                        switch_project(manager,key)
                        st.session_state.ui_dialog=None
                        st.rerun()
                    if row["name"].casefold() in duplicate_names:st.caption(row["root"])
                if is_git and st.button(":material/sync:",key="sync_project_"+key,help="Pull fast-forward updates. Local changes prevent syncing."):
                    st.session_state.project_settings_id=key;st.session_state.ui_dialog="project_sync";st.rerun()
                with st.popover(":material/more_vert:",key="project_menu_"+key,help="Project actions"):
                    if st.button("Project details",key="project_details_"+key,icon=":material/settings:",width="stretch"):
                        st.session_state.project_settings_id=key;st.session_state.ui_dialog="project_settings";st.rerun()
                    if st.button("Remove project",key="remove_project_"+key,icon=":material/archive:",width="stretch"):
                        st.session_state.project_remove_id=key;st.session_state.ui_dialog="project_remove";st.rerun()
    archived=[row for row in manager.project_store().list(include_archived=True)
              if row["id"] not in {item["id"] for item in rows}]
    with st.expander("Removed projects"+(f" · {len(archived)}" if archived else ""),expanded=False):
        st.caption("Removed projects are hidden from the active list. Their folders, repositories, chats and settings are preserved.")
        if not archived:st.caption("No removed projects.")
        for row in archived:
            key=row["id"]
            with st.container(horizontal=True,vertical_alignment="center",wrap=False,gap="xsmall"):
                st.text(row["name"])
                if st.button("Restore",key="restore_project_"+key,icon=":material/restore:"):
                    try:
                        manager.project_store().restore(key)
                        st.session_state.project_created_notice=row["name"]+" restored to saved projects."
                        st.rerun()
                    except Exception as error:st.error(str(error))
    st.divider()
    st.button("Add project",key="add_project_menu",icon=":material/create_new_folder:",width="stretch",on_click=begin_project_setup)
    if active:
        if st.button("Clear project selection",key="clear_project_selection",type="tertiary",width="stretch"):
            switch_project(manager,"");st.session_state.ui_dialog=None;st.rerun()
