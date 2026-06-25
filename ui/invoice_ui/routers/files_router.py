from fastapi import APIRouter, Request

from invoice_ui.models.schemas import FileInfo
from invoice_ui.services import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("", response_model=list[FileInfo])
def list_files(request: Request):
    service = FileService.from_request(request)
    return service.list_files()


@router.get("/summary")
def file_summary(request: Request):
    service = FileService.from_request(request)
    return service.summary()


@router.post("/clear-incoming")
def clear_incoming(request: Request):
    service = FileService.from_request(request)
    return service.clear_incoming()


@router.post("/clear-outgoing")
def clear_outgoing(request: Request):
    service = FileService.from_request(request)
    return service.clear_outgoing()
