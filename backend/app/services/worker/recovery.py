import os
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.occurrence import ScheduleOccurrence
from app.models.upload_job import UploadJob
from app.core.logging import logger


class ErrorClassifier:
    TRANSIENT_KEYWORDS = [
        "timeout",
        "connection reset",
        "connection refused",
        "temporary failure",
        "500 internal server error",
        "502 bad gateway",
        "503 service unavailable",
        "504 gateway timeout",
        "rate limit",
        "429",
        "quota units limit exceeded temporarily",
        "chunk upload timeout",
        "network unreachable"
    ]

    FATAL_KEYWORDS = [
        "quotaexceeded",
        "daily quota",
        "invalid_grant",
        "token has been revoked",
        "unauthorized",
        "category not found",
        "invalid category",
        "badrequest",
        "video not found"
    ]

    @classmethod
    def classify_error(cls, error_str: str) -> Tuple[str, bool]:
        """
        Returns (error_type, is_retryable)
        """
        err_lower = error_str.lower()
        
        # Check fatal first
        for fatal_kw in cls.FATAL_KEYWORDS:
            if fatal_kw in err_lower:
                return ("PERMANENT", False)

        # Check transient keywords
        for trans_kw in cls.TRANSIENT_KEYWORDS:
            if trans_kw in err_lower:
                return ("TRANSIENT", True)

        # Default standard errors to retryable if under max attempts
        return ("TRANSIENT", True)


class RetryEngine:
    BASE_DELAY_SECONDS = 10
    MAX_DELAY_SECONDS = 300

    @classmethod
    def calculate_backoff(cls, retry_count: int) -> int:
        """
        Calculates exponential backoff with jitter: base * 2^retries + random(1, 5)
        """
        backoff = cls.BASE_DELAY_SECONDS * (2 ** retry_count)
        jitter = random.uniform(1.0, 5.0)
        total_delay = int(min(cls.MAX_DELAY_SECONDS, backoff + jitter))
        return total_delay


class ReconciliationService:
    @classmethod
    async def reconcile_orphaned_jobs(cls, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Scans for orphaned or stuck upload jobs after a crash or system reboot.
        Cleans up abandoned temp files on disk and safely resets retryable jobs to QUEUED.
        """
        async def _run_reconciliation(session: AsyncSession) -> Dict[str, Any]:
            logger.info("ReconciliationService: Scanning for stuck or orphaned upload jobs...")

            stmt = select(UploadJob).where(
                UploadJob.status.in_(["IN_PROGRESS", "DOWNLOADING", "UPLOADING", "RETRYING"])
            )
            res = await session.execute(stmt)
            stuck_jobs = res.scalars().all()

            reconciled_count = 0
            cleaned_files_count = 0
            failed_count = 0

            for job in stuck_jobs:
                # 1. Clean up stale temporary files on disk
                if job.temp_file_path and os.path.exists(job.temp_file_path):
                    try:
                        os.remove(job.temp_file_path)
                        cleaned_files_count += 1
                        logger.info(f"Reconciliation: Removed orphaned temp file '{job.temp_file_path}'")
                    except Exception as err:
                        logger.warning(f"Could not remove stale temp file: {err}")

                job.temp_file_path = None

                # 2. Check retry count threshold
                occ = await session.get(ScheduleOccurrence, job.occurrence_id)

                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = "QUEUED"
                    job.error_type = "RECOVERED_FROM_CRASH"
                    job.error_message = f"Recovered after server restart. Enqueued for retry attempt {job.retry_count}/{job.max_retries}."
                    
                    if occ:
                        occ.status = "QUEUED"
                        occ.error_message = job.error_message

                    reconciled_count += 1
                    logger.info(f"Reconciliation: Re-queued stuck job '{job.id}' (Attempt {job.retry_count}/{job.max_retries})")
                else:
                    job.status = "FAILED"
                    job.error_type = "MAX_RETRIES_EXCEEDED"
                    job.error_message = "Max upload retry attempts exceeded following crash recovery."
                    job.completed_at = datetime.now(timezone.utc)

                    if occ:
                        occ.status = "FAILED"
                        occ.error_message = job.error_message

                    failed_count += 1
                    logger.warning(f"Reconciliation: Job '{job.id}' failed permanently (Max retries exceeded).")

            await session.commit()
            summary = {
                "total_stuck_found": len(stuck_jobs),
                "reconciled_to_queue": reconciled_count,
                "permanently_failed": failed_count,
                "cleaned_temp_files": cleaned_files_count
            }
            logger.info(f"ReconciliationService summary: {summary}")
            return summary

        if db:
            return await _run_reconciliation(db)
        else:
            async with AsyncSessionLocal() as session:
                return await _run_reconciliation(session)
