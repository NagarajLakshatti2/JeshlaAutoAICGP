"""One-time Local/Git setup, selected-project details and explicit sync."""
import streamlit as st
from agent.storage.projects import ProjectConfigurationError
from agent.interfaces.dialogs import dismiss_dialog
from agent.interfaces.projects import switch_project,render_saved_projects
from agent.interfaces.folder_picker import open_folder_picker


def problem(error):
    if isinstance(error,ProjectConfigurationError):st.warning(str(error))
    else:st.error("Project setup could not complete. Check folder access and configuration.")


def project_setup_dialog(manager):
    mode=st.segmented_control("Project type",["Local","Git repositories","New project"],default="Local",
                              key="setup_project_type",persist_state="session",width="stretch",label_visibility="collapsed")
    if mode=="New project":
        from agent.interfaces.project_creation import render_project_creation
        render_project_creation(manager);return
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
        mode=st.selectbox("Working copy",["Clone repository","Use existing checkout"],key="git_setup_mode",persist_state="session")
        name=st.text_input("Project name",max_chars=100,key="git_project_name",persist_state="session")
        url=st.text_input("Repository URL",key="git_repository_url",persist_state="session",placeholder="https://github.com/owner/repository")
        accounts=[row for row in manager.connection_store().list() if row["kind"] in {"github","gitlab"}]
        by_id={row["id"]:row for row in accounts}
        account=st.selectbox("Repository access",["",*by_id],format_func=lambda key:by_id[key]["label"] if key else "Public repository (no account)",key="git_project_account",persist_state="session")
        if not accounts:
            st.caption("Private repository? Add a GitHub/GitLab account in Settings → Connections, then select it here.")
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
    if row.get("source")=="git" and st.button("Review commit / push",key="open_git_review",icon=":material/commit:"):
        switch_project(manager,row["id"])
        st.session_state.project_settings_id=row["id"];st.session_state.ui_dialog="project_git";st.rerun()
    from agent.interfaces.project_knowledge import render_project_knowledge
    render_project_knowledge(manager.for_project(row["id"]))
    st.caption("Conversations, memory, approvals and generated downloads stay scoped to this project.")
    st.markdown("**Jira project connection**")
    st.caption("Assign the verified Jira profile and its Jira project key here. Jira reads use this project-specific assignment; no issue changes are enabled.")
    profiles={x["id"]:x for x in manager.connection_store().list() if x["kind"]=="jira_mcp"}
    binding=manager.project_store().bindings(row["id"]).get("jira_mcp",{})
    if profiles:
        choices=["",*profiles]
        current=binding.get("connection_id","")
        selected=st.selectbox("Jira account profile",choices,index=choices.index(current) if current in choices else 0,
                              format_func=lambda key:profiles[key]["label"] if key else "Choose a saved Jira profile",
                              key="jira_profile_"+row["id"])
        project_key=st.text_input("Jira project key",value=binding.get("options",{}).get("project_key",""),
                                  placeholder="For example, DEMO",max_chars=64,key="jira_project_key_"+row["id"])
        if st.button("Save Jira project assignment",key="save_jira_assignment_"+row["id"]):
            try:
                manager.assign_connection(row["id"],"jira_mcp",selected,{"project_key":project_key.strip()})
                st.success("Jira project assignment saved locally. No Jira request was made.");st.rerun()
            except Exception as error:problem(error)
        if binding and st.button("Remove Jira project assignment",key="remove_jira_assignment_"+row["id"]):
            try:manager.remove_connection_assignment(row["id"],"jira_mcp");st.success("Jira assignment removed.");st.rerun()
            except Exception as error:problem(error)
    else:
        st.caption("Add a Jira profile in Settings → Connections first.")
    if st.button("Select this project",key="select_project_details"):
        switch_project(manager,row["id"]);st.session_state.ui_dialog=None;st.rerun()


def project_remove_dialog(manager):
    project_id=st.session_state.get("project_remove_id","")
    row=manager.project_store().get(project_id)
    if not row:
        st.warning("This project is no longer available.")
        return
    st.markdown("Remove **"+row["name"]+"** from your saved projects?")
    st.caption("This hides it from the active project list. Its folder or Git repository, project chats, memory and settings are preserved. You can restore it later under Removed projects.")
    st.caption(row["root"])
    col_remove,col_cancel=st.columns(2)
    with col_remove:
        if st.button("Remove from list",key="confirm_remove_project",type="primary",width="stretch"):
            try:
                if st.session_state.get("selected_project_id")==project_id:
                    switch_project(manager,"")
                manager.project_store().archive(project_id)
                st.session_state.ui_dialog="projects"
                st.session_state.project_created_notice=row["name"]+" removed from saved projects. The project files were kept."
                st.rerun()
            except Exception as error:problem(error)
    with col_cancel:
        if st.button("Cancel",key="cancel_remove_project",width="stretch"):
            st.session_state.ui_dialog="projects";st.rerun()


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


@st.dialog("Saved projects",width="small",on_dismiss=dismiss_dialog,icon=":material/folder_open:")
def project_panel_dialog(manager):
    """All project views replace content inside this one dialog."""
    view=st.session_state.get("ui_dialog")
    st.html("""<style>
    [role="dialog"]:has(.st-key-project_panel) {
        max-height: calc(100dvh - 6rem); overflow-y: auto;
    }
    </style>""")
    with st.container(key="project_panel"):
        if view=="folder_picker":
            from agent.interfaces.folder_picker import folder_dialog
            st.subheader("Choose project folder",anchor=False)
            folder_dialog()
            return
        if view!="projects":
            if st.button("Back to saved projects",icon=":material/arrow_back:",key="back_saved_projects",type="tertiary"):
                st.session_state.ui_dialog="projects";st.rerun()
        if view=="project_setup":
            st.subheader("Add project",anchor=False)
            project_setup_dialog(manager)
        elif view=="project_settings":
            st.subheader("Project details",anchor=False)
            project_settings_dialog(manager)
        elif view=="project_remove":
            st.subheader("Remove project",anchor=False)
            project_remove_dialog(manager)
        elif view=="project_git":
            from agent.interfaces.git_panel import render_git_review
            render_git_review(manager)
        elif view=="project_sync":
            st.subheader("Sync repository",anchor=False)
            project_sync_dialog(manager)
        else:
            render_saved_projects(manager)


def render_project_dialogs(manager):
    if st.session_state.get("ui_dialog") == "project_terminal":
        from agent.interfaces.project_terminal import render_project_terminal
        render_project_terminal(manager)
        return
    if st.session_state.get("ui_dialog")=="project_files":
        from agent.interfaces.project_files import render_project_files
        render_project_files(manager)
        return
    if st.session_state.get("ui_dialog") in {"projects","project_setup","folder_picker","project_settings","project_remove","project_sync","project_git"}:
        project_panel_dialog(manager)
