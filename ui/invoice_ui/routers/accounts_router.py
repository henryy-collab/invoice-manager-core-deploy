from typing import Optional

from fastapi import APIRouter, Query, Request

from invoice_ui.services.accounts_service import AccountsService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
def get_accounts(request: Request, folder: Optional[str] = Query(default=None)):
    service = AccountsService.from_request(request)
    return service.build_records(source_dir=folder)
