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

# AppImage variables that cause re-launch when inherited by subprocesses
_APPIMAGE_VARS = frozenset({
    # AppImage re-launch / identity vars
    "APPIMAGE", "APPDIR", "ARGV0", "OWD",
    "APPIMAGE_EXTRACT_AND_RUN", "APPIMAGE_STARTUP_NET_WM_PID",
    # Library path vars AppImage injects — these break PyQt5/PyQtWebEngine
    # installed inside a venv because the linker finds AppImage's .so first
    "LD_LIBRARY_PATH", "LD_PRELOAD",
    # Python path vars AppImage may set — would shadow venv's site-packages
    "PYTHONPATH", "PYTHONHOME",
    # GLib/GDK module dirs AppImage sets — can conflict with PyQt5's platform plugins
    "GDK_PIXBUF_MODULEDIR", "GDK_PIXBUF_MODULE_FILE",
    "GIO_MODULE_DIR", "GIO_EXTRA_MODULES",
    "GSETTINGS_SCHEMA_DIR",
    "XDG_DATA_DIRS",   # AppImage prepends its own share/ — can confuse Qt theme lookup
})


def appimage_clean_env() -> dict | None:
    """
    If running inside an AppImage, return a cleaned copy of os.environ
    with AppImage re-launch variables stripped out.
    Returns None if not inside an AppImage (no overhead).
    """
    if not os.environ.get("APPIMAGE"):
        return None
    return {k: v for k, v in os.environ.items() if k not in _APPIMAGE_VARS}


def subprocess_args(**kwargs):
    """
    Build kwargs for subprocess.run / subprocess.Popen:
    - Adds CREATE_NO_WINDOW on Windows to suppress console flashing.
    - On Linux inside an AppImage, strips AppImage env vars so subprocesses
      don't accidentally re-launch the AppImage instead of the intended binary.
    Use: subprocess.run(cmd, **subprocess_args(capture_output=True, text=True))
    """
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    elif sys.platform == "linux":
        clean = appimage_clean_env()
        if clean is not None:
            kwargs.setdefault("env", clean)
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
    import sys as _sys, json as _json
    marker = venv_path / ".venvstudio_env"
    if marker.exists():
        try:
            with open(marker, encoding="utf-8") as _f:
                _data = _json.load(_f)
            _type = _data.get("type", "")
            if _type == "pipx":
                _py = _data.get("python_path", "")
                if _py and Path(_py).exists():
                    return Path(_py)
                return Path(_sys.executable)
            if _type == "poetry":
                _pvenv = _data.get("poetry_venv_path", "")
                if _pvenv and Path(_pvenv).exists():
                    _scripts = "Scripts" if get_platform() == "windows" else "bin"
                    _exe = "python.exe" if get_platform() == "windows" else "python"
                    return Path(_pvenv) / _scripts / _exe
        except Exception:
            pass
    if get_platform() == "windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def get_pip_executable(venv_path: Path) -> Path:
    """Return the pip executable path inside a venv."""
    import sys as _sys, json as _json
    marker = venv_path / ".venvstudio_env"
    if marker.exists():
        try:
            with open(marker, encoding="utf-8") as _f:
                _data = _json.load(_f)
            _type = _data.get("type", "")
            if _type == "pipx":
                _py = _data.get("python_path", "") or _sys.executable
                _py_path = Path(_py)
                if get_platform() == "windows":
                    _pip = _py_path.parent / "Scripts" / "pip.exe"
                else:
                    _pip = _py_path.parent / "pip"
                if _pip.exists():
                    return _pip
                return _py_path.parent / ("Scripts/pip.exe" if get_platform() == "windows" else "pip")
            if _type == "poetry":
                _pvenv = _data.get("poetry_venv_path", "")
                if _pvenv and Path(_pvenv).exists():
                    _scripts = "Scripts" if get_platform() == "windows" else "bin"
                    _exe = "pip.exe" if get_platform() == "windows" else "pip"
                    return Path(_pvenv) / _scripts / _exe
        except Exception:
            pass
    if get_platform() == "windows":
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"

def get_pipx_executable() -> Optional[str]:
    """Find pipx executable — prefer direct binary, fallback sys.executable -m pipx."""
    import shutil, sys, os
    is_win = get_platform() == "windows"
    # 1. Direct binary in PATH
    found = shutil.which("pipx")
    if found:
        return found
    # 2. User local bin (~/.local/bin/pipx or %USERPROFILE%\.local\bin\pipx.exe)
    _bin_name = "pipx.exe" if is_win else "pipx"
    user_local = os.path.join(os.path.expanduser("~"), ".local", "bin", _bin_name)
    if os.path.isfile(user_local):
        return user_local
    # 3. AppData\Roaming\Python scripts (Windows pip install --user pipx)
    if is_win:
        appdata = os.environ.get("APPDATA", "")
        for py_ver in ("Python313", "Python312", "Python311", "Python314", "Python310"):
            candidate = os.path.join(appdata, "Python", py_ver, "Scripts", "pipx.exe")
            if os.path.isfile(candidate):
                return candidate
    # 4. Python Scripts dir next to sys.executable
    scripts = os.path.join(os.path.dirname(sys.executable),
                           "Scripts" if is_win else "bin",
                           "pipx.exe" if is_win else "pipx")
    if os.path.isfile(scripts):
        return scripts
    return None


def get_pipx_home() -> Optional[str]:
    """Find pipx home directory (where venvs are stored)."""
    import subprocess, os, sys
    # 1. Env var override
    env_home = os.environ.get("PIPX_HOME")
    if env_home and os.path.isdir(env_home):
        return env_home
    pipx_exe = get_pipx_executable()
    if pipx_exe:
        try:
            r = subprocess.run(
                [pipx_exe, "environment", "--value", "PIPX_HOME"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                p = os.path.expanduser(r.stdout.strip())
                if os.path.isdir(p):
                    return p
        except Exception:
            pass
    # 2. Default locations
    home = os.path.expanduser("~")
    for candidate in [
        os.path.join(home, "pipx"),
        os.path.join(home, ".local", "pipx"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "pipx"),
        os.path.join(os.environ.get("APPDATA", ""), "pipx"),
    ]:
        if os.path.isdir(os.path.join(candidate, "venvs")):
            return candidate
    return None


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

    # EXE/AppImage path — subprocess çağrısında bunlar tekrar başlatılmamalı
    _self_exe = os.path.normcase(os.path.normpath(sys.executable))

    def _try_add(exe_path: str):
        if not exe_path or not os.path.isfile(exe_path):
            return
        normalized = os.path.normcase(os.path.normpath(exe_path))
        if "windowsapps" in normalized:
            return
        # Kendimizi (EXE/AppImage) listeye ekleme
        if normalized == _self_exe:
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
    # NOT: Windows EXE (PyInstaller frozen) içinde shutil.which("python") EXE'nin
    # kendisini döndürebilir — bu durumda PATH aramasını atla
    if not (os.name == "nt" and getattr(sys, "frozen", False)):
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

    def _ver_key(v):
        try:
            return tuple(int(x) for x in v[0].split("."))
        except Exception:
            return (0,)
    pythons.sort(key=_ver_key, reverse=True)
    return pythons
def open_terminal_at(path: Path, terminal_type: str = "",
                     env_type: str = "venv") -> None:
    """Open a terminal/console at the given path.
    
    env_type:
      "venv"         → activate the Python venv (Scripts/activate.bat etc.)
      "conda"        → micromamba activate <path>
      "system_tools" → just cd into the folder, no activation
    """
    system = get_platform()

    # ── Build activation command based on env_type ────────────────────────
    def _make_cmd_windows(path: Path, terminal_type: str) -> str:
        if env_type in ("system_tools", "pipx"):
            # No activate script — just open shell at the folder
            if terminal_type == "wt" and shutil.which("wt"):
                return f'start wt -d "{path}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                return f'start "" "{git_bash}" --login -c "cd \'{path}\' && exec bash"'
            else:
                return f'start cmd /k "cd /d {path}"'

        elif env_type == "conda":
            from src.core.micromamba_installer import get_micromamba_exe
            mamba = get_micromamba_exe()
            if mamba:
                activate_cmd = f'"{mamba}" shell hook -s cmd.exe && "{mamba}" activate "{path}"'
            else:
                activate_cmd = f'conda activate "{path}"'
            if terminal_type == "wt" and shutil.which("wt"):
                return f'start wt -d "{path}" cmd /k "{activate_cmd}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                return f'start "" "{git_bash}" --login -c "cd \'{path}\'"'
            else:
                return f'start cmd /k "cd /d {path} && {activate_cmd}"'

        else:  # venv
            activate_bat = path / "Scripts" / "activate.bat"
            activate_ps1 = path / "Scripts" / "Activate.ps1"
            if terminal_type == "cmd":
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            elif terminal_type == "wt":
                if activate_ps1.exists():
                    return (f'start wt -d "{path}" powershell -NoExit -Command '
                            f'"& \'{activate_ps1}\'"')
                return f'start wt -d "{path}" cmd /k "{activate_bat}"'
            elif terminal_type == "git-bash":
                git_bash = shutil.which("bash")
                if git_bash:
                    activate_sh = path / "Scripts" / "activate"
                    return f'start "" "{git_bash}" --login -c "cd \'{path}\' && source \'{activate_sh}\' && exec bash"'
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            else:
                if shutil.which("wt"):
                    if activate_ps1.exists():
                        return (f'start wt -d "{path}" powershell -NoExit -Command '
                                f'"& \'{activate_ps1}\'"')
                    return f'start wt -d "{path}" cmd /k "{activate_bat}"'
                elif activate_ps1.exists():
                    return (f'start powershell -NoExit -Command "'
                            f'Set-Location \'{path}\'; '
                            f'& \'{activate_ps1}\'"')
                return f'start cmd /k "cd /d {path} && {activate_bat}"'

    def _make_cmd_posix(path: Path) -> str:
        if env_type in ("system_tools", "pipx"):
            return f"cd '{path}'"
        elif env_type == "poetry":
            # Poetry venv is in ~/.cache/pypoetry/virtualenvs/
            import json as _j
            _marker = path / ".venvstudio_env"
            _poetry_venv = ""
            if _marker.exists():
                try:
                    _poetry_venv = _j.loads(_marker.read_text()).get("poetry_venv_path", "")
                except Exception:
                    pass
            if _poetry_venv and Path(_poetry_venv).exists():
                _pa = Path(_poetry_venv) / "bin" / "activate"
                return f"cd '{_poetry_venv}' && source '{_pa}'"
            return f"cd '{path}'"
        elif env_type == "conda":
            _mamba = shutil.which("micromamba") or shutil.which("conda")
            if _mamba:
                return f"cd '{path}' && {_mamba} activate '{path}' 2>/dev/null || true"
            return f"cd '{path}'"
        else:
            activate = path / "bin" / "activate"
            if activate.exists():
                return f"cd '{path}' && source '{activate}'"
            return f"cd '{path}'"

    try:
        if system == "windows":
            cmd = _make_cmd_windows(path, terminal_type)
            subprocess.Popen(cmd, shell=True)

        elif system == "macos":
            posix_cmd = _make_cmd_posix(path)
            if terminal_type == "iterm2":
                script = (
                    f'tell application "iTerm" to create window with default profile '
                    f'command "cd \'{path}\' && {posix_cmd}"'
                )
            else:
                script = (
                    f'tell application "Terminal" to do script '
                    f'"cd \'{path}\' && {posix_cmd}"'
                )
            subprocess.Popen(["osascript", "-e", script])

        else:  # linux
            posix_cmd = _make_cmd_posix(path)

            # AppImage bundles override PATH — resolve the real system PATH
            host_path = os.environ.get("PATH", "")
            system_dirs = [
                "/usr/local/bin", "/usr/bin", "/bin",
                "/usr/local/sbin", "/usr/sbin", "/sbin",
                os.path.expanduser("~/.local/bin"),
            ]
            for d in reversed(system_dirs):
                if d not in host_path:
                    host_path = d + ":" + host_path

            system_bash = "/bin/bash"
            for d in ["/usr/bin", "/bin", "/usr/local/bin"]:
                candidate = os.path.join(d, "bash")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    system_bash = candidate
                    break

            bash_cmd = f"{posix_cmd} && exec {system_bash}"

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
