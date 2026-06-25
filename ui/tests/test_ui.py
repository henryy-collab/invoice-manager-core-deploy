import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoice_ui.main import create_app


@pytest.fixture
def ui_client(tmp_path, monkeypatch):
    config_path = tmp_path / "local_config.json"
    config_path.write_text(json.dumps({
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "incoming"),
        "output_folder": str(tmp_path / "outgoing"),
        "archive_folder": str(tmp_path / "archive"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
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
            "service_account_file": None,
            "tab_name_template": "%b %Y",
            "date_format": "%d/%m/%Y",
            "skip_existing_by": "number",
        },
    }), encoding="utf-8")

    (tmp_path / "incoming").mkdir()
    (tmp_path / "outgoing").mkdir()

    monkeypatch.setenv("INVOICE_UI_CONFIG_PATH", str(config_path))

    app = create_app()
    with TestClient(app) as client:
        yield client


def test_config_read_write(ui_client):
    res = ui_client.get("/api/config")
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert cfg["date_format"] == "%Y%m%d"

    cfg["date_format"] = "%Y-%m-%d"
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 200
    assert res.json()["config"]["date_format"] == "%Y-%m-%d"


def test_config_validation_rejects_invalid(ui_client):
    res = ui_client.get("/api/config")
    cfg = res.json()["config"]
    cfg["source_folder"] = None
    res = ui_client.post("/api/config", json={"config": cfg})
    assert res.status_code == 422


def test_files_list(ui_client, tmp_path):
    incoming = tmp_path / "incoming"
    (incoming / "test.pdf").write_bytes(b"dummy")
    outgoing = tmp_path / "outgoing"
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
    incoming = tmp_path / "incoming"
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
    assert res.json()["success"] is False
    assert "not configured" in res.json()["error"].lower()


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
    pdf = tmp_path / "incoming" / "test.pdf"
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

    res = ui_client.post("/api/parse/run", json={"dry_run": False})
    assert res.status_code == 200
    assert res.json()["success"] is True

    res = ui_client.post("/api/sheets/write")
    assert res.status_code == 200
    data = res.json()
    assert data["skipped"] is True
    assert "disabled" in data["message"].lower()


def test_write_report_disabled_by_default(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "incoming" / "test.pdf"
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
    pdf = tmp_path / "incoming" / "test.pdf"
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


def test_parse_update_recomputes_target_and_status(ui_client, tmp_path, monkeypatch):
    pdf = tmp_path / "incoming" / "test.pdf"
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
    pdf = tmp_path / "incoming" / "test.pdf"
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

    assert (tmp_path / "outgoing" / "Edited_Account_5561278890_Invoice_20240415.pdf").exists()
    assert not pdf.exists()


def test_clear_incoming_deletes_local_files(ui_client, tmp_path):
    pdf = tmp_path / "incoming" / "test.pdf"
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
    pdf = tmp_path / "outgoing" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    meta = tmp_path / "outgoing" / "test.pdf.meta.json"
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



