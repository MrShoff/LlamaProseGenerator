from __future__ import annotations

import streamlit as st

from _sidebar import render as render_sidebar
from config import Config, load_config, save_config, validate_config
from ollama_client import check_connectivity, list_local_models
from scene_manager import discover_scenes
from styles.components import info_banner, page_header, settings_section_open, settings_section_close
from styles.theme import inject_styles

st.set_page_config(
    page_title="Settings · The Scriptorium",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()

if "username" not in st.session_state:
    st.switch_page("app.py")

render_sidebar("Settings")

st.markdown(
    page_header("Settings", "Configure your project and model connection."),
    unsafe_allow_html=True,
)

cfg = load_config()

# ── Project paths ─────────────────────────────────────────────────────────────
st.markdown(settings_section_open("Project Directories"), unsafe_allow_html=True)

prompts_path = st.text_input(
    "Prompts directory",
    value=cfg.prompts_path,
    placeholder=r"D:\YourProject\04_Prompts",
    help="Absolute path to the folder containing CH##_SC##_*.md prompt files.",
)
output_path = st.text_input(
    "Output directory",
    value=cfg.output_path,
    placeholder=r"D:\YourProject\05_Local_Model_Output",
    help="Absolute path where generated scenes will be saved.",
)

# Live directory validation
from pathlib import Path
prompts_ok = bool(prompts_path) and Path(prompts_path).is_dir()
output_specified = bool(output_path)

if prompts_path and not prompts_ok:
    st.markdown(
        info_banner("Prompts directory not found — check the path.", kind="error"),
        unsafe_allow_html=True,
    )
elif prompts_ok:
    with st.spinner("Scanning for scenes…"):
        scenes = discover_scenes(prompts_path)
    st.markdown(
        info_banner(f"Found {len(scenes)} scene{'s' if len(scenes) != 1 else ''} across "
                    f"{len({s.chapter for s in scenes})} chapter(s).", kind="success"),
        unsafe_allow_html=True,
    )

st.markdown(settings_section_close(), unsafe_allow_html=True)

# ── Ollama connection ─────────────────────────────────────────────────────────
st.markdown(settings_section_open("Ollama Connection"), unsafe_allow_html=True)

ollama_url = st.text_input(
    "Ollama URL",
    value=cfg.ollama_url or "http://localhost:11434",
    help="Base URL of the running Ollama instance.",
)

col_test, col_status = st.columns([1, 3])
with col_test:
    test_clicked = st.button("Test connection", use_container_width=True)

if test_clicked:
    with st.spinner("Connecting…"):
        ok, err = check_connectivity(ollama_url)
    if ok:
        st.markdown(
            info_banner("Ollama is reachable.", kind="success"),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            info_banner(f"Cannot reach Ollama: {err}", kind="error"),
            unsafe_allow_html=True,
        )

# Model selector — populated from Ollama if reachable
available_models: list[str] = []
conn_ok, _ = check_connectivity(ollama_url, timeout=3)
if conn_ok:
    available_models = list_local_models(ollama_url)

if available_models:
    current_idx = 0
    if cfg.model_name in available_models:
        current_idx = available_models.index(cfg.model_name)
    model_name = st.selectbox(
        "Model",
        options=available_models,
        index=current_idx,
        help="Select the Ollama model to use for generation.",
    )
else:
    model_name = st.text_input(
        "Model name",
        value=cfg.model_name,
        placeholder="e.g. tinyrick/gemma-4-31B-it-uncensored-heretic-llmfan46:Q4_K_M",
        help="Exact model name as shown in `ollama list`. "
             "Connect to Ollama above for a dropdown instead.",
    )

st.markdown(settings_section_close(), unsafe_allow_html=True)

# ── Generation parameters ─────────────────────────────────────────────────────
st.markdown(settings_section_open("Generation Parameters"), unsafe_allow_html=True)

num_ctx = st.number_input(
    "Context window (tokens)",
    min_value=512,
    max_value=131072,
    value=cfg.num_ctx or 8192,
    step=1024,
    help="Number of tokens to use as the context window. "
         "Larger values allow longer prompts but use more VRAM.",
)

st.markdown(settings_section_close(), unsafe_allow_html=True)

# ── Save ──────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

save_col, _ = st.columns([1, 3])
with save_col:
    save_clicked = st.button("Save settings", type="primary", use_container_width=True)

if save_clicked:
    new_cfg = Config(
        prompts_path=prompts_path.strip(),
        output_path=output_path.strip(),
        ollama_url=ollama_url.strip(),
        model_name=(model_name or "").strip(),
        num_ctx=int(num_ctx),
    )
    validation_errors = validate_config(new_cfg)
    if validation_errors:
        for e in validation_errors:
            st.markdown(info_banner(e, kind="error"), unsafe_allow_html=True)
    else:
        save_config(new_cfg)
        st.markdown(
            info_banner("Settings saved.", kind="success"),
            unsafe_allow_html=True,
        )
        # Clear any cached data that depended on the old config
        st.cache_data.clear()
