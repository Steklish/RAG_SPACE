import json
import os
from typing import Dict, Any

class SettingsStore:
    def __init__(self, storage_path: str = "storage/settings.json"):
        self.storage_path = storage_path
        self.defaults = {"language": "Russian"}
        if not os.path.exists(os.path.dirname(storage_path)):
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)

    def get_settings(self) -> Dict[str, Any]:
        if not os.path.exists(self.storage_path):
            return self.defaults
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Make sure all default keys are present
                for key, value in self.defaults.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except (json.JSONDecodeError, IOError):
            return self.defaults

    def save_settings(self, settings: Dict[str, Any]):
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
