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


def open_terminal_at(path: Path, terminal_type: str = "", env_type: str = "") -> None:
    """Open a terminal/console at the given path with the venv activated."""
    system = get_platform()

    try:
        if system == "windows":
            activate_bat = path / "Scripts" / "activate.bat"
            activate_ps1 = path / "Scripts" / "Activate.ps1"

            if terminal_type == "cmd":
                subprocess.Popen(
                    ["cmd", "/k", f"cd /d {path} && {activate_bat}"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                return

            elif terminal_type == "wt":
                subprocess.Popen(
                    ["wt", "-d", str(path), "cmd", "/k", str(activate_bat)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                return

            elif terminal_type == "git-bash":
                # Find Git Bash executable - NEVER use WSL bash (System32)
                git_bash = None
                for candidate in [
                    r"C:\Program Files\Gitinash.exe",
                    r"C:\Program Files (x86)\Gitinash.exe",
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "bin", "bash.exe"),
                    os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Programs", "Git", "bin", "bash.exe"),
                    os.path.join(os.environ.get("ProgramFiles", ""), "Git", "bin", "bash.exe"),
                ]:
                    if candidate and os.path.exists(candidate):
                        git_bash = candidate
                        break

                if git_bash:
                    activate_sh = path / "Scripts" / "activate"
                    # Convert Windows path to Unix path for bash
                    def to_unix(p):
                        s = str(p).replace("\\", "/")
                        if len(s) > 1 and s[1] == ":":
                            s = "/" + s[0].lower() + s[2:]
                        return s
                    bash_init = f"cd '{to_unix(path)}' && source '{to_unix(activate_sh)}' && exec bash -i"
                    subprocess.Popen(
                        [git_bash, "--login", "-i", "-c", bash_init],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        env={**os.environ, "MSYSTEM": "MINGW64"},
                    )
                    return
                # Git Bash not found, fall through to PowerShell

            # Conda on Windows: add env Scripts to PATH, no shell init needed
            if env_type == "conda":
                # Prepend conda env's Scripts/bin to PATH so conda packages work
                _scripts = str(path / "Scripts")
                _lib_bin = str(path / "Library" / "bin")
                _new_path = f"{_scripts};{_lib_bin};{os.environ.get('PATH', '')}"
                _env = {**os.environ, "PATH": _new_path, "CONDA_PREFIX": str(path),
                        "CONDA_DEFAULT_ENV": path.name}
                subprocess.Popen(
                    ["cmd", "/k", f'cd /d "{path}" && echo Conda env: {path.name} activated'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    env=_env,
                )
                return

            # Default: PowerShell
            if activate_ps1.exists():
                subprocess.Popen(
                    ["powershell", "-NoExit", "-Command",
                     f"Set-Location '{path}'; & '{activate_ps1}'"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            elif activate_bat.exists():
                subprocess.Popen(
                    ["cmd", "/k", f"cd /d {path} && {activate_bat}"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                # pipx or other env types without activate script — just open terminal at path
                subprocess.Popen(
                    ["powershell", "-NoExit", "-Command", f"Set-Location '{path}'"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )

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
            # Detect env type from marker — always read marker, env_type is just a hint
            _marker = path / ".venvstudio_env"
            _env_type = "venv"
            if _marker.exists():
                try:
                    import json as _json
                    with open(_marker) as _mf:
                        _env_type = _json.load(_mf).get("type", env_type or "venv")
                except Exception:
                    pass
            elif env_type:
                _env_type = env_type

            activate = path / "bin" / "activate"

            if _env_type == "pipx":
                # pipx has no activate — just open terminal at pipx home
                bash_cmd = f"cd '{path}' && exec bash"
            elif _env_type == "poetry":
                # Poetry stores actual venv in ~/.cache/pypoetry/virtualenvs/
                _poetry_venv = None
                try:
                    import json as _json2
                    with open(_marker) as _mf2:
                        _poetry_venv = _json2.load(_mf2).get("poetry_venv_path", "")
                except Exception:
                    pass
                if _poetry_venv and Path(_poetry_venv).exists():
                    _pa = Path(_poetry_venv) / "bin" / "activate"
                    bash_cmd = f"cd '{_poetry_venv}' && source '{_pa}' && exec bash"
                else:
                    bash_cmd = f"cd '{path}' && exec bash"
            elif _env_type == "conda":
                # conda activate via micromamba or conda
                _mamba = shutil.which("micromamba") or shutil.which("conda")
                if _mamba:
                    bash_cmd = (
                        f"cd '{path}' && "
                        f"{_mamba} activate '{path}' 2>/dev/null; "
                        f"exec bash"
                    )
                else:
                    bash_cmd = f"cd '{path}' && exec bash"
            elif activate.exists():
                bash_cmd = f"cd '{path}' && source '{activate}' && exec bash"
            else:
                bash_cmd = f"cd '{path}' && exec bash"

            def _launch_linux_terminal(term: str) -> bool:
                """Try to launch a specific terminal. Returns True on success."""
                if not shutil.which(term):
                    return False
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", "bash", "-c", bash_cmd])
                    elif term in ("konsole", "yakuake"):
                        subprocess.Popen([term, "--noclose", "-e", "bash", "-c", bash_cmd])
                    elif term in ("xfce4-terminal", "mate-terminal", "lxterminal", "tilix"):
                        subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"])
                    elif term == "kitty":
                        subprocess.Popen([term, "bash", "-c", bash_cmd])
                    elif term == "alacritty":
                        subprocess.Popen([term, "-e", "bash", "-c", bash_cmd])
                    elif term == "wezterm":
                        subprocess.Popen([term, "start", "--", "bash", "-c", bash_cmd])
                    else:
                        # xterm, x-terminal-emulator and others
                        subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"])
                    return True
                except Exception:
                    return False

            # Explicit terminal selected (not "default" or empty)
            if terminal_type and terminal_type not in ("", "default"):
                if _launch_linux_terminal(terminal_type):
                    return  # success, done

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


def launch_in_terminal(cmd: list, cwd: str = "", terminal_type: str = "") -> bool:
    """Launch a command in a new terminal window (for console apps like IPython).
    Uses the same terminal auto-detection as open_terminal_at.
    Returns True if launched successfully.
    """
    system = get_platform()
    cmd_str = " ".join(f'"{c}"' for c in cmd)
    bash_cmd = f"{cmd_str}; echo ''; read -p 'Press Enter to close...'"

    if system == "windows":
        try:
            subprocess.Popen(
                cmd,
                cwd=cwd or None,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return True
        except Exception:
            return False

    elif system == "macos":
        try:
            script = f'tell application "Terminal" to do script "cd \'{cwd}\' && {cmd_str}"'
            subprocess.Popen(["osascript", "-e", script])
            return True
        except Exception:
            return False

    else:  # linux
        # Clean AppImage env vars so terminal processes don't inherit LD_LIBRARY_PATH etc.
        try:
            from src.utils.platform_utils import appimage_clean_env as _ace
            _term_env = _ace()
        except Exception:
            _term_env = None
        _term_kw = {"env": _term_env} if _term_env is not None else {}

        def _try_term(term: str) -> bool:
            if not shutil.which(term):
                return False
            try:
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term in ("konsole", "yakuake"):
                    subprocess.Popen([term, "--noclose", "-e", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term in ("xfce4-terminal", "mate-terminal", "lxterminal", "tilix"):
                    subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"], cwd=cwd or None, **_term_kw)
                elif term == "kitty":
                    subprocess.Popen([term, "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term == "alacritty":
                    subprocess.Popen([term, "-e", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                elif term == "wezterm":
                    subprocess.Popen([term, "start", "--", "bash", "-c", bash_cmd], cwd=cwd or None, **_term_kw)
                else:
                    subprocess.Popen([term, "-e", f"bash -c '{bash_cmd}'"], cwd=cwd or None, **_term_kw)
                return True
            except Exception:
                return False

        # Try explicit terminal first
        if terminal_type and terminal_type not in ("", "default"):
            if _try_term(terminal_type):
                return True

        # Auto-detect
        auto_order = [
            "gnome-terminal", "konsole", "xfce4-terminal",
            "tilix", "mate-terminal", "alacritty", "kitty",
            "wezterm", "lxterminal", "xterm", "x-terminal-emulator",
        ]
        for term in auto_order:
            if _try_term(term):
                return True

        # Last resort: run in-place (blocks but better than nothing)
        try:
            subprocess.Popen(cmd, cwd=cwd or None)
            return True
        except Exception:
            return False


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
