"""Git account setup and an explicitly parked MCP design for the free-only plan."""
import os
import streamlit as st
from agent.storage.projects import ProjectConfigurationError

LABELS={"github":"GitHub account","gitlab":"GitLab account"}
MCP_LABELS=("Jira MCP","GitHub MCP","Custom MCP server")


def render_connections(backend):
    if not hasattr(backend,"connection_store"):
        st.caption("Connection settings are available with the full project backend.");return
    st.caption("Connect a Git account once for private repository access. Public repositories can be cloned without an account.")
    store=backend.connection_store()
    for row in store.list():
        if row["kind"] not in LABELS:continue
        with st.container(border=True):
            st.markdown("**"+row["label"]+"**")
            st.caption(LABELS[row["kind"]]+" · "+("Verified "+row["checked_at"] if row["status"]=="verified" else "Configured · not yet verified"))
            if row.get("details",{}).get("account"):st.text("Account: "+row["details"]["account"])
            with st.container(horizontal=True):
                if st.button("Test connection",key="test_connection_"+row["id"]):
                    try:
                        with st.spinner("Checking account…"):backend.test_connection(row["id"])
                        st.success("Account verified.");st.rerun()
                    except ProjectConfigurationError as error:st.warning(str(error))
                if st.button("Disconnect",key="disconnect_connection_"+row["id"]):
                    store.disconnect(row["id"]);st.rerun()
    with st.expander("Add Git account",icon=":material/account_tree:"):
        kind=st.selectbox("Provider",["github","gitlab"],format_func=LABELS.__getitem__,key="connection_kind")
        modes=["Environment variable"]+(["Access token"] if os.name=="nt" else [])
        auth=st.selectbox("Credential source",modes,key="connection_auth")
        with st.form("save_connection_form",clear_on_submit=True):
            label=st.text_input("Connection name",placeholder="My "+LABELS[kind],max_chars=100,key="connection_label")
            env_name=st.text_input("Environment variable name",placeholder="GITHUB_TOKEN" if kind=="github" else "GITLAB_TOKEN",key="connection_env") if auth=="Environment variable" else ""
            token=st.text_input("Access token",type="password",key="connection_secret") if auth=="Access token" else ""
            save=st.form_submit_button("Save account")
        if save:
            try:
                if not env_name and not token:raise ProjectConfigurationError("Choose an environment-variable credential or enter an access token.")
                backend.save_connection(kind,label or LABELS[kind],env_name=env_name,token=token)
                st.success("Account configuration saved. Use Test connection when ready.");st.rerun()
            except ProjectConfigurationError as error:st.warning(str(error))
        st.caption("Windows access tokens are encrypted for the server's operating-system user. Tokens never enter a conversation.")
    st.divider();st.markdown("**MCP · Parked**")
    st.caption("Design preview for the free-only plan. Free access has not been confirmed; these controls do not contact a service.")
    for label in MCP_LABELS:
        with st.container(horizontal=True,vertical_alignment="center"):
            st.text(label)
            st.button("Connect",key="parked_"+label,disabled=True)
    with st.expander("Planned project assignments"):
        st.selectbox("Jira project",["Available after MCP is enabled"],disabled=True,key="parked_jira_project")
        st.selectbox("Repository connection",["Available after MCP is enabled"],disabled=True,key="parked_repo_connection")
