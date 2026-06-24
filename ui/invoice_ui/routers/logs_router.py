from fastapi import APIRouter, Request

from invoice_ui.models.schemas import LogEntry
from invoice_ui.services import LogService

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[LogEntry])
def read_logs(request: Request, limit: int = 200):
    service = LogService.from_request(request)
    return service.read_logs(limit=limit)
