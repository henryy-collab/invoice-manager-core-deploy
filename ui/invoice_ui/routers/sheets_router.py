from fastapi import APIRouter, Request

from invoice_ui.services.sheets_service import SheetsService

router = APIRouter(prefix="/api/sheets", tags=["sheets"])


@router.post("/write")
def write_to_report(request: Request):
    service = SheetsService.from_request(request)
    try:
        result = service.write_last_preview_results()
        return result
    except Exception as exc:
        return {"success": False, "error": f"Unexpected error writing to report: {exc}"}
