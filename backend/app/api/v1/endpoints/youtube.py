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
@router.get("/channels/oauth/youtube/callback")
async def youtube_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None), # channel_id passed in state
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 callback from Google. Exchanges code for tokens and redirects to frontend.
    """
    frontend_channels_url = "/channels"

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


@router.get("/quota-summary")
async def get_quota_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns global and per-channel YouTube API quota (tokens) tracking information.
    """
    from app.services.youtube.quota_tracker import YouTubeQuotaTracker, DAILY_QUOTA_LIMIT, QUOTA_VIDEO_UPLOAD
    from app.models.channel import Channel
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    # 1. Fetch all channels
    ch_stmt = select(Channel)
    ch_res = await db.execute(ch_stmt)
    channels = ch_res.scalars().all()

    channel_breakdown = []
    total_used = 0

    for ch in channels:
        used = await YouTubeQuotaTracker.get_used_quota(ch.id, db)
        total_used += used
        channel_breakdown.append({
            "channel_id": ch.id,
            "channel_name": ch.name,
            "used_units": used,
            "remaining_units": max(0, DAILY_QUOTA_LIMIT - used),
            "estimated_uploads_remaining": max(0, (DAILY_QUOTA_LIMIT - used) // QUOTA_VIDEO_UPLOAD)
        })

    # Calculate UTC midnight reset
    now_utc = datetime.now(timezone.utc)
    tomorrow_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_reset = int((tomorrow_utc - now_utc).total_seconds())

    remaining_units = max(0, DAILY_QUOTA_LIMIT - total_used)
    percent_used = round((total_used / DAILY_QUOTA_LIMIT) * 100, 1) if DAILY_QUOTA_LIMIT > 0 else 0

    return {
        "daily_limit": DAILY_QUOTA_LIMIT,
        "total_used_today": total_used,
        "total_remaining_today": remaining_units,
        "percent_used": min(100.0, percent_used),
        "estimated_uploads_remaining": remaining_units // QUOTA_VIDEO_UPLOAD,
        "seconds_until_reset": seconds_until_reset,
        "resets_at": tomorrow_utc.isoformat(),
        "channels": channel_breakdown
    }

