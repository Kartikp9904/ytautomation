import os
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.models.video import Video
from app.models.channel import Channel
from app.services.scheduler.modes.day_of_month import DayOfMonthResolver
from app.services.scheduler.modes.rotation import RotationModeResolver
from app.services.scheduler.modes.shuffle import ShuffleModeResolver
from app.services.scheduler.modes.repeat import RepeatModeResolver
from app.services.worker.worker_pool import UploadWorkerPool
from app.core.logging import logger

_scheduler_instance: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AsyncIOScheduler(timezone="UTC")
    return _scheduler_instance


class SchedulerEngine:
    @classmethod
    def get_job_id(cls, schedule_id: str) -> str:
        return f"schedule_job_{schedule_id}"

    @classmethod
    async def start(cls):
        sched = get_scheduler()
        if not sched.running:
            sched.start()
            logger.info("SchedulerEngine: AsyncIOScheduler started.")
            await cls.sync_all_active_schedules()

    @classmethod
    async def shutdown(cls):
        sched = get_scheduler()
        if sched.running:
            sched.shutdown(wait=False)
            logger.info("SchedulerEngine: AsyncIOScheduler shut down.")

    @classmethod
    async def sync_all_active_schedules(cls):
        """
        Loads all enabled schedules from the database and registers them with the APScheduler.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Schedule).where(Schedule.enabled == True)
            res = await session.execute(stmt)
            schedules = res.scalars().all()
            logger.info(f"Syncing {len(schedules)} active schedules with scheduler...")
            for schedule in schedules:
                try:
                    cls.register_schedule_job(schedule)
                except Exception as e:
                    logger.error(f"Failed to register schedule {schedule.id} ({schedule.name}): {e}")

    @classmethod
    def register_schedule_job(cls, schedule: Schedule):
        sched = get_scheduler()
        job_id = cls.get_job_id(schedule.id)

        # Remove existing job if any
        if sched.get_job(job_id):
            sched.remove_job(job_id)

        if not schedule.enabled:
            return

        # Parse publish_time ("09:00")
        try:
            parts = schedule.publish_time.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
        except Exception:
            hour = 9
            minute = 0

        # Calculate upload trigger time by subtracting lead time buffer
        lead_mins = schedule.upload_lead_minutes if schedule.upload_lead_minutes is not None else 180
        total_mins = hour * 60 + minute - lead_mins
        trigger_hour = (total_mins // 60) % 24
        trigger_minute = total_mins % 60

        tz_str = schedule.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            tz = ZoneInfo("UTC")

        # Configure APScheduler Triggers
        if schedule.schedule_type == "DAILY":
            trigger = CronTrigger(hour=trigger_hour, minute=trigger_minute, second=0, timezone=tz)
        elif schedule.schedule_type == "WEEKLY":
            # Convert ['MON', 'WED'] or [0, 2] to cron string
            days = schedule.days_of_week or ["MON"]
            day_str = ",".join(str(d).lower() for d in days)
            trigger = CronTrigger(day_of_week=day_str, hour=trigger_hour, minute=trigger_minute, second=0, timezone=tz)
        elif schedule.schedule_type == "MONTHLY":
            day_num = schedule.day_of_month or 1
            trigger = CronTrigger(day=day_num, hour=trigger_hour, minute=trigger_minute, second=0, timezone=tz)
        elif schedule.schedule_type == "ONE_TIME":
            target_date = schedule.one_time_date or datetime.now(tz).date()
            run_dt = datetime.combine(target_date, time(trigger_hour, trigger_minute), tzinfo=tz)
            now = datetime.now(tz)
            if run_dt <= now:
                run_dt += timedelta(days=1)
            trigger = DateTrigger(run_date=run_dt, timezone=tz)
        else:
            trigger = CronTrigger(hour=trigger_hour, minute=trigger_minute, second=0, timezone=tz)

        try:
            sched.add_job(
                func=execute_schedule_job,
                trigger=trigger,
                args=[schedule.id],
                id=job_id,
                name=f"Schedule: {schedule.name} ({schedule.id})",
                replace_existing=True,
                misfire_grace_time=3600 # 1 hour grace window
            )
            logger.info(f"Registered job for schedule '{schedule.name}' ({schedule.id}) at trigger {trigger_hour:02d}:{trigger_minute:02d} {tz_str} (Lead: {lead_mins}m, Publish: {hour:02d}:{minute:02d})")
        except Exception as e:
            logger.warning(f"Failed to register job in scheduler: {e}")

    @classmethod
    def unregister_schedule_job(cls, schedule_id: str):
        sched = get_scheduler()
        job_id = cls.get_job_id(schedule_id)
        if sched.get_job(job_id):
            sched.remove_job(job_id)
            logger.info(f"Unregistered job for schedule {schedule_id}")

    @classmethod
    def get_next_run_time(cls, schedule_id: str) -> Optional[datetime]:
        sched = get_scheduler()
        job = sched.get_job(cls.get_job_id(schedule_id))
        return job.next_run_time if job else None


async def execute_schedule_job(
    schedule_id: str,
    db: Optional[AsyncSession] = None,
    manual_target_date: Optional[datetime] = None,
    trigger_upload: bool = True
) -> Optional[str]:
    """
    Main job handler triggered by APScheduler or 'Trigger Now'.
    Generates an idempotent occurrence, resolves matching video, calculates publishAt,
    and runs the YouTube upload pipeline through UploadWorkerPool.
    """
    logger.info(f"Executing schedule job for schedule_id: {schedule_id}")

    async def _execute(session: AsyncSession) -> Optional[str]:
        # 1. Fetch schedule
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        res = await session.execute(stmt)
        schedule = res.scalars().first()
        if not schedule:
            logger.error(f"Schedule {schedule_id} not found in database.")
            return None

        # 2. Fetch channel timezone & calculate publish datetime
        tz_str = schedule.timezone or "UTC"
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            tz = ZoneInfo("UTC")

        now_in_tz = manual_target_date or datetime.now(tz)
        target_date_str = now_in_tz.strftime("%Y-%m-%d")

        # Parse target publish time on this date
        try:
            parts = schedule.publish_time.split(":")
            pub_hour = int(parts[0])
            pub_min = int(parts[1])
        except Exception:
            pub_hour = 9
            pub_min = 0

        scheduled_publish_dt = now_in_tz.replace(
            hour=pub_hour,
            minute=pub_min,
            second=0,
            microsecond=0
        )

        # Idempotency key prevents duplicate execution on the same date
        idempotency_key = f"{schedule.id}:{target_date_str}"
        
        # Check if occurrence already exists
        occ_stmt = select(ScheduleOccurrence).where(
            ScheduleOccurrence.idempotency_key == idempotency_key
        )
        occ_res = await session.execute(occ_stmt)
        existing_occ = occ_res.scalars().first()

        if existing_occ and not manual_target_date:
            logger.warning(
                f"Schedule occurrence for key '{idempotency_key}' already exists (status: {existing_occ.status}). Skipping."
            )
            return existing_occ.id

        # 3. Resolve video based on schedule mode
        resolved_video_id = None
        error_msg = None

        if schedule.mode.upper() == "DAY_OF_MONTH":
            day_result = await DayOfMonthResolver.resolve_video_for_date(
                schedule=schedule,
                target_datetime=now_in_tz,
                db=session
            )
            if day_result.video:
                resolved_video_id = day_result.video.id
            else:
                error_msg = day_result.fallback_reason
        elif schedule.mode.upper() == "ROTATION":
            rot_result = await RotationModeResolver.resolve_video_for_date(
                schedule=schedule,
                target_datetime=now_in_tz,
                db=session,
                advance_index=True
            )
            if rot_result.video:
                resolved_video_id = rot_result.video.id
            else:
                error_msg = rot_result.error_reason
        elif schedule.mode.upper() == "SHUFFLE":
            shuf_result = await ShuffleModeResolver.resolve_video_for_date(
                schedule=schedule,
                target_datetime=now_in_tz,
                db=session,
                advance_queue=True
            )
            if shuf_result.video:
                resolved_video_id = shuf_result.video.id
            else:
                error_msg = shuf_result.error_reason
        elif schedule.mode.upper() in ["REPEAT", "SINGLE_VIDEO"]:
            repeat_res = await RepeatModeResolver.resolve_video_for_date(
                schedule=schedule,
                target_datetime=now_in_tz,
                db=session
            )
            if repeat_res.video:
                resolved_video_id = repeat_res.video.id
            else:
                error_msg = repeat_res.error_reason
        elif schedule.source_type.upper() in ["VIDEO", "SPECIFIC_VIDEO"]:
            resolved_video_id = schedule.source_id

        # 4. Create or Update Occurrence
        if not existing_occ:
            occurrence = ScheduleOccurrence(
                schedule_id=schedule.id,
                channel_id=schedule.channel_id,
                video_id=resolved_video_id,
                scheduled_publish_time=scheduled_publish_dt.replace(tzinfo=None),
                target_upload_time=now_in_tz.replace(tzinfo=None),
                dry_run=schedule.dry_run,
                status="QUEUED" if resolved_video_id else "FAILED",
                idempotency_key=idempotency_key,
                error_message=error_msg
            )
            session.add(occurrence)
            await session.commit()
            await session.refresh(occurrence)
            occ_id = occurrence.id

            if resolved_video_id:
                upload_job = UploadJob(
                    occurrence_id=occ_id,
                    status="QUEUED"
                )
                session.add(upload_job)
                await session.commit()
        else:
            occ_id = existing_occ.id
            if resolved_video_id:
                existing_occ.video_id = resolved_video_id
                existing_occ.status = "QUEUED"
                existing_occ.error_message = None

                uj_stmt = select(UploadJob).where(UploadJob.occurrence_id == occ_id)
                uj_res = await session.execute(uj_stmt)
                uj = uj_res.scalars().first()
                if not uj:
                    uj = UploadJob(occurrence_id=occ_id, status="QUEUED")
                    session.add(uj)
                else:
                    uj.status = "QUEUED"
                    uj.error_message = None
                await session.commit()

        logger.info(f"Created/Queued schedule occurrence {occ_id} for schedule '{schedule.name}' (video_id: {resolved_video_id})")

        # 5. Trigger Upload Pipeline via UploadWorkerPool if enabled
        if trigger_upload and resolved_video_id:
            publish_at_dt = scheduled_publish_dt if schedule.use_youtube_scheduled_publish else None
            try:
                worker_pool = UploadWorkerPool.get_instance()
                await worker_pool.submit_upload(
                    occurrence_id=occ_id,
                    publish_at=publish_at_dt,
                    dry_run=schedule.dry_run,
                    db=session
                )
            except Exception as e:
                logger.error(f"Upload job for occurrence {occ_id} failed: {e}")

        return occ_id

    if db:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)
