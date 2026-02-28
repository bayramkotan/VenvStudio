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
    """Return the default base directory for virtual environments."""
    system = get_platform()
    if system == "windows":
        return Path("C:/venv")
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


def _is_user_python(path: str) -> bool:
    """Return True if this Python is a user-level install.
    Covers: AppData, .local/bin, pyenv, conda user env, pipx — all under home dir.
    Does NOT flag /usr/local (Homebrew system-wide).
    """
    norm = os.path.normpath(path).lower()
    home = os.path.expanduser("~").lower()

    # Must be under home directory to be user-level
    if home not in norm:
        return False

    # Known user-level subdirs under home
    user_subdirs = [
        ".local",          # Linux pip user install
        "appdata",         # Windows pip user install
        ".pyenv",          # pyenv
        ".conda",          # conda user env
        "miniconda",       # miniconda in home
        "anaconda",        # anaconda in home
        "miniforge",       # miniforge in home
        ".rye",            # rye
        ".uv",             # uv
        "pipx",            # pipx
    ]
    return any(sub in norm for sub in user_subdirs)



def find_system_pythons() -> List[Tuple[str, str]]:
    """
    Find available Python installations on the system.
    Returns list of (version_string, executable_path) tuples.
    Skips user-level installs (AppData, .local/bin) to avoid duplicates.
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

        # User-level installs filtrele (AppData, .local/bin)
        if _is_user_python(exe_path):
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
            bash_cmd = f"cd '{path}' && source '{activate}' && exec bash"

            # AppImage: restore host system PATH so terminals can be found
            host_env = os.environ.copy()
            if "APPDIR" in os.environ or "APPIMAGE" in os.environ:
                # Remove AppImage-injected paths, restore original PATH
                original_path = os.environ.get("PATH_ORIG", os.environ.get("PATH", ""))
                # Also add common terminal locations
                extra = "/usr/bin:/usr/local/bin:/bin:/snap/bin:/usr/games"
                host_env["PATH"] = original_path + ":" + extra
                # Unset Qt/library overrides that would confuse the terminal
                for var in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                            "LD_LIBRARY_PATH", "LD_PRELOAD"):
                    host_env.pop(var, None)

            def _find_term(term: str) -> str:
                """Find terminal executable, checking host PATH for AppImage."""
                found = shutil.which(term, path=host_env.get("PATH"))
                return found or ""

            def _launch_linux_terminal(term: str) -> bool:
                """Try to launch a specific terminal. Returns True on success."""
                exe = _find_term(term)
                if not exe:
                    return False
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen([exe, "--", "bash", "-c", bash_cmd], env=host_env)
                    elif term in ("konsole", "yakuake"):
                        subprocess.Popen([exe, "--noclose", "-e", "bash", "-c", bash_cmd], env=host_env)
                    elif term in ("xfce4-terminal", "mate-terminal", "lxterminal", "tilix"):
                        subprocess.Popen([exe, "-e", f"bash -c '{bash_cmd}'"], env=host_env)
                    elif term == "kitty":
                        subprocess.Popen([exe, "bash", "-c", bash_cmd], env=host_env)
                    elif term == "alacritty":
                        subprocess.Popen([exe, "-e", "bash", "-c", bash_cmd], env=host_env)
                    elif term == "wezterm":
                        subprocess.Popen([exe, "start", "--", "bash", "-c", bash_cmd], env=host_env)
                    else:
                        subprocess.Popen([exe, "-e", f"bash -c '{bash_cmd}'"], env=host_env)
                    return True
                except Exception:
                    return False

            # Explicit terminal selected (not "default" or empty)
            if terminal_type and terminal_type not in ("", "default"):
                if _launch_linux_terminal(terminal_type):
                    return

            # Auto-detect: try common terminals in order of preference
            auto_order = [
                "gnome-terminal", "konsole", "xfce4-terminal",
                "tilix", "mate-terminal", "alacritty", "kitty",
                "wezterm", "lxterminal", "xterm", "x-terminal-emulator",
            ]
            for term in auto_order:
                if _launch_linux_terminal(term):
                    break
    except Exception as e:
        print(f"Could not open terminal: {e}")


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
