import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.video import Video
from app.models.folder import ContentFolder
from app.models.schedule import Schedule
from app.models.channel import Channel
from app.services.metadata.content_presets import ContentPresetService


class ResolvedMetadata:
    def __init__(
        self,
        title: str,
        description: str,
        tags: List[str],
        category_id: str,
        privacy_status: str,
        thumbnail_storage_id: Optional[str] = None,
        source_hierarchy: Optional[Dict[str, str]] = None,
        made_for_kids: bool = False,
        age_restricted: bool = False,
        default_language: Optional[str] = None,
        default_audio_language: Optional[str] = None,
        contains_synthetic_media: bool = False
    ):
        self.title = title
        self.description = description
        self.tags = tags
        self.category_id = category_id
        self.privacy_status = privacy_status
        self.thumbnail_storage_id = thumbnail_storage_id
        self.source_hierarchy = source_hierarchy or {}
        self.made_for_kids = made_for_kids
        self.age_restricted = age_restricted
        self.default_language = default_language
        self.default_audio_language = default_audio_language
        self.contains_synthetic_media = contains_synthetic_media

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category_id": self.category_id,
            "privacy_status": self.privacy_status,
            "thumbnail_storage_id": self.thumbnail_storage_id,
            "source_hierarchy": self.source_hierarchy,
            "made_for_kids": self.made_for_kids,
            "age_restricted": self.age_restricted,
            "default_language": self.default_language,
            "default_audio_language": self.default_audio_language,
            "contains_synthetic_media": self.contains_synthetic_media
        }


class MetadataEngine:
    @classmethod
    def substitute_variables(
        cls,
        template: Optional[str],
        channel_name: str,
        video_filename: str,
        target_datetime: datetime,
        category_name: Optional[str] = None,
        preset_category: Optional[str] = None,
        rotation_index: Optional[int] = None
    ) -> str:
        """
        Substitute dynamic variables in title/description templates:
          {channel}      -> Channel display name
          {date}         -> e.g. "15 August 2026"
          {day}          -> e.g. "15" or "01"
          {month}        -> e.g. "August"
          {year}         -> e.g. "2026"
          {filename}     -> Base filename without extension e.g. "15" or "morning_aarti"
          {category}     -> Category name e.g. "Devotional"
          {dynamic_hook} -> Rotated hook for the current day / rotation cycle
          {hook}         -> Rotated hook for the current day / rotation cycle
        """
        if not template:
            return ""

        # Remove extension from filename
        base_filename = video_filename.rsplit(".", 1)[0] if "." in video_filename else video_filename

        # Date formatters
        day_str = target_datetime.strftime("%d") # "15"
        day_num = str(target_datetime.day)       # "15" or "5"
        month_name = target_datetime.strftime("%B") # "August"
        year_str = target_datetime.strftime("%Y")  # "2026"
        formatted_date = f"{day_num} {month_name} {year_str}" # "15 August 2026"

        # Resolve rotating hook & description if requested
        dynamic_hook = ""
        dynamic_desc = ""
        target_preset = preset_category or "mahadev"
        resolved_hook = ContentPresetService.resolve_hook_for_date(
            preset_id=target_preset,
            target_date=target_datetime,
            rotation_index=rotation_index
        )
        if resolved_hook:
            dynamic_hook = resolved_hook

        resolved_desc = ContentPresetService.resolve_description_for_date(
            preset_id=target_preset,
            target_date=target_datetime,
            rotation_index=rotation_index
        )
        if resolved_desc:
            dynamic_desc = resolved_desc

        replacements = {
            "channel": channel_name,
            "date": formatted_date,
            "day": day_str,
            "day_num": day_num,
            "month": month_name,
            "year": year_str,
            "filename": base_filename,
            "category": category_name or "",
            "dynamic_hook": dynamic_hook,
            "hook": dynamic_hook,
            "dynamic_description": dynamic_desc,
            "description": dynamic_desc,
        }

        result = template
        for var_name, var_value in replacements.items():
            pattern = re.compile(rf"\{{{var_name}\}}", re.IGNORECASE)
            result = pattern.sub(var_value, result)

        return result.strip()

    @classmethod
    def resolve_effective_metadata(
        cls,
        video: Video,
        channel: Optional[Channel] = None,
        folder: Optional[ContentFolder] = None,
        schedule: Optional[Schedule] = None,
        target_datetime: Optional[datetime] = None,
        rotation_index: Optional[int] = None
    ) -> ResolvedMetadata:
        """
        Resolve final video title, description, tags, category, privacy, language, audience and thumbnail
        according to the strict priority rules:
          Priority 1: Per-video sidecar metadata (.json) / custom overrides
          Priority 2: Folder default metadata
          Priority 3: Schedule metadata & Preset category
          Priority 4: Channel default metadata
          Priority 5: Global defaults
        """
        dt = target_datetime or datetime.now()
        channel_name = channel.name if channel else "YouTube Channel"
        video_meta = video.custom_metadata or {}
        hierarchy_sources: Dict[str, str] = {}

        preset_category = schedule.preset_category if schedule else None
        preset_info = ContentPresetService.get_preset(preset_category) if preset_category else None

        # 1. RESOLVE TITLE
        raw_title = None
        if video_meta.get("title"):
            raw_title = video_meta["title"]
            hierarchy_sources["title"] = "video_sidecar"
        elif schedule and schedule.title_template:
            raw_title = schedule.title_template
            hierarchy_sources["title"] = "schedule_template"
        elif preset_info and preset_info.get("hooks"):
            raw_title = "{dynamic_hook}"
            hierarchy_sources["title"] = "preset_category_hooks"
        elif folder and folder.default_title_template:
            raw_title = folder.default_title_template
            hierarchy_sources["title"] = "folder_default"
        elif channel and channel.default_title_template:
            raw_title = channel.default_title_template
            hierarchy_sources["title"] = "channel_default"
        else:
            raw_title = "{channel} | {date}"
            hierarchy_sources["title"] = "system_default"

        title = cls.substitute_variables(
            template=raw_title,
            channel_name=channel_name,
            video_filename=video.filename,
            target_datetime=dt,
            preset_category=preset_category,
            rotation_index=rotation_index
        )

        # 2. RESOLVE DESCRIPTION
        raw_desc = None
        if video_meta.get("description"):
            raw_desc = video_meta["description"]
            hierarchy_sources["description"] = "video_sidecar"
        elif schedule and schedule.description_template and schedule.description_template.strip():
            # If user only wrote {dynamic_hook} in description, upgrade to full {dynamic_description}
            if schedule.description_template.strip() in ["{dynamic_hook}", "{hook}"]:
                raw_desc = "{dynamic_description}"
                hierarchy_sources["description"] = "preset_dynamic_description"
            else:
                raw_desc = schedule.description_template
                hierarchy_sources["description"] = "schedule_template"
        elif preset_info:
            raw_desc = "{dynamic_description}"
            hierarchy_sources["description"] = "preset_dynamic_description"
        elif folder and folder.default_description_template:
            raw_desc = folder.default_description_template
            hierarchy_sources["description"] = "folder_default"
        elif channel and channel.default_description_template:
            raw_desc = channel.default_description_template
            hierarchy_sources["description"] = "channel_default"
        else:
            raw_desc = "Uploaded via YouTube Automation Platform for {date}."
            hierarchy_sources["description"] = "system_default"

        description = cls.substitute_variables(
            template=raw_desc,
            channel_name=channel_name,
            video_filename=video.filename,
            target_datetime=dt,
            preset_category=preset_category,
            rotation_index=rotation_index
        )

        # 3. RESOLVE TAGS
        tags: List[str] = []
        if video_meta.get("tags"):
            tags = list(video_meta["tags"])
            hierarchy_sources["tags"] = "video_sidecar"
        elif schedule and schedule.tags and len(schedule.tags) > 0:
            tags = list(schedule.tags)
            hierarchy_sources["tags"] = "schedule_template"
        elif preset_info and preset_info.get("tags") and len(preset_info["tags"]) > 0:
            tags = list(preset_info["tags"])
            hierarchy_sources["tags"] = "preset_category_default"
        elif folder and folder.default_tags and len(folder.default_tags) > 0:
            tags = list(folder.default_tags)
            hierarchy_sources["tags"] = "folder_default"
        elif channel and channel.default_tags and len(channel.default_tags) > 0:
            tags = list(channel.default_tags)
            hierarchy_sources["tags"] = "channel_default"
        else:
            tags = ["devotional", "daily"]
            hierarchy_sources["tags"] = "system_default"

        # 4. RESOLVE CATEGORY ID
        category_id = "22"
        if video_meta.get("category"):
            category_id = str(video_meta["category"])
            hierarchy_sources["category_id"] = "video_sidecar"
        elif schedule and schedule.category_id:
            category_id = schedule.category_id
            hierarchy_sources["category_id"] = "schedule_template"
        elif preset_info and preset_info.get("category_id"):
            category_id = str(preset_info["category_id"])
            hierarchy_sources["category_id"] = "preset_category_default"
        elif folder and folder.default_category_id:
            category_id = folder.default_category_id
            hierarchy_sources["category_id"] = "folder_default"
        elif channel and channel.default_category_id:
            category_id = channel.default_category_id
            hierarchy_sources["category_id"] = "channel_default"
        else:
            category_id = "22"
            hierarchy_sources["category_id"] = "system_default"

        # 5. RESOLVE PRIVACY STATUS
        privacy_status = "private"
        if schedule and schedule.privacy_status:
            privacy_status = schedule.privacy_status
            hierarchy_sources["privacy_status"] = "schedule_setting"
        elif channel and channel.default_privacy_status:
            privacy_status = channel.default_privacy_status
            hierarchy_sources["privacy_status"] = "channel_default"

        # 6. RESOLVE THUMBNAIL
        thumbnail_id = None
        if video.custom_thumbnail_file_id:
            thumbnail_id = video.custom_thumbnail_file_id
            hierarchy_sources["thumbnail"] = "video_sidecar"
        elif folder and folder.default_thumbnail_storage_id:
            thumbnail_id = folder.default_thumbnail_storage_id
            hierarchy_sources["thumbnail"] = "folder_default"
        elif channel and channel.default_thumbnail_storage_id:
            thumbnail_id = channel.default_thumbnail_storage_id
            hierarchy_sources["thumbnail"] = "channel_default"
        else:
            thumbnail_id = None
            hierarchy_sources["thumbnail"] = "none"

        # 7. RESOLVE ADVANCED UPLOAD SETTINGS
        made_for_kids = False
        age_restricted = False
        default_language = "hi"
        default_audio_language = "hi"
        contains_synthetic_media = False

        if schedule:
            made_for_kids = bool(schedule.made_for_kids)
            age_restricted = bool(schedule.age_restricted)
            default_language = schedule.default_language or (preset_info.get("default_language") if preset_info else None) or "hi"
            default_audio_language = schedule.default_audio_language or (preset_info.get("default_audio_language") if preset_info else None) or "hi"
            contains_synthetic_media = bool(schedule.contains_synthetic_media)
        elif preset_info:
            made_for_kids = bool(preset_info.get("made_for_kids", False))
            age_restricted = bool(preset_info.get("age_restricted", False))
            default_language = preset_info.get("default_language", "hi")
            default_audio_language = preset_info.get("default_audio_language", "hi")
            contains_synthetic_media = bool(preset_info.get("contains_synthetic_media", False))

        return ResolvedMetadata(
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy_status,
            thumbnail_storage_id=thumbnail_id,
            source_hierarchy=hierarchy_sources,
            made_for_kids=made_for_kids,
            age_restricted=age_restricted,
            default_language=default_language,
            default_audio_language=default_audio_language,
            contains_synthetic_media=contains_synthetic_media
        )
