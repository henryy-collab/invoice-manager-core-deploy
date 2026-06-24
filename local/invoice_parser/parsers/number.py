import re
from typing import Optional

from invoice_parser.config import NumberParserConfig
from invoice_parser.parsers.base import _run_patterns


def parse_number(text: str, filename_stem: str, config: NumberParserConfig) -> Optional[str]:
    value = _run_patterns(text, config.patterns)
    if value:
        raw = value.strip().upper()
        if not config.require_digit or re.search(r"\d", raw):
            return raw

    if config.fallback_to_filename and re.fullmatch(config.filename_pattern, filename_stem):
        return filename_stem

    return None
