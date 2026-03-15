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
    Searches PATH, Windows Registry, and known install directories.
    No version range limit — future-proof.
    """
    pythons = []
    seen_paths = set()

    def _try_add(exe_path: str):
        if not exe_path or not os.path.isfile(exe_path):
            return
        normalized = os.path.normcase(os.path.normpath(exe_path))
        if "windowsapps" in normalized:
            return
        if normalized in seen_paths:
            return
        seen_paths.add(normalized)
        try:
            result = subprocess.run(
                [exe_path, "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            if version and version[0].isdigit():
                pythons.append((version, exe_path))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # 1) PATH'deki python / python3 komutları
    for candidate in ["python", "python3"]:
        exe = shutil.which(candidate)
        if exe:
            _try_add(exe)

    # 2) Windows: Registry + bilinen kurulum dizinleri
    if os.name == "nt":
        try:
            import winreg
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                for reg_path in [
                    r"SOFTWARE\Python\PythonCore",
                    r"SOFTWARE\WOW6432Node\Python\PythonCore",
                ]:
                    try:
                        with winreg.OpenKey(hive, reg_path) as key:
                            i = 0
                            while True:
                                try:
                                    ver = winreg.EnumKey(key, i)
                                    i += 1
                                    with winreg.OpenKey(key, ver + r"\InstallPath") as ip:
                                        install_dir = winreg.QueryValue(ip, None)
                                        exe = os.path.join(install_dir.rstrip("\\"), "python.exe")
                                        _try_add(exe)
                                except OSError:
                                    break
                    except OSError:
                        continue
        except ImportError:
            pass

        # Bilinen Windows kurulum dizinleri
        search_roots = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
            os.path.expanduser("~"),
        ]
        for root in search_roots:
            if not root or not os.path.isdir(root):
                continue
            try:
                for entry in os.scandir(root):
                    if entry.is_dir() and entry.name.lower().startswith("python"):
                        exe = os.path.join(entry.path, "python.exe")
                        _try_add(exe)
            except PermissionError:
                continue

    # 3) Linux/macOS: /usr/bin, /usr/local/bin, pyenv, .local/bin
    else:
        search_dirs = [
            "/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/.pyenv/shims"),
        ]
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for entry in os.scandir(d):
                    if entry.name.startswith("python") and entry.is_file():
                        _try_add(entry.path)
            except PermissionError:
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

            # AppImage bundles override PATH — resolve the real system PATH
            # so we can find terminal emulators installed on the host.
            host_path = os.environ.get("PATH", "")
            # Prepend standard system dirs that AppImage may have removed
            system_dirs = [
                "/usr/local/bin", "/usr/bin", "/bin",
                "/usr/local/sbin", "/usr/sbin", "/sbin",
                os.path.expanduser("~/.local/bin"),
            ]
            for d in reversed(system_dirs):
                if d not in host_path:
                    host_path = d + ":" + host_path

            # Find real system bash (not AppImage's bundled one)
            system_bash = "/bin/bash"
            for d in ["/usr/bin", "/bin", "/usr/local/bin"]:
                candidate = os.path.join(d, "bash")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    system_bash = candidate
                    break

            # Use --rcfile trick: bash reads our activation script as rc,
            # so the terminal stays open with the venv activated.
            # This is more reliable than "bash -c '... && exec bash'"
            bash_cmd = f"cd '{path}' && source '{activate}' && exec {system_bash}"

            def _find_terminal(term: str) -> Optional[str]:
                """Find terminal executable, checking system PATH even inside AppImage."""
                # First try normal which
                found = shutil.which(term)
                if found:
                    return found
                # Search system dirs manually (AppImage may hide them)
                for d in system_dirs:
                    candidate = os.path.join(d, term)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                        return candidate
                return None

            def _launch_linux_terminal(term: str) -> bool:
                """Try to launch a specific terminal. Returns True on success."""
                term_exe = _find_terminal(term)
                if not term_exe:
                    return False

                # Clean environment for the child process:
                # Remove AppImage-specific env vars so the terminal behaves normally
                clean_env = os.environ.copy()
                clean_env["PATH"] = host_path
                for appimage_var in ("APPIMAGE", "APPDIR", "OWD",
                                     "ARGV0", "APPIMAGE_EXTRACT_AND_RUN"):
                    clean_env.pop(appimage_var, None)
                # Remove LD_LIBRARY_PATH/LD_PRELOAD that AppImage may set
                # (these can break host terminal apps)
                for ld_var in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
                    clean_env.pop(ld_var, None)

                try:
                    if term == "gnome-terminal":
                        subprocess.Popen(
                            [term_exe, "--", system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    elif term in ("konsole", "yakuake"):
                        subprocess.Popen(
                            [term_exe, "--noclose", "-e", system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    elif term in ("xfce4-terminal", "mate-terminal", "lxterminal", "tilix"):
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} -c '{bash_cmd}'"],
                            env=clean_env
                        )
                    elif term == "kitty":
                        subprocess.Popen(
                            [term_exe, system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    elif term == "alacritty":
                        subprocess.Popen(
                            [term_exe, "-e", system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    elif term == "wezterm":
                        subprocess.Popen(
                            [term_exe, "start", "--", system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    elif term == "foot":
                        subprocess.Popen(
                            [term_exe, system_bash, "-c", bash_cmd],
                            env=clean_env
                        )
                    else:
                        # xterm, x-terminal-emulator and others
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} -c '{bash_cmd}'"],
                            env=clean_env
                        )
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
                "wezterm", "foot", "lxterminal", "xterm", "x-terminal-emulator",
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
