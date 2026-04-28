"""
VenvStudio - Virtual Environment Manager
Core operations: create, delete, list, inspect venvs
"""

import os
import sys
import shutil
import subprocess
import json
import logging
import platform as _platform
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.platform_utils import (
    get_python_executable,
    get_pip_executable,
    get_venv_size,
    get_activate_command,
)

# Module-level logger — routes to 'venvstudio.core.venv_manager'
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

# Suppress terminal windows on Windows (EXE builds)
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if _platform.system().lower() == "windows" else 0


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


@dataclass
class VenvInfo:
    """Information about a virtual environment."""
    name: str
    path: Path
    python_version: str = "Unknown"
    size: str = "N/A"
    created: str = ""
    package_count: int = 0
    is_valid: bool = True
    env_type: str = "venv"  # venv | uv | poetry | pipx | conda

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "python_version": self.python_version,
            "size": self.size,
            "created": self.created,
            "package_count": self.package_count,
            "is_valid": self.is_valid,
            "env_type": self.env_type,
        }


class VenvManager:
    """Manages virtual environment operations."""

    # Class-level memory cache — survives multiple VenvManager() instantiations
    _mem_envs: Dict[str, list] = {}         # str(base_dir) -> [VenvInfo, ...]
    _mem_envs_valid: Dict[str, bool] = {}   # str(base_dir) -> is_valid
    _all_cache: Optional[Dict] = None       # in-memory env_cache.json contents
    _all_cache_dirty: bool = False          # needs write to disk

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._base_key = str(self.base_dir)

    def set_base_dir(self, new_dir: Path) -> None:
        """Change the base directory."""
        self.base_dir = new_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_pipx_env(self) -> bool:
        """Auto-create a pipx marker env in pipx home dir if pipx is installed.
        Returns True if pipx env exists or was created, False if pipx not found."""
        import shutil, json as _json, datetime as _dt, sys as _sys
        from src.utils.platform_utils import get_pipx_executable, get_pipx_home, get_pipx_cmd
        pipx_exe = get_pipx_executable()
        if not pipx_exe:
            return False
        pipx_home = get_pipx_home() or ""
        # Use pipx home as the marker dir — not the user venv base dir
        if pipx_home:
            marker_dir = Path(pipx_home)
        else:
            # Fallback to default pipx home locations
            import os
            if sys.platform == "win32":
                marker_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pipx"
            else:
                marker_dir = Path.home() / ".local" / "share" / "pipx"
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker = marker_dir / ".venvstudio_env"
        if not marker.exists():
            try:
                with open(marker, "w", encoding="utf-8") as _f:
                    _json.dump({
                        "type": "pipx",
                        "name": "pipx",
                        "pipx_home": str(pipx_home),
                        "pipx_exe": str(pipx_exe),
                        "python_path": _sys.executable,
                        "created": _dt.datetime.now().isoformat(),
                        "auto_detected": True,
                    }, _f, indent=2)
            except Exception:
                pass
        else:
            # Update pipx_home/exe in case they changed
            try:
                with open(marker, "r", encoding="utf-8") as _f:
                    data = _json.load(_f)
                data["pipx_home"] = str(pipx_home)
                data["pipx_exe"] = str(pipx_exe)
                with open(marker, "w", encoding="utf-8") as _f:
                    _json.dump(data, _f, indent=2)
            except Exception:
                pass
        return True

    def create_venv(
        self,
        name: str,
        python_path: Optional[str] = None,
        with_pip: bool = True,
        system_site_packages: bool = False,
        callback=None,
    ) -> tuple[bool, str]:
        """
        Create a new virtual environment.
        Returns (success, message).
        """
        _log.info(f"create_venv: name={name!r} python={python_path!r} "
                  f"with_pip={with_pip} system_site={system_site_packages}")
        banner_start(
            f"Creating environment '{name}'",
            details=[
                f"Python: {python_path or 'system default'}",
                f"Pip: {'yes' if with_pip else 'no'}",
                f"System site-packages: {'yes' if system_site_packages else 'no'}",
                f"Location: {self.base_dir / name}",
            ],
        )
        venv_path = self.base_dir / name

        if venv_path.exists():
            _log.warning(f"create_venv: env already exists at {venv_path}")
            banner_warning(
                f"Environment '{name}' already exists",
                details=[f"Path: {venv_path}", "Delete it first or pick a new name."],
            )
            return False, f"Environment '{name}' already exists at {venv_path}"

        if python_path:
            python_exe = python_path
        elif _platform.system().lower() == "linux":
            python_exe = "/usr/bin/python3" if os.path.isfile("/usr/bin/python3") else "python3"
        else:
            python_exe = "python"
        cmd = [python_exe, "-m", "venv"]

        if not with_pip:
            cmd.append("--without-pip")
        if system_site_packages:
            cmd.append("--system-site-packages")

        cmd.append(str(venv_path))

        try:
            if callback:
                callback(f"Creating environment '{name}'...")

            result = _run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                # B149: On Debian/Ubuntu, Python 3.14+, and some Windows configs
                # the actual error message goes to STDOUT, not stderr. Combine
                # both streams for both detection and user display so the user
                # always sees what went wrong instead of an empty "Failed to
                # create environment:" box.
                _combined = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
                stderr_lower = _combined.lower()

                # ensurepip/default-pip failure — Python 3.14+ removed --default-pip
                # Retry with --without-pip then install pip manually
                if with_pip and ("ensurepip" in stderr_lower or "default-pip" in stderr_lower or "returned non-zero exit" in stderr_lower):
                    if venv_path.exists():
                        shutil.rmtree(venv_path, ignore_errors=True)
                    if callback:
                        callback("Retrying without ensurepip (Python 3.14+ mode)...")
                    cmd_nopip = [python_exe, "-m", "venv", "--without-pip"]
                    if system_site_packages:
                        cmd_nopip.append("--system-site-packages")
                    cmd_nopip.append(str(venv_path))
                    retry = _run(cmd_nopip, capture_output=True, text=True, timeout=120)
                    if retry.returncode != 0:
                        if venv_path.exists():
                            shutil.rmtree(venv_path, ignore_errors=True)
                        _retry_msg = ((retry.stderr or "") + "\n" + (retry.stdout or "")).strip()
                        return False, f"Failed to create environment:\n{_retry_msg or '(no output)'}"
                    # Install pip manually via ensurepip
                    python_in_venv = get_python_executable(venv_path)
                    if callback:
                        callback("Installing pip manually...")
                    _run(
                        [str(python_in_venv), "-m", "ensurepip"],
                        capture_output=True, text=True, timeout=60,
                    )

                elif "no module named venv" in stderr_lower or "python3-venv" in stderr_lower or "ensurepip is not available" in stderr_lower:
                    if venv_path.exists():
                        shutil.rmtree(venv_path, ignore_errors=True)
                    venv_installed = self._try_install_venv_package(python_exe, callback)
                    if venv_installed:
                        if callback:
                            callback("Retrying environment creation...")
                        retry = _run(cmd, capture_output=True, text=True, timeout=120)
                        if retry.returncode != 0:
                            if venv_path.exists():
                                shutil.rmtree(venv_path, ignore_errors=True)
                            _retry_msg = ((retry.stderr or "") + "\n" + (retry.stdout or "")).strip()
                            return False, f"Failed to create environment after installing python3-venv:\n{_retry_msg or '(no output)'}"
                    else:
                        return False, (
                            f"Failed to create environment:\n{_combined or '(no output)'}\n\n"
                            f"💡 The 'venv' module may be missing.\n"
                            f"Install it with your package manager:\n"
                            f"  Debian/Ubuntu/Pardus: sudo apt install python3-venv\n"
                            f"  Fedora: sudo dnf install python3-libs\n"
                            f"  openSUSE: sudo zypper install python3-venv"
                        )
                else:
                    if venv_path.exists():
                        shutil.rmtree(venv_path, ignore_errors=True)
                    # Show combined stdout+stderr; if both empty, fall back to
                    # a helpful message listing the exact command that failed.
                    if _combined:
                        return False, f"Failed to create environment (exit {result.returncode}):\n{_combined}"
                    return False, (
                        f"Failed to create environment (exit {result.returncode}).\n"
                        f"The command produced no output — this is unusual.\n\n"
                        f"Command: {' '.join(str(c) for c in cmd)}\n\n"
                        f"💡 Common causes:\n"
                        f"  • Debian/Ubuntu/Pardus: 'python3-venv' package not installed\n"
                        f"    → sudo apt install python3-venv\n"
                        f"  • Windows: Python Store alias blocking — disable under\n"
                        f"    Settings → Apps → App execution aliases\n"
                        f"  • macOS: Xcode Command Line Tools missing\n"
                        f"    → xcode-select --install"
                    )

            pip_exe = get_pip_executable(venv_path)
            python_in_venv = get_python_executable(venv_path)
            if with_pip:
                if not pip_exe.exists():
                    # pip yok — ensurepip ile kur
                    if callback:
                        callback("Installing pip...")
                    # ensurepip için sistem env'ini kullan (AppImage env değil)
                    _ensurepip_env = os.environ.copy()
                    for _v in ("APPIMAGE", "APPDIR", "ARGV0", "OWD",
                               "APPIMAGE_EXTRACT_AND_RUN", "LD_LIBRARY_PATH", "LD_PRELOAD"):
                        _ensurepip_env.pop(_v, None)
                    ensurepip_result = subprocess.run(
                        [str(python_in_venv), "-m", "ensurepip", "--upgrade"],
                        capture_output=True, text=True, timeout=60,
                        env=_ensurepip_env,
                    )
                    if ensurepip_result.returncode != 0 or not pip_exe.exists():
                        # ensurepip çalışmadı — get-pip.py ile kur
                        if callback:
                            callback("Installing pip via get-pip.py...")
                        try:
                            import socket, ssl as _ssl, tempfile, os as _os
                            _ctx = _ssl.create_default_context()
                            # Sistem SSL sertifikalarını bul
                            for _cp in (
                                "/etc/ssl/certs/ca-certificates.crt",
                                "/etc/pki/tls/certs/ca-bundle.crt",
                                "/etc/ssl/ca-bundle.pem",
                            ):
                                if _os.path.isfile(_cp):
                                    _ctx.load_verify_locations(_cp)
                                    break
                            with socket.create_connection(("bootstrap.pypa.io", 443), timeout=30) as _sock:
                                with _ctx.wrap_socket(_sock, server_hostname="bootstrap.pypa.io") as _ssock:
                                    _req = (
                                        "GET /pip/latest/get-pip.py HTTP/1.1\r\n"
                                        "Host: bootstrap.pypa.io\r\n"
                                        "User-Agent: VenvStudio\r\n"
                                        "Connection: close\r\n\r\n"
                                    )
                                    _ssock.sendall(_req.encode())
                                    _chunks = []
                                    while True:
                                        _c = _ssock.recv(8192)
                                        if not _c:
                                            break
                                        _chunks.append(_c)
                            _raw = b"".join(_chunks)
                            _body = _raw.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in _raw else _raw
                            _tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
                            _tmp.write(_body)
                            _tmp.close()
                            _run(
                                [str(python_in_venv), _tmp.name],
                                capture_output=True, text=True, timeout=120,
                            )
                            _os.unlink(_tmp.name)
                        except Exception as _e:
                            print(f"[VenvStudio] get-pip.py failed: {_e}")

                # pip varsa upgrade et
                pip_exe = get_pip_executable(venv_path)  # tekrar kontrol
                if pip_exe.exists():
                    if callback:
                        callback("Upgrading pip...")
                    _run(
                        [str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip"],
                        capture_output=True, text=True, timeout=60,
                    )

            meta = {
                "created": datetime.now().isoformat(),
                "python_path": python_exe,
                "created_by": "VenvStudio",
            }
            meta_file = venv_path / ".venvstudio_meta.json"
            with open(meta_file, "w") as f:
                json.dump(meta, f, indent=2)

            # Build success details
            _py_in_venv = get_python_executable(venv_path)
            _details = [f"Path: {venv_path}"]
            try:
                if _py_in_venv.exists():
                    _ver = _run(
                        [str(_py_in_venv), "--version"],
                        capture_output=True, text=True, timeout=5,
                    )
                    _v = (_ver.stdout or _ver.stderr or "").strip()
                    if _v:
                        _details.append(f"Python: {_v}")
            except Exception:
                pass
            if with_pip:
                _details.append("pip: installed & upgraded")
            if system_site_packages:
                _details.append("System site-packages: enabled")
            banner_success(f"Environment '{name}' is ready!", details=_details)

            return True, f"Environment '{name}' created successfully at {venv_path}"

        except subprocess.TimeoutExpired:
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            banner_error(
                f"Creating '{name}' timed out",
                details=["Took longer than 120 seconds", "Check your network or try a different Python"],
            )
            return False, "Environment creation timed out (120s)"
        except Exception as e:
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            banner_error(f"Could not create '{name}'", details=[str(e)])
            return False, f"Error creating environment: {str(e)}"

    # ── Auto-install python3-venv ──────────────────────────────────────────

    @staticmethod
    def _detect_distro_family() -> str:
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
            for line in content.splitlines():
                if line.startswith("id_like=") or line.startswith("id="):
                    val = line.split("=", 1)[1].strip('"').strip("'")
                    if any(d in val for d in ("debian", "ubuntu")):
                        return "debian"
                    if any(d in val for d in ("fedora", "rhel", "centos")):
                        return "fedora"
                    if "arch" in val:
                        return "arch"
                    if "suse" in val:
                        return "suse"
        except (FileNotFoundError, OSError):
            pass
        if shutil.which("apt"):
            return "debian"
        if shutil.which("dnf"):
            return "fedora"
        if shutil.which("pacman"):
            return "arch"
        if shutil.which("zypper"):
            return "suse"
        return "unknown"

    def _try_install_venv_package(self, python_exe: str, callback=None) -> bool:
        if _platform.system().lower() != "linux":
            return False

        distro = self._detect_distro_family()

        py_ver = ""
        try:
            r = _run(
                [python_exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=5,
            )
            py_ver = r.stdout.strip()
        except Exception:
            pass

        if distro == "debian":
            packages = []
            if py_ver:
                packages.append(f"python{py_ver}-venv")
                packages.append(f"python{py_ver}-pip")
            packages.append("python3-venv")
            packages.append("python3-pip")
            packages.append("python-is-python3")
            install_cmd = ["apt", "install", "-y"] + packages
        elif distro in ("fedora", "arch"):
            return True
        elif distro == "suse":
            install_cmd = ["zypper", "--non-interactive", "install", "python3-venv"]
        else:
            return False

        if callback:
            callback(f"Installing python3-venv (requires root)...")

        for cmd in [["pkexec"] + install_cmd, ["sudo"] + install_cmd]:
            try:
                result = _run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    if callback:
                        callback("✅ python3-venv installed successfully!")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        return False

    # ── Delete ─────────────────────────────────────────────────────────────

    def delete_venv(self, name: str, callback=None, env_path=None, env_type: str = "venv") -> tuple[bool, str]:
        """Delete a virtual environment.
        For poetry envs: deletes both the project marker dir (base_dir/name) AND the real venv (env_path).
        For other envs: deletes base_dir/name or env_path if given.
        """
        _log.info(f"delete_venv: name={name!r} env_type={env_type!r} env_path={env_path!r}")
        banner_start(
            f"Deleting environment '{name}'",
            details=[
                f"Type: {env_type}",
                f"Path: {env_path or (self.base_dir / name)}",
            ],
        )
        venv_path = Path(env_path) if env_path else self.base_dir / name
        if not venv_path.exists():
            # For poetry, try base_dir / name as project dir
            alt = self.base_dir / name
            if alt.exists():
                venv_path = alt
            else:
                banner_error(f"Environment '{name}' not found", details=[f"Looked at: {venv_path}"])
                return False, f"Environment '{name}' not found"
        try:
            if callback:
                callback(f"Deleting {name}...")
            shutil.rmtree(venv_path)
            # For poetry: also delete the project marker dir in base_dir if different
            if env_type == "poetry" and env_path:
                for _item in self.base_dir.iterdir():
                    if not _item.is_dir():
                        continue
                    _marker = _item / ".venvstudio_env"
                    if _marker.exists():
                        try:
                            import json as _json
                            _data = _json.loads(_marker.read_text())
                            if _data.get("poetry_venv_path", "") == str(env_path):
                                shutil.rmtree(_item, ignore_errors=True)
                                break
                        except Exception:
                            pass
            if callback:
                callback(f"Deleted {name} successfully.")
            banner_success(f"Environment '{name}' deleted", details=[f"Removed: {venv_path}"])
            return True, f"Environment '{name}' deleted successfully"
        except Exception as e:
            banner_error(f"Could not delete '{name}'", details=[str(e)])
            return False, f"Error deleting environment: {str(e)}"

    def invalidate_cache_by_name(self, name: str) -> None:
        self.invalidate_cache(self.base_dir / name)

    def invalidate_all_caches(self) -> None:
        # Clear ALL memory caches
        VenvManager._mem_envs.pop(self._base_key, None)
        VenvManager._mem_envs_valid.pop(self._base_key, None)
        VenvManager._all_cache = None  # force re-read from disk
        # Then mark disk cache as stale
        all_cache = self._load_all_cache()
        for key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        self._save_all_cache(all_cache)

    def sync_cache_with_disk(self) -> None:
        """Remove stale cache entries — but only for envs inside base_dir.
        External envs (pipx, poetry, conda outside base_dir) are preserved."""
        if not self.base_dir.exists():
            return
        existing_keys = {
            self._cache_key(item)
            for item in self.base_dir.iterdir()
            if item.is_dir()
        }
        all_cache = self._load_all_cache()
        # Only remove entries that ARE inside base_dir but no longer exist
        # Keep entries outside base_dir (pipx, poetry, conda) untouched
        base_key = self._cache_key(self.base_dir)
        cleaned = {}
        for k, v in all_cache.items():
            if k.startswith(base_key):
                # Inside base_dir — remove if dir no longer exists
                if k in existing_keys:
                    cleaned[k] = v
            else:
                # Outside base_dir (pipx, poetry, conda) — always keep
                cleaned[k] = v
        if len(cleaned) != len(all_cache):
            self._save_all_cache(cleaned)

    def list_venvs_fast(self, skip_calc: bool = False) -> List[VenvInfo]:
        # Return from memory cache if valid (skip_calc=False only)
        if (not skip_calc
                and self._base_key in VenvManager._mem_envs
                and VenvManager._mem_envs_valid.get(self._base_key)):
            return list(VenvManager._mem_envs[self._base_key])

        venvs = []
        if not self.base_dir.exists():
            return venvs

        # ── Include pipx from its own home dir (not base_dir) ────────────
        try:
            from src.utils.platform_utils import get_pipx_home, get_pipx_executable, get_pipx_cmd
            import sys as _sys
            _pipx_home = get_pipx_home()
            if not _pipx_home:
                if _sys.platform == "win32":
                    _pipx_home = os.path.join(os.environ.get("LOCALAPPDATA", ""), "pipx")
                else:
                    _pipx_home = os.path.join(os.path.expanduser("~"), ".local", "share", "pipx")
            _pipx_home_path = Path(_pipx_home) if _pipx_home else None
            if _pipx_home_path and _pipx_home_path.exists():
                _marker = _pipx_home_path / ".venvstudio_env"
                if _marker.exists():
                    try:
                        with open(_marker) as _f:
                            _mdata = json.load(_f)
                    except Exception:
                        _mdata = {}
                    _info = VenvInfo(
                        name=_mdata.get("name", "pipx"),
                        path=_pipx_home_path,
                        is_valid=True,
                        env_type="pipx",
                    )
                    _info.created = _mdata.get("created", "")
                    # Python version from marker or system python
                    _pyver = _mdata.get("python_version", "")
                    # Check disk cache before subprocess
                    _pcached = self._read_cache(_pipx_home_path)
                    if _pcached:
                        _info.python_version = _pcached.get("python_version", _pyver or "")
                        _info.package_count = _pcached.get("package_count", 0)
                        _info.size = _pcached.get("size", _info.size or "")
                    else:
                        if not _pyver:
                            try:
                                import sys as _sys
                                _r = _run([_sys.executable, "--version"],
                                          capture_output=True, text=True, timeout=5)
                                _pyver = (_r.stdout.strip() or _r.stderr.strip()).replace("Python ", "")
                            except Exception:
                                pass
                        _info.python_version = _pyver
                        try:
                            import sys as _sys
                            from src.utils.platform_utils import get_pipx_cmd as _gpc3
                            _pipx_cmd = (_gpc3() or [_sys.executable, "-m", "pipx"]) + ["list", "--short"]
                            _r = _run(_pipx_cmd, capture_output=True, text=True, timeout=15)
                            if _r.returncode == 0:
                                _lines = [l for l in _r.stdout.strip().splitlines() if l.strip()]
                                _info.package_count = len(_lines)
                        except Exception:
                            _info.package_count = 0
                        self.write_cache(_pipx_home_path, _info.python_version, _info.package_count, _info.size or "")
                    # Size: scan pipx venvs directory
                    try:
                        _venvs_dir = _pipx_home_path / "venvs"
                        if _venvs_dir.exists():
                            _total = 0
                            for _dp, _dns, _fns in os.walk(str(_venvs_dir)):
                                for _fn in _fns:
                                    _fp = os.path.join(_dp, _fn)
                                    if not os.path.islink(_fp):
                                        _total += os.path.getsize(_fp)
                            # Format size
                            for _unit in ["B", "KB", "MB", "GB"]:
                                if _total < 1024:
                                    _info.size = f"{_total:.1f} {_unit}"
                                    break
                                _total /= 1024
                            else:
                                _info.size = f"{_total:.1f} TB"
                    except Exception:
                        pass
                    # Size: scan pipx venvs directory
                    _venvs_dir = _pipx_home_path / "venvs"
                    if _venvs_dir.exists():
                        _total = 0
                        for _dp, _dns, _fns in os.walk(str(_venvs_dir)):
                            for _fn in _fns:
                                _fp = os.path.join(_dp, _fn)
                                try:
                                    if not os.path.islink(_fp):
                                        _total += os.path.getsize(_fp)
                                except OSError:
                                    pass
                        _sz = _total
                        for _unit in ["B", "KB", "MB", "GB"]:
                            if _sz < 1024:
                                _info.size = f"{_sz:.1f} {_unit}"
                                break
                            _sz /= 1024
                        else:
                            _info.size = f"{_sz:.1f} TB"
                    venvs.append(_info)
        except Exception:
            import traceback; traceback.print_exc()

        # ── Include poetry envs from platform-specific poetry virtualenvs dir ─
        try:
            import sys as _sys
            _plat = _sys.platform
            if _plat == "win32":
                _poetry_base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", ""))) / "pypoetry" / "Cache" / "virtualenvs"
            elif _plat == "darwin":
                _poetry_base = Path.home() / "Library" / "Caches" / "pypoetry" / "virtualenvs"
            else:  # linux
                _poetry_base = Path.home() / ".cache" / "pypoetry" / "virtualenvs"
            if _poetry_base.exists():
                for _penv in sorted(_poetry_base.iterdir()):
                    if not _penv.is_dir():
                        continue
                    # Name: strip hash suffix e.g. poetryenv-0KHIYmlT-py3.14 → poetryenv
                    _parts = _penv.name.rsplit("-", 2)
                    _pname = _parts[0] if len(_parts) >= 3 else _penv.name
                    # Apply display name override if user set one
                    _display_override = _penv / ".venvstudio_display_name"
                    if _display_override.exists():
                        try:
                            _dn = _display_override.read_text(encoding="utf-8").strip()
                            if _dn:
                                _pname = _dn
                        except Exception:
                            pass
                    _pinfo = VenvInfo(name=_pname, path=_penv, is_valid=True, env_type="poetry")
                    # Python version from pyvenv.cfg
                    _pycfg = _penv / "pyvenv.cfg"
                    if _pycfg.exists():
                        try:
                            for _line in _pycfg.read_text().splitlines():
                                if _line.strip().startswith("version"):
                                    _ver = _line.split("=", 1)[1].strip()
                                    # Clean: "3.14.3.final.0" → "3.14.3"
                                    _ver_parts = _ver.split(".")
                                    _clean = []
                                    for _p in _ver_parts:
                                        if _p.isdigit():
                                            _clean.append(_p)
                                        else:
                                            break
                                    _pinfo.python_version = ".".join(_clean) if _clean else _ver
                                    break
                        except Exception:
                            pass
                    # Package count — check cache first
                    _pcached = self._read_cache(_penv)
                    if _pcached:
                        _pinfo.package_count = _pcached.get("package_count", 0)
                        _pinfo.size = _pcached.get("size", "")
                        if _pcached.get("python_version"):
                            _pinfo.python_version = _pcached["python_version"]
                    else:
                        _pip_exe = get_pip_executable(_penv)
                        if _pip_exe.exists():
                            try:
                                _r = _run([str(_pip_exe), "list", "--format=json"],
                                          capture_output=True, text=True, timeout=15)
                                if _r.returncode == 0:
                                    _pinfo.package_count = len(json.loads(_r.stdout))
                            except Exception:
                                pass
                        # Size
                        _pinfo.size = get_venv_size(_penv)
                        # Write to cache
                        self.write_cache(_penv, _pinfo.python_version, _pinfo.package_count, _pinfo.size)
                    # Created from pyvenv.cfg or dir stat
                    try:
                        from datetime import datetime as _dt
                        _pinfo.created = _dt.fromtimestamp(_penv.stat().st_ctime).isoformat()
                    except Exception:
                        pass
                    venvs.append(_pinfo)
        except Exception:
            import traceback; traceback.print_exc()

        for item in sorted(self.base_dir.iterdir()):
            if not item.is_dir():
                continue
            # ── Marker-based env (system_tools or conda) ──────────────────
            marker = item / ".venvstudio_env"
            if marker.exists():
                try:
                    with open(marker) as f:
                        marker_data = json.load(f)
                except Exception:
                    marker_data = {}
                env_type = marker_data.get("type", "system_tools")
                # Skip pipx marker in base_dir — listed from its own home
                if env_type == "pipx":
                    continue
                # Skip poetry marker in base_dir — listed from APPDATA/pypoetry/Cache/virtualenvs
                # (marker has poetry_venv_path pointing to real venv; avoid duplicate)
                if env_type == "poetry":
                    continue
                info = VenvInfo(name=item.name, path=item, is_valid=True,
                                env_type=env_type)

                # ── Resolve Python version from marker or venv binary ─────
                marker_pyver = marker_data.get("python_version", "")

                if env_type == "conda":
                    # Check cache first
                    _cached = self._read_cache(item)
                    if _cached:
                        info.python_version = _cached.get("python_version", marker_pyver or "")
                        info.package_count = _cached.get("package_count", 0)
                        info.size = _cached.get("size", "")
                    else:
                        _conda_pyver = ""
                        _conda_py = None
                        for _cand in (
                            item / "python.exe",
                            item / "Scripts" / "python.exe",
                            item / "bin" / "python",
                            item / "bin" / "python3",
                        ):
                            if _cand.exists():
                                _conda_py = _cand
                                break
                        if _conda_py:
                            try:
                                _r = _run([str(_conda_py), "--version"],
                                          capture_output=True, text=True, timeout=5)
                                _conda_pyver = (
                                    _r.stdout.strip() or _r.stderr.strip()
                                ).replace("Python ", "")
                            except Exception:
                                pass
                        info.python_version = _conda_pyver or marker_pyver or ""
                        try:
                            _cmeta = item / "conda-meta"
                            if _cmeta.exists():
                                info.package_count = len([
                                    f for f in _cmeta.iterdir()
                                    if f.suffix == ".json" and f.name != "history"
                                ])
                            else:
                                info.package_count = 0
                        except Exception:
                            info.package_count = 0
                        self.write_cache(item, info.python_version, info.package_count, info.size)

                elif env_type in ("uv", "poetry"):
                    if env_type == "poetry":
                        _venv_path_str = marker_data.get("poetry_venv_path", "")
                        # Always use the real venv path for cache — even if dir check fails
                        _venv_dir = Path(_venv_path_str) if _venv_path_str else item
                        if _venv_dir.exists():
                            info.path = _venv_dir
                        # If real path doesn't exist, fall back to marker dir
                        if not _venv_dir.exists():
                            _venv_dir = item
                    else:
                        _venv_dir = item
                    # Check cache first — avoids pip list subprocess every launch
                    print(f"[Poetry] checking cache for _venv_dir={_venv_dir} exists={_venv_dir.exists()}")
                    _cached = self._read_cache(_venv_dir)
                    if _cached:
                        info.python_version = _cached.get("python_version", marker_pyver or "")
                        info.package_count = _cached.get("package_count", 0)
                        info.size = _cached.get("size", "")
                        if _venv_dir != item:
                            info.size = _cached.get("size", get_venv_size(_venv_dir))
                    else:
                        # Python version from marker or pyvenv.cfg (no subprocess)
                        if marker_pyver:
                            info.python_version = marker_pyver
                        else:
                            _pycfg = _venv_dir / "pyvenv.cfg"
                            if _pycfg.exists():
                                try:
                                    for _line in _pycfg.read_text().splitlines():
                                        if _line.strip().startswith("version"):
                                            info.python_version = _line.split("=", 1)[1].strip()
                                            break
                                except Exception:
                                    pass
                            if not info.python_version:
                                _py = get_python_executable(_venv_dir)
                                if _py.exists():
                                    try:
                                        _r = _run([str(_py), "--version"],
                                                  capture_output=True, text=True, timeout=5)
                                        info.python_version = (
                                            _r.stdout.strip() or _r.stderr.strip()
                                        ).replace("Python ", "")
                                    except Exception:
                                        pass
                        # Count packages
                        _counted = False
                        if env_type == "uv":
                            try:
                                import shutil as _shutil
                                _uv_bin = _shutil.which("uv")
                                if _uv_bin:
                                    _r = _run([_uv_bin, "pip", "list", "--format=json",
                                               "--python", str(get_python_executable(_venv_dir))],
                                              capture_output=True, text=True, timeout=15)
                                    if _r.returncode == 0:
                                        info.package_count = len(json.loads(_r.stdout))
                                        _counted = True
                            except Exception:
                                pass
                        if not _counted:
                            _pip_exe = get_pip_executable(_venv_dir)
                            if _pip_exe.exists():
                                try:
                                    _r = _run([str(_pip_exe), "list", "--format=json"],
                                              capture_output=True, text=True, timeout=15)
                                    if _r.returncode == 0:
                                        info.package_count = len(json.loads(_r.stdout))
                                except Exception:
                                    pass
                        _sz = get_venv_size(_venv_dir)
                        info.size = _sz
                        print(f"[Poetry] write_cache: {_venv_dir} exists={_venv_dir.exists()} py={info.python_version} pkgs={info.package_count}")
                        self.write_cache(_venv_dir, info.python_version, info.package_count, _sz)

                elif env_type == "pipx":
                    # Check cache first
                    _cached = self._read_cache(item)
                    if _cached:
                        info.python_version = _cached.get("python_version", marker_pyver or "")
                        info.package_count = _cached.get("package_count", 0)
                        info.size = _cached.get("size", "")
                    else:
                        if marker_pyver:
                            info.python_version = marker_pyver
                        else:
                            try:
                                import sys as _sys
                                _r = _run([_sys.executable, "--version"],
                                          capture_output=True, text=True, timeout=5)
                                info.python_version = (
                                    _r.stdout.strip() or _r.stderr.strip()
                                ).replace("Python ", "")
                            except Exception:
                                info.python_version = ""
                        try:
                            import sys as _sys
                            _pipx_cmd = (get_pipx_cmd() or [_sys.executable, "-m", "pipx"]) + ["list", "--short"]
                            _r = _run(_pipx_cmd, capture_output=True, text=True, timeout=15)
                            if _r.returncode == 0:
                                _lines = [l for l in _r.stdout.strip().splitlines() if l.strip()]
                                info.package_count = len(_lines)
                            else:
                                info.package_count = 0
                        except Exception:
                            info.package_count = 0
                        self.write_cache(item, info.python_version, info.package_count, info.size)

                else:  # system_tools
                    info.python_version = ""
                    info.package_count = 0

                info.size = get_venv_size(item)
                # Created date: prefer marker, fallback to filesystem
                _marker_created = marker_data.get("created", "")
                if _marker_created:
                    info.created = _marker_created
                else:
                    try:
                        info.created = datetime.fromtimestamp(
                            item.stat().st_ctime).isoformat()
                    except OSError:
                        pass
                venvs.append(info)
                continue
            # ─────────────────────────────────────────────────────────────
            python_exe = get_python_executable(item)
            is_valid = python_exe.exists()
            info = VenvInfo(name=item.name, path=item, is_valid=is_valid)

            meta_file = item / ".venvstudio_meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                    info.created = meta.get("created", "")
                except (json.JSONDecodeError, IOError):
                    pass
            if not info.created:
                try:
                    info.created = datetime.fromtimestamp(item.stat().st_ctime).isoformat()
                except OSError:
                    pass

            if is_valid:
                cached = self._read_cache(item)
                if cached:
                    info.python_version = cached.get("python_version", "?")
                    info.package_count = cached.get("package_count", 0)
                    info.size = cached.get("size", "?")
                else:
                    if skip_calc:
                        info.python_version = "..."
                        info.package_count = 0
                        info.size = "..."
                        venvs.append(info)
                        continue
                    # Try pyvenv.cfg first (no subprocess needed)
                    _pycfg = item / "pyvenv.cfg"
                    if _pycfg.exists():
                        try:
                            for _line in _pycfg.read_text().splitlines():
                                if _line.strip().startswith("version"):
                                    _v = _line.split("=", 1)[1].strip()
                                    _parts = [p for p in _v.split(".") if p.isdigit()]
                                    info.python_version = ".".join(_parts) if _parts else _v
                                    break
                        except Exception:
                            pass
                    if not info.python_version:
                        try:
                            result = _run(
                                [str(python_exe), "--version"],
                                capture_output=True, text=True, timeout=5,
                            )
                            ver = result.stdout.strip() or result.stderr.strip()
                            info.python_version = ver.replace("Python ", "")
                        except Exception:
                            info.python_version = "?"

                    info.size = get_venv_size(item)

                    pip_exe = get_pip_executable(item)
                    if pip_exe.exists():
                        try:
                            result = _run(
                                [str(pip_exe), "list", "--format=json"],
                                capture_output=True, text=True, timeout=15,
                            )
                            if result.returncode == 0:
                                info.package_count = len(json.loads(result.stdout))
                        except Exception:
                            pass

                    self.write_cache(item, info.python_version, info.package_count, info.size)

            # Not a valid Python venv — treat as system tools env and auto-create marker
            if not is_valid:
                info.is_valid = True  # show in list
                info.env_type = "system_tools"
                info.python_version = ""
                info.package_count = 0
                info.size = get_venv_size(item)
                # Auto-create marker so it's recognized next time
                try:
                    import json as _json, datetime as _dt
                    marker = item / ".venvstudio_env"
                    if not marker.exists():
                        with open(marker, "w") as _f:
                            _json.dump({
                                "type": "system_tools",
                                "name": item.name,
                                "created": _dt.datetime.now().isoformat(),
                                "auto_detected": True,
                            }, _f, indent=2)
                except Exception:
                    pass

            venvs.append(info)
        # Store in memory cache for next call
        VenvManager._mem_envs[self._base_key] = list(venvs)
        VenvManager._mem_envs_valid[self._base_key] = True
        return venvs
    def list_venvs(self, use_cache: bool = True) -> List[VenvInfo]:
        venvs = []
        if not self.base_dir.exists():
            return venvs
        for item in sorted(self.base_dir.iterdir()):
            if item.is_dir():
                # Marker-based env (system_tools or conda)
                marker = item / ".venvstudio_env"
                if marker.exists():
                    try:
                        with open(marker) as f:
                            marker_data = json.load(f)
                    except Exception:
                        marker_data = {}
                    env_type = marker_data.get("type", "system_tools")
                    info = VenvInfo(name=item.name, path=item, is_valid=True,
                                    env_type=env_type)
                    marker_pyver = marker_data.get("python_version", "")

                    if env_type == "conda":
                        _conda_pyver = ""
                        _conda_py = None
                        for _cand in (
                            item / "bin" / "python",
                            item / "bin" / "python3",
                            item / "python.exe",
                            item / "Scripts" / "python.exe",
                        ):
                            if _cand.exists():
                                _conda_py = _cand
                                break
                        if _conda_py:
                            try:
                                _r = _run([str(_conda_py), "--version"],
                                          capture_output=True, text=True, timeout=5)
                                _conda_pyver = (
                                    _r.stdout.strip() or _r.stderr.strip()
                                ).replace("Python ", "")
                            except Exception:
                                pass
                        info.python_version = _conda_pyver or marker_pyver or ""
                    elif env_type in ("uv", "poetry"):
                        if marker_pyver:
                            info.python_version = marker_pyver
                        else:
                            _py = get_python_executable(item)
                            if _py.exists():
                                try:
                                    _r = _run([str(_py), "--version"],
                                              capture_output=True, text=True, timeout=5)
                                    _v = (_r.stdout.strip() or _r.stderr.strip()
                                           ).replace("Python ", "")
                                    info.python_version = _v
                                except Exception:
                                    info.python_version = ""
                            else:
                                info.python_version = ""
                        # Count packages via pip executable in the env
                        _pip_exe = get_pip_executable(item)
                        if _pip_exe.exists():
                            try:
                                _r = _run(
                                    [str(_pip_exe), "list", "--format=json"],
                                    capture_output=True, text=True, timeout=15,
                                )
                                if _r.returncode == 0:
                                    info.package_count = len(json.loads(_r.stdout))
                            except Exception:
                                pass
                    elif env_type == "pipx":
                        if marker_pyver:
                            info.python_version = marker_pyver
                        else:
                            try:
                                import sys as _sys
                                _r = _run([_sys.executable, "--version"],
                                          capture_output=True, text=True, timeout=5)
                                info.python_version = (
                                    _r.stdout.strip() or _r.stderr.strip()
                                ).replace("Python ", "")
                            except Exception:
                                info.python_version = ""
                        try:
                            import sys as _sys
                            from src.utils.platform_utils import get_pipx_cmd as _gpc2
                            _pipx_cmd = (_gpc2() or [_sys.executable, "-m", "pipx"]) + ["list", "--short"]
                            _r = _run(_pipx_cmd,
                                      capture_output=True, text=True, timeout=15)
                            if _r.returncode == 0:
                                _lines = [l for l in _r.stdout.strip().splitlines() if l.strip()]
                                info.package_count = len(_lines)
                            else:
                                info.package_count = 0
                        except Exception:
                            info.package_count = 0
                    else:
                        info.python_version = ""
                        info.package_count = 0

                    info.size = get_venv_size(item)
                    # Created date: prefer marker, fallback to filesystem
                    _marker_created = marker_data.get("created", "")
                    if _marker_created:
                        info.created = _marker_created
                    else:
                        try:
                            info.created = datetime.fromtimestamp(
                                item.stat().st_ctime).isoformat()
                        except OSError:
                            pass
                    venvs.append(info)
                    continue
                info = self.get_venv_info(item.name, use_cache=use_cache)
                if info:
                    venvs.append(info)
        return venvs

    # ── Cache helpers ──────────────────────────────────────────────────────

    def _get_cache_file(self) -> Path:
        system = _platform.system().lower()
        if system == "windows":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif system == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        cache_dir = base / "VenvStudio"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "env_cache.json"

    def _load_all_cache(self) -> Dict[str, Any]:
        """Load cache from memory if available, otherwise from disk once."""
        if VenvManager._all_cache is not None:
            return VenvManager._all_cache
        f = self._get_cache_file()
        if not f.exists():
            VenvManager._all_cache = {}
            return VenvManager._all_cache
        try:
            VenvManager._all_cache = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            VenvManager._all_cache = {}
        return VenvManager._all_cache

    def _save_all_cache(self, data: Dict[str, Any]) -> None:
        VenvManager._all_cache = data  # update memory cache
        try:
            cache_file = self._get_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[VenvStudio] Cache write error: {e}")

    def _cache_key(self, venv_path: Path) -> str:
        """Consistent cache key — always forward slashes, no leading slash on Windows."""
        key = str(venv_path.resolve()).replace("\\", "/").replace("\\\\", "/")
        # pathlib.resolve() on Windows sometimes returns /C:/... — strip leading slash
        if len(key) > 2 and key[0] == "/" and key[2] == ":":
            key = key[1:]
        return key

    def _read_cache(self, venv_path: Path) -> Optional[Dict[str, Any]]:
        all_cache = self._load_all_cache()
        key = self._cache_key(venv_path)
        entry = all_cache.get(key)
        if not entry:
            print(f"[Cache] MISS: {key}")
            return None
        if entry.get("needs_refresh", 1) == 1:
            print(f"[Cache] STALE: {key}")
            return None
        print(f"[Cache] HIT: {key}")
        return entry

    def write_cache(self, venv_path: Path, python_version: str, package_count: int, size: str) -> None:
        all_cache = self._load_all_cache()
        all_cache[self._cache_key(venv_path)] = {
            "python_version": python_version,
            "package_count": package_count,
            "size": size,
            "needs_refresh": 0,
        }
        self._save_all_cache(all_cache)
        print(f"[Cache] Written: {venv_path} -> {python_version}, {package_count} pkgs, {size}")
        print(f"[Cache] File: {self._get_cache_file()}")

    def invalidate_cache(self, venv_path: Path) -> None:
        all_cache = self._load_all_cache()
        key = self._cache_key(venv_path)
        if key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        else:
            all_cache[key] = {"needs_refresh": 1}
        self._save_all_cache(all_cache)

    # ── Venv info ──────────────────────────────────────────────────────────

    def get_venv_info(self, name: str, use_cache: bool = True) -> Optional[VenvInfo]:
        venv_path = self.base_dir / name
        if not venv_path.exists():
            return None

        python_exe = get_python_executable(venv_path)
        is_valid = python_exe.exists()

        info = VenvInfo(name=name, path=venv_path, is_valid=is_valid)

        meta_file = venv_path / ".venvstudio_meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                info.created = meta.get("created", "")
            except (json.JSONDecodeError, IOError):
                pass
        if not info.created:
            try:
                info.created = datetime.fromtimestamp(venv_path.stat().st_ctime).isoformat()
            except OSError:
                pass

        if use_cache and is_valid:
            cached = self._read_cache(venv_path)
            if cached:
                info.python_version = cached.get("python_version", "Unknown")
                info.package_count = cached.get("package_count", 0)
                info.size = cached.get("size", "N/A")
                return info

        if is_valid:
            try:
                result = _run(
                    [str(python_exe), "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                ver = result.stdout.strip() or result.stderr.strip()
                info.python_version = ver.replace("Python ", "")
            except (subprocess.TimeoutExpired, Exception):
                info.python_version = "Unknown"

            info.size = get_venv_size(venv_path)

            pip_exe = get_pip_executable(venv_path)
            if pip_exe.exists():
                try:
                    result = _run(
                        [str(pip_exe), "list", "--format=json"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode == 0:
                        info.package_count = len(json.loads(result.stdout))
                except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
                    pass

            self.write_cache(venv_path, info.python_version, info.package_count, info.size)

        return info

    def clone_venv(self, source_name: str, target_name: str, callback=None,
                   source_path: Optional[str] = None, source_type: str = "venv") -> tuple[bool, str]:
        _log.info(f"clone_venv: {source_name!r} → {target_name!r} "
                  f"source_type={source_type!r} source_path={source_path!r}")
        banner_start(
            f"Cloning '{source_name}' → '{target_name}'",
            details=[
                f"Type: {source_type}",
                f"Source: {source_path or (self.base_dir / source_name)}",
                f"Target: {self.base_dir / target_name}",
            ],
        )
        # ── Env-type guards: pipx / poetry not supported via Clone ─────────
        if source_type == "pipx":
            banner_warning(
                f"Cloning a pipx env is not supported",
                details=["pipx apps are single-binary installs.", "Use: pipx install <pkg>"],
            )
            return False, (
                "Cloning a pipx environment is not supported.\n\n"
                "pipx manages its own isolated environments per CLI app.\n"
                "To replicate a pipx app elsewhere, run:\n\n"
                f"    pipx install {source_name}\n"
                "    pipx reinstall-all\n\n"
                "Or list installed apps with:\n\n"
                "    pipx list"
            )
        if source_type == "poetry":
            # ── Poetry clone: pip freeze from real venv → new poetry project → install ─
            try:
                import shutil as _sh
                poetry_bin = _sh.which("poetry") or _sh.which("poetry.exe")
                if not poetry_bin:
                    banner_warning(
                        "poetry not found — cannot clone Poetry env",
                        details=["Install poetry via Settings → Toolchain Manager"],
                    )
                    return False, (
                        "poetry not found in PATH.\n\n"
                        "Install it via Settings → Toolchain Manager, or manually:\n"
                        "    pip install poetry"
                    )

                # Resolve real venv path (may be in .cache/pypoetry/virtualenvs/)
                source_path_obj = Path(source_path) if source_path else (self.base_dir / source_name)
                real_venv = source_path_obj
                # If source_path is a poetry virtualenvs path, use it directly
                # Otherwise look for pyvenv.cfg to confirm it's a real venv
                if not (real_venv / "pyvenv.cfg").exists():
                    banner_error(
                        f"Could not find valid Poetry venv at {real_venv}",
                        details=["pyvenv.cfg not found"],
                    )
                    return False, f"Could not find valid Poetry environment at {real_venv}"

                # Get Python from the real venv
                _po_py = real_venv / ("Scripts" if sys.platform == "win32" else "bin") / (
                    "python.exe" if sys.platform == "win32" else "python"
                )
                if not _po_py.exists():
                    return False, f"Python interpreter not found in Poetry env at {_po_py}"

                # pip freeze from real venv
                if callback:
                    callback(f"Reading packages from '{source_name}' (pip freeze)...")
                _pip = real_venv / ("Scripts" if sys.platform == "win32" else "bin") / (
                    "pip.exe" if sys.platform == "win32" else "pip"
                )
                if _pip.exists():
                    _freeze_r = _run([str(_pip), "freeze"],
                                     capture_output=True, text=True, timeout=30)
                else:
                    _freeze_r = _run([str(_po_py), "-m", "pip", "freeze"],
                                     capture_output=True, text=True, timeout=30)
                requirements = _freeze_r.stdout if _freeze_r.returncode == 0 else ""

                # Detect Python version
                _pyver_str = ""
                try:
                    _pv = _run([str(_po_py), "--version"],
                               capture_output=True, text=True, timeout=5)
                    _pyver_str = (_pv.stdout.strip() or _pv.stderr.strip()).replace("Python ", "")
                except Exception:
                    pass

                # Create new poetry project
                target_path = self.base_dir / target_name
                if callback:
                    callback(f"Creating new Poetry project '{target_name}'...")
                target_path.mkdir(parents=True, exist_ok=True)
                _new_r = _run([poetry_bin, "new", str(target_path)],
                              capture_output=True, text=True, timeout=120,
                              cwd=str(target_path.parent))
                if _new_r.returncode != 0:
                    # Try init if new fails (dir already exists etc.)
                    _init_r = _run([poetry_bin, "init", "--no-interaction", "--name", target_name],
                                   capture_output=True, text=True, timeout=60,
                                   cwd=str(target_path))
                    if _init_r.returncode != 0:
                        shutil.rmtree(target_path, ignore_errors=True)
                        return False, f"poetry new/init failed:\n{_new_r.stderr[:400]}"

                # Use same Python version
                if _pyver_str:
                    _use_r = _run([poetry_bin, "env", "use", str(_po_py)],
                                  capture_output=True, text=True, timeout=60,
                                  cwd=str(target_path))

                # Install packages
                if requirements.strip():
                    if callback:
                        callback(f"Installing packages into '{target_name}'...")
                    req_file = target_path / "requirements_clone.txt"
                    req_file.write_text(requirements)
                    _inst_r = _run([poetry_bin, "run", "pip", "install", "-r", str(req_file)],
                                   capture_output=True, text=True, timeout=600,
                                   cwd=str(target_path))
                    req_file.unlink(missing_ok=True)
                    if _inst_r.returncode != 0:
                        # Non-fatal — env created but some packages may have failed
                        if callback:
                            callback("⚠ Some packages may not have installed — check manually")
                else:
                    # No packages — just run poetry install to create the venv
                    _run([poetry_bin, "install", "--no-root"],
                         capture_output=True, text=True, timeout=120,
                         cwd=str(target_path))

                # Get real venv path
                _po_venv_path = None
                try:
                    _einfo = _run([poetry_bin, "env", "info", "--path"],
                                  capture_output=True, text=True, timeout=30,
                                  cwd=str(target_path))
                    _ep = _einfo.stdout.strip()
                    if _ep and Path(_ep).exists():
                        _po_venv_path = _ep
                except Exception:
                    pass

                # Write marker
                import json as _json, datetime as _dt
                with open(target_path / ".venvstudio_env", "w") as _f:
                    _json.dump({
                        "type": "poetry",
                        "name": target_name,
                        "python_version": _pyver_str,
                        "poetry_venv_path": _po_venv_path or "",
                        "created": _dt.datetime.now().isoformat(),
                    }, _f, indent=2)

                banner_success(
                    f"Poetry env cloned to '{target_name}'",
                    details=[
                        f"Source: {real_venv}",
                        f"Target project: {target_path}",
                        f"Python: {_pyver_str or 'unknown'}",
                    ],
                )
                return True, f"Poetry environment '{source_name}' cloned to '{target_name}' successfully"

            except Exception as e:
                banner_error(f"Could not clone Poetry env '{source_name}'", details=[str(e)])
                return False, f"Error cloning Poetry environment: {e}"

        source_path_obj = Path(source_path) if source_path else (self.base_dir / source_name)
        if not source_path_obj.exists():
            return False, f"Source environment '{source_name}' not found at {source_path_obj}"

        target_path = self.base_dir / target_name
        if target_path.exists():
            return False, f"Target environment '{target_name}' already exists"

        # ── conda clone via micromamba create --clone ──────────────────────
        if source_type == "conda":
            try:
                from src.core.micromamba_installer import get_micromamba_exe, write_conda_marker
                mm = get_micromamba_exe()
                if not mm:
                    return False, (
                        "micromamba not found. Install it via Settings → Toolchain Manager, "
                        "or clone manually:\n\n"
                        f"    micromamba env export -p {source_path_obj} > env.yml\n"
                        f"    micromamba create -p {target_path} --file env.yml"
                    )
                if callback:
                    callback(f"Cloning conda env to '{target_name}'...")
                result = _run(
                    [str(mm), "create", "-p", str(target_path),
                     "--clone", str(source_path_obj), "--yes"],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode != 0:
                    return False, f"micromamba clone failed:\n{result.stderr.strip() or result.stdout.strip()}"

                # Write marker so VenvStudio recognizes it as conda
                # Try to detect python version from the new env
                _pyver = ""
                try:
                    _py = get_python_executable(target_path)
                    if _py.exists():
                        _r = _run([str(_py), "--version"],
                                  capture_output=True, text=True, timeout=5)
                        _pyver = (_r.stdout or _r.stderr).strip().replace("Python", "").strip()
                except Exception:
                    pass
                try:
                    write_conda_marker(target_path, python_version=_pyver or "3.12")
                except Exception:
                    pass

                banner_success(
                    f"Conda env cloned to '{target_name}'",
                    details=[
                        f"Source: {source_path_obj}",
                        f"Target: {target_path}",
                        f"Python: {_pyver or 'unknown'}",
                    ],
                )
                return True, f"Conda environment '{source_name}' cloned to '{target_name}' successfully"
            except Exception as e:
                banner_error(f"Could not clone conda env '{source_name}'", details=[str(e)])
                return False, f"Error cloning conda env: {e}"

        # ── uv clone: uv pip freeze → uv venv → uv pip install ─────────────
        if source_type == "uv":
            try:
                import shutil as _sh
                uv_bin = _sh.which("uv")
                if not uv_bin:
                    # Platform-aware manual command example
                    from src.utils.platform_utils import get_platform as _gp
                    if _gp() == "windows":
                        _src_py_hint = f"{source_path_obj}\\Scripts\\python.exe"
                        _tgt_py_hint = f"{target_path}\\Scripts\\python.exe"
                    else:
                        _src_py_hint = f"{source_path_obj}/bin/python"
                        _tgt_py_hint = f"{target_path}/bin/python"
                    return False, (
                        "uv not found in PATH. Install it via Settings → Toolchain Manager,\n"
                        "or clone manually:\n\n"
                        f"    uv pip freeze --python {_src_py_hint} > req.txt\n"
                        f"    uv venv {target_path}\n"
                        f"    uv pip install -r req.txt --python {_tgt_py_hint}"
                    )

                src_py = get_python_executable(source_path_obj)
                if not src_py.exists():
                    return False, f"Source Python interpreter not found at {src_py}"

                if callback:
                    callback(f"Reading packages from '{source_name}' (uv pip freeze)...")
                result = _run(
                    [uv_bin, "pip", "freeze", "--python", str(src_py)],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0:
                    return False, f"uv pip freeze failed:\n{result.stderr.strip()}"
                requirements = result.stdout

                if callback:
                    callback(f"Creating new uv env '{target_name}'...")
                # Use the same Python as source to preserve version
                result = _run(
                    [uv_bin, "venv", str(target_path), "--python", str(src_py)],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode != 0:
                    # Retry without --python in case the source interp isn't discoverable
                    result = _run(
                        [uv_bin, "venv", str(target_path)],
                        capture_output=True, text=True, timeout=60,
                    )
                    if result.returncode != 0:
                        return False, f"uv venv failed:\n{result.stderr.strip()}"

                if requirements.strip():
                    req_file = target_path / "requirements_clone.txt"
                    with open(req_file, "w") as f:
                        f.write(requirements)

                    target_py = get_python_executable(target_path)
                    if callback:
                        callback(f"Installing packages into '{target_name}' (uv pip install)...")
                    result = _run(
                        [uv_bin, "pip", "install", "-r", str(req_file),
                         "--python", str(target_py)],
                        capture_output=True, text=True, timeout=600,
                    )
                    req_file.unlink(missing_ok=True)
                    if result.returncode != 0:
                        return False, f"Created env but failed to install some packages:\n{result.stderr.strip()}"

                banner_success(
                    f"uv env cloned to '{target_name}'",
                    details=[f"Source: {source_path_obj}", f"Target: {target_path}"],
                )
                return True, f"uv environment '{source_name}' cloned to '{target_name}' successfully"
            except Exception as e:
                banner_error(f"Could not clone uv env '{source_name}'", details=[str(e)])
                return False, f"Error cloning uv env: {e}"

        # ── venv clone (default): pip freeze → create → pip install -r ─────
        source_pip = get_pip_executable(source_path_obj)
        if not source_pip.exists():
            return False, (
                f"Source pip not found at {source_pip}.\n\n"
                f"This env appears to have no pip installed. Install pip first, or\n"
                f"recreate the env with '--with-pip' and try again."
            )

        try:
            result = _run(
                [str(source_pip), "freeze"],
                capture_output=True, text=True, timeout=15,
            )
            requirements = result.stdout

            success, msg = self.create_venv(target_name, callback=callback)
            if not success:
                return False, msg

            if requirements.strip():
                req_file = target_path / "requirements_clone.txt"
                with open(req_file, "w") as f:
                    f.write(requirements)

                target_pip = get_pip_executable(target_path)
                if callback:
                    callback(f"Installing packages into '{target_name}'...")

                result = _run(
                    [str(target_pip), "install", "-r", str(req_file)],
                    capture_output=True, text=True, timeout=300,
                )
                req_file.unlink(missing_ok=True)

                if result.returncode != 0:
                    banner_error(
                        f"Clone completed but some packages failed",
                        details=[f"Target: {target_path}", "Check pip output below"],
                    )
                    return False, f"Created env but failed to install some packages:\n{result.stderr}"

            # Count packages for nice summary
            _pkg_count = 0
            try:
                _pkg_count = len([l for l in requirements.splitlines() if l and not l.startswith("#")])
            except Exception:
                pass
            banner_success(
                f"Environment '{target_name}' ready!",
                details=[
                    f"Cloned from: {source_name}",
                    f"Path: {target_path}",
                    f"Packages reinstalled: {_pkg_count}" if _pkg_count else f"Packages reinstalled: ok",
                ],
            )
            return True, f"Environment '{source_name}' cloned to '{target_name}' successfully"

        except Exception as e:
            banner_error(f"Could not clone '{source_name}'", details=[str(e)])
            return False, f"Error cloning environment: {str(e)}"

    def rename_venv(self, old_name: str, new_name: str,
                    old_path: Optional[str] = None, env_type: str = "venv") -> tuple[bool, str]:
        _log.info(f"rename_venv: {old_name!r} → {new_name!r} env_type={env_type!r}")
        banner_start(
            f"Renaming '{old_name}' → '{new_name}' (folder-only)",
            details=[f"Type: {env_type}", f"Path: {old_path or (self.base_dir / old_name)}"],
        )
        # ── Env-type guards ────────────────────────────────────────────────
        if env_type == "pipx":
            banner_warning(
                "Rename not supported for pipx",
                details=["Use: pipx uninstall + pipx install"],
            )
            return False, (
                "Renaming a pipx environment is not supported.\n\n"
                "pipx apps are identified by their package name. To 'rename':\n\n"
                f"    pipx uninstall {old_name}\n"
                f"    pipx install {new_name}"
            )
        if env_type == "poetry":
            banner_warning(
                "Rename not supported for Poetry",
                details=["Edit pyproject.toml name + poetry install"],
            )
            return False, (
                "Renaming a Poetry environment by folder is not supported.\n\n"
                "Poetry env names are derived from the project name in pyproject.toml.\n"
                "To rename, update the 'name' field in your pyproject.toml, then run:\n\n"
                "    poetry env remove --all\n"
                "    poetry install"
            )
        if env_type == "conda":
            banner_warning(
                "In-place rename not supported for conda",
                details=["Use Rename (Full) instead — safe clone + delete"],
            )
            return False, (
                "Renaming a conda environment in place is not supported by micromamba.\n\n"
                "Use the 'Rename (Full)' option instead, which will:\n"
                "  1. Export packages from the old env\n"
                "  2. Create a new env with the desired name\n"
                "  3. Delete the old env\n\n"
                "Or do it manually:\n\n"
                f"    micromamba env export -n {old_name} > env.yml\n"
                f"    micromamba create -n {new_name} --file env.yml\n"
                f"    micromamba env remove -n {old_name} --yes"
            )

        # ── venv / uv: folder rename ───────────────────────────────────────
        old_path_obj = Path(old_path) if old_path else (self.base_dir / old_name)
        new_path_obj = self.base_dir / new_name

        if not old_path_obj.exists():
            banner_error(f"Source env '{old_name}' not found", details=[f"Looked at: {old_path_obj}"])
            return False, f"Environment '{old_name}' not found at {old_path_obj}"
        if new_path_obj.exists():
            banner_error(f"Target '{new_name}' already exists", details=[f"Path: {new_path_obj}"])
            return False, f"Environment '{new_name}' already exists"

        try:
            old_path_obj.rename(new_path_obj)
            banner_success(
                f"Renamed '{old_name}' → '{new_name}'",
                details=[
                    f"Old path: {old_path_obj}",
                    f"New path: {new_path_obj}",
                    "⚠ Note: activate scripts may contain old path — run Rename (Full) for a full rewrite",
                ],
            )
            return True, f"Environment '{old_name}' renamed to '{new_name}'"
        except Exception as e:
            banner_error(f"Could not rename '{old_name}'", details=[str(e)])
            return False, f"Error renaming environment: {str(e)}"

    def rename_full_venv(self, old_name: str, new_name: str, callback=None,
                         old_path: Optional[str] = None, env_type: str = "venv") -> tuple[bool, str]:
        """
        Full rename: clone old env to new name, then delete old.
        Slower but safe — all packages reinstalled, paths correct.
        """
        _log.info(f"rename_full_venv: {old_name!r} → {new_name!r} env_type={env_type!r}")
        banner_start(
            f"Full rename '{old_name}' → '{new_name}'",
            details=[
                f"Type: {env_type}",
                "Step 1/2: Clone with new name",
                "Step 2/2: Delete old env",
                "⏳ This may take a while (packages reinstalled)",
            ],
        )
        # pipx full rename not supported — clone_venv will return helpful error
        if env_type == "pipx":
            return self.clone_venv(old_name, new_name, callback=callback,
                                   source_path=old_path, source_type=env_type)

        if callback:
            callback(f"Cloning '{old_name}' → '{new_name}'...")
        success, msg = self.clone_venv(old_name, new_name, callback=callback,
                                       source_path=old_path, source_type=env_type)
        if not success:
            banner_error(
                f"Full rename aborted",
                details=[f"Could not clone '{old_name}'", "Old env is untouched", msg.splitlines()[0] if msg else ""],
            )
            return False, f"Failed to create '{new_name}': {msg}"

        if callback:
            callback(f"Deleting old environment '{old_name}'...")
        try:
            # Use delete_venv so conda/marker handling is correct
            success, msg = self.delete_venv(old_name, callback=callback,
                                            env_path=old_path, env_type=env_type)
            if not success:
                banner_warning(
                    f"New env created but old env remains",
                    details=[f"'{new_name}' is ready", f"Could not delete '{old_name}' — delete manually"],
                )
                return False, f"'{new_name}' created but could not delete '{old_name}': {msg}"
        except Exception as e:
            banner_warning(
                f"New env created but old env remains",
                details=[f"'{new_name}' is ready", f"Delete '{old_name}' failed: {e}"],
            )
            return False, f"'{new_name}' created but could not delete '{old_name}': {e}"

        banner_success(
            f"Full rename complete: '{old_name}' → '{new_name}'",
            details=["All packages reinstalled with correct paths", "Old env deleted"],
        )
        return True, f"Environment '{old_name}' fully renamed to '{new_name}'"

    def set_poetry_display_name(self, env_path, new_display_name: str) -> tuple[bool, str]:
        """Set a display name override for a Poetry env (VenvStudio-only, doesn't touch Poetry itself).
        The override is stored in a .venvstudio_display_name file inside the poetry env dir.
        """
        _log.info(f"set_poetry_display_name: path={env_path!r} new_name={new_display_name!r}")
        try:
            _p = Path(env_path)
            if not _p.exists() or not _p.is_dir():
                banner_error("Poetry env path not found", details=[f"Path: {env_path}"])
                return False, f"Poetry environment path not found: {env_path}"
            marker = _p / ".venvstudio_display_name"
            if new_display_name.strip():
                marker.write_text(new_display_name.strip(), encoding="utf-8")
                banner_success(
                    "Display name set",
                    details=[f"Env: {_p.name}", f"New display name: {new_display_name.strip()}"],
                )
                return True, f"Display name set to '{new_display_name.strip()}'"
            else:
                # Empty → remove override (revert to default stripped name)
                if marker.exists():
                    marker.unlink()
                banner_success(
                    "Display name override cleared",
                    details=[f"Env: {_p.name}", "Reverted to default poetry name"],
                )
                return True, "Display name override cleared"
        except Exception as e:
            banner_error("Could not set display name", details=[str(e)])
            return False, f"Could not set display name: {e}"

