import pytest
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.video import Video
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.services.metadata.metadata_engine import MetadataEngine


def test_substitute_variables():
    dt = datetime(2026, 8, 15, 9, 0, 0)
    template = "Darshan {day} | {month} {year} | {channel} | Video #{filename}"
    res = MetadataEngine.substitute_variables(
        template=template,
        channel_name="Mahadev Bhakti",
        video_filename="15.mp4",
        target_datetime=dt
    )
    assert res == "Darshan 15 | August 2026 | Mahadev Bhakti | Video #15"


def test_metadata_priority_resolution():
    # 1. Channel level only (Priority 4)
    channel = Channel(
        name="Channel A",
        default_title_template="Channel Title {date}",
        default_tags=["ch_tag"],
        default_category_id="22",
        default_privacy_status="public",
        default_thumbnail_storage_id="thumb_channel"
    )
    video = Video(
        filename="15.mp4",
        path="Channel_1/15.mp4",
        storage_file_id="vid_15",
        storage_provider="local"
    )

    res1 = MetadataEngine.resolve_effective_metadata(video=video, channel=channel)
    assert "Channel Title" in res1.title
    assert res1.tags == ["ch_tag"]
    assert res1.thumbnail_storage_id == "thumb_channel"
    assert res1.source_hierarchy["title"] == "channel_default"

    # 2. Add Folder level (Priority 3: overrides Channel)
    folder = ContentFolder(
        name="Mahadev",
        storage_folder_id="f_mahadev",
        path="Channel_1/Mahadev",
        default_title_template="Folder Aarti {filename} | {channel}",
        default_tags=["folder_tag"],
        default_thumbnail_storage_id="thumb_folder"
    )
    res2 = MetadataEngine.resolve_effective_metadata(
        video=video, channel=channel, folder=folder
    )
    assert res2.title == "Folder Aarti 15 | Channel A"
    assert res2.tags == ["folder_tag"]
    assert res2.thumbnail_storage_id == "thumb_folder"
    assert res2.source_hierarchy["title"] == "folder_default"

    # 3. Add Schedule level (Priority 2: overrides Folder and Channel)
    schedule = Schedule(
        channel_id="ch_1",
        name="Daily Morning",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id="f_mahadev",
        mode="DAY_OF_MONTH",
        publish_time="09:00",
        timezone="UTC",
        title_template="Schedule Aarti {date}",
        tags=["sched_tag"],
        privacy_status="private"
    )
    res3 = MetadataEngine.resolve_effective_metadata(
        video=video, channel=channel, folder=folder, schedule=schedule
    )
    assert "Schedule Aarti" in res3.title
    assert res3.tags == ["sched_tag"]
    assert res3.privacy_status == "private"
    assert res3.source_hierarchy["title"] == "schedule_template"

    # 4. Add Video sidecar metadata (Priority 1: Highest Priority: overrides Folder, Schedule, Channel)
    video.custom_metadata = {
        "title": "Exact Special Sidecar Title",
        "tags": ["exact_tag"],
        "category": "10"
    }
    video.custom_thumbnail_file_id = "thumb_exact_15"

    res4 = MetadataEngine.resolve_effective_metadata(
        video=video, channel=channel, folder=folder, schedule=schedule
    )
    assert res4.title == "Exact Special Sidecar Title"
    assert res4.tags == ["exact_tag"]
    assert res4.category_id == "10"
    assert res4.thumbnail_storage_id == "thumb_exact_15"
    assert res4.source_hierarchy["title"] == "video_sidecar"
    assert res4.source_hierarchy["thumbnail"] == "video_sidecar"


@pytest.mark.asyncio
async def test_videos_and_folders_api(client: AsyncClient, test_db_session: AsyncSession):
    # 1. Setup Channel, Folder, and Videos in DB
    channel = Channel(name="Devotional Channel", timezone="Asia/Kolkata")
    test_db_session.add(channel)
    await test_db_session.commit()
    await test_db_session.refresh(channel)

    folder = ContentFolder(
        channel_id=channel.id,
        storage_folder_id="f_test_1",
        name="Hanuman",
        path="Devotional/Hanuman"
    )
    test_db_session.add(folder)
    await test_db_session.commit()
    await test_db_session.refresh(folder)

    v1 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="sf_15",
        filename="15.mp4",
        path="Devotional/Hanuman/15.mp4",
        day_of_month_index=15,
        custom_metadata={"title": "Hanuman Chalisa Day 15", "tags": ["hanuman", "chalisa"]}
    )
    v2 = Video(
        channel_id=channel.id,
        folder_id=folder.id,
        storage_provider="local",
        storage_file_id="sf_01",
        filename="1.mp4",
        path="Devotional/Hanuman/1.mp4",
        day_of_month_index=1
    )
    test_db_session.add_all([v1, v2])
    await test_db_session.commit()
    await test_db_session.refresh(v1)
    await test_db_session.refresh(v2)

    # 2. List Videos
    res = await client.get("/api/v1/videos")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2

    # 3. Filter by day_of_month=15
    res_15 = await client.get("/api/v1/videos", params={"day_of_month": 15})
    assert res_15.status_code == 200
    items_15 = res_15.json()["items"]
    assert len(items_15) == 1
    assert items_15[0]["filename"] == "15.mp4"

    # 4. Preview Effective Metadata Endpoint
    preview_res = await client.post(
        f"/api/v1/videos/{v1.id}/preview-metadata",
        json={"target_date": "2026-08-15T09:00:00"}
    )
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["title"] == "Hanuman Chalisa Day 15"
    assert preview_data["tags"] == ["hanuman", "chalisa"]
    assert preview_data["source_hierarchy"]["title"] == "video_sidecar"

    # 5. Toggle Video enabled status
    toggle_res = await client.patch(f"/api/v1/videos/{v1.id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    # 6. List Folders
    folders_res = await client.get("/api/v1/folders")
    assert folders_res.status_code == 200
    f_items = folders_res.json()["items"]
    assert len(f_items) >= 1
    assert f_items[0]["name"] == "Hanuman"
    assert f_items[0]["videos_count"] == 2
