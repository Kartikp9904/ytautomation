from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ScheduleOccurrence(Base, TimestampMixin):
    __tablename__ = "schedule_occurrences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=True, index=True)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)

    # Unique idempotency key to prevent ANY duplicate uploads
    idempotency_key = Column(String(512), unique=True, index=True, nullable=False)

    scheduled_publish_time = Column(DateTime(timezone=True), nullable=False)
    target_upload_time = Column(DateTime(timezone=True), nullable=False)

    # PENDING, DOWNLOADING, UPLOADING, COMPLETED, FAILED, SKIPPED
    status = Column(String(50), default="PENDING", nullable=False, index=True)
    dry_run = Column(Boolean, default=False, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    youtube_video_id = Column(String(100), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    schedule = relationship("Schedule", back_populates="occurrences")
    channel = relationship("Channel", back_populates="occurrences")
    video = relationship("Video", back_populates="occurrences")
    upload_jobs = relationship("UploadJob", back_populates="occurrence", cascade="all, delete-orphan")
