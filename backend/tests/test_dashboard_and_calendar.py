import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.channel import Channel
from app.models.video import Video
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence


@pytest.mark.asyncio
async def test_today_timeline_and_calendar_events(client: AsyncClient, test_db_session: AsyncSession):
    channel = Channel(name="Calendar Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="cal_vid_1",
        filename="video_01.mp4",
        path="video_01.mp4"
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    schedule = Schedule(
        channel_id=channel.id,
        name="Daily Calendar Schedule",
        schedule_type="DAILY",
        source_type="VIDEO",
        source_id=video.id,
        mode="REPEAT",
        publish_time="18:00",
        timezone="UTC"
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    now_utc = datetime.now(timezone.utc)

    # 1. Occurrence for Today
    occ_today = ScheduleOccurrence(
        schedule_id=schedule.id,
        channel_id=channel.id,
        video_id=video.id,
        idempotency_key="cal_occ_today",
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc - timedelta(hours=2),
        status="QUEUED"
    )
    test_db_session.add(occ_today)
    await test_db_session.commit()

    # 2. Test Today's Timeline Endpoint
    t_res = await client.get("/api/v1/schedules/timeline/today")
    assert t_res.status_code == 200
    timeline = t_res.json()
    assert len(timeline) >= 1
    assert timeline[0]["channel_name"] == "Calendar Channel"
    assert timeline[0]["video_title"] == "video_01.mp4"

    # 3. Test Calendar Events Endpoint
    c_res = await client.get(f"/api/v1/schedules/calendar/events?year={now_utc.year}&month={now_utc.month}")
    assert c_res.status_code == 200
    events = c_res.json()
    assert len(events) >= 1
    assert events[0]["channel_name"] == "Calendar Channel"
    assert events[0]["date"] == now_utc.strftime("%Y-%m-%d")
