"""Review every new project file before a separately approved creation."""
import json
import streamlit as st
from agent.interfaces.folder_picker import open_folder_picker


def render_project_creation(manager):
    st.caption("Create a new source folder from a reviewed starter. Existing destinations are rejected. Dependencies, commands, tests and Git are separate steps.")
    name = st.text_input("Project name", key="create_project_name", max_chars=100)
    parent = st.text_input("Parent folder", key="create_project_parent", placeholder="Choose an existing parent folder")
    if st.button("Choose parent folder", key="choose_create_project_parent", icon=":material/folder_open:"):
        open_folder_picker("create_project_parent"); st.rerun()
    template = st.selectbox("Starter", ["python", "java-playwright"], format_func=lambda x: "Python package" if x == "python" else "Playwright Java / Gradle", key="create_project_template")
    package = st.text_input("Package name", value="jeshla_demo" if template == "python" else "com.jeshla.demo", key="create_project_package_" + template,
                            help="Dots create parent/child package folders.")
    inputs = {"name": name, "parent": parent, "template": template, "package": package}
    review = st.session_state.get("project_creation_review")
    if review and review["inputs"] != inputs:
        try: manager.cancel_new_project(review["token"])
        except ValueError: pass
        st.session_state.pop("project_creation_review", None); review = None
    if st.button("Prepare project review", key="prepare_new_project"):
        try:
            review = {**manager.prepare_new_project(name, parent, template, package), "inputs": inputs}
            st.session_state.project_creation_review = review
        except ValueError as error:
            st.warning(str(error))
    if not review:
        return
    try:
        status = manager.new_project_status(review["token"])
    except ValueError as error:
        st.warning(str(error)); return
    plan = review["proposal"]["arguments"]["plan"]
    st.text("Destination: " + plan["destination"])
    st.caption(str(len(plan["files"])) + " files · " + str(plan["total_bytes"]) + " bytes in this exact review")
    for item in plan["files"]:
        with st.expander(item["relative_path"]):
            st.code(item["content"], language="text", wrap_lines=True)
    with st.expander("Exact creation action"):
        st.code(json.dumps(review["proposal"], ensure_ascii=False, indent=2), language="json", wrap_lines=True)
    if status["proposal"] not in {"pending", "completed"}:
        st.warning("Creation review is " + status["proposal"] + ". Inspect its saved receipt and destination before preparing another action; no automatic retry or cleanup is performed.")
        return
    approval_label = "Register created project" if status["proposal"] == "completed" else "Approve and create project"
    if st.button(approval_label, key="approve_new_project", type="primary"):
        try:
            result = manager.create_new_project(review["token"], review["name"])
            st.session_state.pop("project_creation_review", None)
            st.session_state.project_created_notice = "Created " + result["project"]["name"] + ". Select its name to work in it. No dependencies were installed or tests run."
            st.session_state.ui_dialog = "projects"
            st.rerun()
        except ValueError as error:
            st.warning(str(error))
        except OSError:
            st.error("Project setup could not finish. Inspect the saved action receipt and created folder before retrying; existing files will not be overwritten.")
    if status["proposal"] == "pending" and st.button("Cancel creation review", key="cancel_new_project"):
        try:
            manager.cancel_new_project(review["token"])
            st.session_state.pop("project_creation_review", None)
            st.rerun()
        except ValueError as error:
            st.warning(str(error))
