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


def _multi_platform_config(tmp_path: Path) -> AppConfig:
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir(parents=True)
    config = AppConfig.model_validate(
        {
            "source_folder": str(tmp_path / "data"),
            "input_folder": str(tmp_path / "data" / "incoming"),
            "output_folder": str(tmp_path / "data" / "outgoing"),
            "archive_folder": str(tmp_path / "data" / "archive"),
            "log_file": str(tmp_path / "data" / "logs" / "app.log"),
            "default_document_type": "google_ads",
            "rclone": {
                "enabled": True,
                "remote": "test-remote",
                "source_drive_folder": "GOOGLE/Source",
                "destination_drive_folder": "GOOGLE/Dest",
                "destination_subfolder_template": "{year}{month}",
                "archive_drive_folder": None,
            },
            "platforms": {
                "facebook": {
                    "rclone": {
                        "source_drive_folder": "META/Source",
                        "destination_drive_folder": "META/Dest",
                        "destination_subfolder_template": "{year}{month}",
                        "archive_drive_folder": None,
                    }
                }
            },
        }
    )
    return resolve_config_paths(config, config_path)


def test_pull_incoming_copies_from_each_platform(tmp_path, monkeypatch):
    config = _multi_platform_config(tmp_path)
    service = SyncService(config)
    calls: list[list[str]] = []

    def fake_run(args):
        calls.append(list(args))
        return {"success": True, "stderr": "", "error": None}

    monkeypatch.setattr(service, "_run_rclone", fake_run)
    result = service.pull_incoming()

    assert result["success"] is True
    copy_calls = [c for c in calls if c[0] == "copy"]
    assert len(copy_calls) == 2
    remotes = {c[1] for c in copy_calls}
    assert remotes == {"test-remote:GOOGLE/Source", "test-remote:META/Source"}
    assert set(result["platforms"]) == {"google_ads", "facebook"}


def test_push_outgoing_routes_by_document_type(tmp_path, monkeypatch):
    config = _multi_platform_config(tmp_path)
    service = SyncService(config)
    outgoing = Path(config.output_folder)
    outgoing.mkdir(parents=True)

    ga_meta = {
        "account": "GA", "number": "1", "date": "20260430",
        "currency": "HKD", "total": "1.00", "document_type": "google_ads",
    }
    fb_meta = {
        "account": "FB", "number": "2", "date": "20260901",
        "currency": "HKD", "total": "2.00", "document_type": "facebook",
    }
    (outgoing / "ga.pdf").write_bytes(b"x")
    (outgoing / "ga.pdf.meta.json").write_text(json.dumps(ga_meta), encoding="utf-8")
    (outgoing / "fb.pdf").write_bytes(b"x")
    (outgoing / "fb.pdf.meta.json").write_text(json.dumps(fb_meta), encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(args):
        calls.append(list(args))
        return {"success": True, "stderr": "", "error": None}

    monkeypatch.setattr(service, "_run_rclone", fake_run)
    result = service.push_outgoing()

    assert result["success"] is True
    assert result["pushed"] == 2
    copy_calls = [c for c in calls if c[0] == "copy"]
    destinations = {c[-1] for c in copy_calls}
    assert "test-remote:GOOGLE/Dest/202604" in destinations
    assert "test-remote:META/Dest/202609" in destinations


def test_clear_remote_input_deletes_from_each_platform(tmp_path, monkeypatch):
    config = _multi_platform_config(tmp_path)
    service = SyncService(config)
    state_dir = Path(config.output_folder).parent / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "last_run_processed.json").write_text(
        json.dumps({"processed": ["ga.pdf", "fb.pdf"], "manual_review": [], "failed": []}),
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def fake_run(args):
        calls.append(list(args))
        return {"success": True, "stderr": "", "error": None}

    monkeypatch.setattr(service, "_run_rclone", fake_run)
    result = service.clear_remote_input()

    assert result["success"] is True
    assert result["deleted"] == 2
    delete_calls = [c for c in calls if c[0] == "delete"]
    assert len(delete_calls) == 2
    remotes = {c[-1] for c in delete_calls}
    assert remotes == {"test-remote:GOOGLE/Source", "test-remote:META/Source"}
    assert (state_dir / "last_run_processed.json").exists() is False
