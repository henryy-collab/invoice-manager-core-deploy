import csv
import io
from dataclasses import dataclass
from datetime import datetime

from invoice_parser.config import AppConfig, DocumentTypeConfig


@dataclass
class ReportRow:
    client_ref: str = ""
    account_id: str = ""
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
    invoice_type: str = ""


_COLUMNS = [
    "Client Ref.",
    "Account ID",
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
    "Invoice Type",
]


_COLUMN_TO_ATTR = {
    "Client Ref.": "client_ref",
    "Account ID": "account_id",
    "Platform": "platform",
    "Agreed Amount": "agreed_amount",
    "Invoice No.": "invoice_no",
    "Amount": "amount",
    "Invoice Date": "invoice_date",
    "Paid Date": "paid_date",
    "AM": "am",
    "PM": "pm",
    "Informed AM & PM": "informed_am_pm",
    "Top up date": "top_up_date",
    "Topped Currency": "topped_currency",
    "Topped amount": "topped_amount",
    "Balance": "balance",
    "Invoice Type": "invoice_type",
}


def _result_to_row(result, type_config: DocumentTypeConfig) -> ReportRow:
    row = ReportRow()
    fields = result.fields
    column_to_field = {column: field for field, column in type_config.report_columns.items()}
    for column, attr in _COLUMN_TO_ATTR.items():
        field = column_to_field.get(column)
        if field is not None:
            if field in ("document_type", "platform"):
                setattr(row, attr, getattr(result, "document_type", "") or fields.get(field) or "")
            else:
                setattr(row, attr, fields.get(field) or "")
    return row


def _row_to_list(row: ReportRow) -> list[str]:
    return [
        row.client_ref,
        row.account_id,
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
        row.invoice_type,
    ]


def build_report_rows(results: list, config: AppConfig) -> list[ReportRow]:
    rows = []
    for result in results:
        type_config = config.document_types.get(
            getattr(result, "document_type", config.default_document_type),
            config.document_types[config.default_document_type],
        )
        rows.append(_result_to_row(result, type_config))
    return rows


def generate_csv_content(results: list, config: AppConfig) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(_COLUMNS)
    for row in build_report_rows(results, config):
        writer.writerow(_row_to_list(row))
    return buffer.getvalue()


def build_filename(config: AppConfig, timestamp: datetime | None = None) -> str:
    if timestamp is None:
        timestamp = datetime.now()
    return config.reports.filename_template.format(timestamp=timestamp.strftime("%Y%m%d_%H%M%S"))
