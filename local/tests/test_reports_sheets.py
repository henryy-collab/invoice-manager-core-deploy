from datetime import datetime

import pytest

from invoice_parser.config import AppConfig, GoogleSheetsConfig
from invoice_parser.models import Invoice
from invoice_parser.reports.sheets import (
    HEADER_COLUMNS,
    _group_invoices_by_sheet,
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
    grouped = _group_invoices_by_sheet(invoices, config)
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
    assert HEADER_COLUMNS[4] == "PDF Invoice No."
    assert HEADER_COLUMNS[5] == "PDF Invoice Date"
    assert HEADER_COLUMNS[7] == "Invoice Date"


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
