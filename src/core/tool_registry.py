"""
Tool Registry — tracks installed tool paths and versions.

Stores a JSON file with tool metadata so VenvStudio knows where
uv, poetry, pipx, micromamba etc. are installed.
"""

import json
import os
import shutil
import platform as _platform
from datetime import datetime
from pathlib import Path


def _get_registry_path() -> Path:
    """Return platform-appropriate registry file path."""
    system = _platform.system().lower()
    if system == "windows":
        base = Path(os.environ.get("APPDATA",
                                    Path.home() / "AppData" / "Roaming"))
    elif system == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME",
                                    Path.home() / ".config"))
    registry_dir = base / "VenvStudio"
    registry_dir.mkdir(parents=True, exist_ok=True)
    return registry_dir / "tool_registry.json"


class ToolRegistry:
    """Track installed tools (uv, poetry, pipx, micromamba) with paths and versions."""

    def __init__(self):
        self._path = _get_registry_path()
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def scope_of(path: str) -> str:
        """'user' or 'system' — can we write next to this executable?

        N57: the Toolchain Manager needs to tell the two apart to label a tool
        and to know whether an upgrade will need elevation. The question is not
        "which directory is this" but "can this process write there", so it is
        answered by trying, not by matching path prefixes that differ per
        distro, per Python installer and per Windows layout.
        """
        import tempfile as _tf
        d = os.path.dirname(path) if os.path.isfile(path) else path
        if not d or not os.path.isdir(d):
            return "unknown"
        try:
            with _tf.NamedTemporaryFile(dir=d, prefix=".vs-wtest-"):
                return "user"
        except OSError:
            return "system"

    def register(self, tool_name: str, path: str, version: str = "",
                 installed_by: str = "venvstudio", scope: str = ""):
        """Register a tool with its path, version, install source and scope.

        `installed_by` answers WHO put it there and only ever holds
        "venvstudio" or "external". It used to be set to "system" for anything
        merely discovered on PATH, which read like an install-scope claim and
        was not one -- a tool found in ~/.local/bin was recorded as "system".
        Scope is a separate question and now has its own field. (N57)
        """
        if installed_by not in ("venvstudio", "external"):
            # Tolerate the old "system" value from existing registry files and
            # from any caller not yet updated.
            installed_by = "external"
        self._data[tool_name] = {
            "path": str(path),
            "version": version,
            "installed_by": installed_by,
            "scope": scope or self.scope_of(str(path)),
            "installed_at": datetime.now().isoformat(),
        }
        self._save()

    def get_scope(self, tool_name: str) -> str:
        """'user', 'system' or '' — install scope of a registered tool.

        Recomputed when the stored entry predates the field, so upgrading
        VenvStudio does not leave every tool unlabelled.
        """
        entry = self._data.get(tool_name, {})
        scope = entry.get("scope", "")
        if not scope and entry.get("path"):
            scope = self.scope_of(entry["path"])
            if scope != "unknown":
                entry["scope"] = scope
                self._save()
        return scope

    def find(self, tool_name: str) -> str:
        """Find tool executable — registry first, then shutil.which fallback.
        Returns path string or empty string if not found.
        """
        # 1. Check registry
        entry = self._data.get(tool_name, {})
        reg_path = entry.get("path", "")
        if reg_path and os.path.isfile(reg_path):
            return reg_path

        # 2. shutil.which fallback
        found = shutil.which(tool_name)
        if not found:
            found = shutil.which(tool_name + ".exe")
        if found:
            # Discovered, not installed by us -- see register()'s note on why
            # this is no longer called "system".
            self.register(tool_name, found, installed_by="external")
            return found

        # 3. Common locations
        common_paths = self._common_paths(tool_name)
        for p in common_paths:
            if os.path.isfile(p):
                self.register(tool_name, p, installed_by="external")
                return p

        return ""

    def _common_paths(self, tool_name: str) -> list:
        """Return common installation paths for a tool."""
        import sys
        paths = []
        scripts = os.path.join(os.path.dirname(sys.executable),
                               "Scripts" if sys.platform == "win32" else "bin")
        for name in (tool_name, tool_name + ".exe"):
            paths.append(os.path.join(scripts, name))

        # User site-packages scripts
        try:
            import site
            user_scripts = os.path.join(
                site.getusersitepackages(), "..", "..",
                "Scripts" if sys.platform == "win32" else "bin")
            for name in (tool_name, tool_name + ".exe"):
                paths.append(os.path.normpath(os.path.join(user_scripts, name)))
        except Exception:
            pass

        # ~/.local/bin (Linux/macOS)
        if sys.platform != "win32":
            paths.append(os.path.expanduser(f"~/.local/bin/{tool_name}"))

        return paths

    def get_path(self, tool_name: str) -> str:
        """Get registered path for a tool (no search)."""
        entry = self._data.get(tool_name, {})
        return entry.get("path", "")

    def get_version(self, tool_name: str) -> str:
        """Get registered version for a tool."""
        entry = self._data.get(tool_name, {})
        return entry.get("version", "")

    def get_info(self, tool_name: str) -> dict:
        """Get full info dict for a tool."""
        return self._data.get(tool_name, {})

    def list_all(self) -> dict:
        """Return all registered tools."""
        return dict(self._data)

    def remove(self, tool_name: str):
        """Remove a tool from registry."""
        if tool_name in self._data:
            del self._data[tool_name]
            self._save()

    def update_version(self, tool_name: str, version: str):
        """Update just the version for a tool."""
        if tool_name in self._data:
            self._data[tool_name]["version"] = version
            self._save()
