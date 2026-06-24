from pathlib import Path

import fitz


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        chunks = [page.get_text() for page in doc]
    finally:
        doc.close()
    return "\n".join(chunks)
