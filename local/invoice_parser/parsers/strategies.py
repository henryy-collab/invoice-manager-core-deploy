from typing import Callable, Optional

from invoice_parser.config import AppConfig, FieldConfig
from invoice_parser.parsers.account import normalize_account, parse_account
from invoice_parser.parsers.currency import parse_currency
from invoice_parser.parsers.date import parse_date_field
from invoice_parser.parsers.number import parse_number
from invoice_parser.parsers.total import parse_total


Strategy = Callable[[str, str, str, FieldConfig, AppConfig], Optional[str]]


def _run_account(text: str, _filename_stem: str, _date_format: str, field_config: FieldConfig, _config: AppConfig) -> Optional[str]:
    from invoice_parser.config import AccountParserConfig
    config = AccountParserConfig.model_validate(field_config.model_dump())
    return parse_account(text, config)


def _run_number(text: str, filename_stem: str, _date_format: str, field_config: FieldConfig, _config: AppConfig) -> Optional[str]:
    from invoice_parser.config import NumberParserConfig
    config = NumberParserConfig.model_validate(field_config.model_dump())
    return parse_number(text, filename_stem, config)


def _run_date(text: str, _filename_stem: str, date_format: str, field_config: FieldConfig, _config: AppConfig) -> Optional[str]:
    from invoice_parser.config import DateParserConfig
    config = DateParserConfig.model_validate(field_config.model_dump())
    return parse_date_field(text, date_format, config)


def _run_currency(text: str, _filename_stem: str, _date_format: str, field_config: FieldConfig, _config: AppConfig) -> Optional[str]:
    from invoice_parser.config import CurrencyParserConfig
    config = CurrencyParserConfig.model_validate(field_config.model_dump())
    return parse_currency(text, config)


def _run_total(text: str, _filename_stem: str, _date_format: str, field_config: FieldConfig, _config: AppConfig) -> Optional[str]:
    from invoice_parser.config import TotalParserConfig
    config = TotalParserConfig.model_validate(field_config.model_dump())
    return parse_total(text, config)


STRATEGIES: dict[str, Strategy] = {
    "account": _run_account,
    "number": _run_number,
    "date": _run_date,
    "currency": _run_currency,
    "total": _run_total,
}


def run_strategy(
    strategy_name: str,
    text: str,
    filename_stem: str,
    date_format: str,
    field_config: FieldConfig,
    config: AppConfig,
) -> Optional[str]:
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown parser strategy: {strategy_name}")
    return STRATEGIES[strategy_name](text, filename_stem, date_format, field_config, config)


def normalize_field(value: Optional[str], field_name: str, field_config: FieldConfig) -> Optional[str]:
    if field_name != "account" or value is None:
        return value
    from invoice_parser.config import AccountParserConfig
    config = AccountParserConfig.model_validate(field_config.model_dump())
    normalized = normalize_account(value, config)
    return None if normalized == config.fallback else normalized
