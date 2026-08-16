import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel


@pytest.mark.asyncio
async def test_get_timezones(client: AsyncClient):
    response = await client.get("/api/v1/channels/timezones")
    assert response.status_code == 200
    timezones = response.json()
    assert isinstance(timezones, list)
    assert len(timezones) > 0
    # Check that Asia/Kolkata and UTC are in the list
    tz_names = [tz["name"] for tz in timezones]
    assert "Asia/Kolkata" in tz_names
    assert "UTC" in tz_names


@pytest.mark.asyncio
async def test_create_channel_success(client: AsyncClient):
    payload = {
        "name": "Mahadev Bhakti Channel",
        "timezone": "Asia/Kolkata",
        "enabled": True,
        "default_title_template": "Mahadev Aarti | {date} | Har Har Mahadev",
        "default_description_template": "Welcome to our devotional channel. Today's video: {date}",
        "default_tags": ["mahadev", "shiv", "bhasma"],
        "default_category_id": "22",
        "default_privacy_status": "private"
    }
    response = await client.post("/api/v1/channels", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["timezone"] == "Asia/Kolkata"
    assert data["default_tags"] == payload["default_tags"]
    assert data["enabled"] is True
    assert "id" in data
    assert data["schedules_count"] == 0


@pytest.mark.asyncio
async def test_create_channel_invalid_timezone(client: AsyncClient):
    payload = {
        "name": "Invalid TZ Channel",
        "timezone": "Mars/Olympus_Mons",
        "enabled": True
    }
    response = await client.post("/api/v1/channels", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_and_get_channels(client: AsyncClient):
    # Create two channels
    await client.post("/api/v1/channels", json={
        "name": "Channel Alpha",
        "timezone": "UTC",
        "enabled": True
    })
    c2 = await client.post("/api/v1/channels", json={
        "name": "Channel Beta",
        "timezone": "America/New_York",
        "enabled": False
    })
    c2_id = c2.json()["id"]

    # List
    list_res = await client.get("/api/v1/channels")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 2
    names = [c["name"] for c in data["items"]]
    assert "Channel Alpha" in names
    assert "Channel Beta" in names

    # Get Single
    get_res = await client.get(f"/api/v1/channels/{c2_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Channel Beta"


@pytest.mark.asyncio
async def test_update_channel(client: AsyncClient):
    created = await client.post("/api/v1/channels", json={
        "name": "Initial Name",
        "timezone": "UTC"
    })
    channel_id = created.json()["id"]

    update_payload = {
        "name": "Updated Devotional Hub",
        "timezone": "Asia/Kolkata",
        "default_title_template": "Updated Title {date}"
    }
    update_res = await client.put(f"/api/v1/channels/{channel_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Updated Devotional Hub"
    assert updated_data["timezone"] == "Asia/Kolkata"
    assert updated_data["default_title_template"] == "Updated Title {date}"


@pytest.mark.asyncio
async def test_toggle_channel_status(client: AsyncClient):
    created = await client.post("/api/v1/channels", json={
        "name": "Toggle Channel",
        "timezone": "UTC",
        "enabled": True
    })
    channel_id = created.json()["id"]
    assert created.json()["enabled"] is True

    # Toggle off
    t1 = await client.patch(f"/api/v1/channels/{channel_id}/toggle")
    assert t1.status_code == 200
    assert t1.json()["enabled"] is False

    # Toggle on
    t2 = await client.patch(f"/api/v1/channels/{channel_id}/toggle")
    assert t2.status_code == 200
    assert t2.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_channel(client: AsyncClient):
    created = await client.post("/api/v1/channels", json={
        "name": "Channel To Delete",
        "timezone": "UTC"
    })
    channel_id = created.json()["id"]

    # Delete
    del_res = await client.delete(f"/api/v1/channels/{channel_id}")
    assert del_res.status_code == 204

    # Verify 404
    get_res = await client.get(f"/api/v1/channels/{channel_id}")
    assert get_res.status_code == 404
