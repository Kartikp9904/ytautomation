import os
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.channel import Channel
from app.models.schedule import Schedule
from app.models.video import Video
from app.models.occurrence import ScheduleOccurrence
from app.models.oauth import OAuthCredential
from app.services.scheduler.scheduler_engine import SchedulerEngine, execute_schedule_job
from app.services.youtube.uploader import YouTubeUploaderService
from app.core.security import encrypt_secret


@pytest.mark.asyncio
async def test_scheduled_upload_with_publish_at(test_db_session: AsyncSession):
    # Setup dummy video file
    os.makedirs(settings.LOCAL_STORAGE_BASE_PATH, exist_ok=True)
    vid_name = "scheduled_test_vid.mp4"
    vid_path = os.path.join(settings.LOCAL_STORAGE_BASE_PATH, vid_name)
    with open(vid_path, "wb") as f:
        f.write(b"dummy video content scheduled")

    try:
        channel = Channel(name="Scheduled Channel", timezone="UTC", youtube_channel_id="UC_SCHED")
        test_db_session.add(channel)
        await test_db_session.commit()
        await test_db_session.refresh(channel)

        cred = OAuthCredential(
            service_type="youtube_channel",
            channel_id=channel.id,
            account_email="sched@youtube.com",
            encrypted_refresh_token=encrypt_secret("ref_tok"),
            encrypted_access_token=encrypt_secret("acc_tok"),
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
            is_valid=True
        )
        test_db_session.add(cred)

        video = Video(
            channel_id=channel.id,
            storage_provider="local",
            storage_file_id=vid_name,
            filename=vid_name,
            path=vid_name,
            enabled=True
        )
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)

        future_publish = datetime(2026, 8, 20, 18, 0, 0, tzinfo=timezone.utc)

        occurrence = ScheduleOccurrence(
            channel_id=channel.id,
            video_id=video.id,
            idempotency_key="sched_test_occ_1",
            scheduled_publish_time=future_publish.replace(tzinfo=None),
            target_upload_time=datetime.now(),
            status="QUEUED"
        )
        test_db_session.add(occurrence)
        await test_db_session.commit()
        await test_db_session.refresh(occurrence)

        # Mock YouTube client
        mock_youtube = MagicMock()
        mock_insert = MagicMock()
        mock_insert.next_chunk.return_value = (None, {"id": "YT_SCHED_VID_999"})
        mock_youtube.videos().insert.return_value = mock_insert

        with patch("app.services.youtube.uploader.YouTubeOAuthService.get_authenticated_service", return_value=mock_youtube):
            res = await YouTubeUploaderService.run_upload_job(
                occurrence_id=occurrence.id,
                publish_at=future_publish,
                db=test_db_session
            )

            assert res["status"] == "SUCCESS"
            assert res["youtube_video_id"] == "YT_SCHED_VID_999"
            assert res["publish_at"] == "2026-08-20T18:00:00.000Z"

            # Check insert arguments passed to YouTube API
            call_kwargs = mock_youtube.videos().insert.call_args[1]
            status_sent = call_kwargs["body"]["status"]
            assert status_sent["privacyStatus"] == "private"
            assert status_sent["publishAt"] == "2026-08-20T18:00:00.000Z"

    finally:
        if os.path.exists(vid_path):
            os.remove(vid_path)


@pytest.mark.asyncio
async def test_dry_run_mode(test_db_session: AsyncSession):
    channel = Channel(name="Dry Run Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="dummy_file_dry",
        filename="dry_run.mp4",
        path="dry_run.mp4",
        enabled=True
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    schedule = Schedule(
        channel_id=channel.id,
        name="Dry Run Daily",
        schedule_type="DAILY",
        source_type="VIDEO",
        source_id=video.id,
        mode="REPEAT",
        publish_time="15:00",
        timezone="UTC",
        upload_lead_minutes=120,
        use_youtube_scheduled_publish=True,
        dry_run=True,
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    occ_id = await execute_schedule_job(
        schedule_id=schedule.id,
        db=test_db_session,
        trigger_upload=True
    )

    assert occ_id is not None

    # Check occurrence status
    occ = await test_db_session.get(ScheduleOccurrence, occ_id)
    assert occ.status == "COMPLETED"
    assert occ.dry_run is True
    assert occ.youtube_video_id == "DRY_RUN_MOCK_ID"


@pytest.mark.asyncio
async def test_trigger_now_endpoint(client: AsyncClient, test_db_session: AsyncSession):
    channel = Channel(name="Trigger Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="vid_trig",
        filename="trig.mp4",
        path="trig.mp4",
        enabled=True
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    schedule = Schedule(
        channel_id=channel.id,
        name="Trigger Now Schedule",
        schedule_type="DAILY",
        source_type="VIDEO",
        source_id=video.id,
        mode="REPEAT",
        publish_time="10:00",
        timezone="UTC",
        dry_run=True,
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    res = await client.post(f"/api/v1/schedules/{schedule.id}/trigger-now")
    assert res.status_code == 200
    data = res.json()
    assert data["schedule_id"] == schedule.id
    assert "occurrence_id" in data
