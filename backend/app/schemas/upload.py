from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ManualUploadRequest(BaseModel):
    video_id: str
    channel_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[str] = None
    privacy_status: Optional[str] = "private"


class ManualUploadResponse(BaseModel):
    message: str
    occurrence_id: str
    job_id: str
    status: str


class UploadJobResponse(BaseModel):
    id: str
    occurrence_id: str
    status: str
    bytes_downloaded: int
    bytes_uploaded: int
    total_bytes: int
    progress_percentage: float = 0.0
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadJobListResponse(BaseModel):
    total: int
    items: List[UploadJobResponse]
