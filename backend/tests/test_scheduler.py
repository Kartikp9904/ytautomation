import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.services.scheduler.scheduler_engine import (
    SchedulerEngine,
    get_scheduler,
    execute_schedule_job
)


@pytest.mark.asyncio
async def test_scheduler_engine_job_registration(test_db_session: AsyncSession):
    # Initialize scheduler
    sched = get_scheduler()
    if not sched.running:
        sched.start()

    channel = Channel(name="Bhakti Channel", timezone="Asia/Kolkata")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_sched_test",
        name="Aarti Daily",
        path="Bhakti/Aarti"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    schedule = Schedule(
        channel_id=channel.id,
        name="Daily Morning Aarti",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id=folder.id,
        mode="DAY_OF_MONTH",
        publish_time="09:30",
        timezone="Asia/Kolkata",
        enabled=True
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    # 1. Register in APScheduler
    SchedulerEngine.register_schedule_job(schedule)
    job_id = SchedulerEngine.get_job_id(schedule.id)
    job = sched.get_job(job_id)
    assert job is not None
    assert "Daily Morning Aarti" in job.name

    # 2. Check next run time exists
    next_run = SchedulerEngine.get_next_run_time(schedule.id)
    assert next_run is not None

    # 3. Test execution and idempotency
    target_dt = datetime(2026, 8, 15, 9, 30, 0)
    occ_id_1 = await execute_schedule_job(
        schedule.id,
        db=test_db_session,
        manual_target_date=target_dt
    )
    assert occ_id_1 is not None

    # Re-executing on same date should return the exact same occurrence without creating duplicate
    occ_id_2 = await execute_schedule_job(
        schedule.id,
        db=test_db_session,
        manual_target_date=target_dt
    )
    assert occ_id_2 == occ_id_1

    # 4. Unregister
    SchedulerEngine.unregister_schedule_job(schedule.id)
    assert sched.get_job(job_id) is None


@pytest.mark.asyncio
async def test_schedules_api_endpoints(client: AsyncClient, test_db_session: AsyncSession):
    # 1. Create Channel
    channel = Channel(name="Spiritual World", timezone="America/New_York")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_spiritual",
        name="Daily Chants",
        path="Spiritual/Daily"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    # 2. POST /api/v1/schedules
    payload = {
        "channel_id": channel.id,
        "name": "Morning Chants NY",
        "schedule_type": "DAILY",
        "source_type": "FOLDER",
        "source_id": folder.id,
        "mode": "DAY_OF_MONTH",
        "publish_time": "08:00",
        "timezone": "America/New_York",
        "title_template": "Morning Chant {date} | {channel}",
        "tags": ["chants", "morning"],
        "privacy_status": "public",
        "enabled": True
    }
    create_res = await client.post("/api/v1/schedules", json=payload)
    assert create_res.status_code == 201
    sched_data = create_res.json()
    schedule_id = sched_data["id"]
    assert sched_data["name"] == "Morning Chants NY"
    assert sched_data["channel_name"] == "Spiritual World"
    assert sched_data["source_name"] == "Daily Chants"
    assert sched_data["next_run_time"] is not None

    # 3. GET /api/v1/schedules
    list_res = await client.get("/api/v1/schedules")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. POST /api/v1/schedules/{id}/trigger-now (Run Now)
    trigger_res = await client.post(f"/api/v1/schedules/{schedule_id}/trigger-now")
    assert trigger_res.status_code == 200
    assert trigger_res.json()["status"] == "QUEUED"

    # 5. GET /api/v1/schedules/{id}/occurrences
    occ_res = await client.get(f"/api/v1/schedules/{schedule_id}/occurrences")
    assert occ_res.status_code == 200
    occurrences = occ_res.json()
    assert len(occurrences) >= 1
    assert occurrences[0]["schedule_id"] == schedule_id

    # 6. PATCH /api/v1/schedules/{id}/toggle
    toggle_res = await client.patch(f"/api/v1/schedules/{schedule_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    # 7. DELETE /api/v1/schedules/{id}
    del_res = await client.delete(f"/api/v1/schedules/{schedule_id}")
    assert del_res.status_code == 204
