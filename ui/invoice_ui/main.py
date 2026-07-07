from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from invoice_ui.config import UIConfig
from invoice_ui.routers import (
    config_router,
    files_router,
    logs_router,
    parse_router,
    reports_router,
    sheets_router,
    sync_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Invoice Parser UI",
        description="Web UI for the local invoice parser and renamer.",
        version="1.0.0",
    )

    ui_config = UIConfig.from_env()

    app.include_router(config_router)
    app.include_router(files_router)
    app.include_router(parse_router)
    app.include_router(logs_router)
    app.include_router(sync_router)
    app.include_router(reports_router)
    app.include_router(sheets_router)

    static_dir = ui_config.static_dir
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        index = static_dir / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"message": "Invoice Parser UI static files not found."}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/files/{folder}/{filename}")
    async def download_file(folder: str, filename: str, request: Request):
        from invoice_ui.dependencies import get_app_config

        config = get_app_config(request)
        if folder == "incoming":
            source = Path(config.input_folder)
        elif folder == "outgoing":
            source = Path(config.output_folder)
        else:
            return {"error": "Invalid folder"}

        file_path = source / filename
        try:
            file_path.resolve().relative_to(source.resolve())
        except ValueError:
            return {"error": "Invalid file path"}
        if file_path.exists():
            return FileResponse(file_path)
        return {"error": "File not found"}

    return app


app = create_app()
