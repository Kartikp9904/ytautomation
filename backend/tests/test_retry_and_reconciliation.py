import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.channel import Channel
from app.models.video import Video
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.services.worker.recovery import ErrorClassifier, RetryEngine, ReconciliationService
from app.services.youtube.uploader import YouTubeUploaderService


def test_error_classification():
    # Transient network/server errors
    err1, is_ret1 = ErrorClassifier.classify_error("504 Gateway Timeout")
    assert err1 == "TRANSIENT"
    assert is_ret1 is True

    err2, is_ret2 = ErrorClassifier.classify_error("Connection reset by peer during chunk upload")
    assert err2 == "TRANSIENT"
    assert is_ret2 is True

    err3, is_ret3 = ErrorClassifier.classify_error("HTTP 429 Rate limit exceeded")
    assert err3 == "TRANSIENT"
    assert is_ret3 is True

    # Permanent fatal errors
    err4, is_ret4 = ErrorClassifier.classify_error("The daily quotaExceeded limit was hit.")
    assert err4 == "PERMANENT"
    assert is_ret4 is False

    err5, is_ret5 = ErrorClassifier.classify_error("OAuth error: invalid_grant - token has been revoked")
    assert err5 == "PERMANENT"
    assert is_ret5 is False


def test_exponential_backoff_calculation():
    delay_0 = RetryEngine.calculate_backoff(0)
    assert 10 <= delay_0 <= 20

    delay_1 = RetryEngine.calculate_backoff(1)
    assert 20 <= delay_1 <= 30

    delay_2 = RetryEngine.calculate_backoff(2)
    assert 40 <= delay_2 <= 50

    delay_10 = RetryEngine.calculate_backoff(10)
    assert delay_10 <= RetryEngine.MAX_DELAY_SECONDS


@pytest.mark.asyncio
async def test_reconciliation_service(test_db_session: AsyncSession):
    # Setup channel and video
    channel = Channel(name="Reconcile Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="rec_video_1",
        filename="rec_video.mp4",
        path="rec_video.mp4"
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    now_utc = datetime.now(timezone.utc)

    # 1. Stuck Job under max retries
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        temp_file_1 = tmp.name

    occ1 = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video.id,
        idempotency_key="rec_occ_1",
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="DOWNLOADING"
    )
    test_db_session.add(occ1)
    await test_db_session.commit()
    await test_db_session.refresh(occ1)

    job1 = UploadJob(
        occurrence_id=occ1.id,
        status="DOWNLOADING",
        retry_count=1,
        max_retries=5,
        temp_file_path=temp_file_1
    )
    test_db_session.add(job1)

    # 2. Stuck Job exceeding max retries
    occ2 = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video.id,
        idempotency_key="rec_occ_2",
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="IN_PROGRESS"
    )
    test_db_session.add(occ2)
    await test_db_session.commit()
    await test_db_session.refresh(occ2)

    job2 = UploadJob(
        occurrence_id=occ2.id,
        status="IN_PROGRESS",
        retry_count=5,
        max_retries=5
    )
    test_db_session.add(job2)
    await test_db_session.commit()

    assert os.path.exists(temp_file_1)

    # Run Reconciliation
    summary = await ReconciliationService.reconcile_orphaned_jobs(db=test_db_session)

    assert summary["total_stuck_found"] == 2
    assert summary["reconciled_to_queue"] == 1
    assert summary["permanently_failed"] == 1
    assert summary["cleaned_temp_files"] == 1
    assert not os.path.exists(temp_file_1)

    # Check updated records
    await test_db_session.refresh(job1)
    assert job1.status == "QUEUED"
    assert job1.retry_count == 2
    assert job1.error_type == "RECOVERED_FROM_CRASH"

    await test_db_session.refresh(job2)
    assert job2.status == "FAILED"
    assert job2.error_type == "MAX_RETRIES_EXCEEDED"


@pytest.mark.asyncio
async def test_reconciliation_and_retry_api(client: AsyncClient, test_db_session: AsyncSession):
    # Setup channel and video
    channel = Channel(name="API Retry Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="api_retry_video",
        filename="api_retry_video.mp4",
        path="api_retry_video.mp4"
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    now_utc = datetime.now(timezone.utc)

    occ = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video.id,
        idempotency_key="api_retry_occ",
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="FAILED",
        error_message="Network connection lost"
    )
    test_db_session.add(occ)
    await test_db_session.commit()
    await test_db_session.refresh(occ)

    job = UploadJob(
        occurrence_id=occ.id,
        status="FAILED",
        retry_count=1,
        max_retries=5,
        error_message="Network connection lost"
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    # 1. Test Reconcile Endpoint
    rec_res = await client.post("/api/v1/uploads/reconcile")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "total_stuck_found" in rec_data

    # 2. Test Manual Retry Endpoint
    retry_res = await client.post(f"/api/v1/uploads/{job.id}/retry")
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert retry_data["status"] == "QUEUED"
    assert retry_data["job_id"] == job.id


@pytest.mark.asyncio
async def test_idempotency_duplicate_protection(test_db_session: AsyncSession):
    channel = Channel(name="Idempotency Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    video = Video(
        channel_id=channel.id,
        storage_provider="local",
        storage_file_id="idem_video",
        filename="idem_video.mp4",
        path="idem_video.mp4"
    )
    test_db_session.add(video)
    await test_db_session.commit()
    await test_db_session.refresh(video)

    now_utc = datetime.now(timezone.utc)

    occ = ScheduleOccurrence(
        channel_id=channel.id,
        video_id=video.id,
        idempotency_key="idem_occ_key_1",
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="COMPLETED",
        youtube_video_id="ALREADY_UPLOADED_123"
    )
    test_db_session.add(occ)
    await test_db_session.commit()
    await test_db_session.refresh(occ)

    # Running upload job on already completed occurrence must return ALREADY_COMPLETED and not duplicate
    result = await YouTubeUploaderService.run_upload_job(
        occurrence_id=occ.id,
        db=test_db_session
    )

    assert result["status"] == "ALREADY_COMPLETED"
    assert result["youtube_video_id"] == "ALREADY_UPLOADED_123"
