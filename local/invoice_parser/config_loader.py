import base64
import json
import os
from pathlib import Path

APP_CONFIG_ENV = "APP_CONFIG_JSON"
SERVICE_ACCOUNT_ENV = "SERVICE_ACCOUNT_JSON"
RCLONE_ENV = "RCLONE_CONF"

SERVICE_ACCOUNT_KEY_FILE = "/app/keys/connect-ai-pc-fad7ca673e19.json"
RCLONE_CONFIG_FILE = "/root/.config/rclone/rclone.conf"


def _package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _repo_root() -> Path:
    return _package_root().parent


def default_config_path() -> Path:
    return _repo_root() / "local" / "local_config.json"


def example_config_path() -> Path:
    return _repo_root() / "local" / "local_config.example.json"


def _decode_base64(value: str) -> str:
    try:
        decoded = base64.b64decode(value, validate=True)
        return decoded.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return value


def _read_explicit_file(explicit: Path | None) -> Path | None:
    if explicit is not None and explicit.exists():
        return explicit
    return None


def _read_env_path() -> Path | None:
    env_path = os.getenv("INVOICE_UI_CONFIG_PATH")
    if not env_path:
        return None
    candidate = Path(env_path).resolve()
    if candidate.exists():
        return candidate
    return None


def resolve_config_path(explicit: Path | None = None) -> Path:
    if found := _read_explicit_file(explicit):
        return found
    if found := _read_env_path():
        return found
    if os.getenv(APP_CONFIG_ENV):
        return default_config_path()
    if default_config_path().exists():
        return default_config_path()
    return example_config_path()


def load_config_source(explicit: Path | None = None) -> tuple[Path, dict]:
    path = resolve_config_path(explicit)
    inline = os.getenv(APP_CONFIG_ENV)
    if path == default_config_path() and inline:
        return path, json.loads(inline)
    return path, json.loads(path.read_text(encoding="utf-8"))


def materialize_secrets() -> list[str]:
    """Write service-account and rclone secrets from env vars into well-known paths.

    Accepts raw or base64-encoded values, and the legacy pipe-joined rclone
    format. Returns a list of human-readable status messages.
    """
    messages: list[str] = []

    key_b64 = os.getenv(f"{SERVICE_ACCOUNT_ENV}_B64")
    key_raw = os.getenv(SERVICE_ACCOUNT_ENV)
    if key_b64 or key_raw:
        value = _decode_base64(key_b64) if key_b64 else key_raw
        dest = Path(SERVICE_ACCOUNT_KEY_FILE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(value, encoding="utf-8")
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        messages.append("Service-account key written from environment")
    else:
        messages.append("No service-account key mounted or provided")

    rclone_b64 = os.getenv(f"{RCLONE_ENV}_B64")
    rclone_raw = os.getenv(RCLONE_ENV)
    if rclone_b64 or rclone_raw:
        value = _decode_base64(rclone_b64) if rclone_b64 else rclone_raw
        dest = Path(RCLONE_CONFIG_FILE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(value.replace("|", "\n"), encoding="utf-8")
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        messages.append("rclone config written from environment")
    else:
        messages.append("No rclone config mounted or provided")

    return messages