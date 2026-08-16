import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.services.youtube.uploader import YouTubeUploaderService
from app.core.logging import logger


class UploadWorkerPool:
    _instance: Optional['UploadWorkerPool'] = None
    
    def __init__(self, max_concurrent: int = 3, per_channel_concurrent: int = 1, cooldown_seconds: int = 5):
        self.max_concurrent = max_concurrent
        self.per_channel_concurrent = per_channel_concurrent
        self.cooldown_seconds = cooldown_seconds
        
        self._global_semaphore = asyncio.Semaphore(self.max_concurrent)
        self._channel_locks: Dict[str, asyncio.Lock] = {}
        self._channel_last_upload_time: Dict[str, float] = {}
        self._running_jobs: Dict[str, Dict[str, Any]] = {} # job_id -> metadata
        self._is_paused = False

    @classmethod
    def get_instance(cls) -> 'UploadWorkerPool':
        if cls._instance is None:
            cls._instance = UploadWorkerPool(
                max_concurrent=settings.MAX_CONCURRENT_UPLOADS,
                per_channel_concurrent=settings.PER_CHANNEL_MAX_CONCURRENT,
                cooldown_seconds=settings.CHANNEL_UPLOAD_COOLDOWN_SECONDS
            )
        return cls._instance

    def _get_channel_lock(self, channel_id: str) -> asyncio.Lock:
        if channel_id not in self._channel_locks:
            self._channel_locks[channel_id] = asyncio.Lock()
        return self._channel_locks[channel_id]

    async def submit_upload(
        self,
        occurrence_id: str,
        title_override: Optional[str] = None,
        description_override: Optional[str] = None,
        tags_override: Optional[list] = None,
        category_id_override: Optional[str] = None,
        privacy_status_override: Optional[str] = None,
        publish_at: Optional[datetime] = None,
        dry_run: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Submits an upload job through the concurrency-controlled worker pool.
        Acquires global slot and per-channel lock, enforces cooldown, and executes pipeline.
        """
        if self._is_paused:
            logger.warning(f"UploadWorkerPool is currently paused. Occurrence '{occurrence_id}' queued.")

        # Resolve channel_id from occurrence
        channel_id = "unknown"
        if db:
            occ = await db.get(ScheduleOccurrence, occurrence_id)
            if occ:
                channel_id = occ.channel_id
        else:
            async with AsyncSessionLocal() as session:
                occ = await session.get(ScheduleOccurrence, occurrence_id)
                if occ:
                    channel_id = occ.channel_id

        channel_lock = self._get_channel_lock(channel_id)

        # 1. Acquire Per-Channel Mutex Lock (ensures 1 upload at a time per channel)
        async with channel_lock:
            # Enforce cooldown delay between successive uploads on the same channel
            last_time = self._channel_last_upload_time.get(channel_id, 0.0)
            elapsed = time.time() - last_time
            if elapsed < self.cooldown_seconds:
                sleep_time = self.cooldown_seconds - elapsed
                logger.info(f"Enforcing channel '{channel_id}' rate limit cooldown: sleeping {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)

            # 2. Acquire Global Concurrency Semaphore Slot (limits total system concurrent uploads)
            async with self._global_semaphore:
                self._running_jobs[occurrence_id] = {
                    "channel_id": channel_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "dry_run": dry_run
                }

                try:
                    logger.info(f"WorkerPool acquired slot: executing upload for occurrence '{occurrence_id}' on channel '{channel_id}' (Active: {len(self._running_jobs)}/{self.max_concurrent})...")
                    
                    result = await YouTubeUploaderService.run_upload_job(
                        occurrence_id=occurrence_id,
                        title_override=title_override,
                        description_override=description_override,
                        tags_override=tags_override,
                        category_id_override=category_id_override,
                        privacy_status_override=privacy_status_override,
                        publish_at=publish_at,
                        dry_run=dry_run,
                        db=db
                    )
                    return result
                finally:
                    self._channel_last_upload_time[channel_id] = time.time()
                    self._running_jobs.pop(occurrence_id, None)
                    logger.info(f"WorkerPool released slot for occurrence '{occurrence_id}' (Remaining active: {len(self._running_jobs)}).")

    def pause(self):
        self._is_paused = True
        logger.info("UploadWorkerPool paused.")

    def resume(self):
        self._is_paused = False
        logger.info("UploadWorkerPool resumed.")

    def get_status(self) -> Dict[str, Any]:
        return {
            "max_concurrent_uploads": self.max_concurrent,
            "per_channel_max_concurrent": self.per_channel_concurrent,
            "channel_cooldown_seconds": self.cooldown_seconds,
            "active_uploads_count": len(self._running_jobs),
            "is_paused": self._is_paused,
            "running_jobs": list(self._running_jobs.values()),
            "active_channels": list(set(job["channel_id"] for job in self._running_jobs.values()))
        }
