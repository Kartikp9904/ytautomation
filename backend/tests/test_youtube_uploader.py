import os
import tempfile
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.video import Video
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.models.oauth import OAuthCredential
from app.services.youtube.uploader import YouTubeUploaderService
from app.core.security import encrypt_secret


@pytest.mark.asyncio
async def test_manual_upload_endpoints(client: AsyncClient, test_db_session: AsyncSession):
    # Setup channel and video
    channel = Channel(name="Manual Upload Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="manual_vid_1",
        filename="promo.mp4",
        path="promo.mp4",
        enabled=True
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    # 1. Trigger manual upload
    res = await client.post(
        "/api/v1/uploads/manual",
        json={
            "video_id": video.id,
            "channel_id": channel.id,
            "title": "Special Launch Video",
            "privacy_status": "unlisted"
        }
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert "occurrence_id" in data
    assert data["status"] == "QUEUED"

    job_id = data["job_id"]

    # 2. Inspect job progress
    res_job = await client.get(f"/api/v1/uploads/{job_id}")
    assert res_job.status_code == 200
    job_data = res_job.json()
    assert job_data["id"] == job_id
    assert job_data["status"] == "QUEUED"

    # 3. List all jobs
    res_list = await client.get("/api/v1/uploads")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1


@pytest.mark.asyncio
async def test_uploader_service_pipeline_mocked(test_db_session: AsyncSession):
    # Ensure local storage base dir exists
    os.makedirs(settings.LOCAL_STORAGE_BASE_PATH, exist_ok=True)
    test_file_name = "test_pipe_video.mp4"
    dummy_video_path = os.path.join(settings.LOCAL_STORAGE_BASE_PATH, test_file_name)
    with open(dummy_video_path, "wb") as f:
        f.write(b"dummy video content 1234567890")

    try:
        channel = Channel(name="Pipeline Channel", timezone="UTC", youtube_channel_id="UC_PIPE")
        test_db_session.add(channel)
        await test_db_session.commit()
        await test_db_session.refresh(channel)

        cred = OAuthCredential(
            service_type="youtube_channel",
            channel_id=channel.id,
            account_email="pipe@youtube.com",
            encrypted_refresh_token=encrypt_secret("ref_tok"),
            encrypted_access_token=encrypt_secret("acc_tok"),
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
            is_valid=True
        )
        test_db_session.add(cred)

        video = Video(
            channel_id=channel.id,
            storage_provider="local",
            storage_file_id=test_file_name,
            filename=test_file_name,
            path=test_file_name,
            enabled=True
        )
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)

        occurrence = ScheduleOccurrence(
            channel_id=channel.id,
            video_id=video.id,
            idempotency_key="pipe_test_occ_1",
            scheduled_publish_time=datetime.now(),
            target_upload_time=datetime.now(),
            status="QUEUED"
        )
        test_db_session.add(occurrence)
        await test_db_session.commit()
        await test_db_session.refresh(occurrence)

        # Mock YouTube client
        mock_youtube = MagicMock()
        mock_insert_request = MagicMock()
        mock_insert_request.next_chunk.return_value = (None, {"id": "YT_VID_123"})
        mock_youtube.videos().insert.return_value = mock_insert_request

        with patch("app.services.youtube.uploader.YouTubeOAuthService.get_authenticated_service", return_value=mock_youtube):
            result = await YouTubeUploaderService.run_upload_job(
                occurrence_id=occurrence.id,
                title_override="Mocked Upload Title",
                db=test_db_session
            )

            assert result["status"] == "SUCCESS"
            assert result["youtube_video_id"] == "YT_VID_123"
            assert "https://youtu.be/YT_VID_123" in result["youtube_url"]

    finally:
        if os.path.exists(dummy_video_path):
            os.remove(dummy_video_path)
