import logging

from invoice_parser.config import AppConfig
from invoice_parser.processor import process_pdfs


def _make_text():
    return """
Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
"""


def test_processor_renames_and_archives(tmp_path, monkeypatch):
    config_dict = {
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "inbox"),
        "output_folder": str(tmp_path / "outbox"),
        "archive_folder": str(tmp_path / "archive"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    }
    config = AppConfig.model_validate(config_dict)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()

    pdf = inbox / "5561278890.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr(
        "invoice_parser.processor.extract_text", lambda _path: _make_text()
    )

    logger = logging.getLogger("test_processor")
    process_pdfs(config, logger)

    assert (outbox / "Test_Client_5561278890_Invoice_20240415.pdf").exists()
    assert (tmp_path / "archive" / "5561278890.pdf").exists()


def test_processor_manual_review_for_missing_fields(tmp_path, monkeypatch):
    config_dict = {
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "inbox"),
        "output_folder": str(tmp_path / "outbox"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    }
    config = AppConfig.model_validate(config_dict)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()

    pdf = inbox / "missing.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr("invoice_parser.processor.extract_text", lambda _path: "No data")

    logger = logging.getLogger("test_processor_missing")
    process_pdfs(config, logger)

    assert (outbox / "000_missing.pdf").exists()


def test_processor_dry_run_does_not_modify(tmp_path, monkeypatch):
    config_dict = {
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "inbox"),
        "output_folder": str(tmp_path / "outbox"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
        "features": {"dry_run": True},
    }
    config = AppConfig.model_validate(config_dict)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()

    pdf = inbox / "5561278890.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr(
        "invoice_parser.processor.extract_text", lambda _path: _make_text()
    )

    logger = logging.getLogger("test_processor_dry")
    process_pdfs(config, logger)

    assert not (outbox / "Test_Client_5561278890_Invoice_20240415.pdf").exists()
    assert not (tmp_path / "archive").exists()


def test_processor_skip_already_processed(tmp_path, monkeypatch):
    config_dict = {
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "inbox"),
        "output_folder": str(tmp_path / "outbox"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    }
    config = AppConfig.model_validate(config_dict)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()

    pdf = inbox / "Test_Client_5561278890_Invoice_20240415.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr(
        "invoice_parser.processor.extract_text", lambda _path: _make_text()
    )

    logger = logging.getLogger("test_processor_skip")
    process_pdfs(config, logger)

    # Should remain the only file (no new renamed file created)
    assert list(inbox.glob("*.pdf")) == [pdf]


def test_processor_cleanup_after_processing(tmp_path, monkeypatch):
    config_dict = {
        "source_folder": str(tmp_path),
        "input_folder": str(tmp_path / "inbox"),
        "output_folder": str(tmp_path / "outbox"),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    }
    config = AppConfig.model_validate(config_dict)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()

    pdf = inbox / "5561278890.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr(
        "invoice_parser.processor.extract_text", lambda _path: _make_text()
    )

    logger = logging.getLogger("test_processor_cleanup")
    process_pdfs(config, logger)

    assert (outbox / "Test_Client_5561278890_Invoice_20240415.pdf").exists()
    assert not (inbox / "5561278890.pdf").exists()
