from pathlib import Path
from typing import Optional

from fastapi import Request

from invoice_parser.config import AppConfig
from invoice_parser.logging import setup_logging
from invoice_ui.config import UIConfig


def get_ui_config() -> UIConfig:
    return UIConfig.from_env()


def _resolve_config_path(request: Request) -> Path:
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


def get_config_path(request: Request) -> Path:
    return _resolve_config_path(request)


def get_app_config(request: Request) -> AppConfig:
    import json

    from pydantic import ValidationError

    config_path = get_config_path(request)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}")
    except ValidationError as exc:
        raise ValueError(f"Config validation failed: {exc}")


def get_logger(request: Request):
    config = get_app_config(request)
    config_path = get_config_path(request)
    log_path = Path(config.log_file)
    if not log_path.is_absolute():
        log_path = config_path.parent / log_path
    return setup_logging(log_path)


def get_config_dir(request: Request) -> Path:
    return get_config_path(request).parent
