from fastapi import APIRouter, Request

from invoice_ui.models.schemas import (
    ParsePreviewRequest,
    ParseResponse,
    ParseUpdateRequest,
    RunResponse,
)
from invoice_ui.services import ParseService

router = APIRouter(prefix="/api/parse", tags=["parse"])


@router.post("/preview", response_model=ParseResponse)
def preview_parse(request: Request):
    service = ParseService.from_request(request)
    return service.preview()


@router.post("/update", response_model=ParseResponse)
def update_parse(payload: ParseUpdateRequest, request: Request):
    service = ParseService.from_request(request)
    return service.update_result(payload.source_name, payload.fields)


@router.post("/run", response_model=RunResponse)
def run_parse(payload: ParsePreviewRequest, request: Request):
    service = ParseService.from_request(request)
    result = service.run(dry_run=payload.dry_run)
    return RunResponse(**result)
