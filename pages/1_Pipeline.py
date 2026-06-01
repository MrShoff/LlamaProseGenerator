from __future__ import annotations

import difflib
import html
import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from _sidebar import render as render_sidebar
from config import load_config, validate_config
from session import init_session, sync_session
from user_prefs import load_prefs, save_prefs
from database import (
    acquire_generation_lock,
    get_all_scene_statuses,
    get_generation_lock,
    init_db,
    release_generation_lock,
    set_scene_status,
)
from ollama_client import check_connectivity, generate
from scene_manager import (
    CRITIQUE_TEMPERATURE,
    REVISION_TEMPERATURE,
    VARIANT_TEMPERATURES,
    assemble_chapter,
    build_critique_user_prompt,
    build_judge_prompt,
    build_revision_user_prompt,
    build_system_prompt,
    chapter_is_assembleable,
    critique_path,
    discover_scenes,
    parse_critique_verdict,
    read_output,
    read_prompt,
    revision_path,
    scenes_for_chapter,
    selected_path,
    variant_path,
    write_output,
)
from styles.components import (
    critique_card,
    diff_view,
    info_banner,
    intervention_banner,
    ornament_divider,
    page_header,
    scene_nav_chapter,
    step_indicator,
)
from styles.theme import inject_styles

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pipeline · The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
init_db()
init_session()

if "username" not in st.session_state:
    st.switch_page("app.py")

sync_session()

cfg = load_config()
errors = validate_config(cfg)
configured = len(errors) == 0

# ── Pipeline steps ────────────────────────────────────────────────────────────

PIPELINE_STEPS = [("draft", "Draft"), ("critique", "Critique"), ("revision", "Revision"), ("select", "Select")]
_STEP_ORDER = ["draft", "critique", "revision", "select"]

_STATUS_TO_STEP: dict[str, str] = {
    "needs_draft":        "draft",
    "has_variants":       "draft",
    "has_critique":       "critique",
    "has_revision":       "revision",
    "selected":           "select",
    "assembled":          "select",
    "needs_intervention": "revision",
}


def _completed_steps(status: str, active_variant: str | None) -> set[str]:
    if status == "has_variants" and active_variant:
        return {"draft"}
    if status == "has_critique":
        return {"draft"}
    if status == "has_revision":
        return {"draft", "critique"}
    if status in ("selected", "assembled"):
        return {"draft", "critique", "revision"}
    if status == "needs_intervention":
        return {"draft"}
    return set()


def _step_accessible(step_id: str, status: str, active_variant: str | None) -> bool:
    if step_id == "draft":
        return True
    if step_id == "critique":
        return bool(active_variant) or status not in ("needs_draft", "has_variants")
    if step_id == "revision":
        return status in ("has_critique", "has_revision", "selected", "assembled", "needs_intervention")
    if step_id == "select":
        return status in ("has_revision", "selected", "assembled")
    return False


def _get_current_step(scene_key: str, status: str) -> str:
    step_key = f"step_{scene_key}"
    if step_key not in st.session_state:
        st.session_state[step_key] = _STATUS_TO_STEP.get(status, "draft")
    return st.session_state[step_key]


def _set_step(scene_key: str, step: str) -> None:
    st.session_state[f"step_{scene_key}"] = step


# ── Cached scene discovery ────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def _discover(prompts_path: str):
    return discover_scenes(prompts_path)


@st.cache_data(ttl=15, show_spinner=False)
def _check_ollama(url: str) -> bool:
    ok, _ = check_connectivity(url)
    return ok


# ── Status helpers ────────────────────────────────────────────────────────────

def _effective_status(chapter: int, scene: int, scene_key: str, db_statuses: dict, output_path: str) -> str:
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


def _get_all_scenes(cfg):
    return _discover(cfg.prompts_path)


# ── Diff helper ───────────────────────────────────────────────────────────────

def _build_diff_html(original: str, revised: str) -> tuple[str, str]:
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


# ── Dialogs ───────────────────────────────────────────────────────────────────

@st.dialog("Confirm Selection")
def _confirm_select(info, output_path: str, source_path: Path, label: str) -> None:
    st.markdown(
        f"Mark **{label}** as the final version of **{info.scene_key}**?  \n"
        "This writes `scene_selected.md` and unlocks the next scene.",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirm", type="primary", use_container_width=True):
            text = source_path.read_text(encoding="utf-8")
            dest = selected_path(output_path, info.chapter, info.scene)
            write_output(dest, text)
            set_scene_status(info.scene_key, "selected", st.session_state.username)
            _set_step(info.scene_key, "select")
            st.cache_data.clear()
            st.toast(f"{info.scene_key} selected — next scene unlocked.", icon="✅")
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
                st.toast(f"Chapter {chapter:02d} assembled.", icon="📖")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ── Judge helper ──────────────────────────────────────────────────────────────

def _judge_best_variant(var_texts: dict[str, str], cfg) -> str:
    """Ask Ollama to pick the best variant. Falls back to 'b' on any error."""
    try:
        result = generate(
            cfg.ollama_url, cfg.model_name,
            "You are a precise literary editor. Follow all instructions exactly.",
            build_judge_prompt(var_texts),
            temperature=0.1,
            num_ctx=cfg.num_ctx,
        )
        for char in result.strip().upper():
            if char in ("A", "B", "C"):
                return char.lower()
    except Exception:
        pass
    return "b"


# ── Variant edit widget ───────────────────────────────────────────────────────

def _variant_edit_ui(info, variant: str, file_path: Path, edit_key: str, username: str) -> None:
    current_text = read_output(file_path) or ""

    st.markdown(
        f'<div style="font-family:var(--font-ui);font-size:0.6875rem;font-weight:700;'
        f'letter-spacing:0.1em;text-transform:uppercase;color:var(--gold);'
        f'margin-bottom:0.5rem;">Editing — {edit_key.split("_", 3)[-1].replace("_", " ").title()}</div>',
        unsafe_allow_html=True,
    )
    c_save, c_cancel, _ = st.columns([1, 1, 5])
    with c_save:
        save_clicked = st.button("Save", type="primary", key=f"save__{edit_key}", use_container_width=True)
    with c_cancel:
        cancel_clicked = st.button("Discard", key=f"cancel__{edit_key}", use_container_width=True)

    edited = st.text_area(
        "Edit text",
        value=current_text,
        height=520,
        key=f"ta__{edit_key}",
        label_visibility="collapsed",
    )

    if save_clicked:
        lock = get_generation_lock(info.scene_key)
        if lock:
            st.warning(f"Cannot save — Ollama is generating for this scene ({lock['locked_by']}).")
            return
        write_output(file_path, edited)
        del st.session_state[edit_key]
        st.cache_data.clear()
        st.toast("Saved.", icon="✓")
        st.rerun()

    if cancel_clicked:
        del st.session_state[edit_key]
        st.rerun()


# ── Autopilot runner ──────────────────────────────────────────────────────────

def _process_one_scene(
    info, scene_idx: int, scenes: list, cfg, db_statuses: dict,
    username: str, loop_limit: int,
) -> tuple[list[str], bool, bool]:
    """Process one scene for auto-pilot.

    Returns (log_lines, should_stop, scene_selected).
    """
    log: list[str] = []

    def _log(msg: str) -> None:
        log.append(f"{datetime.now().strftime('%H:%M')}  {msg}")

    locked = _is_locked(scene_idx, scenes, db_statuses, cfg.output_path)
    if locked:
        _log(f"⏸ {info.scene_key}: prior scene incomplete — stopping.")
        return log, True, False

    row = db_statuses.get(info.scene_key, {})
    status = row.get("status", "needs_draft")

    if status in ("selected", "assembled"):
        _log(f"✓ {info.scene_key}: already complete.")
        return log, False, True

    if status == "needs_intervention":
        _log(f"⚠ {info.scene_key}: awaiting manual intervention — stopping.")
        return log, True, False

    _log(f"▸ {info.scene_key}")
    stopped = False

    # ── Generate variants ──
    var_texts: dict[str, str] = {}
    for v in ("a", "b", "c"):
        t = read_output(variant_path(cfg.output_path, info.chapter, info.scene, v))
        if t:
            var_texts[v] = t

    if len(var_texts) < 3:
        _log("  Generating 3 draft variants…")
        if not acquire_generation_lock(info.scene_key, username, "autopilot_draft"):
            _log("  ⚠ Scene locked by another user — stopping.")
            return log, True, False
        try:
            system_prompt = build_system_prompt(info, cfg.output_path, scenes)
            user_prompt = read_prompt(info, "DRAFT_PROMPT")
            for v, temp in VARIANT_TEMPERATURES.items():
                _log(f"    Variant {v.upper()} (temp {temp:.2f})…")
                text = generate(
                    cfg.ollama_url, cfg.model_name,
                    system_prompt, user_prompt,
                    temperature=temp, num_ctx=cfg.num_ctx,
                )
                write_output(variant_path(cfg.output_path, info.chapter, info.scene, v), text)
                var_texts[v] = text
        except Exception as exc:
            _log(f"  ✕ Generation failed: {exc}")
            stopped = True
        finally:
            release_generation_lock(info.scene_key)
        if stopped:
            return log, True, False
        set_scene_status(info.scene_key, "has_variants", username)
        _log("  3 variants generated.")

    # ── Judge variants ──
    variant = row.get("active_variant")
    if not variant:
        _log("  Judging variants…")
        variant = _judge_best_variant(var_texts, cfg)
        _log(f"  Variant {variant.upper()} selected as best.")
        set_scene_status(info.scene_key, "has_variants", username, active_variant=variant)

    # ── Critique / revision loop ──
    current_text = var_texts.get(variant) or ""
    if not current_text:
        vp = variant_path(cfg.output_path, info.chapter, info.scene, variant)
        if vp.exists():
            current_text = vp.read_text(encoding="utf-8")
    if not current_text:
        _log(f"  ✕ No text for Variant {variant.upper()} — skipping.")
        return log, False, False

    passed = False
    loop_count = row.get("loop_count") or 0

    while loop_count < loop_limit:
        _log(f"  Critique cycle {loop_count + 1}/{loop_limit}…")
        if not acquire_generation_lock(info.scene_key, username, f"autopilot_crit_{loop_count}"):
            _log("  ⚠ Scene locked — stopping.")
            return log, True, False
        try:
            sp = build_system_prompt(info, cfg.output_path, scenes)
            cu = build_critique_user_prompt(info, current_text)
            crit = generate(
                cfg.ollama_url, cfg.model_name, sp, cu,
                temperature=CRITIQUE_TEMPERATURE, num_ctx=cfg.num_ctx,
            )
            write_output(critique_path(cfg.output_path, info.chapter, info.scene, variant), crit)
        except Exception as exc:
            _log(f"  ✕ Critique failed: {exc}")
            stopped = True
        finally:
            release_generation_lock(info.scene_key)
        if stopped:
            return log, True, False

        set_scene_status(info.scene_key, "has_critique", username,
                         active_variant=variant, loop_count=loop_count)
        critique_passed, fixes = parse_critique_verdict(crit)

        if critique_passed:
            _log("  ✓ Critique passed — auto-selecting.")
            dest = selected_path(cfg.output_path, info.chapter, info.scene)
            write_output(dest, current_text)
            set_scene_status(info.scene_key, "selected", username,
                             active_variant=variant, loop_count=loop_count)
            st.toast(f"{info.scene_key} auto-selected.", icon="✅")
            passed = True
            break

        fixes_preview = "; ".join(fixes[:2]) if fixes else "see critique"
        _log(f"  Critique: {fixes_preview}")
        _log("  Generating revision…")

        if not acquire_generation_lock(info.scene_key, username, f"autopilot_rev_{loop_count}"):
            _log("  ⚠ Scene locked — stopping.")
            return log, True, False
        try:
            sp = build_system_prompt(info, cfg.output_path, scenes)
            ru = build_revision_user_prompt(info, current_text, crit)
            rev = generate(
                cfg.ollama_url, cfg.model_name, sp, ru,
                temperature=REVISION_TEMPERATURE, num_ctx=cfg.num_ctx,
            )
            write_output(revision_path(cfg.output_path, info.chapter, info.scene, variant), rev)
        except Exception as exc:
            _log(f"  ✕ Revision failed: {exc}")
            stopped = True
        finally:
            release_generation_lock(info.scene_key)
        if stopped:
            return log, True, False

        set_scene_status(info.scene_key, "has_revision", username,
                         active_variant=variant, loop_count=loop_count + 1)
        current_text = rev
        loop_count += 1

    if not passed:
        _log(f"  ⚠ Loop limit ({loop_limit}) reached — manual review required.")
        set_scene_status(info.scene_key, "needs_intervention", username,
                         active_variant=variant, loop_count=loop_count)
        st.toast(f"{info.scene_key} needs your attention.", icon="⚠️")
        return log, True, False

    return log, False, True


def _render_autopilot_log(log_lines: list[str]) -> None:
    """Render accumulated log in a fixed-height scrollable box."""
    def _line_html(line: str) -> str:
        # Lines have format "HH:MM  message"; split the timestamp for separate styling
        if len(line) >= 5 and line[2] == ":" and line[4:6] == "  ":
            ts = html.escape(line[:5])
            msg = html.escape(line[6:])
            return (
                f'<div class="autopilot-log-line">'
                f'<span class="log-ts">{ts}</span> {msg}'
                f'</div>'
            )
        return f'<div class="autopilot-log-line">{html.escape(line)}</div>'

    lines_html = "".join(_line_html(line) for line in log_lines)
    st.markdown(
        f'<div class="autopilot-log" id="autopilot-log">{lines_html}</div>'
        '<script>'
        'var el=document.getElementById("autopilot-log");'
        'if(el){el.scrollTop=el.scrollHeight;}'
        '</script>',
        unsafe_allow_html=True,
    )


def _save_autopilot_prefs() -> None:
    username = st.session_state.get("username")
    if not username:
        return
    prefs = load_prefs(username)
    prefs.autopilot_enabled = st.session_state.get("autopilot_enabled", True)
    prefs.autopilot_loop_limit = int(st.session_state.get("autopilot_loop_limit_val", 3))
    save_prefs(username, prefs)


def _render_autopilot_page(scenes: list, cfg, db_statuses: dict) -> None:
    """Scene-at-a-time autopilot runner with stop button and scrollable log."""
    username = st.session_state.username
    loop_limit = st.session_state.get("autopilot_loop_limit_val", cfg.autopilot_loop_limit)

    # Init per-run state
    if "autopilot_scene_idx" not in st.session_state:
        st.session_state.autopilot_scene_idx = 0
    if "autopilot_log" not in st.session_state:
        st.session_state.autopilot_log = []
    if "autopilot_selected_count" not in st.session_state:
        st.session_state.autopilot_selected_count = 0

    scene_idx: int = st.session_state.autopilot_scene_idx
    stop_requested: bool = st.session_state.get("autopilot_stop_requested", False)
    done = stop_requested or scene_idx >= len(scenes)

    # ── Header + stop button ──
    st.markdown(
        page_header("Auto-pilot", "Processing all unlocked scenes sequentially."),
        unsafe_allow_html=True,
    )
    col_stop, _ = st.columns([1, 6])
    with col_stop:
        if not done:
            if st.button("⬛ Stop", key="autopilot_stop_btn"):
                st.session_state.autopilot_stop_requested = True
                st.rerun()

    # ── Log ──
    _render_autopilot_log(st.session_state.autopilot_log)

    if done:
        # Finalise
        selected = st.session_state.autopilot_selected_count
        if stop_requested:
            st.markdown(info_banner("Auto-pilot stopped by user.", kind="warning"), unsafe_allow_html=True)
        else:
            st.markdown(
                info_banner(f"Auto-pilot complete — {selected} scene(s) selected.", kind="info"),
                unsafe_allow_html=True,
            )
            st.toast("Auto-pilot finished.", icon="✅")
        # Clean up state
        for k in ("autopilot_scene_idx", "autopilot_log", "autopilot_selected_count", "autopilot_stop_requested"):
            st.session_state.pop(k, None)
        st.session_state.autopilot_running = False
        st.cache_data.clear()
        st.rerun()
    else:
        # Process next scene
        info = scenes[scene_idx]
        with st.spinner(f"Processing {info.scene_key} ({scene_idx + 1}/{len(scenes)})…"):
            log_entries, should_stop, was_selected = _process_one_scene(
                info, scene_idx, scenes, cfg, db_statuses, username, loop_limit,
            )
        st.session_state.autopilot_log.extend(log_entries)
        st.session_state.autopilot_scene_idx = scene_idx + 1
        if was_selected:
            st.session_state.autopilot_selected_count += 1
        if should_stop:
            st.session_state.autopilot_stop_requested = True
        st.rerun()


# ── Scene picker (sidebar) ────────────────────────────────────────────────────

def _render_scene_picker(scenes, cfg, db_statuses: dict) -> None:
    selected_key = st.session_state.get("pipeline_scene", "")
    chapters = sorted({s.chapter for s in scenes})

    with st.sidebar:
        st.markdown('<hr style="margin:0.5rem 0;">', unsafe_allow_html=True)

        # ── Auto-pilot controls ──
        st.markdown('<div class="nav-section-label">Auto-pilot</div>', unsafe_allow_html=True)

        # Load prefs once per session (cleared on hard refresh — exactly when we want to restore)
        if "autopilot_enabled" not in st.session_state:
            _prefs = load_prefs(st.session_state.username)
            st.session_state.autopilot_enabled = _prefs.autopilot_enabled
            st.session_state.autopilot_loop_limit_val = _prefs.autopilot_loop_limit
            if "pipeline_scene" not in st.session_state and _prefs.last_pipeline_scene:
                st.session_state.pipeline_scene = _prefs.last_pipeline_scene

        st.checkbox("Enabled", key="autopilot_enabled", on_change=_save_autopilot_prefs)
        st.number_input(
            "Max revision cycles",
            min_value=1, max_value=10,
            value=cfg.autopilot_loop_limit,
            step=1,
            key="autopilot_loop_limit_val",
            on_change=_save_autopilot_prefs,
        )

        if st.session_state.get("autopilot_enabled"):
            if _check_ollama(cfg.ollama_url):
                if st.button("▶ Start Auto-pilot", type="primary", use_container_width=True):
                    st.session_state.autopilot_running = True
                    st.rerun()
            else:
                st.markdown(
                    info_banner("Ollama offline — cannot run.", kind="error"),
                    unsafe_allow_html=True,
                )

        st.markdown('<hr style="margin:0.5rem 0;">', unsafe_allow_html=True)

        # ── Scene list ──
        st.markdown('<div class="nav-section-label">Scenes</div>', unsafe_allow_html=True)
        st.markdown('<div class="scene-nav-group">', unsafe_allow_html=True)

        for ch in chapters:
            ch_scenes = scenes_for_chapter(scenes, ch)
            completed = sum(
                1 for s in ch_scenes
                if _effective_status(s.chapter, s.scene, s.scene_key, db_statuses, cfg.output_path)
                in ("selected", "assembled")
            )
            st.markdown(scene_nav_chapter(ch, completed, len(ch_scenes)), unsafe_allow_html=True)

            for s in sorted(ch_scenes):
                global_idx = scenes.index(s)
                locked = _is_locked(global_idx, scenes, db_statuses, cfg.output_path)
                status = _effective_status(s.chapter, s.scene, s.scene_key, db_statuses, cfg.output_path)
                is_active = s.scene_key == selected_key

                # CSS class for button styling
                if is_active:
                    css = "scene-active"
                elif locked:
                    css = "scene-locked"
                elif status == "needs_intervention":
                    css = "scene-intervention"
                elif status in ("selected", "assembled"):
                    css = "scene-complete"
                else:
                    css = ""

                # Label with status indicator
                if status in ("selected", "assembled"):
                    label = f"✓  Scene {s.scene:02d}"
                elif status == "needs_intervention":
                    label = f"⚠  Scene {s.scene:02d}"
                elif status not in ("needs_draft",) and not locked:
                    label = f"●  Scene {s.scene:02d}"
                else:
                    label = f"    Scene {s.scene:02d}"

                st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                if st.button(label, key=f"nav_{s.scene_key}", use_container_width=True):
                    if not locked:
                        # Reset step to status-default when navigating
                        step_key = f"step_{s.scene_key}"
                        if step_key in st.session_state:
                            del st.session_state[step_key]
                        st.session_state.pipeline_scene = s.scene_key
                        _uname = st.session_state.username
                        _p = load_prefs(_uname)
                        _p.last_pipeline_scene = s.scene_key
                        save_prefs(_uname, _p)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if chapter_is_assembleable(cfg.output_path, ch, scenes):
                if st.button(
                    f"Assemble Ch. {ch:02d}",
                    key=f"assemble_{ch}",
                    use_container_width=True,
                    type="primary",
                ):
                    _confirm_assemble(ch, scenes, cfg.output_path)

        st.markdown("</div>", unsafe_allow_html=True)


# ── Draft step ────────────────────────────────────────────────────────────────

def _render_draft_step(info, scenes, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    var_a = read_output(variant_path(output_path, info.chapter, info.scene, "a"))
    var_b = read_output(variant_path(output_path, info.chapter, info.scene, "b"))
    var_c = read_output(variant_path(output_path, info.chapter, info.scene, "c"))
    has_variants = var_a is not None

    if not has_variants:
        connected, conn_err = check_connectivity(cfg.ollama_url)
        if not connected:
            st.markdown(
                info_banner(f"Ollama offline: {conn_err} — cannot generate.", kind="error"),
                unsafe_allow_html=True,
            )
            return

        existing_lock = get_generation_lock(info.scene_key)
        if existing_lock:
            st.markdown(
                info_banner(
                    f"Generation in progress by **{existing_lock['locked_by']}** "
                    f"({existing_lock['pass_name']}) — please wait.",
                    kind="warning",
                ),
                unsafe_allow_html=True,
            )
            if st.button("Refresh"):
                st.rerun()
            return

        # Action button first, context below
        if st.button("Generate 3 Variants", type="primary", key=f"gen3_{info.scene_key}"):
            if not acquire_generation_lock(info.scene_key, username, "draft"):
                st.markdown(
                    info_banner("Another user just started generating. Refresh to see their progress.", kind="warning"),
                    unsafe_allow_html=True,
                )
                return
            try:
                system_prompt = build_system_prompt(info, output_path, scenes)
                user_prompt = read_prompt(info, "DRAFT_PROMPT")
            except FileNotFoundError as exc:
                release_generation_lock(info.scene_key)
                st.markdown(info_banner(f"Prompt file missing: {exc}", kind="error"), unsafe_allow_html=True)
                return
            try:
                with st.status("Generating draft variants…", expanded=True) as sb:
                    for variant, temp in VARIANT_TEMPERATURES.items():
                        sb.write(f"Variant {variant.upper()} · temp {temp:.2f}…")
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
                    sb.update(label="All variants generated.", state="complete")
            finally:
                release_generation_lock(info.scene_key)

            set_scene_status(info.scene_key, "has_variants", username)
            st.cache_data.clear()
            st.toast(f"3 variants generated for {info.scene_key}", icon="✅")
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            info_banner(
                "No drafts yet. Generate 3 variants at stepped temperatures to give yourself creative range.",
                kind="info",
            ),
            unsafe_allow_html=True,
        )
        return

    # ── Variants exist — proceed controls ABOVE text ──
    active_v = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)
    show_proceed = status not in ("has_critique", "has_revision", "selected", "assembled")

    if show_proceed:
        options = ["a", "b", "c"]
        default_idx = options.index(active_v) if active_v in options else 0
        c_radio, c_btn = st.columns([3, 1])
        with c_radio:
            choice = st.radio(
                "Proceed with variant",
                options=options,
                format_func=lambda v: f"Variant {v.upper()}",
                horizontal=True,
                index=default_idx,
                key=f"variant_choice_{info.scene_key}",
            )
        with c_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Proceed to Critique →", type="primary",
                         key=f"to_crit_{info.scene_key}", use_container_width=True):
                set_scene_status(info.scene_key, "has_variants", username, active_variant=choice)
                _set_step(info.scene_key, "critique")
                st.cache_data.clear()
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Variant sub-tabs ──
    vmap = {"a": var_a, "b": var_b, "c": var_c}
    tab_a, tab_b, tab_c = st.tabs([
        f"Variant A · {VARIANT_TEMPERATURES['a']:.2f}",
        f"Variant B · {VARIANT_TEMPERATURES['b']:.2f}",
        f"Variant C · {VARIANT_TEMPERATURES['c']:.2f}",
    ])

    for tab, (v, text) in zip([tab_a, tab_b, tab_c], vmap.items()):
        with tab:
            edit_key = f"edit_{info.scene_key}_{v}"
            vpath = variant_path(output_path, info.chapter, info.scene, v)
            if st.session_state.get(edit_key):
                _variant_edit_ui(info, v, vpath, edit_key, username)
            else:
                if text:
                    wc = len(text.split())
                    lock = get_generation_lock(info.scene_key)
                    if not lock:
                        if st.button(f"Edit Variant {v.upper()}", key=f"edit_btn_{info.scene_key}_{v}"):
                            st.session_state[edit_key] = True
                            st.rerun()
                    st.markdown(
                        f'<div class="prose-card">'
                        f'<div class="card-header"><span>Variant {v.upper()}</span>'
                        f'<span>{wc:,} words</span></div>'
                        f'<div class="card-body">{html.escape(text)}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(info_banner("Variant file missing.", kind="error"), unsafe_allow_html=True)


# ── Critique step ─────────────────────────────────────────────────────────────

def _render_critique_step(info, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    if status == "needs_draft":
        st.markdown(
            '<div class="locked-state"><div class="lock-icon">◌</div>'
            '<div class="lock-title">Draft first</div>'
            '<div class="lock-subtitle">Generate variants before critiquing.</div></div>',
            unsafe_allow_html=True,
        )
        return

    variant = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)
    if not variant:
        st.markdown(
            info_banner("Select a variant in the Draft step first.", kind="info"),
            unsafe_allow_html=True,
        )
        return

    variant_text = read_output(variant_path(output_path, info.chapter, info.scene, variant))
    if not variant_text:
        st.markdown(info_banner(f"Variant {variant.upper()} file not found.", kind="error"), unsafe_allow_html=True)
        return

    critique_text = read_output(critique_path(output_path, info.chapter, info.scene, variant))

    if critique_text:
        passed, fixes = parse_critique_verdict(critique_text)

        # Proceed button + verdict ABOVE text
        if status not in ("has_revision", "selected", "assembled"):
            c_verdict, c_btn = st.columns([3, 1])
            with c_btn:
                if st.button("Proceed to Revision →", type="primary",
                             key=f"to_rev_{info.scene_key}", use_container_width=True):
                    set_scene_status(info.scene_key, "has_critique", username, active_variant=variant)
                    _set_step(info.scene_key, "revision")
                    st.rerun()
            with c_verdict:
                if passed:
                    st.markdown(
                        info_banner("Critique verdict: PASS — no critical issues found.", kind="success"),
                        unsafe_allow_html=True,
                    )
                else:
                    preview = " · ".join(fixes[:2]) if fixes else "see critique"
                    st.markdown(
                        info_banner(f"Critique verdict: FAIL — {preview}", kind="warning"),
                        unsafe_allow_html=True,
                    )
            st.markdown("<br>", unsafe_allow_html=True)

        wc = len(variant_text.split())
        st.markdown(
            f'<div class="prose-card">'
            f'<div class="card-header"><span>Variant {variant.upper()}</span>'
            f'<span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(variant_text)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(critique_card(critique_text), unsafe_allow_html=True)
        return

    # ── Run critique ──
    connected, conn_err = check_connectivity(cfg.ollama_url)
    if not connected:
        st.markdown(info_banner(f"Ollama offline: {conn_err}", kind="error"), unsafe_allow_html=True)
        return

    lock = get_generation_lock(info.scene_key)
    if lock:
        st.markdown(
            info_banner(f"Generation in progress by **{lock['locked_by']}** — please wait.", kind="warning"),
            unsafe_allow_html=True,
        )
        return

    # Action button ABOVE text
    if st.button(f"Run Critique on Variant {variant.upper()}", type="primary",
                 key=f"run_crit_{info.scene_key}"):
        if not acquire_generation_lock(info.scene_key, username, f"critique_{variant}"):
            st.markdown(info_banner("Another user just started. Please refresh.", kind="warning"), unsafe_allow_html=True)
            return
        try:
            with st.status("Running critique…", expanded=True) as sb:
                sb.write(f"Evaluating Variant {variant.upper()} · temp {CRITIQUE_TEMPERATURE:.2f}…")
                try:
                    sp = build_system_prompt(info, output_path, _get_all_scenes(cfg))
                    up = build_critique_user_prompt(info, variant_text)
                    crit = generate(
                        cfg.ollama_url, cfg.model_name, sp, up,
                        temperature=CRITIQUE_TEMPERATURE, num_ctx=cfg.num_ctx,
                    )
                    write_output(critique_path(output_path, info.chapter, info.scene, variant), crit)
                    sb.update(label="Critique complete.", state="complete")
                except (ConnectionError, TimeoutError, RuntimeError) as exc:
                    st.markdown(info_banner(f"Generation failed: {exc}", kind="error"), unsafe_allow_html=True)
                    return
        finally:
            release_generation_lock(info.scene_key)

        set_scene_status(info.scene_key, "has_critique", username, active_variant=variant)
        st.toast(f"Critique complete for {info.scene_key} Variant {variant.upper()}", icon="✅")
        _set_step(info.scene_key, "critique")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    wc = len(variant_text.split())
    st.markdown(
        f'<div class="prose-card">'
        f'<div class="card-header"><span>Variant {variant.upper()} — will be critiqued</span>'
        f'<span>{wc:,} words</span></div>'
        f'<div class="card-body">{html.escape(variant_text)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Revision step ─────────────────────────────────────────────────────────────

def _render_revision_step(info, cfg, status: str, db_statuses: dict) -> None:
    username = st.session_state.username
    output_path = cfg.output_path

    if status in ("needs_draft", "has_variants"):
        st.markdown(
            '<div class="locked-state"><div class="lock-icon">◌</div>'
            '<div class="lock-title">Critique first</div>'
            '<div class="lock-subtitle">Run a critique before generating a revision.</div></div>',
            unsafe_allow_html=True,
        )
        return

    variant = _active_variant(info.scene_key, db_statuses, output_path, info.chapter, info.scene)
    if not variant:
        st.markdown(info_banner("No active variant — check the Critique step.", kind="error"), unsafe_allow_html=True)
        return

    variant_text = read_output(variant_path(output_path, info.chapter, info.scene, variant))
    critique_text = read_output(critique_path(output_path, info.chapter, info.scene, variant))
    revised_text = read_output(revision_path(output_path, info.chapter, info.scene, variant))

    if not variant_text or not critique_text:
        st.markdown(info_banner("Missing variant or critique file.", kind="error"), unsafe_allow_html=True)
        return

    if revised_text:
        # Controls ABOVE diff
        if status not in ("selected", "assembled"):
            c_meta, c_btn = st.columns([3, 1])
            with c_btn:
                if st.button("Proceed to Select →", type="primary",
                             key=f"to_sel_{info.scene_key}", use_container_width=True):
                    set_scene_status(info.scene_key, "has_revision", username, active_variant=variant)
                    _set_step(info.scene_key, "select")
                    st.rerun()
            with c_meta:
                wc = len(revised_text.split())
                st.markdown(
                    f'<div style="font-family:var(--font-ui);font-size:0.875rem;'
                    f'color:var(--text-secondary);padding:0.6rem 0;">Revision ready — {wc:,} words</div>',
                    unsafe_allow_html=True,
                )

            # Edit revision button
            rev_path_obj = revision_path(output_path, info.chapter, info.scene, variant)
            edit_key = f"edit_{info.scene_key}_{variant}_rev"
            lock = get_generation_lock(info.scene_key)
            if not lock:
                if st.session_state.get(edit_key):
                    _variant_edit_ui(info, variant, rev_path_obj, edit_key, username)
                    return
                if st.button("Edit Revision", key=f"editbtn_{edit_key}"):
                    st.session_state[edit_key] = True
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        orig_html, rev_html = _build_diff_html(variant_text, revised_text)
        st.markdown(diff_view(orig_html, rev_html), unsafe_allow_html=True)
        return

    # ── Generate revision ──
    connected, conn_err = check_connectivity(cfg.ollama_url)
    if not connected:
        st.markdown(info_banner(f"Ollama offline: {conn_err}", kind="error"), unsafe_allow_html=True)
        return

    lock = get_generation_lock(info.scene_key)
    if lock:
        st.markdown(
            info_banner(f"Generation in progress by **{lock['locked_by']}** — please wait.", kind="warning"),
            unsafe_allow_html=True,
        )
        return

    # Action button ABOVE split view
    if st.button(f"Generate Revision of Variant {variant.upper()}", type="primary",
                 key=f"gen_rev_{info.scene_key}"):
        if not acquire_generation_lock(info.scene_key, username, f"revision_{variant}"):
            st.markdown(info_banner("Another user just started. Please refresh.", kind="warning"), unsafe_allow_html=True)
            return
        try:
            with st.status("Generating revision…", expanded=True) as sb:
                sb.write(f"Revising Variant {variant.upper()} · temp {REVISION_TEMPERATURE:.2f}…")
                try:
                    sp = build_system_prompt(info, output_path, _get_all_scenes(cfg))
                    up = build_revision_user_prompt(info, variant_text, critique_text)
                    rev = generate(
                        cfg.ollama_url, cfg.model_name, sp, up,
                        temperature=REVISION_TEMPERATURE, num_ctx=cfg.num_ctx,
                    )
                    write_output(revision_path(output_path, info.chapter, info.scene, variant), rev)
                    sb.update(label="Revision complete.", state="complete")
                except (ConnectionError, TimeoutError, RuntimeError) as exc:
                    st.markdown(info_banner(f"Generation failed: {exc}", kind="error"), unsafe_allow_html=True)
                    return
        finally:
            release_generation_lock(info.scene_key)

        set_scene_status(info.scene_key, "has_revision", username, active_variant=variant)
        _set_step(info.scene_key, "revision")
        st.toast(f"Revision complete for {info.scene_key} Variant {variant.upper()}", icon="✅")
        st.rerun()

    # Split view BELOW button
    st.markdown("<br>", unsafe_allow_html=True)
    col_v, col_c = st.columns([1, 1], gap="large")
    with col_v:
        wc = len(variant_text.split())
        st.markdown(
            f'<div class="prose-card">'
            f'<div class="card-header"><span>Variant {variant.upper()}</span>'
            f'<span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(variant_text)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(critique_card(critique_text), unsafe_allow_html=True)


# ── Select step ───────────────────────────────────────────────────────────────

def _render_select_step(info, cfg, status: str, db_statuses: dict) -> None:
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
            info_banner("This scene is complete. The next scene is now unlocked.", kind="success"),
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="prose-card" style="border-color:var(--gold-muted);">'
            f'<div class="card-header" style="color:var(--gold);">'
            f'<span>Selected Draft</span><span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(sel_text or "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # Build candidates
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
        # Select button ABOVE card
        if st.button(f"Select as Final — {label}", key=f"sel_{v_key}_{info.scene_key}", type="primary"):
            _confirm_select(info, output_path, path, label)
        st.markdown(
            f'<div class="prose-card">'
            f'<div class="card-header"><span>{label}</span><span>{wc:,} words</span></div>'
            f'<div class="card-body">{html.escape(text[:1200])}{"…" if len(text) > 1200 else ""}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)


# ── Main layout ───────────────────────────────────────────────────────────────

render_sidebar("Pipeline")

if not configured:
    st.markdown(page_header("Pipeline", "Scene production workspace."), unsafe_allow_html=True)
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

# ── Auto-pilot mode ───────────────────────────────────────────────────────────

if st.session_state.get("autopilot_running"):
    _render_autopilot_page(scenes, cfg, db_statuses)
    st.stop()

# ── Normal pipeline view ──────────────────────────────────────────────────────

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

info = next((s for s in scenes if s.scene_key == selected_key), None)
if not info:
    st.error(f"Scene {selected_key} not found.")
    st.stop()

status = _effective_status(info.chapter, info.scene, info.scene_key, db_statuses, cfg.output_path)
active_v = _active_variant(info.scene_key, db_statuses, cfg.output_path, info.chapter, info.scene)
global_idx = scenes.index(info)
locked = _is_locked(global_idx, scenes, db_statuses, cfg.output_path)

# ── Page header ──
if status in ("selected", "assembled"):
    status_label = f"✓ {status.title()}"
elif status == "needs_intervention":
    status_label = "⚠ Needs Review"
else:
    status_label = status.replace("_", " ").title()

st.markdown(
    page_header(
        f"Chapter {info.chapter:02d} · Scene {info.scene:02d}",
        f"{info.scene_key}  ·  {status_label}",
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

# ── Intervention banner + recovery actions ──
if status == "needs_intervention":
    last_crit = read_output(critique_path(cfg.output_path, info.chapter, info.scene, active_v or "a"))
    _, fixes = parse_critique_verdict(last_crit) if last_crit else (False, [])
    st.markdown(intervention_banner(fixes), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Reset — Resume Manual Review", type="secondary",
                     key=f"reset_intervention_{info.scene_key}"):
            set_scene_status(info.scene_key, "has_revision", st.session_state.username, active_variant=active_v)
            _set_step(info.scene_key, "revision")
            st.cache_data.clear()
            st.rerun()
    with c2:
        rev_p = revision_path(cfg.output_path, info.chapter, info.scene, active_v or "a")
        if rev_p.exists():
            if st.button("Select Current Revision as Final", type="primary",
                         key=f"force_sel_{info.scene_key}"):
                _confirm_select(
                    info, cfg.output_path, rev_p,
                    f"Revision of Variant {(active_v or 'a').upper()}"
                )
    st.markdown("<br>", unsafe_allow_html=True)

# ── Step indicator (visual) ──
current_step = _get_current_step(selected_key, status)
completed = _completed_steps(status, active_v)

st.markdown(step_indicator(PIPELINE_STEPS, current_step, completed), unsafe_allow_html=True)

# ── Step navigation buttons ──
step_cols = st.columns(len(PIPELINE_STEPS))
for col, (step_id, step_label) in zip(step_cols, PIPELINE_STEPS):
    with col:
        is_current = current_step == step_id
        is_done = step_id in completed
        accessible = _step_accessible(step_id, status, active_v)
        label = f"✓ {step_label}" if is_done and not is_current else step_label
        if st.button(
            label,
            key=f"stepnav_{selected_key}_{step_id}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
            disabled=not accessible and not is_current,
        ):
            _set_step(selected_key, step_id)
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Render current step ──
if current_step == "draft":
    _render_draft_step(info, scenes, cfg, status, db_statuses)
elif current_step == "critique":
    _render_critique_step(info, cfg, status, db_statuses)
elif current_step == "revision":
    _render_revision_step(info, cfg, status, db_statuses)
elif current_step == "select":
    _render_select_step(info, cfg, status, db_statuses)
