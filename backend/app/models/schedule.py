from sqlalchemy import Column, String, Integer, Boolean, Date, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # DAILY, WEEKLY, MONTHLY, ONE_TIME, CUSTOM_DATE
    schedule_type = Column(String(50), nullable=False)
    
    # SPECIFIC_VIDEO, FOLDER, POOL, DAY_OF_MONTH
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)

    # REPEAT, ROTATION, SHUFFLE, ONE_TIME, DAY_OF_MONTH
    mode = Column(String(50), nullable=False)

    publish_time = Column(String(10), nullable=False) # "09:00" in channel's timezone
    timezone = Column(String(64), nullable=False) # e.g. "Asia/Kolkata"
    upload_lead_minutes = Column(Integer, default=180, nullable=False) # upload 3h in advance

    # Scheduling filters
    days_of_week = Column(JSON, default=list, nullable=True) # [0,1,2,3,4,5,6] (Monday=0)
    days_of_month = Column(JSON, default=list, nullable=True) # [1, 15, 30]
    one_time_date = Column(Date, nullable=True) # for ONE_TIME

    # Optional schedule-level metadata overrides
    title_template = Column(String(500), nullable=True)
    description_template = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=True)
    category_id = Column(String(10), nullable=True)
    privacy_status = Column(String(20), default="private", nullable=False)

    # Advanced YouTube Upload options
    made_for_kids = Column(Boolean, default=False, nullable=False)
    age_restricted = Column(Boolean, default=False, nullable=False)
    default_language = Column(String(10), nullable=True) # e.g. "hi", "en"
    default_audio_language = Column(String(10), nullable=True)
    contains_synthetic_media = Column(Boolean, default=False, nullable=False)
    preset_category = Column(String(50), nullable=True) # e.g. "mahadev", "shinchan"

    use_youtube_scheduled_publish = Column(Boolean, default=True, nullable=False)
    dry_run = Column(Boolean, default=False, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    channel = relationship("Channel", back_populates="schedules")
    occurrences = relationship("ScheduleOccurrence", back_populates="schedule", cascade="all, delete-orphan")
    rotation_state = relationship("RotationState", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    shuffle_state = relationship("ShuffleState", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
