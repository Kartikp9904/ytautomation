import urllib.parse
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.models.oauth import OAuthCredential
from app.core.logging import logger


class GoogleDriveOAuthService:
    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    @classmethod
    def get_authorization_url(cls, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth 2.0 Authorization URL for Google Drive access.
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID is not configured in environment or settings.")

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(cls.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        if state:
            params["state"] = state

        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    @classmethod
    async def exchange_code_and_save(cls, db: AsyncSession, code: str) -> OAuthCredential:
        """
        Exchange authorization code for tokens, fetch account email, and encrypt tokens in DB.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google Client ID or Client Secret not configured.")

        # Exchange code with Google OAuth token endpoint
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)
            if resp.status_code != 200:
                logger.error(f"Google Drive token exchange failed: {resp.text}")
                raise ValueError(f"Failed to exchange Google OAuth code: {resp.text}")
            token_data = resp.json()

        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        if not refresh_token:
            # If prompt=consent was omitted or re-authenticating without revoke
            logger.warning("No refresh_token returned by Google. Offline access may have already been granted.")

        # Fetch account email using access token
        account_email = None
        if access_token:
            try:
                async with httpx.AsyncClient() as client:
                    user_resp = await client.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if user_resp.status_code == 200:
                        account_email = user_resp.json().get("email")
            except Exception as e:
                logger.warning(f"Could not fetch user email: {e}")

        # Check existing drive credential
        stmt = select(OAuthCredential).where(OAuthCredential.service_type == "google_drive")
        result = await db.execute(stmt)
        cred = result.scalars().first()

        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else (cred.encrypted_refresh_token if cred else "")
        encrypted_access = encrypt_token(access_token) if access_token else None

        if cred:
            if refresh_token:
                cred.encrypted_refresh_token = encrypted_refresh
            cred.encrypted_access_token = encrypted_access
            cred.token_expiry = expiry
            cred.account_email = account_email or cred.account_email
            cred.is_valid = True
            cred.last_error = None
        else:
            cred = OAuthCredential(
                service_type="google_drive",
                account_email=account_email,
                encrypted_refresh_token=encrypted_refresh,
                encrypted_access_token=encrypted_access,
                token_expiry=expiry,
                scopes=cls.SCOPES,
                is_valid=True
            )
            db.add(cred)

        await db.commit()
        await db.refresh(cred)
        return cred

    @classmethod
    async def get_drive_status(cls, db: AsyncSession) -> Dict[str, Any]:
        stmt = select(OAuthCredential).where(OAuthCredential.service_type == "google_drive")
        result = await db.execute(stmt)
        cred = result.scalars().first()

        if not cred or not cred.is_valid:
            return {
                "connected": False,
                "account_email": None,
                "has_credentials": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
                "last_error": cred.last_error if cred else None
            }

        return {
            "connected": True,
            "account_email": cred.account_email,
            "has_credentials": True,
            "token_expiry": cred.token_expiry.isoformat() if cred.token_expiry else None,
            "last_error": None
        }

    @classmethod
    async def disconnect_drive(cls, db: AsyncSession) -> bool:
        stmt = delete(OAuthCredential).where(OAuthCredential.service_type == "google_drive")
        await db.execute(stmt)
        await db.commit()
        return True
