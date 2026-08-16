import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.schedule import Schedule
from app.services.scheduler.modes.shuffle import ShuffleModeResolver
from app.services.scheduler.scheduler_engine import execute_schedule_job


@pytest.mark.asyncio
async def test_shuffle_mode_non_repeating_and_cycle(test_db_session: AsyncSession):
    channel = Channel(name="Shuffle Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_shuf",
        name="Shuffle Pool",
        path="Shuffle"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    # Add 3 videos to shuffle pool
    v1 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_shuf_1",
        filename="Clip_A.mp4",
        path="Shuffle/Clip_A.mp4",
        enabled=True
    )
    v2 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_shuf_2",
        filename="Clip_B.mp4",
        path="Shuffle/Clip_B.mp4",
        enabled=True
    )
    v3 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_shuf_3",
        filename="Clip_C.mp4",
        path="Shuffle/Clip_C.mp4",
        enabled=True
    )
    test_db_session.add_all([v1, v2, v3])
    await test_db_session.commit()

    schedule = Schedule(
        channel_id=channel.id,
        name="Shuffle Test Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="SHUFFLE",
        publish_time="11:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # 1. First pick (Cycle 1, 2 remaining after pick)
    res1 = await ShuffleModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 1, 11, 0, 0),
        db=test_db_session,
        advance_queue=True
    )
    assert res1.is_matched is True
    assert res1.current_cycle == 1
    assert res1.remaining_count == 2
    assert res1.used_count == 1
    vid1_id = res1.video.id

    # 2. Second pick (Cycle 1, 1 remaining after pick)
    res2 = await ShuffleModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 2, 11, 0, 0),
        db=test_db_session,
        advance_queue=True
    )
    assert res2.is_matched is True
    assert res2.current_cycle == 1
    assert res2.remaining_count == 1
    assert res2.used_count == 2
    vid2_id = res2.video.id
    assert vid2_id != vid1_id # Non-repeating!

    # 3. Third pick (Cycle 1, 0 remaining after pick)
    res3 = await ShuffleModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 3, 11, 0, 0),
        db=test_db_session,
        advance_queue=True
    )
    assert res3.is_matched is True
    assert res3.current_cycle == 1
    assert res3.remaining_count == 0
    assert res3.used_count == 3
    vid3_id = res3.video.id
    assert vid3_id != vid1_id and vid3_id != vid2_id

    # All 3 videos were played exactly once in Cycle 1!
    assert {vid1_id, vid2_id, vid3_id} == {v1.id, v2.id, v3.id}

    # 4. Fourth pick -> Automatically advances to Cycle 2 with fresh reshuffle!
    res4 = await ShuffleModeResolver.resolve_video_for_date(
        schedule=schedule,
        target_datetime=datetime(2026, 8, 4, 11, 0, 0),
        db=test_db_session,
        advance_queue=True
    )
    assert res4.is_matched is True
    assert res4.current_cycle == 2
    assert res4.is_new_cycle is True
    assert res4.remaining_count == 2
    assert res4.used_count == 1


@pytest.mark.asyncio
async def test_reshuffle_endpoint(client: AsyncClient, test_db_session: AsyncSession):
    channel = Channel(name="Reshuffle Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_reshuf",
        name="Reshuffle Pool",
        path="Reshuffle"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    v1 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_r1",
        filename="1.mp4",
        path="Reshuffle/1.mp4",
        enabled=True
    )
    v2 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_r2",
        filename="2.mp4",
        path="Reshuffle/2.mp4",
        enabled=True
    )
    test_db_session.add_all([v1, v2])
    await test_db_session.commit()

    schedule = Schedule(
        channel_id=channel.id,
        name="Reshuffle API Test",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="SHUFFLE",
        publish_time="09:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # Call reshuffle endpoint
    res = await client.post(f"/api/v1/schedules/{schedule.id}/reshuffle")
    assert res.status_code == 200
    data = res.json()
    assert data["total_shuffled"] == 2
    assert data["current_cycle"] == 1
