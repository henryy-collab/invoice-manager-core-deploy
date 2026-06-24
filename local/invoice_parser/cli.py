import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from invoice_parser.config import AppConfig, resolve_config_paths
from invoice_parser.logging import log_error, setup_logging
from invoice_parser.processor import process_pdfs


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and rename invoice PDFs.")
    parser.add_argument("test_file", nargs="?", help="Process a single PDF file instead of the source folder.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config file (default: local_config.json next to script).")
    return parser


def _resolve_config_path(args_config: Path | None) -> Path:
    if args_config:
        return args_config

    # When invoked as python parse_and_rename.py
    entry_dir = Path(__file__).resolve().parent.parent
    candidate = entry_dir / "local_config.json"
    if candidate.exists():
        return candidate

    # When invoked as python -m invoice_parser.cli
    package_root = Path(__file__).resolve().parent.parent
    candidate = package_root / "local_config.json"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        "Could not find local_config.json. Use --config to specify its location."
    )


def main():
    args = _build_arg_parser().parse_args()

    try:
        config_path = _resolve_config_path(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = AppConfig.model_validate(raw)
        config = resolve_config_paths(config, config_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON in {config_path}: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValidationError as exc:
        print(f"ERROR: Config validation failed:\n{exc}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        config.features.dry_run = True

    log_path = Path(config.log_file)

    logger = setup_logging(log_path)

    test_file = None
    if args.test_file:
        test_file = Path(args.test_file).resolve()
        if not test_file.exists():
            log_error(logger, "TEST_FILE_NOT_FOUND", {"path": str(test_file)})
            sys.exit(1)

    process_pdfs(config, logger, test_file)


if __name__ == "__main__":
    main()
