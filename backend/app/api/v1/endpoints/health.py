import os
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.health import SystemHealthResponse, StorageHealth

router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"], response_model=SystemHealthResponse)
async def get_system_health(db: AsyncSession = Depends(get_db)):
    # 1. Database Check
    db_status = "HEALTHY"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "ERROR"

    # 2. Disk Space Check
    free_gb = None
    total_gb = None
    try:
        temp_path = os.path.abspath(settings.TEMP_STORAGE_PATH)
        os.makedirs(temp_path, exist_ok=True)
        usage = shutil.disk_usage(temp_path)
        free_gb = round(usage.free / (1024 ** 3), 2)
        total_gb = round(usage.total / (1024 ** 3), 2)
    except Exception:
        pass

    storage_health = StorageHealth(
        provider="Google Drive (Cloud)",
        connected=True,
        free_space_gb=free_gb,
        total_space_gb=total_gb
    )

    overall_status = "HEALTHY" if db_status == "HEALTHY" else "DEGRADED"

    return SystemHealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        database=db_status,
        scheduler="INITIALIZING", # Will connect with APScheduler in Phase 5
        storage=storage_health,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
