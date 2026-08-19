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


def test_parse_account_bracketed_returns_name_only(sample_config):
    assert parse_account("Account: Test Client [12345]", sample_config.parsers.account) == "Test Client"


def test_parse_account_id_bracketed(sample_config):
    assert parse_account("Account: Test Client [12345]", sample_config.parsers.account_id) == "12345"


def test_parse_account_id_explicit_line(sample_config):
    assert parse_account("Account ID: 12345", sample_config.parsers.account_id) == "12345"


def test_parse_account_id_missing(sample_config):
    assert parse_account("Account: ACME Inc", sample_config.parsers.account_id) is None


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


def test_parse_total_primary_regexes(sample_text, sample_config):
    sample_config.parsers.total.primary_regex = ""
    sample_config.parsers.total.primary_regexes = [
        r"Total\s*amount\s*due(?:\s*in\s*[A-Z]{3})?[:\s]*([A-Z$€£¥]*)\s*(-?[\d,]+\.\d{2})",
    ]
    assert parse_total(sample_text, sample_config.parsers.total) == "12345.67"


def test_parse_total_negative_amount(sample_config):
    sample_config.parsers.total.primary_regex = ""
    sample_config.parsers.total.primary_regexes = [
        r"Total\s+in\s+[A-Z]{3}[:\s]*(-?)([A-Z$€£¥]*)\s*(-?[\d,]+\.\d{2})",
    ]
    sample_config.parsers.total.fallback_regex = r"(-?)(?:HK\$|US\$|\$|€|£|¥)\s*(-?[\d,]+\.\d{2})"
    assert parse_total("Total in HKD\n-HK$40.83", sample_config.parsers.total) == "-40.83"


def test_parse_total_fallback_negative_amount(sample_config):
    sample_config.parsers.total.primary_regex = ""
    sample_config.parsers.total.primary_regexes = []
    sample_config.parsers.total.fallback_regex = r"(-?)(?:HK\$|US\$|\$|€|£|¥)\s*(-?[\d,]+\.\d{2})"
    assert parse_total("Credit note -HK$40.83", sample_config.parsers.total) == "-40.83"


def test_parse_total_fallback_max(sample_config):
    sample_config.parsers.total.pick_max = True
    assert parse_total("US\$ 10.00 US\$ 99.99", sample_config.parsers.total) == "99.99"


def test_parse_total_header_block_returns_last_amount(sample_config):
    text = """
Total amount due in SGD
SGD 31,278.03
SGD 0.00
SGD 5.87
SGD 0.00
SGD 31,283.90
Summary for 1 Jun 2026 - 30 Jun 2026
"""
    assert parse_total(text, sample_config.parsers.total) == "31283.90"


def test_parse_total_header_block_credit_note(sample_config):
    text = """
Total in HKD
-HK$40.83
HK$0.00
-HK$40.83
Summary for 1 Jun 2026 - 8 Jun 2026
"""
    assert parse_total(text, sample_config.parsers.total) == "-40.83"


def test_parse_total_header_block_consolidated_invoice(sample_config):
    text = """
Total amount due in HKD
HK$180,652.13
HK$0.00
HK$180,652.13
Summary for 1 Jun 2026 - 30 Jun 2026
"""
    assert parse_total(text, sample_config.parsers.total) == "180652.13"


def test_parse_total_header_block_ignores_subsequent_non_amount_lines(sample_config):
    text = """
Total amount due in HKD
HK$1,000.00
HK$0.00
HK$1,000.00
Google Asia Pacific Pte. Ltd.
70 Pasir Panjang Road
"""
    assert parse_total(text, sample_config.parsers.total) == "1000.00"


def test_parse_total_falls_back_when_no_header_block(sample_config):
    sample_config.parsers.total.primary_regex = ""
    sample_config.parsers.total.primary_regexes = []
    sample_config.parsers.total.fallback_regex = r"(-?)(?:HK\$|US\$|\$|€|£|¥)\s*(-?[\d,]+\.\d{2})"
    assert parse_total("Credit note -HK$40.83", sample_config.parsers.total) == "-40.83"


def test_parse_invoice(sample_text, sample_config):
    invoice = parse_invoice(sample_text, "12345", sample_config)
    assert invoice.account == "ACME Inc"
    assert invoice.number == "INV-2024-001"
    assert invoice.date == "20240415"
    assert invoice.total == "12345.67"
    assert invoice.currency == "HKD"


def test_parse_invoice_extracts_account_id_separately(sample_config):
    text = """
Account: Test Client [12345]
Invoice number: 5561278890
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 9,999.99
"""
    invoice = parse_invoice(text, "5561278890", sample_config)
    assert invoice.account == "Test Client"
    assert invoice.account_id == "12345"
