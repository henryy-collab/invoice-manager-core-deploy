import json
from pathlib import Path

from invoice_parser.config_loader import (
    APP_CONFIG_ENV,
    SERVICE_ACCOUNT_ENV,
    RCLONE_ENV,
    materialize_secrets,
    resolve_config_path,
    load_config_source,
)


def test_resolve_prefers_explicit_file(tmp_path):
    explicit = tmp_path / "custom.json"
    explicit.write_text("{}")
    assert resolve_config_path(explicit) == explicit


def test_resolve_prefers_env_path_over_default(tmp_path, monkeypatch):
    env_file = tmp_path / "env_config.json"
    env_file.write_text("{}")
    monkeypatch.setenv("INVOICE_UI_CONFIG_PATH", str(env_file))
    assert resolve_config_path(None) == env_file


def test_resolve_inline_env_uses_default_path(tmp_path, monkeypatch):
    default = tmp_path / "local" / "local_config.json"
    default.parent.mkdir(parents=True)
    default.write_text("{}")
    monkeypatch.setenv(APP_CONFIG_ENV, json.dumps({"source_folder": "data"}))
    monkeypatch.setattr(
        "invoice_parser.config_loader._repo_root", lambda: tmp_path
    )
    assert resolve_config_path(None) == default


def test_resolve_falls_back_to_example(tmp_path, monkeypatch):
    example = tmp_path / "local" / "local_config.example.json"
    example.parent.mkdir(parents=True)
    example.write_text("{}")
    monkeypatch.setattr(
        "invoice_parser.config_loader._repo_root", lambda: tmp_path
    )
    assert resolve_config_path(None) == example


def test_load_inline_env_config(tmp_path, monkeypatch):
    default = tmp_path / "local" / "local_config.json"
    default.parent.mkdir(parents=True)
    monkeypatch.setattr(
        "invoice_parser.config_loader._repo_root", lambda: tmp_path
    )
    monkeypatch.setenv(APP_CONFIG_ENV, json.dumps({"source_folder": "data"}))
    path, raw = load_config_source(None)
    assert path == default
    assert raw == {"source_folder": "data"}


def test_materialize_secrets_no_env(monkeypatch):
    for key in (SERVICE_ACCOUNT_ENV, f"{SERVICE_ACCOUNT_ENV}_B64", RCLONE_ENV, f"{RCLONE_ENV}_B64"):
        monkeypatch.delenv(key, raising=False)
    messages = materialize_secrets()
    assert any("No service-account" in m for m in messages)
    assert any("No rclone" in m for m in messages)


def test_materialize_secrets_base64(tmp_path, monkeypatch):
    import base64
    monkeypatch.setattr("invoice_parser.config_loader.SERVICE_ACCOUNT_KEY_FILE", str(tmp_path / "key.json"))
    monkeypatch.setattr("invoice_parser.config_loader.RCLONE_CONFIG_FILE", str(tmp_path / "rclone.conf"))
    monkeypatch.setenv(f"{SERVICE_ACCOUNT_ENV}_B64", base64.b64encode(b'{"client_email":"a@b"}').decode())
    monkeypatch.setenv(f"{RCLONE_ENV}_B64", base64.b64encode(b"[mydrive]\ntype=drive").decode())
    materialize_secrets()
    key = (tmp_path / "key.json").read_text(encoding="utf-8")
    conf = (tmp_path / "rclone.conf").read_text(encoding="utf-8")
    assert key == '{"client_email":"a@b"}'
    assert conf == "[mydrive]\ntype=drive"


def test_materialize_secrets_pipe_rclone(tmp_path, monkeypatch):
    monkeypatch.setattr("invoice_parser.config_loader.SERVICE_ACCOUNT_KEY_FILE", str(tmp_path / "key.json"))
    monkeypatch.setattr("invoice_parser.config_loader.RCLONE_CONFIG_FILE", str(tmp_path / "rclone.conf"))
    monkeypatch.setenv(SERVICE_ACCOUNT_ENV, '{"client_email":"a@b"}')
    monkeypatch.setenv(RCLONE_ENV, "[mydrive]|type=drive")
    materialize_secrets()
    conf = (tmp_path / "rclone.conf").read_text(encoding="utf-8")
    assert conf == "[mydrive]\ntype=drive"