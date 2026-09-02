import json
import re
import shutil
from pathlib import Path
from typing import Optional

from invoice_parser.config import AccountParserConfig, FieldConfig, FilenameConfig
from invoice_parser.logging import log_info
from invoice_parser.models import Document
from invoice_parser.parsers.account import normalize_account


def is_already_processed(name: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    return False


def missing_required_fields(
    document: Document, required: list[str], fields_config: dict[str, FieldConfig]
) -> list[str]:
    missing = []
    for field in required:
        value = getattr(document, field)
        field_config = fields_config.get(field)
        if field == "account" and field_config is not None:
            account_config = AccountParserConfig.model_validate(field_config.model_dump())
            value = normalize_account(value, account_config)
            if value == account_config.fallback:
                missing.append(field)
        elif not value:
            missing.append(field)
    return missing


def archive_original(
    pdf_path: Path,
    archive_dir: Path,
    dry_run: bool,
    logger,
) -> None:
    if dry_run:
        log_info(logger, "DRY_RUN_WOULD_ARCHIVE", {
            "from": pdf_path.name,
            "to": str(archive_dir / pdf_path.name),
        })
        return

    archive_dir.mkdir(exist_ok=True)
    archive_target = archive_dir / pdf_path.name
    if not archive_target.exists():
        shutil.copy2(pdf_path, archive_target)
        log_info(logger, "ARCHIVED", {"file": pdf_path.name, "archive": str(archive_dir)})


def write_metadata_file(target: Path, document: Document) -> None:
    meta_path = target.with_suffix(target.suffix + ".meta.json")
    meta = document.to_dict()
    accounts = meta.get("accounts")
    if isinstance(accounts, str):
        try:
            meta["accounts"] = json.loads(accounts)
        except (ValueError, TypeError):
            pass
    meta.pop("document_type", None)
    meta["document_type"] = document.document_type
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def rename_pdf(
    pdf_path: Path,
    target: Path,
    dry_run: bool,
    logger,
    event_name: str = "RENAMED",
) -> None:
    if dry_run:
        log_info(logger, "DRY_RUN_WOULD_RENAME", {
            "from": pdf_path.name,
            "to": target.name,
        })
        return

    pdf_path.rename(target)
    log_info(logger, event_name, {"from": pdf_path.name, "to": target.name})


def cleanup_source(pdf_path: Path, logger) -> None:
    try:
        pdf_path.unlink()
        log_info(logger, "CLEANED_UP", {"file": str(pdf_path)})
    except OSError as exc:
        log_info(logger, "CLEANUP_FAILED", {"file": str(pdf_path), "error": str(exc)})
