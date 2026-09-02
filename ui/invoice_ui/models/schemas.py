from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ConfigResponse(BaseModel):
    config: dict[str, Any]
    path: str


class ConfigSaveRequest(BaseModel):
    config: dict[str, Any]


class FileInfo(BaseModel):
    name: str
    path: str
    folder: str
    size: int
    modified: datetime
    status: str


class ParsePreviewRequest(BaseModel):
    dry_run: bool = True


class ParseUpdateRequest(BaseModel):
    source_name: str
    fields: dict[str, Optional[str]]


class ParseResultItem(BaseModel):
    source_name: str
    source_path: str
    fields: dict[str, Optional[str]]
    missing_required: list[str]
    target_name: str
    needs_manual_review: bool
    number_fallback_used: bool
    document_type: str = "google_ads"


class ParseResponse(BaseModel):
    dry_run: bool
    results: list[ParseResultItem]
    processed_count: int
    manual_review_count: int
    skipped_count: int
    failed_count: int


class RunResponse(BaseModel):
    success: bool
    dry_run: bool
    message: str


class LogEntry(BaseModel):
    timestamp: Optional[str]
    level: str
    event: str
    extra: Optional[dict[str, Any]] = None
