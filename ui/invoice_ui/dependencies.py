from pathlib import Path
from typing import Optional

from fastapi import Request

from invoice_parser.config import AppConfig, resolve_config_paths
from invoice_parser.logging import setup_logging
from invoice_ui.config import UIConfig


def get_ui_config() -> UIConfig:
    return UIConfig.from_env()


def resolve_default_config_path() -> Path:
    import os

    ui_config = get_ui_config()
    if env_path := os.getenv(ui_config.config_path_env):
        candidate = Path(env_path).resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Config path from {ui_config.config_path_env} not found: {candidate}")

    # Repo root is two levels above ui/invoice_ui/
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidate = repo_root / "local" / "local_config.json"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        "Could not find local/local_config.json. Use INVOICE_UI_CONFIG_PATH to specify its location."
    )


def _resolve_config_path(request: Request) -> Path:
    return resolve_default_config_path()


def get_config_path(request: Request) -> Path:
    return _resolve_config_path(request)


def load_app_config_from_path(config_path: Path) -> AppConfig:
    import json

    from pydantic import ValidationError

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = AppConfig.model_validate(raw)
        return resolve_config_paths(config, config_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}")
    except ValidationError as exc:
        raise ValueError(f"Config validation failed: {exc}")


def get_app_config(request: Request) -> AppConfig:
    return load_app_config_from_path(get_config_path(request))


def get_logger(request: Request):
    config = get_app_config(request)
    log_path = Path(config.log_file)
    return setup_logging(log_path)


def get_config_dir(request: Request) -> Path:
    return get_config_path(request).parent
