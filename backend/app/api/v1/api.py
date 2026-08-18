from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, channels, drive, videos, folders, schedules, youtube, uploads, presets

api_router = APIRouter()

api_router.include_router(health.router, tags=["System & Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])
api_router.include_router(drive.router, prefix="/drive", tags=["Google Drive & Storage"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(folders.router, prefix="/folders", tags=["Folders"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
api_router.include_router(youtube.router, prefix="/youtube", tags=["YouTube OAuth & API"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["YouTube Uploads & Queue"])
api_router.include_router(presets.router, prefix="/presets", tags=["Content Niche Presets & Hooks"])
