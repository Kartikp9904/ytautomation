from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.models.video import Video
from app.models.channel import Channel
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.schemas.video import (
    VideoResponse,
    VideoListResponse,
    VideoUpdate,
    MetadataPreviewRequest,
    MetadataPreviewResponse,
)
from app.services.metadata.metadata_engine import MetadataEngine

router = APIRouter()


@router.get("", response_model=VideoListResponse)
async def list_videos(
    channel_id: Optional[str] = Query(default=None, description="Filter by channel ID"),
    folder_id: Optional[str] = Query(default=None, description="Filter by folder ID"),
    day_of_month: Optional[int] = Query(default=None, ge=1, le=31, description="Filter by day of month (1-31)"),
    enabled: Optional[bool] = Query(default=None, description="Filter by enabled status"),
    search: Optional[str] = Query(default=None, description="Search by filename or path"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Video, Channel.name.label("channel_name"), ContentFolder.name.label("folder_name"))\
        .outerjoin(Channel, Video.channel_id == Channel.id)\
        .outerjoin(ContentFolder, Video.folder_id == ContentFolder.id)

    if channel_id:
        stmt = stmt.where(Video.channel_id == channel_id)
    if folder_id:
        target_f = (await db.execute(select(ContentFolder).where(ContentFolder.id == folder_id))).scalars().first()
        if target_f:
            all_fols = (await db.execute(select(ContentFolder.id).where(
                or_(
                    ContentFolder.id == target_f.id,
                    ContentFolder.path.like(f"{target_f.path}%"),
                    ContentFolder.name == target_f.name
                )
            ))).scalars().all()
            stmt = stmt.where(
                or_(
                    Video.folder_id.in_(all_fols),
                    Video.path.like(f"{target_f.name}%"),
                    Video.path.like(f"{target_f.path}%")
                )
            )
        else:
            stmt = stmt.where(Video.folder_id == folder_id)
    if day_of_month is not None:
        stmt = stmt.where(Video.day_of_month_index == day_of_month)
    if enabled is not None:
        stmt = stmt.where(Video.enabled == enabled)
    if search:
        search_filter = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Video.filename.ilike(search_filter),
                Video.path.ilike(search_filter)
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paged items
    stmt = stmt.order_by(Video.day_of_month_index.asc().nulls_last(), Video.filename.asc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for video, ch_name, f_name in rows:
        resp = VideoResponse(
            id=video.id,
            channel_id=video.channel_id,
            folder_id=video.folder_id,
            storage_provider=video.storage_provider,
            storage_file_id=video.storage_file_id,
            filename=video.filename,
            path=video.path,
            mime_type=video.mime_type,
            size_bytes=video.size_bytes,
            day_of_month_index=video.day_of_month_index,
            custom_metadata=video.custom_metadata,
            custom_thumbnail_file_id=video.custom_thumbnail_file_id,
            enabled=video.enabled,
            last_used_at=video.last_used_at,
            created_at=video.created_at,
            updated_at=video.updated_at,
            channel_name=ch_name,
            folder_name=f_name
        )
        items.append(resp)

    return VideoListResponse(total=total, items=items)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Video, Channel.name.label("channel_name"), ContentFolder.name.label("folder_name"))\
        .outerjoin(Channel, Video.channel_id == Channel.id)\
        .outerjoin(ContentFolder, Video.folder_id == ContentFolder.id)\
        .where(Video.id == video_id)
    
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID '{video_id}' not found"
        )
    
    video, ch_name, f_name = row
    return VideoResponse(
        id=video.id,
        channel_id=video.channel_id,
        folder_id=video.folder_id,
        storage_provider=video.storage_provider,
        storage_file_id=video.storage_file_id,
        filename=video.filename,
        path=video.path,
        mime_type=video.mime_type,
        size_bytes=video.size_bytes,
        day_of_month_index=video.day_of_month_index,
        custom_metadata=video.custom_metadata,
        custom_thumbnail_file_id=video.custom_thumbnail_file_id,
        enabled=video.enabled,
        last_used_at=video.last_used_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
        channel_name=ch_name,
        folder_name=f_name
    )


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: str,
    data: VideoUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalars().first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID '{video_id}' not found"
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(video, field, val)

    await db.commit()
    await db.refresh(video)
    return await get_video(video_id, db)


@router.patch("/{video_id}/toggle", response_model=VideoResponse)
async def toggle_video_status(video_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalars().first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID '{video_id}' not found"
        )

    video.enabled = not video.enabled
    await db.commit()
    return await get_video(video_id, db)


@router.post("/{video_id}/preview-metadata", response_model=MetadataPreviewResponse)
async def preview_video_metadata(
    video_id: str,
    data: MetadataPreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    # Fetch video
    v_stmt = select(Video).where(Video.id == video_id)
    v_res = await db.execute(v_stmt)
    video = v_res.scalars().first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with ID '{video_id}' not found"
        )

    # Fetch channel
    ch_id = data.channel_id or video.channel_id
    channel = None
    if ch_id:
        ch_res = await db.execute(select(Channel).where(Channel.id == ch_id))
        channel = ch_res.scalars().first()

    # Fetch folder
    folder = None
    if video.folder_id:
        f_res = await db.execute(select(ContentFolder).where(ContentFolder.id == video.folder_id))
        folder = f_res.scalars().first()

    # Fetch schedule
    schedule = None
    if data.schedule_id:
        s_res = await db.execute(select(Schedule).where(Schedule.id == data.schedule_id))
        schedule = s_res.scalars().first()

    target_dt = datetime.fromisoformat(data.target_date) if data.target_date else datetime.now()

    resolved = MetadataEngine.resolve_effective_metadata(
        video=video,
        channel=channel,
        folder=folder,
        schedule=schedule,
        target_datetime=target_dt
    )

    return MetadataPreviewResponse(
        video_id=video.id,
        video_filename=video.filename,
        title=resolved.title,
        description=resolved.description,
        tags=resolved.tags,
        category_id=resolved.category_id,
        privacy_status=resolved.privacy_status,
        thumbnail_storage_id=resolved.thumbnail_storage_id,
        source_hierarchy=resolved.source_hierarchy
    )


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a video from the database index"""
    stmt = select(Video).where(Video.id == video_id)
    res = await db.execute(stmt)
    video = res.scalars().first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    await db.delete(video)
    await db.commit()
    return {"message": "Video deleted successfully", "video_id": video_id}


@router.delete("/actions/clear-sample-data")
async def clear_sample_data(db: AsyncSession = Depends(get_db)):
    """Clears mock sample video and folder test records from the database"""
    v_stmt = select(Video).where(
        or_(
            Video.path.like("Channel_1%"),
            Video.path.like("Channel_2%"),
            Video.path.like("storage_test%")
        )
    )
    v_res = await db.execute(v_stmt)
    sample_videos = v_res.scalars().all()
    for v in sample_videos:
        await db.delete(v)

    f_stmt = select(ContentFolder).where(
        or_(
            ContentFolder.path.like("Channel_1%"),
            ContentFolder.path.like("Channel_2%"),
            ContentFolder.path.like("storage_test%")
        )
    )
    f_res = await db.execute(f_stmt)
    sample_folders = f_res.scalars().all()
    for f in sample_folders:
        await db.delete(f)

    await db.commit()
    return {
        "message": "Sample data cleared successfully",
        "videos_deleted": len(sample_videos),
        "folders_deleted": len(sample_folders)
    }
