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
    # B196: no hard-coded "dark" any more. Empty means nobody has chosen
    # yet, and WindowThemeMixin fills it in from the desktop's own setting
    # on the first run -- light when the desktop does not say, because a
    # light window is readable on every desktop and a dark one is wrong on
    # most. The AppImage catalog test rejected the v1.6.109 build for
    # opening dark on a light test system.
    "theme": "",
    # True while the theme is whatever the desktop says. Choosing a theme
    # anywhere in the app turns it off -- see set() below.
    "theme_follows_system": True,
    "auto_upgrade_pip": True,
    "show_hidden_packages": False,
    # Educational side of VenvStudio: show the terminal command behind each
    # action. On by default; power users can quiet the log.
    "show_commands": True,
    # Total size of venvstudio.log plus its rotated backups, in MB.
    # 12 MB holds roughly six weeks of ordinary use.
    "log_history_mb": 12,
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
        _pin_saved_theme = False
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("Invalid config format")
                # B196: an install that already carries a theme is an
                # install whose owner has been looking at that theme.
                # Adding theme_follows_system must not change what they
                # see, so a config written before the key existed keeps
                # its saved theme. Only a config with no theme at all --
                # a genuine first run -- follows the desktop.
                _pin_saved_theme = (bool(loaded.get("theme"))
                                    and "theme_follows_system" not in loaded)
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
        if _pin_saved_theme:
            self._settings["theme_follows_system"] = False
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
        # B196: choosing a theme anywhere in the app stops it following the
        # desktop. Several places write "theme" directly -- the Appearance
        # page, the Advanced page's reset, the View menu -- and making each
        # of them remember to clear the flag is the duplication this
        # codebase keeps paying for. One place, every caller.
        #
        # set_system_theme() below is the one writer that is NOT a choice,
        # and it bypasses this on purpose.
        if key == "theme":
            self._settings["theme_follows_system"] = (
                str(value or "").strip().lower() in ("", "system", "auto"))
        self._settings[key] = value
        if self._batch_mode:
            self._batch_dirty = True
        else:
            self.save()

    def set_system_theme(self, theme_id: str) -> None:
        """Record the theme the DESKTOP asked for, keeping follow mode on.

        B196. set() turns following off, because a theme written anywhere
        in the app is a choice someone made. This is the only writer that
        is not a choice, so it is the only one that may leave the flag
        alone.
        """
        self._settings["theme"] = theme_id
        self._settings["theme_follows_system"] = True
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
