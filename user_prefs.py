from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

_PREFS_PATH = Path(__file__).parent / "user_prefs.json"


@dataclass
class UserPrefs:
    autopilot_enabled: bool = True
    autopilot_loop_limit: int = 3
    last_pipeline_scene: str = ""


def load_prefs(username: str) -> UserPrefs:
    if not _PREFS_PATH.exists():
        return UserPrefs()
    try:
        data = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        raw = data.get(username, {})
        known = {k: v for k, v in raw.items() if k in UserPrefs.__dataclass_fields__}
        return UserPrefs(**known)
    except (json.JSONDecodeError, TypeError):
        return UserPrefs()


def save_prefs(username: str, prefs: UserPrefs) -> None:
    all_prefs: dict = {}
    if _PREFS_PATH.exists():
        try:
            all_prefs = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            pass
    all_prefs[username] = asdict(prefs)
    _PREFS_PATH.write_text(json.dumps(all_prefs, indent=2), encoding="utf-8")
