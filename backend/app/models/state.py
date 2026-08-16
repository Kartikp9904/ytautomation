from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RotationState(Base, TimestampMixin):
    __tablename__ = "rotation_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), unique=True, nullable=False)
    last_video_id = Column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    current_index = Column(Integer, default=0, nullable=False)

    schedule = relationship("Schedule", back_populates="rotation_state")


class ShuffleState(Base, TimestampMixin):
    __tablename__ = "shuffle_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), unique=True, nullable=False)
    remaining_video_ids = Column(JSON, default=list, nullable=False)
    used_video_ids = Column(JSON, default=list, nullable=False)
    current_cycle = Column(Integer, default=1, nullable=False)

    schedule = relationship("Schedule", back_populates="shuffle_state")
