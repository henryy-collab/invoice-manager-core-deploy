import json
from pathlib import Path

import pytest

from invoice_ui.services.sync_service import SyncService
from invoice_parser.config import AppConfig, resolve_config_paths


def _config(tmp_path: Path, archive_drive_folder: str | None) -> AppConfig:
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir(parents=True)
    config = AppConfig.model_validate(
        {
            "source_folder": str(tmp_path / "data"),
            "input_folder": str(tmp_path / "data" / "incoming"),
            "output_folder": str(tmp_path / "data" / "outgoing"),
            "archive_folder": str(tmp_path / "data" / "archive"),
            "log_file": str(tmp_path / "data" / "logs" / "app.log"),
            "rclone": {
                "enabled": True,
                "remote": "test-remote",
                "source_drive_folder": "Source",
                "destination_drive_folder": "Dest",
                "archive_drive_folder": archive_drive_folder,
            },
        }
    )
    return resolve_config_paths(config, config_path)


def test_push_archive_disabled_when_none(tmp_path):
    config = _config(tmp_path, None)
    service = SyncService(config)
    result = service.push_archive()
    assert result["success"] is True
    assert "disabled" in result["message"].lower()


def test_push_archive_disabled_when_empty(tmp_path):
    config = _config(tmp_path, "")
    service = SyncService(config)
    result = service.push_archive()
    assert result["success"] is True
    assert "disabled" in result["message"].lower()


def test_rclone_error_summary_for_missing_directory():
    config = AppConfig.model_validate(
        {
            "source_folder": "/tmp/data",
            "rclone": {"enabled": True, "remote": "test-remote", "source_drive_folder": "Missing"},
        }
    )
    service = SyncService(config)
    summary = service._summarize_rclone_error(
        "2026/01/01 12:00:00 ERROR : : error listing: directory not found\n"
    )
    assert "folder not found" in summary.lower()


def test_rclone_error_summary_for_permission_denied():
    config = AppConfig.model_validate(
        {
            "source_folder": "/tmp/data",
            "rclone": {"enabled": True, "remote": "test-remote", "source_drive_folder": "X"},
        }
    )
    service = SyncService(config)
    summary = service._summarize_rclone_error("Permission denied")
    assert "permission denied" in summary.lower()
