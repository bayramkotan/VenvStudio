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


def _fmt_path(p) -> str:
    """Display-only path formatting for log messages.

    Cache keys are intentionally normalized to forward slashes (v1.4.82 fix)
    and MUST stay that way internally. This helper only affects how paths
    LOOK in the logs: native separators per OS (Windows: backslash,
    Linux/macOS: forward slash). Never use this for cache keys or for paths
    passed to subprocess/filesystem calls.
    """
    s = str(p)
    return s.replace("/", "\\") if os.name == "nt" else s.replace("\\", "/")

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


# ── B199: reading a venv that cannot run ───────────────────────────────────
#
# Everything below answers a question about an environment WITHOUT starting
# its Python, because the case these exist for is the one where there is no
# Python to start. They live here rather than in venv_manager.py for the
# reason this module exists: the clone and rename mixins need the same
# answers, and two copies of this logic would disagree within a release.


def venv_python_home(venv_path) -> str:
    """The interpreter directory pyvenv.cfg says this venv was built on."""
    try:
        _text = (Path(venv_path) / "pyvenv.cfg").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for _line in _text.splitlines():
        if "=" in _line and _line.split("=", 1)[0].strip() == "home":
            return _line.split("=", 1)[1].strip()
    return ""


def venv_cfg_version(venv_path) -> str:
    """The Python version pyvenv.cfg recorded, digits only.

    "3.13.13.final.0" -> "3.13.13". This is written when the environment is
    created and never needs the interpreter to read, which is the point: a
    broken environment can still say which Python it wants.
    """
    try:
        _text = (Path(venv_path) / "pyvenv.cfg").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for _line in _text.splitlines():
        if "=" not in _line:
            continue
        if _line.split("=", 1)[0].strip() not in ("version", "version_info"):
            continue
        _raw = _line.split("=", 1)[1].strip()
        _parts = []
        for _p in _raw.split("."):
            if _p.isdigit():
                _parts.append(_p)
            else:
                break
        return ".".join(_parts) if _parts else _raw
    return ""


def count_installed_packages(venv_path) -> int:
    """How many packages are on disk, without running anything.

    B199. `pip list` needs the interpreter, and the whole reason this
    function exists is that the interpreter is missing. The packages are
    still there, and every one of them leaves a .dist-info directory beside
    itself (PEP 376), so they can be counted by looking.

    Deliberately counts distinct NAMES: a site-packages directory can hold
    both a .dist-info and a legacy .egg-info for the same package, and
    counting both would inflate the number the user is being asked to
    trust.
    """
    _p = Path(venv_path)
    _roots = [_p / "Lib" / "site-packages"]          # Windows layout
    for _libdir in ("lib", "lib64"):                 # POSIX layout
        try:
            _roots += sorted((_p / _libdir).glob("python*/site-packages"))
        except OSError:
            pass
    _names = set()
    for _root in _roots:
        try:
            for _entry in _root.iterdir():
                if _entry.suffix in (".dist-info", ".egg-info"):
                    _names.add(_entry.name.split("-")[0].lower())
        except OSError:
            continue
    return len(_names)


def broken_venv_reason(venv_path) -> str:
    """Why this venv cannot run, in words, or "" when it is fine.

    B199 (Bayram, 2026-11-01). His `ml` environment was 166 packages and
    1.6 GB at 21:00. The Python it was built on --
    /usr/local/bin/python3.13 -> /opt/python/3.13.13/bin/python3 -- then
    went away. By 23:26 VenvStudio showed the same environment as a tools
    folder with no runtime and no packages, so the only reasonable reading
    was that it was empty and broken. He deleted it and built it again.

    A directory holding a pyvenv.cfg is a virtual environment. That it
    cannot run today is a fact about its interpreter, not about what kind
    of thing it is, and it is a fact worth saying out loud.

    Returns "" for anything that is not a venv at all -- a tools folder
    has no interpreter either, and that is not a fault.
    """
    _p = Path(venv_path)
    if not (_p / "pyvenv.cfg").is_file():
        return ""
    from src.utils.platform_utils import get_python_executable
    _py = get_python_executable(_p)
    try:
        if _py.exists():
            return ""
    except OSError:
        pass
    # A dangling symlink is the common case: a venv points straight at the
    # interpreter it was made from, and that interpreter was upgraded or
    # uninstalled out from under it.
    try:
        if _py.is_symlink():
            return (f"The Python this environment was built on is gone: "
                    f"{_py.name} points at {os.readlink(_py)}, which no "
                    f"longer exists.")
    except OSError:
        pass
    _home = venv_python_home(_p)
    if _home:
        return (f"The Python this environment was built on is gone: "
                f"pyvenv.cfg names {_home}, and there is no interpreter "
                f"left in the environment.")
    return "This environment has no Python interpreter in it."


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
        _log.debug(f"🚀 subprocess: {cmd_str}")
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
            _log.warning(f"  ↳ ✖ exit={rc}  stderr={stderr_preview!r}")
        else:
            _log.debug(f"  ↳ ✔ exit=0")
    except Exception:
        pass

    return result
