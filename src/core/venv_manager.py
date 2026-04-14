"""
VenvStudio - Virtual Environment Manager
Core operations: create, delete, list, inspect venvs
"""

import os
import sys
import shutil
import subprocess
import json
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
    """subprocess.run wrapper — uses subprocess_args for platform safety."""
    from src.utils.platform_utils import subprocess_args
    # subprocess_args: Windows CREATE_NO_WINDOW + EXE PATH fix, Linux AppImage env clean
    merged = subprocess_args()
    for k, v in merged.items():
        kwargs.setdefault(k, v)
    return subprocess.run(*args, **kwargs)


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

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

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
        venv_path = self.base_dir / name

        if venv_path.exists():
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
                stderr_lower = (result.stderr or "").lower()

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
                        return False, f"Failed to create environment:\n{retry.stderr}"
                    # Install pip manually via ensurepip
                    python_in_venv = get_python_executable(venv_path)
                    if callback:
                        callback("Installing pip manually...")
                    _run(
                        [str(python_in_venv), "-m", "ensurepip"],
                        capture_output=True, text=True, timeout=60,
                    )

                elif "no module named venv" in stderr_lower:
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
                            return False, f"Failed to create environment after installing python3-venv:\n{retry.stderr}"
                    else:
                        return False, (
                            f"Failed to create environment:\n{result.stderr}\n\n"
                            f"💡 The 'venv' module may be missing.\n"
                            f"Install it with your package manager:\n"
                            f"  Debian/Ubuntu/Pardus: sudo apt install python3-venv\n"
                            f"  Fedora: sudo dnf install python3-libs\n"
                            f"  openSUSE: sudo zypper install python3-venv"
                        )
                else:
                    if venv_path.exists():
                        shutil.rmtree(venv_path, ignore_errors=True)
                    return False, f"Failed to create environment:\n{result.stderr}"

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

            return True, f"Environment '{name}' created successfully at {venv_path}"

        except subprocess.TimeoutExpired:
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            return False, "Environment creation timed out (120s)"
        except Exception as e:
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
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
        venv_path = Path(env_path) if env_path else self.base_dir / name
        if not venv_path.exists():
            # For poetry, try base_dir / name as project dir
            alt = self.base_dir / name
            if alt.exists():
                venv_path = alt
            else:
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
            return True, f"Environment '{name}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting environment: {str(e)}"

    def invalidate_cache_by_name(self, name: str) -> None:
        self.invalidate_cache(self.base_dir / name)

    def invalidate_all_caches(self) -> None:
        all_cache = self._load_all_cache()
        for key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        self._save_all_cache(all_cache)

    def sync_cache_with_disk(self) -> None:
        if not self.base_dir.exists():
            return
        existing_keys = {
            self._cache_key(item)
            for item in self.base_dir.iterdir()
            if item.is_dir()
        }
        all_cache = self._load_all_cache()
        cleaned = {k: v for k, v in all_cache.items() if k in existing_keys}
        if len(cleaned) != len(all_cache):
            self._save_all_cache(cleaned)

    def list_venvs_fast(self, skip_calc: bool = False) -> List[VenvInfo]:
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
                    if not _pyver:
                        try:
                            import sys as _sys
                            _r = _run([_sys.executable, "--version"],
                                      capture_output=True, text=True, timeout=5)
                            _pyver = (_r.stdout.strip() or _r.stderr.strip()).replace("Python ", "")
                        except Exception:
                            pass
                    _info.python_version = _pyver
                    # Count installed pipx apps
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
                    # Package count
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
                    # Always try real binary first — marker may have short version
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
                    # Count conda packages from conda-meta (most reliable, no subprocess needed)
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

                elif env_type in ("uv", "poetry"):
                    # For poetry: real venv is at poetry_venv_path in marker
                    # For uv: venv is at item itself
                    if env_type == "poetry":
                        _venv_path_str = marker_data.get("poetry_venv_path", "")
                        _venv_dir = Path(_venv_path_str) if _venv_path_str else item
                        if _venv_dir != item and _venv_dir.exists():
                            info.path = _venv_dir
                            info.size = get_venv_size(_venv_dir)
                    else:
                        _venv_dir = item
                    # Python version from marker or pyvenv.cfg or binary
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
                    # uv envs: no pip.exe, no pip module — use "uv pip list"
                    # poetry/venv envs: pip.exe exists
                    _counted = False
                    if env_type == "uv":
                        try:
                            from src.utils.platform_utils import get_pipx_executable as _dummy
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

                elif env_type == "pipx":
                    # Get Python version — prefer marker, fallback to sys.executable
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
                    # Count installed pipx apps
                    try:
                        import sys as _sys
                        from src.utils.platform_utils import get_pipx_executable as _gpx
                        _pipx_cmd = (get_pipx_cmd() or [_sys.executable, "-m", "pipx"]) + ["list", "--short"]
                        _r = _run(_pipx_cmd,
                                  capture_output=True, text=True, timeout=15)
                        if _r.returncode == 0:
                            _lines = [l for l in _r.stdout.strip().splitlines() if l.strip()]
                            info.package_count = len(_lines)
                        else:
                            info.package_count = 0
                    except Exception:
                        info.package_count = 0

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
        f = self._get_cache_file()
        if not f.exists():
            return {}
        try:
            return json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all_cache(self, data: Dict[str, Any]) -> None:
        try:
            cache_file = self._get_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[VenvStudio] Cache write error: {e}")

    def _cache_key(self, venv_path: Path) -> str:
        return str(venv_path.resolve()).replace("\\", "/").replace("\\\\", "/")

    def _read_cache(self, venv_path: Path) -> Optional[Dict[str, Any]]:
        all_cache = self._load_all_cache()
        entry = all_cache.get(self._cache_key(venv_path))
        if not entry:
            return None
        if entry.get("needs_refresh", 1) == 1:
            return None
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

    def clone_venv(self, source_name: str, target_name: str, callback=None) -> tuple[bool, str]:
        source_path = self.base_dir / source_name
        if not source_path.exists():
            return False, f"Source environment '{source_name}' not found"

        target_path = self.base_dir / target_name
        if target_path.exists():
            return False, f"Target environment '{target_name}' already exists"

        source_pip = get_pip_executable(source_path)

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
                    return False, f"Created env but failed to install some packages:\n{result.stderr}"

            return True, f"Environment '{source_name}' cloned to '{target_name}' successfully"

        except Exception as e:
            return False, f"Error cloning environment: {str(e)}"

    def rename_venv(self, old_name: str, new_name: str) -> tuple[bool, str]:
        old_path = self.base_dir / old_name
        new_path = self.base_dir / new_name

        if not old_path.exists():
            return False, f"Environment '{old_name}' not found"
        if new_path.exists():
            return False, f"Environment '{new_name}' already exists"

        try:
            old_path.rename(new_path)
            return True, f"Environment '{old_name}' renamed to '{new_name}'"
        except Exception as e:
            return False, f"Error renaming environment: {str(e)}"

    def rename_full_venv(self, old_name: str, new_name: str, callback=None) -> tuple[bool, str]:
        """
        Full rename: clone old env to new name, then delete old.
        Slower but safe — all packages reinstalled, paths correct.
        """
        if callback:
            callback(f"Cloning '{old_name}' → '{new_name}'...")
        success, msg = self.clone_venv(old_name, new_name, callback=callback)
        if not success:
            return False, f"Failed to create '{new_name}': {msg}"

        if callback:
            callback(f"Deleting old environment '{old_name}'...")
        old_path = self.base_dir / old_name
        try:
            shutil.rmtree(old_path)
        except Exception as e:
            return False, f"'{new_name}' created but could not delete '{old_name}': {e}"

        return True, f"Environment '{old_name}' fully renamed to '{new_name}'"

