from invoice_parser.config import AppConfig
from invoice_parser.models import Invoice
from invoice_parser.parsers.account import normalize_account, parse_account
from invoice_parser.parsers.currency import parse_currency
from invoice_parser.parsers.date import parse_date_field
from invoice_parser.parsers.number import parse_number
from invoice_parser.parsers.total import parse_total


def parse_invoice(text: str, filename_stem: str, config: AppConfig) -> Invoice:
    parsers = config.parsers
    return Invoice(
        account=parse_account(text, parsers.account),
        number=parse_number(text, filename_stem, parsers.number),
        date=parse_date_field(text, config.date_format, parsers.date),
        currency=parse_currency(text, parsers.currency),
        total=parse_total(text, parsers.total),
    )


def missing_required_fields(
    invoice: Invoice, required: list[str], account_config
) -> list[str]:
    missing = []
    for field in required:
        value = getattr(invoice, field)
        if field == "account":
            value = normalize_account(value, account_config)
            if value == account_config.fallback:
                missing.append(field)
        elif not value:
            missing.append(field)
    return missing
