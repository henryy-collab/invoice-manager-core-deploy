import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from invoice_parser.config import AccountParserConfig, AppConfig
from invoice_parser.extractor import extract_text
from invoice_parser.filename import build_filename, resolve_unique_name
from invoice_parser.files import (
    archive_original,
    is_already_processed,
    missing_required_fields,
    rename_pdf,
    write_metadata_file,
)

from invoice_parser.logging import log_error, log_info
from invoice_parser.models import Invoice
from invoice_parser.parsers.invoice import parse_invoice


@dataclass
class ParseResult:
    source_path: Path
    text: Optional[str]
    invoice: Invoice
    missing_required: list[str] = field(default_factory=list)
    target_name: Optional[str] = None
    number_fallback_used: bool = False

    @property
    def needs_manual_review(self) -> bool:
        return bool(self.missing_required)

    def to_dict(self) -> dict:
        return {
            "source_path": str(self.source_path),
            "fields": self.invoice.to_dict(),
            "missing_required": self.missing_required,
            "target_name": self.target_name,
            "number_fallback_used": self.number_fallback_used,
            "needs_manual_review": self.needs_manual_review,
        }


def _resolve_target_name(
    pdf_path: Path,
    output: Path,
    config: AppConfig,
    invoice: Invoice,
    missing: list[str],
    used_names: set[Path],
) -> str:
    if missing:
        target = resolve_unique_name(
            output,
            pdf_path.name,
            used_names,
            prefix=config.filename.manual_review_prefix,
            suffix_template=config.filename.collision_suffix,
            track=config.features.deduplicate_within_run,
        )
    else:
        new_name = build_filename(config.filename_template, invoice, config.filename)
        target = resolve_unique_name(
            output,
            new_name,
            used_names,
            suffix_template=config.filename.collision_suffix,
            track=config.features.deduplicate_within_run,
        )
    return target.name


def _write_run_state(output: Path, processed: list[str], manual_review: list[str], failed: list[str]) -> None:
    state_dir = output.parent / "state"
    state_dir.mkdir(exist_ok=True)
    state_path = state_dir / "last_run_processed.json"
    state = {
        "processed": processed,
        "manual_review": manual_review,
        "failed": failed,
    }
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def parse_single_pdf(
    pdf_path: Path,
    config: AppConfig,
    used_names: Optional[set[Path]] = None,
) -> ParseResult:
    output = Path(config.output_folder)
    text = extract_text(pdf_path)
    invoice = parse_invoice(text, pdf_path.stem, config)

    missing = missing_required_fields(
        invoice, config.features.manual_review_for_missing, config.parsers.account
    )

    number_fallback_used = False
    if not invoice.number and config.features.number_fallback_to_filename:
        invoice.number = pdf_path.stem
        number_fallback_used = True

    used = used_names if used_names is not None else set()
    target_name = _resolve_target_name(pdf_path, output, config, invoice, missing, used)

    return ParseResult(
        source_path=pdf_path,
        text=text,
        invoice=invoice,
        missing_required=missing,
        target_name=target_name,
        number_fallback_used=number_fallback_used,
    )


def process_pdfs(config: AppConfig, logger, test_file: Optional[Path] = None):
    input_dir = Path(config.input_folder)
    output = Path(config.output_folder)
    archive = Path(config.archive_folder) if Path(config.archive_folder).is_absolute() else output / config.archive_folder

    used_names: set[Path] = set()
    files = [test_file] if test_file else sorted(input_dir.glob("*.pdf"))

    processed: list[str] = []
    manual_review: list[str] = []
    failed: list[str] = []

    for pdf_path in files:
        if pdf_path is None:
            continue
        if not pdf_path.is_file():
            continue

        if config.features.skip_already_processed:
            if is_already_processed(pdf_path.name, config.filename.already_processed_patterns):
                log_info(logger, "SKIP_ALREADY_PROCESSED", {"file": pdf_path.name})
                continue

        try:
            log_info(logger, "PARSE_START", {"file": pdf_path.name})

            result = parse_single_pdf(pdf_path, config, used_names=used_names)
            log_info(logger, "PARSE_FIELDS", {"file": pdf_path.name, "fields": result.invoice.to_dict()})

            if result.number_fallback_used:
                log_info(logger, "NUMBER_FALLBACK", {"file": pdf_path.name, "number": result.invoice.number})

            target = output / result.target_name

            if result.needs_manual_review:
                rename_pdf(pdf_path, target, config.features.dry_run, logger, "MANUAL_REVIEW")
                if not config.features.dry_run:
                    write_metadata_file(target, result.invoice)
                log_error(
                    logger,
                    "MANUAL_REVIEW_RENAME",
                    {
                        "from": pdf_path.name,
                        "to": target.name,
                        "reason": f"Missing required fields: {result.missing_required}",
                    },
                )
                manual_review.append(pdf_path.name)
                continue

            if config.features.archive:
                archive_original(pdf_path, archive, config.features.dry_run, logger)

            rename_pdf(pdf_path, target, config.features.dry_run, logger)
            if not config.features.dry_run:
                write_metadata_file(target, result.invoice)

            processed.append(pdf_path.name)

        except Exception as exc:
            log_error(logger, "PROCESS_FAILED", {"file": pdf_path.name, "error": str(exc)})
            failed.append(pdf_path.name)

    if not config.features.dry_run:
        _write_run_state(output, processed, manual_review, failed)
