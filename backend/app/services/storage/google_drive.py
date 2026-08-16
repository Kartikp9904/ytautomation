import io
import os
import json
from typing import List, Optional, Callable, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from app.services.storage.base import StorageProvider, StorageItem, StorageFileMetadata
from app.core.config import settings
from app.core.logging import logger
from app.core.security import decrypt_token


class GoogleDriveStorageProvider(StorageProvider):
    DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self, encrypted_refresh_token: Optional[str] = None):
        self.encrypted_refresh_token = encrypted_refresh_token
        self._service = None

    @property
    def provider_name(self) -> str:
        return "google_drive"

    def _get_service(self):
        if self._service is not None:
            return self._service

        if not self.encrypted_refresh_token or not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return None

        try:
            refresh_token = decrypt_token(self.encrypted_refresh_token)
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/drive.readonly"]
            )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
            return self._service
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            return None

    async def is_connected(self) -> bool:
        service = self._get_service()
        if not service:
            return False
        try:
            # Quick query to test token validity
            service.files().list(pageSize=1, fields="files(id)").execute()
            return True
        except Exception as e:
            logger.warning(f"Google Drive connection check failed: {e}")
            return False

    async def list_folders(self, parent_id: Optional[str] = None) -> List[StorageItem]:
        service = self._get_service()
        if not service:
            return []

        query = f"mimeType = '{self.DRIVE_FOLDER_MIME}' and trashed = false"
        if parent_id and parent_id != "root":
            query += f" and '{parent_id}' in parents"
        else:
            # Top-level or root folders
            query += " and ('root' in parents or sharedWithMe = true)"

        items: List[StorageItem] = []
        page_token = None
        try:
            while True:
                response = service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime)",
                    pageToken=page_token,
                    pageSize=100
                ).execute()

                for f in response.get("files", []):
                    items.append(StorageItem(
                        id=f["id"],
                        name=f["name"],
                        is_folder=True,
                        path=f["name"],
                        parent_id=f.get("parents", [None])[0],
                        modified_time=f.get("modifiedTime")
                    ))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"Error querying Drive folders: {e}")

        return sorted(items, key=lambda x: x.name)

    async def list_files(self, folder_id: Optional[str] = None) -> List[StorageItem]:
        service = self._get_service()
        if not service:
            return []

        query = f"mimeType != '{self.DRIVE_FOLDER_MIME}' and trashed = false"
        if folder_id and folder_id != "root":
            query += f" and '{folder_id}' in parents"
        else:
            query += " and 'root' in parents"

        items: List[StorageItem] = []
        page_token = None
        try:
            while True:
                response = service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime)",
                    pageToken=page_token,
                    pageSize=100
                ).execute()

                for f in response.get("files", []):
                    items.append(StorageItem(
                        id=f["id"],
                        name=f["name"],
                        is_folder=False,
                        path=f["name"],
                        size_bytes=int(f.get("size", 0)),
                        mime_type=f.get("mimeType"),
                        parent_id=f.get("parents", [None])[0],
                        modified_time=f.get("modifiedTime")
                    ))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"Error querying Drive files: {e}")

        return sorted(items, key=lambda x: x.name)

    async def get_file_metadata(self, file_id: str) -> Optional[StorageFileMetadata]:
        service = self._get_service()
        if not service:
            return None
        try:
            f = service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, md5Checksum"
            ).execute()
            return StorageFileMetadata(
                id=f["id"],
                name=f["name"],
                size_bytes=int(f.get("size", 0)),
                mime_type=f.get("mimeType", "application/octet-stream"),
                md5_checksum=f.get("md5Checksum")
            )
        except Exception as e:
            logger.error(f"Error fetching Drive file metadata for {file_id}: {e}")
            return None

    async def download_file(
        self,
        file_id: str,
        destination_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        service = self._get_service()
        if not service:
            return False

        try:
            metadata = await self.get_file_metadata(file_id)
            total_size = metadata.size_bytes if metadata else 0

            parent_dir = os.path.dirname(os.path.abspath(destination_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            request = service.files().get_media(fileId=file_id)
            with open(destination_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024 * 5) # 5MB chunks
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status and progress_callback:
                        progress_callback(int(status.resumable_progress), total_size or int(status.total_size))
            return True
        except Exception as e:
            logger.error(f"Failed to download Google Drive file {file_id}: {e}")
            return False

    async def read_text_file(self, file_id: str) -> Optional[str]:
        service = self._get_service()
        if not service:
            return None
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read Drive text file {file_id}: {e}")
            return None
