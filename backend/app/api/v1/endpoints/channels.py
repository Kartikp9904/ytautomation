from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.channel import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelListResponse,
    TimezoneOption,
)
from app.services.channel_service import ChannelService

router = APIRouter()


@router.get("", response_model=ChannelListResponse)
async def list_channels(db: AsyncSession = Depends(get_db)):
    total, items = await ChannelService.list_channels(db)
    return ChannelListResponse(total=total, items=items)


@router.get("/timezones", response_model=List[TimezoneOption])
async def get_timezones():
    return ChannelService.get_supported_timezones()


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(data: ChannelCreate, db: AsyncSession = Depends(get_db)):
    return await ChannelService.create_channel(db, data)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    channel = await ChannelService.get_channel_by_id(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID '{channel_id}' not found"
        )
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: str,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db)
):
    channel = await ChannelService.update_channel(db, channel_id, data)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID '{channel_id}' not found"
        )
    return channel


@router.patch("/{channel_id}/toggle", response_model=ChannelResponse)
async def toggle_channel_status(channel_id: str, db: AsyncSession = Depends(get_db)):
    channel = await ChannelService.toggle_channel(db, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID '{channel_id}' not found"
        )
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await ChannelService.delete_channel(db, channel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID '{channel_id}' not found"
        )
    return None
