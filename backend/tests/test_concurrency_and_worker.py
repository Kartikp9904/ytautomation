import asyncio
import time
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.video import Video
from app.models.occurrence import ScheduleOccurrence
from app.services.worker.worker_pool import UploadWorkerPool


@pytest.mark.asyncio
async def test_worker_pool_queue_status_and_pause_resume(client: AsyncClient):
    # 1. Get queue status
    res = await client.get("/api/v1/uploads/queue/status")
    assert res.status_code == 200
    data = res.json()
    assert "max_concurrent_uploads" in data
    assert "per_channel_max_concurrent" in data
    assert "active_uploads_count" in data
    assert data["is_paused"] is False

    # 2. Pause queue
    res_pause = await client.post("/api/v1/uploads/queue/pause")
    assert res_pause.status_code == 200
    assert UploadWorkerPool.get_instance()._is_paused is True

    # 3. Resume queue
    res_resume = await client.post("/api/v1/uploads/queue/resume")
    assert res_resume.status_code == 200
    assert UploadWorkerPool.get_instance()._is_paused is False


@pytest.mark.asyncio
async def test_per_channel_concurrency_serialization(test_db_session: AsyncSession):
    """
    Ensures multiple uploads for the same channel run sequentially, never concurrently.
    """
    channel = Channel(name="Concurrent Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video1 = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="con_vid_1",
        filename="con1.mp4",
        path="con1.mp4",
        enabled=True
    )
    video2 = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="con_vid_2",
        filename="con2.mp4",
        path="con2.mp4",
        enabled=True
    )
    test_db_session.add_all([video1, video2])
    await test_db_session.commit()
    await test_db_session.refresh(video1)
    await test_db_session.refresh(video2)

    occ1 = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video1.id,
        idempotency_key="occ_con_1",
        scheduled_publish_time=datetime.now(),
        target_upload_time=datetime.now(),
        dry_run=True,
        status="QUEUED"
    )
    occ2 = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video2.id,
        idempotency_key="occ_con_2",
        scheduled_publish_time=datetime.now(),
        target_upload_time=datetime.now(),
        dry_run=True,
        status="QUEUED"
    )
    test_db_session.add_all([occ1, occ2])
    await test_db_session.commit()
    await test_db_session.refresh(occ1)
    await test_db_session.refresh(occ2)

    active_counts = []

    async def mock_upload(occurrence_id, **kwargs):
        pool = UploadWorkerPool.get_instance()
        active_counts.append(len(pool._running_jobs))
        await asyncio.sleep(0.05)
        return {"status": "SUCCESS"}

    with patch("app.services.worker.worker_pool.YouTubeUploaderService.run_upload_job", side_effect=mock_upload):
        pool = UploadWorkerPool.get_instance()
        # Set small cooldown for test speed
        pool.cooldown_seconds = 0.01

        # Submit both concurrently
        res1, res2 = await asyncio.gather(
            pool.submit_upload(occ1.id, dry_run=True),
            pool.submit_upload(occ2.id, dry_run=True)
        )

        assert res1["status"] == "SUCCESS"
        assert res2["status"] == "SUCCESS"
        # Due to per-channel lock, active job count for this channel never exceeded 1
        assert max(active_counts) == 1
