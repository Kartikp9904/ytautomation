from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SourceChannelSyncBase(BaseModel):
    source_channel_url: str
    target_channel_id: str
    sync_mode: str = "ALL" # ALL, SHORTS_ONLY, FULL_VIDEOS_ONLY
    auto_publish: bool = False
    publish_privacy_status: str = "public" # public, unlisted, private
    
    # Scheduling & Drip Configuration
    publish_mode: str = "SCHEDULED" # SCHEDULED, IMMEDIATE, MANUAL
    daily_publish_count: int = 3
    publish_time_slots: List[str] = ["10:00", "15:00", "20:00"]
    timezone: str = "UTC"
    max_video_size_mb: int = 300

    title_prefix: Optional[str] = None
    title_suffix: Optional[str] = None
    description_footer: Optional[str] = None
    custom_tags: Optional[List[str]] = []
    enabled: bool = True


class SourceChannelSyncCreate(SourceChannelSyncBase):
    pass


class SourceChannelSyncUpdate(BaseModel):
    source_channel_url: Optional[str] = None
    target_channel_id: Optional[str] = None
    sync_mode: Optional[str] = None
    auto_publish: Optional[bool] = None
    publish_privacy_status: Optional[str] = None
    publish_mode: Optional[str] = None
    daily_publish_count: Optional[int] = None
    publish_time_slots: Optional[List[str]] = None
    timezone: Optional[str] = None
    max_video_size_mb: Optional[int] = None
    title_prefix: Optional[str] = None
    title_suffix: Optional[str] = None
    description_footer: Optional[str] = None
    custom_tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


class SyncedSourceVideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sync_id: str
    source_video_id: str
    source_url: str
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    category_id: Optional[str] = "20"
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_short: bool = False
    download_status: str
    upload_status: str
    uploaded_youtube_video_id: Optional[str] = None
    uploaded_youtube_url: Optional[str] = None
    error_message: Optional[str] = None
    published_at_source: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SourceChannelSyncResponse(SourceChannelSyncBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_channel_name: Optional[str] = None
    source_channel_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    target_channel_name: Optional[str] = None
    videos_synced_count: Optional[int] = 0
    videos_uploaded_count: Optional[int] = 0
    last_scheduled_slot_published: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SyncTriggerResponse(BaseModel):
    success: bool
    message: str
    videos_found: int = 0
    videos_downloaded: int = 0
    videos_uploaded: int = 0
