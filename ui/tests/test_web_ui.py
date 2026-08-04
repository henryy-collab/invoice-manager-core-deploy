import json
from pathlib import Path

from web_ui import ensure_app_directories


def test_ensure_app_directories_creates_missing_directories(tmp_path):
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "source_folder": "data",
                "input_folder": "data/incoming",
                "output_folder": "data/outgoing",
                "archive_folder": "data/archive",
                "log_file": "data/logs/app.log",
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / ".git").mkdir()

    ensure_app_directories(config_path)

    assert (tmp_path / "data" / "incoming").exists()
    assert (tmp_path / "data" / "outgoing").exists()
    assert (tmp_path / "data" / "archive").exists()
    assert (tmp_path / "data" / "logs").exists()


def test_ensure_app_directories_skips_missing_config(tmp_path):
    missing_path = tmp_path / "local" / "local_config.json"
    ensure_app_directories(missing_path)
