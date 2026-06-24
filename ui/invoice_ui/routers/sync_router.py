from fastapi import APIRouter, Request

from invoice_ui.services.sync_service import SyncService

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/status")
def sync_status(request: Request):
    service = SyncService.from_request(request)
    return service.status()


@router.post("/incoming")
def sync_incoming(request: Request):
    service = SyncService.from_request(request)
    return service.pull_incoming()


@router.post("/outgoing")
def sync_outgoing(request: Request):
    service = SyncService.from_request(request)
    return service.push_outgoing()


@router.post("/archive")
def sync_archive(request: Request):
    service = SyncService.from_request(request)
    return service.push_archive()


@router.post("/clear-input")
def sync_clear_input(request: Request):
    service = SyncService.from_request(request)
    return service.clear_remote_input()
