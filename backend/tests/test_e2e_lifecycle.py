import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.channel import Channel
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.services.scanner.scanner_service import ScannerService
from app.services.metadata.metadata_engine import MetadataEngine
from app.services.scheduler.scheduler_engine import execute_schedule_job
from app.services.scheduler.modes.rotation import RotationModeResolver
from app.services.scheduler.modes.shuffle import ShuffleModeResolver
from app.services.worker.worker_pool import UploadWorkerPool
from app.services.worker.recovery import ReconciliationService
from app.services.youtube.quota_tracker import YouTubeQuotaTracker, DAILY_QUOTA_LIMIT


@pytest.mark.asyncio
async def test_full_e2e_platform_lifecycle(client: AsyncClient, test_db_session: AsyncSession):
    """
    End-to-End System Test covering all platform components:
    1. Channel Provisioning & Timezone
    2. Video Ingestion, Day-of-Month Parsing & Sidecar Metadata
    3. 5-Tier Metadata Template Resolution
    4. Rotation & Shuffle Queue Progressions
    5. YouTube Quota Management
    6. Concurrency-Controlled Worker Upload & Dry Run Execution
    7. Crash Recovery & Reconciliation
    8. Today's Timeline & Calendar Event Queries
    """

    # -------------------------------------------------------------------------
    # STEP 1: Channel Provisioning & Timezone Configuration
    # -------------------------------------------------------------------------
    ch_payload = {
        "name": "E2E Gaming Channel",
        "timezone": "America/New_York",
        "default_title_template": "{channel} - Daily Stream Episode {day}",
        "default_description_template": "Published on {date} for {channel}. Check out our website!",
        "default_tags": ["gaming", "automation", "e2e"],
        "default_category_id": "20",
        "default_privacy_status": "private"
    }
    ch_res = await client.post("/api/v1/channels", json=ch_payload)
    assert ch_res.status_code == 201
    channel_data = ch_res.json()
    channel_id = channel_data["id"]
    assert channel_data["name"] == "E2E Gaming Channel"
    assert channel_data["timezone"] == "America/New_York"

    # -------------------------------------------------------------------------
    # STEP 2: Video Asset Ingestion & Folder Setup
    # -------------------------------------------------------------------------
    folder = ContentFolder(
        channel_id=channel_id,
        storage_folder_id="e2e_folder_1",
        name="Season 1 Clips",
        path="/Season 1 Clips"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    # Ingest 3 Videos: 01_intro.mp4, 15_midgame.mp4, 28_finale.mp4
    video_1 = Video(
        channel_id=channel_id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_01_file",
        filename="01_intro.mp4",
        path="/Season 1 Clips/01_intro.mp4",
        day_of_month_index=1,
        custom_metadata={"title": "Introductory Special - Day 1", "tags": ["pilot", "intro"]},
        enabled=True
    )
    video_2 = Video(
        channel_id=channel_id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_15_file",
        filename="15_midgame.mp4",
        path="/Season 1 Clips/15_midgame.mp4",
        day_of_month_index=15,
        enabled=True
    )
    video_3 = Video(
        channel_id=channel_id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="vid_28_file",
        filename="28_finale.mp4",
        path="/Season 1 Clips/28_finale.mp4",
        day_of_month_index=28,
        enabled=True
    )
    test_db_session.add_all([video_1, video_2, video_3])
    await test_db_session.commit()
    await test_db_session.refresh(video_1)
    await test_db_session.refresh(video_2)
    await test_db_session.refresh(video_3)

    # -------------------------------------------------------------------------
    # STEP 3: 5-Tier Metadata Hierarchy Resolution
    # -------------------------------------------------------------------------
    channel_obj = await test_db_session.get(Channel, channel_id)
    target_dt = datetime(2026, 8, 1, 15, 0, 0, tzinfo=timezone.utc)

    meta = MetadataEngine.resolve_effective_metadata(
        video=video_1,
        channel=channel_obj,
        folder=folder,
        target_datetime=target_dt
    )
    # Sidecar overrides channel default template
    assert meta.title == "Introductory Special - Day 1"
    assert "pilot" in meta.tags
    assert meta.category_id == "20"

    # Video 2 uses channel default template with {channel} and {day} substituted
    meta_2 = MetadataEngine.resolve_effective_metadata(
        video=video_2,
        channel=channel_obj,
        folder=folder,
        target_datetime=target_dt
    )
    assert meta_2.title == "E2E Gaming Channel - Daily Stream Episode 01"

    # -------------------------------------------------------------------------
    # STEP 4: Multi-Mode Schedules (Rotation & Shuffle Progression)
    # -------------------------------------------------------------------------
    # 4a. Rotation Schedule
    rot_sched = Schedule(
        channel_id=channel_id,
        name="Rotation Daily Stream",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="ROTATION",
        publish_time="19:00",
        timezone="America/New_York",
        upload_lead_minutes=180,
        use_youtube_scheduled_publish=True,
        dry_run=True,
        enabled=True
    )
    test_db_session.add(rot_sched)
    await test_db_session.commit()
    await test_db_session.refresh(rot_sched)

    # Execute Rotation Occurrence 1 (Index 0 -> video 1)
    occ1_id = await execute_schedule_job(rot_sched.id, db=test_db_session, trigger_upload=True)
    occ1 = await test_db_session.get(ScheduleOccurrence, occ1_id)
    assert occ1.video_id == video_1.id
    assert occ1.status == "COMPLETED"

    # Idempotency check: Executing again on the same day returns existing occurrence
    occ1_again_id = await execute_schedule_job(rot_sched.id, db=test_db_session, trigger_upload=True)
    assert occ1_again_id == occ1_id

    # Rotation Resolver Day 2 progression -> video 2
    rot_res_2 = await RotationModeResolver.resolve_video_for_date(
        schedule=rot_sched,
        target_datetime=datetime(2026, 8, 16, 19, 0, tzinfo=timezone.utc),
        db=test_db_session
    )
    assert rot_res_2.video.id == video_2.id

    # 4b. Shuffle Schedule
    shuf_sched = Schedule(
        channel_id=channel_id,
        name="Shuffle Highlights",
        schedule_type="WEEKLY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="SHUFFLE",
        publish_time="12:00",
        timezone="America/New_York",
        dry_run=True,
        enabled=True
    )
    test_db_session.add(shuf_sched)
    await test_db_session.commit()
    await test_db_session.refresh(shuf_sched)

    shuf_res_1 = await ShuffleModeResolver.resolve_video_for_date(
        schedule=shuf_sched,
        target_datetime=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
        db=test_db_session
    )
    assert shuf_res_1.video.id in [video_1.id, video_2.id, video_3.id]

    # -------------------------------------------------------------------------
    # STEP 5: YouTube Quota Tracking
    # -------------------------------------------------------------------------
    can_upload, used_units, quota_msg = await YouTubeQuotaTracker.can_upload_video(channel_id, test_db_session)
    assert can_upload is True
    assert used_units >= 0
    assert "Quota OK" in quota_msg

    # -------------------------------------------------------------------------
    # STEP 6: Worker Pool Concurrency & Rate Limiter Verification
    # -------------------------------------------------------------------------
    pool_status = UploadWorkerPool.get_instance().get_status()
    assert pool_status["max_concurrent_uploads"] >= 1
    assert pool_status["per_channel_max_concurrent"] == 1
    assert pool_status["is_paused"] is False

    # -------------------------------------------------------------------------
    # STEP 7: Crash Recovery & Stale File Reconciliation
    # -------------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_f:
        orphan_path = tmp_f.name

    stuck_occ = ScheduleOccurrence(
        channel_id=channel_id,
        video_id=video_3.id,
        idempotency_key="stuck_occ_e2e",
        scheduled_publish_time=datetime.now(timezone.utc),
        target_upload_time=datetime.now(timezone.utc),
        status="DOWNLOADING"
    )
    test_db_session.add(stuck_occ)
    await test_db_session.commit()
    await test_db_session.refresh(stuck_occ)

    stuck_job = UploadJob(
        occurrence_id=stuck_occ.id,
        status="DOWNLOADING",
        retry_count=1,
        max_retries=5,
        temp_file_path=orphan_path
    )
    test_db_session.add(stuck_job)
    await test_db_session.commit()

    assert os.path.exists(orphan_path)
    recon_res = await ReconciliationService.reconcile_orphaned_jobs(db=test_db_session)
    assert recon_res["reconciled_to_queue"] >= 1
    assert not os.path.exists(orphan_path)

    # -------------------------------------------------------------------------
    # STEP 8: API Endpoints (Timeline & Calendar Simulation)
    # -------------------------------------------------------------------------
    timeline_res = await client.get("/api/v1/schedules/timeline/today")
    assert timeline_res.status_code == 200

    sim_res = await client.post(f"/api/v1/schedules/{rot_sched.id}/simulate-calendar?year=2026&month=8")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["month"] == 8
    assert len(sim_data["days"]) == 31
