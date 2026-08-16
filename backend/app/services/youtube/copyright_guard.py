import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from googleapiclient.errors import HttpError

from app.core.database import AsyncSessionLocal
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.models.video import Video
from app.models.channel import Channel
from app.models.schedule import Schedule
from app.services.youtube.youtube_oauth import YouTubeOAuthService
from app.services.youtube.quota_tracker import YouTubeQuotaTracker
from app.core.logging import logger

REJECTION_REASONS = {
    "copyright",
    "claim",
    "termsOfUse",
    "duplicate",
    "legal",
    "inappropriate",
    "violatesTermsOfService"
}


class CopyrightGuardService:
    @classmethod
    async def inspect_youtube_video(
        cls,
        youtube: Any,
        youtube_video_id: str
    ) -> Dict[str, Any]:
        """
        Queries YouTube Data API v3 for status, processing details, and rejection reasons.
        """
        try:
            request = youtube.videos().list(
                part="snippet,status,processingDetails,contentDetails",
                id=youtube_video_id
            )
            response = request.execute()
            items = response.get("items", [])
            if not items:
                return {
                    "exists": False,
                    "is_flagged": False,
                    "reason": "Video not found on YouTube (may have been manually deleted or removed)"
                }

            item = items[0]
            status = item.get("status", {})
            processing = item.get("processingDetails", {})

            upload_status = status.get("uploadStatus", "").lower()
            rejection_reason = status.get("rejectionReason", "")
            processing_status = processing.get("processingStatus", "").lower()
            processing_failure_reason = processing.get("processingFailureReason", "")

            is_flagged = False
            flag_reason = None

            if rejection_reason and (rejection_reason.lower() in REJECTION_REASONS or "copyright" in rejection_reason.lower()):
                is_flagged = True
                flag_reason = f"Rejection: {rejection_reason}"
            elif upload_status == "rejected":
                is_flagged = True
                flag_reason = f"Upload rejected: {rejection_reason or 'Policy Violation'}"
            elif processing_status == "failed" or processing_status == "terminated":
                is_flagged = True
                flag_reason = f"Processing {processing_status}: {processing_failure_reason or 'Failed'}"

            return {
                "exists": True,
                "is_flagged": is_flagged,
                "reason": flag_reason,
                "upload_status": upload_status,
                "rejection_reason": rejection_reason,
                "processing_status": processing_status,
                "privacy_status": status.get("privacyStatus")
            }
        except HttpError as e:
            logger.error(f"YouTube API HttpError during copyright inspection for '{youtube_video_id}': {e}")
            if e.resp.status == 404:
                return {"exists": False, "is_flagged": False, "reason": "Video 404 Not Found"}
            raise e
        except Exception as e:
            logger.error(f"Error inspecting video '{youtube_video_id}': {e}")
            return {"exists": False, "is_flagged": False, "reason": str(e)}

    @classmethod
    async def delete_from_youtube(
        cls,
        youtube: Any,
        youtube_video_id: str,
        channel_id: str,
        db: AsyncSession
    ) -> bool:
        """Deletes a video from YouTube via Data API (costs 50 quota units)"""
        try:
            del_request = youtube.videos().delete(id=youtube_video_id)
            del_request.execute()
            await YouTubeQuotaTracker.record_quota_usage(channel_id, 50, db)
            logger.info(f"Successfully deleted video '{youtube_video_id}' from YouTube channel '{channel_id}'.")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Video '{youtube_video_id}' was already deleted from YouTube (404).")
                return True
            logger.error(f"Failed to delete video '{youtube_video_id}' from YouTube: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting video '{youtube_video_id}': {e}")
            return False

    @classmethod
    async def handle_flagged_video(
        cls,
        occurrence_id: str,
        flag_reason: str,
        auto_replace: bool = True,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        1. Deletes the flagged video from YouTube.
        2. Disables the offending source video in the database.
        3. Updates Occurrence status to 'COPYRIGHT_DELETED'.
        4. If auto_replace is True and occurrence belongs to a schedule, triggers an immediate replacement upload.
        """
        async def _execute(session: AsyncSession) -> Dict[str, Any]:
            stmt = select(ScheduleOccurrence).where(ScheduleOccurrence.id == occurrence_id)
            res = await session.execute(stmt)
            occ = res.scalars().first()
            if not occ:
                return {"success": False, "error": f"Occurrence '{occurrence_id}' not found"}

            yt_id = occ.youtube_video_id
            deleted_from_yt = False

            if yt_id and yt_id != "DRY_RUN_MOCK_ID":
                try:
                    youtube = await YouTubeOAuthService.get_authenticated_service(occ.channel_id, session)
                    deleted_from_yt = await cls.delete_from_youtube(youtube, yt_id, occ.channel_id, session)
                except Exception as e:
                    logger.error(f"Could not authenticate with YouTube to delete '{yt_id}': {e}")

            # 2. Disable source video in database so it is never scheduled again
            if occ.video_id:
                v_res = await session.execute(select(Video).where(Video.id == occ.video_id))
                bad_video = v_res.scalars().first()
                if bad_video:
                    bad_video.enabled = False
                    logger.info(f"Disabled copyright-flagged source video '{bad_video.filename}' (ID: {bad_video.id}) in database.")

            # 3. Update occurrence record
            occ.status = "COPYRIGHT_DELETED"
            occ.error_message = f"Copyright/Policy Flag: {flag_reason}. Deleted from YouTube."
            
            # Update associated UploadJob if present
            job_res = await session.execute(select(UploadJob).where(UploadJob.occurrence_id == occ.id))
            job = job_res.scalars().first()
            if job:
                job.status = "COPYRIGHT_DELETED"
                job.error_message = occ.error_message

            await session.commit()
            logger.warning(f"Occurrence '{occurrence_id}' marked as COPYRIGHT_DELETED. Reason: {flag_reason}")

            replacement_occurrence_id = None
            # 4. Auto-Replacement: Trigger replacement video for the schedule
            if auto_replace and occ.schedule_id:
                try:
                    from app.services.scheduler.scheduler_engine import execute_schedule_job
                    logger.info(f"Auto-Replacement: Triggering next replacement video for schedule '{occ.schedule_id}'...")
                    replacement_occurrence_id = await execute_schedule_job(
                        schedule_id=occ.schedule_id,
                        db=session,
                        manual_target_date=datetime.now(),
                        trigger_upload=True
                    )
                    logger.info(f"Auto-Replacement created new occurrence: '{replacement_occurrence_id}'")
                except Exception as rep_err:
                    logger.error(f"Failed to trigger auto-replacement for schedule '{occ.schedule_id}': {rep_err}")

            return {
                "success": True,
                "occurrence_id": occ.id,
                "youtube_video_id": yt_id,
                "deleted_from_youtube": deleted_from_yt,
                "status": "COPYRIGHT_DELETED",
                "reason": flag_reason,
                "replacement_occurrence_id": replacement_occurrence_id
            }

        if db:
            return await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _execute(session)

    @classmethod
    async def audit_occurrence(
        cls,
        occurrence_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Audits a single occurrence by checking its live YouTube status.
        If flagged, automatically deletes and replaces the video.
        """
        async def _execute(session: AsyncSession) -> Dict[str, Any]:
            stmt = select(ScheduleOccurrence).where(ScheduleOccurrence.id == occurrence_id)
            res = await session.execute(stmt)
            occ = res.scalars().first()
            if not occ or not occ.youtube_video_id or occ.youtube_video_id == "DRY_RUN_MOCK_ID":
                return {"status": "SKIPPED", "message": "No YouTube video to audit"}

            try:
                youtube = await YouTubeOAuthService.get_authenticated_service(occ.channel_id, session)
            except Exception as e:
                return {"status": "ERROR", "message": f"YouTube auth failed: {e}"}

            inspection = await cls.inspect_youtube_video(youtube, occ.youtube_video_id)
            
            if inspection.get("is_flagged"):
                logger.warning(f"Copyright/Notice detected on occurrence '{occ.id}' ({occ.youtube_video_id}): {inspection.get('reason')}")
                action_result = await cls.handle_flagged_video(
                    occurrence_id=occ.id,
                    flag_reason=inspection.get("reason") or "Copyright/Policy rejection",
                    auto_replace=True,
                    db=session
                )
                return {
                    "status": "FLAGGED_AND_REPLACED",
                    "inspection": inspection,
                    "action_result": action_result
                }

            return {
                "status": "CLEAN",
                "occurrence_id": occ.id,
                "youtube_video_id": occ.youtube_video_id,
                "inspection": inspection
            }

        if db:
            return await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _execute(session)

    @classmethod
    async def audit_recent_uploads(
        cls,
        channel_id: Optional[str] = None,
        limit: int = 20,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Audits recently completed uploads to check for copyright notices or rejections.
        """
        async def _execute(session: AsyncSession) -> Dict[str, Any]:
            stmt = select(ScheduleOccurrence).where(
                and_(
                    ScheduleOccurrence.status.in_(["COMPLETED", "UPLOADING"]),
                    ScheduleOccurrence.youtube_video_id.isnot(None),
                    ScheduleOccurrence.youtube_video_id != "DRY_RUN_MOCK_ID"
                )
            )
            if channel_id:
                stmt = stmt.where(ScheduleOccurrence.channel_id == channel_id)

            stmt = stmt.order_by(ScheduleOccurrence.created_at.desc()).limit(limit)
            res = await session.execute(stmt)
            occurrences = res.scalars().all()

            results = []
            flagged_count = 0

            for occ in occurrences:
                audit_res = await cls.audit_occurrence(occ.id, db=session)
                results.append(audit_res)
                if audit_res.get("status") == "FLAGGED_AND_REPLACED":
                    flagged_count += 1

            return {
                "total_audited": len(occurrences),
                "flagged_and_replaced": flagged_count,
                "clean_count": len(occurrences) - flagged_count,
                "results": results
            }

        if db:
            return await _execute(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _execute(session)
