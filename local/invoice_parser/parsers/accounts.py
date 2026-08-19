import json
import re
from typing import Optional

from invoice_parser.config import AccountsParserConfig

_TABLE_ID_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
_TABLE_ID_PART_RE = re.compile(r"^\d{3}-\d{3}-$")
_TABLE_ID_TAIL_RE = re.compile(r"^\d{3,4}$")
_TABLE_AMOUNT_RE = re.compile(r"^-?[\d,]+\.\d{2}$")


def parse_accounts(text: str, config: AccountsParserConfig) -> Optional[str]:
    records = _parse_summary_table(text, config)
    if records is None:
        records = _parse_single_account(text, config)
    if not records:
        return None
    return json.dumps(records)


def _parse_summary_table(text: str, config: AccountsParserConfig) -> Optional[list[dict]]:
    lines = text.splitlines()
    marker_re = re.compile(config.summary_marker_regex, re.IGNORECASE)
    amount_header_re = re.compile(config.amount_header_regex, re.IGNORECASE)

    marker_idx = next((i for i, line in enumerate(lines) if marker_re.search(line)), None)
    if marker_idx is None:
        return None

    j = marker_idx + 1
    while j < len(lines) and not amount_header_re.match(lines[j].strip()):
        j += 1
    if j >= len(lines):
        return None
    j += 1

    rows: list[dict] = []
    current: Optional[dict] = None

    def _finalize() -> None:
        nonlocal current
        if current is None:
            return
        row_lines = current["lines"]
        amount = None
        for line in reversed(row_lines):
            if _TABLE_AMOUNT_RE.match(line):
                amount = line.replace(",", "")
                break
        name_parts = []
        for line in row_lines:
            name_parts.append(line)
            if "]" in line or len(name_parts) >= config.name_max_lines:
                break
        name = re.sub(r"\s*\[.*$", "", " ".join(x.strip() for x in name_parts).strip())
        rows.append({
            "account": name,
            "account_id": current["id"],
            "amount": amount or "",
        })
        current = None

    while j < len(lines):
        stripped = lines[j].strip()
        if re.fullmatch(r"Tax Invoice", stripped, re.IGNORECASE):
            break
        if _TABLE_ID_RE.match(stripped) or _TABLE_ID_PART_RE.match(stripped):
            _finalize()
            current = {"id": stripped, "lines": []}
        elif current is not None:
            if current["lines"] == [] and _TABLE_ID_TAIL_RE.match(stripped) and current["id"].endswith("-"):
                current["id"] = current["id"] + stripped
            else:
                current["lines"].append(stripped)
        j += 1
    _finalize()

    if not rows:
        return None

    aggregated: dict[str, dict] = {}
    for row in rows:
        account_id = row["account_id"]
        if account_id not in aggregated:
            aggregated[account_id] = {"account": row["account"], "amount": 0.0}
        try:
            aggregated[account_id]["amount"] += float(row["amount"]) if row["amount"] else 0.0
        except ValueError:
            pass

    return [
        {
            "account": record["account"],
            "account_id": account_id,
            "amount": f"{record['amount']:.2f}",
        }
        for account_id, record in aggregated.items()
    ]


def _parse_single_account(text: str, config: AccountsParserConfig) -> Optional[list[dict]]:
    lines = text.splitlines()
    account_re = re.compile(config.account_line_regex, re.IGNORECASE)
    account_id_re = re.compile(config.account_id_line_regex, re.IGNORECASE)

    for idx, line in enumerate(lines):
        match = account_re.search(line)
        if not match:
            continue
        account = match.group(1).strip()
        account_id = _extract_account_id(lines, idx, account_id_re, config)
        if not account or not account_id:
            continue
        amount = _extract_invoice_total(text, config) or ""
        return [{"account": account, "account_id": account_id, "amount": amount}]
    return None


def _extract_account_id(lines: list[str], idx: int, account_id_re: re.Pattern, config: AccountsParserConfig) -> Optional[str]:
    start = max(0, idx - config.id_lookahead)
    for i in range(idx - 1, start - 1, -1):
        match = account_id_re.search(lines[i])
        if match:
            return match.group(1).strip()
    end = min(len(lines), idx + 1 + config.id_lookahead)
    for i in range(idx + 1, end):
        match = account_id_re.search(lines[i])
        if match:
            return match.group(1).strip()
    return None


def _extract_invoice_total(text: str, config: AccountsParserConfig) -> Optional[str]:
    total_re = re.compile(config.total_label_regex, re.IGNORECASE)
    amount_re = re.compile(config.amount_regex, re.IGNORECASE)
    match = total_re.search(text)
    if not match:
        return None
    for line in text[match.end():match.end() + 300].splitlines():
        amount = _parse_amount(line, amount_re)
        if amount is not None:
            return amount
    return None


def _parse_amount(line: str, amount_re: re.Pattern) -> Optional[str]:
    match = amount_re.search(line)
    if not match:
        return None
    sign = match.group(1) or ""
    value = match.group(2) or ""
    value = value.replace(",", "")
    if value.startswith("-"):
        sign = ""
    return sign + value
