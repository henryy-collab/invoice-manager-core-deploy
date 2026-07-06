import re
from typing import Optional

from invoice_parser.config import TotalParserConfig


_AMOUNT_RE = re.compile(r"(-?)(?:HK\$|US\$|\$|€|£|¥|SGD|HKD|USD|AUD|GBP|EUR|JPY)?\s*(-?[\d,]+\.\d{2})", re.IGNORECASE)
_HEADER_RE = re.compile(r"(Total\s*amount\s*due\s*in|Total\s+in)\s+([A-Z]{3})", re.IGNORECASE)


def _extract_amount(match: re.Match) -> str:
    sign = ""
    value = ""
    # Inspect groups from left to right: first look for a sign, then the numeric amount.
    for i in range(1, (match.lastindex or 0) + 1):
        group = match.group(i)
        if group is None:
            continue
        if "-" in group:
            sign = "-"
        if re.search(r"\d", group):
            value = group.replace(",", "")

    # Also detect a leading minus before the currency symbol in the full match.
    full_match = match.group(0)
    if full_match.lstrip().startswith("-") and not value.lstrip().startswith("-"):
        sign = "-"

    # Avoid double negative
    if value.startswith("-"):
        sign = ""

    return sign + value


def _parse_amount_from_text(text: str) -> Optional[str]:
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    return _extract_amount(match)


def _parse_total_header_block(text: str) -> Optional[str]:
    """Look for 'Total amount due in <CURRENCY>' / 'Total in <CURRENCY>' and return the last amount in the following block."""
    header_match = _HEADER_RE.search(text)
    if not header_match:
        return None

    # Slice text starting from the end of the header
    start = header_match.end()
    block = text[start:start + 1200]

    amounts: list[str] = []
    lines = block.splitlines()
    for line in lines[:8]:
        stripped = line.strip()
        if not stripped:
            continue
        amount = _parse_amount_from_text(stripped)
        if amount is not None:
            amounts.append(amount)
        elif re.search(r"[A-Za-z]{3,}", stripped) and amounts:
            # Non-amount line after we've started collecting means the block is ending
            break

    return amounts[-1] if amounts else None


def parse_total(text: str, config: TotalParserConfig) -> Optional[str]:
    # Prefer the structured header block because PDF column layouts often reorder lines.
    header_total = _parse_total_header_block(text)
    if header_total is not None:
        return header_total

    primary_regexes = list(config.primary_regexes or [])
    if config.primary_regex:
        primary_regexes.insert(0, config.primary_regex)

    for pattern in primary_regexes:
        if not pattern:
            continue
        match = re.compile(pattern, re.IGNORECASE).search(text)
        if match:
            return _extract_amount(match)

    fallback = re.compile(config.fallback_regex)
    amounts = fallback.findall(text)
    if amounts:
        cleaned = []
        for amount in amounts:
            # findall may return a tuple if the regex has multiple groups
            if isinstance(amount, tuple):
                parts = [p for p in amount if p]
                value = parts[-1].replace(",", "") if parts else ""
                sign = "-" if any("-" in p for p in parts[:-1]) else ""
                if value.startswith("-"):
                    sign = ""
                cleaned.append(sign + value)
            else:
                cleaned.append(amount.replace(",", ""))
        if config.pick_max:
            return max(cleaned, key=lambda x: float(x))
        return cleaned[0]

    return None
