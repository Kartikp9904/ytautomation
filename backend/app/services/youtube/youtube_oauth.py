import json
import urllib.parse
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret
from app.models.channel import Channel
from app.models.oauth import OAuthCredential
from app.services.youtube.quota_tracker import YouTubeQuotaTracker, QUOTA_READ_LIST
from app.core.logging import logger

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email"
]


class YouTubeOAuthService:
    @classmethod
    def get_client_config(cls) -> Dict[str, Any]:
        """Loads Google OAuth client credentials from configuration"""
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        if not client_id or not client_secret:
            logger.warning("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing from settings.")

        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }

    @classmethod
    def generate_auth_url(cls, channel_id: str, redirect_uri: str) -> str:
        """Generates Google OAuth consent screen URL with state=channel_id"""
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID is not configured in environment or settings.")

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": channel_id
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    @classmethod
    async def exchange_code_for_tokens(
        cls,
        channel_id: str,
        code: str,
        redirect_uri: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Exchanges authorization code for tokens, verifies YouTube channel,
        encrypts credentials, and updates channel records.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google Client ID or Client Secret not configured.")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)
            if resp.status_code != 200:
                logger.error(f"YouTube token exchange failed: {resp.text}")
                raise ValueError(f"Failed to exchange YouTube OAuth code: {resp.text}")
            token_data = resp.json()

        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=YOUTUBE_SCOPES
        )

        # Verify YouTube Channel identity using authenticated YouTube API service
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        response = youtube.channels().list(
            mine=True,
            part="snippet,contentDetails,statistics"
        ).execute()

        await YouTubeQuotaTracker.record_quota_usage(channel_id, QUOTA_READ_LIST, db)

        items = response.get("items", [])
        if not items:
            raise ValueError("No YouTube channel found associated with this Google Account.")

        yt_channel_info = items[0]
        yt_channel_id = yt_channel_info.get("id")
        snippet = yt_channel_info.get("snippet", {})
        yt_title = snippet.get("title", "")
        yt_custom_url = snippet.get("customUrl", "")
        yt_thumb = snippet.get("thumbnails", {}).get("default", {}).get("url", "")
        account_email = None

        # Fetch user email if available
        try:
            oauth2_client = build("oauth2", "v2", credentials=creds, cache_discovery=False)
            user_info = oauth2_client.userinfo().get().execute()
            account_email = user_info.get("email")
        except Exception as e:
            logger.warning(f"Could not retrieve user email during OAuth exchange: {e}")

        # Update Channel record
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await db.execute(stmt)
        channel = res.scalars().first()
        if not channel:
            raise ValueError(f"Channel with ID '{channel_id}' not found.")

        channel.youtube_channel_id = yt_channel_id
        # Optionally update name if blank or default
        if not channel.name or channel.name.startswith("New Channel"):
            channel.name = yt_title

        # Encrypt tokens and save OAuthCredential
        cred_stmt = select(OAuthCredential).where(
            OAuthCredential.channel_id == channel_id,
            OAuthCredential.service_type == "youtube_channel"
        )
        cred_res = await db.execute(cred_stmt)
        oauth_cred = cred_res.scalars().first()

        encrypted_refresh = encrypt_secret(creds.refresh_token or "")
        encrypted_access = encrypt_secret(creds.token or "")

        if not oauth_cred:
            oauth_cred = OAuthCredential(
                service_type="youtube_channel",
                channel_id=channel_id,
                account_email=account_email,
                encrypted_refresh_token=encrypted_refresh,
                encrypted_access_token=encrypted_access,
                token_expiry=creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
                scopes=YOUTUBE_SCOPES,
                is_valid=True
            )
            db.add(oauth_cred)
        else:
            if creds.refresh_token:
                oauth_cred.encrypted_refresh_token = encrypted_refresh
            oauth_cred.encrypted_access_token = encrypted_access
            oauth_cred.token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
            oauth_cred.account_email = account_email or oauth_cred.account_email
            oauth_cred.is_valid = True
            oauth_cred.last_error = None

        await db.commit()
        await db.refresh(channel)

        return {
            "channel_id": channel.id,
            "youtube_channel_id": yt_channel_id,
            "youtube_title": yt_title,
            "youtube_thumbnail": yt_thumb,
            "account_email": account_email
        }

    @classmethod
    async def get_authenticated_service(
        cls,
        channel_id: str,
        db: AsyncSession
    ):
        """
        Retrieves YouTube API client v3 for a channel with automatic token refresh.
        """
        stmt = select(OAuthCredential).where(
            OAuthCredential.channel_id == channel_id,
            OAuthCredential.service_type == "youtube_channel",
            OAuthCredential.is_valid == True
        )
        res = await db.execute(stmt)
        oauth_cred = res.scalars().first()
        if not oauth_cred:
            raise ValueError(f"No valid YouTube OAuth credentials found for channel '{channel_id}'.")

        refresh_token = decrypt_secret(oauth_cred.encrypted_refresh_token)
        access_token = decrypt_secret(oauth_cred.encrypted_access_token) if oauth_cred.encrypted_access_token else None

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=YOUTUBE_SCOPES
        )

        # Refresh token if expired
        if creds.expired or not creds.valid:
            try:
                creds.refresh(Request())
                oauth_cred.encrypted_access_token = encrypt_secret(creds.token or "")
                oauth_cred.token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
                oauth_cred.is_valid = True
                oauth_cred.last_error = None
                await db.commit()
                logger.info(f"Refreshed YouTube access token for channel {channel_id}.")
            except Exception as e:
                oauth_cred.is_valid = False
                oauth_cred.last_error = str(e)
                await db.commit()
                raise ValueError(f"Failed to refresh YouTube OAuth token for channel {channel_id}: {e}")

        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    @classmethod
    async def disconnect_channel(cls, channel_id: str, db: AsyncSession):
        """Revokes and removes YouTube OAuth connection for a channel"""
        stmt = select(OAuthCredential).where(
            OAuthCredential.channel_id == channel_id,
            OAuthCredential.service_type == "youtube_channel"
        )
        res = await db.execute(stmt)
        creds = res.scalars().all()
        for c in creds:
            await db.delete(c)

        ch_stmt = select(Channel).where(Channel.id == channel_id)
        ch_res = await db.execute(ch_stmt)
        channel = ch_res.scalars().first()
        if channel:
            channel.youtube_channel_id = None

        await db.commit()
        logger.info(f"Disconnected YouTube OAuth for channel {channel_id}.")

    @classmethod
    async def get_connection_status(
        cls,
        channel_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Returns connection status, quota usage, and channel info"""
        stmt = select(Channel).where(Channel.id == channel_id)
        res = await db.execute(stmt)
        channel = res.scalars().first()
        if not channel:
            raise ValueError(f"Channel with ID '{channel_id}' not found.")

        cred_stmt = select(OAuthCredential).where(
            OAuthCredential.channel_id == channel_id,
            OAuthCredential.service_type == "youtube_channel"
        )
        cred_res = await db.execute(cred_stmt)
        oauth_cred = cred_res.scalars().first()

        quota_used = await YouTubeQuotaTracker.get_used_quota(channel_id, db)

        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "is_connected": bool(oauth_cred and oauth_cred.is_valid and channel.youtube_channel_id),
            "youtube_channel_id": channel.youtube_channel_id,
            "account_email": oauth_cred.account_email if oauth_cred else None,
            "token_expiry": oauth_cred.token_expiry.isoformat() if (oauth_cred and oauth_cred.token_expiry) else None,
            "daily_quota_used": quota_used,
            "daily_quota_limit": 10000,
            "last_error": oauth_cred.last_error if oauth_cred else None
        }
