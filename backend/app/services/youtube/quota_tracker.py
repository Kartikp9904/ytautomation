from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.setting import SystemSetting
from app.core.logging import logger

# YouTube API Quota costs (Units)
QUOTA_VIDEO_UPLOAD = 1600
QUOTA_VIDEO_UPDATE = 50
QUOTA_THUMBNAIL_SET = 50
QUOTA_READ_LIST = 1
DAILY_QUOTA_LIMIT = 10000


class YouTubeQuotaTracker:
    @classmethod
    def _get_key(cls, channel_id: str, target_date: Optional[datetime] = None) -> str:
        d = target_date or datetime.now(timezone.utc)
        date_str = d.strftime("%Y-%m-%d")
        return f"yt_quota:{channel_id}:{date_str}"

    @classmethod
    async def get_used_quota(cls, channel_id: str, db: AsyncSession) -> int:
        key = cls._get_key(channel_id)
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        res = await db.execute(stmt)
        setting = res.scalars().first()
        if setting and setting.value:
            try:
                return int(setting.value)
            except ValueError:
                return 0
        return 0

    @classmethod
    async def record_quota_usage(
        cls,
        channel_id: str,
        units: int,
        db: AsyncSession
    ) -> int:
        key = cls._get_key(channel_id)
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        res = await db.execute(stmt)
        setting = res.scalars().first()

        current_val = 0
        if setting and setting.value:
            try:
                current_val = int(setting.value)
            except ValueError:
                current_val = 0

        new_val = current_val + units

        if setting:
            setting.value = str(new_val)
        else:
            setting = SystemSetting(key=key, value=str(new_val))
            db.add(setting)

        await db.commit()
        logger.info(f"Recorded {units} YouTube quota units for channel {channel_id}. Total today: {new_val}/{DAILY_QUOTA_LIMIT}")
        return new_val

    @classmethod
    async def can_upload_video(cls, channel_id: str, db: AsyncSession) -> Tuple[bool, int, str]:
        """Returns (can_upload, units_used, message)"""
        used = await cls.get_used_quota(channel_id, db)
        projected = used + QUOTA_VIDEO_UPLOAD

        if projected > DAILY_QUOTA_LIMIT:
            msg = f"Daily YouTube API quota limit would be exceeded ({projected}/{DAILY_QUOTA_LIMIT} units). Upload postponed."
            logger.warning(msg)
            return False, used, msg

        return True, used, f"Quota OK: {used}/{DAILY_QUOTA_LIMIT} units used."
