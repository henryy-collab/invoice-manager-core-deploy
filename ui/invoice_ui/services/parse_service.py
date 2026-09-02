import json
from pathlib import Path

from fastapi import Request

from invoice_parser.config import AppConfig, DocumentTypeConfig
from invoice_parser.files import (
    archive_original,
    is_already_processed,
    missing_required_fields,
    rename_pdf,
    write_metadata_file,
)
from invoice_parser.filename import build_filename, resolve_unique_name
from invoice_parser.logging import log_info
from invoice_parser.models import DEFAULT_DOCUMENT_TYPE, Document, Invoice
from invoice_parser.processor import (
    _resolve_target_name,
    _write_run_state,
    parse_single_pdf,
    process_pdfs,
)
from invoice_ui.dependencies import get_app_config, get_config_path, get_logger
from invoice_ui.models.schemas import (
    ParsePreviewRequest,
    ParseResponse,
    ParseResultItem,
    RunResponse,
)


_last_results: list[ParseResultItem] = []
_last_results_renamed: bool = False


class ParseService:
    def __init__(self, config: AppConfig, config_path: Path, logger):
        self.config = config
        self.config_path = config_path
        self.logger = logger

    @classmethod
    def from_request(cls, request: Request) -> "ParseService":
        return cls(
            get_app_config(request),
            get_config_path(request),
            get_logger(request),
        )

    def _default_type_config(self) -> DocumentTypeConfig:
        return self.config.document_types[self.config.default_document_type]

    def preview(self) -> ParseResponse:
        global _last_results_renamed
        input_dir = Path(self.config.input_folder)
        if not input_dir.exists():
            _last_results_renamed = False
            return self._empty_response()

        used_names: set[Path] = set()
        results: list[ParseResultItem] = []
        processed = 0
        manual_review = 0
        skipped = 0
        failed = 0

        for pdf_path in sorted(input_dir.glob("*.pdf")):
            if self.config.features.skip_already_processed:
                if is_already_processed(pdf_path.name, self.config.filename.already_processed_patterns):
                    skipped += 1
                    continue

            try:
                result = parse_single_pdf(pdf_path, self.config, used_names=used_names)
                results.append(self._to_result_item(pdf_path.name, result))
                if result.needs_manual_review:
                    manual_review += 1
                else:
                    processed += 1
            except Exception:
                failed += 1
                results.append(ParseResultItem(
                    source_name=pdf_path.name,
                    source_path=str(pdf_path),
                    fields={"account": None, "account_id": None, "number": None, "date": None, "total": None, "currency": None},
                    missing_required=[],
                    target_name=pdf_path.name,
                    needs_manual_review=True,
                    number_fallback_used=False,
                    document_type=self.config.default_document_type,
                ))

        return self._store_and_respond(results, processed, manual_review, skipped, failed)

    def can_write_report(self) -> bool:
        return bool(_last_results and _last_results_renamed)

    def update_result(self, source_name: str, fields: dict[str, str | None]) -> ParseResponse:
        global _last_results_renamed
        if not _last_results:
            return self._empty_response()

        results_by_name = {r.source_name: r for r in _last_results}
        if source_name not in results_by_name:
            raise ValueError(f"Unknown source file: {source_name}")

        updated = results_by_name[source_name]
        merged_fields = {**updated.fields, **fields}
        for key in merged_fields:
            if merged_fields[key] is not None:
                merged_fields[key] = str(merged_fields[key]).strip() or None
            if merged_fields[key] == "":
                merged_fields[key] = None

        type_config = self.config.document_types.get(
            updated.document_type, self._default_type_config()
        )
        document = Document(**merged_fields)
        missing = missing_required_fields(
            document, type_config.manual_review_for_missing, type_config.fields
        )

        output = Path(self.config.output_folder)
        used_names: set[Path] = set()
        target_name = _resolve_target_name(
            Path(self.config.input_folder) / source_name,
            output,
            self.config,
            type_config,
            document,
            missing,
            used_names,
        )

        updated_item = ParseResultItem(
            source_name=source_name,
            source_path=updated.source_path,
            fields=document.to_dict(),
            missing_required=missing,
            target_name=target_name,
            needs_manual_review=bool(missing),
            number_fallback_used=updated.number_fallback_used,
            document_type=updated.document_type,
        )

        new_results = [updated_item if r.source_name == source_name else r for r in _last_results]
        self._recompute_target_names(new_results)

        processed = sum(1 for r in new_results if not r.needs_manual_review)
        manual_review = sum(1 for r in new_results if r.needs_manual_review)
        _last_results_renamed = False
        return self._store_and_respond(new_results, processed, manual_review, skipped=0, failed=0)

    def _recompute_target_names(self, results: list[ParseResultItem]) -> None:
        output = Path(self.config.output_folder)
        used_names: set[Path] = set()
        for i, item in enumerate(results):
            document = Document(**item.fields)
            type_config = self.config.document_types.get(
                item.document_type, self._default_type_config()
            )
            pdf_path = Path(item.source_path)
            target_name = _resolve_target_name(
                pdf_path,
                output,
                self.config,
                type_config,
                document,
                item.missing_required,
                used_names,
            )
            results[i] = item.model_copy(update={"target_name": target_name})

    def run(self, dry_run: bool = False) -> dict:
        if not dry_run and _last_results:
            return self._run_from_preview(dry_run)

        config = self.config
        if dry_run:
            config.features.dry_run = True

        log_info(self.logger, "UI_RUN_STARTED", {"dry_run": dry_run})
        process_pdfs(config, self.logger)
        log_info(self.logger, "UI_RUN_FINISHED", {"dry_run": dry_run})

        return {
            "success": True,
            "dry_run": dry_run,
            "message": "Dry-run completed. No files were modified." if dry_run else "Run completed. Files renamed/archived.",
        }

    def _run_from_preview(self, dry_run: bool) -> dict:
        global _last_results_renamed
        config = self.config
        input_dir = Path(config.input_folder)
        output = Path(config.output_folder)
        archive = Path(config.archive_folder) if Path(config.archive_folder).is_absolute() else output / config.archive_folder

        processed: list[str] = []
        manual_review: list[str] = []
        failed: list[str] = []

        for item in _last_results:
            pdf_path = Path(item.source_path)
            if not pdf_path.is_file():
                failed.append(item.source_name)
                continue

            try:
                target = output / item.target_name
                if item.needs_manual_review:
                    rename_pdf(pdf_path, target, dry_run, self.logger, "MANUAL_REVIEW")
                    if not dry_run:
                        write_metadata_file(target, Document(document_type=item.document_type, **item.fields))
                    manual_review.append(item.source_name)
                    continue

                if config.features.archive:
                    archive_original(pdf_path, archive, dry_run, self.logger)

                rename_pdf(pdf_path, target, dry_run, self.logger)
                if not dry_run:
                    write_metadata_file(target, Document(document_type=item.document_type, **item.fields))
                processed.append(item.source_name)
            except Exception as exc:
                log_info(self.logger, "PROCESS_FAILED", {"file": item.source_name, "error": str(exc)})
                failed.append(item.source_name)

        if not dry_run:
            _write_run_state(output, processed, manual_review, failed)
            _last_results_renamed = True

        return {
            "success": True,
            "dry_run": dry_run,
            "message": f"Run completed. {len(processed)} renamed, {len(manual_review)} manual review, {len(failed)} failed.",
        }

    def get_last_preview_results(self) -> list[ParseResultItem]:
        return _last_results

    def _to_result_item(self, source_name: str, result) -> ParseResultItem:
        return ParseResultItem(
            source_name=source_name,
            source_path=str(result.source_path),
            fields=result.document.to_dict(),
            missing_required=result.missing_required,
            target_name=result.target_name,
            needs_manual_review=result.needs_manual_review,
            number_fallback_used=result.number_fallback_used,
            document_type=result.document_type,
        )

    def _empty_response(self) -> ParseResponse:
        return ParseResponse(
            dry_run=True,
            results=[],
            processed_count=0,
            manual_review_count=0,
            skipped_count=0,
            failed_count=0,
        )

    def _store_and_respond(
        self,
        results: list[ParseResultItem],
        processed: int,
        manual_review: int,
        skipped: int,
        failed: int,
    ) -> ParseResponse:
        global _last_results, _last_results_renamed
        _last_results = results
        if not results:
            _last_results_renamed = False
        return ParseResponse(
            dry_run=True,
            results=results,
            processed_count=processed,
            manual_review_count=manual_review,
            skipped_count=skipped,
            failed_count=failed,
        )
