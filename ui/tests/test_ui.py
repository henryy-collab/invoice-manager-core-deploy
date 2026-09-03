import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoice_ui.main import create_app


@pytest.fixture
def ui_client(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    config_path = tmp_path / "local" / "local_config.json"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({
        "source_folder": "data",
        "input_folder": "data/incoming",
        "output_folder": "data/outgoing",
        "archive_folder": "data/archive",
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
        "default_document_type": "google_ads",
        "document_types": {
            "google_ads": {
                "classifier": {"patterns": ["Invoice", "Invoice number", "Invoice date"]},
                "fields": {
                    "account": {
                        "parser": "account",
                        "patterns": [{"regex": "^Account:\\s*(.+?)(?=\\s*\\[|\\s*$)", "group": 1, "flags": ["IGNORECASE", "MULTILINE"]}],
                        "unknown_values": ["-"],
                        "fallback": "UNKNOWN",
                    },
                    "account_id": {
                        "parser": "account_id",
                        "patterns": [
                            {"regex": "Account:\\s*[^\\[]*?\\[([\\d\\-]+)\\]", "group": 1, "flags": ["IGNORECASE"]},
                            {"regex": "Account\\s*ID[:\\s]+([\\d\\-]+)", "group": 1, "flags": ["IGNORECASE"]},
                        ],
                        "unknown_values": ["-"],
                        "fallback": "UNKNOWN",
                    },
                    "accounts": {
                        "parser": "accounts",
                        "summary_marker_regex": "Summary\\s+of\\s+costs\\s+by\\s+account\\s+budget",
                        "amount_header_regex": "^Amount\\s*\\(?[A-Z$€£¥]*\\)?$",
                        "account_line_regex": "^Account:\\s*(.+?)(?=\\s*\\[|\\s*$)",
                        "account_id_line_regex": "Account\\s*ID[:\\s]+([\\d\\-]+)",
                        "total_label_regex": "(Total\\s*amount\\s*due\\s*in|Total\\s+in)\\s+[A-Z]{3}",
                        "amount_regex": "(-?)(?:HK\\$|US\\$|\\$|€|£|¥|SGD|HKD|USD|AUD|GBP|EUR|JPY)?\\s*(-?[\\d,]+\\.\\d{2})",
                        "id_lookahead": 4,
                        "name_max_lines": 3,
                    },
                    "number": {
                        "parser": "number",
                        "patterns": [{"regex": "Invoice\\s*number[:\\s]+([A-Z0-9\\-]+)", "group": 1, "flags": ["IGNORECASE"]}],
                        "require_digit": True,
                        "fallback_to_filename": True,
                        "filename_pattern": "^\\d+$",
                    },
                    "date": {
                        "parser": "date",
                        "parse_formats": ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"],
                        "nearby_line_window": 2,
                        "details_block": {
                            "enabled": True,
                            "header": "Details",
                            "dot_separator_regex": "^\\.{5,}$",
                            "label_regex": "Invoice\\s*number|Invoice\\s*date|Payment\\s*terms|Billing\\s*ID|Account\\s*ID",
                            "max_label_length": 80,
                        },
                    },
                    "currency": {
                        "parser": "currency",
                        "primary_regex": "Total\\s*amount\\s*due\\s*in\\s*([A-Z]{3})",
                        "symbol_map": {"HK$": "HKD", "US$": "USD"},
                    },
                    "total": {
                        "parser": "total",
                        "primary_regex": "",
                        "primary_regexes": [
                            r"Total\s*amount\s*due(?:\s*in\s*[A-Z]{3})?[:\s]*([A-Z$€£¥]*)\s*(-?[\d,]+\.\d{2})",
                            r"Total\s+in\s+[A-Z]{3}[:\s]*(-?)([A-Z$€£¥]*)\s*(-?[\d,]+\.\d{2})",
                        ],
                        "fallback_regex": r"(-?)(?:HK\$|US\$|\$|€|£|¥)\s*(-?[\d,]+\.\d{2})",
                        "pick_max": True,
                    },
                },
                "filename_template": "{account}_{number}_Invoice_{date}.pdf",
                "placeholders": {
                    "account": {"sanitize": True, "fallback": "UNKNOWN"},
                    "number": {"sanitize": True, "fallback": "unknown"},
                    "date": {"fallback": "unknown-date"},
                    "total": {"fallback": "unknown"},
                    "currency": {"fallback": "unknown"},
                },
                "manual_review_for_missing": ["account", "date"],
                "report_columns": {
                    "account": "Client Ref.",
                    "account_id": "Account ID",
                    "date": "PDF Invoice Date",
                    "number": "PDF Invoice No.",
                    "currency": "Topped Currency",
                    "total": "Topped amount",
                    "platform": "Platform",
                },
            }
        },
        "rclone": {
            "enabled": False,
            "remote": "mydrive-shared",
            "source_drive_folder": "InvoicesRAW",
            "destination_drive_folder": "Invoices",
            "destination_subfolder_template": None,
            "archive_drive_folder": None,
        },
        "reports": {
            "enabled": True,
            "filename_template": "parsed_fields_{timestamp}.csv",
        },
        "google_sheets": {
            "enabled": False,
            "spreadsheet_url": None,
            "service_account_file": "keys/test.json",
            "tab_name_template": "%b %Y",
            "date_format": "%d/%m/%Y",
            "skip_existing_by": "number",
        },
    }), encoding="utf-8")

    (tmp_path / "data" / "incoming").mkdir(parents=True)
    (tmp_path / "data" / "outgoing").mkdir(parents=True)

    monkeypatch.setenv("INVOICE_UI_CONFIG_PATH", str(config_path))

    app = create_app()
    with TestClient(app) as client:
        yield client


def test_config_read_write(ui_client):
    res = ui_client.get("/api/config")
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert cfg["date_format"] == "%Y%m%d"
    assert "document_types" in cfg

    cfg["date_format"] = "%Y-%m-%d"
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200
    assert res.json()["config"]["date_format"] == "%Y-%m-%d"
    assert "document_types" in res.json()["config"]


def test_config_load_from_env_when_file_missing(monkeypatch, tmp_path):
    from invoice_parser.config_loader import APP_CONFIG_ENV
    from invoice_ui.services.config_service import ConfigService

    env_config = {
        "source_folder": "data",
        "input_folder": "data/incoming",
        "output_folder": "data/outgoing",
        "archive_folder": "data/archive",
        "default_document_type": "google_ads",
        "document_types": {
            "google_ads": {"classifier": {"patterns": ["Invoice"]}, "fields": {}, "placeholders": {}, "manual_review_for_missing": [], "report_columns": {}},
            "facebook": {"classifier": {"patterns": ["Invoice #"]}, "fields": {}, "placeholders": {}, "manual_review_for_missing": [], "report_columns": {}},
        },
        "rclone": {"enabled": True, "remote": "mydrive-service", "source_drive_folder": "GA", "destination_drive_folder": "GA Out", "destination_subfolder_template": "{year}{month}", "archive_drive_folder": None},
        "reports": {"enabled": True, "filename_template": "parsed_fields_{timestamp}.csv"},
        "google_sheets": {"enabled": True, "spreadsheet_url": "https://docs.google.com/spreadsheets/d/ABC/edit", "service_account_file": "keys/file.json", "tab_name_template": "%b %Y", "date_format": "%d/%m/%Y", "skip_existing_by": "number", "raw_sheet_suffix": " [Auto]", "protect_raw_sheets": True},
        "platforms": {
            "facebook": {
                "rclone": {"source_drive_folder": "META", "destination_drive_folder": "META Out"},
                "google_sheets": {"spreadsheet_url": "https://docs.google.com/spreadsheets/d/DEF/edit"},
            }
        },
    }
    monkeypatch.setenv(APP_CONFIG_ENV, json.dumps(env_config))
    missing_path = tmp_path / "local" / "local_config.json"
    assert not missing_path.exists()

    loaded = ConfigService(missing_path).load()
    assert loaded["default_document_type"] == "google_ads"
    assert set(loaded["document_types"]) == {"google_ads", "facebook"}
    assert loaded["platforms"]["facebook"]["rclone"]["source_drive_folder"] == "META"


def test_config_round_trip_preserves_document_types(ui_client, tmp_path):
    res = ui_client.get("/api/config")
    assert res.status_code == 200
    cfg = res.json()["config"]

    cfg["document_types"]["testtype"] = {
        "classifier": {"patterns": ["Test"]},
        "fields": {},
        "filename_template": "{number}.pdf",
        "placeholders": {},
        "manual_review_for_missing": [],
        "report_columns": {},
    }
    cfg["default_document_type"] = "testtype"

    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200
    saved = res.json()["config"]
    assert "testtype" in saved["document_types"]
    assert saved["default_document_type"] == "testtype"
    assert saved["document_types"]["testtype"]["filename_template"] == "{number}.pdf"

    # Paths saved back should be relative
    assert not Path(saved["source_folder"]).is_absolute()
    assert not Path(saved["google_sheets"]["service_account_file"]).is_absolute()

    # Default google_ads report columns should be preserved
    google_ads = saved["document_types"]["google_ads"]
    assert google_ads["report_columns"]["account"] == "Client Ref."
    assert google_ads["report_columns"]["total"] == "Topped amount"


def test_config_round_trip_preserves_report_columns(ui_client):
    res = ui_client.get("/api/config")
    assert res.status_code == 200
    cfg = res.json()["config"]

    cfg["document_types"]["google_ads"]["report_columns"] = {
        "number": "Client Ref.",
        "account": "Invoice No.",
        "date": "Invoice Date",
        "total": "Topped amount",
        "currency": "Topped Currency",
    }

    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200
    saved = res.json()["config"]
    report_columns = saved["document_types"]["google_ads"]["report_columns"]
    assert report_columns["number"] == "Client Ref."
    assert report_columns["account"] == "Invoice No."
    assert report_columns["date"] == "Invoice Date"
    assert report_columns["total"] == "Topped amount"
    assert report_columns["currency"] == "Topped Currency"
    assert "Client Ref." in report_columns.values()
    assert "Invoice No." in report_columns.values()


def test_config_validation_rejects_invalid(ui_client):
    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["source_folder"] = None
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 422


def test_files_list(ui_client, tmp_path):
    incoming = tmp_path / "data" / "incoming"
    (incoming / "test.pdf").write_bytes(b"dummy")
    outgoing = tmp_path / "data" / "outgoing"
    (outgoing / "done.pdf").write_bytes(b"dummy")

    res = ui_client.get("/api/files")
    assert res.status_code == 200
    files = res.json()
    assert len(files) == 2
    names = {f["name"] for f in files}
    assert names == {"test.pdf", "done.pdf"}
    folders = {f["folder"] for f in files}
    assert folders == {"incoming", "outgoing"}


def test_download_file(ui_client, tmp_path):
    incoming = tmp_path / "data" / "incoming"
    (incoming / "download_me.pdf").write_bytes(b"pdf-content")

    res = ui_client.get("/files/incoming/download_me.pdf")
    assert res.status_code == 200
    assert res.content == b"pdf-content"

    res = ui_client.get("/files/outgoing/missing.pdf")
    assert res.status_code == 200
    assert res.json() == {"error": "File not found"}



def test_preview_empty(ui_client):
    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200
    data = res.json()
    assert data["results"] == []


def test_logs_empty(ui_client):
    res = ui_client.get("/api/logs")
    assert res.status_code == 200
    assert res.json() == []


def test_static_index(ui_client):
    res = ui_client.get("/")
    assert res.status_code == 200
    assert "Invoice Parser" in res.text


def test_sync_status(ui_client):
    res = ui_client.get("/api/sync/status")
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is False
    assert data["remote"] == "mydrive-shared"
    assert data["source_drive_folder"] == "InvoicesRAW"
    assert data["destination_drive_folder"] == "Invoices"
    assert data["archive_drive_folder"] is None


def test_sync_disabled_returns_error(ui_client):
    res = ui_client.post("/api/sync/incoming")
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "disabled" in res.json()["error"].lower()


def test_sync_archive_not_configured(ui_client):
    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["rclone"]["enabled"] = True
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200

    res = ui_client.post("/api/sync/archive")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "disabled" in res.json()["message"].lower()


def test_sync_archive_empty_string_disabled(ui_client):
    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["rclone"]["enabled"] = True
    cfg["rclone"]["archive_drive_folder"] = ""
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200

    res = ui_client.post("/api/sync/archive")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "disabled" in res.json()["message"].lower()


def test_sync_clear_input_no_state(ui_client):
    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["rclone"]["enabled"] = True
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200

    res = ui_client.post("/api/sync/clear-input")
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "no successful run" in res.json()["error"].lower()


def test_write_report_requires_preview(ui_client):
    res = ui_client.post("/api/sheets/write")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "rename" in data["error"].lower()


def test_write_report_requires_rename(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200

    res = ui_client.post("/api/sheets/write")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "rename" in data["error"].lower()

    res = ui_client.post("/api/sheets/write", json={"overwrite": True})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "rename" in data["error"].lower()

    res = ui_client.post("/api/parse/run", json={"dry_run": False})
    assert res.status_code == 200
    assert res.json()["success"] is True

    res = ui_client.post("/api/sheets/write")
    assert res.status_code == 200
    data = res.json()
    assert data["skipped"] is True
    assert "disabled" in data["message"].lower()


def test_write_report_disabled_by_default(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200

    res = ui_client.post("/api/parse/run", json={"dry_run": False})
    assert res.status_code == 200
    assert res.json()["success"] is True

    res = ui_client.post("/api/sheets/write")
    assert res.status_code == 200
    data = res.json()
    assert data["skipped"] is True
    assert "disabled" in data["message"].lower()


def test_download_csv_requires_preview(ui_client):
    res = ui_client.post("/api/reports/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.content.decode("utf-8-sig")
    assert "Client Ref." in content


def test_download_csv_after_preview(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200

    res = ui_client.post("/api/reports/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "parsed_fields_" in res.headers["content-disposition"]
    assert ".csv" in res.headers["content-disposition"]

    content = res.content.decode("utf-8-sig")
    assert "Client Ref." in content
    assert "Test Client" in content
    assert "HKD" in content
    assert "9999.99" in content
    assert "Invoice No." in content
    assert "5561278890" not in content
    assert "Invoice Type" in content
    assert "google_ads" in content
    lines = [
        [cell.strip().strip('"') for cell in line.split(",")]
        for line in content.strip().splitlines()
    ]
    header = lines[0]
    data_row = lines[1]
    assert data_row[header.index("Platform")] == "google_ads"
    assert data_row[header.index("Account ID")] == "12345"


def test_preview_parses_account_id_separately(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    fields = data["results"][0]["fields"]
    assert fields["account"] == "Test Client"
    assert fields["account_id"] == "12345"


def test_preview_parses_accounts_breakdown(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Invoice number: 5565701224
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
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    fields = data["results"][0]["fields"]
    assert fields["account"] == "HKCT - Brand"
    assert fields["account_id"] == "8021550535"
    import json
    records = json.loads(fields["accounts"])
    assert records == [
        {"account": "HKCT - Brand", "account_id": "8021550535", "amount": "804.21"},
        {"account": "HKCT - CIE", "account_id": "7511909696", "amount": "18813.00"},
    ]


def test_accounts_endpoint_returns_aggregated_records(ui_client, tmp_path, monkeypatch):
    archive = tmp_path / "data" / "archive"
    archive.mkdir(parents=True)
    (archive / "5565701224.pdf").write_bytes(b"%PDF-1.4 dummy")
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "last_run_processed.json").write_text(
        json.dumps({"processed": ["5565701224.pdf"]}), encoding="utf-8"
    )

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Invoice number: 5565701224
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
""")

    res = ui_client.get("/api/accounts")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    by_id = {r["account_id"]: r for r in data["records"]}
    assert by_id["8021550535"]["account"] == "HKCT - Brand"
    assert by_id["8021550535"]["amount"] == "804.21"
    assert by_id["8021550535"]["invoices"][0]["date"] == "2026-04-30"


def test_accounts_endpoint_latest_run_excludes_prior_and_scope_all(ui_client, tmp_path, monkeypatch):
    archive = tmp_path / "data" / "archive"
    archive.mkdir(parents=True)
    (archive / "a.pdf").write_bytes(b"%PDF-1.4 dummy")
    (archive / "b.pdf").write_bytes(b"%PDF-1.4 dummy")
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "last_run_processed.json").write_text(
        json.dumps({"processed": ["a.pdf"]}), encoding="utf-8"
    )

    base = """Invoice number: 5561278890
Invoice date: 30 April 2026
Total amount due in HKD
HK$18,995.38
HK$0.00
HK$18,995.38
Account: Intertextile Shanghai [Monthly Invoicing]
Account ID: 180-983-1993
Account budget: Monthly Invoicing
"""
    texts = {
        "a.pdf": base,
        "b.pdf": base.replace("5561278890", "9999999999").replace("Intertextile Shanghai", "Other Client").replace("180-983-1993", "200-000-0000"),
    }
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda p: texts[p.name])

    latest = ui_client.get("/api/accounts").json()
    assert latest["count"] == 1
    assert latest["records"][0]["account_id"] == "1809831993"

    all_data = ui_client.get("/api/accounts?scope=all").json()
    assert all_data["count"] == 2
    assert {r["account_id"] for r in all_data["records"]} == {"1809831993", "2000000000"}


def test_accounts_endpoint_no_state_returns_empty(ui_client, tmp_path, monkeypatch):
    archive = tmp_path / "data" / "archive"
    archive.mkdir(parents=True)
    (archive / "a.pdf").write_bytes(b"%PDF-1.4 dummy")
    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _p: "irrelevant")

    res = ui_client.get("/api/accounts")
    assert res.status_code == 200
    assert res.json() == {"records": [], "count": 0, "errors": 0}


def test_download_csv_uses_alternate_report_columns(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Jane Doe
Invoice number: R-001
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 500.00
""")

    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["document_types"] = {
        "google_ads": {
            "classifier": {"patterns": ["Invoice"]},
            "fields": {},
            "filename_template": "{account}_{number}_Invoice_{date}.pdf",
            "placeholders": {},
            "manual_review_for_missing": [],
            "report_columns": {
                "number": "Client Ref.",
                "account": "Invoice No.",
                "date": "Invoice Date",
                "total": "Topped amount",
                "currency": "Topped Currency",
            },
        }
    }
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1

    res = ui_client.post("/api/parse/update", json={
        "source_name": "test.pdf",
        "fields": {"number": "R-001", "account": "Jane Doe"},
    })
    assert res.status_code == 200

    res = ui_client.post("/api/reports/export")
    assert res.status_code == 200
    content = res.content.decode("utf-8-sig")
    lines = content.strip().split("\n")
    header = lines[0].split(",")
    data_row = lines[1].split(",")
    client_ref_idx = header.index("Client Ref.")
    invoice_no_idx = header.index("Invoice No.")
    assert data_row[client_ref_idx] == "R-001"
    assert data_row[invoice_no_idx] == "Jane Doe"


def test_parse_update_recomputes_target_and_status(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert data["results"][0]["target_name"] == "Test_Client_5561278890_Invoice_20240415.pdf"

    res = ui_client.post("/api/parse/update", json={
        "source_name": "test.pdf",
        "fields": {"account": "Updated Account"},
    })
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert data["results"][0]["target_name"] == "Updated_Account_5561278890_Invoice_20240415.pdf"


def test_run_uses_preview_results(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: """Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
""")

    res = ui_client.post("/api/parse/preview")
    assert res.status_code == 200

    res = ui_client.post("/api/parse/update", json={
        "source_name": "test.pdf",
        "fields": {"account": "Edited Account"},
    })
    assert res.status_code == 200

    res = ui_client.post("/api/parse/run", json={"dry_run": False})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    assert (tmp_path / "data" / "outgoing" / "Edited_Account_5561278890_Invoice_20240415.pdf").exists()
    assert not pdf.exists()


def test_clear_incoming_deletes_local_files(ui_client, tmp_path):
    pdf = tmp_path / "data" / "incoming" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    res = ui_client.post("/api/files/clear-incoming")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["deleted"] == 1
    assert not pdf.exists()


def test_clear_incoming_when_folder_empty(ui_client, tmp_path):
    res = ui_client.post("/api/files/clear-incoming")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["deleted"] == 0


def test_clear_outgoing_deletes_local_files(ui_client, tmp_path):
    pdf = tmp_path / "data" / "outgoing" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    meta = tmp_path / "data" / "outgoing" / "test.pdf.meta.json"
    meta.write_text("{}", encoding="utf-8")

    res = ui_client.post("/api/files/clear-outgoing")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["deleted"] == 2
    assert not pdf.exists()
    assert not meta.exists()


def test_clear_outgoing_when_folder_empty(ui_client, tmp_path):
    res = ui_client.post("/api/files/clear-outgoing")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["deleted"] == 0



