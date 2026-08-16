from sqlalchemy import Column, String, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class OAuthCredential(Base, TimestampMixin):
    __tablename__ = "oauth_credentials"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # 'google_drive' or 'youtube_channel'
    service_type = Column(String(50), nullable=False, index=True)
    channel_id = Column(String(36), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True, index=True)
    
    account_email = Column(String(255), nullable=True)
    # Encrypted with AES-256-GCM
    encrypted_refresh_token = Column(Text, nullable=False)
    encrypted_access_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, default=list, nullable=False)

    is_valid = Column(Boolean, default=True, nullable=False)
    last_error = Column(Text, nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="oauth_credential")
