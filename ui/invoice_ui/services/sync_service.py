import json
import re
import shutil
import subprocess
from pathlib import Path

from fastapi import Request

from invoice_ui.dependencies import get_app_config


class SyncService:
    def __init__(self, config):
        self.config = config

    @classmethod
    def from_request(cls, request: Request) -> "SyncService":
        return cls(get_app_config(request))

    def _rclone_available(self) -> bool:
        return shutil.which("rclone") is not None

    def _run_rclone(self, args: list[str]) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        if not self._rclone_available():
            return {"success": False, "error": "rclone command not found"}

        try:
            result = subprocess.run(
                ["rclone", *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "rclone command timed out"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _state_dir(self) -> Path:
        return Path(self.config.output_folder).parent / "state"

    def _last_run_state_path(self) -> Path:
        return self._state_dir() / "last_run_processed.json"

    def _cleanup_local_folder(self, folder: str) -> dict:
        path = Path(folder)
        if not path.exists():
            return {"success": True, "deleted": 0}
        deleted = 0
        errors = []
        for pdf_path in path.glob("*.pdf"):
            try:
                pdf_path.unlink()
                deleted += 1
            except OSError as exc:
                errors.append(f"{pdf_path.name}: {exc}")
        return {"success": not errors, "deleted": deleted, "errors": errors}

    def _cleanup_metadata_files(self, folder: str) -> dict:
        path = Path(folder)
        if not path.exists():
            return {"success": True, "deleted": 0}
        deleted = 0
        errors = []
        for meta_path in path.glob("*.pdf.meta.json"):
            try:
                meta_path.unlink()
                deleted += 1
            except OSError as exc:
                errors.append(f"{meta_path.name}: {exc}")
        return {"success": not errors, "deleted": deleted, "errors": errors}

    def _remote_path(self, folder: str | None) -> str | None:
        if folder is None:
            return None
        return f"{self.config.rclone.remote}:{folder}"

    def _resolve_subfolder(self, template: str, date_str: str | None) -> str:
        if not date_str or not re.match(r"^\d{8}$", date_str):
            return "unknown-date"
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        result = template
        result = result.replace("{date}", date_str)
        result = result.replace("{year}", year)
        result = result.replace("{month}", month)
        result = result.replace("{day}", day)
        return result

    def _read_metadata_date(self, pdf_path: Path) -> str | None:
        meta_path = pdf_path.with_suffix(pdf_path.suffix + ".meta.json")
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return meta.get("date")
        except (json.JSONDecodeError, OSError):
            return None

    def pull_incoming(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        remote_path = self._remote_path(self.config.rclone.source_drive_folder)
        if remote_path is None:
            return {"success": False, "error": "source_drive_folder is not configured"}
        local_path = str(Path(self.config.input_folder))

        before_count = len(list(Path(local_path).glob("*.pdf"))) if Path(local_path).exists() else 0
        result = self._run_rclone(["sync", remote_path, local_path])
        if not result["success"]:
            return result

        after_count = len(list(Path(local_path).glob("*.pdf"))) if Path(local_path).exists() else 0
        transferred = max(0, after_count - before_count)
        result["before_count"] = before_count
        result["after_count"] = after_count
        result["transferred"] = transferred
        if transferred == 0:
            result["message"] = "Pull completed but no new files were downloaded."
        else:
            result["message"] = f"Pull completed. {transferred} new file(s) downloaded."
        return result

    def push_outgoing(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        remote_path = self._remote_path(self.config.rclone.destination_drive_folder)
        if remote_path is None:
            return {"success": False, "error": "destination_drive_folder is not configured"}
        local_path = str(Path(self.config.output_folder))
        subfolder_template = self.config.rclone.destination_subfolder_template

        if not subfolder_template:
            pdf_files = sorted(Path(local_path).glob("*.pdf"))
            if not pdf_files:
                return {"success": True, "message": "No outgoing files to push"}
            result = self._run_rclone(["copy", local_path, remote_path])
            if result["success"]:
                cleanup = self._cleanup_local_folder(local_path)
                result["cleanup"] = cleanup
                result["message"] = f"Push completed. {len(pdf_files)} file(s) uploaded."
            return result

        output_path = Path(local_path)
        if not output_path.exists():
            return {"success": True, "message": "No outgoing files to push"}

        pdf_files = sorted(output_path.glob("*.pdf"))
        if not pdf_files:
            return {"success": True, "message": "No outgoing files to push"}

        grouped: dict[str, list[Path]] = {}
        for pdf_path in pdf_files:
            date_str = self._read_metadata_date(pdf_path)
            subfolder = self._resolve_subfolder(subfolder_template, date_str)
            grouped.setdefault(subfolder, []).append(pdf_path)

        pushed = 0
        errors = []
        subfolder_counts: dict[str, int] = {}

        for subfolder, files in grouped.items():
            list_file = self._state_dir() / f"_push_outgoing_{subfolder}.txt"
            try:
                list_file.write_text("\n".join(f.name for f in files), encoding="utf-8")
            except OSError as exc:
                errors.append(f"{subfolder}: failed to write file list: {exc}")
                continue

            try:
                file_remote_path = f"{remote_path}/{subfolder}"
                result = self._run_rclone(["copy", "--files-from", str(list_file), local_path, file_remote_path])
            finally:
                try:
                    list_file.unlink()
                except OSError:
                    pass

            if result["success"]:
                pushed += len(files)
                subfolder_counts[subfolder] = len(files)
            else:
                errors.append(f"{subfolder}: {result.get('stderr') or result.get('error')}")

        if not errors:
            cleanup_result = self._cleanup_local_folder(local_path)
            meta_cleanup_result = self._cleanup_metadata_files(local_path)
        else:
            cleanup_result = {"success": True, "deleted": 0, "errors": []}
            meta_cleanup_result = {"success": True, "deleted": 0, "errors": []}

        return {
            "success": not errors,
            "pushed": pushed,
            "message": f"Push completed. {pushed} file(s) uploaded." if not errors else "Push failed for some subfolders.",
            "subfolders": subfolder_counts,
            "errors": errors,
            "cleanup": cleanup_result,
            "metadata_cleanup": meta_cleanup_result,
        }

    def push_archive(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        remote_path = self._remote_path(self.config.rclone.archive_drive_folder)
        if remote_path is None:
            return {"success": False, "error": "archive_drive_folder is not configured"}
        local_path = str(Path(self.config.archive_folder))
        pdf_files = sorted(Path(local_path).glob("*.pdf"))
        if not pdf_files:
            return {"success": True, "message": "No archive files to push"}
        result = self._run_rclone(["copy", local_path, remote_path])
        if result.get("success"):
            result["message"] = f"Push Archive completed. {len(pdf_files)} file(s) uploaded."
        return result

    def clear_remote_input(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        if not self._rclone_available():
            return {"success": False, "error": "rclone command not found"}

        state_path = self._last_run_state_path()
        if not state_path.exists():
            return {"success": False, "error": "No successful run recorded"}

        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {"success": False, "error": f"Failed to read run state: {exc}"}

        processed = state.get("processed", [])
        if not processed:
            return {"success": True, "message": "No processed files to clear", "deleted": 0}

        remote_path = self._remote_path(self.config.rclone.source_drive_folder)
        if remote_path is None:
            return {"success": False, "error": "source_drive_folder is not configured"}

        list_file = self._state_dir() / "_clear_input_files.txt"
        try:
            list_file.write_text("\n".join(processed), encoding="utf-8")
        except OSError as exc:
            return {"success": False, "error": f"Failed to write file list: {exc}"}

        try:
            result = self._run_rclone(["delete", "--files-from", str(list_file), remote_path])
        finally:
            try:
                list_file.unlink()
            except OSError:
                pass

        if not result["success"]:
            return {
                "success": False,
                "deleted": 0,
                "errors": [result.get("stderr") or result.get("error") or "Unknown error"],
            }

        try:
            state_path.unlink()
        except OSError as exc:
            return {
                "success": True,
                "deleted": len(processed),
                "errors": [f"Failed to remove state file: {exc}"],
            }

        return {
            "success": True,
            "deleted": len(processed),
            "errors": [],
        }

    def status(self) -> dict:
        return {
            "enabled": self.config.rclone.enabled,
            "remote": self.config.rclone.remote,
            "source_drive_folder": self.config.rclone.source_drive_folder,
            "destination_drive_folder": self.config.rclone.destination_drive_folder,
            "destination_subfolder_template": self.config.rclone.destination_subfolder_template,
            "archive_drive_folder": self.config.rclone.archive_drive_folder,
            "rclone_available": self._rclone_available(),
            "input_folder": self.config.input_folder,
            "output_folder": self.config.output_folder,
            "archive_folder": self.config.archive_folder,
            "can_clear_remote_input": self._last_run_state_path().exists(),
        }
