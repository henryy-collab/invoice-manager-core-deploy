import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from invoice_parser.config import AppConfig, GoogleSheetsConfig
from invoice_parser.models import Invoice

HEADER_COLUMNS = [
    "Client Ref.",
    "Platform",
    "Agreed Amount",
    "Invoice No.",
    "PDF Invoice No.",
    "PDF Invoice Date",
    "Amount",
    "Invoice Date",
    "Paid Date",
    "AM",
    "PM",
    "Informed AM & PM",
    "Top up date",
    "Topped amount",
    "Balance",
]

_SHEET_URL_RE = re.compile(r"/d/([a-zA-Z0-9\-_]+)")


def extract_spreadsheet_id(url: str | None) -> str:
    if not url:
        raise ValueError("spreadsheet_url is not configured")
    match = _SHEET_URL_RE.search(url)
    if not match:
        raise ValueError(f"could not extract spreadsheet ID from URL: {url}")
    return match.group(1)


def build_sheet_name(config: GoogleSheetsConfig, dt: datetime) -> str:
    return dt.strftime(config.tab_name_template)


def _parse_date(value: str | None, date_format: str) -> datetime | None:
    if not value:
        return None
    formats = [date_format, "%Y%m%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("$", "").replace("€", "").replace("£", "").replace("¥", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _format_row(invoice: Invoice, config: GoogleSheetsConfig) -> list[Any]:
    date_value = _parse_date(invoice.date, config.date_format)
    amount_value = _parse_amount(invoice.total)

    return [
        invoice.account or "",
        "",
        "",
        "",
        invoice.number or "",
        date_value.strftime("%Y-%m-%d") if date_value is not None else "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        amount_value if amount_value is not None else "",
        "",
    ]


def _group_invoices_by_sheet(
    invoices: list[Invoice],
    config: GoogleSheetsConfig,
) -> dict[str, list[Invoice]]:
    grouped: dict[str, list[Invoice]] = defaultdict(list)
    for invoice in invoices:
        dt = _parse_date(invoice.date, config.date_format)
        sheet_name = build_sheet_name(config, dt) if dt else build_sheet_name(config, datetime.now())
        grouped[sheet_name].append(invoice)
    return grouped


def get_existing_invoice_numbers(values: list[list[Any]], number_column: int = 4) -> set[str]:
    existing: set[str] = set()
    for i, row in enumerate(values):
        if i == 0:
            continue
        if len(row) > number_column and row[number_column]:
            existing.add(str(row[number_column]))
    return existing


def _authenticate_client(service_account_file: str | None):
    import gspread
    from google.oauth2.service_account import Credentials

    if service_account_file is None:
        raise RuntimeError("service_account_file must be configured for Google Sheets reporting")

    path = Path(service_account_file)
    if not path.exists():
        raise FileNotFoundError(f"service account file not found: {service_account_file}")
    creds = Credentials.from_service_account_file(
        str(path),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def _open_worksheet(client, spreadsheet_id: str, sheet_name: str):
    import gspread

    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(HEADER_COLUMNS))


def _ensure_headers(worksheet) -> list[list[Any]]:
    values = worksheet.get_all_values()
    if not values or values[0] != HEADER_COLUMNS:
        worksheet.clear()
        worksheet.append_row(HEADER_COLUMNS)
        values = [HEADER_COLUMNS]
    return values


def _append_to_sheet(
    worksheet,
    invoices: list[Invoice],
    config: GoogleSheetsConfig,
) -> int:
    values = _ensure_headers(worksheet)
    existing_numbers = get_existing_invoice_numbers(values)

    rows: list[list[Any]] = []
    for invoice in invoices:
        number = invoice.number or ""
        if number in existing_numbers:
            continue
        existing_numbers.add(number)
        rows.append(_format_row(invoice, config))

    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    return len(rows)


def append_invoice_rows(
    invoices: list[Invoice],
    config: AppConfig,
) -> dict[str, Any]:
    gs_config = config.google_sheets
    if not gs_config.enabled:
        return {"success": True, "skipped": True, "message": "Google Sheets reporting is disabled."}

    if not invoices:
        return {"success": True, "skipped": True, "message": "No processed invoices to report."}

    try:
        spreadsheet_id = extract_spreadsheet_id(gs_config.spreadsheet_url)
        client = _authenticate_client(gs_config.service_account_file)

        grouped = _group_invoices_by_sheet(invoices, gs_config)
        sheet_counts: dict[str, int] = {}

        for sheet_name, sheet_invoices in grouped.items():
            worksheet = _open_worksheet(client, spreadsheet_id, sheet_name)
            written = _append_to_sheet(worksheet, sheet_invoices, gs_config)
            sheet_counts[sheet_name] = written

        total_written = sum(sheet_counts.values())

        return {
            "success": True,
            "written": total_written,
            "sheets": sheet_counts,
            "message": f"Wrote {total_written} row(s) across {len(sheet_counts)} sheet(s).",
        }
    except FileNotFoundError as exc:
        return {
            "success": False,
            "error": f"Service account file not found: {exc}. Check google_sheets.service_account_file in config.",
        }
    except ValueError as exc:
        return {"success": False, "error": f"Invalid Google Sheets config: {exc}"}
    except Exception as exc:
        return {"success": False, "error": f"Google Sheets error: {exc}"}
