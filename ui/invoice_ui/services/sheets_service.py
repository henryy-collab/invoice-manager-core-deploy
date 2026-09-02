from pathlib import Path

from invoice_parser.config import AppConfig
from invoice_parser.models import Document
from invoice_parser.reports.sheets import append_invoice_rows
from invoice_ui.services import ParseService


class SheetsService:
    def __init__(self, config: AppConfig, config_path: Path | None = None):
        self.config = config
        self.config_path = config_path

    @classmethod
    def from_request(cls, request) -> "SheetsService":
        from invoice_ui.dependencies import get_app_config, get_config_path

        return cls(get_app_config(request), get_config_path(request))

    def write_preview_results(self, results: list, overwrite: bool = False) -> dict:
        if not self.config.google_sheets.enabled:
            return {"success": True, "skipped": True, "message": "Google Sheets reporting is disabled."}

        documents = [
            Document(document_type=r.document_type, **r.fields)
            for r in results if not r.needs_manual_review
        ]
        if not documents:
            return {"success": True, "skipped": True, "message": "No processed invoices to report."}

        grouped: dict[str, list] = {}
        for document in documents:
            grouped.setdefault(document.document_type, []).append(document)

        total_written = 0
        total_updated = 0
        sheet_counts: dict[str, dict] = {}
        errors: list[str] = []

        for document_type, group in grouped.items():
            config = self.config.model_copy(deep=True)
            gs = config.google_sheets_for(document_type)
            if gs.service_account_file and not Path(gs.service_account_file).is_absolute():
                gs.service_account_file = str(self._project_root() / gs.service_account_file)
            config.google_sheets = gs
            result = append_invoice_rows(group, config, overwrite=overwrite)
            if result.get("success"):
                total_written += result.get("written", 0)
                total_updated += result.get("updated", 0)
                sheet_counts[document_type] = result
            else:
                errors.append(f"{document_type}: {result.get('error', 'unknown error')}")

        if not sheet_counts:
            return {"success": False, "error": " ".join(errors)}

        message_parts = [f"Wrote {total_written} row(s) across {len(sheet_counts)} platform type(s)."]
        if total_updated:
            message_parts.append(f"Updated {total_updated} existing row(s).")
        if errors:
            message_parts.append("Errors: " + " ".join(errors))

        return {
            "success": not errors,
            "written": total_written,
            "updated": total_updated,
            "sheets": sheet_counts,
            "errors": errors,
            "message": " ".join(message_parts),
        }

    def write_last_preview_results(self, parse_service: ParseService | None = None, overwrite: bool = False) -> dict:
        if parse_service is None:
            parse_service = ParseService(self.config, self.config_path, None)
        if not parse_service.can_write_report():
            return {
                "success": False,
                "error": "Rename files before writing to the report. If you edited fields, click Rename Files again.",
            }
        return self.write_preview_results(parse_service.get_last_preview_results(), overwrite=overwrite)

    def _project_root(self) -> Path:
        path = Path(__file__).resolve()
        while path.parent != path:
            if (path / "pyproject.toml").exists():
                return path
            path = path.parent
        return Path.cwd()
