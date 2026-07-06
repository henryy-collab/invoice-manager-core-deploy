import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from invoice_parser.classifier import classify_document
from invoice_parser.config import AppConfig, DocumentTypeConfig
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
from invoice_parser.models import DEFAULT_DOCUMENT_TYPE, Document, Invoice
from invoice_parser.parsers.invoice import parse_document


@dataclass
class ParseResult:
    source_path: Path
    text: Optional[str]
    document: Document
    missing_required: list[str] = field(default_factory=list)
    target_name: Optional[str] = None
    number_fallback_used: bool = False
    document_type: str = DEFAULT_DOCUMENT_TYPE

    @property
    def invoice(self) -> Document:
        return self.document

    @property
    def needs_manual_review(self) -> bool:
        return bool(self.missing_required)

    def to_dict(self) -> dict:
        return {
            "source_path": str(self.source_path),
            "fields": self.document.to_dict(),
            "missing_required": self.missing_required,
            "target_name": self.target_name,
            "number_fallback_used": self.number_fallback_used,
            "needs_manual_review": self.needs_manual_review,
            "document_type": self.document_type,
        }


def _resolve_target_name(
    pdf_path: Path,
    output: Path,
    config: AppConfig,
    type_config: DocumentTypeConfig,
    document: Document,
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
        new_name = build_filename(type_config.filename_template, document, type_config)
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
    document_type = classify_document(text, config.document_types, config.default_document_type)
    type_config = config.document_types[document_type]
    document = parse_document(text, pdf_path.stem, config, type_config=type_config, document_type=document_type)

    missing = missing_required_fields(
        document, type_config.manual_review_for_missing, type_config.fields
    )

    number_fallback_used = False
    number_config = type_config.fields.get("number")
    if (
        number_config is not None
        and number_config.parser == "number"
        and not document.number
        and config.features.number_fallback_to_filename
    ):
        document.number = pdf_path.stem
        number_fallback_used = True

    used = used_names if used_names is not None else set()
    target_name = _resolve_target_name(pdf_path, output, config, type_config, document, missing, used)

    return ParseResult(
        source_path=pdf_path,
        text=text,
        document=document,
        missing_required=missing,
        target_name=target_name,
        number_fallback_used=number_fallback_used,
        document_type=document_type,
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
            log_info(logger, "PARSE_FIELDS", {"file": pdf_path.name, "fields": result.document.to_dict()})

            if result.number_fallback_used:
                log_info(logger, "NUMBER_FALLBACK", {"file": pdf_path.name, "number": result.document.number})

            target = output / result.target_name

            if result.needs_manual_review:
                rename_pdf(pdf_path, target, config.features.dry_run, logger, "MANUAL_REVIEW")
                if not config.features.dry_run:
                    write_metadata_file(target, result.document)
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
                write_metadata_file(target, result.document)

            processed.append(pdf_path.name)

        except Exception as exc:
            log_error(logger, "PROCESS_FAILED", {"file": pdf_path.name, "error": str(exc)})
            failed.append(pdf_path.name)

    if not config.features.dry_run:
        _write_run_state(output, processed, manual_review, failed)
