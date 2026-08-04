import json
import logging
import sys
from pathlib import Path
from typing import Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        extra = getattr(record, "extra", None)
        if extra:
            base["extra"] = extra
        return json.dumps(base, ensure_ascii=False)


def setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("invoice_parser")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        logger.handlers.clear()

    formatter = JsonFormatter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log_info(logger: logging.Logger, event: str, extra: Optional[dict] = None) -> None:
    logger.info(event, extra={"extra": extra or {}})


def log_error(logger: logging.Logger, event: str, extra: Optional[dict] = None) -> None:
    logger.error(event, extra={"extra": extra or {}})
