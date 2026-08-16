from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider
from app.services.storage.google_drive import GoogleDriveStorageProvider
from app.models.oauth import OAuthCredential
from app.core.config import settings


async def get_storage_provider(
    provider_name: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> StorageProvider:
    """
    Factory function to retrieve the active StorageProvider instance.
    """
    target_provider = (provider_name or settings.STORAGE_PROVIDER).lower()

    if target_provider == "google_drive" and db is not None:
        # Retrieve encrypted refresh token from DB
        stmt = select(OAuthCredential).where(
            OAuthCredential.service_type == "google_drive",
            OAuthCredential.is_valid == True
        )
        result = await db.execute(stmt)
        cred = result.scalars().first()
        if cred and cred.encrypted_refresh_token:
            return GoogleDriveStorageProvider(encrypted_refresh_token=cred.encrypted_refresh_token)
        # If no credentials yet, return unauthenticated instance (will report is_connected=False)
        return GoogleDriveStorageProvider(encrypted_refresh_token=None)

    # Default to LocalStorageProvider
    return LocalStorageProvider(base_path=settings.LOCAL_STORAGE_BASE_PATH)
