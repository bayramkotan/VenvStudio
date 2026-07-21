"""
VenvStudio - Platform-specific utilities
Cross-platform support for Windows, macOS, and Linux
"""

import logging
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
        # conda envs put python.exe at the ROOT, not under Scripts\\.
        # Probing Scripts\\python.exe (which doesn't exist) caused
        # "[WinError 2] cannot find the file specified" when installing
        # pip apps (e.g. Gradio) into a conda env.
        _root_py = venv_path / "python.exe"
        _scripts_py = venv_path / "Scripts" / "python.exe"
        if _root_py.exists() and not _scripts_py.exists():
            return _root_py
        return _scripts_py
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
        # conda: pip.exe (if present) sits in Scripts\\, but python is at root.
        _scripts_pip = venv_path / "Scripts" / "pip.exe"
        if _scripts_pip.exists():
            return _scripts_pip
        return _scripts_pip  # caller uses python -m pip when missing
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
    # 5. Check if pipx is available as a module (python3 -m pipx)
    try:
        import subprocess
        r = subprocess.run([sys.executable, "-m", "pipx", "--version"],
                           **subprocess_args(capture_output=True, text=True, timeout=5))
        if r.returncode == 0:
            return sys.executable  # caller should use [exe, "-m", "pipx", ...]
    except Exception:
        pass
    return None


def get_pipx_cmd() -> list:
    """Return the command list to invoke pipx.
    Returns ['pipx'] if binary found, or [sys.executable, '-m', 'pipx'] as fallback.
    """
    import sys as _sys
    exe = get_pipx_executable()
    if exe is None:
        return []
    # If exe == sys.executable, pipx is only available as a module
    import os as _os
    if _os.path.normpath(exe) == _os.path.normpath(_sys.executable):
        return [exe, "-m", "pipx"]
    return [exe]


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
                **subprocess_args(capture_output=True, text=True, timeout=10)
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
            mamba_str = str(mamba) if mamba else "micromamba"
            # MAMBA_ROOT_PREFIX — use parent of the mamba executable or user home
            import os as _os
            mamba_root = _os.environ.get("MAMBA_ROOT_PREFIX", "")
            if not mamba_root and mamba:
                mamba_root = str(Path(mamba).parent.parent)
                if not mamba_root or mamba_root == ".":
                    mamba_root = str(Path.home() / "micromamba")
            if not mamba_root:
                mamba_root = str(Path.home() / "micromamba")

            # Find the mamba_hook.bat (installed by 'micromamba shell init --shell cmd.exe')
            # Default locations on Windows
            def _find_mamba_hook_bat() -> Optional[str]:
                candidates = [
                    Path(_os.environ.get("APPDATA", "")) / "mamba" / "condabin" / "mamba_hook.bat",
                    Path(_os.environ.get("LOCALAPPDATA", "")) / "mamba" / "condabin" / "mamba_hook.bat",
                    Path(mamba_root) / "condabin" / "mamba_hook.bat",
                    Path.home() / ".local" / "share" / "mamba" / "condabin" / "mamba_hook.bat",
                ]
                for c in candidates:
                    if c.exists():
                        return str(c)
                return None

            # Find Activate.ps1 for PowerShell hook (also installed by 'shell init')
            def _find_mamba_hook_ps1() -> Optional[str]:
                candidates = [
                    Path(_os.environ.get("APPDATA", "")) / "mamba" / "condabin" / "Conda.psm1",
                    Path(mamba_root) / "condabin" / "Conda.psm1",
                ]
                for c in candidates:
                    if c.exists():
                        return str(c.parent)  # parent dir of the module
                return None

            mamba_hook_bat = _find_mamba_hook_bat()

            # Ensure shell init has been run — if hook files missing, run init once
            if not mamba_hook_bat:
                try:
                    subprocess.run(
                        [mamba_str, "shell", "init", "--shell", "cmd.exe",
                         "--root-prefix", mamba_root],
                        **subprocess_args(capture_output=True, text=True, timeout=30),
                    )
                    mamba_hook_bat = _find_mamba_hook_bat()
                except Exception:
                    pass
                try:
                    subprocess.run(
                        [mamba_str, "shell", "init", "--shell", "powershell",
                         "--root-prefix", mamba_root],
                        **subprocess_args(capture_output=True, text=True, timeout=30),
                    )
                except Exception:
                    pass

            # cmd.exe activation: set MAMBA_ROOT_PREFIX, CALL mamba_hook.bat, activate
            if mamba_hook_bat:
                cmd_activate = (
                    f'set "MAMBA_ROOT_PREFIX={mamba_root}" '
                    f'&& CALL "{mamba_hook_bat}" '
                    f'&& micromamba activate "{path}"'
                )
            else:
                # Fallback: run shell directly inside the env (no activation prompt, but paths work)
                cmd_activate = f'"{mamba_str}" run -p "{path}" cmd /k'

            # PowerShell activation: the init creates a profile hook; we just need to activate.
            # Try loading Conda.psm1 if present, otherwise fall back to shell hook pipe.
            ps_activate = (
                f'$env:MAMBA_ROOT_PREFIX=\'{mamba_root}\'; '
                f'try {{ (& \'{mamba_str}\' shell hook -s powershell) | Out-String | Invoke-Expression }} '
                f'catch {{ Write-Host \'Hook failed, trying direct run...\'; & \'{mamba_str}\' run -p \'{path}\' powershell -NoExit; exit }}; '
                f'micromamba activate \'{path}\''
            )

            if terminal_type == "wt" and shutil.which("wt"):
                # Windows Terminal with cmd (uses mamba_hook.bat which is most reliable)
                if mamba_hook_bat:
                    return f'start wt -d "{path}" cmd /k "{cmd_activate}"'
                return f'start wt -d "{path}" powershell -NoExit -Command "{ps_activate}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                # Git-Bash: use bash-style hook
                bash_activate = (
                    f"export MAMBA_ROOT_PREFIX='{mamba_root}'; "
                    f"eval \"$('{mamba_str}' shell hook -s bash)\"; "
                    f"micromamba activate '{path}'"
                )
                return (f'start "" "{git_bash}" --login -c '
                        f'"cd \'{path}\' && {bash_activate} && exec bash"')
            elif terminal_type == "pwsh":
                # PowerShell 7+ — same activation hook as Windows PowerShell,
                # just launched through pwsh instead of powershell.
                return (f'start pwsh -NoExit -Command '
                        f'"Set-Location \'{path}\'; {ps_activate}"')
            elif terminal_type == "powershell":
                return (f'start powershell -NoExit -Command '
                        f'"Set-Location \'{path}\'; {ps_activate}"')
            else:
                # Default: cmd.exe via mamba_hook.bat (most reliable on Windows)
                return f'start cmd /k "cd /d {path} && {cmd_activate}"'

        else:  # venv
            activate_bat = path / "Scripts" / "activate.bat"
            activate_ps1 = path / "Scripts" / "Activate.ps1"
            if terminal_type == "cmd":
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            elif terminal_type == "pwsh":
                # PowerShell 7+ via pwsh.exe; activate through Activate.ps1
                if activate_ps1.exists():
                    return (f'start pwsh -NoExit -Command '
                            f'"Set-Location \'{path}\'; & \'{activate_ps1}\'"')
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
            # Try micromamba first, fall back to conda
            _mamba = shutil.which("micromamba")
            _conda = shutil.which("conda") if not _mamba else None
            # Detect mamba from common install paths if not in PATH
            if not _mamba and not _conda:
                import os as _os
                for _candidate in (
                    Path.home() / ".local" / "bin" / "micromamba",
                    Path.home() / "micromamba" / "bin" / "micromamba",
                    Path("/usr/local/bin/micromamba"),
                    Path("/opt/homebrew/bin/micromamba"),
                ):
                    if _candidate.exists():
                        _mamba = str(_candidate)
                        break

            if _mamba:
                import os as _os
                mamba_root = _os.environ.get("MAMBA_ROOT_PREFIX", "")
                if not mamba_root:
                    mamba_root = str(Path(_mamba).parent.parent)
                    if not mamba_root or mamba_root in ("", "."):
                        mamba_root = str(Path.home() / "micromamba")
                # bash/zsh hook → eval → activate
                # Works on Linux, macOS, FreeBSD — any POSIX shell with eval
                return (
                    f"cd '{path}' && "
                    f"export MAMBA_ROOT_PREFIX='{mamba_root}' && "
                    f"eval \"$('{_mamba}' shell hook -s bash)\" && "
                    f"micromamba activate '{path}'"
                )
            elif _conda:
                # Fallback for full conda: try 'conda activate' after sourcing profile
                return (
                    f"cd '{path}' && "
                    f"source \"$(dirname '{_conda}')/../etc/profile.d/conda.sh\" 2>/dev/null && "
                    f"conda activate '{path}' 2>/dev/null || cd '{path}'"
                )
            # Nothing found — just cd
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

            # ── Build an rcfile so shell functions (micromamba, conda activate)
            # remain loaded in the INTERACTIVE bash session.
            # Old approach `{posix_cmd} && exec bash` loses functions defined
            # via `eval $(mamba shell hook -s bash)` because exec starts a new
            # shell that re-reads ~/.bashrc only.
            import tempfile as _tempfile
            _rc_content = (
                "# VenvStudio-generated rcfile (temporary)\n"
                "# Load user's normal init so prompt/aliases work\n"
                "[ -f ~/.bashrc ] && source ~/.bashrc\n"
                "\n"
                "# VenvStudio: activate environment\n"
                f"{posix_cmd}\n"
            )
            _rc_file = _tempfile.NamedTemporaryFile(
                mode="w", suffix=".venvstudio-rc", prefix="vs-",
                delete=False, encoding="utf-8",
            )
            _rc_file.write(_rc_content)
            _rc_file.close()
            _rc_path = _rc_file.name

            # Interactive bash with our rcfile → env activated, prompt shows
            # (env) prefix, functions loaded, Ctrl-D / exit closes the shell.
            bash_cmd = f'{system_bash} --rcfile "{_rc_path}" -i'

            # Schedule rcfile cleanup: add a trap in the rcfile so when the
            # shell exits, the temp file is removed.
            _cleanup_trap = (
                f"\n# Cleanup temp rcfile when shell exits\n"
                f"trap 'rm -f \"{_rc_path}\"' EXIT\n"
            )
            with open(_rc_path, "a", encoding="utf-8") as _f:
                _f.write(_cleanup_trap)

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
                    _snew = {"start_new_session": True}
                    if term == "xdg-terminal":
                        # openSUSE: xdg-terminal [command] — pass shell with rcfile
                        subprocess.Popen(
                            [term_exe, f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
                        )
                    elif term == "gnome-terminal":
                        subprocess.Popen(
                            [term_exe, "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term in ("konsole", "yakuake"):
                        subprocess.Popen(
                            [term_exe, "--noclose", "-e", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term in ("xfce4-terminal", "mate-terminal", "cinnamon-terminal", "lxterminal", "tilix"):
                        # These expect a single -e argument with shell+args as string
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
                        )
                    elif term == "kgx":
                        # GNOME Console (openSUSE and others)
                        subprocess.Popen(
                            [term_exe, "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "kitty":
                        subprocess.Popen(
                            [term_exe, system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "alacritty":
                        subprocess.Popen(
                            [term_exe, "-e", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "wezterm":
                        subprocess.Popen(
                            [term_exe, "start", "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "foot":
                        subprocess.Popen(
                            [term_exe, system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    else:
                        # xterm, x-terminal-emulator and others
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
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
                # GNOME
                "gnome-terminal",   # Ubuntu, Fedora, Debian GNOME
                "kgx",              # openSUSE GNOME (GNOME Console)
                # KDE
                "konsole",          # KDE Plasma
                "yakuake",          # KDE drop-down
                # XFCE
                "xfce4-terminal",   # XFCE
                # Other DEs
                "mate-terminal",    # MATE
                "lxterminal",       # LXDE
                "tilix",            # GNOME tiling
                "cinnamon-terminal", # Cinnamon (rare, falls through)
                # GPU-accelerated / cross-DE
                "alacritty",
                "kitty",
                "wezterm",
                "foot",             # Wayland-native
                # Fallbacks
                "xterm",
                "x-terminal-emulator",  # Debian alternatives system
                "xdg-terminal",         # openSUSE fallback (requires xdg-terminal-exec)
            ]
            for term in auto_order:
                if _launch_linux_terminal(term):
                    break
    except Exception as e:
        logging.getLogger("venvstudio.gui.terminal").warning(
            f"⚠️ [Terminal] Could not open terminal: {e}"
        )


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


def open_url(url: str) -> tuple[bool, str]:
    """Open a URL in the default web browser — AppImage-safe.

    Inside an AppImage, webbrowser.open() spawns xdg-open/the browser with
    the AppImage-injected environment (LD_LIBRARY_PATH, APPDIR, ...), which
    makes the host browser fail to start silently. Same root cause that
    open_folder() below already handles for file managers.

    Linux + AppImage → spawn an opener with appimage_clean_env().
    Everything else  → plain webbrowser.open() (works fine).

    Returns (success, message).
    """
    if get_platform() not in ("windows", "macos") and os.environ.get("APPIMAGE"):
        clean_env = appimage_clean_env() or os.environ.copy()
        candidates = ("xdg-open", "x-www-browser", "sensible-browser",
                      "firefox", "chromium", "chromium-browser", "google-chrome")
        for tool in candidates:
            exe = shutil.which(tool, path=clean_env.get("PATH"))
            if not exe:
                continue
            try:
                subprocess.Popen(
                    [exe, url], env=clean_env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True, f"Opened {url}"
            except Exception:
                continue
        return False, "No usable browser opener found (AppImage)"
    try:
        import webbrowser
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, f"Could not open URL: {e}"


def open_folder(path) -> tuple[bool, str]:
    """Open a folder in the system file manager.

    Cross-platform:
      - Windows  → explorer.exe "<path>"
      - macOS    → open "<path>"
      - Linux    → xdg-open "<path>"  (falls back to common file managers)
      - FreeBSD  → xdg-open (if available) / falls back like Linux

    If the given path is a file, opens the containing directory (and on Windows
    additionally selects the file).

    Returns (success, message).
    """
    try:
        p = Path(path)
    except Exception as e:
        return False, f"Invalid path: {e}"

    if not p.exists():
        return False, f"Path does not exist: {p}"

    system = get_platform()
    target = p if p.is_dir() else p.parent

    try:
        if system == "windows":
            if p.is_dir():
                # Open the directory itself
                subprocess.Popen(["explorer.exe", str(p)])
            else:
                # Open containing folder with the file selected
                subprocess.Popen(["explorer.exe", "/select,", str(p)])
            return True, f"Opened {target}"

        elif system == "macos":
            if p.is_dir():
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["open", "-R", str(p)])
            return True, f"Opened {target}"

        else:  # linux / bsd
            # Clean AppImage-injected env so the file manager uses the host
            clean_env = os.environ.copy()
            for var in ("APPIMAGE", "APPDIR", "OWD", "ARGV0",
                        "APPIMAGE_EXTRACT_AND_RUN",
                        "LD_LIBRARY_PATH", "LD_PRELOAD"):
                clean_env.pop(var, None)

            # Prefer xdg-open (DE-neutral), then fall back to specific FMs
            candidates = [
                "xdg-open",
                "gio",          # GNOME (used as: gio open <path>)
                "nautilus",     # GNOME
                "dolphin",      # KDE
                "thunar",       # XFCE
                "pcmanfm",      # LXDE
                "nemo",         # Cinnamon
                "caja",         # MATE
                "Thunar",       # openSUSE capitalised variant
                "xdg-open",     # retry (some distros have it in /usr/local/bin)
            ]
            _seen = set()
            for tool in candidates:
                if tool in _seen:
                    continue
                _seen.add(tool)
                exe = shutil.which(tool)
                if not exe:
                    # Also search /usr/bin and /usr/local/bin directly (openSUSE PATH issues)
                    for _d in ("/usr/bin", "/usr/local/bin", "/usr/bin/X11"):
                        _c = os.path.join(_d, tool)
                        if os.path.isfile(_c) and os.access(_c, os.X_OK):
                            exe = _c
                            break
                if not exe:
                    continue
                try:
                    if tool == "gio":
                        subprocess.Popen([exe, "open", str(target)], env=clean_env,
                                         start_new_session=True)
                    else:
                        subprocess.Popen([exe, str(target)], env=clean_env,
                                         start_new_session=True)
                    return True, f"Opened {target} with {tool}"
                except Exception:
                    continue

            return False, ("No file manager found. Install 'xdg-utils' or "
                           "a desktop file manager (nautilus, dolphin, thunar, ...).")

    except Exception as e:
        return False, f"Could not open folder: {e}"
