#!/usr/bin/env python3
"""
Bootstrap the app at container startup: materialize secrets from environment
variables into well-known paths, then repair the app config if it was provided
inline. Replaces the hand-rolled base64/pipe logic previously in entrypoint.sh.
"""
import sys
from pathlib import Path

from invoice_parser.config_loader import (
    SERVICE_ACCOUNT_KEY_FILE,
    RCLONE_CONFIG_FILE,
    example_config_path,
    materialize_secrets,
)


def _repair_config() -> None:
    config_path = Path("/app/local/local_config.json")
    if not config_path.exists():
        return
    example_path = example_config_path()
    if not example_path.exists():
        print("Example config not found, skipping repair.")
        return

    import json

    def load_json(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def deep_merge(default, override):
        if isinstance(override, dict) and isinstance(default, dict):
            result = dict(default)
            for key, value in override.items():
                result[key] = deep_merge(result.get(key), value) if key in result else value
            return result
        return override

    default = load_json(example_path)
    user = load_json(config_path)
    merged = deep_merge(default, user)

    rclone = merged.setdefault("rclone", {})
    if rclone.get("archive_drive_folder") == "":
        rclone["archive_drive_folder"] = None

    path_keys = ["source_folder", "input_folder", "output_folder", "archive_folder", "log_file"]
    for key in path_keys:
        value = merged.get(key)
        if isinstance(value, str) and value.startswith("ui/"):
            merged[key] = value.replace("ui/", "", 1)

    for section in ("parsers", "document_types", "filename"):
        if section in default:
            merged[section] = default[section]

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)


def main() -> int:
    for message in materialize_secrets():
        print(message)

    config_path = Path("/app/local/local_config.json")
    if config_path.exists():
        print("Repairing config from env var...")
        _repair_config()
    return 0


if __name__ == "__main__":
    sys.exit(main())