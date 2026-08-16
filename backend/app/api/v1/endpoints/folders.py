from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.models.folder import ContentFolder
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.folder import FolderResponse, FolderListResponse, FolderUpdate

router = APIRouter()


@router.get("", response_model=FolderListResponse)
async def list_content_folders(
    channel_id: Optional[str] = Query(default=None, description="Filter folders by channel"),
    has_videos: bool = Query(default=False, description="Filter only folders containing videos"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ContentFolder, Channel.name.label("channel_name"))\
        .outerjoin(Channel, ContentFolder.channel_id == Channel.id)

    if channel_id:
        stmt = stmt.where(ContentFolder.channel_id == channel_id)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for folder, ch_name in rows:
        # Count videos directly in this folder or in descendant paths
        v_count_res = await db.execute(
            select(func.count(Video.id)).where(
                or_(
                    Video.folder_id == folder.id,
                    Video.path.like(f"{folder.name}%"),
                    Video.path.like(f"{folder.path}%")
                )
            )
        )
        videos_count = v_count_res.scalar() or 0

        if has_videos and videos_count == 0:
            continue

        items.append(FolderResponse(
            id=folder.id,
            storage_folder_id=folder.storage_folder_id,
            name=folder.name,
            path=folder.path,
            channel_id=folder.channel_id,
            default_title_template=folder.default_title_template,
            default_description_template=folder.default_description_template,
            default_tags=folder.default_tags or [],
            default_category_id=folder.default_category_id,
            default_thumbnail_storage_id=folder.default_thumbnail_storage_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            videos_count=videos_count,
            channel_name=ch_name
        ))

    return FolderListResponse(total=len(items), items=items)


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_content_folder(folder_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ContentFolder, Channel.name.label("channel_name"))\
        .outerjoin(Channel, ContentFolder.channel_id == Channel.id)\
        .where(ContentFolder.id == folder_id)

    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content Folder with ID '{folder_id}' not found"
        )

    folder, ch_name = row
    v_count_res = await db.execute(select(func.count(Video.id)).where(Video.folder_id == folder.id))
    videos_count = v_count_res.scalar() or 0

    return FolderResponse(
        id=folder.id,
        storage_folder_id=folder.storage_folder_id,
        name=folder.name,
        path=folder.path,
        channel_id=folder.channel_id,
        default_title_template=folder.default_title_template,
        default_description_template=folder.default_description_template,
        default_tags=folder.default_tags or [],
        default_category_id=folder.default_category_id,
        default_thumbnail_storage_id=folder.default_thumbnail_storage_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        videos_count=videos_count,
        channel_name=ch_name
    )


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_content_folder(
    folder_id: str,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ContentFolder).where(ContentFolder.id == folder_id)
    result = await db.execute(stmt)
    folder = result.scalars().first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content Folder with ID '{folder_id}' not found"
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(folder, field, val)

    await db.commit()
    return await get_content_folder(folder_id, db)
