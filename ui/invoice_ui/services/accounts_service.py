import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Request

from invoice_parser.config import AppConfig
from invoice_parser.processor import parse_single_pdf
from invoice_ui.dependencies import get_app_config


class AccountsService:
    def __init__(self, config: AppConfig):
        self.config = config

    @classmethod
    def from_request(cls, request: Request) -> "AccountsService":
        return cls(get_app_config(request))

    def build_records(self, source_dir: Optional[str] = None, scope: str = "latest") -> dict:
        folder = Path(source_dir or self.config.archive_folder)
        aggregated: dict[str, dict] = {}
        errors = 0

        allowed = self._latest_run_files() if scope == "latest" else None

        if folder.is_dir():
            for pdf_path in sorted(folder.glob("*.pdf")):
                if allowed is not None and pdf_path.name not in allowed:
                    continue
                try:
                    result = parse_single_pdf(pdf_path, self.config)
                    self._merge_document(result.document.to_dict(), aggregated)
                except Exception:
                    errors += 1

        records = []
        for rec in aggregated.values():
            records.append({
                "account_id": rec["account_id"],
                "account": rec["account"],
                "amount": f"{rec['amount']:.2f}",
                "invoice_count": len(rec["invoices"]),
                "invoices": rec["invoices"],
            })
        records.sort(key=lambda r: r["account"].lower())

        return {"records": records, "count": len(records), "errors": errors}

    def _latest_run_files(self) -> Optional[set[str]]:
        state_path = Path(self.config.output_folder).parent / "state" / "last_run_processed.json"
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return set()
        return set(data.get("processed") or [])

    def _merge_document(self, fields: dict, aggregated: dict) -> None:
        accounts_raw = fields.get("accounts")
        if not accounts_raw:
            return
        try:
            accounts = json.loads(accounts_raw)
        except (ValueError, TypeError):
            return

        number = fields.get("number")
        date = self._to_iso_date(fields.get("date"))
        currency = fields.get("currency")

        for acc in accounts:
            account_id = acc.get("account_id")
            if not account_id:
                continue
            amount = acc.get("amount")
            rec = aggregated.setdefault(account_id, {
                "account_id": account_id,
                "account": acc.get("account", ""),
                "amount": 0.0,
                "invoices": [],
            })
            if amount:
                try:
                    rec["amount"] += float(amount)
                except ValueError:
                    pass
            rec["invoices"].append({
                "number": number or "",
                "date": date or "",
                "currency": currency or "",
                "amount": amount or "",
            })

    def _to_iso_date(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = str(value).strip()
        formats = [
            self.config.date_format,
            "%Y%m%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d %b %Y",
            "%d %B %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return value
