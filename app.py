from __future__ import annotations

import streamlit as st

from _sidebar import render as render_sidebar
from config import load_config, validate_config
from database import init_db
from session import init_session, sync_session
from scene_manager import (
    chapter_is_assembleable,
    discover_scenes,
    scenes_for_chapter,
    selected_path,
    split_paragraphs,
    status_from_files,
)
from styles.components import (
    chapter_progress_bar,
    info_banner,
    ornament_divider,
    page_header,
    stat_card,
    status_badge,
    username_screen,
)
from styles.theme import inject_styles

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
init_db()
init_session()

# ── Username gate ────────────────────────────────────────────────────────────
if "username" not in st.session_state:
    st.markdown(username_screen(), unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.form("username_form", clear_on_submit=False):
            name = st.text_input(
                "Your name",
                placeholder="How shall we call you?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Enter The Scriptorium",
                type="primary",
                use_container_width=True,
            )
            if submitted:
                cleaned = name.strip()
                if cleaned:
                    st.session_state.username = cleaned
                    st.query_params["u"] = cleaned
                    st.rerun()
                else:
                    st.error("A name is required to enter.")
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────────────
sync_session()
render_sidebar("Dashboard")

# ── Main content ─────────────────────────────────────────────────────────────
cfg = load_config()
errors = validate_config(cfg)
configured = len(errors) == 0

st.markdown(
    page_header(
        "Dashboard",
        f"Welcome back, {st.session_state.username}.",
    ),
    unsafe_allow_html=True,
)

if not configured:
    st.markdown(
        info_banner(
            "Project paths are not configured. "
            "Visit Settings to set your prompts directory and output directory.",
            kind="warning",
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Settings.py", label="Open Settings →", icon=":material/settings:")
    st.stop()

# ── Load project data ─────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _load_project(prompts_path: str, output_path: str) -> dict:
    scenes = discover_scenes(prompts_path)
    chapters = sorted({s.chapter for s in scenes})

    selected_count = 0
    total_words = 0
    chapter_summaries: list[dict] = []

    for ch in chapters:
        ch_scenes = scenes_for_chapter(scenes, ch)
        ch_selected = 0
        for s in ch_scenes:
            sp = selected_path(output_path, ch, s.scene)
            if sp.exists():
                selected_count += 1
                ch_selected += 1
                text = sp.read_text(encoding="utf-8")
                total_words += len(text.split())
        chapter_summaries.append(
            {
                "chapter": ch,
                "total": len(ch_scenes),
                "completed": ch_selected,
                "assembleable": chapter_is_assembleable(output_path, ch, scenes),
            }
        )

    return {
        "scenes": scenes,
        "total_scenes": len(scenes),
        "selected_scenes": selected_count,
        "total_words": total_words,
        "chapters": chapters,
        "chapter_summaries": chapter_summaries,
    }


with st.spinner(""):
    data = _load_project(cfg.prompts_path, cfg.output_path)

scenes = data["scenes"]

# ── Stats row ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_card(data["total_scenes"], "Scenes Planned"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card(data["selected_scenes"], "Scenes Complete"), unsafe_allow_html=True)
with c3:
    st.markdown(
        stat_card(f"{data['total_words']:,}", "Words Written"),
        unsafe_allow_html=True,
    )
with c4:
    pct = (
        round(data["selected_scenes"] / data["total_scenes"] * 100)
        if data["total_scenes"] > 0
        else 0
    )
    st.markdown(stat_card(f"{pct}%", "Manuscript Progress"), unsafe_allow_html=True)

st.markdown(ornament_divider(), unsafe_allow_html=True)

# ── Chapter overview grid ─────────────────────────────────────────────────────
st.markdown(
    '<p style="font-family:var(--font-ui);font-size:0.6875rem;font-weight:700;'
    'letter-spacing:0.12em;text-transform:uppercase;color:var(--text-muted);">'
    'Chapter Progress</p>',
    unsafe_allow_html=True,
)

cols = st.columns(min(len(data["chapter_summaries"]), 6))
for i, ch_data in enumerate(data["chapter_summaries"]):
    col = cols[i % len(cols)]
    with col:
        status = "assembled" if ch_data["assembleable"] else (
            "selected" if ch_data["completed"] == ch_data["total"] else
            "has_variants" if ch_data["completed"] > 0 else
            "needs_draft"
        )
        st.markdown(
            f'<div class="stat-card" style="padding:1rem;">'
            f'<div style="font-family:var(--font-ui);font-size:0.6875rem;'
            f'color:var(--text-muted);letter-spacing:0.08em;text-transform:uppercase;">'
            f'Chapter {ch_data["chapter"]:02d}</div>'
            f'<div style="margin:0.5rem 0 0.375rem;">{status_badge(status)}</div>'
            f'<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.5rem;">'
            f'{ch_data["completed"]}/{ch_data["total"]} scenes</div>'
            + chapter_progress_bar(ch_data["completed"], ch_data["total"])
            + '</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Next action ───────────────────────────────────────────────────────────────
next_scene = None
for s in scenes:
    status = status_from_files(cfg.output_path, s.chapter, s.scene)
    if status != "selected":
        next_scene = (s, status)
        break

if next_scene:
    s, status = next_scene
    st.markdown(
        f'<div class="prose-card" style="border-color:var(--border-strong);">'
        f'<div class="card-header">'
        f'<span>Continue Writing</span>'
        f'{status_badge(status)}'
        f'</div>'
        f'<div style="font-family:var(--font-display);font-size:1.25rem;'
        f'color:var(--text-primary);margin-bottom:0.5rem;">'
        f'Chapter {s.chapter:02d} · Scene {s.scene:02d}</div>'
        f'<div style="font-family:var(--font-ui);font-size:0.875rem;'
        f'color:var(--text-secondary);">'
        f'{s.scene_key} is ready for its next stage.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Pipeline.py", label="Open Pipeline →", icon=":material/edit_document:")
else:
    st.markdown(
        info_banner("All planned scenes are complete.", kind="success"),
        unsafe_allow_html=True,
    )
