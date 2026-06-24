import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request

from invoice_parser.files import is_already_processed
from invoice_ui.dependencies import get_app_config
from invoice_ui.models.schemas import FileInfo


class FileService:
    def __init__(self, config):
        self.config = config

    @classmethod
    def from_request(cls, request: Request) -> "FileService":
        return cls(get_app_config(request))

    def _input_dir(self) -> Path:
        return Path(self.config.input_folder)

    def _output_dir(self) -> Path:
        return Path(self.config.output_folder)

    def list_files(self) -> list[FileInfo]:
        files: list[FileInfo] = []
        files.extend(self._list_folder(self._input_dir(), "incoming"))
        files.extend(self._list_folder(self._output_dir(), "outgoing"))
        return files

    def _list_folder(self, folder: Path, folder_name: str) -> list[FileInfo]:
        if not folder.exists():
            return []

        result = []
        for pdf_path in sorted(folder.glob("*.pdf")):
            stat = pdf_path.stat()
            result.append(FileInfo(
                name=pdf_path.name,
                path=str(pdf_path),
                folder=folder_name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                status=self._status(pdf_path.name, folder_name),
            ))
        return result

    def _status(self, name: str, folder: str) -> str:
        if folder == "outgoing":
            return "outgoing"
        if name.startswith("000_"):
            return "manual_review"
        if is_already_processed(name, self.config.filename.already_processed_patterns):
            return "processed"
        return "unprocessed"

    def summary(self) -> dict[str, int]:
        files = self.list_files()
        return {
            "total": len(files),
            "processed": sum(1 for f in files if f.status == "processed"),
            "manual_review": sum(1 for f in files if f.status == "manual_review"),
            "unprocessed": sum(1 for f in files if f.status == "unprocessed"),
        }

    def clear_incoming(self) -> dict:
        input_dir = self._input_dir()
        if not input_dir.exists():
            return {"success": True, "deleted": 0, "message": "Incoming folder does not exist."}

        deleted = 0
        failed = 0
        for pdf_path in input_dir.glob("*.pdf"):
            try:
                pdf_path.unlink()
                deleted += 1
            except OSError:
                failed += 1

        if failed:
            return {"success": False, "deleted": deleted, "error": f"Deleted {deleted} file(s), {failed} failed."}
        return {"success": True, "deleted": deleted, "message": f"Deleted {deleted} file(s) from incoming folder."}
