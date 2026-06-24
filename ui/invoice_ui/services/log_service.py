import json
from datetime import datetime
from pathlib import Path

from fastapi import Request

from invoice_ui.dependencies import get_app_config, get_config_path
from invoice_ui.models.schemas import LogEntry


class LogService:
    def __init__(self, config, config_path: Path):
        self.config = config
        self.config_path = config_path

    @classmethod
    def from_request(cls, request: Request) -> "LogService":
        return cls(get_app_config(request), get_config_path(request))

    def _log_path(self) -> Path:
        log_path = Path(self.config.log_file)
        if not log_path.is_absolute():
            log_path = self.config_path.parent / log_path
        return log_path

    def read_logs(self, limit: int = 200) -> list[LogEntry]:
        log_path = self._log_path()
        if not log_path.exists():
            return []

        entries = []
        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(LogEntry(
                        timestamp=data.get("timestamp"),
                        level=data.get("level", "INFO"),
                        event=data.get("event", ""),
                        extra=data.get("extra"),
                    ))
                except json.JSONDecodeError:
                    entries.append(LogEntry(
                        timestamp=None,
                        level="UNKNOWN",
                        event=line,
                    ))

        entries.reverse()
        return entries[:limit]

    def last_run_timestamp(self) -> str | None:
        for entry in self.read_logs(limit=100):
            if entry.event == "UI_RUN_FINISHED" or entry.event == "PROCESS_FAILED":
                return entry.timestamp
        return None
