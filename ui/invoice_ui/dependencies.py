from pathlib import Path
from typing import Optional
import json

from fastapi import Request

from invoice_parser.config import AppConfig, resolve_config_paths
from invoice_parser.config_loader import load_config_source, resolve_config_path
from invoice_parser.logging import setup_logging
from invoice_ui.config import UIConfig


def get_ui_config() -> UIConfig:
    return UIConfig.from_env()


def resolve_default_config_path() -> Path:
    return resolve_config_path()


def _resolve_config_path(request: Request) -> Path:
    return resolve_default_config_path()


def get_config_path(request: Request) -> Path:
    return _resolve_config_path(request)


def load_app_config_from_path(config_path: Path) -> AppConfig:
    from invoice_parser.config_loader import load_config_source
    from pydantic import ValidationError

    try:
        _, raw = load_config_source(config_path)
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
