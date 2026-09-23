from sqlalchemy import Column, String, Boolean, Text, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class SourceChannelSync(Base, TimestampMixin):
    __tablename__ = "source_channel_syncs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_channel_url = Column(String(500), nullable=False)
    source_channel_name = Column(String(255), nullable=True)
    source_channel_id = Column(String(100), index=True, nullable=True)
    target_channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    
    sync_mode = Column(String(50), default="ALL", nullable=False) # ALL, SHORTS_ONLY, FULL_VIDEOS_ONLY
    auto_publish = Column(Boolean, default=False, nullable=False)
    publish_privacy_status = Column(String(20), default="public", nullable=False) # public, unlisted, private
    
    # Metadata customization overrides
    title_prefix = Column(String(255), nullable=True)
    title_suffix = Column(String(255), nullable=True)
    description_footer = Column(Text, nullable=True)
    custom_tags = Column(JSON, default=list, nullable=True)
    
    enabled = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    target_channel = relationship("Channel", backref="source_sync_configs")
    synced_videos = relationship("SyncedSourceVideo", back_populates="sync_config", cascade="all, delete-orphan")


class SyncedSourceVideo(Base, TimestampMixin):
    __tablename__ = "synced_source_videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sync_id = Column(String(36), ForeignKey("source_channel_syncs.id", ondelete="CASCADE"), nullable=False)
    source_video_id = Column(String(100), index=True, nullable=False)
    source_url = Column(String(500), nullable=False)
    
    # Extracted metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=True)
    category_id = Column(String(20), default="20", nullable=True) # 20 = Gaming
    thumbnail_url = Column(String(1000), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_short = Column(Boolean, default=False, nullable=False)
    published_at_source = Column(DateTime(timezone=True), nullable=True)
    
    # Processing states
    download_status = Column(String(50), default="PENDING", nullable=False) # PENDING, DOWNLOADING, DOWNLOADED, FAILED
    upload_status = Column(String(50), default="PENDING", nullable=False) # PENDING, UPLOADING, UPLOADED, SKIPPED, FAILED
    local_temp_path = Column(String(1000), nullable=True)
    uploaded_youtube_video_id = Column(String(100), nullable=True)
    uploaded_youtube_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    sync_config = relationship("SourceChannelSync", back_populates="synced_videos")
