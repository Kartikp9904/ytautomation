from sqlalchemy import Column, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    youtube_channel_id = Column(String(100), unique=True, index=True, nullable=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    # Channel-level default metadata
    default_title_template = Column(String(500), nullable=True)
    default_description_template = Column(Text, nullable=True)
    default_tags = Column(JSON, default=list, nullable=True)
    default_category_id = Column(String(10), default="22", nullable=True) # 22 = People & Blogs
    default_privacy_status = Column(String(20), default="private", nullable=False) # private, unlisted, public
    default_thumbnail_storage_id = Column(String(255), nullable=True)

    # Relationships
    folders = relationship("ContentFolder", back_populates="channel", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="channel")
    schedules = relationship("Schedule", back_populates="channel", cascade="all, delete-orphan")
    occurrences = relationship("ScheduleOccurrence", back_populates="channel", cascade="all, delete-orphan")
    oauth_credential = relationship("OAuthCredential", back_populates="channel", uselist=False, cascade="all, delete-orphan")
