from __future__ import annotations

# ---------------------------------------------------------------------------
# HTML component generators
# All functions return HTML strings for use with st.markdown(unsafe_allow_html=True).
# Classes are defined in styles/theme.py.
# ---------------------------------------------------------------------------

_STATUS_META: dict[str, tuple[str, str, str]] = {
    "locked":       ("locked",   "◌",  "Locked"),
    "needs_draft":  ("needs",    "✦",  "Needs Draft"),
    "has_variants": ("progress", "◈",  "Variants Ready"),
    "in_critique":  ("progress", "◎",  "Critiquing"),
    "has_critique": ("progress", "◉",  "Critique Done"),
    "in_revision":  ("progress", "◈",  "Revising"),
    "has_revision": ("progress", "◈",  "Revised"),
    "selected":     ("complete", "✓",  "Selected"),
    "assembled":    ("complete", "◆",  "Assembled"),
    "error":        ("error",    "✕",  "Error"),
}


def status_badge(status: str) -> str:
    cls, icon, label = _STATUS_META.get(status, ("needs", "?", status))
    return (
        f'<span class="status-badge {cls}">'
        f'<span>{icon}</span>{label}'
        f'</span>'
    )


def ollama_indicator(connected: bool, error: str = "") -> str:
    if connected:
        return (
            '<div class="ollama-status online">'
            '<div class="dot"></div>'
            'Ollama connected'
            '</div>'
        )
    tip = f' title="{error}"' if error else ""
    return (
        f'<div class="ollama-status offline"{tip}>'
        '<div class="dot"></div>'
        'Ollama offline'
        '</div>'
    )


def scriptorium_logo() -> str:
    return (
        '<div class="scriptorium-logo">'
        '<div class="title">The Scriptorium</div>'
        '<div class="subtitle">Prose Generation Studio</div>'
        '</div>'
    )


def nav_section_label(label: str) -> str:
    return f'<div class="nav-section-label">{label}</div>'


def user_badge(username: str) -> str:
    return (
        '<div class="user-badge">'
        '<div class="label">Logged in as</div>'
        f'<div class="name">{username}</div>'
        '</div>'
    )


def page_header(title: str, subtitle: str = "") -> str:
    sub = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    return (
        f'<div class="page-header animate-fade-in">'
        f'<div class="page-title">{title}</div>'
        f'{sub}'
        f'</div>'
    )


def stat_card(value: str | int, label: str) -> str:
    return (
        f'<div class="stat-card">'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'</div>'
    )


def ornament_divider() -> str:
    return '<div class="ornament-divider">· · · ✦ · · ·</div>'


def prose_card_open(title: str, meta: str = "") -> str:
    meta_html = f'<span>{meta}</span>' if meta else ""
    return (
        f'<div class="prose-card animate-fade-in">'
        f'<div class="card-header"><span>{title}</span>{meta_html}</div>'
        f'<div class="card-body">'
    )


def prose_card_close(footer: str = "") -> str:
    footer_html = (
        f'<div class="card-footer">{footer}</div>' if footer else ""
    )
    return f'</div>{footer_html}</div>'


def generation_card(label: str, sublabel: str = "") -> str:
    sub = f'<div class="gen-sublabel">{sublabel}</div>' if sublabel else ""
    return (
        '<div class="generation-card">'
        '<div class="gen-spinner"></div>'
        f'<div class="gen-label">{label}</div>'
        f'{sub}'
        '</div>'
    )


def comment_annotation(
    username: str,
    content: str,
    comment_type: str,
    timestamp: str,
) -> str:
    is_ai = comment_type == "ai_prompt"
    extra_class = " ai-prompt" if is_ai else ""
    ai_badge = '<span class="ai-badge">AI Prompt</span>' if is_ai else ""
    return (
        f'<div class="comment-annotation{extra_class}">'
        f'<div class="comment-header">'
        f'<span class="comment-user">{username}{ai_badge}</span>'
        f'<span class="comment-time">{timestamp}</span>'
        f'</div>'
        f'<div class="comment-body">{content}</div>'
        f'</div>'
    )


def info_banner(message: str, kind: str = "info") -> str:
    icons = {"info": "ℹ", "warning": "⚠", "error": "✕", "success": "✓"}
    icon = icons.get(kind, "ℹ")
    return (
        f'<div class="info-banner {kind}">'
        f'<span class="banner-icon">{icon}</span>'
        f'<span>{message}</span>'
        f'</div>'
    )


def settings_section_open(title: str) -> str:
    return (
        f'<div class="settings-section">'
        f'<div class="section-title">{title}</div>'
    )


def settings_section_close() -> str:
    return '</div>'


def chapter_progress_bar(completed: int, total: int) -> str:
    segs: list[str] = []
    for i in range(total):
        cls = "complete" if i < completed else ""
        segs.append(f'<div class="seg {cls}"></div>')
    inner = "".join(segs)
    return f'<div class="chapter-bar">{inner}</div>'


def username_screen() -> str:
    return (
        '<div class="username-screen">'
        '<div class="logo-mark">The Scriptorium</div>'
        '<div class="logo-sub">A Prose Generation Studio</div>'
        '<div class="prompt-text">'
        'Who enters the archive today?'
        '</div>'
        '</div>'
    )
