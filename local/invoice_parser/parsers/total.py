import re
from typing import Optional

from invoice_parser.config import TotalParserConfig


def parse_total(text: str, config: TotalParserConfig) -> Optional[str]:
    primary = re.compile(config.primary_regex, re.IGNORECASE)
    match = primary.search(text)
    if match:
        return match.group(2).replace(",", "")

    fallback = re.compile(config.fallback_regex)
    amounts = fallback.findall(text)
    if amounts:
        cleaned = [a.replace(",", "") for a in amounts]
        if config.pick_max:
            return max(cleaned, key=lambda x: float(x))
        return cleaned[0]

    return None
