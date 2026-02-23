"""
VenvStudio - Platform-specific utilities
Cross-platform support for Windows, macOS, and Linux
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple


# ── Windows console suppression ──
# Windows'ta subprocess çağrılarında konsol penceresi açılmasını engelle
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def subprocess_args(**kwargs):
    """Add CREATE_NO_WINDOW on Windows to suppress console flashing.
    Use: subprocess.run(cmd, **subprocess_args(capture_output=True, text=True))
    """
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return kwargs


def get_platform() -> str:
    """Return normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system  # 'windows' or 'linux'


def get_default_venv_base_dir() -> Path:
    """Return the default base directory for virtual environments.
    On Windows, falls back to D:/venv, E:/venv if C: is unavailable or has < 500 MB free.
    """
    system = get_platform()
    if system == "windows":
        import shutil
        for letter in ["C", "D", "E", "F"]:
            drive = Path(f"{letter}:/")
            if not drive.exists():
                continue
            try:
                usage = shutil.disk_usage(str(drive))
                if usage.free < 500 * 1024 * 1024:  # 500 MB minimum
                    continue
            except Exception:
                pass  # If we can't check space, assume it's OK
            return Path(f"{letter}:/venv")
        return Path.home() / "venv"  # Last resort
    elif system == "macos":
        return Path.home() / "venv"
    else:  # linux
        return Path.home() / "venv"


def get_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    system = get_platform()
    if system == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config_dir = base / "VenvStudio"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_python_executable(venv_path: Path) -> Path:
    """Return the python executable path inside a venv."""
    if get_platform() == "windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def get_pip_executable(venv_path: Path) -> Path:
    """Return the pip executable path inside a venv."""
    if get_platform() == "windows":
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


def get_activate_command(venv_path: Path) -> str:
    """Return the activation command for a venv (for display purposes)."""
    system = get_platform()
    if system == "windows":
        return str(venv_path / "Scripts" / "activate.bat")
    return f"source {venv_path / 'bin' / 'activate'}"


def find_system_pythons() -> List[Tuple[str, str]]:
    """
    Find available Python installations on the system.
    Returns list of (version_string, executable_path) tuples.
    """
    pythons = []
    seen_versions = set()
    seen_paths = set()

    candidates = ["python3", "python"]
    for major in [3]:
        for minor in range(6, 15):
            candidates.append(f"python{major}.{minor}")

    for candidate in candidates:
        exe_path = shutil.which(candidate)
        if not exe_path:
            continue

        # Windows Store alias filtrele
        normalized = os.path.normpath(exe_path).lower()
        if "windowsapps" in normalized:
            continue

        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)

        try:
            result = subprocess.run(
                [exe_path, "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            version = result.stdout.strip() or result.stderr.strip()
            version = version.replace("Python ", "")

            # Versiyon numarası formatını kontrol et (x.y.z)
            if not version or not version[0].isdigit():
                continue

            if version not in seen_versions:
                seen_versions.add(version)
                pythons.append((version, exe_path))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

    pythons.sort(key=lambda x: x[0], reverse=True)
    return pythons


def open_terminal_at(path: Path, terminal_type: str = "") -> None:
    """Open a terminal/console at the given path with the venv activated."""
    system = get_platform()

    try:
        if system == "windows":
            activate_bat = path / "Scripts" / "activate.bat"
            activate_ps1 = path / "Scripts" / "Activate.ps1"

            if terminal_type == "cmd":
                cmd = f'start cmd /k "cd /d {path} && {activate_bat}"'
            elif terminal_type == "wt":
                cmd = f'start wt -d "{path}" cmd /k "{activate_bat}"'
            elif terminal_type == "git-bash":
                git_bash = shutil.which("bash")
                if git_bash:
                    activate_sh = path / "Scripts" / "activate"
                    cmd = f'start "" "{git_bash}" --login -c "cd \'{path}\' && source \'{activate_sh}\' && exec bash"'
                else:
                    cmd = f'start cmd /k "cd /d {path} && {activate_bat}"'
            else:
                # Default: PowerShell
                if activate_ps1.exists():
                    cmd = (
                        f'start powershell -NoExit -Command "'
                        f'Set-Location \'{path}\'; '
                        f'& \'{activate_ps1}\'"'
                    )
                else:
                    cmd = f'start cmd /k "cd /d {path} && {activate_bat}"'

            subprocess.Popen(cmd, shell=True)

        elif system == "macos":
            activate = path / "bin" / "activate"
            if terminal_type == "iterm2":
                script = (
                    f'tell application "iTerm" to create window with default profile '
                    f'command "cd \'{path}\' && source \'{activate}\'"'
                )
            else:
                script = (
                    f'tell application "Terminal" to do script '
                    f'"cd \'{path}\' && source \'{activate}\'"'
                )
            subprocess.Popen(["osascript", "-e", script])

        else:  # linux
            activate = path / "bin" / "activate"
            # Use double quotes inside bash_cmd to avoid single-quote path issues
            bash_cmd = f'cd "{path}" && source "{activate}" && exec bash'

            # Ensure DISPLAY and DBUS are passed to subprocess (needed when launched via python main.py)
            import os as _os
            env = _os.environ.copy()
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"

            def _popen(cmd):
                subprocess.Popen(cmd, env=env, start_new_session=True)

            # Terminal preference list with correct argument styles
            terminal_args = {
                "gnome-terminal":  lambda: ["gnome-terminal", "--", "bash", "-c", bash_cmd],
                "konsole":         lambda: ["konsole", "-e", "bash", "-c", bash_cmd],
                "xfce4-terminal":  lambda: ["xfce4-terminal", "-e", f"bash -c {bash_cmd!r}"],
                "tilix":           lambda: ["tilix", "-e", "bash", "-c", bash_cmd],
                "mate-terminal":   lambda: ["mate-terminal", "-e", f"bash -c {bash_cmd!r}"],
                "alacritty":       lambda: ["alacritty", "-e", "bash", "-c", bash_cmd],
                "kitty":           lambda: ["kitty", "bash", "-c", bash_cmd],
                "wezterm":         lambda: ["wezterm", "start", "bash", "-c", bash_cmd],
                "lxterminal":      lambda: ["lxterminal", "-e", f"bash -c {bash_cmd!r}"],
                "xterm":           lambda: ["xterm", "-e", f"bash -c {bash_cmd!r}"],
            }

            # If specific terminal requested
            if terminal_type and terminal_type in terminal_args and shutil.which(terminal_type):
                _popen(terminal_args[terminal_type]())
            else:
                # Auto-detect: try each in order
                launched = False
                for term, args_fn in terminal_args.items():
                    if shutil.which(term):
                        try:
                            _popen(args_fn())
                            launched = True
                            break
                        except Exception:
                            continue
                if not launched:
                    # Last resort: xdg-terminal or x-terminal-emulator
                    for fallback in ["x-terminal-emulator", "xdg-terminal"]:
                        if shutil.which(fallback):
                            try:
                                _popen([fallback, "-e", f"bash -c {bash_cmd!r}"])
                                break
                            except Exception:
                                pass
    except Exception as e:
        import traceback
        print(f"Could not open terminal: {e}")
        traceback.print_exc()


def get_venv_size(venv_path: Path) -> str:
    """Calculate and return human-readable size of a venv directory."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(venv_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
    except OSError:
        return "N/A"

    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"
