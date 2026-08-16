from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.services.youtube.youtube_oauth import YouTubeOAuthService

router = APIRouter()


@router.get("/auth-url")
async def get_youtube_auth_url(
    channel_id: str = Query(..., description="ID of channel to connect"),
    redirect_uri: Optional[str] = Query(default=None)
):
    """
    Generates the Google OAuth authorization URL for connecting a YouTube Channel.
    """
    uri = redirect_uri or settings.YOUTUBE_REDIRECT_URI or "http://localhost:8000/api/v1/youtube/oauth/callback"

    try:
        auth_url = YouTubeOAuthService.generate_auth_url(channel_id=channel_id, redirect_uri=uri)
        return {"auth_url": auth_url, "channel_id": channel_id, "redirect_uri": uri}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate YouTube authorization URL: {e}"
        )


@router.get("/callback")
@router.get("/oauth/callback")
async def youtube_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None), # channel_id passed in state
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 callback from Google. Exchanges code for tokens and redirects to frontend.
    """
    frontend_channels_url = "http://localhost:5173/channels"

    if error:
        return RedirectResponse(
            url=f"{frontend_channels_url}?youtube_error={error}"
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_channels_url}?youtube_error=missing_code_or_state"
        )

    channel_id = state
    redirect_uri = settings.YOUTUBE_REDIRECT_URI or "http://localhost:8000/api/v1/youtube/oauth/callback"

    try:
        logger.info(f"Exchanging YouTube OAuth code for channel {channel_id} (redirect_uri: {redirect_uri})...")
        result = await YouTubeOAuthService.exchange_code_for_tokens(
            channel_id=channel_id,
            code=code,
            redirect_uri=redirect_uri,
            db=db
        )
        logger.info(f"YouTube OAuth success for channel {channel_id}: {result}")
        return RedirectResponse(
            url=f"{frontend_channels_url}?youtube_connected=true&channel_id={channel_id}&title={result.get('youtube_title')}"
        )
    except Exception as e:
        logger.error(f"YouTube OAuth callback error for channel {channel_id}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_channels_url}?youtube_error={str(e)}"
        )


@router.get("/{channel_id}/status")
async def get_youtube_connection_status(
    channel_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Inspects YouTube connection status, quota consumption, and channel info.
    """
    try:
        return await YouTubeOAuthService.get_connection_status(channel_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{channel_id}/disconnect")
async def disconnect_youtube_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnects and removes YouTube OAuth tokens for a channel.
    """
    try:
        await YouTubeOAuthService.disconnect_channel(channel_id, db)
        return {"message": f"YouTube channel disconnected successfully.", "channel_id": channel_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/audit-copyright")
async def audit_copyright(
    channel_id: Optional[str] = Query(default=None, description="Optional channel ID filter"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Audits recently uploaded YouTube videos for copyright strikes, claims, and policy rejections.
    Automatically deletes flagged videos from YouTube, disables source files, and triggers replacement uploads.
    """
    from app.services.youtube.copyright_guard import CopyrightGuardService
    try:
        return await CopyrightGuardService.audit_recent_uploads(channel_id=channel_id, limit=limit, db=db)
    except Exception as e:
        logger.error(f"Failed to run copyright audit: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/occurrences/{occurrence_id}/audit")
async def audit_single_occurrence(
    occurrence_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Audits a specific upload occurrence for copyright/strike status.
    """
    from app.services.youtube.copyright_guard import CopyrightGuardService
    try:
        return await CopyrightGuardService.audit_occurrence(occurrence_id=occurrence_id, db=db)
    except Exception as e:
        logger.error(f"Failed to audit occurrence {occurrence_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/occurrences/{occurrence_id}/delete-and-replace")
async def delete_and_replace_occurrence(
    occurrence_id: str,
    reason: str = Query(default="Manual Request", description="Reason for deletion"),
    auto_replace: bool = Query(default=True, description="Whether to upload replacement from schedule"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually deletes a video from YouTube, marks the occurrence as COPYRIGHT_DELETED,
    and optionally triggers an immediate replacement upload for that schedule.
    """
    from app.services.youtube.copyright_guard import CopyrightGuardService
    try:
        return await CopyrightGuardService.handle_flagged_video(
            occurrence_id=occurrence_id,
            flag_reason=reason,
            auto_replace=auto_replace,
            db=db
        )
    except Exception as e:
        logger.error(f"Failed to delete and replace occurrence {occurrence_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
