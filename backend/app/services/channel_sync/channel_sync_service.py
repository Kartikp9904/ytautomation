import os
import tempfile
import asyncio
import re
import shutil
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from googleapiclient.http import MediaFileUpload

from app.core.database import AsyncSessionLocal
from app.models.channel_sync import SourceChannelSync, SyncedSourceVideo
from app.models.channel import Channel
from app.models.setting import SystemSetting
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
    def normalize_channel_url(cls, raw_url: str, sync_mode: str = "ALL") -> str:
        """
        Normalizes handles/URLs and ensures correct tab target (/shorts vs /videos).
        """
        clean = raw_url.strip().rstrip("/")
        if clean.startswith("@"):
            clean = f"https://www.youtube.com/{clean}"
        elif "youtube.com" not in clean and not clean.startswith("http"):
            if clean.startswith("UC"):
                clean = f"https://www.youtube.com/channel/{clean}"
            else:
                clean = f"https://www.youtube.com/@{clean.lstrip('@')}"

        # Strip any subtab suffix (/videos, /shorts, /featured, /streams, /community)
        base = re.sub(r'/(videos|shorts|featured|streams|community)/?$', '', clean)

        if sync_mode == "SHORTS_ONLY":
            return f"{base}/shorts"
        elif sync_mode == "FULL_VIDEOS_ONLY":
            return f"{base}/videos"
        else:
            return base

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
                publish_mode=cfg.publish_mode or "SCHEDULED",
                daily_publish_count=cfg.daily_publish_count or 3,
                publish_time_slots=cfg.publish_time_slots or ["10:00", "15:00", "20:00"],
                timezone=cfg.timezone or "UTC",
                max_video_size_mb=cfg.max_video_size_mb or 300,
                last_scheduled_slot_published=cfg.last_scheduled_slot_published,
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

        # Clean & normalize URL according to sync mode
        clean_url = cls.normalize_channel_url(data.source_channel_url, data.sync_mode)

        cfg = SourceChannelSync(
            source_channel_url=clean_url,
            target_channel_id=data.target_channel_id,
            sync_mode=data.sync_mode,
            auto_publish=data.auto_publish,
            publish_privacy_status=data.publish_privacy_status,
            publish_mode=data.publish_mode or "SCHEDULED",
            daily_publish_count=data.daily_publish_count or 3,
            publish_time_slots=data.publish_time_slots or ["10:00", "15:00", "20:00"],
            timezone=data.timezone or "UTC",
            max_video_size_mb=data.max_video_size_mb or 300,
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
        if "source_channel_url" in update_data:
            target_mode = update_data.get("sync_mode", cfg.sync_mode)
            update_data["source_channel_url"] = cls.normalize_channel_url(update_data["source_channel_url"], target_mode)
        elif "sync_mode" in update_data:
            update_data["source_channel_url"] = cls.normalize_channel_url(cfg.source_channel_url, update_data["sync_mode"])

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
    def _write_cookies_to_disk(cls, cookies_text: str) -> str:
        os.makedirs(settings.TEMP_STORAGE_PATH, exist_ok=True)
        target_path = os.path.join(settings.TEMP_STORAGE_PATH, "cookies.txt")
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(cookies_text.strip())
        return target_path

    @classmethod
    def _get_cookiefile_option(cls) -> Optional[str]:
        """Resolves optional cookies file from environment, temp_storage, or local path"""
        custom_path = os.environ.get("YOUTUBE_COOKIES_FILE")
        if custom_path and os.path.exists(custom_path) and os.path.getsize(custom_path) > 0:
            return custom_path

        temp_storage_cookie = os.path.join(settings.TEMP_STORAGE_PATH, "cookies.txt")
        if os.path.exists(temp_storage_cookie) and os.path.getsize(temp_storage_cookie) > 0:
            return os.path.abspath(temp_storage_cookie)

        for name in ["cookies.txt", "youtube_cookies.txt", os.path.join("temp_storage", "cookies.txt")]:
            if os.path.exists(name) and os.path.getsize(name) > 0:
                return os.path.abspath(name)

        raw_cookies = os.environ.get("YOUTUBE_COOKIES")
        if raw_cookies and raw_cookies.strip():
            temp_cookie_path = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
            try:
                with open(temp_cookie_path, "w", encoding="utf-8") as f:
                    f.write(raw_cookies.strip())
                return temp_cookie_path
            except Exception:
                pass

        return None

    @classmethod
    async def get_cookies_status(cls, db: AsyncSession) -> Dict[str, Any]:
        """Checks if YouTube cookies are available and active"""
        file_path = cls._get_cookiefile_option()
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return {
                "has_cookies": True,
                "source": "file",
                "file_path": os.path.basename(file_path),
                "size_bytes": os.path.getsize(file_path)
            }

        # Check DB
        stmt = select(SystemSetting).where(SystemSetting.key == "youtube_cookies")
        res = await db.execute(stmt)
        setting = res.scalars().first()
        if setting and setting.value and isinstance(setting.value, dict) and setting.value.get("cookies"):
            cls._write_cookies_to_disk(setting.value["cookies"])
            return {
                "has_cookies": True,
                "source": "database",
                "updated_at": setting.value.get("updated_at")
            }

        return {
            "has_cookies": False,
            "source": None
        }

    @classmethod
    async def save_cookies(cls, db: AsyncSession, cookies_text: str) -> Dict[str, Any]:
        """Saves Netscape-format YouTube cookies into database and disk"""
        clean_text = cookies_text.strip()
        if not clean_text:
            raise ValueError("Cookies text cannot be empty.")

        cls._write_cookies_to_disk(clean_text)

        stmt = select(SystemSetting).where(SystemSetting.key == "youtube_cookies")
        res = await db.execute(stmt)
        setting = res.scalars().first()

        now_str = datetime.now(timezone.utc).isoformat()
        if setting:
            setting.value = {"cookies": clean_text, "updated_at": now_str}
        else:
            setting = SystemSetting(
                key="youtube_cookies",
                value={"cookies": clean_text, "updated_at": now_str},
                description="YouTube cookies for yt-dlp authenticated extraction and downloads"
            )
            db.add(setting)

        await db.commit()
        logger.info("Successfully saved and synced YouTube cookies.")
        return {"success": True, "message": "Cookies successfully saved and activated."}

    @classmethod
    async def delete_cookies(cls, db: AsyncSession) -> Dict[str, Any]:
        """Deletes cookies from database and local storage"""
        target_path = os.path.join(settings.TEMP_STORAGE_PATH, "cookies.txt")
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass

        stmt = delete(SystemSetting).where(SystemSetting.key == "youtube_cookies")
        await db.execute(stmt)
        await db.commit()
        logger.info("YouTube cookies removed from disk and database.")
        return {"success": True, "message": "Cookies removed."}

    @classmethod
    async def restore_cookies_from_db(cls):
        """Restores cookies from DB on startup if not present on disk"""
        try:
            target_path = os.path.join(settings.TEMP_STORAGE_PATH, "cookies.txt")
            if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                return

            async with AsyncSessionLocal() as session:
                stmt = select(SystemSetting).where(SystemSetting.key == "youtube_cookies")
                res = await session.execute(stmt)
                setting = res.scalars().first()
                if setting and setting.value and isinstance(setting.value, dict) and setting.value.get("cookies"):
                    cls._write_cookies_to_disk(setting.value["cookies"])
                    logger.info("Restored YouTube cookies from database to local temp_storage.")
        except Exception as e:
            logger.warning(f"Could not restore cookies from database: {e}")

    @classmethod
    def _extract_channel_metadata_sync(cls, channel_url: str, limit: int = 15) -> Dict[str, Any]:
        """Runs yt-dlp to inspect source channel and list recent videos with fallback strategies"""
        if not yt_dlp:
            raise RuntimeError("yt-dlp is not installed in the environment.")

        cookie_file = cls._get_cookiefile_option()
        has_cookies = bool(cookie_file and os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 0)
        node_available = bool(shutil.which('node'))

        strategies = []
        if has_cookies:
            # When browser cookies are available, use standard web client first
            strategies.append({"name": "authenticated_web", "player_client": None, "use_cookie": True})
            strategies.append({"name": "authenticated_android_web", "player_client": ["android", "web"], "use_cookie": True})
        strategies.extend([
            {"name": "android_web_no_cookie", "player_client": ["android", "web"], "use_cookie": False},
            {"name": "android_only", "player_client": ["android"], "use_cookie": False},
            {"name": "default_web_no_cookie", "player_client": None, "use_cookie": False},
        ])

        last_err = None
        for strat in strategies:
            ydl_opts: Dict[str, Any] = {
                'extract_flat': True,
                'playlistend': limit,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
            }
            if node_available:
                ydl_opts['js_runtimes'] = {'node': {}}

            if strat.get("use_cookie") and has_cookies and cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            if strat.get("player_client"):
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': strat["player_client"]
                    }
                }

            try:
                logger.info(f"Extracting channel metadata for '{channel_url}' using strategy '{strat['name']}' (cookies: {bool(ydl_opts.get('cookiefile'))})...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(channel_url, download=False)
                    if info and (info.get("entries") or info.get("title")):
                        return info
            except Exception as e:
                logger.warning(f"Channel metadata strategy '{strat['name']}' failed for {channel_url}: {e}")
                last_err = e

        if last_err:
            raise last_err
        return {}

    @classmethod
    def _download_video_and_metadata_sync(cls, video_url: str, output_dir: str) -> Dict[str, Any]:
        """Downloads single video and extracts detailed metadata with multi-strategy fallbacks and ffmpeg remuxing"""
        if not yt_dlp:
            raise RuntimeError("yt-dlp is not installed in the environment.")

        out_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        cookie_file = cls._get_cookiefile_option()
        has_cookies = bool(cookie_file and os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 0)
        node_available = bool(shutil.which('node'))
        has_ffmpeg = bool(shutil.which('ffmpeg'))

        strategies = []
        if has_cookies:
            # If user provided authenticated browser cookies, use standard web client first
            strategies.append({"name": "authenticated_web", "player_client": None, "use_cookie": True})
            strategies.append({"name": "authenticated_android_web", "player_client": ["android", "web"], "use_cookie": True})
        strategies.extend([
            {"name": "android_web_no_cookie", "player_client": ["android", "web"], "use_cookie": False},
            {"name": "android_only", "player_client": ["android"], "use_cookie": False},
            {"name": "default_web_no_cookie", "player_client": None, "use_cookie": False},
        ])

        last_err = None
        for strat in strategies:
            ydl_opts: Dict[str, Any] = {
                'format': 'bv*+ba/b',
                'outtmpl': out_template,
                'quiet': True,
                'no_warnings': True,
                'writethumbnail': True,
            }
            if has_ffmpeg:
                ydl_opts['merge_output_format'] = 'mp4'
                ydl_opts['postprocessors'] = [
                    {
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }
                ]

            if node_available:
                ydl_opts['js_runtimes'] = {'node': {}}

            if strat.get("use_cookie") and has_cookies and cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            if strat.get("player_client"):
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': strat["player_client"]
                    }
                }

            try:
                logger.info(f"Downloading video '{video_url}' with strategy '{strat['name']}' (cookies: {bool(ydl_opts.get('cookiefile'))})...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    if not info:
                        continue

                    video_id = info.get("id")
                    ext = info.get("ext", "mp4")
                    expected_filepath = os.path.join(output_dir, f"{video_id}.{ext}")

                    found_path = None
                    if os.path.exists(expected_filepath):
                        found_path = expected_filepath
                    else:
                        for f in os.listdir(output_dir):
                            if video_id and f.startswith(video_id) and not f.endswith(('.jpg', '.png', '.webp', '.part', '.mhtml', '.json', '.temp')):
                                found_path = os.path.join(output_dir, f)
                                break

                    if found_path and os.path.exists(found_path):
                        logger.info(f"Successfully downloaded video '{video_url}' via strategy '{strat['name']}' -> {found_path}")
                        return {
                            "info": info,
                            "filepath": found_path
                        }
            except Exception as e:
                logger.warning(f"Download strategy '{strat['name']}' failed for {video_url}: {e}")
                last_err = e

        if last_err:
            raise last_err
        raise RuntimeError(f"All download strategies failed for {video_url}.")

    @classmethod
    async def sync_channel(
        cls,
        db: AsyncSession,
        sync_id: str,
        max_videos_to_download: int = 5
    ) -> SyncTriggerResponse:
        """
        Executes full sync pipeline:
        1. Formulates target URLs based on sync_mode (/shorts vs /videos vs both)
        2. Queries source channel using yt-dlp flat extraction
        3. Filters out existing/duplicate videos
        4. Ingests video metadata records into SyncedSourceVideo (STAGED)
        5. If publish_mode is IMMEDIATE or auto_publish is True, immediately uploads
        """
        cfg = await cls.get_sync_config(db, sync_id)
        if not cfg:
            raise ValueError(f"Sync configuration with ID '{sync_id}' not found.")

        logger.info(f"Starting channel sync for '{cfg.source_channel_url}' (mode: {cfg.sync_mode}) -> target channel ID {cfg.target_channel_id}...")

        videos_found = 0
        videos_downloaded = 0
        videos_uploaded = 0

        try:
            # Clean and isolate base channel URL
            clean_url = cfg.source_channel_url.strip().rstrip('/')
            base_url = re.sub(r'/(videos|shorts|featured|streams|community)/?$', '', clean_url)

            # Determine tab targets to scan based on sync_mode
            scan_targets = []
            if cfg.sync_mode == "SHORTS_ONLY":
                scan_targets.append((f"{base_url}/shorts", True))
            elif cfg.sync_mode == "FULL_VIDEOS_ONLY":
                scan_targets.append((f"{base_url}/videos", False))
            else: # "ALL"
                # Scan both tabs so both Shorts and Full Videos are discovered
                scan_targets.append((f"{base_url}/shorts", True))
                scan_targets.append((f"{base_url}/videos", False))

            entries_to_process = []
            for scan_url, is_shorts_tab in scan_targets:
                try:
                    c_info = await asyncio.to_thread(cls._extract_channel_metadata_sync, scan_url, 15)
                    uploader = c_info.get("uploader") or c_info.get("channel")
                    if uploader and not cfg.source_channel_name:
                        cfg.source_channel_name = uploader
                    ch_id = c_info.get("channel_id")
                    if ch_id and not cfg.source_channel_id:
                        cfg.source_channel_id = ch_id

                    tab_entries = c_info.get("entries") or []
                    for e in tab_entries:
                        if e and e.get("id"):
                            entries_to_process.append((e, is_shorts_tab))
                except Exception as ext_err:
                    logger.warning(f"Error querying source tab {scan_url}: {ext_err}")

            cfg.last_synced_at = datetime.now(timezone.utc)
            cfg.last_error = None
            await db.commit()

            videos_found = len(entries_to_process)
            logger.info(f"Source channel '{cfg.source_channel_name}' returned {videos_found} candidates across scanned tabs.")

            for entry, is_shorts_tab in entries_to_process:
                v_id = entry.get("id")
                if not v_id:
                    continue

                # Check duplicate
                dup_stmt = select(SyncedSourceVideo).where(
                    SyncedSourceVideo.sync_id == cfg.id,
                    SyncedSourceVideo.source_video_id == v_id
                )
                dup_res = await db.execute(dup_stmt)
                if dup_res.scalars().first():
                    continue # Already processed, skip

                v_title = entry.get("title") or "Untitled Video"
                v_duration = entry.get("duration") or 0

                if is_shorts_tab:
                    is_short = True
                    v_url = entry.get("url") or f"https://www.youtube.com/shorts/{v_id}"
                    if "shorts" not in v_url and "watch" not in v_url:
                        v_url = f"https://www.youtube.com/shorts/{v_id}"
                else:
                    v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                    is_short = bool(v_duration and v_duration <= 65) or ("/shorts/" in (entry.get("url") or ""))

                # Check mode filter
                if cfg.sync_mode == "SHORTS_ONLY" and not is_short:
                    continue
                if cfg.sync_mode == "FULL_VIDEOS_ONLY" and is_short:
                    continue

                # Check if we hit limit per sync run
                if videos_downloaded >= max_videos_to_download:
                    break

                # Resolve thumbnail with fallback
                thumb = entry.get("thumbnail")
                if isinstance(thumb, list) and len(thumb) > 0:
                    thumb = thumb[-1].get("url")
                if not thumb or not isinstance(thumb, str):
                    thumb = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"

                # Create record - STAGED (Metadata only stored in DB! Zero video file bytes on disk)
                synced_video = SyncedSourceVideo(
                    sync_id=cfg.id,
                    source_video_id=v_id,
                    source_url=v_url,
                    title=v_title,
                    description=entry.get("description") or "",
                    tags=entry.get("tags") or [],
                    thumbnail_url=thumb,
                    duration_seconds=v_duration if v_duration else None,
                    is_short=is_short,
                    download_status="STAGED",
                    upload_status="PENDING"
                )
                db.add(synced_video)
                await db.commit()
                await db.refresh(synced_video)
                videos_downloaded += 1

                # If IMMEDIATE mode or legacy auto_publish is set, trigger single upload right away
                if (cfg.publish_mode == "IMMEDIATE" or cfg.auto_publish):
                    try:
                        logger.info(f"Immediate publish mode enabled: uploading video '{v_title}' ({v_id})...")
                        await cls.upload_synced_video(db, synced_video.id)
                        videos_uploaded += 1
                    except Exception as up_err:
                        logger.error(f"Immediate upload failed for video {v_id}: {up_err}")

            return SyncTriggerResponse(
                success=True,
                message=f"Sync completed. Staged {videos_downloaded} new video(s). {videos_uploaded} published immediately, {max(0, videos_downloaded - videos_uploaded)} queued for scheduled publishing.",
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
        """
        Just-In-Time 1-by-1 Uploader:
        Downloads ONLY this single video, checks file size limit, uploads to YouTube,
        and GUARANTEES immediate deletion from disk upon completion or failure.
        """
        stmt = select(SyncedSourceVideo).options(
            selectinload(SyncedSourceVideo.sync_config).selectinload(SourceChannelSync.target_channel)
        ).where(SyncedSourceVideo.id == synced_video_id)
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

        temp_dir = None
        active_filepath = None

        try:
            # 1. Just-In-Time download for this single video if not already present
            if not v.local_temp_path or not os.path.exists(v.local_temp_path):
                temp_dir = tempfile.mkdtemp(prefix="yt_jit_upload_")
                logger.info(f"Just-In-Time: Downloading single video '{v.title}' ({v.source_video_id}) for upload...")
                dl_result = await asyncio.to_thread(cls._download_video_and_metadata_sync, v.source_url, temp_dir)
                active_filepath = dl_result.get("filepath")
                full_info = dl_result.get("info") or {}

                if not active_filepath or not os.path.exists(active_filepath):
                    raise ValueError(f"Downloader did not produce video file for '{v.title}'.")

                v.local_temp_path = active_filepath
                v.title = full_info.get("title") or v.title
                v.description = full_info.get("description") or v.description
                v.tags = full_info.get("tags") or v.tags
                v.category_id = str(full_info.get("categories", ["20"])[0]) if full_info.get("categories") else "20"
                v.download_status = "DOWNLOADED"
                await db.commit()
            else:
                active_filepath = v.local_temp_path

            # 2. File Size Safety Guard
            file_size_mb = os.path.getsize(active_filepath) / (1024 * 1024)
            logger.info(f"Video '{v.title}' size: {file_size_mb:.2f} MB (Max allowed: {cfg.max_video_size_mb} MB)")
            if cfg.max_video_size_mb and file_size_mb > cfg.max_video_size_mb:
                raise ValueError(f"Video file size ({file_size_mb:.1f} MB) exceeds maximum allowed size ({cfg.max_video_size_mb} MB). Skipped.")

            v.upload_status = "UPLOADING"
            await db.commit()

            # 3. Authenticate with target YouTube channel
            youtube = await YouTubeOAuthService.get_authenticated_service(target_channel.id, db)

            # 4. Format title, description, and tags
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

            # 5. Build metadata payload
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
                active_filepath,
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
            return v

        except Exception as up_err:
            logger.error(f"Failed to upload synced video {v.id}: {up_err}", exc_info=True)
            v.upload_status = "FAILED"
            v.error_message = str(up_err)
            await db.commit()
            raise up_err

        finally:
            # Clean up local temporary file immediately to ensure 0 disk waste
            if active_filepath and os.path.exists(active_filepath):
                try:
                    os.remove(active_filepath)
                    logger.info(f"Cleaned up temporary video file: {active_filepath}")
                except Exception:
                    pass
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass
            v.local_temp_path = None
            await db.commit()

    @classmethod
    async def check_and_run_due_drip_uploads(cls):
        """
        Evaluates active source syncs in 'SCHEDULED' publish_mode.
        Runs every minute via APScheduler.
        If current local time matches one of the publish_time_slots, publishes the next queued video.
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(SourceChannelSync).where(
                    SourceChannelSync.enabled == True,
                    SourceChannelSync.publish_mode == "SCHEDULED"
                )
                res = await session.execute(stmt)
                configs = res.scalars().all()

                now_utc = datetime.now(timezone.utc)

                for cfg in configs:
                    tz_name = cfg.timezone or "UTC"
                    try:
                        tz = ZoneInfo(tz_name)
                    except Exception:
                        tz = timezone.utc

                    local_now = now_utc.astimezone(tz)
                    cur_time_str = f"{local_now.hour:02d}:{local_now.minute:02d}"
                    slots = cfg.publish_time_slots or ["10:00", "15:00", "20:00"]

                    # Prevent double execution within 3 minutes of last publish
                    if cfg.last_scheduled_slot_published:
                        last_diff = (now_utc - cfg.last_scheduled_slot_published).total_seconds()
                        if last_diff < 180:
                            continue

                    if cur_time_str not in slots:
                        continue

                    # Find next pending video in queue
                    v_stmt = select(SyncedSourceVideo).where(
                        SyncedSourceVideo.sync_id == cfg.id,
                        SyncedSourceVideo.upload_status == "PENDING"
                    ).order_by(SyncedSourceVideo.created_at.asc())
                    v_res = await session.execute(v_stmt)
                    next_video = v_res.scalars().first()

                    if next_video:
                        logger.info(
                            f"[Daily Drip Scheduler] Slot '{cur_time_str}' reached for sync '{cfg.id}'. "
                            f"Publishing next queued video '{next_video.title}' (ID: {next_video.id})..."
                        )
                        cfg.last_scheduled_slot_published = now_utc
                        await session.commit()

                        try:
                            await cls.upload_synced_video(session, next_video.id)
                            logger.info(f"[Daily Drip Scheduler] Published video '{next_video.title}'.")
                        except Exception as upload_err:
                            logger.error(f"[Daily Drip Scheduler] Error uploading video: {upload_err}")
                    else:
                        logger.info(
                            f"[Daily Drip Scheduler] Slot '{cur_time_str}' reached for sync '{cfg.id}', but queue is empty. "
                            f"Attempting auto-sync to discover new videos..."
                        )
                        cfg.last_scheduled_slot_published = now_utc
                        await session.commit()
                        try:
                            sync_resp = await cls.sync_channel(session, cfg.id, max_videos_to_download=3)
                            if sync_resp.videos_downloaded > 0:
                                v_res2 = await session.execute(v_stmt)
                                new_video = v_res2.scalars().first()
                                if new_video:
                                    await cls.upload_synced_video(session, new_video.id)
                        except Exception as sync_err:
                            logger.warning(f"[Daily Drip Scheduler] Auto-sync attempt error: {sync_err}")

            except Exception as e:
                logger.error(f"Error in check_and_run_due_drip_uploads: {e}", exc_info=True)

    @classmethod
    async def auto_sync_all_active_channels(cls):
        """
        Periodic background job to automatically ingest new videos into the staged queue.
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(SourceChannelSync).where(SourceChannelSync.enabled == True)
                res = await session.execute(stmt)
                configs = res.scalars().all()
                for cfg in configs:
                    try:
                        logger.info(f"[Auto-Ingest] Checking for new source videos: {cfg.source_channel_url}")
                        await cls.sync_channel(session, cfg.id, max_videos_to_download=5)
                    except Exception as err:
                        logger.warning(f"[Auto-Ingest] Failed checking {cfg.source_channel_url}: {err}")
            except Exception as e:
                logger.error(f"Error in auto_sync_all_active_channels: {e}", exc_info=True)
