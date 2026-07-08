"""
venv_manager cache mixin — split from venv_manager.py.

Holds the on-disk env cache helpers (env_cache.json read/write, keying,
invalidation). Mixed into VenvManager; relies only on self.* attributes
set up by VenvManager.__init__ (base_dir etc.) plus the module logger.
"""

import os
import json
import logging
import platform as _platform
from pathlib import Path
from typing import Optional, Dict, Any

from src.core.venv_manager_common import _fmt_path

_log = logging.getLogger("venvstudio.core.venv_manager")


class _CacheMixin:
    """Env cache persistence (env_cache.json). Mixed into VenvManager."""

    def _get_cache_file(self) -> Path:
        system = _platform.system().lower()
        if system == "windows":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif system == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        cache_dir = base / "VenvStudio"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "env_cache.json"

    def _load_all_cache(self) -> Dict[str, Any]:
        """Load cache from memory if available, otherwise from disk once."""
        if type(self)._all_cache is not None:
            return type(self)._all_cache
        f = self._get_cache_file()
        if not f.exists():
            type(self)._all_cache = {}
            return type(self)._all_cache
        try:
            type(self)._all_cache = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            type(self)._all_cache = {}
        return type(self)._all_cache

    def _save_all_cache(self, data: Dict[str, Any]) -> None:
        type(self)._all_cache = data  # update memory cache
        try:
            cache_file = self._get_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            _log.warning(f"⚠️ [Cache] Write error: {e}")

    def _cache_key(self, venv_path: Path) -> str:
        """Consistent cache key — always forward slashes, no leading slash on Windows."""
        key = str(venv_path.resolve()).replace("\\", "/").replace("\\\\", "/")
        # pathlib.resolve() on Windows sometimes returns /C:/... — strip leading slash
        if len(key) > 2 and key[0] == "/" and key[2] == ":":
            key = key[1:]
        return key

    def _read_cache(self, venv_path: Path) -> Optional[Dict[str, Any]]:
        all_cache = self._load_all_cache()
        key = self._cache_key(venv_path)
        entry = all_cache.get(key)
        if not entry:
            _log.debug(f"📦 [Cache] MISS: {_fmt_path(key)}")
            return None
        if entry.get("needs_refresh", 1) == 1:
            _log.debug(f"♻️ [Cache] STALE: {_fmt_path(key)} (needs_refresh=1)")
            return None
        _log.debug(f"✅ [Cache] HIT: {_fmt_path(key)} (py={entry.get('python_version','?')} pkgs={entry.get('package_count','?')})")
        return entry

    def write_cache(self, venv_path: Path, python_version: str, package_count: int, size: str) -> None:
        all_cache = self._load_all_cache()
        all_cache[self._cache_key(venv_path)] = {
            "python_version": python_version,
            "package_count": package_count,
            "size": size,
            "needs_refresh": 0,
        }
        self._save_all_cache(all_cache)
        _log.info(f"💾 [Cache] Written: {_fmt_path(venv_path)} → py={python_version} pkgs={package_count} size={size}")
        _log.debug(f"📄 [Cache] File: {_fmt_path(self._get_cache_file())}")

    def invalidate_cache(self, venv_path: Path) -> None:
        all_cache = self._load_all_cache()
        key = self._cache_key(venv_path)
        if key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        else:
            all_cache[key] = {"needs_refresh": 1}
        self._save_all_cache(all_cache)
