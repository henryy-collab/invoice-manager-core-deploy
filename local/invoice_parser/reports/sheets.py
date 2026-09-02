import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from invoice_parser.config import AppConfig, DocumentTypeConfig, GoogleSheetsConfig
from invoice_parser.models import Document, Invoice

HEADER_COLUMNS = [
    "Client Ref.",
    "Account ID",
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
    "Topped Currency",
    "Topped amount",
    "Balance",
    "Invoice Type",
]

_SHEET_WARNING = "COPY THIS SHEET FIRST, THEN DELETE [AUTO]. DO NOT EDIT DIRECTLY — IT BREAKS AUTOMATION."

_SHEET_URL_RE = re.compile(r"/d/([a-zA-Z0-9\-_]+)")


def extract_spreadsheet_id(url: str | None) -> str:
    if not url:
        raise ValueError("spreadsheet_url is not configured")
    match = _SHEET_URL_RE.search(url)
    if not match:
        raise ValueError(f"could not extract spreadsheet ID from URL: {url}")
    return match.group(1)


def build_sheet_name(config: GoogleSheetsConfig, dt: datetime) -> str:
    return dt.strftime(config.tab_name_template) + config.raw_sheet_suffix


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


def _format_row(document: Document, type_config: DocumentTypeConfig, config: GoogleSheetsConfig) -> list[Any]:
    column_to_field = {column: field for field, column in type_config.report_columns.items()}

    row: list[Any] = []
    for column in HEADER_COLUMNS:
        field = column_to_field.get(column)
        if field is None:
            row.append("")
            continue

        value = document.get(field)
        if field in ("document_type", "platform"):
            value = document.document_type

        if column == "PDF Invoice Date":
            date_value = _parse_date(value, config.date_format)
            row.append(date_value.strftime("%Y-%m-%d") if date_value is not None else "")
        elif column == "Topped amount":
            amount_value = _parse_amount(value)
            row.append(amount_value if amount_value is not None else "")
        else:
            row.append(value or "")

    return row


def _group_documents_by_sheet(
    documents: list[Document],
    config: GoogleSheetsConfig,
) -> dict[str, list[Document]]:
    grouped: dict[str, list[Document]] = defaultdict(list)
    for document in documents:
        dt = _parse_date(document.get("date"), config.date_format)
        sheet_name = build_sheet_name(config, dt) if dt else build_sheet_name(config, datetime.now())
        grouped[sheet_name].append(document)
    return grouped


def _find_header_column_index(values: list[list[Any]], column_name: str) -> int | None:
    if len(values) < 2:
        return None
    header_row = values[1]
    for i, cell in enumerate(header_row):
        if cell == column_name:
            return i
    return None


def _map_existing_rows(values: list[list[Any]], column_index: int | None = None) -> dict[str, int]:
    existing: dict[str, int] = {}
    for i, row in enumerate(values):
        if i in (0, 1):
            continue
        if column_index is not None:
            if len(row) > column_index and row[column_index]:
                existing[str(row[column_index])] = i + 1
        else:
            for cell in row:
                cell_str = str(cell)
                if cell_str:
                    existing.setdefault(cell_str, i + 1)
    return existing


def _read_service_account_email(service_account_file: str) -> str | None:
    path = Path(service_account_file)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("client_email")
    except (json.JSONDecodeError, OSError):
        return None


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


def _protect_worksheet(spreadsheet, worksheet, service_account_email: str | None) -> None:
    spreadsheet.batch_update({
        "requests": [{
            "addProtectedRange": {
                "protectedRange": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 1,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 26,
                    },
                    "description": "COPY this sheet first, then delete [Auto]. Do NOT edit directly — it breaks automation.",
                    "warningOnly": True,
                },
            },
        }],
    })


def _open_worksheet(client, spreadsheet_id: str, sheet_name: str, service_account_email: str | None):
    import gspread

    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        return spreadsheet, spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(HEADER_COLUMNS))
        worksheet.append_row([_SHEET_WARNING])
        worksheet.append_row(HEADER_COLUMNS)
        _format_warning(spreadsheet, worksheet)
        _protect_worksheet(spreadsheet, worksheet, service_account_email)
        return spreadsheet, worksheet


def _format_warning(spreadsheet, worksheet):
    end_column = len(HEADER_COLUMNS) - 1
    spreadsheet.batch_update({
        "requests": [
            {
                "mergeCells": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(HEADER_COLUMNS),
                    },
                    "mergeType": "MERGE_ALL",
                },
            },
        ],
    })
    worksheet.format("A1", {
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1, "green": 0, "blue": 0},
            "fontSize": 14,
        },
        "backgroundColor": {"red": 1, "green": 1, "blue": 0},
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
    })
    if end_column > 0:
        worksheet.format(
            f"A1:{chr(65 + end_column)}1",
            {"backgroundColor": {"red": 1, "green": 1, "blue": 0}},
        )


def _ensure_headers(worksheet, spreadsheet) -> list[list[Any]]:
    values = worksheet.get_all_values()

    has_warning = bool(values) and bool(values[0]) and values[0][0] == _SHEET_WARNING
    has_header = bool(values) and len(values) > 1 and values[1] == HEADER_COLUMNS

    if has_warning and has_header:
        return values

    if not values or all(not any(str(cell).strip() for cell in row) for row in values):
        worksheet.clear()
        worksheet.append_row([_SHEET_WARNING])
        worksheet.append_row(HEADER_COLUMNS)
        _format_warning(spreadsheet, worksheet)
        return [[_SHEET_WARNING], HEADER_COLUMNS]

    # Auto tab with data but a stale header: align the header row so future
    # appends line up with HEADER_COLUMNS. Existing rows are matched by key
    # scan, so this stays safe even when legacy rows are shorter than the new
    # column layout.
    if has_warning and len(values) > 1:
        worksheet.update("A2", [HEADER_COLUMNS], value_input_option="USER_ENTERED")
        values[1] = list(HEADER_COLUMNS)

    return values


def _resolve_key_column_index(
    type_config: DocumentTypeConfig,
) -> int | None:
    target_column = type_config.report_columns.get("number")
    if target_column is None:
        return None
    if target_column not in HEADER_COLUMNS:
        return None
    return HEADER_COLUMNS.index(target_column)


def _upsert_to_sheet(
    spreadsheet,
    worksheet,
    documents: list[Document],
    config: AppConfig,
    overwrite: bool = False,
) -> dict[str, int]:
    gs_config = config.google_sheets
    default_type_config = config.document_types[config.default_document_type]

    if overwrite:
        worksheet.clear()
        values: list[list[Any]] = []
    else:
        values = _ensure_headers(worksheet, spreadsheet)

    if not values:
        worksheet.append_row([_SHEET_WARNING])
        worksheet.append_row(HEADER_COLUMNS)
        _format_warning(spreadsheet, worksheet)
        values = [[_SHEET_WARNING], HEADER_COLUMNS]

    key_column_index: int | None = None
    existing_rows: dict[str, int] = {}

    updates: list[tuple[int, list[Any]]] = []
    new_rows: list[list[Any]] = []

    for document in documents:
        type_config = config.document_types.get(document.document_type, default_type_config)
        if key_column_index is None:
            key_column_index = _resolve_key_column_index(type_config)
            if not overwrite:
                existing_rows = _map_existing_rows(values)

        row = _format_row(document, type_config, gs_config)
        if key_column_index is not None and len(row) > key_column_index:
            key_value = str(row[key_column_index])
        else:
            key_value = document.get("number") or ""

        if key_value and key_value in existing_rows and not overwrite:
            row_number = existing_rows[key_value]
            updates.append((row_number, row))
        else:
            new_rows.append(row)
            if key_value:
                existing_rows[key_value] = len(values) + len(new_rows)

    for row_number, row in updates:
        worksheet.update(f"A{row_number}", [row], value_input_option="USER_ENTERED")

    if new_rows:
        worksheet.append_rows(new_rows, value_input_option="USER_ENTERED")

    return {"written": len(new_rows), "updated": len(updates)}



def append_invoice_rows(
    documents: list[Document],
    config: AppConfig,
    overwrite: bool = False,
) -> dict[str, Any]:
    gs_config = config.google_sheets
    if not gs_config.enabled:
        return {"success": True, "skipped": True, "message": "Google Sheets reporting is disabled."}

    if not documents:
        return {"success": True, "skipped": True, "message": "No processed invoices to report."}

    try:
        spreadsheet_id = extract_spreadsheet_id(gs_config.spreadsheet_url)
        client = _authenticate_client(gs_config.service_account_file)
        service_account_email = _read_service_account_email(gs_config.service_account_file) if gs_config.service_account_file else None

        grouped = _group_documents_by_sheet(documents, gs_config)
        sheet_counts: dict[str, dict[str, int]] = {}

        for sheet_name, sheet_documents in grouped.items():
            spreadsheet, worksheet = _open_worksheet(client, spreadsheet_id, sheet_name, service_account_email)
            sheet_counts[sheet_name] = _upsert_to_sheet(spreadsheet, worksheet, sheet_documents, config, overwrite=overwrite)

        total_written = sum(counts["written"] for counts in sheet_counts.values())
        total_updated = sum(counts["updated"] for counts in sheet_counts.values())

        message_parts = [f"Wrote {total_written} row(s) across {len(sheet_counts)} sheet(s)."]
        if total_updated:
            message_parts.append(f"Updated {total_updated} existing row(s).")

        return {
            "success": True,
            "written": total_written,
            "updated": total_updated,
            "sheets": sheet_counts,
            "message": " ".join(message_parts),
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
