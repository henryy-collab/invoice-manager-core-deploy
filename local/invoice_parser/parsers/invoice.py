from invoice_parser.config import AppConfig, DocumentTypeConfig
from invoice_parser.models import Document, Invoice
from invoice_parser.parsers.strategies import run_strategy


def parse_document(
    text: str,
    filename_stem: str,
    config: AppConfig,
    type_config: DocumentTypeConfig | None = None,
    document_type: str | None = None,
) -> Document:
    type_config = type_config or config.document_types[config.default_document_type]
    document_type = document_type or config.default_document_type

    fields = {
        field_name: run_strategy(
            field_config.parser,
            text,
            filename_stem,
            config.date_format,
            field_config,
            config,
        )
        for field_name, field_config in type_config.fields.items()
    }
    return Document(document_type=document_type, **fields)


parse_invoice = parse_document
