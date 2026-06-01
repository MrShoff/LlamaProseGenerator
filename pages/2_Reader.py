from __future__ import annotations

import streamlit as st

from _sidebar import render as render_sidebar
from styles.components import ornament_divider, page_header
from styles.theme import inject_styles

st.set_page_config(
    page_title="Reader · The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()

if "username" not in st.session_state:
    st.switch_page("app.py")

render_sidebar("Reader")

st.markdown(
    page_header("Reader", "Read the manuscript in its current form."),
    unsafe_allow_html=True,
)

st.markdown(ornament_divider(), unsafe_allow_html=True)

st.markdown(
    '<div class="prose-card" style="text-align:center;padding:4rem 2rem;">'
    '<div style="font-family:var(--font-display);font-size:1.75rem;font-weight:300;'
    'color:var(--text-secondary);margin-bottom:1rem;">'
    'Coming in Phase 4'
    '</div>'
    '<div style="font-family:var(--font-ui);font-size:0.875rem;color:var(--text-muted);">'
    'The full manuscript reader — with annotations, inline editing, '
    'and paragraph-level AI revision — will be built here.'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
