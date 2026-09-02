from invoice_parser.classifier import classify_document
from invoice_parser.config import AppConfig


def _build_config(extra_types=None):
    data = {"source_folder": "/tmp"}
    if extra_types:
        data["document_types"] = extra_types
    return AppConfig.model_validate(data)


def test_classify_document_returns_default_when_no_match():
    config = _build_config()
    text = "Some unrelated document"
    assert classify_document(text, config.document_types, config.default_document_type) == config.default_document_type


def test_classify_document_matches_default_type():
    config = _build_config()
    text = "Invoice number: 12345\nInvoice date: 2024-01-01"
    assert classify_document(text, config.document_types, config.default_document_type) == "google_ads"


def test_classify_document_prefers_type_with_more_matches():
    config = _build_config({
        "google_ads": {
            "classifier": {"patterns": ["Invoice"]},
            "fields": {},
        },
        "receipt": {
            "classifier": {"patterns": ["Receipt", "Payment received"]},
            "fields": {},
        },
    })

    text = "Receipt for your payment\nPayment received on 2024-01-01"
    assert classify_document(text, config.document_types, config.default_document_type) == "receipt"


def test_classify_document_falls_back_to_default_on_tie():
    config = _build_config({
        "google_ads": {
            "classifier": {"patterns": ["Document"]},
            "fields": {},
        },
        "receipt": {
            "classifier": {"patterns": ["Document"]},
            "fields": {},
        },
    })

    text = "Important document"
    result = classify_document(text, config.document_types, config.default_document_type)
    assert result == config.default_document_type


def test_classify_document_empty_text_returns_default():
    config = _build_config()
    assert classify_document("", config.document_types, config.default_document_type) == config.default_document_type
