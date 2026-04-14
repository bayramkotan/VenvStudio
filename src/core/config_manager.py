"""
VenvStudio - Configuration Manager
JSON-based settings persistence
"""

import json
from pathlib import Path
from typing import Any, Optional

from src.utils.platform_utils import get_config_dir, get_default_venv_base_dir


DEFAULT_SETTINGS = {
    "venv_base_dir": str(get_default_venv_base_dir()),
    "theme": "dark",
    "auto_upgrade_pip": True,
    "show_hidden_packages": False,
    "default_python": "",  # empty = system default
    "window_width": 1100,
    "window_height": 750,
    "recent_envs": [],
}


class ConfigManager:
    """Manages application configuration stored as JSON."""

    def __init__(self):
        self._config_dir = get_config_dir()
        self._config_file = self._config_dir / "settings.json"
        self._settings = {}
        self._batch_mode = False  # When True, set() won't auto-save
        self._batch_dirty = False  # Track if any changes made during batch
        self.load()

    def load(self) -> None:
        """Load settings from file, creating defaults if needed."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("Invalid config format")
                self._settings = loaded
                # Merge any new default keys
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in self._settings:
                        self._settings[key] = value
            except (json.JSONDecodeError, IOError, ValueError):
                # Bozuk veya geçersiz JSON — yedekle ve sıfırla
                try:
                    import shutil
                    _bak = self._config_file.with_suffix(".json.bak")
                    shutil.copy2(self._config_file, _bak)
                except Exception:
                    pass
                self._settings = DEFAULT_SETTINGS.copy()
        else:
            self._settings = DEFAULT_SETTINGS.copy()
        self.save()

    def save(self) -> None:
        """Save current settings to file. Re-creates dir/file if deleted (e.g. after Remove All Data)."""
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value. Saves immediately unless in batch mode."""
        self._settings[key] = value
        if self._batch_mode:
            self._batch_dirty = True
        else:
            self.save()

    def begin_batch(self) -> None:
        """Start batch mode — set() calls won't trigger disk writes."""
        self._batch_mode = True
        self._batch_dirty = False

    def end_batch(self) -> None:
        """End batch mode — writes to disk once if any changes were made."""
        self._batch_mode = False
        if self._batch_dirty:
            self.save()
            self._batch_dirty = False

    def get_venv_base_dir(self) -> Path:
        """Get the base directory for virtual environments."""
        return Path(self._settings.get("venv_base_dir", str(get_default_venv_base_dir())))

    def set_venv_base_dir(self, path: str) -> None:
        """Set the base directory for virtual environments."""
        self.set("venv_base_dir", path)

    def add_recent_env(self, env_name: str) -> None:
        """Add an environment to recent list."""
        recent = self._settings.get("recent_envs", [])
        if env_name in recent:
            recent.remove(env_name)
        recent.insert(0, env_name)
        self._settings["recent_envs"] = recent[:10]  # Keep last 10
        self.save()

    @property
    def config_file_path(self) -> Path:
        return self._config_file
