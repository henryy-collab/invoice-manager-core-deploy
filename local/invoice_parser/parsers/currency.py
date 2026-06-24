import re
from typing import Optional

from invoice_parser.config import CurrencyParserConfig


def parse_currency(text: str, config: CurrencyParserConfig) -> Optional[str]:
    primary = re.compile(config.primary_regex, re.IGNORECASE)
    match = primary.search(text)
    if match:
        return match.group(1).upper()

    for symbol, code in config.symbol_map.items():
        if symbol in text:
            return code

    return None
