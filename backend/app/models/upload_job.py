from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class UploadJob(Base, TimestampMixin):
    __tablename__ = "upload_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    occurrence_id = Column(String(36), ForeignKey("schedule_occurrences.id", ondelete="CASCADE"), nullable=False, index=True)

    # QUEUED, IN_PROGRESS, SUCCESS, FAILED, RETRYING
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=5, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # TEMPORARY, PERMANENT, QUOTA_EXCEEDED
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    temp_file_path = Column(String(1024), nullable=True)
    bytes_downloaded = Column(BigInteger, default=0, nullable=False)
    bytes_uploaded = Column(BigInteger, default=0, nullable=False)
    total_bytes = Column(BigInteger, default=0, nullable=False)
    youtube_resumable_uri = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    occurrence = relationship("ScheduleOccurrence", back_populates="upload_jobs")
