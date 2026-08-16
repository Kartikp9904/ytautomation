import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.schedule import Schedule
from app.services.scheduler.modes.repeat import RepeatModeResolver
from app.services.scheduler.scheduler_engine import execute_schedule_job
from app.services.metadata.metadata_engine import MetadataEngine


@pytest.mark.asyncio
async def test_repeat_mode_resolution(test_db_session: AsyncSession):
    # Setup channel, folder, and a single evergreen video
    channel = Channel(
        name="Evergreen Channel",
        timezone="Asia/Kolkata",
        default_title_template="Daily Meditation | {date} | {channel}"
    )
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_meditation",
        name="Meditation",
        path="Evergreen/Meditation"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    video = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_meditation_1",
        filename="peaceful_mantra.mp4",
        path="Evergreen/Meditation/peaceful_mantra.mp4",
        enabled=True
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    # 1. Schedule pointing directly to video
    schedule = Schedule(
        channel_id=channel.id,
        name="Daily Peaceful Mantra",
        schedule_type="DAILY",
        source_type="VIDEO",
        source_id=video.id,
        mode="REPEAT",
        publish_time="07:00",
        timezone="Asia/Kolkata",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # 2. Resolve on Day 1
    dt1 = datetime(2026, 8, 15, 7, 0, 0)
    res1 = await RepeatModeResolver.resolve_video_for_date(schedule, dt1, test_db_session)
    assert res1.is_matched is True
    assert res1.video.id == video.id

    # Check dynamic title evaluation on Day 1
    meta1 = MetadataEngine.resolve_effective_metadata(
        video=res1.video,
        channel=channel,
        target_datetime=dt1
    )
    assert "15 August 2026" in meta1.title
    assert "Evergreen Channel" in meta1.title

    # 3. Resolve on Day 2
    dt2 = datetime(2026, 8, 16, 7, 0, 0)
    res2 = await RepeatModeResolver.resolve_video_for_date(schedule, dt2, test_db_session)
    assert res2.is_matched is True
    assert res2.video.id == video.id

    # Check dynamic title evaluation on Day 2 (Different date, same video!)
    meta2 = MetadataEngine.resolve_effective_metadata(
        video=res2.video,
        channel=channel,
        target_datetime=dt2
    )
    assert "16 August 2026" in meta2.title

    # 4. Test Job Execution in Repeat Mode
    occ_id = await execute_schedule_job(schedule.id, db=test_db_session, manual_target_date=dt1)
    assert occ_id is not None


@pytest.mark.asyncio
async def test_repeat_mode_disabled_video(test_db_session: AsyncSession):
    channel = Channel(name="Test Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="vid_dis",
        filename="disabled.mp4",
        path="Test/disabled.mp4",
        enabled=False # Disabled!
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    schedule = Schedule(
        channel_id=channel.id,
        name="Disabled Video Schedule",
        schedule_type="DAILY",
        source_type="VIDEO",
        source_id=video.id,
        mode="REPEAT",
        publish_time="08:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    res = await RepeatModeResolver.resolve_video_for_date(schedule, datetime.now(), test_db_session)
    assert res.is_matched is False
    assert "disabled" in res.error_reason.lower()
