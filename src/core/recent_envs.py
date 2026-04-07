"""
RecentEnvsManager — tracks recently opened/selected environments.

Stores a JSON file (recent_envs.json) in the VenvStudio config directory.
Max 10 entries, newest first. Auto-removes entries for deleted paths.
"""

import json
import os
import platform as _platform
from datetime import datetime
from pathlib import Path


def _get_recent_envs_path() -> Path:
    """Return platform-appropriate path for recent_envs.json."""
    system = _platform.system().lower()
    if system == "windows":
        base = Path(os.environ.get("APPDATA",
                                    Path.home() / "AppData" / "Roaming"))
    elif system == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME",
                                    Path.home() / ".config"))
    config_dir = base / "VenvStudio"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "recent_envs.json"


MAX_RECENT = 10


class RecentEnvsManager:
    """Manage recently opened environments list."""

    def __init__(self):
        self._path = _get_recent_envs_path()

    def load(self) -> list:
        """Load recent envs list, pruning missing paths automatically."""
        entries = self._read()
        # Prune entries whose paths no longer exist
        valid = [e for e in entries if os.path.exists(e.get("path", ""))]
        if len(valid) != len(entries):
            self._write(valid)
        return valid

    def touch(self, name: str, path: str, env_type: str = "venv"):
        """Add or update an entry (move to top), save."""
        entries = self._read()
        norm_path = os.path.normcase(os.path.normpath(path))

        # Remove existing entry for this path if present
        entries = [e for e in entries
                   if os.path.normcase(os.path.normpath(e.get("path", ""))) != norm_path]

        # Prepend new entry
        entries.insert(0, {
            "name": name,
            "path": str(path),
            "type": env_type,
            "last_opened": datetime.now().isoformat(),
        })

        # Cap at MAX_RECENT
        entries = entries[:MAX_RECENT]
        self._write(entries)

    def remove(self, path: str):
        """Remove entry by path."""
        norm = os.path.normcase(os.path.normpath(path))
        entries = self._read()
        entries = [e for e in entries
                   if os.path.normcase(os.path.normpath(e.get("path", ""))) != norm]
        self._write(entries)

    def clear(self):
        """Remove all recent env entries."""
        self._write([])

    # ── internal ──────────────────────────────────────────────────────────

    def _read(self) -> list:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    def _write(self, entries: list):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
