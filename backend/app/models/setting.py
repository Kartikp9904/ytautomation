from sqlalchemy import Column, String, JSON
from app.core.database import Base
from app.models.base import TimestampMixin


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
