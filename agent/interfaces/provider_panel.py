"""Explicit next-start model settings, without secret values or hot switching."""
import streamlit as st


def render_provider_panel(backend,inline=False):
    with st.container() if inline else st.popover("Model settings",icon=":material/settings:",width="stretch"):
        info=backend.provider_info()
        st.caption("Provider: "+info["provider"])
        st.text("Configured model: "+(info["model"] or "Not configured"))
        if not info["supported"]:
            st.warning("Choose ollama, openrouter, groq or gemini in your local configuration.")
        elif info["local"]:
            st.caption("Ollama inference runs on its configured server; no API key is required.")
        elif info["key_present"]:
            st.caption("API key is present. Its value is hidden.")
        else:
            st.warning("API key is missing. Configure it locally before sending a request.")
        st.caption("Configuration only: connection, model access and remaining quota have not been checked.")
        st.markdown("To change service, edit **LLM_PROVIDER** and the provider's **MODEL** setting in your local `.env`, then restart Streamlit and any running console agent. Your saved chats remain available.")
        if hasattr(backend,"save_model_settings"):
            st.caption("Save the next-start configuration below. API keys and the running provider remain unchanged. Model availability is checked only when a request is made.")
            if st.session_state.pop("reset_settings_confirmation",False):st.session_state.confirm_settings=False
            with st.form("model_settings_editor"):
                provider=st.selectbox("Provider for next restart",["ollama","openrouter","groq","gemini"],index=["ollama","openrouter","groq","gemini"].index(info["provider"]) if info["supported"] else 0,key="next_provider")
                model=st.text_input("Model ID for next restart",max_chars=200,key="next_model")
                confirmed=st.checkbox("Save this provider and model to local .env",key="confirm_settings")
                save=st.form_submit_button("Save model settings",width="stretch")
            if save:
                if not confirmed:st.warning("Confirm the exact provider/model change before saving.")
                else:
                    try:
                        result=backend.save_model_settings(provider,model)
                        st.session_state.reset_settings_confirmation=True
                        st.session_state.saved_settings_notice="Saved "+result["provider"]+" / "+result["model"]+". Restart Streamlit and the console to apply. Environment overrides may take precedence."
                        st.rerun()
                    except ValueError as error:st.warning(str(error))
                    except Exception:
                        st.error("Could not save settings. Check local file permissions; the active provider has not changed.")
        if st.session_state.get("saved_settings_notice"):st.info(st.session_state.saved_settings_notice)
        st.caption("Never paste API keys into a conversation.")
