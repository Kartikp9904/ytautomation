import os
import tempfile
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from googleapiclient.http import MediaFileUpload

from app.models.channel_sync import SourceChannelSync, SyncedSourceVideo
from app.models.channel import Channel
from app.schemas.channel_sync import (
    SourceChannelSyncCreate,
    SourceChannelSyncUpdate,
    SourceChannelSyncResponse,
    SyncedSourceVideoResponse,
    SyncTriggerResponse,
)
from app.services.youtube.youtube_oauth import YouTubeOAuthService
from app.services.youtube.quota_tracker import YouTubeQuotaTracker, QUOTA_VIDEO_UPLOAD
from app.core.config import settings
from app.core.logging import logger

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class ChannelSyncService:
    @classmethod
    async def list_sync_configs(cls, db: AsyncSession) -> List[SourceChannelSyncResponse]:
        stmt = select(SourceChannelSync).order_by(SourceChannelSync.created_at.desc())
        res = await db.execute(stmt)
        configs = res.scalars().all()

        if not configs:
            return []

        # Fetch channel names in one query to avoid async lazy loading
        ch_stmt = select(Channel.id, Channel.name)
        ch_res = await db.execute(ch_stmt)
        channel_names = {row[0]: row[1] for row in ch_res.all()}

        # Fetch video counts
        total_counts = {}
        uploaded_counts = {}

        v_stmt = select(SyncedSourceVideo.sync_id, func.count(SyncedSourceVideo.id)).group_by(SyncedSourceVideo.sync_id)
        v_res = await db.execute(v_stmt)
        for sync_id, count in v_res.all():
            total_counts[sync_id] = count

        up_stmt = select(SyncedSourceVideo.sync_id, func.count(SyncedSourceVideo.id)).where(
            SyncedSourceVideo.upload_status == "UPLOADED"
        ).group_by(SyncedSourceVideo.sync_id)
        up_res = await db.execute(up_stmt)
        for sync_id, count in up_res.all():
            uploaded_counts[sync_id] = count

        responses = []
        for cfg in configs:
            total_videos = total_counts.get(cfg.id, 0)
            uploaded_videos = uploaded_counts.get(cfg.id, 0)
            target_ch_name = channel_names.get(cfg.target_channel_id)

            responses.append(SourceChannelSyncResponse(
                id=cfg.id,
                source_channel_url=cfg.source_channel_url,
                source_channel_name=cfg.source_channel_name,
                source_channel_id=cfg.source_channel_id,
                target_channel_id=cfg.target_channel_id,
                target_channel_name=target_ch_name,
                sync_mode=cfg.sync_mode,
                auto_publish=cfg.auto_publish,
                publish_privacy_status=cfg.publish_privacy_status,
                title_prefix=cfg.title_prefix,
                title_suffix=cfg.title_suffix,
                description_footer=cfg.description_footer,
                custom_tags=cfg.custom_tags or [],
                enabled=cfg.enabled,
                last_synced_at=cfg.last_synced_at,
                last_error=cfg.last_error,
                videos_synced_count=total_videos,
                videos_uploaded_count=uploaded_videos,
                created_at=cfg.created_at,
                updated_at=cfg.updated_at
            ))

        return responses

    @classmethod
    async def get_sync_config(cls, db: AsyncSession, sync_id: str) -> Optional[SourceChannelSync]:
        stmt = select(SourceChannelSync).where(SourceChannelSync.id == sync_id)
        res = await db.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def create_sync_config(cls, db: AsyncSession, data: SourceChannelSyncCreate) -> SourceChannelSync:
        # Validate target channel exists
        ch_stmt = select(Channel).where(Channel.id == data.target_channel_id)
        ch_res = await db.execute(ch_stmt)
        if not ch_res.scalars().first():
            raise ValueError(f"Target channel with ID '{data.target_channel_id}' not found.")

        # Clean URL/handle
        clean_url = data.source_channel_url.strip()
        if clean_url.startswith("@"):
            clean_url = f"https://www.youtube.com/{clean_url}/videos"
        elif "youtube.com" in clean_url and not any(clean_url.endswith(x) for x in ["/videos", "/shorts"]):
            clean_url = f"{clean_url.rstrip('/')}/videos"

        cfg = SourceChannelSync(
            source_channel_url=clean_url,
            target_channel_id=data.target_channel_id,
            sync_mode=data.sync_mode,
            auto_publish=data.auto_publish,
            publish_privacy_status=data.publish_privacy_status,
            title_prefix=data.title_prefix,
            title_suffix=data.title_suffix,
            description_footer=data.description_footer,
            custom_tags=data.custom_tags or [],
            enabled=data.enabled
        )
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
        return cfg

    @classmethod
    async def update_sync_config(cls, db: AsyncSession, sync_id: str, data: SourceChannelSyncUpdate) -> Optional[SourceChannelSync]:
        cfg = await cls.get_sync_config(db, sync_id)
        if not cfg:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(cfg, field, val)

        await db.commit()
        await db.refresh(cfg)
        return cfg

    @classmethod
    async def delete_sync_config(cls, db: AsyncSession, sync_id: str) -> bool:
        cfg = await cls.get_sync_config(db, sync_id)
        if not cfg:
            return False
        await db.delete(cfg)
        await db.commit()
        return True

    @classmethod
    async def list_synced_videos(cls, db: AsyncSession, sync_id: Optional[str] = None) -> List[SyncedSourceVideoResponse]:
        stmt = select(SyncedSourceVideo)
        if sync_id:
            stmt = stmt.where(SyncedSourceVideo.sync_id == sync_id)
        stmt = stmt.order_by(SyncedSourceVideo.created_at.desc())
        
        res = await db.execute(stmt)
        videos = res.scalars().all()
        return [SyncedSourceVideoResponse.model_validate(v) for v in videos]

    @classmethod
    def _extract_channel_metadata_sync(cls, channel_url: str, limit: int = 15) -> Dict[str, Any]:
        """Runs yt-dlp to inspect source channel and list recent videos"""
        if not yt_dlp:
            raise RuntimeError("yt-dlp is not installed in the environment.")

        ydl_opts = {
            'extract_flat': True,
            'playlistend': limit,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return info or {}

    @classmethod
    def _download_video_and_metadata_sync(cls, video_url: str, output_dir: str) -> Dict[str, Any]:
        """Downloads the single video and extracts detailed metadata (tags, description, full resolution)"""
        if not yt_dlp:
            raise RuntimeError("yt-dlp is not installed in the environment.")

        out_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'writethumbnail': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_id = info.get("id")
            ext = info.get("ext", "mp4")
            expected_filepath = os.path.join(output_dir, f"{video_id}.{ext}")
            
            # Find matching downloaded video file
            found_path = None
            if os.path.exists(expected_filepath):
                found_path = expected_filepath
            else:
                for f in os.listdir(output_dir):
                    if f.startswith(video_id) and not f.endswith(('.jpg', '.png', '.webp', '.part')):
                        found_path = os.path.join(output_dir, f)
                        break

            return {
                "info": info,
                "filepath": found_path
            }

    @classmethod
    async def sync_channel(
        cls,
        db: AsyncSession,
        sync_id: str,
        max_videos_to_download: int = 5
    ) -> SyncTriggerResponse:
        """
        Executes full sync pipeline:
        1. Queries source channel using yt-dlp
        2. Filters out existing/duplicate videos
        3. Downloads newest videos
        4. If auto_publish is on, uploads to target YouTube channel
        """
        cfg = await cls.get_sync_config(db, sync_id)
        if not cfg:
            raise ValueError(f"Sync configuration with ID '{sync_id}' not found.")

        logger.info(f"Starting channel sync for '{cfg.source_channel_url}' -> target channel ID {cfg.target_channel_id}...")

        temp_dir = tempfile.mkdtemp(prefix="yt_sync_")
        videos_found = 0
        videos_downloaded = 0
        videos_uploaded = 0

        try:
            # 1. Extract channel listing
            channel_info = await asyncio.to_thread(cls._extract_channel_metadata_sync, cfg.source_channel_url, 15)
            entries = channel_info.get("entries") or []
            cfg.source_channel_name = channel_info.get("uploader") or channel_info.get("channel") or cfg.source_channel_name
            cfg.source_channel_id = channel_info.get("channel_id") or cfg.source_channel_id
            cfg.last_synced_at = datetime.now(timezone.utc)
            cfg.last_error = None
            await db.commit()

            videos_found = len(entries)
            logger.info(f"Source channel '{cfg.source_channel_name}' returned {videos_found} videos.")

            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get("id")
                if not v_id:
                    continue

                # Check duplicate
                dup_stmt = select(SyncedSourceVideo).where(SyncedSourceVideo.source_video_id == v_id)
                dup_res = await db.execute(dup_stmt)
                if dup_res.scalars().first():
                    continue # Already processed, skip

                v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                v_title = entry.get("title") or "Untitled Video"
                v_duration = entry.get("duration") or 0
                is_short = bool(v_duration and v_duration <= 65) or ("/shorts/" in v_url)

                # Check mode filter
                if cfg.sync_mode == "SHORTS_ONLY" and not is_short:
                    continue
                if cfg.sync_mode == "FULL_VIDEOS_ONLY" and is_short:
                    continue

                # Check if we hit limit per sync run
                if videos_downloaded >= max_videos_to_download:
                    break

                # Create record
                synced_video = SyncedSourceVideo(
                    sync_id=cfg.id,
                    source_video_id=v_id,
                    source_url=v_url,
                    title=v_title,
                    description=entry.get("description") or "",
                    tags=entry.get("tags") or [],
                    thumbnail_url=entry.get("thumbnail"),
                    duration_seconds=v_duration,
                    is_short=is_short,
                    download_status="DOWNLOADING",
                    upload_status="PENDING"
                )
                db.add(synced_video)
                await db.commit()
                await db.refresh(synced_video)

                # Download video & full metadata
                try:
                    logger.info(f"Downloading source video '{v_title}' ({v_id})...")
                    dl_result = await asyncio.to_thread(cls._download_video_and_metadata_sync, v_url, temp_dir)
                    full_info = dl_result.get("info") or {}
                    filepath = dl_result.get("filepath")

                    if filepath and os.path.exists(filepath):
                        synced_video.local_temp_path = filepath
                        synced_video.download_status = "DOWNLOADED"
                        synced_video.title = full_info.get("title") or synced_video.title
                        synced_video.description = full_info.get("description") or synced_video.description
                        synced_video.tags = full_info.get("tags") or synced_video.tags
                        synced_video.category_id = str(full_info.get("categories", ["20"])[0]) if full_info.get("categories") else "20"
                        await db.commit()
                        videos_downloaded += 1
                    else:
                        synced_video.download_status = "FAILED"
                        synced_video.error_message = "File was not saved by downloader."
                        await db.commit()
                        continue

                    # 4. Auto-Publish if enabled
                    if cfg.auto_publish and synced_video.download_status == "DOWNLOADED":
                        await cls.upload_synced_video(db, synced_video.id)
                        videos_uploaded += 1

                except Exception as dl_err:
                    logger.error(f"Failed to download/process video {v_id}: {dl_err}", exc_info=True)
                    synced_video.download_status = "FAILED"
                    synced_video.error_message = str(dl_err)
                    await db.commit()

            return SyncTriggerResponse(
                success=True,
                message=f"Sync completed successfully. Found {videos_found} videos, downloaded {videos_downloaded}, uploaded {videos_uploaded}.",
                videos_found=videos_found,
                videos_downloaded=videos_downloaded,
                videos_uploaded=videos_uploaded
            )

        except Exception as e:
            logger.error(f"Channel sync failed for {cfg.source_channel_url}: {e}", exc_info=True)
            cfg.last_error = str(e)
            await db.commit()
            return SyncTriggerResponse(
                success=False,
                message=f"Sync failed: {str(e)}",
                videos_found=videos_found,
                videos_downloaded=videos_downloaded,
                videos_uploaded=videos_uploaded
            )

    @classmethod
    async def upload_synced_video(cls, db: AsyncSession, synced_video_id: str) -> SyncedSourceVideo:
        """Uploads a downloaded synced video to the target YouTube channel"""
        stmt = select(SyncedSourceVideo).where(SyncedSourceVideo.id == synced_video_id)
        res = await db.execute(stmt)
        v = res.scalars().first()
        if not v:
            raise ValueError(f"Synced video with ID '{synced_video_id}' not found.")

        cfg = v.sync_config
        if not cfg:
            raise ValueError("Associated source channel sync config not found.")

        target_channel = cfg.target_channel
        if not target_channel:
            raise ValueError(f"Target YouTube channel with ID '{cfg.target_channel_id}' not found.")

        if not v.local_temp_path or not os.path.exists(v.local_temp_path):
            # Re-download if file missing
            temp_dir = tempfile.mkdtemp(prefix="yt_upload_")
            dl_result = await asyncio.to_thread(cls._download_video_and_metadata_sync, v.source_url, temp_dir)
            v.local_temp_path = dl_result.get("filepath")
            if not v.local_temp_path or not os.path.exists(v.local_temp_path):
                raise ValueError(f"Could not locate downloaded file for video '{v.title}'.")

        v.upload_status = "UPLOADING"
        await db.commit()

        try:
            # 1. Authenticate with target YouTube channel
            youtube = await YouTubeOAuthService.get_authenticated_service(target_channel.id, db)

            # 2. Format title, description, and tags
            final_title = v.title
            if cfg.title_prefix:
                final_title = f"{cfg.title_prefix.strip()} {final_title}"
            if cfg.title_suffix:
                final_title = f"{final_title} {cfg.title_suffix.strip()}"
            final_title = final_title[:100]

            final_desc = v.description or ""
            if cfg.description_footer:
                final_desc = f"{final_desc}\n\n{cfg.description_footer.strip()}"
            final_desc = final_desc[:5000]

            combined_tags = (v.tags or []) + (cfg.custom_tags or [])
            safe_tags = []
            cur_len = 0
            for t in combined_tags:
                clean_tag = str(t).strip()
                if not clean_tag:
                    continue
                if cur_len + len(clean_tag) + 1 <= 490:
                    safe_tags.append(clean_tag)
                    cur_len += len(clean_tag) + 1
                else:
                    break

            # 3. Build metadata payload
            body = {
                "snippet": {
                    "title": final_title,
                    "description": final_desc,
                    "tags": safe_tags,
                    "categoryId": str(v.category_id or "20")
                },
                "status": {
                    "privacyStatus": cfg.publish_privacy_status.lower(),
                    "selfDeclaredMadeForKids": False
                }
            }

            media_body = MediaFileUpload(
                v.local_temp_path,
                mimetype="video/*",
                chunksize=1024 * 1024 * 5,
                resumable=True
            )

            insert_request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media_body
            )

            # Execute resumable upload
            response = None
            while response is None:
                status, response = await asyncio.to_thread(insert_request.next_chunk)
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress for synced video '{final_title}': {progress}%")

            yt_video_id = response.get("id")
            if not yt_video_id:
                raise ValueError("YouTube API did not return video ID upon upload completion.")

            await YouTubeQuotaTracker.record_quota_usage(target_channel.id, QUOTA_VIDEO_UPLOAD, db)

            v.uploaded_youtube_video_id = yt_video_id
            v.uploaded_youtube_url = f"https://youtu.be/{yt_video_id}"
            v.upload_status = "UPLOADED"
            v.error_message = None
            await db.commit()
            await db.refresh(v)

            logger.info(f"Successfully uploaded synced video '{final_title}' -> https://youtu.be/{yt_video_id}")

            # Clean up local file
            try:
                if v.local_temp_path and os.path.exists(v.local_temp_path):
                    os.remove(v.local_temp_path)
            except Exception:
                pass

            return v

        except Exception as up_err:
            logger.error(f"Failed to upload synced video {v.id}: {up_err}", exc_info=True)
            v.upload_status = "FAILED"
            v.error_message = str(up_err)
            await db.commit()
            raise up_err
