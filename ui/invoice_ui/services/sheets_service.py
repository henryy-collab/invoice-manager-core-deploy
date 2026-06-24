from pathlib import Path

from invoice_parser.config import AppConfig
from invoice_parser.models import Invoice
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

    def write_preview_results(self, results: list) -> dict:
        if not self.config.google_sheets.enabled:
            return {"success": True, "skipped": True, "message": "Google Sheets reporting is disabled."}

        invoices = [Invoice(**r.fields) for r in results if not r.needs_manual_review]
        if not invoices:
            return {"success": True, "skipped": True, "message": "No processed invoices to report."}

        config = self.config.model_copy(deep=True)
        gs = config.google_sheets
        if gs.service_account_file and not Path(gs.service_account_file).is_absolute():
            gs.service_account_file = str(self._project_root() / gs.service_account_file)

        return append_invoice_rows(invoices, config)

    def write_last_preview_results(self, parse_service: ParseService | None = None) -> dict:
        if parse_service is None:
            parse_service = ParseService(self.config, self.config_path, None)
        if not parse_service.can_write_report():
            return {
                "success": False,
                "error": "Rename files before writing to the report. If you edited fields, click Rename Files again.",
            }
        return self.write_preview_results(parse_service.get_last_preview_results())

    def _project_root(self) -> Path:
        path = Path(__file__).resolve()
        while path.parent != path:
            if (path / "pyproject.toml").exists():
                return path
            path = path.parent
        return Path.cwd()
