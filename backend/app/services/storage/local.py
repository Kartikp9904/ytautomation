import os
import shutil
import mimetypes
from typing import List, Optional, Callable
from app.services.storage.base import StorageProvider, StorageItem, StorageFileMetadata
from app.core.config import settings
from app.core.logging import logger


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = os.path.abspath(base_path or settings.LOCAL_STORAGE_BASE_PATH)
        os.makedirs(self.base_path, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "local"

    async def is_connected(self) -> bool:
        return os.path.exists(self.base_path) and os.path.isdir(self.base_path)

    def _get_abs_path(self, item_id: Optional[str]) -> str:
        if not item_id or item_id == "root":
            return self.base_path
        
        # item_id is relative path from base_path
        target = os.path.abspath(os.path.join(self.base_path, item_id))
        # Ensure target is within base_path directory
        base_prefix = self.base_path if self.base_path.endswith(os.sep) else self.base_path + os.sep
        if target != self.base_path and not target.startswith(base_prefix):
            raise ValueError(f"Illegal path traversal attempt: '{item_id}'")
        return target

    def _get_rel_id(self, abs_path: str) -> str:
        rel = os.path.relpath(abs_path, self.base_path)
        return rel.replace("\\", "/")

    async def list_folders(self, parent_id: Optional[str] = None) -> List[StorageItem]:
        target_dir = self._get_abs_path(parent_id)
        if not os.path.exists(target_dir):
            return []

        folders = []
        try:
            for entry in os.scandir(target_dir):
                if entry.is_dir() and not entry.name.startswith("."):
                    rel_id = self._get_rel_id(entry.path)
                    folders.append(StorageItem(
                        id=rel_id,
                        name=entry.name,
                        is_folder=True,
                        path=rel_id,
                        parent_id=parent_id or "root",
                        modified_time=str(entry.stat().st_mtime)
                    ))
        except Exception as e:
            logger.error(f"Error listing local folders in {target_dir}: {e}")
        return sorted(folders, key=lambda f: f.name)

    async def list_files(self, folder_id: Optional[str] = None) -> List[StorageItem]:
        target_dir = self._get_abs_path(folder_id)
        if not os.path.exists(target_dir):
            return []

        files = []
        try:
            for entry in os.scandir(target_dir):
                if entry.is_file() and not entry.name.startswith("."):
                    rel_id = self._get_rel_id(entry.path)
                    mime, _ = mimetypes.guess_type(entry.name)
                    stat = entry.stat()
                    files.append(StorageItem(
                        id=rel_id,
                        name=entry.name,
                        is_folder=False,
                        path=rel_id,
                        size_bytes=stat.st_size,
                        mime_type=mime or "application/octet-stream",
                        parent_id=folder_id or "root",
                        modified_time=str(stat.st_mtime)
                    ))
        except Exception as e:
            logger.error(f"Error listing local files in {target_dir}: {e}")
        return sorted(files, key=lambda f: f.name)

    async def get_file_metadata(self, file_id: str) -> Optional[StorageFileMetadata]:
        abs_path = self._get_abs_path(file_id)
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            return None

        stat = os.stat(abs_path)
        mime, _ = mimetypes.guess_type(abs_path)
        return StorageFileMetadata(
            id=file_id,
            name=os.path.basename(abs_path),
            size_bytes=stat.st_size,
            mime_type=mime or "application/octet-stream"
        )

    async def download_file(
        self,
        file_id: str,
        destination_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        src_path = self._get_abs_path(file_id)
        if not os.path.exists(src_path):
            return False

        os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
        total_size = os.path.getsize(src_path)
        bytes_copied = 0
        chunk_size = 1024 * 1024 # 1MB chunks

        with open(src_path, "rb") as fsrc, open(destination_path, "wb") as fdst:
            while True:
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                fdst.write(chunk)
                bytes_copied += len(chunk)
                if progress_callback:
                    progress_callback(bytes_copied, total_size)

        return True

    async def read_text_file(self, file_id: str) -> Optional[str]:
        abs_path = self._get_abs_path(file_id)
        if not os.path.exists(abs_path):
            return None
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read text file {file_id}: {e}")
            return None
