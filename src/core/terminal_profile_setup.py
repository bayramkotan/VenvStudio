"""
Terminal Profile Setup (F172)
==============================

After installing a Nerd Font and an oh-my-posh / Starship theme, the user's
default terminal still uses its old (non-Nerd) font, so the prompt renders
broken glyphs (□ characters) instead of nice icons.

This module creates a NEW profile in the user's terminal emulator with the
Nerd Font applied, so the user can simply switch to that profile and see a
working prompt.

Linux-first implementation. Each terminal emulator has its own config
mechanism — we ship adapters for the most common ones.

Public API
----------
- detect_terminal() -> str | None
    Best-guess identifier of the user's terminal emulator.
    Returns one of: "gnome-terminal", "mate-terminal", "konsole",
    "xfce4-terminal", "tilix", "alacritty", "kitty", "wezterm", or None.

- supported_terminals() -> list[str]
    Terminals we know how to write a profile for.

- create_nerd_font_profile(terminal, font_family, profile_name="VenvStudio Posh",
                            set_default=False) -> tuple[bool, str]
    Create the profile. Returns (ok, message). Never raises — always
    returns a human-readable message.

Future work
-----------
Windows Terminal (settings.json), iTerm2 (plist) — sonraki sprintte.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional


SYSTEM = platform.system()


# ── Detection ────────────────────────────────────────────────────────────────

_TERMINAL_ENV_HINTS = {
    "gnome-terminal":  ("GNOME_TERMINAL_SCREEN", "GNOME_TERMINAL_SERVICE"),
    "mate-terminal":   ("MATE_TERMINAL_VERSION",),
    "konsole":         ("KONSOLE_VERSION", "KONSOLE_DBUS_SESSION"),
    "xfce4-terminal":  ("XFCE4_TERMINAL_VERSION",),  # rarely set, fallback to which
    "tilix":           ("TILIX_ID",),
    "alacritty":       ("ALACRITTY_LOG", "ALACRITTY_SOCKET"),
    "kitty":           ("KITTY_WINDOW_ID", "KITTY_PID"),
    "wezterm":         ("WEZTERM_PANE", "WEZTERM_EXECUTABLE"),
}


def detect_terminal() -> Optional[str]:
    """Best-guess the user's terminal emulator."""
    # 1) Env-var hints (most reliable when present)
    for term, env_keys in _TERMINAL_ENV_HINTS.items():
        for k in env_keys:
            if os.environ.get(k):
                return term

    # 2) TERM_PROGRAM (set by some)
    tp = os.environ.get("TERM_PROGRAM", "").lower()
    for known in ("kitty", "wezterm", "alacritty", "konsole"):
        if known in tp:
            return known

    # 3) Walk parent processes (works on Linux even outside the terminal env)
    try:
        ppid = os.getppid()
        # Up to 6 levels up
        for _ in range(6):
            try:
                with open(f"/proc/{ppid}/comm", "r") as f:
                    name = f.read().strip().lower()
                for known in ("gnome-terminal", "mate-terminal", "konsole",
                              "xfce4-terminal", "tilix", "alacritty",
                              "kitty", "wezterm"):
                    if known.replace("-", "") in name.replace("-", ""):
                        # Some show "gnome-terminal-" trimmed in comm
                        return known
                with open(f"/proc/{ppid}/status", "r") as f:
                    for line in f:
                        if line.startswith("PPid:"):
                            ppid = int(line.split()[1])
                            break
                    else:
                        break
            except (OSError, ValueError):
                break
    except Exception:
        pass

    return None


def supported_terminals() -> list[str]:
    """Terminals this module knows how to write a profile for."""
    return ["gnome-terminal", "mate-terminal", "konsole",
            "alacritty", "kitty", "wezterm"]


# ── Profile creation dispatcher ──────────────────────────────────────────────

def create_nerd_font_profile(terminal: str,
                             font_family: str,
                             profile_name: str = "VenvStudio Posh",
                             font_size: int = 11,
                             set_default: bool = False) -> tuple[bool, str]:
    """Create a new terminal profile with the given Nerd Font.

    Returns (ok, message). The message is user-facing.
    """
    handlers = {
        "gnome-terminal":  _setup_gnome_terminal,
        "mate-terminal":   _setup_mate_terminal,
        "konsole":         _setup_konsole,
        "alacritty":       _setup_alacritty,
        "kitty":           _setup_kitty,
        "wezterm":         _setup_wezterm,
    }
    handler = handlers.get(terminal)
    if handler is None:
        return False, (
            f"Automatic profile creation is not yet supported for '{terminal}'.\n"
            f"Please open your terminal preferences and set the font to: {font_family}"
        )
    try:
        return handler(font_family, profile_name, font_size, set_default)
    except Exception as e:
        return False, f"Failed to create profile: {type(e).__name__}: {e}"


# ── GNOME Terminal (dconf) ───────────────────────────────────────────────────

_GNOME_PROFILES_KEY = "/org/gnome/terminal/legacy/profiles:/"


def _setup_gnome_terminal(font_family: str, profile_name: str,
                          font_size: int, set_default: bool) -> tuple[bool, str]:
    if shutil.which("dconf") is None:
        return False, "dconf command not found — cannot configure GNOME Terminal automatically."

    profile_uuid = str(uuid.uuid4())
    base = f"{_GNOME_PROFILES_KEY}:{profile_uuid}/"
    font_str = f"{font_family} {font_size}"

    # 1) Append to the profile list
    list_key = f"{_GNOME_PROFILES_KEY}list"
    current_list = _dconf_read(list_key) or "[]"
    # current_list is like "['uuid1', 'uuid2']"
    new_list = _append_to_dconf_list(current_list, profile_uuid)
    _dconf_write(list_key, new_list)

    # 2) Write the new profile values
    _dconf_write(f"{base}visible-name", f"'{profile_name}'")
    _dconf_write(f"{base}use-system-font", "false")
    _dconf_write(f"{base}font", f"'{font_str}'")

    # 3) Optionally set as default
    if set_default:
        _dconf_write(f"{_GNOME_PROFILES_KEY}default", f"'{profile_uuid}'")

    msg = (
        f"✅ GNOME Terminal profile '{profile_name}' created with font '{font_str}'.\n"
        f"   Open a new terminal → Right-click → Profiles → {profile_name}"
    )
    if set_default:
        msg += "\n   This profile is now the default."
    return True, msg


# ── MATE Terminal (dconf, slightly different schema) ─────────────────────────

_MATE_PROFILES_KEY = "/org/mate/terminal/profiles/"


def _setup_mate_terminal(font_family: str, profile_name: str,
                         font_size: int, set_default: bool) -> tuple[bool, str]:
    if shutil.which("dconf") is None:
        return False, "dconf command not found — cannot configure MATE Terminal automatically."

    # MATE uses a slug (not uuid) for the profile name
    slug = profile_name.lower().replace(" ", "-")
    base = f"{_MATE_PROFILES_KEY}{slug}/"
    font_str = f"{font_family} {font_size}"

    # Add to global list
    list_key = "/org/mate/terminal/global/profile-list"
    current_list = _dconf_read(list_key) or "[]"
    new_list = _append_to_dconf_list(current_list, slug)
    _dconf_write(list_key, new_list)

    # Write profile values
    _dconf_write(f"{base}visible-name", f"'{profile_name}'")
    _dconf_write(f"{base}use-system-font", "false")
    _dconf_write(f"{base}font", f"'{font_str}'")

    if set_default:
        _dconf_write("/org/mate/terminal/global/default-profile", f"'{slug}'")

    msg = (
        f"✅ MATE Terminal profile '{profile_name}' created with font '{font_str}'.\n"
        f"   Open a new terminal → Edit → Profiles → {profile_name}"
    )
    if set_default:
        msg += "\n   This profile is now the default."
    return True, msg


# ── KDE Konsole (file-based) ─────────────────────────────────────────────────

def _setup_konsole(font_family: str, profile_name: str,
                   font_size: int, set_default: bool) -> tuple[bool, str]:
    profiles_dir = Path.home() / ".local" / "share" / "konsole"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    safe_name = profile_name.replace(" ", "_")
    profile_file = profiles_dir / f"{safe_name}.profile"
    profile_file.write_text(
        "[Appearance]\n"
        f"Font={font_family},{font_size},-1,5,50,0,0,0,0,0\n"
        "\n"
        "[General]\n"
        f"Name={profile_name}\n"
        "Parent=FALLBACK/\n",
        encoding="utf-8",
    )

    msg = (
        f"✅ Konsole profile written to {profile_file}\n"
        f"   Open Konsole → Settings → Manage Profiles → select '{profile_name}'"
    )
    if set_default:
        # konsolerc default profile setting
        konsolerc = Path.home() / ".config" / "konsolerc"
        try:
            existing = konsolerc.read_text(encoding="utf-8") if konsolerc.exists() else ""
            if "[Desktop Entry]" not in existing:
                existing += "\n[Desktop Entry]\n"
            if "DefaultProfile=" in existing:
                # Replace existing
                lines = []
                for ln in existing.splitlines():
                    if ln.startswith("DefaultProfile="):
                        lines.append(f"DefaultProfile={safe_name}.profile")
                    else:
                        lines.append(ln)
                existing = "\n".join(lines)
            else:
                existing += f"DefaultProfile={safe_name}.profile\n"
            konsolerc.write_text(existing, encoding="utf-8")
            msg += "\n   This profile is now the default."
        except Exception as e:
            msg += f"\n   ⚠ Could not set as default: {e}"
    return True, msg


# ── Alacritty (YAML/TOML) ────────────────────────────────────────────────────

def _setup_alacritty(font_family: str, profile_name: str,
                     font_size: int, set_default: bool) -> tuple[bool, str]:
    # Alacritty has a single config file, not profiles. We append a comment
    # block + override snippet that the user can uncomment.
    cfg_dir = Path.home() / ".config" / "alacritty"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    # Prefer TOML (modern alacritty). Fall back to a profile file alongside.
    profile_file = cfg_dir / f"{profile_name.replace(' ', '_')}.toml"
    profile_file.write_text(
        f"# {profile_name} — VenvStudio generated\n"
        "[font]\n"
        f'size = {font_size}\n'
        "[font.normal]\n"
        f'family = "{font_family}"\n'
        f'style = "Regular"\n'
        "[font.bold]\n"
        f'family = "{font_family}"\n'
        f'style = "Bold"\n'
        "[font.italic]\n"
        f'family = "{font_family}"\n'
        f'style = "Italic"\n',
        encoding="utf-8",
    )
    msg = (
        f"✅ Alacritty profile written to {profile_file}\n"
        f"   To use it, add this line to your alacritty.toml:\n"
        f'     import = ["{profile_file}"]'
    )
    if set_default:
        msg += "\n   ⚠ Setting as default requires editing alacritty.toml manually (Alacritty has no profile selector)."
    return True, msg


# ── Kitty ────────────────────────────────────────────────────────────────────

def _setup_kitty(font_family: str, profile_name: str,
                 font_size: int, set_default: bool) -> tuple[bool, str]:
    cfg_dir = Path.home() / ".config" / "kitty"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    profile_file = cfg_dir / f"{profile_name.replace(' ', '_')}.conf"
    profile_file.write_text(
        f"# {profile_name} — VenvStudio generated\n"
        f"font_family      {font_family}\n"
        f"bold_font        {font_family} Bold\n"
        f"italic_font      {font_family} Italic\n"
        f"font_size        {font_size}\n",
        encoding="utf-8",
    )
    msg = (
        f"✅ Kitty profile written to {profile_file}\n"
        f"   Use it by running: kitty --config {profile_file}"
    )
    if set_default:
        # Append `include` to main kitty.conf
        main_cfg = cfg_dir / "kitty.conf"
        try:
            existing = main_cfg.read_text(encoding="utf-8") if main_cfg.exists() else ""
            include_line = f"include {profile_file.name}\n"
            if include_line not in existing:
                existing = existing.rstrip() + "\n# VenvStudio profile\n" + include_line
                main_cfg.write_text(existing, encoding="utf-8")
            msg += f"\n   Included in {main_cfg} (restart kitty to apply)."
        except Exception as e:
            msg += f"\n   ⚠ Could not update kitty.conf: {e}"
    return True, msg


# ── WezTerm (Lua) ────────────────────────────────────────────────────────────

def _setup_wezterm(font_family: str, profile_name: str,
                   font_size: int, set_default: bool) -> tuple[bool, str]:
    cfg_dir = Path.home() / ".config" / "wezterm"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    snippet = (
        f"-- {profile_name} — VenvStudio generated\n"
        "-- Add this to your wezterm.lua's config table:\n"
        f'-- config.font = wezterm.font("{font_family}")\n'
        f"-- config.font_size = {font_size}\n"
    )
    snippet_file = cfg_dir / f"{profile_name.replace(' ', '_')}.lua"
    snippet_file.write_text(snippet, encoding="utf-8")
    return True, (
        f"✅ WezTerm snippet written to {snippet_file}\n"
        f"   Edit ~/.config/wezterm/wezterm.lua and add:\n"
        f'     config.font = wezterm.font("{font_family}")\n'
        f"     config.font_size = {font_size}"
    )


# ── dconf helpers ────────────────────────────────────────────────────────────

def _dconf_read(key: str) -> Optional[str]:
    try:
        r = subprocess.run(["dconf", "read", key], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _dconf_write(key: str, value: str) -> bool:
    try:
        r = subprocess.run(["dconf", "write", key, value],
                           capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _append_to_dconf_list(current: str, item: str) -> str:
    """Append item to a dconf list literal like ['a', 'b'] → ['a', 'b', 'item']."""
    s = current.strip()
    if not s or s in ("[]", "@as []"):
        return f"['{item}']"
    # Strip leading "@as " type hint if present
    if s.startswith("@as "):
        s = s[4:].strip()
    if not (s.startswith("[") and s.endswith("]")):
        return f"['{item}']"
    inner = s[1:-1].strip()
    if item in inner:
        return s  # already there
    if not inner:
        return f"['{item}']"
    return f"[{inner}, '{item}']"
