from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class VideoBase(BaseModel):
    filename: str
    path: str
    mime_type: str = "video/mp4"
    size_bytes: int = 0
    day_of_month_index: Optional[int] = None
    enabled: bool = True
    custom_metadata: Optional[Dict[str, Any]] = None
    custom_thumbnail_file_id: Optional[str] = None


class VideoUpdate(BaseModel):
    enabled: Optional[bool] = None
    channel_id: Optional[str] = None
    folder_id: Optional[str] = None
    day_of_month_index: Optional[int] = None
    custom_metadata: Optional[Dict[str, Any]] = None
    custom_thumbnail_file_id: Optional[str] = None


class VideoResponse(VideoBase):
    id: str
    channel_id: Optional[str] = None
    folder_id: Optional[str] = None
    storage_provider: str
    storage_file_id: str
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Associated info
    channel_name: Optional[str] = None
    folder_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VideoListResponse(BaseModel):
    total: int
    items: List[VideoResponse]


class MetadataPreviewRequest(BaseModel):
    channel_id: Optional[str] = None
    schedule_id: Optional[str] = None
    target_date: Optional[str] = None # ISO format e.g. "2026-08-15T09:00:00"


class MetadataPreviewResponse(BaseModel):
    video_id: str
    video_filename: str
    title: str
    description: str
    tags: List[str]
    category_id: str
    privacy_status: str
    thumbnail_storage_id: Optional[str] = None
    source_hierarchy: Dict[str, str]
