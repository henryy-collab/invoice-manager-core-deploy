import json
from pathlib import Path

import pytest

from invoice_parser.config import AppConfig


@pytest.fixture
def sample_text():
    return """
Account: ACME Inc
Invoice number: INV-2024-001
Invoice date: 15 April 2024
Total amount due in HKD: HK$ 12,345.67
Payment terms: Net 30

Details
15 April 2024
INV-2024-001
Net 30
"""


@pytest.fixture
def minimal_config_dict(tmp_path):
    return {
        "source_folder": str(tmp_path),
        "filename_template": "{account}_{number}_Invoice_{date}.pdf",
        "date_format": "%Y%m%d",
    }


@pytest.fixture
def sample_config(minimal_config_dict):
    return AppConfig.model_validate(minimal_config_dict)


@pytest.fixture
def sample_invoice():
    from invoice_parser.models import Invoice
    return Invoice(
        account="ACME Inc",
        number="INV-2024-001",
        date="20240415",
        total="12345.67",
        currency="HKD",
    )


@pytest.fixture
def make_pdf(tmp_path):
    def _make_pdf(name: str, content: bytes = b"%PDF-1.4 dummy") -> Path:
        pdf_path = tmp_path / name
        pdf_path.write_bytes(content)
        return pdf_path
    return _make_pdf
