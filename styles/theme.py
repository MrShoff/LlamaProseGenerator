from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Design token reference
# ---------------------------------------------------------------------------
# All colour tokens and typographic scale are documented in DESIGN_SYSTEM.md.
# This file is the single source of truth for *applied* CSS.

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────────── */
:root {
    --bg-base:        #0D0B14;
    --bg-surface:     #151220;
    --bg-elevated:    #1E1A2E;
    --bg-inset:       #0A0812;

    --text-primary:   #EDE8DF;
    --text-secondary: #8A7F9A;
    --text-muted:     #4A4458;
    --text-inverse:   #0D0B14;

    --gold:           #C9A84C;
    --gold-muted:     #8A6E2A;
    --gold-glow:      rgba(201, 168, 76, 0.15);
    --gold-subtle:    rgba(201, 168, 76, 0.07);

    --rose:           #9B4D6B;
    --rose-muted:     #6B3349;
    --rose-glow:      rgba(155, 77, 107, 0.15);

    --status-locked:    #3A3550;
    --status-needs:     #2A4A6A;
    --status-progress:  #4A3E1A;
    --status-complete:  #1A3C2A;
    --status-error:     #4A1A24;

    --border-subtle:  #1A1628;
    --border-medium:  #2A2640;
    --border-strong:  #3E3A58;

    --font-display:   'Cormorant Garamond', Georgia, serif;
    --font-ui:        'Inter', 'Segoe UI', system-ui, sans-serif;

    --radius-sm:      4px;
    --radius-md:      8px;
    --radius-lg:      12px;
    --radius-pill:    999px;

    --transition-fast: 120ms ease;
    --transition-base: 200ms ease;
    --transition-slow: 350ms ease;

    --shadow-card:    0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3);
    --shadow-elevated: 0 4px 24px rgba(0,0,0,0.6), 0 1px 4px rgba(0,0,0,0.5);
}

/* ── Global reset ──────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body {
    margin: 0;
    padding: 0;
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-ui);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Streamlit shell overrides ─────────────────────────────────────────── */
.stApp {
    background-color: var(--bg-base) !important;
}

/* Hide Streamlit chrome */
#MainMenu            { display: none !important; }
footer               { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stSidebarNav"]   { display: none !important; }
[data-testid="stToolbar"]      { display: none !important; }
.stDeployButton                { display: none !important; }

/* ── Sidebar ───────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: var(--bg-surface) !important;
    border-right: 1px solid var(--border-subtle) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background-color: var(--bg-surface) !important;
    padding-top: 0 !important;
}
/* Remove gap above sidebar content */
section[data-testid="stSidebar"] .block-container {
    padding-top: 0 !important;
}

/* ── Main content area ─────────────────────────────────────────────────── */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1200px;
}

/* ── Typography ────────────────────────────────────────────────────────── */
h1, h2, h3, h4 {
    font-family: var(--font-display) !important;
    color: var(--text-primary) !important;
    font-weight: 400;
    letter-spacing: 0.01em;
}
h1 { font-size: 2.25rem; font-weight: 300; }
h2 { font-size: 1.75rem; }
h3 { font-size: 1.375rem; }

p, li, span, label, div {
    font-family: var(--font-ui);
}

/* Override Streamlit markdown text colour */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: var(--text-primary);
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
/* primaryColor in config.toml handles primary button fill (gold).         */
/* We layer on shape, font, and interaction refinements here.              */
.stButton > button,
[data-testid^="baseButton"] {
    font-family: var(--font-ui) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.02em !important;
    border-radius: var(--radius-md) !important;
    padding: 0.5rem 1.25rem !important;
    transition: transform var(--transition-fast),
                box-shadow var(--transition-fast),
                background-color var(--transition-fast) !important;
}

/* Secondary button */
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-secondaryFormSubmit"] {
    background-color: transparent !important;
    border: 1px solid var(--border-medium) !important;
    color: var(--text-primary) !important;
}
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-secondaryFormSubmit"]:hover {
    background-color: var(--bg-elevated) !important;
    border-color: var(--border-strong) !important;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* Primary — hover lift (fill comes from config.toml primaryColor) */
button[data-testid="baseButton-primary"]:hover,
button[data-testid="baseButton-primaryFormSubmit"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px var(--gold-glow);
}
button[data-testid="baseButton-primary"]:active,
button[data-testid="baseButton-primaryFormSubmit"]:active {
    transform: translateY(0);
}

/* Focus ring */
.stButton > button:focus-visible,
[data-testid^="baseButton"]:focus-visible {
    outline: 2px solid var(--gold) !important;
    outline-offset: 2px;
}

/* ── Form inputs ───────────────────────────────────────────────────────── */
[data-testid="stTextInput"] > div > div > input,
[data-testid="stTextArea"]  > div > div > textarea,
[data-testid="stNumberInput"] input {
    background-color: var(--bg-inset) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.875rem !important;
    transition: border-color var(--transition-fast);
}
[data-testid="stTextInput"] > div > div > input:focus,
[data-testid="stTextArea"]  > div > div > textarea:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 3px var(--gold-glow) !important;
    outline: none !important;
}
[data-testid="stTextInput"] > div > div > input::placeholder,
[data-testid="stTextArea"]  > div > div > textarea::placeholder {
    color: var(--text-muted) !important;
}

/* Input labels */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"]  label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {
    color: var(--text-secondary) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background-color: var(--bg-inset) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid var(--border-medium) !important;
    gap: 0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--text-secondary) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 0.625rem 1.25rem !important;
    transition: all var(--transition-fast) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background-color: var(--bg-elevated) !important;
}
[data-testid="stTabs"] [aria-selected="true"][data-baseweb="tab"] {
    color: var(--gold) !important;
    border-bottom-color: var(--gold) !important;
    background-color: transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding: 1.5rem 0 0 0 !important;
}

/* ── Dividers ──────────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid var(--border-subtle) !important;
    margin: 1.5rem 0 !important;
}

/* ── Notifications / alerts ────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-medium) !important;
}

/* ── Page link (sidebar nav) ───────────────────────────────────────────── */
[data-testid="stPageLink"] a {
    color: var(--text-secondary) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.875rem !important;
    font-weight: 500;
    text-decoration: none !important;
    display: flex;
    align-items: center;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
}
[data-testid="stPageLink"] a:hover {
    color: var(--text-primary) !important;
    background-color: var(--bg-elevated) !important;
}
[data-testid="stPageLink-active"] a {
    color: var(--gold) !important;
    background-color: var(--gold-subtle) !important;
}

/* ── Spinner ───────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div {
    border-top-color: var(--gold) !important;
}

/* ── Progress bar ──────────────────────────────────────────────────────── */
[data-testid="stProgressBar"] > div > div {
    background-color: var(--gold) !important;
    background-image: linear-gradient(90deg, var(--gold-muted), var(--gold)) !important;
}
[data-testid="stProgressBar"] > div {
    background-color: var(--border-medium) !important;
    border-radius: var(--radius-pill) !important;
}

/* ── Expander ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
    background-color: var(--bg-surface) !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
}

/* ── Columns ───────────────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb {
    background: var(--border-medium);
    border-radius: var(--radius-pill);
}
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }

/* ── Animations ────────────────────────────────────────────────────────── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-subtle {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.7; }
}
@keyframes spin-ring {
    to { transform: rotate(360deg); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
}

.animate-fade-in {
    animation: fadeIn var(--transition-base) ease both;
}
.animate-pulse {
    animation: pulse-subtle 2s ease infinite;
}

/* ── Scriptorium custom classes ─────────────────────────────────────────── */

/* Sidebar logo block */
.scriptorium-logo {
    padding: 1.75rem 1.25rem 1.25rem;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 0.5rem;
}
.scriptorium-logo .title {
    font-family: var(--font-display);
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--gold);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    line-height: 1.2;
}
.scriptorium-logo .subtitle {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 400;
    color: var(--text-muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 3px;
}

/* Ollama status pill */
.ollama-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: var(--radius-pill);
    margin: 0 1.25rem 0.75rem;
}
.ollama-status.online {
    background: rgba(42, 92, 66, 0.3);
    border: 1px solid rgba(42, 92, 66, 0.6);
    color: #6DD5A0;
}
.ollama-status.offline {
    background: rgba(107, 42, 53, 0.3);
    border: 1px solid rgba(107, 42, 53, 0.6);
    color: #C87070;
}
.ollama-status .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.ollama-status.online  .dot { background: #6DD5A0; }
.ollama-status.offline .dot { background: #C87070; animation: pulse-subtle 2s ease infinite; }

/* Sidebar nav section label */
.nav-section-label {
    font-family: var(--font-ui);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0.75rem 1.25rem 0.25rem;
}

/* User badge at sidebar bottom */
.user-badge {
    padding: 0.875rem 1.25rem;
    border-top: 1px solid var(--border-subtle);
    margin-top: auto;
}
.user-badge .label {
    font-size: 0.6875rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}
.user-badge .name {
    font-size: 0.875rem;
    color: var(--text-primary);
    font-weight: 500;
    margin-top: 2px;
}

/* Status badge pills */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: var(--font-ui);
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: var(--radius-pill);
}
.status-badge.locked   { background: rgba(58,53,80,0.4);  border: 1px solid rgba(58,53,80,0.7);  color: #6B6488; }
.status-badge.needs    { background: rgba(42,74,106,0.3); border: 1px solid rgba(42,74,106,0.6); color: #7AB3D8; }
.status-badge.progress { background: rgba(74,62,26,0.35); border: 1px solid rgba(74,62,26,0.7); color: #C9A84C; }
.status-badge.complete { background: rgba(26,60,42,0.35); border: 1px solid rgba(26,60,42,0.7); color: #6DD5A0; }
.status-badge.error    { background: rgba(74,26,36,0.35); border: 1px solid rgba(74,26,36,0.7); color: #C87070; }

/* Prose card */
.prose-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-lg);
    padding: 1.75rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-card);
    animation: fadeIn var(--transition-base) ease both;
}
.prose-card .card-header {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding-bottom: 0.875rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.prose-card .card-body {
    font-family: var(--font-display);
    font-size: 1.0625rem;
    line-height: 1.8;
    color: var(--text-primary);
}
.prose-card .card-footer {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    color: var(--text-muted);
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    gap: 1rem;
}

/* Stat card */
.stat-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem;
    text-align: center;
    transition: border-color var(--transition-base), box-shadow var(--transition-base);
}
.stat-card:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-card);
}
.stat-card .stat-value {
    font-family: var(--font-display);
    font-size: 2.25rem;
    font-weight: 300;
    color: var(--gold);
    line-height: 1.1;
}
.stat-card .stat-label {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-top: 0.375rem;
}

/* Page header */
.page-header {
    margin-bottom: 2rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid var(--border-subtle);
}
.page-header .page-title {
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 300;
    color: var(--text-primary);
    letter-spacing: 0.02em;
    margin: 0;
}
.page-header .page-subtitle {
    font-family: var(--font-ui);
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-top: 0.375rem;
}

/* Decorative ornament divider */
.ornament-divider {
    text-align: center;
    color: var(--gold);
    font-size: 0.875rem;
    letter-spacing: 0.5em;
    margin: 1.5rem 0;
    opacity: 0.5;
}

/* Generation progress card */
.generation-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-lg);
    padding: 3rem 2rem;
    text-align: center;
    animation: pulse-subtle 2s ease infinite;
}
.generation-card .gen-spinner {
    width: 48px; height: 48px;
    border: 3px solid var(--border-medium);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin-ring 0.9s linear infinite;
    margin: 0 auto 1.5rem;
}
.generation-card .gen-label {
    font-family: var(--font-display);
    font-size: 1.375rem;
    font-weight: 400;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
}
.generation-card .gen-sublabel {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    color: var(--text-muted);
    letter-spacing: 0.05em;
}

/* Comment annotation */
.comment-annotation {
    border-left: 3px solid var(--border-medium);
    padding: 0.625rem 1rem;
    margin-top: 0.5rem;
    background: var(--bg-inset);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.comment-annotation.ai-prompt {
    border-left-color: var(--rose);
}
.comment-annotation .comment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.375rem;
}
.comment-annotation .comment-user {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-primary);
}
.comment-annotation .comment-time {
    font-family: var(--font-ui);
    font-size: 0.625rem;
    color: var(--text-muted);
}
.comment-annotation .comment-body {
    font-family: var(--font-ui);
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.55;
}
.comment-annotation .ai-badge {
    font-size: 0.5625rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rose);
    background: var(--rose-glow);
    padding: 2px 6px;
    border-radius: var(--radius-pill);
    border: 1px solid var(--rose-muted);
    margin-left: 6px;
}

/* Info / warning banner */
.info-banner {
    background: var(--bg-elevated);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
    padding: 0.875rem 1.25rem;
    font-family: var(--font-ui);
    font-size: 0.875rem;
    color: var(--text-secondary);
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}
.info-banner.warning {
    border-color: rgba(107, 84, 26, 0.6);
    background: rgba(74,62,26,0.2);
}
.info-banner.error {
    border-color: rgba(107, 42, 53, 0.6);
    background: rgba(74,26,36,0.2);
    color: #C87070;
}
.info-banner.success {
    border-color: rgba(26,60,42,0.6);
    background: rgba(26,60,42,0.2);
    color: #6DD5A0;
}
.info-banner .banner-icon { flex-shrink: 0; margin-top: 1px; }

/* Username entry screen */
.username-screen {
    max-width: 420px;
    margin: 0 auto;
    padding-top: 4rem;
    animation: fadeIn 400ms ease both;
}
.username-screen .logo-mark {
    font-family: var(--font-display);
    font-size: 3rem;
    font-weight: 300;
    color: var(--gold);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-align: center;
    margin-bottom: 0.25rem;
}
.username-screen .logo-sub {
    text-align: center;
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 3rem;
}
.username-screen .prompt-text {
    font-family: var(--font-display);
    font-size: 1.125rem;
    color: var(--text-secondary);
    text-align: center;
    margin-bottom: 2rem;
    line-height: 1.6;
}

/* Settings section card */
.settings-section {
    background: var(--bg-surface);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}
.settings-section .section-title {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 1rem;
    padding-bottom: 0.625rem;
    border-bottom: 1px solid var(--border-subtle);
}

/* Chapter progress segment bar */
.chapter-bar {
    display: flex;
    gap: 3px;
    height: 4px;
    border-radius: var(--radius-pill);
    overflow: hidden;
    margin-top: 0.375rem;
}
.chapter-bar .seg {
    flex: 1;
    border-radius: 2px;
    background: var(--border-medium);
    transition: background var(--transition-slow);
}
.chapter-bar .seg.complete { background: var(--gold); }
.chapter-bar .seg.progress { background: var(--gold-muted); }

/* ── Scene picker (Pipeline sidebar) ────────────────────────────────────── */
.scene-nav-group {
    padding: 0 0.75rem;
}
.scene-nav-chapter {
    font-family: var(--font-ui);
    font-size: 0.5875rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0.875rem 0.5rem 0.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.scene-nav-chapter:not(:first-child) {
    border-top: 1px solid var(--border-subtle);
}
/* Make scene picker st.buttons look like nav items */
.scene-nav-group .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    font-family: var(--font-ui) !important;
    font-size: 0.8125rem !important;
    font-weight: 400 !important;
    padding: 0.375rem 0.625rem !important;
    border-radius: var(--radius-sm) !important;
    border: none !important;
    background: transparent !important;
    color: var(--text-secondary) !important;
    width: 100% !important;
    letter-spacing: 0 !important;
    margin-bottom: 1px;
    transition: background var(--transition-fast), color var(--transition-fast) !important;
}
.scene-nav-group .stButton > button:hover {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    transform: none !important;
    box-shadow: none !important;
}
.scene-active .stButton > button {
    background: var(--gold-subtle) !important;
    color: var(--gold) !important;
    font-weight: 500 !important;
}
.scene-locked .stButton > button {
    opacity: 0.4 !important;
    cursor: default !important;
}

/* ── Critique card ──────────────────────────────────────────────────────── */
.critique-card {
    background: var(--bg-inset);
    border: 1px solid var(--border-medium);
    border-left: 3px solid var(--rose);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    padding: 1.25rem 1.5rem;
    font-family: var(--font-ui);
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--text-secondary);
    white-space: pre-wrap;
}
.critique-card .critique-header {
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--rose);
    margin-bottom: 0.875rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-subtle);
}

/* ── Diff view ──────────────────────────────────────────────────────────── */
.diff-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-top: 0.5rem;
}
.diff-col-label {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.625rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-subtle);
}
.diff-col-label.original { color: var(--text-muted); }
.diff-col-label.revised  { color: var(--gold); }
.diff-prose {
    font-family: var(--font-display);
    font-size: 1rem;
    line-height: 1.8;
    color: var(--text-primary);
    white-space: pre-wrap;
}
.diff-removed {
    background: rgba(139, 40, 40, 0.25);
    color: #C87070;
    border-radius: 2px;
    padding: 0 2px;
}
.diff-added {
    background: rgba(40, 100, 60, 0.22);
    color: #70C894;
    border-radius: 2px;
    padding: 0 2px;
}

/* ── Locked scene state ─────────────────────────────────────────────────── */
.locked-state {
    text-align: center;
    padding: 4rem 2rem;
}
.locked-state .lock-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    opacity: 0.4;
}
.locked-state .lock-title {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 300;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
}
.locked-state .lock-subtitle {
    font-family: var(--font-ui);
    font-size: 0.875rem;
    color: var(--text-muted);
}

/* ── st.status() override ───────────────────────────────────────────────── */
[data-testid="stStatusWidget"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: var(--radius-md) !important;
}

/* ── Reader ─────────────────────────────────────────────────────────────── */
.reader-chapter-heading {
    font-family: var(--font-display);
    font-size: 2.25rem;
    font-weight: 300;
    color: var(--text-primary);
    letter-spacing: 0.06em;
    text-align: center;
    margin: 2.5rem 0 0.375rem;
    line-height: 1.2;
}
.reader-chapter-ornament {
    text-align: center;
    color: var(--gold);
    font-size: 0.75rem;
    letter-spacing: 0.45em;
    opacity: 0.55;
    margin-bottom: 2.25rem;
}
.reader-scene-label {
    font-family: var(--font-ui);
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    text-align: center;
    margin: 2rem 0 1.5rem;
}
.reader-para-block {
    margin-bottom: 0.25rem;
}
.reader-paragraph {
    font-family: var(--font-display);
    font-size: 1.125rem;
    line-height: 1.9;
    color: var(--text-primary);
    padding: 0.5rem 0.875rem;
    border-radius: var(--radius-sm);
    border-left: 3px solid transparent;
    transition: background var(--transition-fast), border-color var(--transition-fast);
    white-space: pre-wrap;
}
.reader-paragraph:hover {
    background: var(--bg-elevated);
}
.reader-paragraph.edited {
    border-left-color: var(--gold-muted);
}
/* Action bar buttons — JS stamps .reader-action-bar-buttons on the real stHorizontalBlock
   and manages display:none / display:'' to show/hide it on click or text selection. */
.reader-action-bar-buttons {
    padding: 0 0.875rem 0.5rem !important;
    margin-top: -0.25rem !important;
    gap: 0.375rem !important;
}
.reader-action-bar-buttons .stButton > button {
    font-size: 0.625rem !important;
    padding: 1px 7px !important;
    border-radius: var(--radius-pill) !important;
    border: 1px solid var(--border-medium) !important;
    background: transparent !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    min-height: unset !important;
    line-height: 1.6 !important;
    transition: border-color var(--transition-fast),
                color var(--transition-fast), background var(--transition-fast) !important;
    transform: none !important;
    box-shadow: none !important;
}
.reader-action-bar-buttons .stButton > button:hover {
    border-color: var(--border-strong) !important;
    color: var(--text-primary) !important;
    background: var(--bg-elevated) !important;
    box-shadow: none !important;
}
/* AI button (2nd column) */
.reader-action-bar-buttons [data-testid="stColumn"]:nth-child(2) .stButton > button:hover {
    border-color: var(--rose-muted) !important;
    color: var(--rose) !important;
    background: var(--rose-glow) !important;
}
/* Edit button (3rd column) */
.reader-action-bar-buttons [data-testid="stColumn"]:nth-child(3) .stButton > button:hover {
    border-color: var(--gold-muted) !important;
    color: var(--gold) !important;
    background: var(--gold-subtle) !important;
}
/* Active action block */
.reader-action-open {
    background: var(--bg-inset);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
    padding: 1rem 1.25rem;
    margin: 0.25rem 0 0.75rem;
}
.reader-action-open .action-header {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
}
/* Progress footer */
.reader-footer {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    text-align: center;
    padding: 2.5rem 0 1rem;
    border-top: 1px solid var(--border-subtle);
    margin-top: 3rem;
}
.reader-footer .word-count {
    font-size: 1.25rem;
    font-family: var(--font-display);
    font-weight: 300;
    color: var(--gold);
    letter-spacing: 0.02em;
    display: block;
    margin-bottom: 0.375rem;
}

/* ── Auto-pilot log ──────────────────────────────────────────────────────── */
.autopilot-log {
    height: 360px;
    overflow-y: auto;
    background: var(--bg-inset);
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
    font-family: var(--font-ui);
    font-size: 0.8125rem;
    color: var(--text-secondary);
    margin: 0.75rem 0 1.25rem;
    scroll-behavior: smooth;
}
.autopilot-log-line {
    padding: 0.1rem 0;
    white-space: pre-wrap;
    line-height: 1.6;
}
.log-ts {
    font-variant-numeric: tabular-nums;
    color: var(--text-muted);
    font-size: 0.75em;
    letter-spacing: 0.03em;
    user-select: none;
}

/* ── Pipeline step indicator ─────────────────────────────────────────────── */
.step-indicator {
    display: flex;
    align-items: center;
    padding: 0.75rem 0 1rem;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
    min-width: 72px;
}
.step-dot {
    width: 30px; height: 30px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 600;
    transition: all var(--transition-base);
    flex-shrink: 0;
}
.step-label {
    font-family: var(--font-ui);
    font-size: 0.625rem;
    font-weight: 500;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
}
.step-conn {
    flex: 1;
    height: 2px;
    background: var(--border-medium);
    margin-bottom: 1.1rem;
    transition: background var(--transition-slow);
    min-width: 16px;
}
.step-conn.done { background: var(--gold-muted); }
.step-item.step-done .step-dot {
    background: rgba(26,60,42,0.5);
    border: 1px solid rgba(42,92,66,0.6);
    color: #6DD5A0;
}
.step-item.step-done .step-label { color: var(--text-muted); }
.step-item.step-active .step-dot {
    background: var(--gold-subtle);
    border: 2px solid var(--gold);
    color: var(--gold);
}
.step-item.step-active .step-label { color: var(--gold); font-weight: 700; }
.step-item.step-future .step-dot {
    background: var(--bg-inset);
    border: 1px solid var(--border-medium);
    color: var(--text-muted);
}
.step-item.step-future .step-label { color: var(--text-muted); }

/* ── Scene sidebar states ─────────────────────────────────────────────────── */
.scene-complete .stButton > button {
    color: #6DD5A0 !important;
}
.scene-complete.scene-active .stButton > button {
    color: var(--gold) !important;
}
.scene-intervention .stButton > button {
    color: #C87070 !important;
    background: rgba(74,26,36,0.15) !important;
}
.scene-intervention .stButton > button:hover {
    background: rgba(74,26,36,0.35) !important;
    color: #E08080 !important;
}

/* ── Intervention banner ──────────────────────────────────────────────────── */
.intervention-banner {
    background: rgba(74,26,36,0.2);
    border: 1px solid rgba(107,42,53,0.65);
    border-left: 4px solid #C87070;
    border-radius: var(--radius-md);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    animation: fadeIn var(--transition-base) ease both;
}
.intervention-banner .int-header {
    font-family: var(--font-ui);
    font-size: 0.6875rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #C87070;
    margin-bottom: 0.75rem;
}
.intervention-banner .int-fixes {
    font-family: var(--font-ui);
    font-size: 0.875rem;
    color: var(--text-secondary);
    line-height: 1.65;
}
.intervention-banner .int-fix-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
}
.intervention-banner .int-fix-bullet {
    color: #C87070;
    flex-shrink: 0;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
