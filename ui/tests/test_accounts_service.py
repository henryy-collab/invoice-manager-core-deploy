import json
from pathlib import Path

from invoice_parser.config import AppConfig
from invoice_ui.services.accounts_service import AccountsService

MULTI_ACCOUNT_TEXT = """Invoice number: 5565701224
Invoice date: 30 April 2026
Total amount due in HKD
HK$19,617.21
HK$0.00
HK$19,617.21
Summary of costs by account budget
1 Apr 2026 - 30 Apr 2026
Account ID
Account
Account budget
Purchase
Order
Amount(HK$)
802-155-
0535
HKCT - Brand [Monthly Invoicing]
HKCT_HKCT Brand_2026 Apr
804.21
751-190-
9696
HKCT - CIE [Monthly Invoicing]
HKCT_CIE_2026 Apr
18,813.00
Tax Invoice
Invoice number: 5565701224
Page 3 of 10
HK$804.21
HK$0.00
HK$804.21
Subtotal in HKD
GST (0%)
Total in HKD
Account: HKCT - Brand [Monthly Invoicing]
Account ID: 802-155-0535
Account budget: HKCT_HKCT Brand_2026 Apr
"""

SINGLE_ACCOUNT_TEXT = """Invoice number: 5561278890
Invoice date: 30 April 2026
Total amount due in HKD
HK$18,995.38
HK$0.00
HK$18,995.38
Page 2 of 5
HK$18,995.38
HK$0.00
HK$18,995.38
Subtotal in HKD
GST (0%)
Total in HKD
Account: Intertextile Shanghai [Monthly Invoicing]
Account ID: 180-983-1993
Account budget: Monthly Invoicing - 20230620
"""


def _make_config(tmp_path):
    return AppConfig.model_validate({
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "incoming"),
        "output_folder": str(tmp_path / "outgoing"),
        "archive_folder": str(tmp_path / "archive"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    })


def _make_archive(tmp_path, files: dict):
    archive = tmp_path / "archive"
    archive.mkdir(parents=True)
    for name in files:
        (archive / name).write_bytes(b"%PDF-1.4 dummy")


def _write_state(tmp_path, processed: list[str]):
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "last_run_processed.json").write_text(
        json.dumps({"processed": processed}), encoding="utf-8"
    )


def test_build_records_latest_run_multi_account_aggregated(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"5565701224.pdf": None})
    _write_state(tmp_path, ["5565701224.pdf"])
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _p: MULTI_ACCOUNT_TEXT)

    result = AccountsService(config).build_records()

    assert result["errors"] == 0
    assert result["count"] == 2
    by_id = {r["account_id"]: r for r in result["records"]}
    brand = by_id["8021550535"]
    assert brand["account"] == "HKCT - Brand"
    assert brand["amount"] == "804.21"
    assert brand["invoice_count"] == 1
    assert brand["invoices"][0]["number"] == "5565701224"
    assert brand["invoices"][0]["date"] == "2026-04-30"
    assert brand["invoices"][0]["currency"] == "HKD"
    assert by_id["7511909696"]["amount"] == "18813.00"


def test_build_records_single_account_uses_invoice_total(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"5561278890.pdf": None})
    _write_state(tmp_path, ["5561278890.pdf"])
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _p: SINGLE_ACCOUNT_TEXT)

    result = AccountsService(config).build_records()

    assert result["count"] == 1
    rec = result["records"][0]
    assert rec["account_id"] == "1809831993"
    assert rec["account"] == "Intertextile Shanghai"
    assert rec["amount"] == "18995.38"
    assert rec["invoices"][0]["date"] == "2026-04-30"


def test_build_records_aggregates_same_account_across_invoices(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"a.pdf": None, "b.pdf": None})
    _write_state(tmp_path, ["a.pdf", "b.pdf"])
    texts = {
        "a.pdf": SINGLE_ACCOUNT_TEXT.replace("5561278890", "1111111111").replace("April", "May"),
        "b.pdf": SINGLE_ACCOUNT_TEXT,
    }
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda p: texts[Path(p).name])

    result = AccountsService(config).build_records()

    assert result["count"] == 1
    rec = result["records"][0]
    assert rec["account_id"] == "1809831993"
    assert rec["amount"] == "37990.76"
    assert rec["invoice_count"] == 2
    assert {inv["number"] for inv in rec["invoices"]} == {"1111111111", "5561278890"}
    assert {inv["date"] for inv in rec["invoices"]} == {"2026-04-30", "2026-05-30"}


def test_build_records_latest_run_excludes_prior_files(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"a.pdf": None, "b.pdf": None})
    _write_state(tmp_path, ["a.pdf"])
    texts = {
        "a.pdf": SINGLE_ACCOUNT_TEXT,
        "b.pdf": SINGLE_ACCOUNT_TEXT.replace("5561278890", "9999999999"),
    }
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda p: texts[Path(p).name])

    result = AccountsService(config).build_records()

    assert result["count"] == 1
    assert result["records"][0]["account_id"] == "1809831993"
    assert {inv["number"] for inv in result["records"][0]["invoices"]} == {"5561278890"}


def test_build_records_no_state_returns_empty(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"a.pdf": None})
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _p: SINGLE_ACCOUNT_TEXT)

    result = AccountsService(config).build_records()

    assert result == {"records": [], "count": 0, "errors": 0}


def test_build_records_scope_all_ignores_state(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    _make_archive(tmp_path, {"a.pdf": None, "b.pdf": None})
    _write_state(tmp_path, ["a.pdf"])
    texts = {
        "a.pdf": SINGLE_ACCOUNT_TEXT,
        "b.pdf": SINGLE_ACCOUNT_TEXT.replace("5561278890", "9999999999").replace("Intertextile Shanghai", "Other Client").replace("180-983-1993", "200-000-0000"),
    }
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda p: texts[Path(p).name])

    result = AccountsService(config).build_records(scope="all")

    assert result["count"] == 2
    ids = {r["account_id"] for r in result["records"]}
    assert ids == {"1809831993", "2000000000"}


def test_build_records_empty_archive(tmp_path):
    config = _make_config(tmp_path)
    result = AccountsService(config).build_records(scope="all")
    assert result == {"records": [], "count": 0, "errors": 0}
