import csv
import io
from dataclasses import dataclass
from datetime import datetime

from invoice_parser.config import AppConfig


@dataclass
class ReportRow:
    client_ref: str = ""
    platform: str = ""
    agreed_amount: str = ""
    invoice_no: str = ""
    amount: str = ""
    invoice_date: str = ""
    paid_date: str = ""
    am: str = ""
    pm: str = ""
    informed_am_pm: str = ""
    top_up_date: str = ""
    topped_currency: str = ""
    topped_amount: str = ""
    balance: str = ""


_COLUMNS = [
    "Client Ref.",
    "Platform",
    "Agreed Amount",
    "Invoice No.",
    "Amount",
    "Invoice Date",
    "Paid Date",
    "AM",
    "PM",
    "Informed AM & PM",
    "Top up date",
    "Topped Currency",
    "Topped amount",
    "Balance",
]


def _result_to_row(result) -> ReportRow:
    fields = result.fields
    return ReportRow(
        client_ref=fields.get("account") or "",
        invoice_date=fields.get("date") or "",
        topped_currency=fields.get("currency") or "",
        topped_amount=fields.get("total") or "",
    )


def _row_to_list(row: ReportRow) -> list[str]:
    return [
        row.client_ref,
        row.platform,
        row.agreed_amount,
        row.invoice_no,
        row.amount,
        row.invoice_date,
        row.paid_date,
        row.am,
        row.pm,
        row.informed_am_pm,
        row.top_up_date,
        row.topped_currency,
        row.topped_amount,
        row.balance,
    ]


def build_report_rows(results: list) -> list[ReportRow]:
    return [_result_to_row(r) for r in results]


def generate_csv_content(results: list) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(_COLUMNS)
    for row in build_report_rows(results):
        writer.writerow(_row_to_list(row))
    return buffer.getvalue()


def build_filename(config: AppConfig, timestamp: datetime | None = None) -> str:
    if timestamp is None:
        timestamp = datetime.now()
    return config.reports.filename_template.format(timestamp=timestamp.strftime("%Y%m%d_%H%M%S"))
