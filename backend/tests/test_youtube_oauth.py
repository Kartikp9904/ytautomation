import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.channel import Channel
from app.models.oauth import OAuthCredential
from app.services.youtube.quota_tracker import YouTubeQuotaTracker, DAILY_QUOTA_LIMIT, QUOTA_VIDEO_UPLOAD
from app.services.youtube.youtube_oauth import YouTubeOAuthService
from app.core.security import encrypt_secret


@pytest.mark.asyncio
async def test_youtube_quota_tracker(test_db_session: AsyncSession):
    channel_id = "test_chan_quota"

    # Initially 0 quota used
    used = await YouTubeQuotaTracker.get_used_quota(channel_id, test_db_session)
    assert used == 0

    # Can upload video
    can_up, used_units, msg = await YouTubeQuotaTracker.can_upload_video(channel_id, test_db_session)
    assert can_up is True
    assert used_units == 0

    # Record upload of 1600 units
    new_val = await YouTubeQuotaTracker.record_quota_usage(channel_id, QUOTA_VIDEO_UPLOAD, test_db_session)
    assert new_val == 1600

    # Verify updated quota
    used_after = await YouTubeQuotaTracker.get_used_quota(channel_id, test_db_session)
    assert used_after == 1600

    # Max out quota
    await YouTubeQuotaTracker.record_quota_usage(channel_id, 9000, test_db_session)
    can_up_after, _, block_msg = await YouTubeQuotaTracker.can_upload_video(channel_id, test_db_session)
    assert can_up_after is False
    assert "exceeded" in block_msg.lower()


@pytest.mark.asyncio
async def test_youtube_auth_url_and_status_endpoints(client: AsyncClient, test_db_session: AsyncSession):
    channel = Channel(name="Tech Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    # 1. Get Auth URL
    res_url = await client.get(f"/api/v1/youtube/auth-url?channel_id={channel.id}")
    assert res_url.status_code == 200
    data_url = res_url.json()
    assert "auth_url" in data_url
    assert channel.id in data_url["auth_url"]
    assert "youtube.upload" in data_url["auth_url"]

    # 2. Check initial status (disconnected)
    res_status = await client.get(f"/api/v1/youtube/{channel.id}/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["is_connected"] is False
    assert data_status["daily_quota_used"] == 0

    # 3. Connect mock OAuth credentials
    cred = OAuthCredential(
        service_type="youtube_channel",
        channel_id=channel.id,
        account_email="creator@youtube.com",
        encrypted_refresh_token=encrypt_secret("dummy_refresh_token"),
        encrypted_access_token=encrypt_secret("dummy_access_token"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
        is_valid=True
    )
    channel.youtube_channel_id = "UC_TEST_123456789"
    test_db_session.add(cred)
    await test_db_session.commit()

    # 4. Check status again (now connected)
    res_status_conn = await client.get(f"/api/v1/youtube/{channel.id}/status")
    assert res_status_conn.status_code == 200
    data_conn = res_status_conn.json()
    assert data_conn["is_connected"] is True
    assert data_conn["youtube_channel_id"] == "UC_TEST_123456789"
    assert data_conn["account_email"] == "creator@youtube.com"

    # 5. Disconnect channel
    res_disc = await client.post(f"/api/v1/youtube/{channel.id}/disconnect")
    assert res_disc.status_code == 200

    # 6. Verify disconnected
    res_status_after = await client.get(f"/api/v1/youtube/{channel.id}/status")
    assert res_status_after.status_code == 200
    assert res_status_after.json()["is_connected"] is False
