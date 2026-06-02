from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

_CONFIG_PATH = Path(__file__).parent / "config.json"


@dataclass
class Config:
    prompts_path: str = ""
    output_path: str = ""
    ollama_url: str = "http://localhost:11434"
    model_name: str = ""
    num_ctx: int = 8192
    autopilot_loop_limit: int = 3


def load_config() -> Config:
    if not _CONFIG_PATH.exists():
        return Config()
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
        return Config(**known)
    except (json.JSONDecodeError, TypeError):
        return Config()


def save_config(cfg: Config) -> None:
    _CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")


def validate_config(cfg: Config) -> list[str]:
    errors: list[str] = []
    if not cfg.prompts_path:
        errors.append("Prompts path is required.")
    elif not Path(cfg.prompts_path).is_dir():
        errors.append(f"Prompts path does not exist: {cfg.prompts_path}")
    if not cfg.output_path:
        errors.append("Output path is required.")
    if not cfg.model_name:
        errors.append("Model name is required.")
    if not cfg.ollama_url:
        errors.append("Ollama URL is required.")
    return errors
