import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from invoice_parser.config import AppConfig, resolve_config_paths
from invoice_parser.config_loader import load_config_source, resolve_config_path
from invoice_parser.nocodb import upload_from_config


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload parsed invoice metadata to a NocoDB 'Invoices' table.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without uploading.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config file.")
    return parser


def main():
    args = _build_arg_parser().parse_args()

    try:
        config_path = resolve_config_path(args.config)
        _, raw = load_config_source(config_path)
        config = AppConfig.model_validate(raw)
        config = resolve_config_paths(config, config_path)
    except ValidationError as exc:
        print(f"ERROR: Config validation failed:\n{exc}", file=sys.stderr)
        sys.exit(1)

    result = upload_from_config(config, dry_run=args.dry_run)

    if result.get("skipped"):
        print(result.get("message", "Nothing to upload."))
        return

    print(f"Uploaded: {result['uploaded']}")
    if result.get("url"):
        print(f"Target: {result['url']}/api/v3/data/{result['base_id']}/{result['table_id']}/records")

    if result["errors"]:
        print("Errors:", file=sys.stderr)
        for err in result["errors"]:
            print(f"  {err.get('file', '?')}: {err.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()