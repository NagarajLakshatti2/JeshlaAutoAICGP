"""Native chat popovers positioned beside Streamlit's retained options menu."""
import streamlit as st
from agent.interfaces.attachments import render_attachment_list
from agent.interfaces.chat_toolbar import render_provider_info


def render_header_actions(backend,session):
    # Streamlit has no public slot for custom toolbar controls. Scope this
    # positioning rule to our own keyed container; keep native popover behavior.
    st.html("""<style>
    .st-key-chat_header_actions {
        position: fixed;
        top: 0.375rem;
        right: 3.5rem;
        width: fit-content;
        max-width: calc(100vw - 7rem);
        z-index: 999990;
    }
    /* Reserve the native running/connection-status area only when present. */
    [data-testid="stApp"]:has([data-testid="stStatusWidgetRunningIcon"], [data-testid="stConnectionStatus"]) .st-key-chat_header_actions {
        right: 11rem;
        max-width: calc(100vw - 15rem);
    }
    /* File changes use the native Rerun/Auto rerun menu entries. Preserve Stop
       and connection errors; suppress only the standalone source-change prompt. */
    [data-testid="stStatusWidget"]:not(:has([data-testid="stStatusWidgetRunningIcon"], [data-testid="stConnectionStatus"])) {
        display: none;
    }
    [data-testid="stAppDeployButton"] {
        display: none;
    }
    </style>""")
    with st.container(key="chat_header_actions",horizontal=True,width="content",wrap=False,gap="small",vertical_alignment="center"):
        render_attachment_list(backend,session)
        render_provider_info(backend)
