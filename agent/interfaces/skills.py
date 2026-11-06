"""Project skill preview and user-reviewed chat drafts."""
import streamlit as st


def draft_skill(backend, session, project_id, path):
    if st.session_state.get("active_chat") != session or st.session_state.get("selected_project_id") != project_id:
        return
    from agent.runtime.project_skills import project_skills
    scope = backend.request_scope()
    if not scope or scope["project_id"] != project_id:
        return
    skill = next((row for row in project_skills(scope["bound_project_root"]) if row["path"] == path), None)
    if skill:
        st.session_state.message = ("Use the project skill " + skill["name"] + " for the task below.\n\n"
                                    + skill["content"] + "\n\nTask: ")


def render_skills(backend, session):
    with st.expander("Skills", icon=":material/psychology:"):
        if backend is None or not getattr(backend, "project_id", None):
            st.caption("Select a saved project to browse its skills.")
            return
        from agent.runtime.project_skills import project_skills
        scope = backend.request_scope()
        try:
            rows = project_skills(scope["bound_project_root"])
        except (OSError, UnicodeError):
            st.warning("Project skills could not be read.")
            return
        if not rows:
            st.caption("Add a SKILL.md file under .agents/skills/<name> in this project.")
            return
        for row in rows:
            with st.expander(row["name"]):
                st.code(row["content"], language="markdown")
                st.button("Use in message draft", key="skill_" + row["path"],
                          on_click=draft_skill,
                          args=(backend, session, scope["project_id"], row["path"]))
