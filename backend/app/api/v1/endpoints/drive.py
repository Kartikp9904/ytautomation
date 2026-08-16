import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.schemas.drive import (
    DriveAuthUrlResponse,
    DriveCallbackRequest,
    DriveStatusResponse,
    DriveFolderItemResponse,
    ScanTriggerRequest,
    ScanSummaryResponse,
)
from app.services.google_drive.oauth import GoogleDriveOAuthService
from app.services.storage.factory import get_storage_provider
from app.services.scanner.scanner_service import ScannerService

router = APIRouter()


@router.get("/auth-url", response_model=DriveAuthUrlResponse)
async def get_drive_auth_url(state: Optional[str] = None):
    try:
        url = GoogleDriveOAuthService.get_authorization_url(state=state)
        return DriveAuthUrlResponse(auth_url=url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/callback")
@router.get("/oauth/callback")
async def handle_drive_get_callback(
    code: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Browser redirect callback from Google Drive OAuth.
    """
    frontend_drive_url = "http://localhost:5173/drive"
    if error:
        return RedirectResponse(url=f"{frontend_drive_url}?drive_error={error}")
    if not code:
        return RedirectResponse(url=f"{frontend_drive_url}?drive_error=missing_code")

    try:
        await GoogleDriveOAuthService.exchange_code_and_save(db, code)
        return RedirectResponse(url=f"{frontend_drive_url}?connected=true")
    except Exception as e:
        return RedirectResponse(url=f"{frontend_drive_url}?drive_error={str(e)}")


@router.post("/callback", response_model=DriveStatusResponse)
async def handle_drive_callback(
    data: DriveCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        cred = await GoogleDriveOAuthService.exchange_code_and_save(db, data.code)
        return DriveStatusResponse(
            connected=True,
            account_email=cred.account_email,
            has_credentials=True,
            token_expiry=cred.token_expiry.isoformat() if cred.token_expiry else None,
            storage_provider="google_drive"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/status", response_model=DriveStatusResponse)
async def get_drive_connection_status(db: AsyncSession = Depends(get_db)):
    status_info = await GoogleDriveOAuthService.get_drive_status(db)
    return DriveStatusResponse(
        connected=status_info["connected"],
        account_email=status_info.get("account_email"),
        has_credentials=status_info.get("has_credentials", False),
        token_expiry=status_info.get("token_expiry"),
        last_error=status_info.get("last_error"),
        storage_provider=settings.STORAGE_PROVIDER
    )


@router.post("/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_drive(db: AsyncSession = Depends(get_db)):
    await GoogleDriveOAuthService.disconnect_drive(db)
    return {"message": "Google Drive disconnected successfully."}


@router.get("/folders", response_model=List[DriveFolderItemResponse])
async def list_folders(
    parent_id: Optional[str] = Query(default=None, description="Parent folder ID or 'root'"),
    provider_name: Optional[str] = Query(default=None, description="Override storage provider"),
    provider: Optional[str] = Query(default=None, description="Alias for provider_name"),
    db: AsyncSession = Depends(get_db)
):
    target = provider or provider_name
    storage_prov = await get_storage_provider(provider_name=target, db=db)
    items = await storage_prov.list_folders(parent_id=parent_id)
    return [
        DriveFolderItemResponse(
            id=item.id,
            name=item.name,
            path=item.path,
            parent_id=item.parent_id,
            modified_time=item.modified_time
        )
        for item in items
    ]


@router.post("/scan", response_model=ScanSummaryResponse)
async def trigger_storage_scan(
    data: ScanTriggerRequest,
    db: AsyncSession = Depends(get_db)
):
    provider = await get_storage_provider(provider_name=data.provider, db=db)
    result = await ScannerService.scan_and_index(
        db=db,
        provider=provider,
        root_id=data.root_folder_id,
        channel_id=data.channel_id
    )
    return ScanSummaryResponse(
        root_id=result.root_id,
        folders_found=result.folders_found,
        videos_found=result.videos_found,
        sidecar_json_found=result.sidecar_json_found,
        thumbnails_found=result.thumbnails_found,
        errors=result.errors
    )


@router.post("/create-sample-data")
async def create_sample_local_data():
    """
    Development/Testing helper: Creates a realistic sample devotional video folder structure
    with day-of-month numeric files (1.mp4 ... 31.mp4), sidecar JSONs, and thumbnail files.
    """
    base = os.path.abspath(settings.LOCAL_STORAGE_BASE_PATH)
    sample_structure = {
        "Channel_1/Mahadev": [
            "1.mp4", "2.mp4", "3.mp4", "15.mp4", "15.json", "15.jpg", "28.mp4", "30.mp4", "31.mp4"
        ],
        "Channel_1/Hanuman": [
            "1.mp4", "2.mp4", "15.mp4", "15.jpg", "chalisa.mp4"
        ],
        "Channel_1/Krishna": [
            "1.mp4", "darshan.mp4", "bhajan.mp4"
        ],
        "Channel_2/Mahadev": [
            "morning_aarti.mp4", "bhasma_aarti.mp4", "darshan.mp4", "shiv_mantra.mp4", "default.jpg"
        ],
        "Channel_2/Hanuman": [
            "chalisa.mp4", "hanuman_aarti.mp4"
        ]
    }

    dummy_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    dummy_image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"

    created_count = 0
    for rel_folder, files in sample_structure.items():
        folder_dir = os.path.join(base, rel_folder)
        os.makedirs(folder_dir, exist_ok=True)
        for fname in files:
            file_path = os.path.join(folder_dir, fname)
            if fname.endswith(".json"):
                meta = {
                    "title": f"Special Aarti | {os.path.splitext(fname)[0]} | Har Har Mahadev",
                    "description": "Daily devotional sacred prayers and darshan.",
                    "tags": ["mahadev", "shiv", "bhakti", "aarti"],
                    "category": "10"
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            elif fname.endswith(".jpg"):
                with open(file_path, "wb") as f:
                    f.write(dummy_image_bytes)
            else:
                with open(file_path, "wb") as f:
                    f.write(dummy_video_bytes)
            created_count += 1

    return {
        "message": "Sample local devotional folder structure created successfully.",
        "base_path": base,
        "total_files_created": created_count,
        "structure": list(sample_structure.keys())
    }
