from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.channel_sync import (
    SourceChannelSyncCreate,
    SourceChannelSyncUpdate,
    SourceChannelSyncResponse,
    SyncedSourceVideoResponse,
    SyncTriggerResponse,
)
from app.services.channel_sync.channel_sync_service import ChannelSyncService

router = APIRouter()


@router.get("", response_model=List[SourceChannelSyncResponse])
async def list_channel_sync_configs(db: AsyncSession = Depends(get_db)):
    """List all configured source channel sync monitors"""
    return await ChannelSyncService.list_sync_configs(db)


@router.post("", response_model=SourceChannelSyncResponse, status_code=status.HTTP_201_CREATED)
async def create_channel_sync_config(
    data: SourceChannelSyncCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a new external YouTube channel to monitor and auto-sync"""
    try:
        cfg = await ChannelSyncService.create_sync_config(db, data)
        configs = await ChannelSyncService.list_sync_configs(db)
        for c in configs:
            if c.id == cfg.id:
                return c
        return cfg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{sync_id}", response_model=SourceChannelSyncResponse)
async def update_channel_sync_config(
    sync_id: str,
    data: SourceChannelSyncUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update settings for a source channel sync monitor"""
    cfg = await ChannelSyncService.update_sync_config(db, sync_id, data)
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sync monitor with ID '{sync_id}' not found.")
    configs = await ChannelSyncService.list_sync_configs(db)
    for c in configs:
        if c.id == cfg.id:
            return c
    return cfg


@router.delete("/{sync_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel_sync_config(
    sync_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a source channel sync monitor and its video history"""
    success = await ChannelSyncService.delete_sync_config(db, sync_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sync monitor with ID '{sync_id}' not found.")
    return None


@router.post("/{sync_id}/trigger", response_model=SyncTriggerResponse)
async def trigger_channel_sync(
    sync_id: str,
    max_videos: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger immediate scanning, downloading, and auto-upload for a source channel"""
    return await ChannelSyncService.sync_channel(db, sync_id, max_videos_to_download=max_videos)


@router.get("/videos", response_model=List[SyncedSourceVideoResponse])
async def list_synced_videos(
    sync_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """List all extracted/downloaded videos across all source channels"""
    return await ChannelSyncService.list_synced_videos(db, sync_id)


@router.post("/videos/{video_id}/upload", response_model=SyncedSourceVideoResponse)
async def upload_single_synced_video(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """One-click upload for a single downloaded video to target channel"""
    try:
        v = await ChannelSyncService.upload_synced_video(db, video_id)
        return SyncedSourceVideoResponse.model_validate(v)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
