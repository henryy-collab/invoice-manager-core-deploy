from invoice_parser.parsers.account import normalize_account, parse_account
from invoice_parser.parsers.currency import parse_currency
from invoice_parser.parsers.date import parse_date_field
from invoice_parser.parsers.invoice import parse_invoice
from invoice_parser.parsers.number import parse_number
from invoice_parser.parsers.total import parse_total


def test_parse_account(sample_text, sample_config):
    assert parse_account(sample_text, sample_config.parsers.account) == "ACME Inc"


def test_parse_account_returns_none_when_missing(sample_config):
    assert parse_account("No account here", sample_config.parsers.account) is None


def test_normalize_account_known_value(sample_config):
    assert normalize_account("ACME", sample_config.parsers.account) == "ACME"


def test_normalize_account_unknown_value(sample_config):
    assert normalize_account("N/A", sample_config.parsers.account) == "UNKNOWN"


def test_normalize_account_empty(sample_config):
    assert normalize_account(None, sample_config.parsers.account) == "UNKNOWN"


def test_parse_number(sample_text, sample_config):
    assert parse_number(sample_text, "12345", sample_config.parsers.number) == "INV-2024-001"


def test_parse_number_fallback_to_filename(sample_config):
    assert parse_number("No number", "5561278890", sample_config.parsers.number) == "5561278890"


def test_parse_number_no_fallback_when_disabled(sample_config):
    sample_config.parsers.number.fallback_to_filename = False
    assert parse_number("No number", "5561278890", sample_config.parsers.number) is None


def test_parse_date_field(sample_text, sample_config):
    assert parse_date_field(sample_text, "%Y%m%d", sample_config.parsers.date) == "20240415"


def test_parse_date_field_missing(sample_config):
    assert parse_date_field("No dates", "%Y%m%d", sample_config.parsers.date) is None


def test_parse_currency(sample_text, sample_config):
    assert parse_currency(sample_text, sample_config.parsers.currency) == "HKD"


def test_parse_currency_from_symbol(sample_config):
    sample_config.parsers.currency.symbol_map = {"US$": "USD"}
    assert parse_currency("Total US$ 100.00", sample_config.parsers.currency) == "USD"


def test_parse_total(sample_text, sample_config):
    assert parse_total(sample_text, sample_config.parsers.total) == "12345.67"


def test_parse_total_fallback_max(sample_config):
    sample_config.parsers.total.pick_max = True
    assert parse_total("US$ 10.00 US$ 99.99", sample_config.parsers.total) == "99.99"


def test_parse_invoice(sample_text, sample_config):
    invoice = parse_invoice(sample_text, "12345", sample_config)
    assert invoice.account == "ACME Inc"
    assert invoice.number == "INV-2024-001"
    assert invoice.date == "20240415"
    assert invoice.total == "12345.67"
    assert invoice.currency == "HKD"
