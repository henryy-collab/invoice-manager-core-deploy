#!/usr/bin/env python3
"""
Repair a local_config.json that may have been corrupted by encoding issues or UI edits.

Preserves environment-specific settings (rclone, google_sheets, features, timezone,
paths, etc.) and restores known-good parser / document-type patterns from the example
config shipped in the repo.
"""
import json
import sys
from pathlib import Path

CONFIG_PATH = Path("/app/local/local_config.json")
EXAMPLE_PATH = Path("/app/local/local_config.example.json")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def deep_merge(default, override):
    """Recursively merge override into default. Lists are replaced."""
    if isinstance(override, dict) and isinstance(default, dict):
        result = dict(default)
        for key, value in override.items():
            result[key] = deep_merge(result.get(key), value) if key in result else value
        return result
    return override


def repair_config():
    if not EXAMPLE_PATH.exists():
        print("Example config not found, skipping repair.")
        return 0

    default = load_json(EXAMPLE_PATH)

    if not CONFIG_PATH.exists():
        print("Config file not found, copying example.")
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return 0

    user = load_json(CONFIG_PATH)

    # Preserve environment-specific settings, use example defaults for missing keys.
    merged = deep_merge(default, user)

    # Fix archive_drive_folder empty string -> null (disabled)
    rclone = merged.setdefault("rclone", {})
    if rclone.get("archive_drive_folder") == "":
        rclone["archive_drive_folder"] = None

    # Fix paths that may have been accidentally prefixed with ui/ during local edits.
    path_keys = [
        "source_folder",
        "input_folder",
        "output_folder",
        "archive_folder",
        "log_file",
    ]
    for key in path_keys:
        value = merged.get(key)
        if isinstance(value, str) and value.startswith("ui/"):
            merged[key] = value.replace("ui/", "", 1)

    # Replace parser and document-type patterns with known-good defaults. These are
    # app internals, not environment-specific, so they should always be correct.
    if "parsers" in default:
        merged["parsers"] = default["parsers"]
    if "document_types" in default:
        merged["document_types"] = default["document_types"]
    if "filename" in default:
        merged["filename"] = default["filename"]

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print("Config repaired successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(repair_config())
