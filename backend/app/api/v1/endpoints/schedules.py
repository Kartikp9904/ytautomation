from typing import Optional, List
from datetime import datetime, date, time, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.core.database import get_db
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.state import RotationState, ShuffleState
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleOccurrenceResponse,
    TriggerNowResponse,
    ResetRotationResponse,
    ReshuffleResponse,
    CalendarSimulationResponse,
    CalendarDaySimulation,
    TimelineItem,
    CalendarEventItem
)
from app.services.scheduler.scheduler_engine import SchedulerEngine, execute_schedule_job
from app.services.scheduler.modes.day_of_month import DayOfMonthResolver
from app.services.scheduler.modes.rotation import RotationModeResolver
from app.services.scheduler.modes.shuffle import ShuffleModeResolver

router = APIRouter()


@router.get("/timeline/today", response_model=List[TimelineItem])
async def get_today_timeline(db: AsyncSession = Depends(get_db)):
    """
    Returns all schedule occurrences and manual uploads targeted for today.
    """
    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)

    stmt = select(
        ScheduleOccurrence,
        Channel.name.label("channel_name"),
        Schedule.name.label("schedule_name"),
        Video.filename.label("video_filename")
    )\
        .join(Channel, ScheduleOccurrence.channel_id == Channel.id)\
        .outerjoin(Schedule, ScheduleOccurrence.schedule_id == Schedule.id)\
        .outerjoin(Video, ScheduleOccurrence.video_id == Video.id)\
        .where(
            ScheduleOccurrence.scheduled_publish_time >= today_start,
            ScheduleOccurrence.scheduled_publish_time < today_end
        )\
        .order_by(ScheduleOccurrence.scheduled_publish_time)

    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for occ, ch_name, sch_name, v_fname in rows:
        title = v_fname or f"Upload ({occ.id[:8]})"
        yt_url = f"https://youtu.be/{occ.youtube_video_id}" if occ.youtube_video_id and occ.youtube_video_id != "DRY_RUN_MOCK_ID" else None
        
        items.append(TimelineItem(
            id=occ.id,
            schedule_id=occ.schedule_id,
            schedule_name=sch_name or "Manual Upload",
            channel_name=ch_name,
            channel_id=occ.channel_id,
            video_title=title,
            scheduled_publish_time=occ.scheduled_publish_time.isoformat(),
            target_upload_time=occ.target_upload_time.isoformat(),
            status=occ.status,
            dry_run=occ.dry_run,
            youtube_video_id=occ.youtube_video_id,
            youtube_url=yt_url
        ))

    return items


@router.get("/calendar/events", response_model=List[CalendarEventItem])
async def get_calendar_events(
    year: int = Query(default=datetime.now().year, ge=2020, le=2050),
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    channel_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns calendar publication events for a specific month and year.
    """
    start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    stmt = select(
        ScheduleOccurrence,
        Channel.name.label("channel_name"),
        Schedule.name.label("schedule_name"),
        Schedule.mode.label("schedule_mode"),
        Schedule.publish_time.label("sched_publish_time"),
        Video.filename.label("video_filename")
    )\
        .join(Channel, ScheduleOccurrence.channel_id == Channel.id)\
        .outerjoin(Schedule, ScheduleOccurrence.schedule_id == Schedule.id)\
        .outerjoin(Video, ScheduleOccurrence.video_id == Video.id)\
        .where(
            ScheduleOccurrence.scheduled_publish_time >= start_date,
            ScheduleOccurrence.scheduled_publish_time < end_date
        )

    if channel_id:
        stmt = stmt.where(ScheduleOccurrence.channel_id == channel_id)

    stmt = stmt.order_by(ScheduleOccurrence.scheduled_publish_time)
    res = await db.execute(stmt)
    rows = res.all()

    events = []
    for occ, ch_name, sch_name, sch_mode, pub_time, v_fname in rows:
        title = v_fname or "Scheduled Video"
        d_str = occ.scheduled_publish_time.strftime("%Y-%m-%d")
        yt_url = f"https://youtu.be/{occ.youtube_video_id}" if occ.youtube_video_id and occ.youtube_video_id != "DRY_RUN_MOCK_ID" else None

        events.append(CalendarEventItem(
            id=occ.id,
            date=d_str,
            title=title,
            schedule_name=sch_name or "Manual Upload",
            channel_name=ch_name,
            mode=sch_mode or "DIRECT",
            publish_time=pub_time or occ.scheduled_publish_time.strftime("%H:%M"),
            status=occ.status,
            dry_run=occ.dry_run,
            youtube_url=yt_url
        ))

    return events


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    channel_id: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    schedule_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Schedule, Channel.name.label("channel_name"))\
        .outerjoin(Channel, Schedule.channel_id == Channel.id)

    if channel_id:
        stmt = stmt.where(Schedule.channel_id == channel_id)
    if enabled is not None:
        stmt = stmt.where(Schedule.enabled == enabled)
    if mode:
        stmt = stmt.where(Schedule.mode == mode.upper())
    if schedule_type:
        stmt = stmt.where(Schedule.schedule_type == schedule_type.upper())

    stmt = stmt.order_by(desc(Schedule.created_at))
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for sched, ch_name in rows:
        # Resolve source name (Folder name or Video filename)
        src_name = sched.source_id
        if sched.source_type == "FOLDER":
            f_res = await db.execute(select(ContentFolder.name).where(ContentFolder.id == sched.source_id))
            f_name = f_res.scalar()
            if f_name:
                src_name = f_name
        elif sched.source_type == "VIDEO" or sched.source_type == "SPECIFIC_VIDEO":
            v_res = await db.execute(select(Video.filename).where(Video.id == sched.source_id))
            v_name = v_res.scalar()
            if v_name:
                src_name = v_name

        next_run = SchedulerEngine.get_next_run_time(sched.id) if sched.enabled else None

        # Rotation state if applicable
        rot_idx = None
        rot_total = None
        if sched.mode == "ROTATION":
            r_res = await db.execute(select(RotationState).where(RotationState.schedule_id == sched.id))
            r_state = r_res.scalars().first()
            rot_idx = r_state.current_index if r_state else 0
            videos = await RotationModeResolver.get_ordered_videos(sched, db)
            rot_total = len(videos)

        # Shuffle state if applicable
        shuf_rem = None
        shuf_used = None
        shuf_cyc = None
        if sched.mode == "SHUFFLE":
            s_res = await db.execute(select(ShuffleState).where(ShuffleState.schedule_id == sched.id))
            s_state = s_res.scalars().first()
            if s_state:
                shuf_rem = len(s_state.remaining_video_ids or [])
                shuf_used = len(s_state.used_video_ids or [])
                shuf_cyc = s_state.current_cycle

        items.append(ScheduleResponse(
            id=sched.id,
            channel_id=sched.channel_id,
            name=sched.name,
            schedule_type=sched.schedule_type,
            source_type=sched.source_type,
            source_id=sched.source_id,
            mode=sched.mode,
            publish_time=sched.publish_time,
            timezone=sched.timezone,
            days_of_week=sched.days_of_week or [],
            day_of_month=sched.days_of_month[0] if sched.days_of_month else None,
            enabled=sched.enabled,
            title_template=sched.title_template,
            description_template=sched.description_template,
            tags=sched.tags or [],
            category_id=sched.category_id,
            privacy_status=sched.privacy_status,
            created_at=sched.created_at,
            updated_at=sched.updated_at,
            next_run_time=next_run,
            channel_name=ch_name,
            source_name=src_name,
            current_rotation_index=rot_idx,
            total_rotation_videos=rot_total,
            shuffle_remaining_count=shuf_rem,
            shuffle_used_count=shuf_used,
            shuffle_cycle=shuf_cyc
        ))

    return ScheduleListResponse(total=len(items), items=items)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    ch_res = await db.execute(select(Channel).where(Channel.id == data.channel_id))
    channel = ch_res.scalars().first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID '{data.channel_id}' not found"
        )

    timezone = data.timezone or channel.timezone or "UTC"

    schedule = Schedule(
        channel_id=data.channel_id,
        name=data.name,
        schedule_type=data.schedule_type.upper(),
        source_type=data.source_type.upper(),
        source_id=data.source_id,
        mode=data.mode.upper(),
        publish_time=data.publish_time,
        timezone=timezone,
        days_of_week=[d.upper() for d in data.days_of_week] if data.days_of_week else [],
        days_of_month=[data.day_of_month] if data.day_of_month else [],
        enabled=data.enabled,
        title_template=data.title_template,
        description_template=data.description_template,
        tags=data.tags or [],
        category_id=data.category_id,
        privacy_status=data.privacy_status or "private"
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    if schedule.mode == "ROTATION":
        await RotationModeResolver.get_or_create_state(schedule.id, db)
    elif schedule.mode == "SHUFFLE":
        await ShuffleModeResolver.get_or_create_state(schedule.id, db)

    if schedule.enabled:
        SchedulerEngine.register_schedule_job(schedule)

    return await get_schedule(schedule.id, db)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Schedule, Channel.name.label("channel_name"))\
        .outerjoin(Channel, Schedule.channel_id == Channel.id)\
        .where(Schedule.id == schedule_id)
    
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    sched, ch_name = row
    src_name = sched.source_id
    if sched.source_type == "FOLDER":
        f_res = await db.execute(select(ContentFolder.name).where(ContentFolder.id == sched.source_id))
        f_name = f_res.scalar()
        if f_name:
            src_name = f_name
    elif sched.source_type == "VIDEO" or sched.source_type == "SPECIFIC_VIDEO":
        v_res = await db.execute(select(Video.filename).where(Video.id == sched.source_id))
        v_name = v_res.scalar()
        if v_name:
            src_name = v_name

    next_run = SchedulerEngine.get_next_run_time(sched.id) if sched.enabled else None

    rot_idx = None
    rot_total = None
    if sched.mode == "ROTATION":
        r_res = await db.execute(select(RotationState).where(RotationState.schedule_id == sched.id))
        r_state = r_res.scalars().first()
        rot_idx = r_state.current_index if r_state else 0
        videos = await RotationModeResolver.get_ordered_videos(sched, db)
        rot_total = len(videos)

    shuf_rem = None
    shuf_used = None
    shuf_cyc = None
    if sched.mode == "SHUFFLE":
        s_res = await db.execute(select(ShuffleState).where(ShuffleState.schedule_id == sched.id))
        s_state = s_res.scalars().first()
        if s_state:
            shuf_rem = len(s_state.remaining_video_ids or [])
            shuf_used = len(s_state.used_video_ids or [])
            shuf_cyc = s_state.current_cycle

    return ScheduleResponse(
        id=sched.id,
        channel_id=sched.channel_id,
        name=sched.name,
        schedule_type=sched.schedule_type,
        source_type=sched.source_type,
        source_id=sched.source_id,
        mode=sched.mode,
        publish_time=sched.publish_time,
        timezone=sched.timezone,
        days_of_week=sched.days_of_week or [],
        day_of_month=sched.days_of_month[0] if sched.days_of_month else None,
        enabled=sched.enabled,
        title_template=sched.title_template,
        description_template=sched.description_template,
        tags=sched.tags or [],
        category_id=sched.category_id,
        privacy_status=sched.privacy_status,
        created_at=sched.created_at,
        updated_at=sched.updated_at,
        next_run_time=next_run,
        channel_name=ch_name,
        source_name=src_name,
        current_rotation_index=rot_idx,
        total_rotation_videos=rot_total,
        shuffle_remaining_count=shuf_rem,
        shuffle_used_count=shuf_used,
        shuffle_cycle=shuf_cyc
    )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        if field == "schedule_type" and val:
            val = val.upper()
        if field == "mode" and val:
            val = val.upper()
        if field == "source_type" and val:
            val = val.upper()
        if field == "day_of_month":
            schedule.days_of_month = [val] if val else []
            continue
        setattr(schedule, field, val)

    await db.commit()
    await db.refresh(schedule)

    if schedule.mode == "ROTATION":
        await RotationModeResolver.get_or_create_state(schedule.id, db)
    elif schedule.mode == "SHUFFLE":
        await ShuffleModeResolver.get_or_create_state(schedule.id, db)

    if schedule.enabled:
        SchedulerEngine.register_schedule_job(schedule)
    else:
        SchedulerEngine.unregister_schedule_job(schedule.id)

    return await get_schedule(schedule_id, db)


@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule_status(schedule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    schedule.enabled = not schedule.enabled
    await db.commit()
    await db.refresh(schedule)

    if schedule.enabled:
        SchedulerEngine.register_schedule_job(schedule)
    else:
        SchedulerEngine.unregister_schedule_job(schedule.id)

    return await get_schedule(schedule_id, db)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    SchedulerEngine.unregister_schedule_job(schedule_id)
    await db.delete(schedule)
    await db.commit()
    return None


@router.post("/{schedule_id}/trigger-now", response_model=TriggerNowResponse)
async def trigger_schedule_now(schedule_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    occ_id = await execute_schedule_job(schedule.id, db=db, manual_target_date=datetime.now())

    return TriggerNowResponse(
        message=f"Schedule '{schedule.name}' triggered successfully.",
        schedule_id=schedule.id,
        occurrence_id=occ_id,
        status="QUEUED"
    )


@router.post("/{schedule_id}/reset-rotation", response_model=ResetRotationResponse)
async def reset_rotation_index(
    schedule_id: str,
    index: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    state = await RotationModeResolver.reset_rotation_index(schedule.id, index, db)
    return ResetRotationResponse(
        message=f"Rotation index for schedule '{schedule.name}' updated to {state.current_index}.",
        schedule_id=schedule.id,
        current_index=state.current_index
    )


@router.post("/{schedule_id}/reshuffle", response_model=ReshuffleResponse)
async def reshuffle_schedule_pool(
    schedule_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    state = await ShuffleModeResolver.reshuffle_pool(schedule.id, db)
    return ReshuffleResponse(
        message=f"Video pool for schedule '{schedule.name}' reshuffled successfully.",
        schedule_id=schedule.id,
        total_shuffled=len(state.remaining_video_ids or []),
        current_cycle=state.current_cycle
    )


@router.get("/{schedule_id}/occurrences", response_model=List[ScheduleOccurrenceResponse])
async def list_schedule_occurrences(
    schedule_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ScheduleOccurrence)\
        .where(ScheduleOccurrence.schedule_id == schedule_id)\
        .order_by(desc(ScheduleOccurrence.scheduled_publish_time))\
        .limit(limit)

    res = await db.execute(stmt)
    occurrences = res.scalars().all()
    return occurrences


@router.post("/{schedule_id}/simulate-calendar", response_model=CalendarSimulationResponse)
async def simulate_calendar_month(
    schedule_id: str,
    year: int = Query(default=datetime.now().year, ge=2020, le=2050),
    month: int = Query(default=datetime.now().month, ge=1, le=12),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Schedule).where(Schedule.id == schedule_id)
    res = await db.execute(stmt)
    schedule = res.scalars().first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID '{schedule_id}' not found"
        )

    if schedule.mode.upper() == "SHUFFLE":
        results = await ShuffleModeResolver.simulate_month_schedule(schedule, year, month, db)
    elif schedule.mode.upper() == "ROTATION":
        results = await RotationModeResolver.simulate_month_schedule(schedule, year, month, db)
    else:
        results = await DayOfMonthResolver.simulate_month_schedule(schedule, year, month, db)

    days_in_month, is_leap = DayOfMonthResolver.get_days_in_month(year, month)

    day_items = [
        CalendarDaySimulation(
            date=r.target_date.isoformat(),
            day_number=r.day_number,
            video_id=r.video.id if r.video else None,
            video_filename=r.video.filename if r.video else None,
            is_matched=r.is_matched,
            is_fallback=r.is_fallback,
            fallback_reason=r.fallback_reason,
            is_leap_year=r.is_leap_year,
            days_in_month=r.days_in_month
        )
        for r in results
    ]

    return CalendarSimulationResponse(
        schedule_id=schedule.id,
        year=year,
        month=month,
        days_in_month=days_in_month,
        is_leap_year=is_leap,
        days=day_items
    )
