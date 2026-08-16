import random
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.schedule import Schedule
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.state import ShuffleState
from app.core.logging import logger


class ShuffleResolutionResult:
    def __init__(
        self,
        target_date: date,
        video: Optional[Video] = None,
        is_matched: bool = False,
        current_cycle: int = 1,
        remaining_count: int = 0,
        used_count: int = 0,
        is_new_cycle: bool = False,
        error_reason: Optional[str] = None
    ):
        self.target_date = target_date
        self.video = video
        self.is_matched = is_matched
        self.current_cycle = current_cycle
        self.remaining_count = remaining_count
        self.used_count = used_count
        self.is_new_cycle = is_new_cycle
        self.error_reason = error_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.target_date.isoformat(),
            "video_id": self.video.id if self.video else None,
            "video_filename": self.video.filename if self.video else None,
            "is_matched": self.is_matched,
            "current_cycle": self.current_cycle,
            "remaining_count": self.remaining_count,
            "used_count": self.used_count,
            "is_new_cycle": self.is_new_cycle,
            "error_reason": self.error_reason
        }


class ShuffleModeResolver:
    @classmethod
    async def get_or_create_state(
        cls,
        schedule_id: str,
        db: AsyncSession
    ) -> ShuffleState:
        stmt = select(ShuffleState).where(ShuffleState.schedule_id == schedule_id)
        res = await db.execute(stmt)
        state = res.scalars().first()

        if not state:
            state = ShuffleState(
                schedule_id=schedule_id,
                remaining_video_ids=[],
                used_video_ids=[],
                current_cycle=1
            )
            db.add(state)
            await db.commit()
            await db.refresh(state)

        return state

    @classmethod
    async def get_available_videos(
        cls,
        schedule: Schedule,
        db: AsyncSession
    ) -> List[Video]:
        """Fetches all enabled videos in the folder, subfolders, or channel source"""
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

        res = await db.execute(stmt)
        vids = list(res.scalars().all())

        if not vids and schedule.channel_id:
            fallback_stmt = select(Video).where(Video.enabled == True, Video.channel_id == schedule.channel_id)
            fallback_res = await db.execute(fallback_stmt)
            vids = list(fallback_res.scalars().all())

        return vids

    @classmethod
    async def resolve_video_for_date(
        cls,
        schedule: Schedule,
        target_datetime: datetime,
        db: AsyncSession,
        advance_queue: bool = True
    ) -> ShuffleResolutionResult:
        """
        Resolves the next non-repeating random video for Shuffle Mode.
        Guarantees every video plays once before any repeats, advancing cycle on exhaustion.
        """
        target_d = target_datetime.date() if isinstance(target_datetime, datetime) else target_datetime

        available_videos = await cls.get_available_videos(schedule, db)
        if not available_videos:
            reason = f"No enabled videos found in source '{schedule.source_id}' for shuffle schedule '{schedule.name}'."
            logger.warning(reason)
            return ShuffleResolutionResult(
                target_date=target_d,
                video=None,
                is_matched=False,
                current_cycle=1,
                remaining_count=0,
                used_count=0,
                error_reason=reason
            )

        video_map = {v.id: v for v in available_videos}
        valid_video_ids = set(video_map.keys())

        state = await cls.get_or_create_state(schedule.id, db)
        remaining = [vid for vid in (state.remaining_video_ids or []) if vid in valid_video_ids]
        used = [vid for vid in (state.used_video_ids or []) if vid in valid_video_ids]
        current_cycle = state.current_cycle or 1
        is_new_cycle = False

        # If remaining is empty or fresh start -> initialize randomized cycle
        if not remaining:
            all_ids = list(valid_video_ids)
            random.shuffle(all_ids)
            remaining = all_ids
            used = []
            if state.used_video_ids:
                current_cycle += 1
                is_new_cycle = True
            logger.info(
                f"Shuffle schedule '{schedule.name}': initialized new cycle {current_cycle} with {len(remaining)} videos."
            )

        # Select next random video from remaining queue
        selected_video_id = remaining[0]
        selected_video = video_map[selected_video_id]

        if advance_queue:
            remaining.pop(0)
            used.append(selected_video_id)
            state.remaining_video_ids = remaining
            state.used_video_ids = used
            state.current_cycle = current_cycle
            await db.commit()
            logger.info(
                f"Shuffle schedule '{schedule.name}': selected '{selected_video.filename}'. Remaining in cycle {current_cycle}: {len(remaining)}."
            )

        return ShuffleResolutionResult(
            target_date=target_d,
            video=selected_video,
            is_matched=True,
            current_cycle=current_cycle,
            remaining_count=len(remaining),
            used_count=len(used),
            is_new_cycle=is_new_cycle
        )

    @classmethod
    async def reshuffle_pool(
        cls,
        schedule_id: str,
        db: AsyncSession
    ) -> ShuffleState:
        """Manually reshuffle remaining or full video pool for a schedule"""
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        res = await db.execute(stmt)
        schedule = res.scalars().first()
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        available_videos = await cls.get_available_videos(schedule, db)
        all_ids = [v.id for v in available_videos]
        random.shuffle(all_ids)

        state = await cls.get_or_create_state(schedule_id, db)
        state.remaining_video_ids = all_ids
        state.used_video_ids = []
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
        """Simulates Shuffle Mode video assignment for each day of the month without mutating database state"""
        from app.services.scheduler.modes.day_of_month import DayOfMonthResolver, DayResolutionResult
        days_in_month, is_leap = DayOfMonthResolver.get_days_in_month(year, month)
        available_videos = await cls.get_available_videos(schedule, db)
        
        if not available_videos:
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
        video_map = {v.id: v for v in available_videos}
        valid_ids = list(video_map.keys())
        
        sim_remaining = [vid for vid in (state.remaining_video_ids or []) if vid in video_map]
        if not sim_remaining:
            sim_remaining = list(valid_ids)
            random.shuffle(sim_remaining)

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

            if not sim_remaining:
                sim_remaining = list(valid_ids)
                random.shuffle(sim_remaining)

            chosen_id = sim_remaining.pop(0)
            chosen_vid = video_map.get(chosen_id)

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
