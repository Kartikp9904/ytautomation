from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ContentFolder(Base, TimestampMixin):
    __tablename__ = "content_folders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True)
    storage_folder_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(1024), nullable=False)

    # Folder-level default metadata
    default_title_template = Column(String(500), nullable=True)
    default_description_template = Column(Text, nullable=True)
    default_tags = Column(JSON, default=list, nullable=True)
    default_category_id = Column(String(10), nullable=True)
    default_thumbnail_storage_id = Column(String(255), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="folders")
    videos = relationship("Video", back_populates="folder")
