"""One-time Local/Git setup, selected-project details and explicit sync."""
from pathlib import Path
import streamlit as st
from agent.storage.projects import ProjectConfigurationError
from agent.interfaces.dialogs import dismiss_dialog
from agent.interfaces.projects import switch_project
from agent.interfaces.folder_picker import open_folder_picker


def problem(error):
    if isinstance(error,ProjectConfigurationError):st.warning(str(error))
    else:st.error("Project setup could not complete. Check folder access and configuration.")


@st.dialog("Add project",width="medium",on_dismiss=dismiss_dialog,icon=":material/create_new_folder:")
def project_setup_dialog(manager):
    mode=st.segmented_control("Project type",["Local","Git repositories"],default="Local",
                              key="setup_project_type",width="stretch",label_visibility="collapsed")
    if mode!="Git repositories":
        name=st.text_input("Project name",max_chars=100,key="new_project_name",persist_state="session")
        folder=st.text_input("Project folder",key="new_project_folder",persist_state="session",placeholder="Choose an existing folder")
        if st.button("Choose folder",icon=":material/folder_open:",key="choose_local_folder"):
            open_folder_picker("new_project_folder");st.rerun()
        if st.button("Save project",type="primary",key="save_local_project",width="stretch"):
            try:
                row=manager.add_project(name,folder)
                switch_project(manager,row["id"]);st.session_state.ui_dialog=None;st.rerun()
            except Exception as error:problem(error)
    else:
        st.caption("GitHub.com / GitLab.com · standard Git operations. No paid service is enabled.")
        mode=st.selectbox("Working copy",["Clone repository","Use existing checkout"],key="git_setup_mode")
        name=st.text_input("Project name",max_chars=100,key="git_project_name",persist_state="session")
        url=st.text_input("Repository URL",key="git_repository_url",persist_state="session",placeholder="https://github.com/owner/repository")
        accounts=[row for row in manager.connection_store().list() if row["kind"] in {"github","gitlab"}]
        by_id={row["id"]:row for row in accounts}
        account=st.selectbox("Repository access",["",*by_id],format_func=lambda key:by_id[key]["label"] if key else "Public repository",key="git_project_account")
        if not accounts:
            st.caption("For private repositories, configure your GitHub/GitLab account in Settings → Connections.")
        destination=st.text_input("Local destination" if mode=="Clone repository" else "Existing checkout folder",key="git_destination",persist_state="session",
                                  placeholder="A new folder for a clone" if mode=="Clone repository" else "Repository root folder")
        if st.button("Choose folder",icon=":material/folder_open:",key="choose_git_destination"):
            open_folder_picker("git_destination",clone_parent=mode=="Clone repository");st.rerun()
        label="Clone and save project" if mode=="Clone repository" else "Save repository project"
        if st.button(label,type="primary",key="save_git_project",width="stretch"):
            try:
                with st.spinner("Configuring working copy…"):
                    row=(manager.clone_project(name,url,destination,account) if mode=="Clone repository"
                         else manager.attach_git_project(name,destination,url,account))
                switch_project(manager,row["id"]);st.session_state.ui_dialog=None;st.rerun()
            except Exception as error:problem(error)


@st.dialog("Project details",width="medium",on_dismiss=dismiss_dialog,icon=":material/folder:")
def project_settings_dialog(manager):
    row=manager.project_store().get(st.session_state.get("project_settings_id",""))
    if not row:st.warning("This project is no longer available.");return
    st.markdown("**"+row["name"]+"**");st.text(row["root"])
    st.caption("Git working copy" if row.get("source")=="git" else "Local folder")
    if row.get("remote_url"):
        st.text(row["remote_url"])
        from urllib.parse import urlsplit
        kind="github" if urlsplit(row["remote_url"]).hostname=="github.com" else "gitlab"
        accounts={x["id"]:x for x in manager.connection_store().list() if x["kind"]==kind}
        choices=["",*accounts];current=row.get("account_id","")
        account=st.selectbox("Repository account",choices,index=choices.index(current) if current in choices else 0,
                             format_func=lambda key:accounts[key]["label"] if key else "Public repository",key="project_repository_account_"+row["id"])
        if st.button("Save repository account",key="save_project_repository_account"):
            try:manager.update_project_account(row["id"],account);st.success("Repository access updated.")
            except Exception as error:problem(error)
    st.caption("Conversations, memory, approvals and generated downloads stay scoped to this project.")
    st.info("Jira/GitHub MCP is parked for the free-only plan. No new MCP connection or remote MCP action is enabled.")
    if st.button("Select this project",key="select_project_details"):
        switch_project(manager,row["id"]);st.session_state.ui_dialog=None;st.rerun()


@st.dialog("Sync repository",width="medium",on_dismiss=dismiss_dialog,icon=":material/sync:")
def project_sync_dialog(manager):
    row=manager.project_store().get(st.session_state.get("project_settings_id",""))
    if not row or row.get("source")!="git":st.warning("Choose a configured Git repository.");return
    st.markdown("**"+row["name"]+"**");st.text(row["root"]);st.text(row["remote_url"])
    st.caption("Pull updates using fast-forward only. Local changes or a diverged branch stop the operation. This does not push.")
    if st.button("Sync now",key="confirm_project_sync",type="primary"):
        try:
            with st.spinner("Syncing repository…"):manager.sync_project(row["id"])
            st.success("Repository synchronized. No push was performed.")
        except Exception as error:problem(error)


def render_project_dialogs(manager):
    dialog=st.session_state.get("ui_dialog")
    if dialog=="project_setup":project_setup_dialog(manager)
    elif dialog=="folder_picker":
        from agent.interfaces.folder_picker import folder_dialog
        folder_dialog()
    elif dialog=="project_settings":project_settings_dialog(manager)
    elif dialog=="project_sync":project_sync_dialog(manager)
