import re
from typing import Optional

from invoice_parser.config import DateParserConfig
from invoice_parser.parsers.base import parse_date


def _find_details_index(lines: list[str], header: str) -> Optional[int]:
    for i, line in enumerate(lines):
        if re.fullmatch(re.escape(header), line.strip(), re.IGNORECASE):
            return i
    return None


def parse_details_block(lines: list[str], date_fmt: str, config: DateParserConfig) -> Optional[str]:
    details = config.details_block
    if not details.enabled:
        return None

    details_index = _find_details_index(lines, details.header)
    if details_index is None:
        return None

    dot_sep = re.compile(details.dot_separator_regex)
    label_re = re.compile(details.label_regex, re.IGNORECASE)

    values = []
    i = details_index - 1
    while i >= 0:
        line = lines[i].strip()
        if not line:
            i -= 1
            continue
        if dot_sep.match(line):
            if i - 1 >= 0:
                value = lines[i - 1].strip()
                if value and not dot_sep.match(value) and not label_re.search(value):
                    values.append(value)
                i -= 2
                continue
        i -= 1
    values.reverse()

    labels = []
    for line in lines[details_index + 1:]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("-") or line.startswith("*") or len(line) > details.max_label_length:
            continue
        if label_re.search(line):
            labels.append(line)
        elif labels:
            break

    invoice_date_re = re.compile(r"Invoice\s*date", re.IGNORECASE)
    for idx, label in enumerate(labels):
        if invoice_date_re.search(label) and idx < len(values):
            parsed = parse_date(values[idx], date_fmt, config.parse_formats)
            if parsed:
                return parsed

    return None


def parse_date_field(text: str, date_fmt: str, config: DateParserConfig) -> Optional[str]:
    lines = text.splitlines()
    window = config.nearby_line_window
    date_regex = re.compile(
        r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{4})\b"
    )
    invoice_date_re = re.compile(r"Invoice\s*date", re.IGNORECASE)

    for i, line in enumerate(lines):
        if not invoice_date_re.search(line):
            continue
        neighbors = lines[max(0, i - window):min(len(lines), i + window + 1)]
        for candidate in neighbors:
            match = date_regex.search(candidate)
            if match:
                parsed = parse_date(match.group(1), date_fmt, config.parse_formats)
                if parsed:
                    return parsed

    return parse_details_block(lines, date_fmt, config)
