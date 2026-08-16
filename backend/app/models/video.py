from sqlalchemy import Column, String, BigInteger, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Video(Base, TimestampMixin):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(String(36), ForeignKey("content_folders.id", ondelete="SET NULL"), nullable=True, index=True)
    storage_provider = Column(String(50), default="google_drive", nullable=False)
    storage_file_id = Column(String(255), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    path = Column(String(1024), nullable=False)
    mime_type = Column(String(100), default="video/mp4", nullable=False)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    
    # 1-31 if named e.g. 15.mp4 or 01.mp4 for day-of-month scheduling
    day_of_month_index = Column(Integer, index=True, nullable=True)
    
    # Optional custom sidecar metadata (.json)
    custom_metadata = Column(JSON, nullable=True)
    # Optional matching sidecar thumbnail (.jpg/.png)
    custom_thumbnail_file_id = Column(String(255), nullable=True)

    enabled = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="videos")
    folder = relationship("ContentFolder", back_populates="videos")
    occurrences = relationship("ScheduleOccurrence", back_populates="video")
