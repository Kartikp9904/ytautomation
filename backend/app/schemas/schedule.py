from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class ScheduleBase(BaseModel):
    channel_id: str
    name: str
    schedule_type: str = Field(default="DAILY", description="DAILY, WEEKLY, MONTHLY, ONE_TIME")
    source_type: str = Field(default="FOLDER", description="FOLDER, VIDEO")
    source_id: str
    mode: str = Field(default="DAY_OF_MONTH", description="DAY_OF_MONTH, REPEAT, ROTATION, SHUFFLE, SINGLE_VIDEO")
    publish_time: str = Field(default="09:00", description="HH:MM format in channel timezone")
    timezone: str = "UTC"
    upload_lead_minutes: int = Field(default=180, ge=0, description="Minutes before publish time to start upload")
    use_youtube_scheduled_publish: bool = Field(default=True, description="Schedule via YouTube publishAt")
    dry_run: bool = Field(default=False, description="Simulate upload without pushing to YouTube")
    days_of_week: Optional[List[str]] = Field(default=None, description="e.g. ['MON', 'WED', 'FRI']")
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    repeat_interval_days: Optional[int] = Field(default=None, ge=1)
    enabled: bool = True
    
    # Metadata Overrides (Optional)
    title_template: Optional[str] = None
    description_template: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[str] = None
    privacy_status: Optional[str] = "private"
    custom_thumbnail_file_id: Optional[str] = None


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    schedule_type: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    mode: Optional[str] = None
    publish_time: Optional[str] = None
    timezone: Optional[str] = None
    upload_lead_minutes: Optional[int] = None
    use_youtube_scheduled_publish: Optional[bool] = None
    dry_run: Optional[bool] = None
    days_of_week: Optional[List[str]] = None
    day_of_month: Optional[int] = None
    repeat_interval_days: Optional[int] = None
    enabled: Optional[bool] = None
    title_template: Optional[str] = None
    description_template: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[str] = None
    privacy_status: Optional[str] = None
    custom_thumbnail_file_id: Optional[str] = None


class ScheduleResponse(ScheduleBase):
    id: str
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Dynamic fields
    next_run_time: Optional[datetime] = None
    channel_name: Optional[str] = None
    source_name: Optional[str] = None
    
    # Rotation state
    current_rotation_index: Optional[int] = None
    total_rotation_videos: Optional[int] = None

    # Shuffle state
    shuffle_remaining_count: Optional[int] = None
    shuffle_used_count: Optional[int] = None
    shuffle_cycle: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleListResponse(BaseModel):
    total: int
    items: List[ScheduleResponse]


class ScheduleOccurrenceResponse(BaseModel):
    id: str
    schedule_id: Optional[str] = None
    channel_id: str
    video_id: Optional[str] = None
    scheduled_publish_time: datetime
    target_upload_time: datetime
    status: str
    dry_run: bool = False
    youtube_video_id: Optional[str] = None
    idempotency_key: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriggerNowResponse(BaseModel):
    message: str
    schedule_id: str
    occurrence_id: Optional[str] = None
    status: str


class ResetRotationResponse(BaseModel):
    message: str
    schedule_id: str
    current_index: int


class ReshuffleResponse(BaseModel):
    message: str
    schedule_id: str
    total_shuffled: int
    current_cycle: int


class CalendarDaySimulation(BaseModel):
    date: str
    day_number: int
    video_id: Optional[str] = None
    video_filename: Optional[str] = None
    is_matched: bool
    is_fallback: bool
    fallback_reason: Optional[str] = None
    is_leap_year: bool
    days_in_month: int


class CalendarSimulationResponse(BaseModel):
    schedule_id: str
    year: int
    month: int
    days_in_month: int
    is_leap_year: bool
    days: List[CalendarDaySimulation]


class TimelineItem(BaseModel):
    id: str
    schedule_id: Optional[str] = None
    schedule_name: Optional[str] = None
    channel_name: str
    channel_id: str
    video_title: str
    scheduled_publish_time: str
    target_upload_time: str
    status: str
    dry_run: bool
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None


class CalendarEventItem(BaseModel):
    id: str
    date: str # YYYY-MM-DD
    title: str
    schedule_name: str
    channel_name: str
    mode: str
    publish_time: str
    status: str
    dry_run: bool
    youtube_url: Optional[str] = None
