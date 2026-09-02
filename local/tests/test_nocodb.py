import json
from pathlib import Path

from invoice_parser.config import AppConfig
from invoice_parser.nocodb import _build_payload, find_meta_files, upload_invoices, upload_from_config


def test_build_payload_maps_fields_and_empty_source():
    fields = {
        "account": "ACME",
        "account_id": "123-456",
        "number": "INV-001",
        "date": "20240101",
        "total": "1234.56",
        "currency": "HKD",
        "document_type": "google_ads",
    }
    column_map = {
        "account": "ad_account_name",
        "account_id": "account_id",
        "number": "pdf_invoice_number",
        "date": "pdf_invoice_date",
        "total": "topped_amount",
        "currency": "currency",
        "source": "source",
        "document_type": "invoice_type",
    }
    payload = _build_payload(fields, column_map)
    assert payload["fields"]["ad_account_name"] == "ACME"
    assert payload["fields"]["account_id"] == "123-456"
    assert payload["fields"]["pdf_invoice_number"] == "INV-001"
    assert payload["fields"]["pdf_invoice_date"] == "20240101"
    assert payload["fields"]["topped_amount"] == "1234.56"
    assert payload["fields"]["currency"] == "HKD"
    assert payload["fields"]["source"] == ""
    assert payload["fields"]["invoice_type"] == "google_ads"


def test_find_meta_files(tmp_path):
    (tmp_path / "a.pdf.meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.pdf").write_bytes(b"%PDF")
    files = find_meta_files(tmp_path)
    assert [f.name for f in files] == ["a.pdf.meta.json"]


def test_upload_invoices_dry_run_requires_token_and_prints(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("NOCODB_TOKEN", "test-token")
    meta = tmp_path / "a.pdf.meta.json"
    meta.write_text(json.dumps({"account": "ACME"}), encoding="utf-8")
    result = upload_invoices([meta], "base1", "table1", {"account": "ad_account_name", "source": "source"}, dry_run=True)
    assert result["uploaded"] == 1
    assert not result["errors"]
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "ad_account_name" in out


def test_upload_invoices_missing_token(monkeypatch, tmp_path):
    monkeypatch.delenv("NOCODB_TOKEN", raising=False)
    meta = tmp_path / "a.pdf.meta.json"
    meta.write_text("{}", encoding="utf-8")
    try:
        upload_invoices([meta], "b1", "t1", {}, dry_run=True)
        raised = False
    except Exception:
        raised = True
    assert raised


def test_upload_from_config_disabled(tmp_path):
    config = AppConfig.model_validate({"source_folder": str(tmp_path)})
    result = upload_from_config(config)
    assert result.get("skipped") is True


def test_upload_from_config_requires_ids(tmp_path, monkeypatch):
    monkeypatch.setenv("NOCODB_TOKEN", "t")
    config = AppConfig.model_validate({
        "source_folder": str(tmp_path),
        "output_folder": str(tmp_path),
        "nocodb": {"enabled": True, "base_id": "", "table_id": ""},
    })
    result = upload_from_config(config)
    assert result["success"] is False