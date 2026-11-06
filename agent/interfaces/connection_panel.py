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
    notice=st.session_state.pop("connection_notice",None)
    if notice:
        kind,message=notice
        getattr(st,kind)(message)
    for row in store.list():
        if row["kind"] not in LABELS and row["kind"]!="jira_mcp":continue
        with st.container(border=True):
            st.markdown("**"+row["label"]+"**")
            label=LABELS.get(row["kind"],"Jira MCP profile")
            is_connected=row["status"]=="verified"
            st.caption(label)
            with st.container(horizontal=True,vertical_alignment="center"):
                st.badge("Connected" if is_connected else "Not connected",
                         icon=":material/check_circle:" if is_connected else ":material/cancel:",
                         color="green" if is_connected else "red")
                if is_connected and row.get("checked_at"):
                    st.caption("Verified "+row["checked_at"])
            if row.get("details",{}).get("account"):st.text("Account: "+row["details"]["account"])
            with st.container(horizontal=True):
                if row["kind"]=="jira_mcp":
                    button_label=("Test connection" if row["status"]=="verified" else "Verify connection" if row.get("credential_present") else "Connect Jira")
                    if st.button(button_label,key="test_connection_"+row["id"]):
                        try:
                            with st.spinner("Complete Atlassian sign-in in your browser…"):
                                backend.test_connection(row["id"])
                            st.success("Jira site verified.");st.rerun()
                        except ProjectConfigurationError as error:st.warning(str(error))
                elif st.button("Test connection",key="test_connection_"+row["id"]):
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
                saved=backend.save_connection(kind,label or LABELS[kind],env_name=env_name,token=token)
                try:
                    backend.test_connection(saved["id"])
                    st.session_state["connection_notice"]=("success","Git account saved and verified.")
                except ProjectConfigurationError as error:
                    st.session_state["connection_notice"]=("warning","Git account saved, but verification failed: "+str(error))
                st.rerun()
            except ProjectConfigurationError as error:st.warning(str(error))
        st.caption("Windows access tokens are encrypted for the server's operating-system user. Tokens never enter a conversation.")
    st.divider();st.markdown("**Jira MCP profiles**")
    st.caption("Save multiple Jira sites and assign the right profile to each project. Connect uses browser OAuth only when clicked. This client is limited to single-product Jira reads; Atlassian documents these as free. Enriched or cross-product search is not enabled.")
    with st.form("save_jira_mcp_profile",clear_on_submit=False):
        jira_label=st.text_input("Connection name",placeholder="Work Jira account",max_chars=100,key="jira_mcp_label")
        jira_url=st.text_input("Jira site URL",placeholder="https://your-company.atlassian.net",max_chars=255,key="jira_mcp_url")
        save_jira=st.form_submit_button("Save Jira profile")
    if save_jira:
        if not jira_url.strip():
            st.error("Enter a Jira site URL, for example https://your-company.atlassian.net.")
        else:
            try:
                backend.save_connection("jira_mcp",jira_label or "Jira MCP",jira_url)
                st.success("Jira profile saved locally. No Jira request was made.");st.rerun()
            except (ProjectConfigurationError, ValueError) as error:
                st.error(str(error))
            except Exception:
                st.error("Could not save the Jira profile. Check the site URL and try again.")
    st.markdown("**Other MCP connectors · Parked**")
    st.caption("GitHub MCP and custom MCP are parked placeholders; these buttons are disabled and do not contact a service. GitHub account access for repository cloning is separate and remains available above.")
    for label in MCP_LABELS[1:]:
        with st.container(horizontal=True,vertical_alignment="center"):
            st.text(label)
            st.button("Connect",key="parked_"+label,disabled=True)
    with st.expander("Planned GitHub MCP project assignments"):
        st.selectbox("Repository connection",["Available after MCP is enabled"],disabled=True,key="parked_repo_connection")
