"""
editor_integration.py — Register VenvStudio's venv directory as the default
virtual-environment location inside popular editors/IDEs.

For each supported editor we:
  1. Detect if it's installed (binary path + settings dir)
  2. Read its user settings file (JSON / XML / TOML as needed)
  3. Add or update the venv-path setting — without touching anything else
  4. Back up the original settings file before writing

Supported editors (as of 2026):
  - VS Code         — settings.json / python.venvPath
  - Cursor          — settings.json / python.venvPath (VS Code fork)
  - Windsurf        — settings.json / python.venvPath (VS Code fork)
  - Code - OSS      — settings.json / python.venvPath (community VS Code)
  - VSCodium        — settings.json / python.venvPath
  - Zed             — settings.json (JSONC) / python settings
  - PyCharm         — path registry hint only (full SDK requires IDE UI)

Design principles:
  - NEVER clobber other keys in the settings file
  - Always back up (<file>.vs-backup) before writing
  - Never require admin/root; user-level configs only
  - Return structured status so GUI can show success/fail messages
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EditorInfo:
    """Describes one editor target."""
    id: str                         # stable slug, e.g. "vscode"
    name: str                       # display name, e.g. "VS Code"
    icon: str                       # emoji / unicode
    binary_names: List[str]         # names we look for on PATH
    config_paths: dict              # per-OS user settings.json paths
    installed: bool = False
    config_path: Optional[Path] = None  # resolved path (if found)
    note: str = ""                  # extra info for UI (empty if none)


@dataclass
class RegisterResult:
    """What happened when we tried to register/unregister."""
    ok: bool
    message: str
    backup_path: Optional[Path] = None
    editor_id: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Editor registry
# ─────────────────────────────────────────────────────────────────────────────

def _home() -> Path:
    return Path.home()


def _appdata() -> Path:
    """Windows %APPDATA% or Linux/mac equivalent."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming"))
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support"
    return _home() / ".config"


# Each editor's settings.json locations per platform.
# Paths may not exist yet — we check and optionally create the folder on write.
EDITORS: List[EditorInfo] = [
    EditorInfo(
        id="vscode",
        name="VS Code",
        icon="🆚",
        binary_names=["code", "code.exe", "code-insiders"],
        config_paths={
            "win32":  _appdata() / "Code" / "User" / "settings.json",
            "darwin": _home() / "Library" / "Application Support" / "Code" / "User" / "settings.json",
            "linux":  _home() / ".config" / "Code" / "User" / "settings.json",
        },
    ),
    EditorInfo(
        id="cursor",
        name="Cursor",
        icon="➤",
        binary_names=["cursor"],
        config_paths={
            "win32":  _appdata() / "Cursor" / "User" / "settings.json",
            "darwin": _home() / "Library" / "Application Support" / "Cursor" / "User" / "settings.json",
            "linux":  _home() / ".config" / "Cursor" / "User" / "settings.json",
        },
    ),
    EditorInfo(
        id="windsurf",
        name="Windsurf",
        icon="🌊",
        binary_names=["windsurf"],
        config_paths={
            "win32":  _appdata() / "Windsurf" / "User" / "settings.json",
            "darwin": _home() / "Library" / "Application Support" / "Windsurf" / "User" / "settings.json",
            "linux":  _home() / ".config" / "Windsurf" / "User" / "settings.json",
        },
    ),
    EditorInfo(
        id="vscodium",
        name="VSCodium",
        icon="📘",
        binary_names=["codium"],
        config_paths={
            "win32":  _appdata() / "VSCodium" / "User" / "settings.json",
            "darwin": _home() / "Library" / "Application Support" / "VSCodium" / "User" / "settings.json",
            "linux":  _home() / ".config" / "VSCodium" / "User" / "settings.json",
        },
    ),
    EditorInfo(
        id="code_oss",
        name="Code - OSS",
        icon="🔶",
        binary_names=["code-oss"],
        config_paths={
            "win32":  _appdata() / "Code - OSS" / "User" / "settings.json",
            "darwin": _home() / "Library" / "Application Support" / "Code - OSS" / "User" / "settings.json",
            "linux":  _home() / ".config" / "Code - OSS" / "User" / "settings.json",
        },
    ),
    EditorInfo(
        id="zed",
        name="Zed",
        icon="⚡",
        binary_names=["zed"],
        config_paths={
            "win32":  _appdata() / "Zed" / "settings.json",
            "darwin": _home() / ".config" / "zed" / "settings.json",
            "linux":  _home() / ".config" / "zed" / "settings.json",
        },
        note="Zed reads Python venvs from common venv dirs; adds hint via python.venv_path.",
    ),
    EditorInfo(
        id="pycharm",
        name="PyCharm",
        icon="🧠",
        binary_names=["pycharm", "pycharm.sh", "pycharm64.exe", "charm"],
        config_paths={
            # PyCharm doesn't expose SDK config as a simple JSON — we just
            # write a small marker file in the VenvStudio dir that PyCharm
            # can import. Full SDK registration needs the IDE UI.
            "win32":  _appdata() / "JetBrains" / "options" / "jdk.table.xml",
            "darwin": _home() / "Library" / "Application Support" / "JetBrains" / "options" / "jdk.table.xml",
            "linux":  _home() / ".config" / "JetBrains" / "options" / "jdk.table.xml",
        },
        note="PyCharm SDK registration requires manual step inside the IDE — "
             "this only saves a reminder file you can import.",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────────────────────────────────────

def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _resolve_platform_key() -> str:
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def detect_editors() -> List[EditorInfo]:
    """Walk the registry, mark which editors are installed on this machine."""
    plat = _resolve_platform_key()
    detected: List[EditorInfo] = []

    for entry in EDITORS:
        info = EditorInfo(
            id=entry.id,
            name=entry.name,
            icon=entry.icon,
            binary_names=entry.binary_names,
            config_paths=entry.config_paths,
            note=entry.note,
        )
        cfg = entry.config_paths.get(plat)
        info.config_path = Path(cfg) if cfg else None

        # Consider installed if either the binary is on PATH or the config dir
        # already exists (the editor has been run at least once).
        has_binary = any(_which(n) for n in entry.binary_names)
        has_config_dir = (
            info.config_path is not None
            and info.config_path.parent.exists()
        )
        info.installed = bool(has_binary or has_config_dir)
        detected.append(info)

    return detected


# ─────────────────────────────────────────────────────────────────────────────
# JSONC (JSON with comments) — VS Code family uses this
# ─────────────────────────────────────────────────────────────────────────────

_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _load_jsonc(path: Path) -> dict:
    """Read a JSONC file (JSON with // and /* */ comments, trailing commas)."""
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not raw.strip():
        return {}

    stripped = _BLOCK_COMMENT.sub("", raw)
    stripped = _LINE_COMMENT.sub("", stripped)
    stripped = _TRAILING_COMMA.sub(r"\1", stripped)
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _backup(path: Path) -> Optional[Path]:
    """Create a .vs-backup alongside the file if it exists."""
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".vs-backup")
    try:
        shutil.copy2(path, backup)
        return backup
    except Exception:
        return None


def _write_json(path: Path, data: dict) -> None:
    """Pretty-print JSON (2-space indent) with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Per-editor register/unregister
# ─────────────────────────────────────────────────────────────────────────────

def _is_vscode_family(editor_id: str) -> bool:
    return editor_id in {"vscode", "cursor", "windsurf", "vscodium", "code_oss"}


def register(editor: EditorInfo, venv_dir: Path) -> RegisterResult:
    """Add VenvStudio's venv directory to the editor's settings.

    - VS Code family: sets `python.venvPath` to venv_dir
    - Zed: sets `python.venv_path` (Zed convention)
    - PyCharm: drops a reminder file (manual import required)
    """
    venv_dir = Path(venv_dir).expanduser().resolve()
    if not venv_dir.is_dir():
        return RegisterResult(
            ok=False,
            message=f"Venv directory does not exist: {venv_dir}",
            editor_id=editor.id,
        )

    cfg = editor.config_path
    if cfg is None:
        return RegisterResult(
            ok=False,
            message=f"No config path known for {editor.name} on this OS.",
            editor_id=editor.id,
        )

    if _is_vscode_family(editor.id):
        return _register_vscode_like(cfg, venv_dir, editor)
    if editor.id == "zed":
        return _register_zed(cfg, venv_dir, editor)
    if editor.id == "pycharm":
        return _register_pycharm(cfg, venv_dir, editor)

    return RegisterResult(
        ok=False,
        message=f"Register not implemented for {editor.name}.",
        editor_id=editor.id,
    )


def unregister(editor: EditorInfo) -> RegisterResult:
    """Remove VenvStudio's added key — don't touch anything else."""
    cfg = editor.config_path
    if cfg is None or not cfg.exists():
        return RegisterResult(
            ok=True,
            message="Nothing to unregister (no config file).",
            editor_id=editor.id,
        )

    if _is_vscode_family(editor.id):
        return _unregister_vscode_like(cfg, editor)
    if editor.id == "zed":
        return _unregister_zed(cfg, editor)
    if editor.id == "pycharm":
        return _unregister_pycharm(editor)

    return RegisterResult(
        ok=False,
        message=f"Unregister not implemented for {editor.name}.",
        editor_id=editor.id,
    )


# ── VS Code family ──────────────────────────────────────────────────────────

def _register_vscode_like(cfg: Path, venv_dir: Path, editor: EditorInfo) -> RegisterResult:
    data = _load_jsonc(cfg) if cfg.exists() else {}
    backup = _backup(cfg)

    # VS Code expects a string path. Use forward slashes on Windows too —
    # VS Code accepts both but forward slashes avoid JSON escaping.
    path_str = str(venv_dir).replace("\\", "/")

    data["python.venvPath"] = path_str
    # Also set venvFolders to help discovery (newer Python extension).
    folders = data.get("python.venvFolders")
    if not isinstance(folders, list):
        folders = []
    if path_str not in folders:
        folders.append(path_str)
    data["python.venvFolders"] = folders

    try:
        _write_json(cfg, data)
    except Exception as e:
        return RegisterResult(
            ok=False,
            message=f"Failed to write {cfg}: {e}",
            backup_path=backup,
            editor_id=editor.id,
        )
    return RegisterResult(
        ok=True,
        message=f"Registered '{path_str}' as {editor.name} venv path.",
        backup_path=backup,
        editor_id=editor.id,
    )


def _unregister_vscode_like(cfg: Path, editor: EditorInfo) -> RegisterResult:
    data = _load_jsonc(cfg)
    backup = _backup(cfg)

    changed = False
    if "python.venvPath" in data:
        del data["python.venvPath"]
        changed = True
    if "python.venvFolders" in data:
        del data["python.venvFolders"]
        changed = True

    if not changed:
        return RegisterResult(
            ok=True,
            message=f"Nothing to remove from {editor.name}.",
            editor_id=editor.id,
        )

    try:
        _write_json(cfg, data)
    except Exception as e:
        return RegisterResult(
            ok=False,
            message=f"Failed to write {cfg}: {e}",
            backup_path=backup,
            editor_id=editor.id,
        )
    return RegisterResult(
        ok=True,
        message=f"Unregistered VenvStudio from {editor.name}.",
        backup_path=backup,
        editor_id=editor.id,
    )


# ── Zed ─────────────────────────────────────────────────────────────────────

def _register_zed(cfg: Path, venv_dir: Path, editor: EditorInfo) -> RegisterResult:
    data = _load_jsonc(cfg) if cfg.exists() else {}
    backup = _backup(cfg)

    path_str = str(venv_dir).replace("\\", "/")

    # Zed's Python settings live under a nested key.
    python_cfg = data.setdefault("python", {})
    if not isinstance(python_cfg, dict):
        python_cfg = {}
        data["python"] = python_cfg
    python_cfg["venv_path"] = path_str

    try:
        _write_json(cfg, data)
    except Exception as e:
        return RegisterResult(
            ok=False, message=f"Failed to write {cfg}: {e}",
            backup_path=backup, editor_id=editor.id,
        )
    return RegisterResult(
        ok=True,
        message=f"Registered '{path_str}' as Zed venv path.",
        backup_path=backup,
        editor_id=editor.id,
    )


def _unregister_zed(cfg: Path, editor: EditorInfo) -> RegisterResult:
    data = _load_jsonc(cfg)
    backup = _backup(cfg)

    python_cfg = data.get("python")
    changed = False
    if isinstance(python_cfg, dict) and "venv_path" in python_cfg:
        del python_cfg["venv_path"]
        if not python_cfg:
            del data["python"]
        changed = True

    if not changed:
        return RegisterResult(
            ok=True, message="Nothing to remove from Zed.", editor_id=editor.id,
        )

    try:
        _write_json(cfg, data)
    except Exception as e:
        return RegisterResult(
            ok=False, message=f"Failed to write {cfg}: {e}",
            backup_path=backup, editor_id=editor.id,
        )
    return RegisterResult(
        ok=True, message="Unregistered VenvStudio from Zed.",
        backup_path=backup, editor_id=editor.id,
    )


# ── PyCharm — drop a reminder only ──────────────────────────────────────────

def _pycharm_reminder_path() -> Path:
    """Where we store the PyCharm reminder so the user can find it."""
    return _home() / ".venvstudio" / "pycharm_venv_hint.txt"


def _register_pycharm(cfg: Path, venv_dir: Path, editor: EditorInfo) -> RegisterResult:
    reminder = _pycharm_reminder_path()
    reminder.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "VenvStudio venv path (for manual PyCharm SDK registration):\n"
        f"{venv_dir}\n\n"
        "To register in PyCharm:\n"
        "  1. File → Settings → Project → Python Interpreter\n"
        "  2. Gear icon → Add → Virtualenv Environment → Existing\n"
        f"  3. Point Interpreter to: {venv_dir}/<env-name>/bin/python "
        "(or Scripts\\python.exe on Windows)\n"
    )
    try:
        reminder.write_text(text, encoding="utf-8")
    except Exception as e:
        return RegisterResult(
            ok=False, message=f"Could not write reminder: {e}",
            editor_id=editor.id,
        )
    return RegisterResult(
        ok=True,
        message=f"PyCharm reminder saved to {reminder}. "
                f"Open PyCharm and register {venv_dir} manually.",
        editor_id=editor.id,
    )


def _unregister_pycharm(editor: EditorInfo) -> RegisterResult:
    reminder = _pycharm_reminder_path()
    if reminder.exists():
        try:
            reminder.unlink()
        except Exception as e:
            return RegisterResult(
                ok=False, message=f"Could not delete reminder: {e}",
                editor_id=editor.id,
            )
    return RegisterResult(
        ok=True,
        message="PyCharm reminder removed. The IDE itself was not modified.",
        editor_id=editor.id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience API for the GUI
# ─────────────────────────────────────────────────────────────────────────────

def register_all(venv_dir: Path, editor_ids: Optional[List[str]] = None) -> List[RegisterResult]:
    """Register VenvStudio with every installed editor (or a subset)."""
    detected = detect_editors()
    if editor_ids is not None:
        detected = [e for e in detected if e.id in editor_ids]
    results: List[RegisterResult] = []
    for ed in detected:
        if not ed.installed:
            continue
        results.append(register(ed, venv_dir))
    return results


def current_registered_path(editor: EditorInfo) -> Optional[str]:
    """Return whatever path is currently set in the editor's config (or None)."""
    cfg = editor.config_path
    if cfg is None or not cfg.exists():
        return None
    data = _load_jsonc(cfg)

    if _is_vscode_family(editor.id):
        v = data.get("python.venvPath")
        return v if isinstance(v, str) else None
    if editor.id == "zed":
        pc = data.get("python")
        if isinstance(pc, dict):
            v = pc.get("venv_path")
            return v if isinstance(v, str) else None
        return None
    if editor.id == "pycharm":
        reminder = _pycharm_reminder_path()
        if reminder.exists():
            try:
                text = reminder.read_text(encoding="utf-8")
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith(("VenvStudio", "To", " ", "#")) and "/" in line:
                        return line
            except Exception:
                return None
        return None
    return None
