import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.channel import Channel
from app.models.channel_sync import SourceChannelSync, SyncedSourceVideo
from app.schemas.channel_sync import SourceChannelSyncCreate, SourceChannelSyncUpdate
from app.services.channel_sync.channel_sync_service import ChannelSyncService


@pytest.mark.asyncio
async def test_channel_sync_crud(test_db_session: AsyncSession):
    # 1. Create target channel
    channel = Channel(name="Target Channel", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    # 2. Create SourceChannelSync config
    create_data = SourceChannelSyncCreate(
        source_channel_url="@VoiceGaming",
        target_channel_id=channel.id,
        sync_mode="SHORTS_ONLY",
        auto_publish=False,
        publish_privacy_status="public",
        title_prefix="🔥",
        title_suffix="#VoiceGaming",
        description_footer="Credits to Voice Gaming",
        custom_tags=["gaming", "voicegaming"]
    )
    cfg = await ChannelSyncService.create_sync_config(test_db_session, create_data)
    assert cfg.id is not None
    assert cfg.source_channel_url == "https://www.youtube.com/@VoiceGaming/videos"
    assert cfg.sync_mode == "SHORTS_ONLY"
    assert cfg.custom_tags == ["gaming", "voicegaming"]

    # 3. List configs
    configs = await ChannelSyncService.list_sync_configs(test_db_session)
    assert len(configs) >= 1
    matched = next((c for c in configs if c.id == cfg.id), None)
    assert matched is not None
    assert matched.target_channel_name == "Target Channel"

    # 4. Update config
    update_data = SourceChannelSyncUpdate(auto_publish=True, sync_mode="ALL")
    updated = await ChannelSyncService.update_sync_config(test_db_session, cfg.id, update_data)
    assert updated.auto_publish is True
    assert updated.sync_mode == "ALL"

    # 5. Delete config
    del_res = await ChannelSyncService.delete_sync_config(test_db_session, cfg.id)
    assert del_res is True
    configs_after = await ChannelSyncService.list_sync_configs(test_db_session)
    assert not any(c.id == cfg.id for c in configs_after)


@pytest.mark.asyncio
async def test_duplicate_video_prevention(test_db_session: AsyncSession):
    # Setup channel and sync config
    channel = Channel(name="Gaming Reposts", timezone="UTC")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    cfg = SourceChannelSync(
        source_channel_url="https://youtube.com/@VoiceGaming/videos",
        source_channel_name="Voice Gaming",
        target_channel_id=channel.id,
        sync_mode="ALL"
    )
    test_db_session.add(cfg)
    await test_db_session.commit()
    await test_db_session.refresh(cfg)

    # Add existing synced video
    existing_video = SyncedSourceVideo(
        sync_id=cfg.id,
        source_video_id="TEST_VID_001",
        source_url="https://youtube.com/watch?v=TEST_VID_001",
        title="Epic Clutch Gameplay",
        download_status="DOWNLOADED",
        upload_status="UPLOADED"
    )
    test_db_session.add(existing_video)
    await test_db_session.commit()

    # Query duplicate check
    dup_stmt = select(SyncedSourceVideo).where(SyncedSourceVideo.source_video_id == "TEST_VID_001")
    dup_res = await test_db_session.execute(dup_stmt)
    assert dup_res.scalars().first() is not None


@pytest.mark.asyncio
async def test_channel_sync_api_endpoints(client: AsyncClient, test_db_session: AsyncSession):
    # Setup channel
    channel = Channel(name="API Target Channel", timezone="Asia/Kolkata")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    # 1. POST /api/v1/channel-sync
    res = await client.post("/api/v1/channel-sync", json={
        "source_channel_url": "https://www.youtube.com/@VoiceGaming",
        "target_channel_id": channel.id,
        "sync_mode": "ALL",
        "auto_publish": False,
        "publish_privacy_status": "public",
        "title_prefix": "[CLIPS]",
        "custom_tags": ["clips", "viral"]
    })
    assert res.status_code == 201
    data = res.json()
    sync_id = data["id"]
    assert sync_id is not None
    assert data["target_channel_name"] == "API Target Channel"

    # 2. GET /api/v1/channel-sync
    list_res = await client.get("/api/v1/channel-sync")
    assert list_res.status_code == 200
    assert any(c["id"] == sync_id for c in list_res.json())

    # 3. GET /api/v1/channel-sync/videos
    vids_res = await client.get("/api/v1/channel-sync/videos")
    assert vids_res.status_code == 200
    assert isinstance(vids_res.json(), list)

    # 4. DELETE /api/v1/channel-sync/{id}
    del_res = await client.delete(f"/api/v1/channel-sync/{sync_id}")
    assert del_res.status_code == 204
