"""One composer project picker; configuration is separate from selecting context."""
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
    # Never show the last conversation automatically when switching projects.
    # The scoped catalog retains every saved conversation for explicit selection.
    for key in ("active_chat","chat_draft","chat_opened","chat_picker",*VIEW_KEYS):
        st.session_state.pop(key,None)
    for key in list(st.session_state):
        if key.startswith("memory_") or key in {"saved_facts","chat_notices","last_action_result","archive_results","upload_notice","pending_chat_picker","ui_dialog"}:
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


def project_picker_style():
    st.html("""<style>
    [data-testid="stPopoverBody"]:has(.st-key-project_picker_content) {
        width: min(23rem, calc(100vw - 2rem)); max-height: min(70dvh, 34rem); overflow-y: auto;
    }
    .st-key-project_picker_content { gap: .5rem; }
    .st-key-project_picker_content [class*="st-key-project_name_"] button {
        text-align: left; justify-content: flex-start !important;
    }
    .st-key-project_picker_content hr { margin: .25rem 0; }
    @media (max-width: 640px) {
        [data-testid="stPopoverBody"]:has(.st-key-project_picker_content) {
            position: fixed !important; inset: auto 0 0 0 !important;
            transform: none !important; width: 100vw !important; max-width: 100vw !important;
            height: fit-content; max-height: 75dvh; border-radius: 1rem 1rem 0 0;
            padding-bottom: 1.25rem;
        }
    }
    </style>""")


def render_projects(manager):
    if not hasattr(manager,"project_store"):return
    project_picker_style()
    rows=manager.project_store().list();active=st.session_state.get("selected_project_id","")
    with st.popover("Projects",icon=":material/folder_open:",key="projects_menu"):
        with st.container(key="project_picker_content"):
            st.markdown("**Projects**")
            source=st.segmented_control("Project source",["All","Local","Git"],default="All",
                                        key="project_source_filter",label_visibility="collapsed",width="stretch")
            visible=[row for row in rows if source not in {"Local","Git"} or (row.get("source","local")=="git")== (source=="Git")]
            if not rows:st.caption("Add a project once, then select its name here.")
            elif not visible:st.caption("No configured projects in this category.")
            for row in visible:
                key=row["id"];is_git=row.get("source")=="git"
                with st.container(horizontal=True,vertical_alignment="center",wrap=False,gap="xsmall"):
                    label=row["name"]+(" · Active" if key==active else "")
                    with st.container(key="project_name_"+key):
                        if st.button(label,key="choose_project_"+key,icon=":material/account_tree:" if is_git else ":material/folder:",
                                     type="secondary" if key==active else "tertiary",help=row["root"],width="stretch",wrap=False):
                            switch_project(manager,key);st.rerun()
                    if is_git and st.button(":material/sync:",key="sync_project_"+key,help="Pull fast-forward updates. Local changes prevent syncing."):
                        st.session_state.project_settings_id=key;st.session_state.ui_dialog="project_sync";st.rerun()
                    if st.button(":material/more_vert:",key="project_settings_"+key,help="Project details and connections"):
                        st.session_state.project_settings_id=key;st.session_state.ui_dialog="project_settings";st.rerun()
            st.divider()
            st.button("Add project",key="add_project_menu",icon=":material/create_new_folder:",width="stretch",on_click=begin_project_setup)
            if active:
                if st.button("Clear project selection",key="clear_project_selection",type="tertiary",width="stretch"):
                    switch_project(manager,"");st.rerun()
