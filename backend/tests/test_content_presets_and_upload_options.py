import pytest
from datetime import datetime
from app.services.metadata.content_presets import ContentPresetService
from app.services.metadata.metadata_engine import MetadataEngine, ResolvedMetadata
from app.models.video import Video
from app.models.channel import Channel
from app.models.schedule import Schedule


def test_default_presets_loaded():
    presets = ContentPresetService.list_presets()
    preset_ids = [p["id"] for p in presets]
    assert "mahadev" in preset_ids
    assert "shinchan" in preset_ids

    mahadev = ContentPresetService.get_preset("mahadev")
    assert mahadev is not None
    assert len(mahadev["hooks"]) >= 31, f"Expected at least 31 Mahadev hooks, got {len(mahadev['hooks'])}"

    shinchan = ContentPresetService.get_preset("shinchan")
    assert shinchan is not None
    assert len(shinchan["hooks"]) >= 31, f"Expected at least 31 Shinchan hooks, got {len(shinchan['hooks'])}"


def test_31_day_hook_rotation_and_reset():
    # Day 1
    d1 = datetime(2026, 8, 1)
    hook_day1 = ContentPresetService.resolve_hook_for_date("mahadev", d1)
    assert hook_day1 is not None

    # Day 31
    d31 = datetime(2026, 8, 31)
    hook_day31 = ContentPresetService.resolve_hook_for_date("mahadev", d31)
    assert hook_day31 is not None
    assert hook_day1 != hook_day31

    # Next month Day 1 should reset back to Day 1 hook
    next_m_d1 = datetime(2026, 9, 1)
    hook_next_month_d1 = ContentPresetService.resolve_hook_for_date("mahadev", next_m_d1)
    assert hook_next_month_d1 == hook_day1


def test_metadata_engine_dynamic_hook_substitution():
    dt = datetime(2026, 8, 15)
    title = MetadataEngine.substitute_variables(
        template="{dynamic_hook}",
        channel_name="Bhakti Status",
        video_filename="clip_15.mp4",
        target_datetime=dt,
        preset_category="mahadev"
    )
    assert len(title) > 0
    assert "{dynamic_hook}" not in title
    assert "#shorts" in title.lower()


def test_resolved_metadata_upload_options():
    vid = Video(id="v1", filename="15.mp4", enabled=True)
    ch = Channel(id="c1", name="Mahadev Channel")
    sch = Schedule(
        id="s1",
        channel_id="c1",
        name="Daily Mahadev",
        schedule_type="DAILY",
        source_type="FOLDER",
        source_id="f1",
        mode="DAY_OF_MONTH",
        publish_time="09:00",
        timezone="Asia/Kolkata",
        made_for_kids=False,
        age_restricted=False,
        default_language="hi",
        default_audio_language="hi",
        contains_synthetic_media=False,
        preset_category="mahadev"
    )

    resolved = MetadataEngine.resolve_effective_metadata(
        video=vid,
        channel=ch,
        schedule=sch,
        target_datetime=datetime(2026, 8, 18)
    )

    assert resolved.made_for_kids is False
    assert resolved.age_restricted is False
    assert resolved.default_language == "hi"
    assert resolved.default_audio_language == "hi"
    assert resolved.contains_synthetic_media is False
    assert len(resolved.title) > 0
    assert len(resolved.tags) >= 5


def test_presets_json_import_and_export():
    exported_json = ContentPresetService.export_presets_json()
    assert "mahadev" in exported_json
    assert "shinchan" in exported_json

    custom_import = {
        "custom_test": {
            "id": "custom_test",
            "name": "Custom Test Niche",
            "category_id": "22",
            "hooks": [
                "Custom Hook 1 #shorts",
                "Custom Hook 2 #shorts"
            ],
            "tags": ["test", "custom"]
        }
    }

    res = ContentPresetService.import_presets(custom_import, overwrite_all=False)
    assert res["status"] == "SUCCESS"

    p = ContentPresetService.get_preset("custom_test")
    assert p is not None
    assert len(p["hooks"]) == 2

    # Clean up test preset
    ContentPresetService.delete_preset("custom_test")
    assert ContentPresetService.get_preset("custom_test") is None
