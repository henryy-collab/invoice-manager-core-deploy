from datetime import datetime

import pytest

from invoice_parser.config import AppConfig, DocumentTypeConfig, GoogleSheetsConfig
from invoice_parser.models import Document, Invoice
from invoice_parser.reports.sheets import (
    HEADER_COLUMNS,
    _SHEET_WARNING,
    _ensure_headers,
    _find_header_column_index,
    _format_row,
    _group_documents_by_sheet,
    _map_existing_rows,
    _resolve_key_column_index,
    _upsert_to_sheet,
    append_invoice_rows,
    build_sheet_name,
    extract_spreadsheet_id,
)


def test_extract_spreadsheet_id_from_url():
    url = "https://docs.google.com/spreadsheets/d/ABC123xyz-456/edit#gid=0"
    assert extract_spreadsheet_id(url) == "ABC123xyz-456"


def test_extract_spreadsheet_id_missing_id():
    with pytest.raises(ValueError, match="spreadsheet ID"):
        extract_spreadsheet_id("https://docs.google.com/spreadsheets/edit")


def test_extract_spreadsheet_id_none():
    with pytest.raises(ValueError, match="not configured"):
        extract_spreadsheet_id(None)


def test_build_sheet_name():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    dt = datetime(2026, 4, 30)
    assert build_sheet_name(config, dt) == "Apr 2026 [Auto]"


def test_build_sheet_name_custom_suffix():
    config = GoogleSheetsConfig(
        spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit",
        raw_sheet_suffix=" [RAW]",
    )
    dt = datetime(2026, 4, 30)
    assert build_sheet_name(config, dt) == "Apr 2026 [RAW]"


def test_group_invoices_by_sheet():
    config = GoogleSheetsConfig(
        spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit",
        date_format="%d/%m/%Y",
    )
    invoices = [
        Invoice(account="A", number="N1", date="15/04/2026", total="100.00", currency="HKD"),
        Invoice(account="B", number="N2", date="20/05/2026", total="200.00", currency="HKD"),
        Invoice(account="C", number="N3", date="01/04/2026", total="300.00", currency="HKD"),
    ]
    grouped = _group_documents_by_sheet(invoices, config)
    assert set(grouped.keys()) == {"Apr 2026 [Auto]", "May 2026 [Auto]"}
    assert len(grouped["Apr 2026 [Auto]"]) == 2
    assert len(grouped["May 2026 [Auto]"]) == 1


def test_append_invoice_rows_disabled(config_factory):
    config = config_factory(google_sheets={"enabled": False})
    result = append_invoice_rows([], config)
    assert result["skipped"] is True


def test_append_invoice_rows_no_invoices(config_factory):
    config = config_factory(
        google_sheets={
            "enabled": True,
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/x/edit",
            "service_account_file": "nonexistent.json",
        },
    )
    result = append_invoice_rows([], config)
    assert result["skipped"] is True
    assert "No processed invoices" in result["message"]


def test_pdf_invoice_date_column_position():
    assert HEADER_COLUMNS[5] == "PDF Invoice No."
    assert HEADER_COLUMNS[6] == "PDF Invoice Date"
    assert HEADER_COLUMNS[8] == "Invoice Date"


def test_topped_currency_column_position():
    assert HEADER_COLUMNS[13] == "Top up date"
    assert HEADER_COLUMNS[14] == "Topped Currency"
    assert HEADER_COLUMNS[15] == "Topped amount"
    assert HEADER_COLUMNS[16] == "Balance"


def test_warning_row_constant():
    assert _SHEET_WARNING.startswith("COPY THIS SHEET FIRST")
    assert "DO NOT EDIT DIRECTLY" in _SHEET_WARNING


def test_map_existing_rows():
    values = [
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["A", "", "", "", "N1", "15/04/2026", "", "", "", "", "", "", "", "HKD", "100.00", ""],
        ["B", "", "", "", "N2", "20/05/2026", "", "", "", "", "", "", "", "HKD", "200.00", ""],
    ]
    existing = _map_existing_rows(values, 4)
    assert existing == {"N1": 3, "N2": 4}


def test_find_header_column_index():
    values = [[_SHEET_WARNING], HEADER_COLUMNS]
    assert _find_header_column_index(values, "PDF Invoice No.") == 5
    assert _find_header_column_index(values, "Missing Column") is None
    assert _find_header_column_index([], "PDF Invoice No.") is None


def test_format_row_uses_default_report_columns():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    type_config = DocumentTypeConfig(
        report_columns={
            "account": "Client Ref.",
            "date": "PDF Invoice Date",
            "number": "PDF Invoice No.",
            "currency": "Topped Currency",
            "total": "Topped amount",
        }
    )
    document = Document(
        account="ACME",
        number="INV-001",
        date="15 April 2026",
        currency="HKD",
        total="1,234.56",
    )
    row = _format_row(document, type_config, config)
    assert row[0] == "ACME"
    assert row[5] == "INV-001"
    assert row[6] == "2026-04-15"
    assert row[14] == "HKD"
    assert row[15] == 1234.56


def test_format_row_uses_alternate_report_columns():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    type_config = DocumentTypeConfig(
        report_columns={
            "number": "Client Ref.",
            "account": "Invoice No.",
        }
    )
    document = Document(
        account="ACME",
        number="INV-001",
    )
    row = _format_row(document, type_config, config)
    assert row[0] == "INV-001"
    assert row[4] == "ACME"


def test_format_row_reports_document_type():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    type_config = DocumentTypeConfig(
        report_columns={
            "document_type": "Invoice Type",
        }
    )
    document = Document(document_type="google_ads", account="ACME")
    row = _format_row(document, type_config, config)
    assert row[-1] == "google_ads"
    assert HEADER_COLUMNS[-1] == "Invoice Type"


def test_format_row_reports_platform_from_document_type():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    type_config = DocumentTypeConfig(
        report_columns={
            "platform": "Platform",
        }
    )
    document = Document(document_type="facebook", account="Denza")
    row = _format_row(document, type_config, config)
    assert row[2] == "facebook"
    assert HEADER_COLUMNS[2] == "Platform"


def test_format_row_reports_account_id():
    config = GoogleSheetsConfig(spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit")
    type_config = DocumentTypeConfig(
        report_columns={
            "account_id": "Account ID",
        }
    )
    document = Document(account_id="9338641234")
    row = _format_row(document, type_config, config)
    assert row[1] == "9338641234"
    assert HEADER_COLUMNS[1] == "Account ID"


class FakeSpreadsheet:
    def batch_update(self, *args, **kwargs):
        pass


def _make_worksheet(values=None):
    class FakeWorksheet:
        id = 1

        def __init__(self, values):
            self._values = [list(row) for row in (values or [])]
            self.appended = []
            self.updated = []
            self.cleared = False

        def get_all_values(self):
            return [list(row) for row in self._values]

        def append_rows(self, rows, value_input_option=None):
            self.appended.extend(rows)
            self._values.extend(rows)

        def append_row(self, row):
            self._values.append(list(row))

        def update(self, range_name, values, value_input_option=None):
            self.updated.append((range_name, values))
            row_number = int(range_name.replace("A", "").split(":")[0])
            while len(self._values) < row_number:
                self._values.append([])
            self._values[row_number - 1] = list(values[0])

        def insert_row(self, row, index):
            self._values.insert(index - 1, list(row))

        def clear(self):
            self._values.clear()
            self.cleared = True

        def format(self, *args, **kwargs):
            pass

    return FakeWorksheet(values)


def _make_config():
    from invoice_parser.config import AppConfig, DocumentTypeConfig, GoogleSheetsConfig

    return AppConfig(
        source_folder="local/data",
        google_sheets=GoogleSheetsConfig(
            enabled=True,
            spreadsheet_url="https://docs.google.com/spreadsheets/d/x/edit",
            service_account_file="nonexistent.json",
        ),
        document_types={
            "google_ads": DocumentTypeConfig(
                classifier={"patterns": ["Invoice"]},
                fields={},
                filename_template="{account}_{number}_Invoice_{date}.pdf",
                report_columns={
                    "account": "Client Ref.",
                    "account_id": "Account ID",
                    "date": "PDF Invoice Date",
                    "number": "PDF Invoice No.",
                    "currency": "Topped Currency",
                    "total": "Topped amount",
                },
            )
        },
        default_document_type="google_ads",
    )


def test_upsert_to_sheet_updates_existing_rows_by_number():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["Old", "", "", "", "", "N1", "2026-04-15", "", "", "", "", "", "", "", "HKD", "100.00", "", ""],
    ])
    config = _make_config()
    documents = [
        Document(account="Updated", number="N1", date="15 April 2026", currency="HKD", total="150.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config)

    assert result["written"] == 0
    assert result["updated"] == 1
    assert worksheet.cleared is False
    assert len(worksheet.updated) == 1
    assert worksheet.updated[0][1][0][0] == "Updated"
    assert worksheet._values[2][0] == "Updated"


def test_upsert_to_sheet_appends_new_rows():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
    ])
    config = _make_config()
    documents = [
        Document(account="A", number="N1", date="15 April 2026", currency="HKD", total="100.00"),
        Document(account="B", number="N2", date="16 April 2026", currency="HKD", total="200.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config)

    assert result["written"] == 2
    assert result["updated"] == 0
    assert len(worksheet.appended) == 2
    assert worksheet.appended[0][5] == "N1"
    assert worksheet.appended[1][5] == "N2"


def test_upsert_to_sheet_mixed_update_and_append():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["A", "", "", "", "", "N1", "2026-04-15", "", "", "", "", "", "", "", "HKD", "100.00", "", ""],
    ])
    config = _make_config()
    documents = [
        Document(account="A", number="N1", date="15 April 2026", currency="HKD", total="100.00"),
        Document(account="B", number="N2", date="16 April 2026", currency="HKD", total="200.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config)

    assert result["written"] == 1
    assert result["updated"] == 1
    assert worksheet._values[2][5] == "N1"
    assert worksheet.appended[0][5] == "N2"


def test_upsert_to_sheet_overwrite_clears_and_rewrites():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["A", "", "", "", "", "N1", "2026-04-15", "", "", "", "", "", "", "", "HKD", "100.00", "", ""],
    ])
    config = _make_config()
    documents = [
        Document(account="B", number="N2", date="16 April 2026", currency="HKD", total="200.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config, overwrite=True)

    assert result["written"] == 1
    assert result["updated"] == 0
    assert worksheet.cleared is True
    assert len(worksheet.appended) == 1
    assert worksheet.appended[0][5] == "N2"


@pytest.fixture
def config_factory(tmp_path):
    def _factory(**overrides):
        base = {
            "source_folder": str(tmp_path),
            "filename_template": "{account}_{number}_Invoice_{date}.pdf",
            "date_format": "%Y%m%d",
        }
        base.update(overrides)
        return AppConfig.model_validate(base)
    return _factory


def test_resolve_key_column_index_uses_headless_columns():
    type_config = DocumentTypeConfig(report_columns={"number": "PDF Invoice No."})
    assert _resolve_key_column_index(type_config) == 5


def test_resolve_key_column_index_none_when_unmapped():
    type_config = DocumentTypeConfig(report_columns={"number": "Missing Column"})
    assert _resolve_key_column_index(type_config) is None
    assert _resolve_key_column_index(DocumentTypeConfig(report_columns={})) is None


def test_map_existing_rows_full_scan_finds_number_in_stale_row():
    values = [
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["Hopewell Hotel", "google_ads", "", "", "5647274549", "2026-07-31", "", "", "", "", "", "", "", "HKD", "26482.79", "", ""],
    ]
    existing = _map_existing_rows(values)
    assert existing["5647274549"] == 3
    assert existing["Hopewell Hotel"] == 3
    assert existing["google_ads"] == 3
    assert existing["2026-07-31"] == 3
    assert existing["HKD"] == 3
    assert existing["26482.79"] == 3


def test_ensure_headers_refreshes_stale_header_on_data_tab():
    stale_header = [
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
        "Topped Currency",
        "Topped amount",
        "Balance",
    ]
    worksheet = _make_worksheet([
        [_SHEET_WARNING] + [""] * 5,
        stale_header,
        ["Old", "", "", "N1", "2026-04-15", "", "", "", "", "", "", "", "", "HKD", "100.00", "", ""],
    ])
    values = _ensure_headers(worksheet, FakeSpreadsheet())
    assert values[1] == HEADER_COLUMNS
    assert worksheet.updated[0][0] == "A2"
    assert worksheet.updated[0][1][0] == HEADER_COLUMNS


def test_upsert_updates_existing_stale_layout_row_instead_of_appending():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
        ["Old", "", "", "", "N1", "2026-04-15", "", "", "", "", "", "", "", "", "HKD", "100.00", ""],
    ])
    config = _make_config()
    documents = [
        Document(account="Updated", account_id="Updated", number="N1", date="15 April 2026", currency="HKD", total="150.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config)

    assert result["written"] == 0
    assert result["updated"] == 1
    assert worksheet.cleared is False
    assert len(worksheet.updated) == 1
    assert worksheet.updated[0][1][0][1] == "Updated"
    assert worksheet.updated[0][1][0][0] == "Updated"
    assert worksheet.updated[0][1][0][5] == "N1"


def test_upsert_appends_new_row_with_account_id():
    worksheet = _make_worksheet([
        [_SHEET_WARNING],
        HEADER_COLUMNS,
    ])
    config = _make_config()
    documents = [
        Document(document_type="google_ads", account="A", account_id="9338641234", number="N1", date="15 April 2026", currency="HKD", total="100.00"),
    ]

    result = _upsert_to_sheet(FakeSpreadsheet(), worksheet, documents, config)

    assert result["written"] == 1
    assert result["updated"] == 0
    assert worksheet.appended[0][0] == "A"
    assert worksheet.appended[0][1] == "9338641234"
    assert worksheet.appended[0][5] == "N1"
