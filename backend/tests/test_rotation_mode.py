import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.schedule import Schedule
from app.services.scheduler.modes.rotation import RotationModeResolver
from app.services.scheduler.scheduler_engine import execute_schedule_job


@pytest.mark.asyncio
async def test_rotation_mode_sequential_and_loop(test_db_session: AsyncSession):
    channel = Channel(name="Rotation Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_rot",
        name="Rotation Pool",
        path="Rotation"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    # Add 3 sequential videos
    v1 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_rot_1",
        filename="Episode_01.mp4",
        path="Rotation/Episode_01.mp4",
        enabled=True
    )
    v2 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_rot_2",
        filename="Episode_02.mp4",
        path="Rotation/Episode_02.mp4",
        enabled=True
    )
    v3 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_rot_3",
        filename="Episode_03.mp4",
        path="Rotation/Episode_03.mp4",
        enabled=True
    )
    test_db_session.add_all([v1, v2, v3])
    await test_db_session.commit()

    schedule = Schedule(
        channel_id=channel.id,
        name="Rotation Queue Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="ROTATION",
        publish_time="10:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # 1. First run -> Episode_01 (Index 0 -> advances to 1)
    res1 = await RotationModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 1, 10, 0, 0),
        db=test_db_session,
        advance_index=True
    )
    assert res1.is_matched is True
    assert res1.video.filename == "Episode_01.mp4"
    assert res1.current_index == 0
    assert res1.next_index == 1
    assert res1.is_loop_restart is False

    # 2. Second run -> Episode_02 (Index 1 -> advances to 2)
    res2 = await RotationModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 2, 10, 0, 0),
        db=test_db_session,
        advance_index=True
    )
    assert res2.is_matched is True
    assert res2.video.filename == "Episode_02.mp4"
    assert res2.current_index == 1
    assert res2.next_index == 2
    assert res2.is_loop_restart is False

    # 3. Third run -> Episode_03 (Index 2 -> advances to 0 with loop restart!)
    res3 = await RotationModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 3, 10, 0, 0),
        db=test_db_session,
        advance_index=True
    )
    assert res3.is_matched is True
    assert res3.video.filename == "Episode_03.mp4"
    assert res3.current_index == 2
    assert res3.next_index == 0
    assert res3.is_loop_restart is True

    # 4. Fourth run -> Episode_01 (Wraparound back to beginning!)
    res4 = await RotationModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 4, 10, 0, 0),
        db=test_db_session,
        advance_index=True
    )
    assert res4.is_matched is True
    assert res4.video.filename == "Episode_01.mp4"
    assert res4.current_index == 0


@pytest.mark.asyncio
async def test_reset_rotation_endpoint(client: AsyncClient, test_db_session: AsyncSession):
    channel = Channel(name="Reset Rot Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    schedule = Schedule(
        channel_id=channel.id,
        name="Reset Test Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id="dummy_folder",
        mode="ROTATION",
        publish_time="09:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # Call reset rotation endpoint to set index to 2
    res = await client.post(
        f"/api/v1/schedules/{schedule.id}/reset-rotation",
        params={"index": 2}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_index"] == 2
