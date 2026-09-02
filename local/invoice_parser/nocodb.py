import json
import os
from pathlib import Path
from typing import Any

import httpx

from invoice_parser.config import AppConfig

DEFAULT_URL = "http://localhost:3000"
TOKEN_ENV = "NOCODB_TOKEN"
URL_ENV = "NOCODB_URL"


class NocoDBError(Exception):
    pass


def _token() -> str:
    token = os.getenv(TOKEN_ENV, "")
    if not token:
        raise NocoDBError(f"{TOKEN_ENV} is not set")
    return token


def _url() -> str:
    return (os.getenv(URL_ENV, "") or DEFAULT_URL).rstrip("/")


def _build_payload(fields: dict[str, Any], column_map: dict[str, str]) -> dict[str, Any]:
    """Map parsed invoice fields to NocoDB columns, always including the source (dropdown, empty)."""
    payload: dict[str, Any] = {}
    for field, column in column_map.items():
        if field == "source":
            payload[column] = ""
            continue
        value = fields.get(field)
        payload[column] = value if value is not None else ""
    return {"fields": payload}


def upload_invoices(
    meta_files: list[Path],
    base_id: str,
    table_id: str,
    column_map: dict[str, str],
    dry_run: bool = False,
) -> dict:
    url = _url()
    token = _token()
    uploaded = 0
    errors: list[dict] = []

    endpoint = f"{url}/api/v3/data/{base_id}/{table_id}/records"
    headers = {
        "xc-token": token,
        "Content-Type": "application/json",
    }

    for meta_file in sorted(meta_files):
        try:
            fields = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append({"file": meta_file.name, "error": f"failed to read metadata: {exc}"})
            continue

        payload = _build_payload(fields, column_map)
        if dry_run:
            print(f"[dry-run] {meta_file.name}: {json.dumps(payload, ensure_ascii=False)}")
            uploaded += 1
            continue

        try:
            response = httpx.post(endpoint, json=payload, headers=headers, timeout=30)
            if response.status_code >= 400:
                errors.append({
                    "file": meta_file.name,
                    "error": f"HTTP {response.status_code}: {response.text}",
                })
            else:
                uploaded += 1
        except httpx.HTTPError as exc:
            errors.append({"file": meta_file.name, "error": str(exc)})

    return {
        "success": not errors,
        "uploaded": uploaded,
        "errors": errors,
        "base_id": base_id,
        "table_id": table_id,
        "url": url,
    }


def find_meta_files(output_folder: Path) -> list[Path]:
    return sorted(output_folder.glob("*.pdf.meta.json"))


def upload_from_config(config: AppConfig, dry_run: bool = False) -> dict:
    nc = config.nocodb
    if not nc.enabled:
        return {"success": True, "uploaded": 0, "errors": [], "skipped": True, "message": "NocoDB upload disabled in config."}

    base_id = nc.base_id
    table_id = nc.table_id
    if not base_id or not table_id:
        return {"success": False, "uploaded": 0, "errors": [{"error": "nocodb.base_id and nocodb.table_id must be configured."}], "skipped": False}

    meta_files = find_meta_files(Path(config.output_folder))
    if not meta_files:
        return {"success": True, "uploaded": 0, "errors": [], "skipped": True, "message": "No metadata sidecars found in output folder."}

    result = upload_invoices(meta_files, base_id, table_id, nc.column_map, dry_run=dry_run)
    return result