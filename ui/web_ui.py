import uvicorn

from pathlib import Path

from invoice_ui.config import UIConfig
from invoice_ui.dependencies import load_app_config_from_path, resolve_default_config_path


def ensure_app_directories(config_path: Path) -> None:
    """Create directories referenced by the app config if they do not exist."""
    if not config_path.exists():
        return
    app_config = load_app_config_from_path(config_path)
    Path(app_config.input_folder).mkdir(parents=True, exist_ok=True)
    Path(app_config.output_folder).mkdir(parents=True, exist_ok=True)
    Path(app_config.archive_folder).mkdir(parents=True, exist_ok=True)
    Path(app_config.log_file).parent.mkdir(parents=True, exist_ok=True)


def main():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "local"))
    from setup_data import ensure_data_dirs

    ensure_data_dirs()
    ensure_app_directories(resolve_default_config_path())

    ui_config = UIConfig.from_env()
    uvicorn.run(
        "invoice_ui.main:app",
        host=ui_config.host,
        port=ui_config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
