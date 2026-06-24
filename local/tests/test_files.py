import logging

from invoice_parser.files import (
    archive_original,
    cleanup_source,
    is_already_processed,
    missing_required_fields,
    rename_pdf,
)
from invoice_parser.models import Invoice


def test_is_already_processed_matches_patterns():
    patterns = [r"_Invoice_\d{8}\.pdf$", r"^000_"]
    assert is_already_processed("Foo_123_Invoice_20240415.pdf", patterns) is True
    assert is_already_processed("000_original.pdf", patterns) is True
    assert is_already_processed("original.pdf", patterns) is False


def test_missing_required_fields_account_and_date(sample_config):
    invoice = Invoice()
    missing = missing_required_fields(
        invoice, ["account", "date"], sample_config.parsers.account
    )
    assert "account" in missing
    assert "date" in missing


def test_missing_required_fields_account_present(sample_config):
    invoice = Invoice(account="ACME", date="20240415")
    missing = missing_required_fields(
        invoice, ["account", "date"], sample_config.parsers.account
    )
    assert missing == []


def test_archive_original_copies_file(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    archive = tmp_path / "archive"
    pdf = src / "invoice.pdf"
    pdf.write_text("pdf content")

    logger = logging.getLogger("test")
    archive_original(pdf, archive, dry_run=False, logger=logger)

    assert (archive / "invoice.pdf").exists()
    assert (archive / "invoice.pdf").read_text() == "pdf content"


def test_archive_original_dry_run_does_not_create_dir(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    archive = tmp_path / "archive"
    pdf = src / "invoice.pdf"
    pdf.write_text("pdf content")

    logger = logging.getLogger("test")
    archive_original(pdf, archive, dry_run=True, logger=logger)

    assert not archive.exists()


def test_rename_pdf_renames_file(tmp_path):
    src = tmp_path / "old.pdf"
    src.write_text("x")
    target = tmp_path / "new.pdf"

    logger = logging.getLogger("test")
    rename_pdf(src, target, dry_run=False, logger=logger)

    assert target.exists()
    assert not src.exists()


def test_rename_pdf_dry_run_does_not_rename(tmp_path):
    src = tmp_path / "old.pdf"
    src.write_text("x")
    target = tmp_path / "new.pdf"

    logger = logging.getLogger("test")
    rename_pdf(src, target, dry_run=True, logger=logger)

    assert src.exists()
    assert not target.exists()


def test_cleanup_source_removes_file(tmp_path):
    src = tmp_path / "old.pdf"
    src.write_text("x")

    logger = logging.getLogger("test")
    cleanup_source(src, logger)

    assert not src.exists()
