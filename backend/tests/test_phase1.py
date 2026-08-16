import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import encrypt_token, decrypt_token, create_access_token, decode_access_token
from app.models.channel import Channel
from app.models.schedule import Schedule
from app.models.occurrence import ScheduleOccurrence
from app.core.config import settings
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "HEALTHY"
    assert "storage" in data
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_auth_login_and_token(client: AsyncClient):
    # Test invalid login
    bad_res = await client.post("/api/v1/auth/login", json={"username": "wrong", "password": "bad"})
    assert bad_res.status_code == 401

    # Test valid login
    res = await client.post("/api/v1/auth/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token decoding
    payload = decode_access_token(data["access_token"])
    assert payload is not None
    assert payload["sub"] == settings.ADMIN_USERNAME


def test_token_encryption_roundtrip():
    secret_refresh_token = "1//04test_refresh_token_very_long_secret_1234567890"
    encrypted = encrypt_token(secret_refresh_token)
    assert encrypted != secret_refresh_token
    decrypted = decrypt_token(encrypted)
    assert decrypted == secret_refresh_token


@pytest.mark.asyncio
async def test_channel_and_schedule_models(test_db_session: AsyncSession):
    # Create Channel
    channel = Channel(
        name="Devotional Channel 1",
        youtube_channel_id="UC1234567890",
        timezone="Asia/Kolkata",
        enabled=True,
        default_title_template="Mahadev | {date}",
        default_category_id="22"
    )
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    assert channel.id is not None
    assert channel.name == "Devotional Channel 1"

    # Create Schedule
    schedule = Schedule(
        channel_id=channel.id,
        name="Morning Aarti",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id="folder_123",
        mode="DAY_OF_MONTH",
        publish_time="09:00",
        timezone="Asia/Kolkata",
        upload_lead_minutes=120
    )
    test_db_session.add(schedule)
    await test_db_session.commit()
    await test_db_session.refresh(schedule)

    assert schedule.id is not None
    assert schedule.channel_id == channel.id

    # Create Occurrence with Idempotency Key
    now_utc = datetime.now(timezone.utc)
    idempotency_key = f"{channel.id}:{schedule.id}:{now_utc.isoformat()}:vid_1"
    occurrence = ScheduleOccurrence(
        schedule_id=schedule.id,
        channel_id=channel.id,
        idempotency_key=idempotency_key,
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="PENDING"
    )
    test_db_session.add(occurrence)
    await test_db_session.commit()
    await test_db_session.refresh(occurrence)

    assert occurrence.id is not None
    assert occurrence.status == "PENDING"
