import re
from invoice_parser.config import DocumentTypeConfig


def classify_document(
    text: str,
    document_types: dict[str, DocumentTypeConfig],
    default_type: str,
) -> str:
    """Return the document type whose classifier patterns best match the text.

    Each configured document type has a list of regex patterns. The type with
    the highest number of pattern matches wins. If no type matches, the
    configured ``default_type`` is returned.

    Matching is performed case-insensitively against the full extracted text.
    Patterns are expected to have already been validated when the config was
    loaded.
    """
    if not document_types:
        return default_type

    best_type = default_type
    best_score = 0

    for document_type, type_config in document_types.items():
        score = 0
        for pattern in type_config.classifier.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        if score > best_score:
            best_score = score
            best_type = document_type

    return best_type
