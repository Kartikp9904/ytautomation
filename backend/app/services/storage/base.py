from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any
from pydantic import BaseModel


class StorageItem(BaseModel):
    id: str
    name: str
    is_folder: bool
    path: str
    size_bytes: int = 0
    mime_type: Optional[str] = None
    parent_id: Optional[str] = None
    modified_time: Optional[str] = None


class StorageFileMetadata(BaseModel):
    id: str
    name: str
    size_bytes: int
    mime_type: str
    md5_checksum: Optional[str] = None


class StorageScanResult(BaseModel):
    root_id: str
    folders_found: int = 0
    videos_found: int = 0
    sidecar_json_found: int = 0
    thumbnails_found: int = 0
    errors: List[str] = []


class StorageProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the storage provider e.g. 'google_drive' or 'local'."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if storage provider credentials/paths are valid and accessible."""
        pass

    @abstractmethod
    async def list_folders(self, parent_id: Optional[str] = None) -> List[StorageItem]:
        """List subfolders within a parent folder (or root if None)."""
        pass

    @abstractmethod
    async def list_files(self, folder_id: Optional[str] = None) -> List[StorageItem]:
        """List files directly inside a folder."""
        pass

    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> Optional[StorageFileMetadata]:
        """Retrieve file size, name, and mime type."""
        pass

    @abstractmethod
    async def download_file(
        self,
        file_id: str,
        destination_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download file to destination_path (with optional progress tracking)."""
        pass

    @abstractmethod
    async def read_text_file(self, file_id: str) -> Optional[str]:
        """Read text content of a file (e.g. sidecar JSON)."""
        pass
