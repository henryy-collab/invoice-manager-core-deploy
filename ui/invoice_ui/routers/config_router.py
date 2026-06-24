from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from invoice_ui.dependencies import get_config_path
from invoice_ui.models.schemas import ConfigResponse, ConfigSaveRequest
from invoice_ui.services import ConfigService

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
def get_config(request: Request):
    service = ConfigService.from_request(request)
    return ConfigResponse(config=service.load(), path=str(service.config_path))


@router.post("", response_model=ConfigResponse)
def save_config(payload: ConfigSaveRequest, request: Request):
    service = ConfigService.from_request(request)
    try:
        service.save(payload.config)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ConfigResponse(config=service.load(), path=str(service.config_path))


@router.post("/validate")
def validate_config(payload: ConfigSaveRequest, request: Request):
    service = ConfigService.from_request(request)
    error = service.get_validation_error(payload.config)
    return {"valid": error is None, "error": error}
