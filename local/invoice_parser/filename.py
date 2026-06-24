import re
from pathlib import Path
from typing import Optional

from invoice_parser.config import FilenameConfig, PlaceholderConfig


def sanitize(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\s\/\\:\*\?\"\<\>\|]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _format_placeholder(value: Optional[str], placeholder: PlaceholderConfig) -> str:
    if value is None or value == "":
        return placeholder.fallback
    if placeholder.sanitize:
        return sanitize(value)
    return value


def build_filename(template: str, invoice, config: FilenameConfig) -> str:
    placeholders = {
        "account": _format_placeholder(invoice.account, config.placeholders["account"]),
        "number": _format_placeholder(invoice.number, config.placeholders["number"]),
        "date": _format_placeholder(invoice.date, config.placeholders["date"]),
        "total": _format_placeholder(invoice.total, config.placeholders["total"]),
        "currency": _format_placeholder(invoice.currency, config.placeholders["currency"]),
    }
    result = template
    for key, value in placeholders.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def resolve_unique_name(
    directory: Path,
    name: str,
    used: set[Path],
    prefix: Optional[str] = None,
    suffix_template: str = "_{counter}",
    track: bool = True,
) -> Path:
    candidate = directory / name
    base = candidate.stem
    ext = candidate.suffix

    if prefix:
        base = base[len(prefix):] if base.startswith(prefix) else base
        candidate = directory / f"{prefix}{base}{ext}"

    counter = 1
    while candidate in used or candidate.exists():
        candidate = directory / f"{prefix or ''}{base}{suffix_template.format(counter=counter)}{ext}"
        counter += 1

    if track:
        used.add(candidate)
    return candidate
