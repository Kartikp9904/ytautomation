import zoneinfo
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Channel display name")
    timezone: str = Field(default="UTC", description="IANA Timezone, e.g. Asia/Kolkata")
    enabled: bool = Field(default=True, description="Whether channel is active")
    default_title_template: Optional[str] = Field(default=None, max_length=500)
    default_description_template: Optional[str] = Field(default=None)
    default_tags: List[str] = Field(default_factory=list)
    default_category_id: str = Field(default="22", max_length=10, description="YouTube Video Category ID (22=People & Blogs)")
    default_privacy_status: str = Field(default="private", description="private, unlisted, or public")

    @field_validator("timezone")
    def validate_timezone(cls, v: str) -> str:
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid IANA timezone: '{v}'. Example valid timezones: 'Asia/Kolkata', 'UTC', 'America/New_York'")
        return v

    @field_validator("default_privacy_status")
    def validate_privacy_status(cls, v: str) -> str:
        valid_statuses = ["private", "unlisted", "public"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid privacy status '{v}'. Must be one of {valid_statuses}")
        return v.lower()


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(default=None)
    enabled: Optional[bool] = Field(default=None)
    default_title_template: Optional[str] = Field(default=None, max_length=500)
    default_description_template: Optional[str] = Field(default=None)
    default_tags: Optional[List[str]] = Field(default=None)
    default_category_id: Optional[str] = Field(default=None, max_length=10)
    default_privacy_status: Optional[str] = Field(default=None)

    @field_validator("timezone")
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                zoneinfo.ZoneInfo(v)
            except Exception:
                raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v

    @field_validator("default_privacy_status")
    def validate_privacy_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = ["private", "unlisted", "public"]
            if v.lower() not in valid_statuses:
                raise ValueError(f"Invalid privacy status '{v}'. Must be one of {valid_statuses}")
            return v.lower()
        return v


class ChannelResponse(ChannelBase):
    id: str
    youtube_channel_id: Optional[str] = None
    default_thumbnail_storage_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Dynamic stats
    schedules_count: int = 0
    videos_count: int = 0
    is_connected: bool = False

    model_config = ConfigDict(from_attributes=True)


class ChannelListResponse(BaseModel):
    total: int
    items: List[ChannelResponse]


class TimezoneOption(BaseModel):
    name: str
    label: str
    offset: str
