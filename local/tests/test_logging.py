import json
import logging
from pathlib import Path

from invoice_parser.logging import setup_logging


def test_setup_logging_creates_log_directory(tmp_path):
    log_path = tmp_path / "missing" / "dir" / "app.log"
    logger = setup_logging(log_path)

    assert log_path.parent.exists()
    assert log_path.exists()
    assert logger.name == "invoice_parser"
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    # Verify we can write a log record
    logger.info("test event")
    content = log_path.read_text(encoding="utf-8")
    record = json.loads(content)
    assert record["event"] == "test event"
