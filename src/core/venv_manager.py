"""
VenvStudio - Virtual Environment Manager
Core operations: create, delete, list, inspect venvs
"""

import os
import sys
import shutil
import subprocess
import json
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "python_version": self.python_version,
            "size": self.size,
            "created": self.created,
            "package_count": self.package_count,
            "is_valid": self.is_valid,
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

        python_exe = python_path or sys.executable
        cmd = [python_exe, "-m", "venv"]

        if not with_pip:
            cmd.append("--without-pip")
        if system_site_packages:
            cmd.append("--system-site-packages")

        cmd.append(str(venv_path))

        try:
            if callback:
                callback(f"Creating environment '{name}'...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                # Clean up on failure
                if venv_path.exists():
                    shutil.rmtree(venv_path, ignore_errors=True)

                # Check if python3-venv is missing (Debian/Ubuntu/Pardus)
                stderr_lower = (result.stderr or "").lower()
                if ("ensurepip" in stderr_lower
                        or "no module named venv" in stderr_lower
                        or "returned non-zero exit" in stderr_lower):
                    venv_installed = self._try_install_venv_package(python_exe, callback)
                    if venv_installed:
                        # Retry venv creation after installing python3-venv
                        if callback:
                            callback(f"Retrying environment creation...")
                        retry = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=120,
                        )
                        if retry.returncode == 0:
                            # Success on retry — continue to pip upgrade below
                            pass
                        else:
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
                    return False, f"Failed to create environment:\n{result.stderr}"

            # Upgrade pip if requested
            pip_exe = get_pip_executable(venv_path)
            python_in_venv = get_python_executable(venv_path)
            if with_pip and pip_exe.exists():
                if callback:
                    callback("Upgrading pip...")
                subprocess.run(
                    [str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

            # Save creation metadata
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
        """Detect Linux distro family from /etc/os-release.
        Returns: 'debian', 'fedora', 'arch', 'suse', or 'unknown'.
        """
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
            # ID_LIKE is more reliable for derivatives (Pardus→debian, Manjaro→arch, etc.)
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
        # Fallback: check for apt/dnf/pacman
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
        """Try to install python3-venv package via system package manager.
        Uses pkexec for graphical root elevation.
        Returns True if installation succeeded.
        """
        import platform as _platform
        if _platform.system().lower() != "linux":
            return False

        distro = self._detect_distro_family()

        # Determine python version suffix (e.g. python3.14-venv)
        py_ver = ""
        try:
            r = subprocess.run(
                [python_exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=5,
            )
            py_ver = r.stdout.strip()
        except Exception:
            pass

        if distro == "debian":
            # Versioned + fallback packages for Debian/Ubuntu/Pardus
            # e.g. python3.13-venv, python3.13-pip, python3-venv, python3-pip, python-is-python3
            packages = []
            if py_ver:
                packages.append(f"python{py_ver}-venv")
                packages.append(f"python{py_ver}-pip")
            packages.append("python3-venv")
            packages.append("python3-pip")
            packages.append("python-is-python3")
            install_cmd = ["apt", "install", "-y"] + packages
        elif distro == "fedora":
            return True  # Fedora includes venv by default
        elif distro == "arch":
            return True  # Arch includes venv by default
        elif distro == "suse":
            install_cmd = ["zypper", "--non-interactive", "install", "python3-venv"]
        else:
            return False

        if callback:
            callback(f"Installing python3-venv (requires root)...")

        # Try pkexec (graphical sudo), then sudo
        sudo_cmds = [
            ["pkexec"] + install_cmd,
            ["sudo"] + install_cmd,
        ]

        for cmd in sudo_cmds:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    if callback:
                        callback("✅ python3-venv installed successfully!")
                    return True
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                continue

        return False

    # ── Delete ─────────────────────────────────────────────────────────────

    def delete_venv(self, name: str, callback=None) -> tuple[bool, str]:
        """Delete a virtual environment."""
        venv_path = self.base_dir / name

        if not venv_path.exists():
            return False, f"Environment '{name}' not found"

        try:
            if callback:
                callback(f"Deleting {name}...")
            shutil.rmtree(venv_path)
            if callback:
                callback(f"Deleted {name} successfully.")
            return True, f"Environment '{name}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting environment: {str(e)}"

    def invalidate_cache_by_name(self, name: str) -> None:
        """Invalidate cache for a named env."""
        self.invalidate_cache(self.base_dir / name)

    def invalidate_all_caches(self) -> None:
        """Set needs_refresh=1 for ALL envs — called on manual Refresh button."""
        all_cache = self._load_all_cache()
        for key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        self._save_all_cache(all_cache)

    def sync_cache_with_disk(self) -> None:
        """Remove cache entries for envs that no longer exist on disk.
        Called on startup to keep cache clean.
        """
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
        """Load env list. Uses cache if available, otherwise calculates and saves cache.
        If skip_calc=True, cache misses return placeholder instead of running subprocess.
        """
        venvs = []
        if not self.base_dir.exists():
            return venvs
        for item in sorted(self.base_dir.iterdir()):
            if not item.is_dir():
                continue
            python_exe = get_python_executable(item)
            is_valid = python_exe.exists()
            info = VenvInfo(name=item.name, path=item, is_valid=is_valid)

            # Creation date (no subprocess)
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
                # Try cache first
                cached = self._read_cache(item)
                if cached:
                    # Cache hit - load instantly
                    info.python_version = cached.get("python_version", "?")
                    info.package_count = cached.get("package_count", 0)
                    info.size = cached.get("size", "?")
                else:
                    # Cache miss
                    if skip_calc:
                        info.python_version = "..."
                        info.package_count = 0
                        info.size = "..."
                        venvs.append(info)
                        continue
                    # Calculate now and save
                    try:
                        result = subprocess.run(
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
                            result = subprocess.run(
                                [str(pip_exe), "list", "--format=json"],
                                capture_output=True, text=True, timeout=15,
                            )
                            if result.returncode == 0:
                                info.package_count = len(json.loads(result.stdout))
                        except Exception:
                            pass

                    # Save to cache
                    self.write_cache(item, info.python_version, info.package_count, info.size)

            venvs.append(info)
        return venvs

    def list_venvs(self, use_cache: bool = True) -> List[VenvInfo]:
        """List all virtual environments. Uses cache for speed."""
        venvs = []
        if not self.base_dir.exists():
            return venvs
        for item in sorted(self.base_dir.iterdir()):
            if item.is_dir():
                info = self.get_venv_info(item.name, use_cache=use_cache)
                if info:
                    venvs.append(info)
        return venvs

    # ── Cache helpers ──────────────────────────────────────────────────────
    # Single cache file in AppData/VenvStudio/env_cache.json
    # Structure: { "C:/venv/ml": {"python_version": "3.14", "package_count": 112, "size": "747MB", "needs_refresh": 0}, ... }

    def _get_cache_file(self) -> Path:
        """Returns path to the single cache file in AppData."""
        import platform as _platform
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
        """Load entire cache file."""
        f = self._get_cache_file()
        if not f.exists():
            return {}
        try:
            return json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_all_cache(self, data: Dict[str, Any]) -> None:
        """Save entire cache file."""
        try:
            cache_file = self._get_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[VenvStudio] Cache write error: {e}")

    def _cache_key(self, venv_path: Path) -> str:
        """Normalize path to consistent cache key."""
        return str(venv_path.resolve()).replace("\\", "/").replace("\\\\", "/")

    def _read_cache(self, venv_path: Path) -> Optional[Dict[str, Any]]:
        """Read cache for a specific env. Returns None if needs_refresh=1."""
        all_cache = self._load_all_cache()
        entry = all_cache.get(self._cache_key(venv_path))
        if not entry:
            return None
        if entry.get("needs_refresh", 1) == 1:
            return None
        return entry

    def write_cache(self, venv_path: Path, python_version: str, package_count: int, size: str) -> None:
        """Write cache for env with needs_refresh=0."""
        all_cache = self._load_all_cache()
        all_cache[self._cache_key(venv_path)] = {
            "python_version": python_version,
            "package_count": package_count,
            "size": size,
            "needs_refresh": 0,
        }
        self._save_all_cache(all_cache)
        print(f"[Cache] Written: {self._cache_key(venv_path)} -> {python_version}, {package_count} pkgs, {size}")
        print(f"[Cache] File: {self._get_cache_file()}")

    def invalidate_cache(self, venv_path: Path) -> None:
        """Set needs_refresh=1 for this env."""
        all_cache = self._load_all_cache()
        key = self._cache_key(venv_path)
        if key in all_cache:
            all_cache[key]["needs_refresh"] = 1
        else:
            all_cache[key] = {"needs_refresh": 1}
        self._save_all_cache(all_cache)

    # ── Venv info ──────────────────────────────────────────────────────────

    def get_venv_info(self, name: str, use_cache: bool = True) -> Optional[VenvInfo]:
        """Get detailed information about a virtual environment.
        If use_cache=True and cache exists, returns cached data instantly.
        """
        venv_path = self.base_dir / name
        if not venv_path.exists():
            return None

        python_exe = get_python_executable(venv_path)
        is_valid = python_exe.exists()

        info = VenvInfo(
            name=name,
            path=venv_path,
            is_valid=is_valid,
        )

        # Get creation date from meta (fast, no subprocess)
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

        # Try cache first (AppData/VenvStudio/env_cache.json)
        if use_cache and is_valid:
            cached = self._read_cache(venv_path)
            if cached:
                info.python_version = cached.get("python_version", "Unknown")
                info.package_count = cached.get("package_count", 0)
                info.size = cached.get("size", "N/A")
                return info

        # Cache miss — fetch from disk/subprocess
        if is_valid:
            # Python version
            try:
                result = subprocess.run(
                    [str(python_exe), "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                ver = result.stdout.strip() or result.stderr.strip()
                info.python_version = ver.replace("Python ", "")
            except (subprocess.TimeoutExpired, Exception):
                info.python_version = "Unknown"

            # Size
            info.size = get_venv_size(venv_path)

            # Package count
            pip_exe = get_pip_executable(venv_path)
            if pip_exe.exists():
                try:
                    result = subprocess.run(
                        [str(pip_exe), "list", "--format=json"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode == 0:
                        info.package_count = len(json.loads(result.stdout))
                except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
                    pass

            # Write to cache for next time
            self.write_cache(venv_path, info.python_version, info.package_count, info.size)

        return info

    def clone_venv(self, source_name: str, target_name: str, callback=None) -> tuple[bool, str]:
        """Clone an environment by creating a new one and installing the same packages."""
        source_path = self.base_dir / source_name
        if not source_path.exists():
            return False, f"Source environment '{source_name}' not found"

        target_path = self.base_dir / target_name
        if target_path.exists():
            return False, f"Target environment '{target_name}' already exists"

        # Get source python and packages
        source_pip = get_pip_executable(source_path)

        try:
            # Get requirements from source
            result = subprocess.run(
                [str(source_pip), "freeze"],
                capture_output=True, text=True, timeout=15,
            )
            requirements = result.stdout

            # Create new environment
            success, msg = self.create_venv(target_name, callback=callback)
            if not success:
                return False, msg

            # Install packages
            if requirements.strip():
                req_file = target_path / "requirements_clone.txt"
                with open(req_file, "w") as f:
                    f.write(requirements)

                target_pip = get_pip_executable(target_path)
                if callback:
                    callback(f"Installing packages into '{target_name}'...")

                result = subprocess.run(
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
        """Rename an environment by renaming its directory."""
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
