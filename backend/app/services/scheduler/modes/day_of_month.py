import calendar
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.schedule import Schedule
from app.models.folder import ContentFolder
from app.models.video import Video
from app.core.logging import logger


class DayResolutionResult:
    def __init__(
        self,
        target_date: date,
        day_number: int,
        video: Optional[Video] = None,
        is_matched: bool = False,
        is_fallback: bool = False,
        fallback_reason: Optional[str] = None,
        is_leap_year: bool = False,
        days_in_month: int = 31
    ):
        self.target_date = target_date
        self.day_number = day_number
        self.video = video
        self.is_matched = is_matched
        self.is_fallback = is_fallback
        self.fallback_reason = fallback_reason
        self.is_leap_year = is_leap_year
        self.days_in_month = days_in_month

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.target_date.isoformat(),
            "day_number": self.day_number,
            "video_id": self.video.id if self.video else None,
            "video_filename": self.video.filename if self.video else None,
            "is_matched": self.is_matched,
            "is_fallback": self.is_fallback,
            "fallback_reason": self.fallback_reason,
            "is_leap_year": self.is_leap_year,
            "days_in_month": self.days_in_month
        }


class DayOfMonthResolver:
    @classmethod
    def get_days_in_month(cls, year: int, month: int) -> Tuple[int, bool]:
        """Returns (number_of_days, is_leap_year)"""
        is_leap = calendar.isleap(year)
        _, days_in_month = calendar.monthrange(year, month)
        return days_in_month, is_leap

    @classmethod
    async def resolve_video_for_date(
        cls,
        schedule: Schedule,
        target_datetime: datetime,
        db: AsyncSession
    ) -> DayResolutionResult:
        """
        Resolves the exact matching Video asset for a given target date in Day-of-Month mode.
        Handles calendar boundaries (28/29/30/31 days) and missing video fallbacks.
        """
        year = target_datetime.year
        month = target_datetime.month
        day = target_datetime.day
        target_d = target_datetime.date() if isinstance(target_datetime, datetime) else target_datetime
        days_in_month, is_leap = cls.get_days_in_month(year, month)

        # Ensure folder or channel source is present
        folder_ids = None
        if schedule.source_type == "FOLDER":
            target_f = (await db.execute(select(ContentFolder).where(ContentFolder.id == schedule.source_id))).scalars().first()
            if target_f:
                all_fols = (await db.execute(select(ContentFolder.id).where(
                    or_(
                        ContentFolder.id == target_f.id,
                        ContentFolder.path.like(f"{target_f.path}%"),
                        ContentFolder.name == target_f.name
                    )
                ))).scalars().all()
                folder_ids = list(all_fols)
            else:
                folder_ids = [schedule.source_id]

        # 1. Search for video explicitly matching this day_of_month_index
        stmt = select(Video).where(
            and_(
                Video.enabled == True,
                Video.day_of_month_index == day
            )
        )
        if folder_ids:
            stmt = stmt.where(Video.folder_id.in_(folder_ids))
        elif schedule.channel_id:
            stmt = stmt.where(Video.channel_id == schedule.channel_id)

        res = await db.execute(stmt)
        video = res.scalars().first()

        if video:
            return DayResolutionResult(
                target_date=target_d,
                day_number=day,
                video=video,
                is_matched=True,
                is_leap_year=is_leap,
                days_in_month=days_in_month
            )

        # 2. If not found by index, attempt fuzzy match on filename (e.g. "15.mp4", "01.mp4", "15_*.mp4")
        day_str = f"{day:02d}"
        day_simple = f"{day}"
        fallback_stmt = select(Video).where(
            and_(
                Video.enabled == True,
                (
                    Video.filename.ilike(f"{day_simple}.%") |
                    Video.filename.ilike(f"{day_str}.%") |
                    Video.filename.ilike(f"{day_simple}_%") |
                    Video.filename.ilike(f"{day_str}_%")
                )
            )
        )
        if folder_ids:
            fallback_stmt = fallback_stmt.where(Video.folder_id.in_(folder_ids))
        elif schedule.channel_id:
            fallback_stmt = fallback_stmt.where(Video.channel_id == schedule.channel_id)

        fallback_res = await db.execute(fallback_stmt)
        video = fallback_res.scalars().first()

        if video:
            return DayResolutionResult(
                target_date=target_d,
                day_number=day,
                video=video,
                is_matched=True,
                is_leap_year=is_leap,
                days_in_month=days_in_month
            )

        # 3. Fallback to default video in the folder if configured
        default_stmt = select(Video).where(
            and_(
                Video.enabled == True,
                Video.filename.ilike("default.%")
            )
        )
        if folder_ids:
            default_stmt = default_stmt.where(Video.folder_id.in_(folder_ids))
        elif schedule.channel_id:
            default_stmt = default_stmt.where(Video.channel_id == schedule.channel_id)

        default_res = await db.execute(default_stmt)
        default_video = default_res.scalars().first()

        if default_video:
            return DayResolutionResult(
                target_date=target_d,
                day_number=day,
                video=default_video,
                is_matched=False,
                is_fallback=True,
                fallback_reason=f"Video for day {day} not found. Used folder default.mp4 fallback.",
                is_leap_year=is_leap,
                days_in_month=days_in_month
            )

        # 4. No matching video found
        reason = f"No video found matching day {day} in source {folder_ids or schedule.channel_id}."
        logger.warning(reason)
        return DayResolutionResult(
            target_date=target_d,
            day_number=day,
            video=None,
            is_matched=False,
            is_fallback=False,
            fallback_reason=reason,
            is_leap_year=is_leap,
            days_in_month=days_in_month
        )

    @classmethod
    async def simulate_month_schedule(
        cls,
        schedule: Schedule,
        year: int,
        month: int,
        db: AsyncSession
    ) -> List[DayResolutionResult]:
        """
        Simulate video assignment for every day of a specified month (1 to 28/29/30/31).
        """
        days_in_month, _ = cls.get_days_in_month(year, month)
        results: List[DayResolutionResult] = []

        for d in range(1, days_in_month + 1):
            target_dt = datetime(year, month, d)
            res = await cls.resolve_video_for_date(schedule, target_dt, db)
            results.append(res)

        return results
