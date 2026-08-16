from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class FolderBase(BaseModel):
    name: str
    path: str
    channel_id: Optional[str] = None
    default_title_template: Optional[str] = None
    default_description_template: Optional[str] = None
    default_tags: List[str] = Field(default_factory=list)
    default_category_id: Optional[str] = None
    default_thumbnail_storage_id: Optional[str] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[str] = None
    default_title_template: Optional[str] = None
    default_description_template: Optional[str] = None
    default_tags: Optional[List[str]] = None
    default_category_id: Optional[str] = None
    default_thumbnail_storage_id: Optional[str] = None


class FolderResponse(FolderBase):
    id: str
    storage_folder_id: str
    created_at: datetime
    updated_at: datetime
    videos_count: int = 0
    channel_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FolderListResponse(BaseModel):
    total: int
    items: List[FolderResponse]
