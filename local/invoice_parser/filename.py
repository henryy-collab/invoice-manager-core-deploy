import re
from pathlib import Path
from typing import Optional

from invoice_parser.config import FilenameConfig, PlaceholderConfig
from invoice_parser.models import Document


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


def build_filename(template: str, document: Document, config: FilenameConfig) -> str:
    placeholders = {
        key: _format_placeholder(document.get(key), placeholder_config)
        for key, placeholder_config in config.placeholders.items()
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
