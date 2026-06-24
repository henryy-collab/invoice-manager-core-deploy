from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from invoice_ui.services import ParseService
from invoice_ui.services.reports_service import build_filename, generate_csv_content

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/export")
def export_csv(request: Request):
    parse_service = ParseService.from_request(request)
    results = parse_service.get_last_preview_results()

    if not results:
        return {"success": False, "error": "No preview results available. Click Preview first."}

    config = parse_service.config
    if not config.reports.enabled:
        return {"success": False, "error": "Reports are disabled in config."}

    content = generate_csv_content(results)
    filename = build_filename(config, timestamp=datetime.now())

    return StreamingResponse(
        iter([content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
