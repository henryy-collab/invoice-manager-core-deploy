from typing import Optional

from invoice_parser.config import AccountParserConfig
from invoice_parser.parsers.base import _run_patterns


def parse_account(text: str, config: AccountParserConfig) -> Optional[str]:
    return _run_patterns(text, config.patterns)


def normalize_account(value: Optional[str], config: AccountParserConfig) -> str:
    if not value:
        return config.fallback
    value = value.strip()
    if value in set(config.unknown_values):
        return config.fallback
    return value
