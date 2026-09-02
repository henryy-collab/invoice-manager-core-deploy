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
            success = result.returncode == 0
            summary = None
            if not success:
                summary = self._summarize_rclone_error(result.stderr)
            return {
                "success": success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": summary,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "rclone command timed out"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _summarize_rclone_error(self, stderr: str) -> str:
        if not stderr:
            return "rclone failed with no error output"
        first_line = stderr.strip().splitlines()[0]
        lower = stderr.lower()
        if "directory not found" in lower or "couldn't find directory" in lower:
            return f"Drive folder not found or not accessible: {first_line}"
        if "not found" in lower:
            return f"Remote not found or folder missing: {first_line}"
        if "permission denied" in lower or "access denied" in lower:
            return f"Permission denied by remote: {first_line}"
        if "auth" in lower:
            return f"Authentication failed for remote: {first_line}"
        if "timeout" in lower or "deadline exceeded" in lower:
            return f"rclone timed out: {first_line}"
        return first_line

    def _state_dir(self) -> Path:
        return Path(self.config.output_folder).parent / "state"

    def _ensure_state_dir(self) -> Path:
        state_dir = self._state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

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

    def _metadata_document_type(self, pdf_path: Path) -> str:
        meta_path = pdf_path.with_suffix(pdf_path.suffix + ".meta.json")
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                return meta.get("document_type") or self.config.default_document_type
            except (json.JSONDecodeError, OSError):
                pass
        return self.config.default_document_type

    def pull_incoming(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        local_path = str(Path(self.config.input_folder))

        before_count = len(list(Path(local_path).glob("*.pdf"))) if Path(local_path).exists() else 0
        platform_results: dict[str, bool] = {}
        errors: list[str] = []

        for document_type in self.config.platform_types():
            rconfig = self.config.rclone_for(document_type)
            remote_path = self._remote_path(rconfig.source_drive_folder)
            if remote_path is None:
                continue
            result = self._run_rclone(["copy", remote_path, local_path])
            platform_results[document_type] = result["success"]
            if not result["success"]:
                errors.append(f"{document_type}: {result.get('error') or result.get('stderr') or 'rclone failed'}")

        success = not errors
        after_count = len(list(Path(local_path).glob("*.pdf"))) if Path(local_path).exists() else 0
        transferred = max(0, after_count - before_count)
        result: dict = {
            "success": success,
            "platforms": platform_results,
            "errors": errors,
            "before_count": before_count,
            "after_count": after_count,
            "transferred": transferred,
            "message": f"Pull completed. {transferred} new file(s) downloaded." if not errors else "Pull failed for some platforms.",
        }
        return result

    def push_outgoing(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}

        output_path = Path(self.config.output_folder)
        if not output_path.exists():
            return {"success": True, "message": "No outgoing files to push"}

        pdf_files = sorted(output_path.glob("*.pdf"))
        if not pdf_files:
            return {"success": True, "message": "No outgoing files to push"}

        grouped: dict[tuple[str, str], list[Path]] = {}
        for pdf_path in pdf_files:
            document_type = self._metadata_document_type(pdf_path)
            rconfig = self.config.rclone_for(document_type)
            if rconfig.destination_drive_folder is None:
                continue
            date_str = self._read_metadata_date(pdf_path)
            subfolder = ""
            if rconfig.destination_subfolder_template:
                subfolder = self._resolve_subfolder(rconfig.destination_subfolder_template, date_str)
            grouped.setdefault((document_type, subfolder), []).append(pdf_path)

        if not grouped:
            return {"success": True, "message": "No outgoing files to push", "subfolders": {}}

        pushed = 0
        errors: list[str] = []
        subfolder_counts: dict[str, int] = {}

        for (document_type, subfolder), files in grouped.items():
            rconfig = self.config.rclone_for(document_type)
            remote_path = self._remote_path(rconfig.destination_drive_folder)
            if remote_path is None:
                errors.append(f"{document_type}: destination_drive_folder is not configured")
                continue
            if subfolder:
                remote_path = f"{remote_path}/{subfolder}"

            list_file = self._ensure_state_dir() / f"_push_outgoing_{document_type}_{subfolder or 'root'}.txt"
            try:
                list_file.write_text("\n".join(f.name for f in files), encoding="utf-8")
            except OSError as exc:
                errors.append(f"{document_type}/{subfolder}: failed to write file list: {exc}")
                continue

            try:
                result = self._run_rclone(["copy", "--files-from", str(list_file), str(output_path), remote_path])
            finally:
                try:
                    list_file.unlink()
                except OSError:
                    pass

            if result["success"]:
                pushed += len(files)
                label = f"{document_type}/{subfolder}" if subfolder else document_type
                subfolder_counts[label] = len(files)
            else:
                errors.append(f"{document_type}/{subfolder or 'root'}: {result.get('stderr') or result.get('error')}")

        if not errors:
            cleanup_result = self._cleanup_local_folder(str(output_path))
            meta_cleanup_result = self._cleanup_metadata_files(str(output_path))
        else:
            cleanup_result = {"success": True, "deleted": 0, "errors": []}
            meta_cleanup_result = {"success": True, "deleted": 0, "errors": []}

        return {
            "success": not errors,
            "pushed": pushed,
            "message": f"Push completed. {pushed} file(s) uploaded." if not errors else "Push failed for some platforms.",
            "subfolders": subfolder_counts,
            "errors": errors,
            "cleanup": cleanup_result,
            "metadata_cleanup": meta_cleanup_result,
        }

    def push_archive(self) -> dict:
        if not self.config.rclone.enabled:
            return {"success": False, "error": "rclone sync is disabled in config"}
        archive_folder = self.config.rclone.archive_drive_folder
        if archive_folder is None or archive_folder == "":
            return {"success": True, "message": "Archive disabled: archive_drive_folder is not set"}
        remote_path = self._remote_path(archive_folder)
        if remote_path is None:
            return {"success": True, "message": "Archive disabled: archive_drive_folder is not set"}
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

        remote_targets: list[tuple[str, str]] = []
        for document_type in self.config.platform_types():
            rconfig = self.config.rclone_for(document_type)
            remote_path = self._remote_path(rconfig.source_drive_folder)
            if remote_path is not None:
                remote_targets.append((document_type, remote_path))

        if not remote_targets:
            return {"success": False, "error": "source_drive_folder is not configured for any platform"}

        list_file = self._ensure_state_dir() / "_clear_input_files.txt"
        try:
            list_file.write_text("\n".join(processed), encoding="utf-8")
        except OSError as exc:
            return {"success": False, "error": f"Failed to write file list: {exc}"}

        errors: list[str] = []
        platform_results: dict[str, bool] = {}

        for document_type, remote_path in remote_targets:
            try:
                result = self._run_rclone(["delete", "--files-from", str(list_file), remote_path])
            finally:
                if list_file.is_file():
                    try:
                        list_file.unlink()
                    except OSError:
                        pass
            platform_results[document_type] = result["success"]
            if not result["success"]:
                errors.append(f"{document_type}: {result.get('stderr') or result.get('error') or 'Unknown error'}")

        if errors:
            return {
                "success": False,
                "deleted": 0,
                "platforms": platform_results,
                "errors": errors,
            }

        try:
            state_path.unlink()
        except OSError as exc:
            return {
                "success": True,
                "deleted": len(processed),
                "platforms": platform_results,
                "errors": [f"Failed to remove state file: {exc}"],
            }

        return {
            "success": True,
            "deleted": len(processed),
            "platforms": platform_results,
            "errors": [],
        }

    def status(self) -> dict:
        platforms = []
        for document_type in self.config.platform_types():
            rconfig = self.config.rclone_for(document_type)
            platforms.append({
                "document_type": document_type,
                "enabled": rconfig.enabled,
                "remote": rconfig.remote,
                "source_drive_folder": rconfig.source_drive_folder,
                "destination_drive_folder": rconfig.destination_drive_folder,
                "destination_subfolder_template": rconfig.destination_subfolder_template,
                "archive_drive_folder": rconfig.archive_drive_folder,
            })
        return {
            "enabled": self.config.rclone.enabled,
            "remote": self.config.rclone.remote,
            "source_drive_folder": self.config.rclone.source_drive_folder,
            "destination_drive_folder": self.config.rclone.destination_drive_folder,
            "destination_subfolder_template": self.config.rclone.destination_subfolder_template,
            "archive_drive_folder": self.config.rclone.archive_drive_folder,
            "platforms": platforms,
            "rclone_available": self._rclone_available(),
            "input_folder": self.config.input_folder,
            "output_folder": self.config.output_folder,
            "archive_folder": self.config.archive_folder,
            "can_clear_remote_input": self._last_run_state_path().exists(),
        }
