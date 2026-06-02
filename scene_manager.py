from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_DRAFT_RE = re.compile(r"CH(\d+)_SC(\d+)_DRAFT_PROMPT\.md$", re.IGNORECASE)

# Temperatures for each draft variant — A is conservative, C is bold.
VARIANT_TEMPERATURES: dict[str, float] = {"a": 0.7, "b": 0.85, "c": 1.0}
CRITIQUE_TEMPERATURE = 0.3
REVISION_TEMPERATURE = 0.7
PARAGRAPH_REGEN_TEMPERATURE = 0.75

# Paragraph separator used when splitting prose into addressable units.
_PARA_SEP = "\n\n"


@dataclass(frozen=True, order=True)
class SceneInfo:
    chapter: int
    scene: int
    scene_key: str = field(compare=False)
    prompts_dir: Path = field(compare=False)


# ---------------------------------------------------------------------------
# Scene key helper
# ---------------------------------------------------------------------------

def make_scene_key(chapter: int, scene: int) -> str:
    return f"CH{chapter:02d}_SC{scene:02d}"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_scenes(prompts_path: str | Path) -> list[SceneInfo]:
    root = Path(prompts_path)
    scenes: list[SceneInfo] = []
    for p in root.rglob("*_DRAFT_PROMPT.md"):
        m = _DRAFT_RE.search(p.name)
        if m:
            ch, sc = int(m.group(1)), int(m.group(2))
            scenes.append(
                SceneInfo(
                    chapter=ch,
                    scene=sc,
                    scene_key=make_scene_key(ch, sc),
                    prompts_dir=p.parent,
                )
            )
    return sorted(scenes)


def scenes_for_chapter(scenes: list[SceneInfo], chapter: int) -> list[SceneInfo]:
    return sorted(s for s in scenes if s.chapter == chapter)


# ---------------------------------------------------------------------------
# Prompt file paths
# ---------------------------------------------------------------------------

def _prompt_path(info: SceneInfo, prompt_type: str) -> Path:
    return info.prompts_dir / f"CH{info.chapter:02d}_SC{info.scene:02d}_{prompt_type}.md"


def get_continuity_handoff(info: SceneInfo) -> Path | None:
    matches = list(info.prompts_dir.glob(f"*_TO_SC{info.scene:02d}_CONTINUITY_HANDOFF.md"))
    return matches[0] if matches else None


def read_prompt(info: SceneInfo, prompt_type: str) -> str:
    path = _prompt_path(info, prompt_type)
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Output file paths
# ---------------------------------------------------------------------------

def _output_dir(output_path: str | Path, chapter: int) -> Path:
    return Path(output_path) / f"Chapter_{chapter:02d}"


def variant_path(output_path: str | Path, chapter: int, scene: int, variant: str) -> Path:
    return _output_dir(output_path, chapter) / f"scene_{scene:02d}_variant_{variant}.md"


def critique_path(output_path: str | Path, chapter: int, scene: int, variant: str) -> Path:
    return _output_dir(output_path, chapter) / f"scene_{scene:02d}_variant_{variant}_critique.md"


def revision_path(output_path: str | Path, chapter: int, scene: int, variant: str) -> Path:
    return _output_dir(output_path, chapter) / f"scene_{scene:02d}_variant_{variant}_revised.md"


def selected_path(output_path: str | Path, chapter: int, scene: int) -> Path:
    return _output_dir(output_path, chapter) / f"scene_{scene:02d}_selected.md"


def chapter_path(output_path: str | Path, chapter: int) -> Path:
    return _output_dir(output_path, chapter) / f"chapter_{chapter:02d}.md"


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_output(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------

def build_system_prompt(
    info: SceneInfo,
    output_path: str | Path,
    all_scenes: list[SceneInfo],
) -> str:
    parts: list[str] = [read_prompt(info, "CONTEXT_PACKET")]

    idx = all_scenes.index(info)
    if idx > 0:
        prior = all_scenes[idx - 1]
        prior_text = read_output(selected_path(output_path, prior.chapter, prior.scene))
        if prior_text:
            parts.append("---\nPRIOR SCENE (for continuity):\n" + prior_text)

    handoff = get_continuity_handoff(info)
    if handoff:
        parts.append("---\nCONTINUITY HANDOFF:\n" + handoff.read_text(encoding="utf-8"))

    return "\n\n".join(parts)


def build_critique_user_prompt(info: SceneInfo, variant_text: str) -> str:
    critique_instructions = read_prompt(info, "CRITIQUE_PROMPT")
    verdict_block = (
        "\n\n---\nVERDICT REQUIRED:\n"
        "After your critique, end your response with exactly one of:\n\n"
        "VERDICT: PASS\n"
        "VERDICT: FAIL\n\n"
        "Use VERDICT: PASS only if the scene meets all major criteria with no critical issues.\n"
        "Use VERDICT: FAIL if critical issues require revision, then immediately follow with:\n"
        "REQUIRED FIXES:\n"
        "- [specific issue 1]\n"
        "- [specific issue 2]\n"
        "(List only the critical fixes, not minor stylistic observations.)"
    )
    return f"{critique_instructions}{verdict_block}\n\n---\nSCENE DRAFT:\n{variant_text}"


def parse_critique_verdict(critique_text: str) -> tuple[bool, list[str]]:
    """Parse the structured VERDICT from a critique. Returns (passed, required_fixes)."""
    match = re.search(r"VERDICT:\s*(PASS|FAIL)", critique_text, re.IGNORECASE)
    if not match:
        return False, ["No VERDICT found in critique — review manually."]
    if match.group(1).upper() == "PASS":
        return True, []
    fixes_match = re.search(
        r"REQUIRED FIXES:(.*?)(?:VERDICT:|$)", critique_text, re.DOTALL | re.IGNORECASE
    )
    if fixes_match:
        fixes = [
            ln.strip().lstrip("-•* ").strip()
            for ln in fixes_match.group(1).splitlines()
            if ln.strip().lstrip("-•* ").strip()
        ]
    else:
        fixes = ["See critique for details."]
    return False, fixes or ["See critique for details."]


def build_judge_prompt(variant_texts: dict[str, str]) -> str:
    """Prompt asking the model to pick the best variant. Expects a single-letter response."""
    parts = [
        f"--- VARIANT {v.upper()} ({len(text.split()):,} words) ---\n{text}"
        for v, text in sorted(variant_texts.items())
    ]
    return (
        "You are a senior literary editor. Read the scene variants below and select the one "
        "that best achieves the scene's purpose: strongest narrative voice, most effective "
        "pacing, most compelling prose, and best tonal consistency with the surrounding story.\n\n"
        + "\n\n".join(parts)
        + "\n\nRespond with ONLY a single uppercase letter — A, B, or C — for the best variant. "
        "No explanation, no punctuation, no additional text. Just the letter."
    )


def build_revision_user_prompt(
    info: SceneInfo,
    variant_text: str,
    critique_text: str,
) -> str:
    revision_instructions = read_prompt(info, "REVISION_PROMPT")
    return (
        f"{revision_instructions}\n\n"
        f"---\nORIGINAL DRAFT:\n{variant_text}\n\n"
        f"---\nCRITIQUE:\n{critique_text}"
    )


def build_paragraph_regen_user_prompt(
    paragraph: str,
    before_context: str,
    after_context: str,
    user_instruction: str,
) -> str:
    return (
        f"Rewrite only the following passage according to the instruction below. "
        f"The rewrite must fit seamlessly with the surrounding text.\n\n"
        f"INSTRUCTION: {user_instruction}\n\n"
        f"PRECEDING CONTEXT:\n{before_context}\n\n"
        f"PASSAGE TO REWRITE:\n{paragraph}\n\n"
        f"FOLLOWING CONTEXT:\n{after_context}\n\n"
        f"Output only the rewritten passage — no preamble, no explanation."
    )


# ---------------------------------------------------------------------------
# Paragraph utilities
# ---------------------------------------------------------------------------

def split_paragraphs(text: str) -> list[str]:
    return [p for p in text.split(_PARA_SEP) if p.strip()]


def join_paragraphs(paragraphs: list[str]) -> str:
    return _PARA_SEP.join(paragraphs)


def replace_paragraph(text: str, index: int, replacement: str) -> str:
    paras = split_paragraphs(text)
    if index < 0 or index >= len(paras):
        raise IndexError(f"Paragraph index {index} out of range (0–{len(paras) - 1})")
    paras[index] = replacement.strip()
    return join_paragraphs(paras)


def get_paragraph_context(
    paragraphs: list[str],
    index: int,
    context_window: int = 2,
) -> tuple[str, str]:
    before = _PARA_SEP.join(paragraphs[max(0, index - context_window): index])
    after = _PARA_SEP.join(paragraphs[index + 1: index + 1 + context_window])
    return before, after


# ---------------------------------------------------------------------------
# Status derivation (bootstrapping from file system)
# ---------------------------------------------------------------------------

def status_from_files(
    output_path: str | Path,
    chapter: int,
    scene: int,
) -> str:
    if selected_path(output_path, chapter, scene).exists():
        return "selected"
    for v in ("a", "b", "c"):
        if revision_path(output_path, chapter, scene, v).exists():
            return "has_revision"
    for v in ("a", "b", "c"):
        if critique_path(output_path, chapter, scene, v).exists():
            return "has_critique"
    for v in ("a", "b", "c"):
        if variant_path(output_path, chapter, scene, v).exists():
            return "has_variants"
    return "needs_draft"


def active_variant_from_files(
    output_path: str | Path,
    chapter: int,
    scene: int,
) -> str | None:
    for v in ("a", "b", "c"):
        if revision_path(output_path, chapter, scene, v).exists():
            return v
        if critique_path(output_path, chapter, scene, v).exists():
            return v
    return None


# ---------------------------------------------------------------------------
# Chapter assembly
# ---------------------------------------------------------------------------

def assemble_chapter(
    output_path: str | Path,
    chapter: int,
    all_scenes: list[SceneInfo],
) -> str:
    chapter_scenes = scenes_for_chapter(all_scenes, chapter)
    if not chapter_scenes:
        raise ValueError(f"No scenes found for chapter {chapter}.")

    parts: list[str] = []
    for s in chapter_scenes:
        text = read_output(selected_path(output_path, chapter, s.scene))
        if text is None:
            raise ValueError(
                f"{s.scene_key} has no selected draft — cannot assemble chapter {chapter}."
            )
        parts.append(text.strip())

    assembled = "\n\n---\n\n".join(parts)
    write_output(chapter_path(output_path, chapter), assembled)
    return assembled


def chapter_is_assembleable(
    output_path: str | Path,
    chapter: int,
    all_scenes: list[SceneInfo],
) -> bool:
    return all(
        selected_path(output_path, chapter, s.scene).exists()
        for s in scenes_for_chapter(all_scenes, chapter)
    )
