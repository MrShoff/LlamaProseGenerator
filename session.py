from __future__ import annotations

import streamlit as st


def init_session() -> None:
    """Restore username from the URL query param (?u=) into session_state.

    Call at the very top of every page, before the username gate. If ?u= is
    present the gate is bypassed without user input.
    """
    if "username" not in st.session_state:
        u = st.query_params.get("u", "").strip()
        if u:
            st.session_state.username = u


def sync_session() -> None:
    """Keep the URL in sync with the confirmed username.

    Call once per page after the username gate passes. Sets ?u=<name> so that
    refreshing the current page restores the session without the login form.
    This is a no-op if the URL is already correct.
    """
    if "username" in st.session_state:
        u = st.session_state.username
        if st.query_params.get("u") != u:
            st.query_params["u"] = u
