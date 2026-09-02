import json
import sys
from pathlib import Path

import pytest

from invoice_parser.cli import _build_arg_parser, _resolve_config_path, main


def test_arg_parser_dry_run():
    args = _build_arg_parser().parse_args(["--dry-run"])
    assert args.dry_run is True
    assert args.test_file is None


def test_arg_parser_single_file():
    args = _build_arg_parser().parse_args(["some.pdf"])
    assert args.test_file == "some.pdf"


def test_resolve_config_path_from_args(tmp_path):
    config = tmp_path / "custom.json"
    config.write_text("{}")
    assert _resolve_config_path(config) == config


def test_resolve_config_path_no_config_falls_back(tmp_path, monkeypatch):
    # Ensure no real local_config.json is found by monkeypatching cli.__file__ to a temp dir
    import invoice_parser.cli as cli_module
    from invoice_parser import config_loader

    monkeypatch.setattr(
        cli_module, "__file__", str(tmp_path / "invoice_parser" / "cli.py")
    )
    monkeypatch.setattr(
        config_loader, "__file__", str(tmp_path / "invoice_parser" / "config_loader.py")
    )
    path = _resolve_config_path(None)
    assert path.name == "local_config.example.json"


def test_main_exits_on_missing_test_file(tmp_path, monkeypatch):
    config = tmp_path / "local_config.json"
    config.write_text(json.dumps({
        "source_folder": str(tmp_path),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
        "log_file": str(tmp_path / "test.log"),
    }))

    missing = tmp_path / "missing.pdf"

    monkeypatch.setattr(sys, "argv", ["parse_and_rename.py", str(missing), "--config", str(config)])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_dry_run_uses_config_flag(tmp_path, monkeypatch, capsys):
    config = tmp_path / "local_config.json"
    config.write_text(json.dumps({
        "source_folder": str(tmp_path),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
        "log_file": str(tmp_path / "test.log"),
    }))

    monkeypatch.setattr(
        "invoice_parser.cli.process_pdfs", lambda _config, _logger, _test=None: None
    )

    monkeypatch.setattr(sys, "argv", ["parse_and_rename.py", "--dry-run", "--config", str(config)])
    main()

    # No exception means config loaded and dry-run applied.
