from pathlib import Path

from pydantic import BaseModel


class UIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    static_dir: Path = Path(__file__).resolve().parent.parent / "static"
    config_path_env: str = "INVOICE_UI_CONFIG_PATH"

    @classmethod
    def from_env(cls) -> "UIConfig":
        import os

        host = os.getenv("INVOICE_UI_HOST", "0.0.0.0")
        port = int(os.getenv("INVOICE_UI_PORT", "8000"))
        return cls(host=host, port=port)
