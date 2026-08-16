import os
import tempfile
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from googleapiclient.http import MediaFileUpload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.models.channel import Channel
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.services.storage.factory import get_storage_provider
from app.services.metadata.metadata_engine import MetadataEngine
from app.services.youtube.youtube_oauth import YouTubeOAuthService
from app.services.youtube.quota_tracker import (
    YouTubeQuotaTracker,
    QUOTA_VIDEO_UPLOAD,
    QUOTA_THUMBNAIL_SET
)
from app.services.worker.recovery import ErrorClassifier, RetryEngine
from app.core.logging import logger


class YouTubeUploaderService:
    @classmethod
    async def run_upload_job(
        cls,
        occurrence_id: str,
        title_override: Optional[str] = None,
        description_override: Optional[str] = None,
        tags_override: Optional[list] = None,
        category_id_override: Optional[str] = None,
        privacy_status_override: Optional[str] = None,
        publish_at: Optional[datetime] = None,
        dry_run: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Executes the full automated download, metadata resolution,
        chunked YouTube resumable upload, custom thumbnail attachment,
        publishAt ISO 8601 scheduling, error classification, retry backoff, and quota tracking pipeline.
        """
        async def _execute(session: AsyncSession) -> Dict[str, Any]:
            # 1. Fetch Occurrence & UploadJob
            occ_stmt = select(ScheduleOccurrence).where(ScheduleOccurrence.id == occurrence_id)
            occ_res = await session.execute(occ_stmt)
            occurrence = occ_res.scalars().first()
            if not occurrence:
                raise ValueError(f"Occurrence with ID '{occurrence_id}' not found.")

            # Idempotency check: if already completed, do not duplicate upload
            if occurrence.status == "COMPLETED" and occurrence.youtube_video_id and not dry_run:
                logger.warning(f"Occurrence '{occurrence_id}' is already COMPLETED (YouTube ID: {occurrence.youtube_video_id}). Skipping.")
                return {
                    "status": "ALREADY_COMPLETED",
                    "occurrence_id": occurrence.id,
                    "youtube_video_id": occurrence.youtube_video_id,
                    "youtube_url": f"https://youtu.be/{occurrence.youtube_video_id}"
                }

            job_stmt = select(UploadJob).where(UploadJob.occurrence_id == occurrence_id)
            job_res = await session.execute(job_stmt)
            upload_job = job_res.scalars().first()
            if not upload_job:
                upload_job = UploadJob(occurrence_id=occurrence_id, status="QUEUED")
                session.add(upload_job)
                await session.commit()
                await session.refresh(upload_job)

            # 2. Fetch Channel & Video
            ch_stmt = select(Channel).where(Channel.id == occurrence.channel_id)
            ch_res = await session.execute(ch_stmt)
            channel = ch_res.scalars().first()
            if not channel:
                raise ValueError(f"Channel with ID '{occurrence.channel_id}' not found.")

            if not occurrence.video_id:
                raise ValueError(f"Occurrence '{occurrence_id}' does not have a resolved video.")

            v_stmt = select(Video).where(Video.id == occurrence.video_id)
            v_res = await session.execute(v_stmt)
            video = v_res.scalars().first()
            if not video:
                raise ValueError(f"Video with ID '{occurrence.video_id}' not found.")

            # 3. Resolve Effective Metadata
            folder = None
            if video.folder_id:
                f_stmt = select(ContentFolder).where(ContentFolder.id == video.folder_id)
                f_res = await session.execute(f_stmt)
                folder = f_res.scalars().first()

            schedule = None
            if occurrence.schedule_id:
                sch_stmt = select(Schedule).where(Schedule.id == occurrence.schedule_id)
                sch_res = await session.execute(sch_stmt)
                schedule = sch_res.scalars().first()

            effective_meta = MetadataEngine.resolve_effective_metadata(
                video=video,
                channel=channel,
                folder=folder,
                schedule=schedule,
                target_datetime=occurrence.scheduled_publish_time or datetime.now()
            )

            # Apply runtime overrides if passed
            final_title = title_override or effective_meta.title
            final_desc = description_override or effective_meta.description
            final_tags = tags_override if tags_override is not None else effective_meta.tags
            final_cat = category_id_override or effective_meta.category_id or "22"
            final_privacy = privacy_status_override or effective_meta.privacy_status or "private"

            # 4. Dry Run Mode Check
            is_dry_run = dry_run or occurrence.dry_run
            if is_dry_run:
                logger.info(f"[DRY RUN] Simulating upload for '{final_title}' on channel '{channel.name}' (publishAt: {publish_at}). No YouTube API calls made.")
                upload_job.status = "SUCCESS"
                upload_job.bytes_uploaded = video.size_bytes or 1000
                upload_job.total_bytes = video.size_bytes or 1000
                upload_job.completed_at = datetime.now(timezone.utc)
                
                occurrence.status = "COMPLETED"
                occurrence.dry_run = True
                occurrence.youtube_video_id = "DRY_RUN_MOCK_ID"
                occurrence.error_message = None
                await session.commit()

                return {
                    "status": "SUCCESS",
                    "dry_run": True,
                    "occurrence_id": occurrence.id,
                    "youtube_video_id": "DRY_RUN_MOCK_ID",
                    "youtube_url": "https://youtu.be/DRY_RUN_MOCK_ID",
                    "title": final_title,
                    "publish_at": publish_at.isoformat() if publish_at else None,
                    "bytes_uploaded": video.size_bytes or 1000
                }

            # 5. Quota Pre-Flight Check
            can_upload, used_quota, quota_msg = await YouTubeQuotaTracker.can_upload_video(channel.id, session)
            if not can_upload:
                upload_job.status = "FAILED"
                upload_job.error_type = "QUOTA_EXCEEDED"
                upload_job.error_message = quota_msg
                occurrence.status = "FAILED"
                occurrence.error_message = quota_msg
                await session.commit()
                raise ValueError(quota_msg)

            temp_video_path = None
            temp_thumb_path = None
            media_body = None

            try:
                upload_job.status = "DOWNLOADING"
                upload_job.started_at = datetime.now(timezone.utc)
                occurrence.status = "DOWNLOADING"
                await session.commit()

                # 6. Download Video from StorageProvider to temporary cache
                storage = await get_storage_provider(video.storage_provider, session)
                suffix = os.path.splitext(video.filename)[1] or ".mp4"
                
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                    temp_video_path = tmp_file.name

                upload_job.temp_file_path = temp_video_path
                await session.commit()

                logger.info(f"Downloading video '{video.filename}' from storage '{video.storage_provider}' to '{temp_video_path}'...")
                await storage.download_file(video.storage_file_id, temp_video_path)

                file_size = os.path.getsize(temp_video_path)
                upload_job.bytes_downloaded = file_size
                upload_job.total_bytes = file_size
                upload_job.status = "IN_PROGRESS"
                occurrence.status = "UPLOADING"
                await session.commit()

                # 7. Authenticate with YouTube API
                youtube = await YouTubeOAuthService.get_authenticated_service(channel.id, session)

                # 8. Configure status (privacy & publishAt ISO 8601)
                status_dict: Dict[str, Any] = {
                    "selfDeclaredMadeForKids": False
                }

                if publish_at:
                    utc_publish_at = publish_at if publish_at.tzinfo else publish_at.replace(tzinfo=timezone.utc)
                    status_dict["privacyStatus"] = "private"
                    status_dict["publishAt"] = utc_publish_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    logger.info(f"Configured YouTube scheduled publishAt: {status_dict['publishAt']}")
                else:
                    status_dict["privacyStatus"] = final_privacy.lower()

                # 9. Resumable Upload Body (Ensure tags do not exceed YouTube's 500 total character limit)
                safe_tags = []
                cur_len = 0
                if final_tags:
                    for t in final_tags:
                        clean_tag = str(t).strip()
                        if not clean_tag:
                            continue
                        if cur_len + len(clean_tag) + 1 <= 490:
                            safe_tags.append(clean_tag)
                            cur_len += len(clean_tag) + 1
                        else:
                            break

                body = {
                    "snippet": {
                        "title": final_title[:100],
                        "description": final_desc[:5000],
                        "tags": safe_tags,
                        "categoryId": str(final_cat)
                    },
                    "status": status_dict
                }

                media_body = MediaFileUpload(
                    temp_video_path,
                    mimetype="video/*",
                    chunksize=1024 * 1024 * 5, # 5MB chunks
                    resumable=True
                )

                insert_request = youtube.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media_body
                )

                logger.info(f"Starting chunked YouTube resumable upload for '{final_title}' (Size: {file_size} bytes)...")

                yt_response = None
                while yt_response is None:
                    status_obj, yt_response = insert_request.next_chunk()
                    if status_obj:
                        progress_bytes = status_obj.resumable_progress
                        upload_job.bytes_uploaded = progress_bytes
                        await session.commit()
                        logger.info(f"Upload progress: {progress_bytes}/{file_size} bytes ({(progress_bytes/file_size)*100:.1f}%)")

                yt_video_id = yt_response.get("id")
                if not yt_video_id:
                    raise ValueError(f"YouTube upload finished but returned no video ID: {yt_response}")

                logger.info(f"YouTube upload succeeded! Video ID: {yt_video_id}")
                await YouTubeQuotaTracker.record_quota_usage(channel.id, QUOTA_VIDEO_UPLOAD, session)

                # 10. Upload Custom Thumbnail if available
                thumbnail_storage_id = (
                    video.custom_thumbnail_file_id or
                    (folder.default_thumbnail_storage_id if folder else None) or
                    channel.default_thumbnail_storage_id
                )

                if thumbnail_storage_id:
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_thumb:
                            temp_thumb_path = tmp_thumb.name
                        
                        await storage.download_file(thumbnail_storage_id, temp_thumb_path)
                        thumb_body = MediaFileUpload(temp_thumb_path, mimetype="image/jpeg")
                        youtube.thumbnails().set(
                            videoId=yt_video_id,
                            media_body=thumb_body
                        ).execute()
                        
                        await YouTubeQuotaTracker.record_quota_usage(channel.id, QUOTA_THUMBNAIL_SET, session)
                        logger.info(f"Custom thumbnail attached to video '{yt_video_id}'.")
                    except Exception as thumb_err:
                        logger.warning(f"Could not set custom thumbnail for video '{yt_video_id}': {thumb_err}")

                # 11. Mark Job & Occurrence as COMPLETED
                upload_job.status = "SUCCESS"
                upload_job.bytes_uploaded = file_size
                upload_job.completed_at = datetime.now(timezone.utc)
                
                occurrence.status = "COMPLETED"
                occurrence.youtube_video_id = yt_video_id
                occurrence.error_message = None
                await session.commit()

                # 12. Register post-upload automated copyright audit (10m delay for Content ID scan)
                try:
                    from app.services.scheduler.scheduler_engine import get_scheduler
                    from app.services.youtube.copyright_guard import CopyrightGuardService
                    from apscheduler.triggers.date import DateTrigger
                    sched = get_scheduler()
                    audit_time = datetime.now(timezone.utc) + timedelta(minutes=10)
                    sched.add_job(
                        func=CopyrightGuardService.audit_occurrence,
                        trigger=DateTrigger(run_date=audit_time),
                        args=[occurrence.id],
                        id=f"audit_copyright_{occurrence.id}",
                        replace_existing=True,
                        misfire_grace_time=3600
                    )
                    logger.info(f"Scheduled automated copyright audit for occurrence '{occurrence.id}' at {audit_time.isoformat()}.")
                except Exception as sched_err:
                    logger.warning(f"Could not register automated copyright audit job: {sched_err}")

                return {
                    "status": "SUCCESS",
                    "occurrence_id": occurrence.id,
                    "youtube_video_id": yt_video_id,
                    "youtube_url": f"https://youtu.be/{yt_video_id}",
                    "title": final_title,
                    "publish_at": status_dict.get("publishAt"),
                    "bytes_uploaded": file_size
                }

            except Exception as e:
                err_str = str(e)
                logger.error(f"Error during YouTube upload for occurrence {occurrence_id}: {err_str}", exc_info=True)
                
                # Classify error and calculate retry backoff
                err_type, is_retryable = ErrorClassifier.classify_error(err_str)
                
                if is_retryable and upload_job.retry_count < upload_job.max_retries:
                    upload_job.retry_count += 1
                    backoff_sec = RetryEngine.calculate_backoff(upload_job.retry_count)
                    upload_job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_sec)
                    upload_job.status = "RETRYING"
                    upload_job.error_type = err_type
                    upload_job.error_message = f"{err_str} (Will retry in {backoff_sec}s, attempt {upload_job.retry_count}/{upload_job.max_retries})"
                    
                    occurrence.status = "RETRYING"
                    occurrence.error_message = upload_job.error_message
                else:
                    upload_job.status = "FAILED"
                    upload_job.error_type = err_type
                    upload_job.error_message = err_str
                    upload_job.completed_at = datetime.now(timezone.utc)
                    
                    occurrence.status = "FAILED"
                    occurrence.error_message = err_str

                await session.commit()
                raise e

            finally:
                # Release media body handle
                try:
                    if 'media_body' in locals() and media_body and hasattr(media_body, '_fd') and media_body._fd:
                        try:
                            media_body._fd.close()
                        except Exception:
                            pass
                except Exception:
                    pass

                import gc
                gc.collect()
                
                # 12. Clean up temporary files on VPS
                if temp_video_path and os.path.exists(temp_video_path):
                    try:
                        os.remove(temp_video_path)
                        logger.info(f"Cleaned up temporary video cache: '{temp_video_path}'")
                    except Exception as err:
                        logger.warning(f"Could not delete temp video file: {err}")

                if temp_thumb_path and os.path.exists(temp_thumb_path):
                    try:
                        os.remove(temp_thumb_path)
                        logger.info(f"Cleaned up temporary thumbnail cache: '{temp_thumb_path}'")
                    except Exception as err:
                        logger.warning(f"Could not delete temp thumbnail file: {err}")

        if db:
            return await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _execute(session)
