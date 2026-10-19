"""Compact provider selection and information for the selected provider."""
import streamlit as st

LABELS={"ollama":"Ollama","openrouter":"OpenRouter","groq":"Groq","gemini":"Gemini"}


def provider_options(backend):
    values=list(LABELS)
    if backend.provider not in values:values.insert(0,backend.provider)
    st.session_state.setdefault("browser_provider",backend.provider)
    if st.session_state.browser_provider not in values:st.session_state.browser_provider=backend.provider
    return values


def selected_info(backend):
    provider=st.session_state.get("browser_provider",backend.provider)
    if not hasattr(backend,"provider_info"):return {"provider":provider,"model":"","key_present":None,"local":False,"supported":False}
    try:return backend.provider_info(provider)
    except TypeError:return backend.provider_info()


def render_provider_info(backend):
    with st.popover(":material/info:",help="About the selected provider",key="provider_information",type="tertiary"):
        info=selected_info(backend)
        st.markdown("**"+LABELS.get(info["provider"],info["provider"])+"**")
        st.text("Configured model: "+(info["model"] or "Not configured"))
        st.caption("Uses the configured Ollama server." if info["local"] else "Hosted inference using your configured API key.")
        if info["key_present"] is False:st.warning("API key is missing. Add it locally in .env.")
        st.caption("The configured default model is selected automatically. Availability and quota are checked when you send a request.")


def render_provider_picker(backend):
    st.selectbox("Provider",provider_options(backend),format_func=lambda value:LABELS.get(value,value),key="browser_provider",label_visibility="collapsed",width=165)
