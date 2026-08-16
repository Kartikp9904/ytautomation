import pytest
from datetime import datetime, date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.schedule import Schedule
from app.services.scheduler.modes.day_of_month import DayOfMonthResolver


def test_calendar_leap_year_and_days():
    # Common year Feb 2026 -> 28 days, not leap
    days, is_leap = DayOfMonthResolver.get_days_in_month(2026, 2)
    assert days == 28
    assert is_leap is False

    # Leap year Feb 2028 -> 29 days, leap year
    days_leap, is_leap_2028 = DayOfMonthResolver.get_days_in_month(2028, 2)
    assert days_leap == 29
    assert is_leap_2028 is True

    # 30-day month (April)
    days_apr, _ = DayOfMonthResolver.get_days_in_month(2026, 4)
    assert days_apr == 30

    # 31-day month (August)
    days_aug, _ = DayOfMonthResolver.get_days_in_month(2026, 8)
    assert days_aug == 31


@pytest.mark.asyncio
async def test_day_of_month_resolution_and_fallback(test_db_session: AsyncSession):
    # Setup channel, folder, and videos
    channel = Channel(name="Aarti Channel", timezone="Asia/Kolkata")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_aarti",
        name="Daily Aarti",
        path="Aarti"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    # Add videos for day 1, day 15, and default.mp4
    v1 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_1",
        filename="1.mp4",
        path="Aarti/1.mp4",
        day_of_month_index=1,
        enabled=True
    )
    v15 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_15",
        filename="15.mp4",
        path="Aarti/15.mp4",
        day_of_month_index=15,
        enabled=True
    )
    v_def = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_def",
        filename="default.mp4",
        path="Aarti/default.mp4",
        day_of_month_index=None,
        enabled=True
    )
    test_db_session.add_all([v1, v15, v_def])
    await test_db_session.commit()

    schedule = Schedule(
        channel_id=channel.id,
        name="Aarti Daily Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="DAY_OF_MONTH",
        publish_time="09:00",
        timezone="Asia/Kolkata",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # 1. Test Day 15 exact match
    res_15 = await DayOfMonthResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 15, 9, 0, 0),
        db=test_db_session
    )
    assert res_15.is_matched is True
    assert res_15.video is not None
    assert res_15.video.filename == "15.mp4"

    # 2. Test Day 1 exact match
    res_1 = await DayOfMonthResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 1, 9, 0, 0),
        db=test_db_session
    )
    assert res_1.is_matched is True
    assert res_1.video is not None
    assert res_1.video.filename == "1.mp4"

    # 3. Test Day 20 fallback to default.mp4
    res_20 = await DayOfMonthResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 20, 9, 0, 0),
        db=test_db_session
    )
    assert res_20.is_matched is False
    assert res_20.is_fallback is True
    assert res_20.video is not None
    assert res_20.video.filename == "default.mp4"


@pytest.mark.asyncio
async def test_simulate_calendar_endpoint(client: AsyncClient, test_db_session: AsyncSession):
    # Setup channel, folder, schedule
    channel = Channel(name="Calendar Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_cal",
        name="Month Test",
        path="MonthTest"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    v15 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_15_cal",
        filename="15.mp4",
        path="MonthTest/15.mp4",
        day_of_month_index=15,
        enabled=True
    )
    test_db_session.add(v15)
    await test_db_session.commit()

    schedule = Schedule(
        channel_id=channel.id,
        name="Month Sim Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="DAY_OF_MONTH",
        publish_time="09:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # Simulate February 2028 (Leap year -> 29 days)
    res = await client.post(
        f"/api/v1/schedules/{schedule.id}/simulate-calendar",
        params={"year": 2028, "month": 2}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["year"] == 2028
    assert data["month"] == 2
    assert data["days_in_month"] == 29
    assert data["is_leap_year"] is True
    assert len(data["days"]) == 29
    
    # Day 15 should be matched
    day_15 = data["days"][14]
    assert day_15["day_number"] == 15
    assert day_15["is_matched"] is True
    assert day_15["video_filename"] == "15.mp4"
