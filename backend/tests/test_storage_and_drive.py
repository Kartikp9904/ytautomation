import os
import json
import pytest
import shutil
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.storage.local import LocalStorageProvider
from app.services.scanner.scanner_service import ScannerService, extract_day_of_month
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.channel import Channel
from app.core.config import settings


@pytest.fixture
def temp_test_storage(tmp_path):
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    
    # Create sample folder hierarchy
    mahadev_dir = storage_dir / "Channel_1" / "Mahadev"
    mahadev_dir.mkdir(parents=True)
    
    # Create video files
    (mahadev_dir / "15.mp4").write_bytes(b"dummy video content 15")
    (mahadev_dir / "01.mp4").write_bytes(b"dummy video content 01")
    (mahadev_dir / "morning_aarti.mp4").write_bytes(b"dummy video content aarti")
    
    # Create sidecar json
    meta = {
        "title": "Special Mahadev Aarti",
        "description": "Sacred prayers",
        "tags": ["mahadev", "shiv"],
        "category": "10"
    }
    (mahadev_dir / "15.json").write_text(json.dumps(meta), encoding="utf-8")
    
    # Create sidecar thumbnail
    (mahadev_dir / "15.jpg").write_bytes(b"dummy image bytes")

    return str(storage_dir)


def test_extract_day_of_month():
    assert extract_day_of_month("1.mp4") == 1
    assert extract_day_of_month("01.mp4") == 1
    assert extract_day_of_month("15.mp4") == 15
    assert extract_day_of_month("31.mp4") == 31
    assert extract_day_of_month("15_special.mp4") == 15
    assert extract_day_of_month("darshan_28.mp4") == 28
    assert extract_day_of_month("morning_aarti.mp4") is None
    assert extract_day_of_month("chalisa.mp4") is None


@pytest.mark.asyncio
async def test_local_storage_provider(temp_test_storage, tmp_path):
    provider = LocalStorageProvider(base_path=temp_test_storage)
    assert await provider.is_connected() is True
    assert provider.provider_name == "local"

    # List folders
    folders = await provider.list_folders()
    assert len(folders) >= 1
    assert folders[0].name == "Channel_1"

    # List subfolders
    subfolders = await provider.list_folders("Channel_1")
    assert len(subfolders) >= 1
    assert subfolders[0].name == "Mahadev"

    # List files
    files = await provider.list_files("Channel_1/Mahadev")
    file_names = [f.name for f in files]
    assert "15.mp4" in file_names
    assert "15.json" in file_names
    assert "15.jpg" in file_names

    # Read text file
    json_content = await provider.read_text_file("Channel_1/Mahadev/15.json")
    assert json_content is not None
    data = json.loads(json_content)
    assert data["title"] == "Special Mahadev Aarti"

    # Download / copy file
    download_dest = str(tmp_path / "downloaded_15.mp4")
    progress_called = False

    def progress_cb(current, total):
        nonlocal progress_called
        progress_called = True

    success = await provider.download_file("Channel_1/Mahadev/15.mp4", download_dest, progress_cb)
    assert success is True
    assert os.path.exists(download_dest)
    assert progress_called is True

    # Path traversal protection
    with pytest.raises(ValueError):
        provider._get_abs_path("../../../etc/passwd")


@pytest.mark.asyncio
async def test_scanner_service_indexing_and_idempotency(temp_test_storage, test_db_session: AsyncSession):
    provider = LocalStorageProvider(base_path=temp_test_storage)

    # 1. First scan
    scan1 = await ScannerService.scan_and_index(test_db_session, provider)
    assert scan1.folders_found >= 2
    assert scan1.videos_found == 3
    assert scan1.sidecar_json_found == 1
    assert scan1.thumbnails_found == 1
    assert len(scan1.errors) == 0

    # Verify DB records
    v_stmt = select(Video).order_by(Video.filename.asc())
    v_res = await test_db_session.execute(v_stmt)
    videos = v_res.scalars().all()
    assert len(videos) == 3

    # Check 15.mp4 attributes
    vid_15 = next(v for v in videos if v.filename == "15.mp4")
    assert vid_15.day_of_month_index == 15
    assert vid_15.custom_metadata is not None
    assert vid_15.custom_metadata["title"] == "Special Mahadev Aarti"
    assert vid_15.custom_thumbnail_file_id is not None

    # Check 01.mp4
    vid_01 = next(v for v in videos if v.filename == "01.mp4")
    assert vid_01.day_of_month_index == 1

    # Check morning_aarti.mp4
    vid_aarti = next(v for v in videos if v.filename == "morning_aarti.mp4")
    assert vid_aarti.day_of_month_index is None

    # 2. Second scan (Idempotency test: should not duplicate videos or folders)
    scan2 = await ScannerService.scan_and_index(test_db_session, provider)
    assert scan2.videos_found == 3

    v_res2 = await test_db_session.execute(v_stmt)
    videos2 = v_res2.scalars().all()
    assert len(videos2) == 3 # Still exactly 3 videos in DB


@pytest.mark.asyncio
async def test_drive_api_endpoints(client: AsyncClient):
    # 1. Check status
    res = await client.get("/api/v1/drive/status")
    assert res.status_code == 200
    data = res.json()
    assert "connected" in data
    assert "has_credentials" in data

    # 2. Create sample test data
    sample_res = await client.post("/api/v1/drive/create-sample-data")
    assert sample_res.status_code == 200
    sample_data = sample_res.json()
    assert sample_data["total_files_created"] > 0

    # 3. List folders
    folders_res = await client.get("/api/v1/drive/folders?provider=local")
    assert folders_res.status_code == 200
    folders = folders_res.json()
    assert len(folders) >= 2 # Channel_1, Channel_2

    # 4. Trigger Scan via API
    scan_res = await client.post("/api/v1/drive/scan", json={"provider": "local"})
    assert scan_res.status_code == 200
    scan_summary = scan_res.json()
    assert scan_summary["videos_found"] > 0
    assert scan_summary["folders_found"] > 0
    assert len(scan_summary["errors"]) == 0
