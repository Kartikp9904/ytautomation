from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schedule import Schedule
from app.models.video import Video
from app.core.logging import logger


class RepeatResolutionResult:
    def __init__(
        self,
        target_date: date,
        video: Optional[Video] = None,
        is_matched: bool = False,
        error_reason: Optional[str] = None
    ):
        self.target_date = target_date
        self.video = video
        self.is_matched = is_matched
        self.error_reason = error_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.target_date.isoformat(),
            "video_id": self.video.id if self.video else None,
            "video_filename": self.video.filename if self.video else None,
            "is_matched": self.is_matched,
            "error_reason": self.error_reason
        }


class RepeatModeResolver:
    @classmethod
    async def resolve_video_for_date(
        cls,
        schedule: Schedule,
        target_datetime: datetime,
        db: AsyncSession
    ) -> RepeatResolutionResult:
        """
        Resolves the designated video for Repeat Mode.
        In Repeat Mode, the exact same video is published on every scheduled occurrence,
        while dynamic metadata variables ({date}, {day}, {month}, {year}) evaluate fresh for each run.
        """
        target_d = target_datetime.date() if isinstance(target_datetime, datetime) else target_datetime

        # 1. If source_type is VIDEO / SPECIFIC_VIDEO
        if schedule.source_type.upper() in ["VIDEO", "SPECIFIC_VIDEO"]:
            stmt = select(Video).where(Video.id == schedule.source_id)
            res = await db.execute(stmt)
            video = res.scalars().first()

            if not video:
                reason = f"Target repeat video with ID '{schedule.source_id}' not found in database."
                logger.error(reason)
                return RepeatResolutionResult(target_date=target_d, video=None, is_matched=False, error_reason=reason)

            if not video.enabled:
                reason = f"Target repeat video '{video.filename}' is disabled."
                logger.warning(reason)
                return RepeatResolutionResult(target_date=target_d, video=video, is_matched=False, error_reason=reason)

            return RepeatResolutionResult(target_date=target_d, video=video, is_matched=True)

        # 2. If source_type is FOLDER, select the first enabled video in the folder
        stmt = select(Video).where(
            Video.folder_id == schedule.source_id,
            Video.enabled == True
        ).order_by(Video.filename.asc())
        res = await db.execute(stmt)
        video = res.scalars().first()

        if not video:
            reason = f"No enabled videos found in folder '{schedule.source_id}' for repeat schedule."
            logger.error(reason)
            return RepeatResolutionResult(target_date=target_d, video=None, is_matched=False, error_reason=reason)

        return RepeatResolutionResult(target_date=target_d, video=video, is_matched=True)
