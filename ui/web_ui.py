import uvicorn

from invoice_ui.config import UIConfig


def main():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "local"))
    from setup_data import ensure_data_dirs
    ensure_data_dirs()

    ui_config = UIConfig.from_env()
    uvicorn.run(
        "invoice_ui.main:app",
        host=ui_config.host,
        port=ui_config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
