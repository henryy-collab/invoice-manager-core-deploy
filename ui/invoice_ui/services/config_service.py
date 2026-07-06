import json
from pathlib import Path

from fastapi import Request
from pydantic import ValidationError

from invoice_parser.config import AppConfig, make_config_paths_relative
from invoice_ui.dependencies import get_config_path


class ConfigService:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    @classmethod
    def from_request(cls, request: Request) -> "ConfigService":
        return cls(get_config_path(request))

    def load(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> AppConfig:
        config = AppConfig.model_validate(data)
        config = make_config_paths_relative(config, self.config_path)
        self.config_path.write_text(
            json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return config

    def validate(self, data: dict) -> AppConfig:
        return AppConfig.model_validate(data)

    def get_validation_error(self, data: dict) -> str | None:
        try:
            AppConfig.model_validate(data)
            return None
        except ValidationError as exc:
            return str(exc)
