from pathlib import Path

import pytest
from pydantic import ValidationError

from invoice_parser.config import AppConfig, make_config_paths_relative, resolve_config_paths


def test_config_loads_with_defaults(minimal_config_dict):
    config = AppConfig.model_validate(minimal_config_dict)
    assert config.source_folder == str(minimal_config_dict["source_folder"])
    assert config.input_folder == config.source_folder
    assert config.output_folder == config.source_folder
    assert config.filename_template == "{account}_{number}_Invoice_{date}.pdf"
    assert config.date_format == "%Y%m%d"
    assert config.archive_folder == "archive"
    assert config.features.archive is True
    assert config.features.dry_run is False
    assert config.features.deduplicate_within_run is True


def test_config_staging_folders_resolve_when_provided():
    config = AppConfig.model_validate({
        "source_folder": "/data/source",
        "input_folder": "/data/inbox",
        "output_folder": "/data/outbox",
    })
    assert config.input_folder == "/data/inbox"
    assert config.output_folder == "/data/outbox"


def test_config_default_placeholders(minimal_config_dict):
    config = AppConfig.model_validate(minimal_config_dict)
    assert "account" in config.filename.placeholders
    assert config.filename.placeholders["account"].sanitize is True
    assert config.filename.placeholders["account"].fallback == "UNKNOWN"


def test_config_account_id_defaults(minimal_config_dict):
    config = AppConfig.model_validate(minimal_config_dict)
    assert config.parsers.account_id is not None
    assert len(config.parsers.account_id.patterns) == 2
    assert config.filename.placeholders["account_id"].sanitize is True
    type_config = config.document_types[config.default_document_type]
    assert "account_id" in type_config.fields
    assert "account_id" in type_config.placeholders


def test_config_accounts_defaults(minimal_config_dict):
    config = AppConfig.model_validate(minimal_config_dict)
    assert config.parsers.accounts is not None
    assert "Summary" in config.parsers.accounts.summary_marker_regex
    type_config = config.document_types[config.default_document_type]
    assert "accounts" in type_config.fields


def test_config_accepts_custom_features(minimal_config_dict):
    minimal_config_dict["features"] = {
        "archive": False,
        "manual_review_for_missing": ["account", "date", "number"],
    }
    config = AppConfig.model_validate(minimal_config_dict)
    assert config.features.archive is False
    assert config.features.manual_review_for_missing == ["account", "date", "number"]


def test_config_rejects_invalid_regex(minimal_config_dict):
    minimal_config_dict["parsers"] = {
        "account": {
            "patterns": [{"regex": "[invalid", "group": 1}]
        }
    }
    with pytest.raises(ValidationError):
        AppConfig.model_validate(minimal_config_dict)


def test_config_invalid_regex_includes_error_detail(minimal_config_dict):
    minimal_config_dict["parsers"] = {
        "account": {
            "patterns": [{"regex": "[invalid", "group": 1}]
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        AppConfig.model_validate(minimal_config_dict)
    assert "Invalid regex" in str(exc_info.value)


def test_config_rejects_missing_source_folder():
    with pytest.raises(ValidationError):
        AppConfig.model_validate({})


def test_resolve_config_paths_resolves_service_account_file(tmp_path):
    (tmp_path / ".git").mkdir()
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir()
    data = {
        "source_folder": "local/data",
        "google_sheets": {
            "enabled": True,
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/x/edit",
            "service_account_file": "keys/account.json",
        },
    }
    config = AppConfig.model_validate(data)
    resolved = resolve_config_paths(config, config_path)
    expected = str((tmp_path / "keys" / "account.json").resolve())
    assert resolved.google_sheets.service_account_file == expected


def test_make_config_paths_relative_round_trip(tmp_path):
    (tmp_path / ".git").mkdir()
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir()
    data = {
        "source_folder": str(tmp_path / "local" / "data"),
        "log_file": str(tmp_path / "local" / "data" / "logs" / "app.log"),
        "google_sheets": {
            "enabled": True,
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/x/edit",
            "service_account_file": str(tmp_path / "keys" / "account.json"),
        },
    }
    config = AppConfig.model_validate(data)
    relative = make_config_paths_relative(config, config_path)
    assert relative.source_folder == "local/data"
    assert relative.log_file == "local/data/logs/app.log"
    assert relative.google_sheets.service_account_file == "keys/account.json"
