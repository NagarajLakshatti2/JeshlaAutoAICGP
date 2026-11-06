"""Review Git changes in the same project panel; execution uses stored approvals."""
import streamlit as st
from agent.interfaces.sidebar import ensure_message_chat
from agent.storage.projects import ProjectConfigurationError


def render_git_review(manager):
    from agent.runtime.git_workspace import selected_git_project
    project_id=st.session_state.get("selected_project_id","")
    if not project_id:
        st.info("Select a saved Git project first.");return
    backend=manager.for_project(project_id)
    try:
        project=selected_git_project(backend)
        listing=backend.git_changes()
    except ProjectConfigurationError as error:
        st.warning(str(error));return
    st.subheader("Review Git changes",anchor=False)
    st.caption(project["name"]+" · "+listing["branch"])
    st.text(project["root"])
    with st.expander("Prepare pull-request draft"):
        base = st.text_input("Base branch", value="main", key="git_pr_base")
        head = st.text_input("Head branch", value=listing["branch"], key="git_pr_head")
        title = st.text_input("PR title", max_chars=200, key="git_pr_title")
        body = st.text_area("PR description", max_chars=12000, key="git_pr_body")
        if st.button("Review PR draft", key="git_pr_prepare"):
            try:
                draft = backend.prepare_git_pr(base, head, title, body)
                st.text(draft["title"])
                st.text("Base " + draft["base_commit"] + " → head " + draft["head_commit"])
                st.markdown(draft["body"])
                st.code(draft["diff"], language="diff")
                import json
                st.download_button("Download reviewed draft", json.dumps(draft, indent=2),
                                   file_name="pull-request-draft.json", mime="application/json")
            except ProjectConfigurationError as error:
                st.warning(str(error))
    st.session_state.setdefault("git_review_mode","Commit")
    mode=st.segmented_control("Action",["Commit","Push","Branch"],key="git_review_mode")
    if mode=="Branch":
        name = st.text_input("New branch name", key="git_new_branch")
        st.caption("Create a local branch at the reviewed commit. The current checkout stays selected.")
        if st.button("Prepare branch review", key="prepare_git_branch"):
            try:
                st.session_state.git_write_review = backend.review_git_branch(name)
            except ProjectConfigurationError as error:
                st.warning(str(error))
    elif mode=="Push":
        st.caption("Review every pending commit before publication. A configured account with write access is required.")
        from urllib.parse import urlsplit
        kind="github" if urlsplit(project["remote_url"]).hostname=="github.com" else "gitlab"
        accounts={row["id"]:row for row in manager.connection_store().list() if row["kind"]==kind}
        choices=["",*accounts];current=project.get("account_id","")
        selected=st.selectbox("Repository account",choices,index=choices.index(current) if current in choices else 0,
            format_func=lambda key:accounts[key]["label"] if key else "Select an account",
            key="git_push_account_"+project_id,
            help="Account verification confirms identity. Repository write permission is checked during publication.")
        if st.button("Save repository account",key="git_push_save_account"):
            try:
                if not selected:raise ProjectConfigurationError("Choose a saved account before preparing push.")
                manager.update_project_account(project_id,selected)
                st.session_state.pop("git_write_review",None)
                st.success("Account selected for this project. Prepare a fresh push review.")
            except ProjectConfigurationError as error:st.warning(str(error))
        if not accounts:st.info("Add your Git account in Settings → Connections first.")
        if st.button("Prepare push review",key="prepare_git_push"):
            try:
                with st.spinner("Preparing exact push review…"):review=backend.review_git_push()
                st.session_state.git_write_review=review
            except ProjectConfigurationError as error:st.warning(str(error))
    else:
        st.caption("Select up to eight source files. A commit is local; push has its own approval.")
        if listing["excluded"]:st.caption("Excluded credential/generated/non-source paths: "+str(listing["excluded"]))
        if listing["truncated"]:st.warning("Only the first 100 changed source paths are shown.")
        paths=st.multiselect("Changed files",listing["files"],max_selections=8,key="git_commit_paths")
        message=st.text_input("Commit message",max_chars=1000,key="git_commit_message")
        author=st.text_input("Author name",max_chars=100,key="git_commit_author")
        email=st.text_input("Author email",key="git_commit_email",help="Use your chosen Git commit email, including a GitHub noreply address if desired.")
        if st.button("Prepare commit review",key="prepare_git_commit"):
            try:
                with st.spinner("Preparing exact commit review…"):review=backend.review_git_commit(paths,message,author,email)
                st.session_state.git_write_review=review
            except ProjectConfigurationError as error:st.warning(str(error))
    review=st.session_state.get("git_write_review")
    expected={"Push":"git_push","Commit":"git_commit","Branch":"git_branch"}[mode]
    if review and review.get("kind")==expected and review.get("project",{}).get("id")==project_id:
        st.markdown("**"+{"Push":"Publish these commits","Commit":"Commit these selected changes","Branch":"Create this local branch"}[mode]+"**")
        st.text("Branch: "+review["state"]["branch"])
        if mode=="Push":
            st.text("Remote: "+review["project"]["remote_url"])
            st.caption(str(len(review["commits"]))+" commit(s) will be published.")
        elif mode=="Commit":
            st.text("Message: "+review["message"])
            st.text("Author: "+review["author_name"]+" <"+review["author_email"]+">")
        st.code(review["diff"],language="diff")
        if st.button("Request exact-action approval",key="request_git_approval",type="primary"):
            try:
                session=ensure_message_chat(backend,"Review Git "+mode.casefold()+" for "+project["name"])
                backend.queue_git_review(session,review)
                st.session_state.pop("git_write_review",None)
                st.session_state.ui_dialog=None;st.rerun()
            except ProjectConfigurationError as error:st.warning(str(error))
