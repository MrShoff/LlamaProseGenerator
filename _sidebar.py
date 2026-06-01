from __future__ import annotations

import streamlit as st

from config import load_config, validate_config
from ollama_client import check_connectivity
from styles.components import (
    nav_section_label,
    ollama_indicator,
    scriptorium_logo,
    user_badge,
)


@st.cache_data(ttl=15)
def _ollama_status(ollama_url: str) -> tuple[bool, str]:
    return check_connectivity(ollama_url)


def render(current_page: str = "Dashboard") -> None:
    """Render the shared sidebar. Call at the top of every page."""
    cfg = load_config()
    errors = validate_config(cfg)
    configured = len(errors) == 0

    with st.sidebar:
        st.markdown(scriptorium_logo(), unsafe_allow_html=True)

        # Ollama status indicator
        if configured:
            connected, err = _ollama_status(cfg.ollama_url)
        else:
            connected, err = False, "Not configured"
        st.markdown(ollama_indicator(connected, err), unsafe_allow_html=True)

        # Navigation
        st.markdown(nav_section_label("Navigate"), unsafe_allow_html=True)
        st.page_link("app.py",              label="Dashboard", icon=":material/grid_view:")
        st.page_link("pages/1_Pipeline.py", label="Pipeline",  icon=":material/edit_document:")
        st.page_link("pages/2_Reader.py",   label="Reader",    icon=":material/menu_book:")
        st.page_link("pages/3_Settings.py", label="Settings",  icon=":material/settings:")

        # Config warning
        if not configured:
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("Configure project paths in Settings before generating.", icon="⚠")

        # Push username badge to bottom
        st.markdown(
            "<div style='flex:1; min-height:2rem'></div>",
            unsafe_allow_html=True,
        )
        username = st.session_state.get("username", "")
        if username:
            st.markdown(user_badge(username), unsafe_allow_html=True)
