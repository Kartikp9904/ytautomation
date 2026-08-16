import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from app.models.channel import Channel
from app.models.video import Video
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.services.youtube.copyright_guard import CopyrightGuardService


@pytest.mark.asyncio
async def test_inspect_youtube_video_flagged():
    mock_youtube = MagicMock()
    mock_request = MagicMock()
    mock_request.execute.return_value = {
        "items": [
            {
                "status": {
                    "uploadStatus": "rejected",
                    "rejectionReason": "copyright",
                    "privacyStatus": "private"
                },
                "processingDetails": {
                    "processingStatus": "failed",
                    "processingFailureReason": "copyright"
                }
            }
        ]
    }
    mock_youtube.videos().list.return_value = mock_request

    inspection = await CopyrightGuardService.inspect_youtube_video(mock_youtube, "vid_copyright_123")
    assert inspection["exists"] is True
    assert inspection["is_flagged"] is True
    assert "copyright" in inspection["reason"].lower()


@pytest.mark.asyncio
async def test_inspect_youtube_video_clean():
    mock_youtube = MagicMock()
    mock_request = MagicMock()
    mock_request.execute.return_value = {
        "items": [
            {
                "status": {
                    "uploadStatus": "processed",
                    "privacyStatus": "private"
                },
                "processingDetails": {
                    "processingStatus": "succeeded"
                }
            }
        ]
    }
    mock_youtube.videos().list.return_value = mock_request

    inspection = await CopyrightGuardService.inspect_youtube_video(mock_youtube, "vid_clean_456")
    assert inspection["exists"] is True
    assert inspection["is_flagged"] is False
    assert inspection["reason"] is None


@pytest.mark.asyncio
async def test_handle_flagged_video_workflow(test_db_session):
    # Setup test data
    channel = Channel(
        name="Channel Test Guard",
        youtube_channel_id="UC_guard_123"
    )
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    schedule = Schedule(
        channel_id=channel.id,
        name="Guard Schedule",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id="f_guard",
        mode="SHUFFLE",
        publish_time="09:00",
        timezone="UTC",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    bad_video = Video(
        filename="bad_song.mp4",
        path="Channel_Test/bad_song.mp4",
        storage_file_id="bad_file_1",
        storage_provider="local",
        enabled=True
    )
    test_db_session.add(bad_video)
    await test_db_session.commit()
    await test_db_session.refresh(bad_video)

    occ = ScheduleOccurrence(
        schedule_id=schedule.id,
        channel_id=channel.id,
        video_id=bad_video.id,
        youtube_video_id="yt_bad_999",
        idempotency_key="guard_test_key_1",
        scheduled_publish_time=datetime.now(timezone.utc).replace(tzinfo=None),
        target_upload_time=datetime.now(timezone.utc).replace(tzinfo=None),
        status="COMPLETED"
    )
    test_db_session.add(occ)
    await test_db_session.commit()
    await test_db_session.refresh(occ)

    job = UploadJob(
        occurrence_id=occ.id,
        status="SUCCESS"
    )
    test_db_session.add(job)
    await test_db_session.commit()

    with patch("app.services.youtube.copyright_guard.YouTubeOAuthService.get_authenticated_service", new_callable=AsyncMock) as mock_auth, \
         patch.object(CopyrightGuardService, "delete_from_youtube", new_callable=AsyncMock) as mock_delete, \
         patch("app.services.scheduler.scheduler_engine.execute_schedule_job", new_callable=AsyncMock) as mock_replace_job:

        mock_delete.return_value = True
        mock_replace_job.return_value = "new_rep_occurrence_id"

        result = await CopyrightGuardService.handle_flagged_video(
            occurrence_id=occ.id,
            flag_reason="Rejection: copyright",
            auto_replace=True,
            db=test_db_session
        )

        assert result["success"] is True
        assert result["status"] == "COPYRIGHT_DELETED"
        assert result["replacement_occurrence_id"] == "new_rep_occurrence_id"

        # Verify DB state
        await test_db_session.refresh(occ)
        assert occ.status == "COPYRIGHT_DELETED"
        assert "copyright" in occ.error_message.lower()

        await test_db_session.refresh(bad_video)
        assert bad_video.enabled is False # Disabled in database!

        await test_db_session.refresh(job)
        assert job.status == "COPYRIGHT_DELETED"
