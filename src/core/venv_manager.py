"""
VenvStudio - Virtual Environment Manager
Core operations: create, delete, list, inspect venvs

This module holds the VenvManager base (create/delete/list/inspect) and
composes cache/clone/rename behaviour from mixins in sibling modules:
  - venv_manager_common : shared helpers (_run, _robust_rmtree, banners)
  - venv_manager_cache  : _CacheMixin (env_cache.json persistence)
  - venv_manager_clone  : _CloneMixin (clone_venv)
  - venv_manager_rename : _RenameMixin (rename_venv, rename_full_venv, ...)
The public VenvManager API is unchanged.
"""

import os
import sys
import stat
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

# Shared module-level helpers (moved out to avoid a huge single file).
from src.core.venv_manager_common import (
    _log,
    _fmt_path,
    _run,
    _robust_rmtree,
    _find_windows_python,
    _SUBPROCESS_FLAGS,
    banner_start,
    banner_success,
    banner_error,
    banner_warning,
)

# Behaviour mixins (composed into VenvManager below).
from src.core.venv_manager_cache import _CacheMixin
from src.core.venv_manager_clone import _CloneMixin
from src.core.venv_manager_rename import _RenameMixin


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




class VenvManager(_CacheMixin, _CloneMixin, _RenameMixin):
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
        For pipx envs: deletes the pipx home directory AND its .venvstudio_env marker
          (the marker controls listing — without removing it the row would survive
          the disk delete and reappear after the next refresh, which is B182).
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
            # Pipx delete (v1.4.92): wipe the whole pipx home and re-create
            # a fresh empty marker. User expectation when deleting from the
            # GUI is "remove everything", not "untrack only" — terminal users
            # who want CLI-managed pipx should manage it via `pipx uninstall`
            # outside VenvStudio anyway. Earlier B182 behaviour preserved
            # disk contents which surprised users (folder still 1.8 GB after
            # "delete"). After rmtree we call ensure_pipx_env() so the row
            # comes back empty, ready for fresh installs.
            if env_type == "pipx":
                try:
                    _robust_rmtree(venv_path)
                    _log.info(f"delete_venv: removed pipx home {venv_path}")
                except Exception as _re:
                    _log.warning(f"delete_venv: rmtree pipx home failed: {_re}")
                # Drop cache entry so listing doesn't show stale row
                try:
                    self.invalidate_cache(venv_path)
                except Exception:
                    pass
                # Re-seed an empty pipx home with marker so the env row
                # reappears clean (0 packages, 0 B) on the next refresh.
                try:
                    self.ensure_pipx_env()
                except Exception as _ee:
                    _log.warning(f"delete_venv: ensure_pipx_env after rmtree failed: {_ee}")
                if callback:
                    callback(f"Deleted pipx home for {name}")
                banner_success(
                    f"pipx environment '{name}' deleted",
                    details=[
                        f"Removed: {venv_path}",
                        "All previously installed pipx apps were removed.",
                    ],
                )
                return True, f"Environment '{name}' deleted successfully"
            _robust_rmtree(venv_path)
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
                                try:
                                    _robust_rmtree(_item)
                                except Exception as _re:
                                    _log.warning(f"delete_venv: could not remove poetry marker dir {_item}: {_re}")
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
        type(self)._all_cache = None  # force re-read from disk
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
                        # Size has to be computed BEFORE write_cache below,
                        # otherwise size=N/A gets cached and the Size column
                        # in the env table shows "N/A" forever.
                    # Size: scan the full pipx home (venvs + shared + py).
                    # Pipx symlinks site-packages from venvs/<pkg>/lib/.../
                    # into shared/, so scanning only venvs/ with islink
                    # filtering yields ~0 B even when ~/.local/share/pipx
                    # is hundreds of MB. We walk the whole home dir and
                    # count regular files; this matches `du -sh` closely
                    # enough for the env table.
                    try:
                        _total = 0
                        if _pipx_home_path.exists():
                            for _dp, _dns, _fns in os.walk(str(_pipx_home_path)):
                                for _fn in _fns:
                                    _fp = os.path.join(_dp, _fn)
                                    try:
                                        _total += os.path.getsize(_fp)
                                    except OSError:
                                        pass
                        for _unit in ["B", "KB", "MB", "GB"]:
                            if _total < 1024:
                                _info.size = f"{_total:.1f} {_unit}"
                                break
                            _total /= 1024
                        else:
                            _info.size = f"{_total:.1f} TB"
                    except Exception:
                        pass
                    # Now that size is known, persist the cache entry. This
                    # write was previously above (before size was computed)
                    # which made every pipx row stuck on "N/A" in the Size
                    # column until a manual refresh forced recomputation.
                    try:
                        self.write_cache(_pipx_home_path, _info.python_version, _info.package_count, _info.size or "")
                    except Exception:
                        pass
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
                        # Self-heal stale entries: older versions never computed
                        # conda sizes, so cached "N/A"/empty would stick forever.
                        if not info.size or info.size == "N/A":
                            info.size = get_venv_size(item)
                            self.write_cache(item, info.python_version, info.package_count, info.size)
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
                        # Size MUST be computed before write_cache (same ordering
                        # lesson as the pipx fix), otherwise "N/A" gets cached and
                        # the Size column stays wrong until a forced refresh.
                        info.size = get_venv_size(item)
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
                    _log.debug(f"📝 [Poetry] cache check: venv_dir={_fmt_path(_venv_dir)} exists={_venv_dir.exists()}")
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
                        _log.debug(f"📝 [Poetry] write_cache: {_fmt_path(_venv_dir)} py={info.python_version} pkgs={info.package_count}")
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
