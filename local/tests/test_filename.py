from invoice_parser.filename import (
    build_filename,
    resolve_unique_name,
    sanitize,
)
from invoice_parser.models import Invoice


def test_sanitize_removes_special_chars():
    assert sanitize("ACME Inc / Ltd.") == "ACME_Inc_Ltd."


def test_sanitize_collapses_underscores():
    assert sanitize("ACME   Inc") == "ACME_Inc"


def test_build_filename(sample_invoice, sample_config):
    result = build_filename(
        sample_config.filename_template, sample_invoice, sample_config.filename
    )
    assert result == "ACME_Inc_INV-2024-001_Invoice_20240415.pdf"


def test_build_filename_uses_fallbacks(sample_config):
    invoice = Invoice()
    result = build_filename(
        sample_config.filename_template, invoice, sample_config.filename
    )
    assert result == "UNKNOWN_unknown_Invoice_unknown-date.pdf"


def test_resolve_unique_name_no_collision(tmp_path):
    used = set()
    result = resolve_unique_name(tmp_path, "test.pdf", used)
    assert result == tmp_path / "test.pdf"
    assert result in used


def test_resolve_unique_name_with_collision(tmp_path):
    (tmp_path / "test.pdf").write_text("x")
    used = set()
    result = resolve_unique_name(tmp_path, "test.pdf", used)
    assert result == tmp_path / "test_1.pdf"


def test_resolve_unique_name_with_prefix(tmp_path):
    used = set()
    result = resolve_unique_name(tmp_path, "original.pdf", used, prefix="000_")
    assert result == tmp_path / "000_original.pdf"
