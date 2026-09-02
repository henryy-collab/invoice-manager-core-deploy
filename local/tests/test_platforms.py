from pathlib import Path

from invoice_parser.config import AppConfig


def _base_config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "source_folder": str(tmp_path / "data"),
            "default_document_type": "google_ads",
            "rclone": {
                "enabled": True,
                "remote": "mydrive-service",
                "source_drive_folder": "003 Finance Operations/001 Invoices/001 Google Ads/000 Input Folder",
                "destination_drive_folder": "003 Finance Operations/001 Invoices/001 Google Ads",
                "destination_subfolder_template": "{year}{month}",
                "archive_drive_folder": None,
            },
            "google_sheets": {
                "enabled": True,
                "spreadsheet_url": "https://docs.google.com/spreadsheets/d/GOOGLE/edit",
                "service_account_file": "keys/sa.json",
                "tab_name_template": "%b %Y",
            },
        }
    )


def test_platform_types_includes_default_when_no_platforms(tmp_path):
    config = _base_config(tmp_path)
    assert config.platform_types() == ["google_ads"]


def test_platform_types_includes_configured_and_default(tmp_path):
    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(
        _platform_config_doc()
    ).platforms
    types = config.platform_types()
    assert types == ["google_ads", "facebook"]


def _platform_config_doc() -> dict:
    return {
        "source_folder": "/tmp/data",
        "platforms": {
            "facebook": {
                "rclone": {
                    "source_drive_folder": "003 Finance Operations/001 Invoices/002 Meta Ads/000 Input Folder",
                    "destination_drive_folder": "003 Finance Operations/001 Invoices/002 Meta Ads",
                    "destination_subfolder_template": "{year}{month}",
                    "archive_drive_folder": None,
                },
                "google_sheets": {
                    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/META/edit",
                },
            }
        },
    }


def test_facebook_rclone_overrides_only_set_fields(tmp_path):
    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(_platform_config_doc()).platforms
    fb = config.rclone_for("facebook")
    assert fb.source_drive_folder.endswith("002 Meta Ads/000 Input Folder")
    assert fb.destination_drive_folder.endswith("002 Meta Ads")
    assert fb.destination_subfolder_template == "{year}{month}"
    assert fb.remote == "mydrive-service"
    assert fb.enabled is True


def test_google_ads_rclone_uses_base(tmp_path):
    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(_platform_config_doc()).platforms
    ga = config.rclone_for("google_ads")
    assert ga.source_drive_folder.endswith("001 Google Ads/000 Input Folder")
    assert ga.destination_drive_folder.endswith("001 Google Ads")


def test_facebook_sheets_inherits_base_settings(tmp_path):
    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(_platform_config_doc()).platforms
    fb = config.google_sheets_for("facebook")
    assert fb.spreadsheet_url == "https://docs.google.com/spreadsheets/d/META/edit"
    assert fb.enabled is True
    assert fb.service_account_file == "keys/sa.json"
    assert fb.tab_name_template == "%b %Y"


def test_facebook_sheets_inherits_base_after_round_trip(tmp_path):
    from invoice_parser.config import resolve_config_paths

    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(_platform_config_doc()).platforms
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir(parents=True)
    resolved = resolve_config_paths(config, config_path)
    fb = resolved.google_sheets_for("facebook")
    assert fb.spreadsheet_url == "https://docs.google.com/spreadsheets/d/META/edit"
    assert fb.enabled is True
    assert fb.service_account_file == str((tmp_path / "keys" / "sa.json").resolve())


def test_google_ads_sheets_uses_base_url(tmp_path):
    config = _base_config(tmp_path)
    config.platforms = AppConfig.model_validate(_platform_config_doc()).platforms
    ga = config.google_sheets_for("google_ads")
    assert ga.spreadsheet_url == "https://docs.google.com/spreadsheets/d/GOOGLE/edit"
    assert ga.enabled is True