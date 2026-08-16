import re
import json
import os
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.services.storage.base import StorageProvider, StorageItem, StorageScanResult
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.core.logging import logger

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def extract_day_of_month(filename: str) -> Optional[int]:
    """
    Extract day-of-month index if filename matches numeric day pattern.
    Examples:
      '1.mp4' -> 1
      '05.mp4' -> 5
      '15.mp4' -> 15
      '31.mp4' -> 31
      '15_special.mp4' -> 15
      'darshan_15.mp4' -> 15
    """
    name_without_ext = os.path.splitext(filename)[0]
    
    # 1. Exact numeric filename e.g. "15" or "01"
    if name_without_ext.isdigit():
        val = int(name_without_ext)
        if 1 <= val <= 31:
            return val

    # 2. Leading or trailing number with separator e.g. "15_aarti" or "aarti_15"
    match = re.search(r'(?:^|_)(\d{1,2})(?:_|$)', name_without_ext)
    if match:
        val = int(match.group(1))
        if 1 <= val <= 31:
            return val

    return None


class ScannerService:
    @classmethod
    async def scan_and_index(
        cls,
        db: AsyncSession,
        provider: StorageProvider,
        root_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> StorageScanResult:
        """
        Recursively scan storage provider from root_id and synchronize Folders and Videos in DB.
        """
        scan_result = StorageScanResult(root_id=root_id or "root")

        try:
            # Map of storage_folder_id -> ContentFolder ID in DB
            folder_map: Dict[str, str] = {}
            # List of (folder_storage_id, folder_name, folder_path, parent_id)
            folders_to_process: List[Tuple[str, str, str, Optional[str]]] = []

            # 1. Start from root or list top-level folders
            top_folders = await provider.list_folders(root_id)
            for tf in top_folders:
                folders_to_process.append((tf.id, tf.name, tf.name, root_id))

            # If scanning a specific subfolder directly
            if root_id and root_id != "root":
                root_name = "Folder"
                try:
                    meta = await provider.get_file_metadata(root_id)
                    if meta and meta.filename:
                        root_name = meta.filename
                except Exception:
                    pass
                folders_to_process.append((root_id, root_name, root_name, None))

            # Traverse folder hierarchy
            while folders_to_process:
                curr_id, curr_name, curr_path, parent_id = folders_to_process.pop(0)

                # Upsert ContentFolder
                stmt = select(ContentFolder).where(ContentFolder.storage_folder_id == curr_id)
                res = await db.execute(stmt)
                folder_record = res.scalars().first()

                if not folder_record:
                    folder_record = ContentFolder(
                        storage_folder_id=curr_id,
                        channel_id=channel_id,
                        name=curr_name,
                        path=curr_path
                    )
                    db.add(folder_record)
                    await db.flush()
                else:
                    folder_record.name = curr_name
                    folder_record.path = curr_path
                    if channel_id and not folder_record.channel_id:
                        folder_record.channel_id = channel_id
                    await db.flush()

                folder_map[curr_id] = folder_record.id
                scan_result.folders_found += 1

                # List files in this folder
                files_in_folder = await provider.list_files(curr_id)
                
                # Separate videos, sidecar jsons, and images
                videos: List[StorageItem] = []
                json_files: Dict[str, StorageItem] = {} # basename -> item
                image_files: Dict[str, StorageItem] = {} # basename -> item

                for item in files_in_folder:
                    base_name, ext = os.path.splitext(item.name)
                    ext_lower = ext.lower()
                    if ext_lower in VIDEO_EXTENSIONS:
                        videos.append(item)
                    elif ext_lower == ".json":
                        json_files[base_name] = item
                    elif ext_lower in IMAGE_EXTENSIONS:
                        image_files[base_name] = item

                # Process video files
                for vid in videos:
                    base_name, _ = os.path.splitext(vid.name)
                    day_index = extract_day_of_month(vid.name)

                    # Check matching sidecar json (e.g. 15.json for 15.mp4)
                    custom_metadata = None
                    if base_name in json_files:
                        json_item = json_files[base_name]
                        raw_json = await provider.read_text_file(json_item.id)
                        if raw_json:
                            try:
                                custom_metadata = json.loads(raw_json)
                                scan_result.sidecar_json_found += 1
                            except Exception as je:
                                logger.warning(f"Invalid JSON in sidecar {json_item.name}: {je}")

                    # Check matching thumbnail (e.g. 15.jpg or folder default.jpg)
                    custom_thumb_id = None
                    if base_name in image_files:
                        custom_thumb_id = image_files[base_name].id
                        scan_result.thumbnails_found += 1
                    elif "default" in image_files:
                        custom_thumb_id = image_files["default"].id
                    elif "thumbnail" in image_files:
                        custom_thumb_id = image_files["thumbnail"].id

                    # Upsert Video record
                    v_stmt = select(Video).where(Video.storage_file_id == vid.id)
                    v_res = await db.execute(v_stmt)
                    video_record = v_res.scalars().first()

                    full_video_path = f"{curr_path}/{vid.name}"

                    if not video_record:
                        video_record = Video(
                            storage_provider=provider.provider_name,
                            storage_file_id=vid.id,
                            channel_id=channel_id or folder_record.channel_id,
                            folder_id=folder_record.id,
                            filename=vid.name,
                            path=full_video_path,
                            mime_type=vid.mime_type or "video/mp4",
                            size_bytes=vid.size_bytes,
                            day_of_month_index=day_index,
                            custom_metadata=custom_metadata,
                            custom_thumbnail_file_id=custom_thumb_id,
                            enabled=True
                        )
                        db.add(video_record)
                    else:
                        video_record.filename = vid.name
                        video_record.path = full_video_path
                        video_record.size_bytes = vid.size_bytes
                        video_record.day_of_month_index = day_index
                        video_record.folder_id = folder_record.id
                        if custom_metadata:
                            video_record.custom_metadata = custom_metadata
                        if custom_thumb_id:
                            video_record.custom_thumbnail_file_id = custom_thumb_id
                        if channel_id and not video_record.channel_id:
                            video_record.channel_id = channel_id

                    scan_result.videos_found += 1

                # Subfolders inside current folder
                subfolders = await provider.list_folders(curr_id)
                for sf in subfolders:
                    folders_to_process.append((sf.id, sf.name, f"{curr_path}/{sf.name}", curr_id))

            await db.commit()
            logger.info(
                f"Scan complete for root '{root_id}': "
                f"{scan_result.folders_found} folders, {scan_result.videos_found} videos, "
                f"{scan_result.sidecar_json_found} sidecars, {scan_result.thumbnails_found} thumbnails."
            )

        except Exception as e:
            await db.rollback()
            err_msg = f"Storage scan failed: {str(e)}"
            logger.error(err_msg, exc_info=True)
            scan_result.errors.append(err_msg)

        return scan_result
