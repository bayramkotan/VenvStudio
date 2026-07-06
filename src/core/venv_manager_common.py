"""
venv_manager shared helpers — split from venv_manager.py.

Module-level utilities used by the VenvManager base class and its clone/
rename mixins: the subprocess wrapper (_run), robust rmtree, Windows python
discovery, and banner helpers. Kept in a dependency-free module so both the
base class and the mixins can import from here without a circular import.
"""

import os
import sys
import stat
import shutil
import subprocess
import logging
import platform as _platform
from pathlib import Path

_log = logging.getLogger("venvstudio.core.venv_manager")

# Banner helpers for visual terminal output
try:
    from src.utils.logger import banner_start, banner_success, banner_error, banner_warning
except Exception:
    # Fallback no-ops if logger module has issues during bootstrap
    def banner_start(*args, **kwargs): pass
    def banner_success(*args, **kwargs): pass
    def banner_error(*args, **kwargs): pass
    def banner_warning(*args, **kwargs): pass

_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if _platform.system().lower() == "windows" else 0


def _robust_rmtree(path: Path) -> None:
    """Delete a directory tree, handling read-only files on Windows.

    On Windows, package files (especially in Poetry/pip caches) are often
    marked read-only, causing shutil.rmtree to raise PermissionError /
    [WinError 5] Access is denied. This helper clears the read-only bit
    on the offending file and retries the deletion.

    Raises the original exception if the retry also fails.
    """
    def _on_error(func, target, exc_info):
        # exc_info is (type, value, tb) on Python <3.12 with onerror,
        # or just the exception on Python 3.12+ with onexc — handle both.
        try:
            os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
            func(target)
        except Exception:
            # Re-raise the original error so rmtree fails loudly
            raise

    # Python 3.12+ deprecated onerror in favour of onexc; both still work.
    # Use onerror for max compatibility (works on 3.10+).
    shutil.rmtree(path, onerror=_on_error)


def _find_windows_python() -> str:
    """
    Find real Python executable on Windows when running as a PyInstaller EXE.
    sys.executable points to the EXE binary, not python.exe.
    Searches: PATH, Windows Registry, known install dirs.
    Returns empty string if not found.
    """
    import shutil

    # 1) PATH'de python / python3
    for candidate in ("python", "python3"):
        found = shutil.which(candidate)
        if found and "windowsapps" not in found.lower():
            return found

    # 2) Windows Registry
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for reg_path in (
                r"SOFTWARE\Python\PythonCore",
                r"SOFTWARE\WOW6432Node\Python\PythonCore",
            ):
                try:
                    with winreg.OpenKey(hive, reg_path) as key:
                        i = 0
                        best = ""
                        while True:
                            try:
                                ver = winreg.EnumKey(key, i)
                                i += 1
                                with winreg.OpenKey(key, ver + r"\InstallPath") as ip:
                                    install_dir = winreg.QueryValue(ip, None)
                                    exe = os.path.join(install_dir.rstrip("\\"), "python.exe")
                                    if os.path.isfile(exe):
                                        best = exe  # en son versiyonu al
                            except OSError:
                                break
                        if best:
                            return best
                except OSError:
                    continue
    except ImportError:
        pass

    # 3) Bilinen kurulum dizinleri
    for root in (
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    ):
        if not root or not os.path.isdir(root):
            continue
        try:
            for entry in os.scandir(root):
                if entry.is_dir() and entry.name.lower().startswith("python"):
                    exe = os.path.join(entry.path, "python.exe")
                    if os.path.isfile(exe):
                        return exe
        except PermissionError:
            continue

    return ""


def _run(*args, **kwargs):
    """subprocess.run wrapper — uses subprocess_args for platform safety.
    Logs every invocation at DEBUG level so terminal users see exactly what's
    being executed (create, install, activate etc.).
    """
    from src.utils.platform_utils import subprocess_args
    # subprocess_args: Windows CREATE_NO_WINDOW + EXE PATH fix, Linux AppImage env clean
    merged = subprocess_args()
    for k, v in merged.items():
        kwargs.setdefault(k, v)

    # Log the command being executed (visible in terminal when TTY)
    try:
        cmd = args[0] if args else kwargs.get("args", "?")
        if isinstance(cmd, (list, tuple)):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)
        _log.debug(f"▶ subprocess: {cmd_str}")
    except Exception:
        pass

    result = subprocess.run(*args, **kwargs)

    # Log non-zero exit codes
    try:
        rc = getattr(result, "returncode", None)
        if rc is not None and rc != 0:
            stderr_preview = ""
            if hasattr(result, "stderr") and result.stderr:
                stderr_preview = str(result.stderr)[:200].replace("\n", " ")
            _log.warning(f"  ↳ exit={rc}  stderr={stderr_preview!r}")
        else:
            _log.debug(f"  ↳ exit=0")
    except Exception:
        pass

    return result
