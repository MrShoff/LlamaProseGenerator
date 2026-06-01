from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from _sidebar import render as render_sidebar
from config import load_config, validate_config
from database import (
    add_comment,
    add_edit,
    get_comments,
    init_db,
)
from ollama_client import check_connectivity, generate
from scene_manager import (
    PARAGRAPH_REGEN_TEMPERATURE,
    build_paragraph_regen_user_prompt,
    chapter_path,
    discover_scenes,
    get_paragraph_context,
    join_paragraphs,
    scenes_for_chapter,
    selected_path,
    split_paragraphs,
    write_output,
)
from styles.components import comment_annotation, diff_view, info_banner, ornament_divider
from styles.theme import inject_styles

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Reader · The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()

# Narrow the content column to a comfortable reading measure
st.markdown(
    "<style>.main .block-container { max-width: 74ch; padding-left: 3rem; padding-right: 3rem; }</style>",
    unsafe_allow_html=True,
)

# Paragraph interaction: show action bar on click or text selection
st.markdown(
    """<script>
(function () {
  'use strict';
  if (window.__readerSetup) return;
  window.__readerSetup = true;

  function showBar(pid) {
    document.querySelectorAll('.reader-action-bar:not(.para-open)').forEach(function (b) {
      b.style.display = 'none';
    });
    var bar = document.querySelector('.reader-action-bar[data-para-id="' + pid + '"]');
    if (bar) bar.style.display = 'flex';
  }

  function hideAll() {
    document.querySelectorAll('.reader-action-bar:not(.para-open)').forEach(function (b) {
      b.style.display = 'none';
    });
  }

  function setupParas() {
    document.querySelectorAll('.reader-paragraph:not([data-rl])').forEach(function (para) {
      para.setAttribute('data-rl', '1');
      para.style.cursor = 'text';
      para.addEventListener('click', function (e) {
        e.stopPropagation();
        var pid = this.getAttribute('data-para-id');
        if (!pid) return;
        var bar = document.querySelector('.reader-action-bar[data-para-id="' + pid + '"]');
        if (!bar) return;
        if (bar.classList.contains('para-open')) return;
        if (bar.style.display === 'flex') { hideAll(); } else { showBar(pid); }
      });
    });
  }

  document.addEventListener('mouseup', function () {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) return;
    try {
      var range = sel.getRangeAt(0);
      var node = range.commonAncestorContainer;
      var el = node.nodeType === 3 ? node.parentElement : node;
      var para = el.closest('.reader-paragraph');
      if (!para) return;
      var pid = para.getAttribute('data-para-id');
      if (pid) showBar(pid);
    } catch (_) {}
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.reader-paragraph') &&
        !e.target.closest('.reader-action-bar') &&
        !e.target.closest('.reader-action-open')) {
      hideAll();
    }
  });

  var obs = new MutationObserver(function () {
    clearTimeout(window.__readerSetupT);
    window.__readerSetupT = setTimeout(setupParas, 80);
  });
  obs.observe(document.body, { childList: true, subtree: true });
  setupParas();
})();
</script>""",
    unsafe_allow_html=True,
)

init_db()

if "username" not in st.session_state:
    st.switch_page("app.py")

# ── Session state ─────────────────────────────────────────────────────────────
# reader_open: (content_key, para_idx, action) | None
if "reader_open" not in st.session_state:
    st.session_state.reader_open = None
# reader_ai_pending: {text, content_key, para_idx, original} | None
if "reader_ai_pending" not in st.session_state:
    st.session_state.reader_ai_pending = None


# ── Content model ─────────────────────────────────────────────────────────────
@dataclass
class ContentBlock:
    content_key: str
    chapter: int
    scene: int | None
    label: str
    text: str
    source_path: Path


@st.cache_data(ttl=30, show_spinner=False)
def _load_blocks(prompts_path: str, output_path: str) -> list[dict]:
    """Returns serialisable dicts (cache can't store dataclasses with Path)."""
    scenes = discover_scenes(prompts_path)
    chapters = sorted({s.chapter for s in scenes})
    blocks: list[dict] = []

    for ch in chapters:
        cp = chapter_path(output_path, ch)
        if cp.exists():
            blocks.append(dict(
                content_key=f"CH{ch:02d}",
                chapter=ch,
                scene=None,
                label=f"Chapter {ch:02d}",
                text=cp.read_text(encoding="utf-8"),
                source_path=str(cp),
            ))
        else:
            for s in scenes_for_chapter(scenes, ch):
                sp = selected_path(output_path, ch, s.scene)
                if sp.exists():
                    blocks.append(dict(
                        content_key=s.scene_key,
                        chapter=ch,
                        scene=s.scene,
                        label=f"Chapter {ch:02d} · Scene {s.scene:02d}",
                        text=sp.read_text(encoding="utf-8"),
                        source_path=str(sp),
                    ))

    return blocks


def _block_from_dict(d: dict) -> ContentBlock:
    return ContentBlock(
        content_key=d["content_key"],
        chapter=d["chapter"],
        scene=d["scene"],
        label=d["label"],
        text=d["text"],
        source_path=Path(d["source_path"]),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_edit(block: ContentBlock, para_idx: int, original: str, new_text: str) -> bool:
    """Write the edited paragraph to disk. Returns False if a conflict is detected."""
    current_content = block.source_path.read_text(encoding="utf-8")
    current_paras = split_paragraphs(current_content)
    if para_idx >= len(current_paras):
        return False
    if current_paras[para_idx].strip() != original.strip():
        return False  # content changed since we loaded — conflict
    current_paras[para_idx] = new_text.strip()
    write_output(block.source_path, join_paragraphs(current_paras))
    add_edit(block.content_key, para_idx, st.session_state.username, original, new_text)
    return True


def _build_diff_html(original: str, revised: str) -> tuple[str, str]:
    import difflib
    import re

    def split_sentences(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]

    orig_sents = split_sentences(original)
    rev_sents = split_sentences(revised)
    matcher = difflib.SequenceMatcher(None, orig_sents, rev_sents, autojunk=False)

    orig_parts: list[str] = []
    rev_parts: list[str] = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            orig_parts += [html.escape(s) for s in orig_sents[i1:i2]]
            rev_parts += [html.escape(s) for s in rev_sents[j1:j2]]
        elif op == "replace":
            orig_parts += [f'<span class="diff-removed">{html.escape(s)}</span>' for s in orig_sents[i1:i2]]
            rev_parts += [f'<span class="diff-added">{html.escape(s)}</span>' for s in rev_sents[j1:j2]]
        elif op == "delete":
            orig_parts += [f'<span class="diff-removed">{html.escape(s)}</span>' for s in orig_sents[i1:i2]]
        elif op == "insert":
            rev_parts += [f'<span class="diff-added">{html.escape(s)}</span>' for s in rev_sents[j1:j2]]

    return " ".join(orig_parts), " ".join(rev_parts)


# ── Paragraph renderer ────────────────────────────────────────────────────────

def _render_paragraph(block: ContentBlock, para_idx: int, para_text: str, edit_history_keys: set) -> None:
    """Renders one paragraph with its action bar, comments, and any open action form."""
    key = block.content_key
    open_state = st.session_state.reader_open
    is_open = open_state is not None and open_state[0] == key and open_state[1] == para_idx
    open_action = open_state[2] if is_open else None

    is_edited = (key, para_idx) in edit_history_keys
    edited_class = " edited" if is_edited else ""
    para_id = f"{key}_{para_idx}"
    action_bar_class = " para-open" if is_open else ""

    with st.container():
        # ── Paragraph prose ──
        st.markdown(
            f'<div class="reader-para-block">'
            f'<div class="reader-paragraph{edited_class}" data-para-id="{para_id}">{html.escape(para_text)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Action bar (hidden by default; shown on click/selection via JS, or always when para-open) ──
        st.markdown(f'<div class="reader-action-bar{action_bar_class}" data-para-id="{para_id}">', unsafe_allow_html=True)
        col_c, col_ai, col_e, col_rest = st.columns([1, 1, 1, 8])
        with col_c:
            st.markdown('<div class="reader-action-bar-comment">', unsafe_allow_html=True)
            if st.button("✦ Note", key=f"btn_c_{key}_{para_idx}"):
                if is_open and open_action == "comment":
                    st.session_state.reader_open = None
                else:
                    st.session_state.reader_open = (key, para_idx, "comment")
                    st.session_state.reader_ai_pending = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_ai:
            st.markdown('<div class="reader-action-bar-ai">', unsafe_allow_html=True)
            if st.button("✧ AI", key=f"btn_ai_{key}_{para_idx}"):
                if is_open and open_action == "ai_prompt":
                    st.session_state.reader_open = None
                    st.session_state.reader_ai_pending = None
                else:
                    st.session_state.reader_open = (key, para_idx, "ai_prompt")
                    st.session_state.reader_ai_pending = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_e:
            st.markdown('<div class="reader-action-bar-edit">', unsafe_allow_html=True)
            if st.button("✎ Edit", key=f"btn_e_{key}_{para_idx}"):
                if is_open and open_action == "edit":
                    st.session_state.reader_open = None
                else:
                    st.session_state.reader_open = (key, para_idx, "edit")
                    st.session_state.reader_ai_pending = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Comments ──
        para_comments = get_comments(key, paragraph_index=para_idx)
        for c in para_comments:
            st.markdown(
                comment_annotation(
                    c["username"],
                    c["content"],
                    c["comment_type"],
                    c["created_at"][:16],
                ),
                unsafe_allow_html=True,
            )

        # ── Active action form ──
        if not is_open:
            return

        with st.container():
            if open_action == "comment":
                _render_comment_form(key, para_idx)
            elif open_action == "ai_prompt":
                _render_ai_form(block, para_idx, para_text)
            elif open_action == "edit":
                _render_edit_form(block, para_idx, para_text)


def _render_comment_form(content_key: str, para_idx: int) -> None:
    st.markdown('<div class="reader-action-open"><div class="action-header">Add note</div>', unsafe_allow_html=True)
    c_type = st.radio(
        "Type", ["Viewer note", "AI prompt note"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"ctype_{content_key}_{para_idx}",
    )
    comment_text = st.text_area(
        "Note",
        placeholder="Write your annotation here…",
        height=90,
        label_visibility="collapsed",
        key=f"ctxt_{content_key}_{para_idx}",
    )
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("Post", type="primary", key=f"cpost_{content_key}_{para_idx}"):
            if comment_text.strip():
                ct = "viewer" if c_type == "Viewer note" else "ai_prompt"
                add_comment(
                    content_key,
                    st.session_state.username,
                    comment_text.strip(),
                    ct,
                    paragraph_index=para_idx,
                )
                st.toast("Note posted.", icon="✅")
            st.session_state.reader_open = None
            st.rerun()
    with c2:
        if st.button("Cancel", key=f"ccancel_{content_key}_{para_idx}"):
            st.session_state.reader_open = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_edit_form(block: ContentBlock, para_idx: int, para_text: str) -> None:
    st.markdown('<div class="reader-action-open"><div class="action-header">Edit paragraph</div>', unsafe_allow_html=True)
    new_text = st.text_area(
        "Edit",
        value=para_text,
        height=200,
        label_visibility="collapsed",
        key=f"editarea_{block.content_key}_{para_idx}",
    )
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("Save", type="primary", key=f"esave_{block.content_key}_{para_idx}"):
            if new_text.strip() != para_text.strip():
                ok = _save_edit(block, para_idx, para_text, new_text.strip())
                if ok:
                    st.cache_data.clear()
                    st.toast("Edit saved.", icon="✅")
                else:
                    st.toast("Conflict: paragraph was edited by another user. Refresh to see latest.", icon="⚠️")
                    st.rerun()
                    return
            st.session_state.reader_open = None
            st.rerun()
    with c2:
        if st.button("Cancel", key=f"ecancel_{block.content_key}_{para_idx}"):
            st.session_state.reader_open = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_ai_form(block: ContentBlock, para_idx: int, para_text: str) -> None:
    cfg = load_config()
    pending = st.session_state.reader_ai_pending

    if pending and pending.get("content_key") == block.content_key and pending.get("para_idx") == para_idx:
        # Show diff and accept/discard
        st.markdown('<div class="reader-action-open"><div class="action-header">AI revision — review changes</div>', unsafe_allow_html=True)
        orig_html, rev_html = _build_diff_html(pending["original"], pending["text"])
        st.markdown(diff_view(orig_html, rev_html), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("Accept", type="primary", key=f"ai_acc_{block.content_key}_{para_idx}"):
                ok = _save_edit(block, para_idx, pending["original"], pending["text"])
                if ok:
                    st.cache_data.clear()
                    st.toast("Paragraph updated.", icon="✅")
                else:
                    st.toast("Conflict: paragraph changed since regeneration. Refresh and try again.", icon="⚠️")
                st.session_state.reader_open = None
                st.session_state.reader_ai_pending = None
                st.rerun()
        with c2:
            if st.button("Discard", key=f"ai_dis_{block.content_key}_{para_idx}"):
                st.session_state.reader_open = None
                st.session_state.reader_ai_pending = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Prompt form
    connected, conn_err = check_connectivity(cfg.ollama_url)
    st.markdown('<div class="reader-action-open"><div class="action-header">AI paragraph revision</div>', unsafe_allow_html=True)
    if not connected:
        st.markdown(info_banner(f"Ollama offline: {conn_err}", kind="error"), unsafe_allow_html=True)
    else:
        instruction = st.text_area(
            "Instruction",
            placeholder="e.g. Make this more visceral. Emphasise the sensory detail.",
            height=80,
            label_visibility="collapsed",
            key=f"ai_inst_{block.content_key}_{para_idx}",
        )
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("Regenerate", type="primary", key=f"ai_run_{block.content_key}_{para_idx}"):
                if instruction.strip():
                    paragraphs = split_paragraphs(block.text)
                    before, after = get_paragraph_context(paragraphs, para_idx, context_window=2)
                    user_prompt = build_paragraph_regen_user_prompt(para_text, before, after, instruction.strip())
                    system_prompt = (
                        "You are a prose editor for a dark romantic fantasy novel. "
                        "Maintain the voice, tense, and POV of the surrounding text exactly. "
                        "Output only the rewritten passage — no preamble."
                    )
                    with st.spinner("Generating revision…"):
                        try:
                            result = generate(
                                cfg.ollama_url, cfg.model_name,
                                system_prompt, user_prompt,
                                temperature=PARAGRAPH_REGEN_TEMPERATURE,
                                num_ctx=cfg.num_ctx,
                            )
                            st.session_state.reader_ai_pending = {
                                "text": result,
                                "content_key": block.content_key,
                                "para_idx": para_idx,
                                "original": para_text,
                            }
                        except (ConnectionError, TimeoutError, RuntimeError) as exc:
                            st.markdown(info_banner(str(exc), kind="error"), unsafe_allow_html=True)
                    st.rerun()
        with c2:
            if st.button("Cancel", key=f"ai_cancel_{block.content_key}_{para_idx}"):
                st.session_state.reader_open = None
                st.session_state.reader_ai_pending = None
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ── Sidebar chapter nav ───────────────────────────────────────────────────────

def _render_chapter_nav(blocks: list[ContentBlock]) -> None:
    chapters_seen: set[int] = set()
    with st.sidebar:
        st.markdown('<hr style="margin:0.75rem 0;">', unsafe_allow_html=True)
        st.markdown('<div class="nav-section-label">Contents</div>', unsafe_allow_html=True)
        for b in blocks:
            if b.chapter not in chapters_seen:
                chapters_seen.add(b.chapter)
                wc = len(b.text.split())
                st.markdown(
                    f'<div style="padding:0.3rem 1.25rem;font-family:var(--font-ui);'
                    f'font-size:0.8125rem;color:var(--text-secondary);">'
                    f'Chapter {b.chapter:02d}'
                    f'<span style="color:var(--text-muted);font-size:0.6875rem;margin-left:0.5rem;">'
                    f'{wc:,} w</span></div>',
                    unsafe_allow_html=True,
                )


# ── Main layout ───────────────────────────────────────────────────────────────
render_sidebar("Reader")

cfg = load_config()
errors = validate_config(cfg)
configured = len(errors) == 0

if not configured:
    st.markdown(
        '<div class="page-header"><div class="page-title">Reader</div>'
        '<div class="page-subtitle">Read the manuscript in its current form.</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        info_banner("Configure project paths in Settings before using the reader.", kind="warning"),
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Settings.py", label="Open Settings →", icon=":material/settings:")
    st.stop()

raw_blocks = _load_blocks(cfg.prompts_path, cfg.output_path)

if not raw_blocks:
    st.markdown(
        '<div class="page-header"><div class="page-title">Reader</div>'
        '<div class="page-subtitle">No completed scenes yet.</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        info_banner("Select at least one scene in the Pipeline before reading.", kind="info"),
        unsafe_allow_html=True,
    )
    st.stop()

blocks = [_block_from_dict(d) for d in raw_blocks]

_render_chapter_nav(blocks)

# Load edit history keys for the "edited" paragraph indicator
from database import get_edit_history
edit_keys: set[tuple[str, int]] = set()
for b in blocks:
    for edit in get_edit_history(b.content_key):
        edit_keys.add((edit["scene_key"], edit["paragraph_index"]))

# ── Stats header ──────────────────────────────────────────────────────────────
total_words = sum(len(b.text.split()) for b in blocks)
target_words = 95_000
pct = min(round(total_words / target_words * 100), 100)

st.markdown(
    f'<div style="text-align:center;margin-bottom:2rem;">'
    f'<div style="font-family:var(--font-display);font-size:3rem;font-weight:300;'
    f'color:var(--gold);line-height:1;">{total_words:,}</div>'
    f'<div style="font-family:var(--font-ui);font-size:0.625rem;font-weight:700;'
    f'letter-spacing:0.12em;text-transform:uppercase;color:var(--text-muted);margin-top:4px;">'
    f'Words written · {pct}% of target</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown('<hr style="margin:0 0 0.5rem;">', unsafe_allow_html=True)

# ── Manuscript content ────────────────────────────────────────────────────────
prev_chapter: int | None = None

for block in blocks:
    # Chapter heading when chapter changes
    if block.chapter != prev_chapter:
        prev_chapter = block.chapter
        st.markdown(
            f'<div class="reader-chapter-heading">Chapter {block.chapter:02d}</div>'
            f'<div class="reader-chapter-ornament">· · · ✦ · · ·</div>',
            unsafe_allow_html=True,
        )
    elif block.scene is not None:
        # Scene break within a chapter (when not assembled)
        st.markdown(
            f'<div class="reader-scene-label">Scene {block.scene:02d}</div>',
            unsafe_allow_html=True,
        )

    paragraphs = split_paragraphs(block.text)

    for para_idx, para_text in enumerate(paragraphs):
        if not para_text.strip():
            continue
        _render_paragraph(block, para_idx, para_text, edit_keys)

    # Scene/chapter separator
    st.markdown(ornament_divider(), unsafe_allow_html=True)

# ── Progress footer ───────────────────────────────────────────────────────────
target_lo, target_hi = 95_000, 115_000
st.markdown(
    f'<div class="reader-footer">'
    f'<span class="word-count">{total_words:,}</span>'
    f'words written of {target_lo:,}–{target_hi:,} target · {pct}% complete'
    f'</div>',
    unsafe_allow_html=True,
)
