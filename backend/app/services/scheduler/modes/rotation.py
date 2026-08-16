from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.schedule import Schedule
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.state import RotationState
from app.core.logging import logger


class RotationResolutionResult:
    def __init__(
        self,
        target_date: date,
        video: Optional[Video] = None,
        is_matched: bool = False,
        current_index: int = 0,
        next_index: int = 0,
        total_videos: int = 0,
        is_loop_restart: bool = False,
        error_reason: Optional[str] = None
    ):
        self.target_date = target_date
        self.video = video
        self.is_matched = is_matched
        self.current_index = current_index
        self.next_index = next_index
        self.total_videos = total_videos
        self.is_loop_restart = is_loop_restart
        self.error_reason = error_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.target_date.isoformat(),
            "video_id": self.video.id if self.video else None,
            "video_filename": self.video.filename if self.video else None,
            "is_matched": self.is_matched,
            "current_index": self.current_index,
            "next_index": self.next_index,
            "total_videos": self.total_videos,
            "is_loop_restart": self.is_loop_restart,
            "error_reason": self.error_reason
        }


class RotationModeResolver:
    @classmethod
    async def get_or_create_state(
        cls,
        schedule_id: str,
        db: AsyncSession
    ) -> RotationState:
        stmt = select(RotationState).where(RotationState.schedule_id == schedule_id)
        res = await db.execute(stmt)
        state = res.scalars().first()

        if not state:
            state = RotationState(
                schedule_id=schedule_id,
                current_index=0,
                last_video_id=None
            )
            db.add(state)
            await db.commit()
            await db.refresh(state)

        return state

    @classmethod
    async def get_ordered_videos(
        cls,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[Video]:
        """
        Fetches enabled videos in deterministic order (by filename ascending).
        """
        stmt = select(Video).where(Video.enabled == True)
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
                stmt = stmt.where(or_(Video.folder_id.in_(all_fols), Video.path.like(f"{target_f.name}%"), Video.path.like(f"{target_f.path}%")))
            else:
                stmt = stmt.where(Video.folder_id == schedule.source_id)
        elif schedule.channel_id:
            stmt = stmt.where(Video.channel_id == schedule.channel_id)

        stmt = stmt.order_by(Video.filename.asc())
        res = await db.execute(stmt)
        vids = list(res.scalars().all())

        if not vids and schedule.channel_id:
            fallback_stmt = select(Video).where(Video.enabled == True, Video.channel_id == schedule.channel_id).order_by(Video.filename.asc())
            fallback_res = await db.execute(fallback_stmt)
            vids = list(fallback_res.scalars().all())

        return vids

    @classmethod
    async def resolve_video_for_date(
        cls,
        schedule: Schedule,
        target_datetime: datetime,
        db: AsyncSession,
        advance_index: bool = True
    ) -> RotationResolutionResult:
        """
        Resolves the next sequential video in the rotation queue.
        Persists and advances the rotation state tracker in the database.
        """
        target_d = target_datetime.date() if isinstance(target_datetime, datetime) else target_datetime

        videos = await cls.get_ordered_videos(schedule, db)
        total_videos = len(videos)

        if total_videos == 0:
            reason = f"No enabled videos found in source '{schedule.source_id}' for rotation schedule '{schedule.name}'."
            logger.warning(reason)
            return RotationResolutionResult(
                target_date=target_d,
                video=None,
                is_matched=False,
                current_index=0,
                next_index=0,
                total_videos=0,
                error_reason=reason
            )

        # Retrieve current rotation state
        state = await cls.get_or_create_state(schedule.id, db)
        curr_idx = state.current_index % total_videos
        selected_video = videos[curr_idx]

        next_idx = (curr_idx + 1) % total_videos
        is_loop_restart = (curr_idx == total_videos - 1)

        if advance_index:
            state.last_video_id = selected_video.id
            state.current_index = next_idx
            await db.commit()
            logger.info(
                f"Rotation schedule '{schedule.name}': selected video {curr_idx + 1}/{total_videos} ('{selected_video.filename}'). Next index: {next_idx}."
            )

        return RotationResolutionResult(
            target_date=target_d,
            video=selected_video,
            is_matched=True,
            current_index=curr_idx,
            next_index=next_idx,
            total_videos=total_videos,
            is_loop_restart=is_loop_restart
        )

    @classmethod
    async def reset_rotation_index(
        cls,
        schedule_id: str,
        index: int,
        db: AsyncSession
    ) -> RotationState:
        """Manually set or reset the rotation pointer"""
        state = await cls.get_or_create_state(schedule_id, db)
        state.current_index = max(0, index)
        await db.commit()
        await db.refresh(state)
        return state

    @classmethod
    async def simulate_month_schedule(
        cls,
        schedule: Schedule,
        year: int,
        month: int,
        db: AsyncSession
    ):
        """Simulates Rotation Mode sequential video assignment for each day of the month without mutating database state"""
        from app.services.scheduler.modes.day_of_month import DayOfMonthResolver, DayResolutionResult
        days_in_month, is_leap = DayOfMonthResolver.get_days_in_month(year, month)
        ordered_videos = await cls.get_ordered_videos(schedule, db)

        if not ordered_videos:
            return [
                DayResolutionResult(
                    target_date=date(year, month, d),
                    day_number=d,
                    video=None,
                    is_matched=False,
                    fallback_reason=f"No enabled videos found in source for schedule '{schedule.name}'.",
                    is_leap_year=is_leap,
                    days_in_month=days_in_month
                )
                for d in range(1, days_in_month + 1)
            ]

        state = await cls.get_or_create_state(schedule.id, db)
        curr_idx = state.current_index or 0
        total_videos = len(ordered_videos)

        results = []
        weekday_map = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"}

        for d in range(1, days_in_month + 1):
            target_d = date(year, month, d)
            if schedule.schedule_type == "WEEKLY" and schedule.days_of_week:
                cur_w = weekday_map.get(target_d.weekday())
                if cur_w not in [str(x).upper() for x in schedule.days_of_week]:
                    results.append(
                        DayResolutionResult(
                            target_date=target_d,
                            day_number=d,
                            video=None,
                            is_matched=False,
                            fallback_reason=f"Not scheduled on {cur_w}",
                            is_leap_year=is_leap,
                            days_in_month=days_in_month
                        )
                    )
                    continue

            chosen_vid = ordered_videos[curr_idx % total_videos]
            curr_idx += 1

            results.append(
                DayResolutionResult(
                    target_date=target_d,
                    day_number=d,
                    video=chosen_vid,
                    is_matched=True,
                    is_fallback=False,
                    is_leap_year=is_leap,
                    days_in_month=days_in_month
                )
            )

        return results
