import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.logging import logger

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
PRESETS_FILE = os.path.join(DATA_DIR, "content_presets.json")


class ContentPresetService:
    @classmethod
    def _ensure_data_file(cls) -> Dict[str, Any]:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(PRESETS_FILE):
            # Write empty dict or seed
            default_data = {
                "mahadev": {
                    "id": "mahadev",
                    "name": "🔱 Mahadev (Bhakti / Status / Universal)",
                    "category_id": "22",
                    "category_name": "People & Blogs",
                    "default_language": "hi",
                    "default_audio_language": "hi",
                    "made_for_kids": False,
                    "age_restricted": False,
                    "contains_synthetic_media": False,
                    "description": "हर हर महादेव 🔱 🙏\nमहादेव की असीम कृपा आप और आपके पूरे परिवार पर सदैव बनी रहे।\nकमेंट में \"हर हर महादेव\" लिखकर भोलेनाथ का आशीर्वाद जरूर प्राप्त करें! 🕉️💖\n\n#mahadev #shorts #shivbhakti #bholenath #kedarnath #mahakal #omnamahshivaya #shiv #viralshorts #trending",
                    "tags": ["mahadev", "shorts", "shivbhakti", "bholenath", "kedarnath", "mahakal", "omnamahshivaya", "shivji", "harharmahadev", "mahadevstatus", "status", "viral", "trending"],
                    "hooks": [
                        "🔱 हर हर महादेव 🙏 | ॐ नमः शिवाय ✨ #shorts #mahadev #bholenath",
                        "महादेव का पावन आशीर्वाद 🔱🌸 जय श्री महाकाल #mahadevstatus #shorts",
                        "जय श्री महाकाल ⚡🔱 महादेव का शक्तिशाली रूप #shorts #mahakal #shiv",
                        "शिव शंभू की कृपा आप पर सदैव बनी रहे 🕉️🙏 #shivbhakti #shorts",
                        "भोलेनाथ आपके सभी संकट दूर करेंगे 🔱✨ #bholenath #shorts #mahadev"
                    ]
                }
            }
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data

        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read content presets JSON file: {e}")
            return {}

    @classmethod
    def _save_data_file(cls, data: Dict[str, Any]) -> bool:
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save content presets JSON: {e}")
            return False

    @classmethod
    def list_presets(cls) -> List[Dict[str, Any]]:
        data = cls._ensure_data_file()
        return list(data.values())

    @classmethod
    def get_preset(cls, preset_id: str) -> Optional[Dict[str, Any]]:
        data = cls._ensure_data_file()
        return data.get(preset_id.lower().strip())

    @classmethod
    def save_preset(cls, preset_id: str, preset_data: Dict[str, Any]) -> Dict[str, Any]:
        data = cls._ensure_data_file()
        clean_id = preset_id.lower().strip().replace(" ", "_")
        preset_data["id"] = clean_id
        data[clean_id] = preset_data
        cls._save_data_file(data)
        return preset_data

    @classmethod
    def delete_preset(cls, preset_id: str) -> bool:
        data = cls._ensure_data_file()
        clean_id = preset_id.lower().strip()
        if clean_id in data:
            del data[clean_id]
            cls._save_data_file(data)
            return True
        return False

    @classmethod
    def import_presets(cls, incoming_json: Dict[str, Any], overwrite_all: bool = False) -> Dict[str, Any]:
        """
        Accepts either:
        1. A full dictionary of presets: { "mahadev": {...}, "custom": {...} }
        2. A single preset: { "id": "my_category", "name": "...", "hooks": [...] }
        3. A list of hooks or preset format
        """
        data = {} if overwrite_all else cls._ensure_data_file()

        if isinstance(incoming_json, dict):
            # Check if single preset or multi-preset
            if "hooks" in incoming_json and ("name" in incoming_json or "id" in incoming_json):
                p_id = incoming_json.get("id") or incoming_json.get("name", "custom").lower().strip().replace(" ", "_")
                data[p_id] = incoming_json
            else:
                for k, v in incoming_json.items():
                    if isinstance(v, dict):
                        data[k.lower().strip()] = v
        
        cls._save_data_file(data)
        return {
            "status": "SUCCESS",
            "total_presets": len(data),
            "presets": list(data.values())
        }

    @classmethod
    def export_presets_json(cls) -> str:
        data = cls._ensure_data_file()
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def resolve_hook_for_date(
        cls,
        preset_id: str,
        target_date: Optional[datetime] = None,
        rotation_index: Optional[int] = None
    ) -> Optional[str]:
        """
        Rotates through hooks:
        - If rotation_index is passed, uses index % len(hooks)
        - Otherwise uses day-of-month: (day - 1) % len(hooks)
        - Ensures 31-day rotation seamlessly resets every month!
        """
        preset = cls.get_preset(preset_id)
        if not preset or not preset.get("hooks"):
            return None

        hooks = preset["hooks"]
        if not hooks:
            return None

        if rotation_index is not None:
            idx = rotation_index % len(hooks)
        else:
            d = target_date or datetime.now()
            idx = (d.day - 1) % len(hooks)

        return hooks[idx]
