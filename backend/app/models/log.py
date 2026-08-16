from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime
from app.core.database import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(BigInteger().with_variant(BigInteger, "postgresql").with_variant(BigInteger, "sqlite"), primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)
    module = Column(String(100), nullable=False, index=True)
    channel_id = Column(String(36), nullable=True, index=True)
    occurrence_id = Column(String(36), nullable=True, index=True)
    message = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
