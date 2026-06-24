from invoice_ui.routers.config_router import router as config_router
from invoice_ui.routers.files_router import router as files_router
from invoice_ui.routers.logs_router import router as logs_router
from invoice_ui.routers.parse_router import router as parse_router
from invoice_ui.routers.reports_router import router as reports_router
from invoice_ui.routers.sheets_router import router as sheets_router
from invoice_ui.routers.sync_router import router as sync_router

__all__ = [
    "config_router",
    "files_router",
    "logs_router",
    "parse_router",
    "reports_router",
    "sheets_router",
    "sync_router",
]
