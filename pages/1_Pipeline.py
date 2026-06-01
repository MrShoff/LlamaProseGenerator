from __future__ import annotations

import difflib
import html
import re
from pathlib import Path

import streamlit as st

from _sidebar import render as render_sidebar
from config import load_config, validate_config
from database import (
    get_all_scene_statuses,
    get_scene_status,
    init_db,
    set_scene_status,
)
from ollama_client import check_connectivity, generate
from scene_manager import (
    CRITIQUE_TEMPERATURE,
    REVISION_TEMPERATURE,
    VARIANT_TEMPERATURES,
    assemble_chapter,
    build_critique_user_prompt,
    build_revision_user_prompt,
    build_system_prompt,
    chapter_is_assembleable,
    critique_path,
    discover_scenes,
    read_output,
    read_prompt,
    revision_path,
    scenes_for_chapter,
    selected_path,
    split_paragraphs,
    variant_path,
    write_output,
)
from styles.components import (
    chapter_progress_bar,
    critique_card,
    diff_view,
    info_banner,
    ornament_divider,
    page_header,
    scene_nav_chapter,
    status_badge,
)
from styles.theme import inject_styles

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pipeline · The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
init_db()

if "username" not in st.session_state:
    st.switch_page("app.py")

cfg = load_config()
errors = validate_config(cfg)
configured = len(errors) == 0

# ── Cached scene discovery ───────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _discover(prompts_path: str):
    return discover_scenes(prompts_path)


# ── Status helpers ───────────────────────────────────────────────────────────

def _effective_status(chapter: int, scene: int, scene_key: str, db_statuses: dict, output_path: str) -> str:
    """DB is authoritative; fall back to file-based derivation for bootstrap."""
    from scene_manager import status_from_files
    row = db_statuses.get(scene_key)
    if row:
        return row["status"]
    return status_from_files(output_path, chapter, scene)


def _is_locked(idx: int, scenes: list, db_statuses: dict, output_path: str) -> bool:
    if idx == 0:
        return False
    prior = scenes[idx - 1]
    prior_status = _effective_status(prior.chapter, prior.scene, prior.scene_key, db_statuses, output_path)
    return prior_status not in ("selected", "assembled")


def _active_variant(scene_key: str, db_statuses: dict, output_path: str, chapter: int, scene: int) -> str | None:
    from scene_manager import active_variant_from_files
    row = db_statuses.get(scene_key)
    if row and row.get("active_variant"):
        return row["active_variant"]
    return active_variant_from_files(output_path, chapter, scene)


# ── Diff helper ──────────────────────────────────────────────────────────────

def _build_diff_html(original: str, revised: str) -> tuple[str, str]:
    """Sentence-level diff, returns (orig_html, revised_html)."""
    def split_sentences(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]

    orig_sents = split_sentences(original)
    rev_sents = split_sentences(revised)
    matcher = difflib.SequenceMatcher(None, orig_sents, rev_sents, autojunk=False)

    orig_parts: list[str] = []
    rev_parts: list[str] = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for s in orig_sents[i1:i2]:
                orig_parts.append(html.escape(s))
            for s in rev_sents[j1:j2]:
                rev_parts.append(html.escape(s))
        elif op == "replace":
            for s in orig_sents[i1:i2]:
                orig_parts.append(f'<span class="diff-removed">{html.escape(s)}</span>')
            for s in rev_sents[j1:j2]:
                rev_parts.append(f'<span class="diff-added">{html.escape(s)}</span>')
        elif op == "delete":
            for s in orig_sents[i1:i2]:
                orig_parts.append(f'<span class="diff-removed">{html.escape(s)}</span>')
        elif op == "insert":
            for s in rev_sents[j1:j2]:
                rev_parts.append(f'<span class="diff-added">{html.escape(s)}</span>')

    return " ".join(orig_parts), " ".join(rev_parts)


# ── Dialogs ──────────────────────────────────────────────────────────────────

@st.dialog("Confirm Selection")
def _confirm_select(info, output_path: str, source_path: Path, label: str) -> None:
    st.markdown(
        f"Mark **{label}** as the final version of **{info.scene_key}**?  \n"
        "This will write `scene_selected.md` and unlock the next scene.",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirm", type="primary", use_container_width=True):
            text = source_path.read_text(encoding="utf-8")
            dest = selected_path(output_path, info.chapter, info.scene)
            write_output(dest, text)
            set_scene_status(info.scene_key, "selected", st.session_state.username)
            st.cache_data.clear()
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Assemble Chapter")
def _confirm_assemble(chapter: int, scenes, output_path: str) -> None:
    ch_scenes = scenes_for_chapter(scenes, chapter)
    st.markdown(
        f"Concatenate all {len(ch_scenes)} selected scenes into "
        f"**chapter_{chapter:02d}.md**?"
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Assemble", type="primary", use_container_width=True):
            try:
                assemble_chapter(output_path, chapter, scenes)
                for s in ch_scenes:
                    set_scene_status(s.scene_key, "assembled", st.session_state.username)
                st.cache_data.clear()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ── Scene picker sidebar ─────────────────────────────────────────────────────

def _render_scene_picker(scenes, cfg, db_statuses: dict) -> None:
    selected_key = st.session_state.get("pipeline_scene", "")
    chapters = sorted({s.chapter for s in scenes})

    with st.sidebar:
        st.markdown('<hr style="margin:0.75rem 0;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="nav-section-label">Scenes</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="scene-nav-group">', unsafe_allow_html=True)

        for ch in chapters:
            ch_scenes = scenes_for_chapter(scenes, ch)
            completed = sum(
                1 for s in ch_scenes
                if _effective_status(s.chapter, s.scene, s.scene_key, db_statuses, cfg.output_path)
                in ("selected", "assembled")
            )

            st.markdown(
                scene_nav_chapter(ch, completed, len(ch_scenes)),
                unsafe_allow_html=True,
            )

            for idx, s in enumerate(sorted(scenes), start=0):
                if s.chapter != ch:
                    continue
                global_idx = scenes.index(s)
                locked = _is_locked(global_idx, scenes, db_statuses, cfg.output_path)
                status = _effective_status(s.chapter, s.scene, s.scene_key, db_statuses, cfg.output_path)
                is_active = s.scene_key == selected_key

                css_class = "scene-active" if is_active else ("scene-locked" if locked else "")
                label = f"Scene {s.scene:02d}"

                st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                if st.button(label, key=f"nav_{s.scene_key}", use_container_width=True):
                    st.session_state.pipeline_scene = s.scene_key
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # Assemble button when all chapter scenes are selected
            if chapter_is_assembleable(cfg.output_path, ch, scenes):
                if st.button(
                    f"Assemble Ch. {ch:02d}",
                    key=f"assemble_{ch}",
                    use_container_width=True,
                    type="primary",
                ):
                    _confirm_assemble(ch, scenes, cfg.output_path)

        st.markdown("</div>", unsafe_allow_html=True)


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _render_draft_tab(info, scenes, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    var_a = read_output(variant_path(output_path, info.chapter, info.scene, "a"))
    var_b = read_output(variant_path(output_path, info.chapter, info.scene, "b"))
    var_c = read_output(variant_path(output_path, info.chapter, info.scene, "c"))
    has_variants = var_a is not None

    if not has_variants:
        # ── Generate button ──
        connected, conn_err = check_connectivity(cfg.ollama_url)
        if not connected:
            st.markdown(
                info_banner(f"Ollama is offline: {conn_err}  Cannot generate.", kind="error"),
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            info_banner(
                "No drafts yet. Generate 3 variants (A, B, C) at stepped temperatures "
                "to give yourself creative range to choose from.",
                kind="info",
            ),
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Generate 3 Variants", type="primary"):
            try:
                system_prompt = build_system_prompt(info, output_path, scenes)
                user_prompt = read_prompt(info, "DRAFT_PROMPT")
            except FileNotFoundError as exc:
                st.markdown(info_banner(str(exc), kind="error"), unsafe_allow_html=True)
                return

            with st.status("Generating draft variants…", expanded=True) as status_box:
                for variant, temp in VARIANT_TEMPERATURES.items():
                    status_box.write(f"Variant {variant.upper()} · temperature {temp:.2f}…")
                    try:
                        text = generate(
                            cfg.ollama_url, cfg.model_name,
                            system_prompt, user_prompt,
                            temperature=temp, num_ctx=cfg.num_ctx,
                        )
                        write_output(variant_path(output_path, info.chapter, info.scene, variant), text)
                    except (ConnectionError, TimeoutError, RuntimeError) as exc:
                        st.markdown(info_banner(f"Generation failed: {exc}", kind="error"), unsafe_allow_html=True)
                        return
                status_box.update(label="All variants generated.", state="complete")

            set_scene_status(info.scene_key, "has_variants", username)
            st.cache_data.clear()
            st.rerun()
        return

    # ── Show variants ──
    vmap = {"a": var_a, "b": var_b, "c": var_c}
    tab_a, tab_b, tab_c = st.tabs(
        [f"Variant A · temp 0.70", f"Variant B · temp 0.85", f"Variant C · temp 1.00"]
    )
    for tab, (v, text) in zip([tab_a, tab_b, tab_c], vmap.items()):
        with tab:
            if text:
                wc = len(text.split())
                st.markdown(
                    f'<div class="prose-card">'
                    f'<div class="card-header"><span>Variant {v.upper()}</span>'
                    f'<span>{wc:,} words</span></div>'
                    f'<div class="card-body">{html.escape(text)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(info_banner("This variant file is missing.", kind="error"), unsafe_allow_html=True)

    if status not in ("has_critique", "has_revision", "selected", "assembled"):
        st.markdown(ornament_divider(), unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:var(--font-ui);font-size:0.875rem;'
            'color:var(--text-secondary);margin-bottom:0.75rem;">'
            'Choose a variant to take forward to critique:</p>',
            unsafe_allow_html=True,
        )
        choice = st.radio(
            "Proceed with",
            options=["a", "b", "c"],
            format_func=lambda v: f"Variant {v.upper()}",
            horizontal=True,
            label_visibility="collapsed",
        )
        if st.button("Proceed to Critique →", type="primary"):
            set_scene_status(info.scene_key, "has_variants", username, active_variant=choice)
            st.rerun()


def _render_critique_tab(info, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    if status == "needs_draft":
        st.markdown(
            '<div class="locked-state"><div class="lock-icon">◌</div>'
            '<div class="lock-title">Draft first</div>'
            '<div class="lock-subtitle">Generate at least one variant before critiquing.</div></div>',
            unsafe_allow_html=True,
        )
        return

    variant = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)
    if not variant:
        st.markdown(
            info_banner("Select a variant in the Draft tab to continue.", kind="info"),
            unsafe_allow_html=True,
        )
        return

    variant_text = read_output(variant_path(output_path, info.chapter, info.scene, variant))
    if not variant_text:
        st.markdown(info_banner(f"Variant {variant.upper()} file not found.", kind="error"), unsafe_allow_html=True)
        return

    critique_text = read_output(critique_path(output_path, info.chapter, info.scene, variant))

    # Show the chosen variant read-only
    wc = len(variant_text.split())
    st.markdown(
        f'<div class="prose-card">'
        f'<div class="card-header"><span>Variant {variant.upper()} — being critiqued</span>'
        f'<span>{wc:,} words</span></div>'
        f'<div class="card-body">{html.escape(variant_text)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if critique_text:
        st.markdown(critique_card(critique_text), unsafe_allow_html=True)
        if status not in ("has_revision", "selected", "assembled"):
            if st.button("Proceed to Revision →", type="primary"):
                set_scene_status(info.scene_key, "has_critique", username, active_variant=variant)
                st.rerun()
        return

    # Run critique
    connected, conn_err = check_connectivity(cfg.ollama_url)
    if not connected:
        st.markdown(info_banner(f"Ollama offline: {conn_err}", kind="error"), unsafe_allow_html=True)
        return

    if st.button(f"Run Critique on Variant {variant.upper()}", type="primary"):
        with st.status("Running critique…", expanded=True) as status_box:
            status_box.write(f"Evaluating Variant {variant.upper()} · temperature {CRITIQUE_TEMPERATURE:.2f}…")
            try:
                system_prompt = build_system_prompt(info, output_path, _get_all_scenes(cfg))
                user_prompt = build_critique_user_prompt(info, variant_text)
                crit = generate(
                    cfg.ollama_url, cfg.model_name,
                    system_prompt, user_prompt,
                    temperature=CRITIQUE_TEMPERATURE, num_ctx=cfg.num_ctx,
                )
                write_output(critique_path(output_path, info.chapter, info.scene, variant), crit)
                status_box.update(label="Critique complete.", state="complete")
            except (ConnectionError, TimeoutError, RuntimeError) as exc:
                st.markdown(info_banner(f"Generation failed: {exc}", kind="error"), unsafe_allow_html=True)
                return

        set_scene_status(info.scene_key, "has_critique", username, active_variant=variant)
        st.rerun()


def _render_revision_tab(info, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    if status in ("needs_draft", "has_variants"):
        st.markdown(
            '<div class="locked-state"><div class="lock-icon">◌</div>'
            '<div class="lock-title">Critique first</div>'
            '<div class="lock-subtitle">Complete the critique before generating a revision.</div></div>',
            unsafe_allow_html=True,
        )
        return

    variant = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)
    if not variant:
        st.markdown(info_banner("No active variant found — check the Critique tab.", kind="error"), unsafe_allow_html=True)
        return

    variant_text = read_output(variant_path(output_path, info.chapter, info.scene, variant))
    critique_text = read_output(critique_path(output_path, info.chapter, info.scene, variant))
    revised_text = read_output(revision_path(output_path, info.chapter, info.scene, variant))

    if not variant_text or not critique_text:
        st.markdown(info_banner("Missing variant or critique file.", kind="error"), unsafe_allow_html=True)
        return

    if revised_text:
        # Show diff
        orig_html, rev_html = _build_diff_html(variant_text, revised_text)
        st.markdown(diff_view(orig_html, rev_html), unsafe_allow_html=True)

        if status not in ("selected", "assembled"):
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Proceed to Select →", type="primary"):
                set_scene_status(info.scene_key, "has_revision", username, active_variant=variant)
                st.rerun()
        return

    # Split view: variant + critique
    col_v, col_c = st.columns([1, 1], gap="large")
    with col_v:
        wc = len(variant_text.split())
        st.markdown(
            f'<div class="prose-card" style="height:100%;">'
            f'<div class="card-header"><span>Variant {variant.upper()}</span>'
            f'<span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(variant_text)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(critique_card(critique_text), unsafe_allow_html=True)

    connected, conn_err = check_connectivity(cfg.ollama_url)
    if not connected:
        st.markdown(info_banner(f"Ollama offline: {conn_err}", kind="error"), unsafe_allow_html=True)
        return

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(f"Generate Revision of Variant {variant.upper()}", type="primary"):
        with st.status("Generating revision…", expanded=True) as status_box:
            status_box.write(f"Revising Variant {variant.upper()} · temperature {REVISION_TEMPERATURE:.2f}…")
            try:
                system_prompt = build_system_prompt(info, output_path, _get_all_scenes(cfg))
                user_prompt = build_revision_user_prompt(info, variant_text, critique_text)
                rev = generate(
                    cfg.ollama_url, cfg.model_name,
                    system_prompt, user_prompt,
                    temperature=REVISION_TEMPERATURE, num_ctx=cfg.num_ctx,
                )
                write_output(revision_path(output_path, info.chapter, info.scene, variant), rev)
                status_box.update(label="Revision complete.", state="complete")
            except (ConnectionError, TimeoutError, RuntimeError) as exc:
                st.markdown(info_banner(f"Generation failed: {exc}", kind="error"), unsafe_allow_html=True)
                return

        set_scene_status(info.scene_key, "has_revision", username, active_variant=variant)
        st.rerun()


def _render_select_tab(info, cfg, status: str, db_statuses: dict) -> None:
    output_path = cfg.output_path
    variant = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)

    if status in ("needs_draft", "has_variants", "has_critique"):
        st.markdown(
            '<div class="locked-state"><div class="lock-icon">◌</div>'
            '<div class="lock-title">Revision first</div>'
            '<div class="lock-subtitle">Generate a revision before selecting the final draft.</div></div>',
            unsafe_allow_html=True,
        )
        return

    if status in ("selected", "assembled"):
        sel_text = read_output(selected_path(output_path, info.chapter, info.scene))
        wc = len(sel_text.split()) if sel_text else 0
        st.markdown(
            f'<div class="prose-card" style="border-color:var(--gold-muted);">'
            f'<div class="card-header" style="color:var(--gold);">'
            f'<span>Selected Draft</span><span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(sel_text or "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            info_banner("This scene is complete. The next scene is now unlocked.", kind="success"),
            unsafe_allow_html=True,
        )
        return

    # Build candidate list: variants + revised
    candidates: list[tuple[str, Path, str]] = []
    for v in ("a", "b", "c"):
        p = variant_path(output_path, info.chapter, info.scene, v)
        if p.exists():
            candidates.append((f"Variant {v.upper()} (temp {VARIANT_TEMPERATURES[v]:.2f})", p, v))
    if variant:
        p = revision_path(output_path, info.chapter, info.scene, variant)
        if p.exists():
            candidates.append((f"Revision of Variant {variant.upper()}", p, f"{variant}_revised"))

    if not candidates:
        st.markdown(info_banner("No draft files found.", kind="error"), unsafe_allow_html=True)
        return

    for label, path, v_key in candidates:
        text = path.read_text(encoding="utf-8")
        wc = len(text.split())
        with st.container():
            st.markdown(
                f'<div class="prose-card">'
                f'<div class="card-header"><span>{label}</span><span>{wc:,} words</span></div>'
                f'<div class="card-body">{html.escape(text[:800])}{"…" if len(text) > 800 else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Select as Final — {label}", key=f"sel_{v_key}", type="primary"):
                _confirm_select(info, output_path, path, label)


# ── Utility ──────────────────────────────────────────────────────────────────

def _get_all_scenes(cfg):
    return _discover(cfg.prompts_path)


# ── Main layout ───────────────────────────────────────────────────────────────
render_sidebar("Pipeline")

if not configured:
    st.markdown(
        page_header("Pipeline", "Scene production workspace."),
        unsafe_allow_html=True,
    )
    st.markdown(
        info_banner("Configure project paths in Settings before using the pipeline.", kind="warning"),
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Settings.py", label="Open Settings →", icon=":material/settings:")
    st.stop()

scenes = _get_all_scenes(cfg)
db_statuses = get_all_scene_statuses()

# Sync any scenes not yet in DB from file system
for s in scenes:
    if s.scene_key not in db_statuses:
        from scene_manager import status_from_files, active_variant_from_files
        fs_status = status_from_files(cfg.output_path, s.chapter, s.scene)
        av = active_variant_from_files(cfg.output_path, s.chapter, s.scene)
        set_scene_status(s.scene_key, fs_status, "system", active_variant=av)
        db_statuses[s.scene_key] = {"status": fs_status, "active_variant": av}

_render_scene_picker(scenes, cfg, db_statuses)

# ── Pipeline content area ─────────────────────────────────────────────────────
selected_key = st.session_state.get("pipeline_scene", "")

if not selected_key:
    st.markdown(
        page_header("Pipeline", "Select a scene from the sidebar to begin."),
        unsafe_allow_html=True,
    )
    st.markdown(ornament_divider(), unsafe_allow_html=True)
    st.markdown(
        '<div class="prose-card" style="text-align:center;padding:3rem 2rem;">'
        '<div style="font-family:var(--font-display);font-size:1.75rem;font-weight:300;'
        'color:var(--text-secondary);margin-bottom:0.75rem;">The archive awaits.</div>'
        '<div style="font-family:var(--font-ui);font-size:0.875rem;color:var(--text-muted);">'
        'Choose a scene from the sidebar to open the draft · critique · revise · select pipeline.'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# Find the selected SceneInfo
info = next((s for s in scenes if s.scene_key == selected_key), None)
if not info:
    st.error(f"Scene {selected_key} not found.")
    st.stop()

# Derive current status
status = _effective_status(info.chapter, info.scene, info.scene_key, db_statuses, cfg.output_path)

# Check if locked
global_idx = scenes.index(info)
locked = _is_locked(global_idx, scenes, db_statuses, cfg.output_path)

st.markdown(
    page_header(
        f"Chapter {info.chapter:02d} · Scene {info.scene:02d}",
        f"{info.scene_key}  ·  {status.replace('_', ' ').title()}",
    ),
    unsafe_allow_html=True,
)

if locked:
    prior = scenes[global_idx - 1]
    st.markdown(
        f'<div class="locked-state">'
        f'<div class="lock-icon">🔒</div>'
        f'<div class="lock-title">{info.scene_key} is locked</div>'
        f'<div class="lock-subtitle">Complete and select a draft for '
        f'{prior.scene_key} before working on this scene.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Four-tab pipeline ─────────────────────────────────────────────────────────
tab_draft, tab_critique, tab_revision, tab_select = st.tabs(
    ["Draft", "Critique", "Revision", "Select"]
)

with tab_draft:
    _render_draft_tab(info, scenes, cfg, status, db_statuses)

with tab_critique:
    _render_critique_tab(info, cfg, status, db_statuses)

with tab_revision:
    _render_revision_tab(info, cfg, status, db_statuses)

with tab_select:
    _render_select_tab(info, cfg, status, db_statuses)
