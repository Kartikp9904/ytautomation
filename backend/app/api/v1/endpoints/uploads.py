import uuid
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db, AsyncSessionLocal
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.upload import (
    ManualUploadRequest,
    ManualUploadResponse,
    UploadJobResponse,
    UploadJobListResponse
)
from app.services.worker.worker_pool import UploadWorkerPool
from app.services.worker.recovery import ReconciliationService
from app.core.logging import logger

router = APIRouter()


async def _run_background_upload(
    occurrence_id: str,
    title_override: Optional[str] = None,
    description_override: Optional[str] = None,
    tags_override: Optional[list] = None,
    category_id_override: Optional[str] = None,
    privacy_status_override: Optional[str] = None
):
    try:
        worker_pool = UploadWorkerPool.get_instance()
        await worker_pool.submit_upload(
            occurrence_id=occurrence_id,
            title_override=title_override,
            description_override=description_override,
            tags_override=tags_override,
            category_id_override=category_id_override,
            privacy_status_override=privacy_status_override
        )
    except Exception as e:
        logger.error(f"Background upload task failed for occurrence '{occurrence_id}': {e}")


@router.post("/manual", response_model=ManualUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_now(
    data: ManualUploadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers an immediate 'Upload Now' pipeline for any video library asset
    routed through the concurrency-controlled worker pool.
    """
    # 1. Verify channel and video
    ch_res = await db.execute(select(Channel).where(Channel.id == data.channel_id))
    channel = ch_res.scalars().first()
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel '{data.channel_id}' not found.")

    v_res = await db.execute(select(Video).where(Video.id == data.video_id))
    video = v_res.scalars().first()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video '{data.video_id}' not found.")

    # 2. Create ScheduleOccurrence
    idempotency_key = f"manual:{data.video_id}:{uuid.uuid4().hex}"
    now_utc = datetime.now(timezone.utc)
    
    occurrence = ScheduleOccurrence(
        schedule_id=None,
        channel_id=data.channel_id,
        video_id=data.video_id,
        idempotency_key=idempotency_key,
        scheduled_publish_time=now_utc,
        target_upload_time=now_utc,
        status="QUEUED"
    )
    db.add(occurrence)
    await db.commit()
    await db.refresh(occurrence)

    # 3. Create UploadJob
    job = UploadJob(
        occurrence_id=occurrence.id,
        status="QUEUED"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 4. Enqueue in BackgroundTasks
    background_tasks.add_task(
        _run_background_upload,
        occurrence_id=occurrence.id,
        title_override=data.title,
        description_override=data.description,
        tags_override=data.tags,
        category_id_override=data.category_id,
        privacy_status_override=data.privacy_status
    )

    return ManualUploadResponse(
        message=f"Upload job queued for video '{video.filename}'.",
        occurrence_id=occurrence.id,
        job_id=job.id,
        status="QUEUED"
    )


@router.post("/{job_id}/retry", response_model=Dict[str, Any])
async def retry_failed_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually retries a failed or retrying upload job.
    """
    stmt = select(UploadJob).where(UploadJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Upload job '{job_id}' not found.")

    occ = await db.get(ScheduleOccurrence, job.occurrence_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Associated occurrence not found.")

    job.status = "QUEUED"
    job.error_message = None
    occ.status = "QUEUED"
    occ.error_message = None
    await db.commit()

    background_tasks.add_task(_run_background_upload, occurrence_id=occ.id)

    return {
        "message": f"Retry queued for upload job '{job.id}'.",
        "job_id": job.id,
        "occurrence_id": occ.id,
        "status": "QUEUED"
    }


@router.post("/reconcile", response_model=Dict[str, Any])
async def run_crash_reconciliation(db: AsyncSession = Depends(get_db)):
    """
    Manually triggers crash reconciliation scan for any stuck jobs.
    """
    summary = await ReconciliationService.reconcile_orphaned_jobs(db=db)
    return summary


@router.get("/queue/status", response_model=Dict[str, Any])
async def get_worker_pool_status():
    """
    Returns live diagnostics of the upload worker pool, active slots, and per-channel concurrency.
    """
    return UploadWorkerPool.get_instance().get_status()


@router.post("/queue/pause")
async def pause_worker_queue():
    UploadWorkerPool.get_instance().pause()
    return {"message": "Upload worker pool paused."}


@router.post("/queue/resume")
async def resume_worker_queue():
    UploadWorkerPool.get_instance().resume()
    return {"message": "Upload worker pool resumed."}


@router.get("/{job_id}", response_model=UploadJobResponse)
async def get_upload_job_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UploadJob, ScheduleOccurrence.youtube_video_id)\
        .outerjoin(ScheduleOccurrence, UploadJob.occurrence_id == ScheduleOccurrence.id)\
        .where(UploadJob.id == job_id)

    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Upload job '{job_id}' not found.")

    job, yt_id = row
    percent = 0.0
    if job.total_bytes > 0:
        percent = min(100.0, round((job.bytes_uploaded / job.total_bytes) * 100, 1))

    return UploadJobResponse(
        id=job.id,
        occurrence_id=job.occurrence_id,
        status=job.status,
        bytes_downloaded=job.bytes_downloaded,
        bytes_uploaded=job.bytes_uploaded,
        total_bytes=job.total_bytes,
        progress_percentage=percent,
        youtube_video_id=yt_id,
        youtube_url=f"https://youtu.be/{yt_id}" if yt_id else None,
        error_type=job.error_type,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.get("", response_model=UploadJobListResponse)
async def list_upload_jobs(
    status_filter: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UploadJob, ScheduleOccurrence.youtube_video_id)\
        .outerjoin(ScheduleOccurrence, UploadJob.occurrence_id == ScheduleOccurrence.id)

    if status_filter:
        stmt = stmt.where(UploadJob.status == status_filter.upper())

    stmt = stmt.order_by(desc(UploadJob.created_at)).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for job, yt_id in rows:
        percent = 0.0
        if job.total_bytes > 0:
            percent = min(100.0, round((job.bytes_uploaded / job.total_bytes) * 100, 1))

        items.append(UploadJobResponse(
            id=job.id,
            occurrence_id=job.occurrence_id,
            status=job.status,
            bytes_downloaded=job.bytes_downloaded,
            bytes_uploaded=job.bytes_uploaded,
            total_bytes=job.total_bytes,
            progress_percentage=percent,
            youtube_video_id=yt_id,
            youtube_url=f"https://youtu.be/{yt_id}" if yt_id else None,
            error_type=job.error_type,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at
        ))

    return UploadJobListResponse(total=len(items), items=items)
