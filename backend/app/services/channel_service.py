import zoneinfo
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.channel import Channel
from app.models.schedule import Schedule
from app.models.video import Video
from app.models.oauth import OAuthCredential
from app.schemas.channel import ChannelCreate, ChannelUpdate, ChannelResponse, TimezoneOption


class ChannelService:
    @staticmethod
    def get_supported_timezones() -> List[TimezoneOption]:
        """
        Return a curated and comprehensive list of IANA timezones with current UTC offsets.
        """
        popular_zones = [
            "Asia/Kolkata",
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Dubai",
            "Asia/Singapore",
            "Asia/Tokyo",
            "Australia/Sydney",
            "Pacific/Auckland",
            "America/Sao_Paulo",
            "Africa/Cairo",
        ]
        
        # Add all available timezones sorted
        all_zones = sorted(list(zoneinfo.available_timezones()))
        ordered_zones = []
        for zone in popular_zones:
            if zone in all_zones:
                ordered_zones.append(zone)
        for zone in all_zones:
            if zone not in ordered_zones:
                ordered_zones.append(zone)

        now = datetime.now(timezone.utc)
        result = []
        for tz_name in ordered_zones:
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
                local_time = now.astimezone(tz)
                offset = local_time.strftime("%z")
                formatted_offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC+00:00"
                result.append(TimezoneOption(
                    name=tz_name,
                    label=f"{tz_name} ({formatted_offset})",
                    offset=formatted_offset
                ))
            except Exception:
                continue
        return result

    @staticmethod
    async def get_channel_with_stats(db: AsyncSession, channel: Channel) -> ChannelResponse:
        # Count active schedules
        sched_stmt = select(func.count(Schedule.id)).where(Schedule.channel_id == channel.id)
        sched_res = await db.execute(sched_stmt)
        schedules_count = sched_res.scalar() or 0

        # Count videos
        video_stmt = select(func.count(Video.id)).where(Video.channel_id == channel.id)
        video_res = await db.execute(video_stmt)
        videos_count = video_res.scalar() or 0

        # Check OAuth connection
        oauth_stmt = select(OAuthCredential).where(
            OAuthCredential.channel_id == channel.id,
            OAuthCredential.service_type == "youtube_channel",
            OAuthCredential.is_valid == True
        )
        oauth_res = await db.execute(oauth_stmt)
        is_connected = oauth_res.scalars().first() is not None

        return ChannelResponse(
            id=channel.id,
            name=channel.name,
            youtube_channel_id=channel.youtube_channel_id,
            timezone=channel.timezone,
            enabled=channel.enabled,
            default_title_template=channel.default_title_template,
            default_description_template=channel.default_description_template,
            default_tags=channel.default_tags or [],
            default_category_id=channel.default_category_id or "22",
            default_privacy_status=channel.default_privacy_status,
            default_thumbnail_storage_id=channel.default_thumbnail_storage_id,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            schedules_count=schedules_count,
            videos_count=videos_count,
            is_connected=is_connected
        )

    @classmethod
    async def list_channels(cls, db: AsyncSession) -> Tuple[int, List[ChannelResponse]]:
        stmt = select(Channel).order_by(Channel.name.asc())
        result = await db.execute(stmt)
        channels = result.scalars().all()
        
        channel_responses = []
        for channel in channels:
            res = await cls.get_channel_with_stats(db, channel)
            channel_responses.append(res)
            
        return len(channel_responses), channel_responses

    @classmethod
    async def get_channel_by_id(cls, db: AsyncSession, channel_id: str) -> Optional[ChannelResponse]:
        stmt = select(Channel).where(Channel.id == channel_id)
        result = await db.execute(stmt)
        channel = result.scalars().first()
        if not channel:
            return None
        return await cls.get_channel_with_stats(db, channel)

    @classmethod
    async def create_channel(cls, db: AsyncSession, data: ChannelCreate) -> ChannelResponse:
        channel = Channel(
            name=data.name,
            timezone=data.timezone,
            enabled=data.enabled,
            default_title_template=data.default_title_template,
            default_description_template=data.default_description_template,
            default_tags=data.default_tags,
            default_category_id=data.default_category_id,
            default_privacy_status=data.default_privacy_status
        )
        db.add(channel)
        await db.commit()
        await db.refresh(channel)
        return await cls.get_channel_with_stats(db, channel)

    @classmethod
    async def update_channel(cls, db: AsyncSession, channel_id: str, data: ChannelUpdate) -> Optional[ChannelResponse]:
        stmt = select(Channel).where(Channel.id == channel_id)
        result = await db.execute(stmt)
        channel = result.scalars().first()
        if not channel:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        for field, val in update_dict.items():
            setattr(channel, field, val)

        await db.commit()
        await db.refresh(channel)
        return await cls.get_channel_with_stats(db, channel)

    @classmethod
    async def toggle_channel(cls, db: AsyncSession, channel_id: str) -> Optional[ChannelResponse]:
        stmt = select(Channel).where(Channel.id == channel_id)
        result = await db.execute(stmt)
        channel = result.scalars().first()
        if not channel:
            return None

        channel.enabled = not channel.enabled
        await db.commit()
        await db.refresh(channel)
        return await cls.get_channel_with_stats(db, channel)

    @classmethod
    async def delete_channel(cls, db: AsyncSession, channel_id: str) -> bool:
        stmt = select(Channel).where(Channel.id == channel_id)
        result = await db.execute(stmt)
        channel = result.scalars().first()
        if not channel:
            return False

        await db.delete(channel)
        await db.commit()
        return True
