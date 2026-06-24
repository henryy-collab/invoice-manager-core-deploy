import re
from datetime import datetime
from typing import Optional

from invoice_parser.config import RegexPattern


def _compile_flags(flag_names: list[str]) -> int:
    flags = 0
    for name in flag_names:
        flag = getattr(re, name.upper(), None)
        if flag is None:
            raise ValueError(f"Unknown regex flag: {name}")
        flags |= flag
    return flags


def _run_pattern(text: str, pattern: RegexPattern) -> Optional[str]:
    compiled = re.compile(pattern.regex, _compile_flags(pattern.flags))
    match = compiled.search(text)
    if not match:
        return None
    if pattern.group <= len(match.groups()):
        return match.group(pattern.group).strip()
    return None


def _run_patterns(text: str, patterns: list[RegexPattern]) -> Optional[str]:
    for pattern in patterns:
        value = _run_pattern(text, pattern)
        if value:
            return value
    return None


def parse_date(date_str: str, fmt: str, parse_formats: list[str]) -> Optional[str]:
    date_str = date_str.strip().replace(",", "")
    for parse_fmt in parse_formats:
        try:
            dt = datetime.strptime(date_str, parse_fmt)
            return dt.strftime(fmt)
        except ValueError:
            continue
    return None
