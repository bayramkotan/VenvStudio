"""
VenvStudio - Pip Manager
Package installation, removal, listing, and search operations
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from src.utils.platform_utils import get_pip_executable, get_python_executable


@dataclass
class PackageInfo:
    """Information about an installed package."""
    name: str
    version: str
    latest_version: str = ""
    summary: str = ""
    is_outdated: bool = False


class PipManager:
    """Manages pip/uv operations for a specific virtual environment."""

    def __init__(self, venv_path: Path, backend: str = "pip"):
        self.venv_path = venv_path
        self.pip_exe = get_pip_executable(venv_path)
        self.python_exe = get_python_executable(venv_path)
        self._ssl_available = None  # cached SSL check
        self._backend = backend  # "pip" or "uv"
        self._uv_exe = None  # cached uv path

    def _find_uv(self) -> Optional[str]:
        """Find uv executable — check venv, then system PATH."""
        if self._uv_exe is not None:
            return self._uv_exe if self._uv_exe else None
        import shutil
        # Check venv Scripts/bin first
        from src.utils.platform_utils import get_platform
        if get_platform() == "windows":
            venv_uv = self.venv_path / "Scripts" / "uv.exe"
        else:
            venv_uv = self.venv_path / "bin" / "uv"
        if venv_uv.exists():
            self._uv_exe = str(venv_uv)
            return self._uv_exe
        # Then system PATH
        found = shutil.which("uv")
        if found:
            self._uv_exe = found
            return self._uv_exe
        self._uv_exe = ""
        return None

    def _ensure_uv(self, callback=None) -> bool:
        """Ensure uv is available, install globally if not."""
        if self._find_uv():
            return True
        # Try to install uv via pip (into venv)
        try:
            if callback:
                callback("Installing uv (one-time setup)...")
            from src.utils.platform_utils import subprocess_args
            result = subprocess.run(
                [str(self.python_exe), "-m", "pip", "install", "uv"],
                **subprocess_args(capture_output=True, text=True, timeout=120)
            )
            if result.returncode == 0:
                self._uv_exe = None  # reset cache
                return self._find_uv() is not None
        except Exception:
            pass
        return False

    @property
    def backend(self) -> str:
        return self._backend

    @backend.setter
    def backend(self, value: str):
        self._backend = value if value in ("pip", "uv") else "pip"

    def _check_ssl(self) -> bool:
        """Check if SSL is available in this environment's Python."""
        if self._ssl_available is not None:
            return self._ssl_available
        try:
            from src.utils.platform_utils import subprocess_args
            result = subprocess.run(
                [str(self.python_exe), "-c", "import ssl; print('OK')"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            self._ssl_available = result.returncode == 0 and "OK" in result.stdout
        except Exception:
            self._ssl_available = False
        return self._ssl_available

    def _run_pip(self, args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        """Run a pip/uv command and return the result."""
        from src.utils.platform_utils import subprocess_args

        # Use uv if selected and available
        if self._backend == "uv" and self._find_uv():
            uv_exe = self._find_uv()
            # uv pip install/list/uninstall/freeze — same interface
            cmd = [uv_exe, "pip"] + args + ["--python", str(self.python_exe)]
        else:
            cmd = [str(self.python_exe), "-m", "pip"] + args

            # SSL yoksa --trusted-host ekle (only for pip, uv handles this)
            if not self._check_ssl():
                if args and args[0] in ("install", "download", "search"):
                    cmd.extend([
                        "--trusted-host", "pypi.org",
                        "--trusted-host", "pypi.python.org",
                        "--trusted-host", "files.pythonhosted.org",
                    ])
                elif len(args) >= 2 and args[0] == "list" and "--outdated" in args:
                    cmd.extend([
                        "--trusted-host", "pypi.org",
                        "--trusted-host", "pypi.python.org",
                        "--trusted-host", "files.pythonhosted.org",
                    ])

        return subprocess.run(
            cmd,
            **subprocess_args(
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        )

    def list_packages(self) -> List[PackageInfo]:
        """List all installed packages."""
        try:
            result = self._run_pip(["list", "--format=json"])
            if result.returncode == 0:
                raw = json.loads(result.stdout)
                return [
                    PackageInfo(name=p["name"], version=p["version"])
                    for p in raw
                ]
        except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception):
            pass
        return []

    def list_outdated(self) -> List[PackageInfo]:
        """List outdated packages."""
        try:
            result = self._run_pip(["list", "--outdated", "--format=json"], timeout=60)
            if result.returncode == 0:
                raw = json.loads(result.stdout)
                return [
                    PackageInfo(
                        name=p["name"],
                        version=p["version"],
                        latest_version=p.get("latest_version", ""),
                        is_outdated=True,
                    )
                    for p in raw
                ]
        except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception):
            pass
        return []

    def install_packages(
        self,
        packages: List[str],
        upgrade: bool = False,
        callback=None,
    ) -> Tuple[bool, str]:
        """
        Install one or more packages.
        Returns (success, output_message).
        """
        if not packages:
            return False, "No packages specified"

        # If uv backend selected, ensure it's available
        if self._backend == "uv":
            if not self._ensure_uv(callback):
                if callback:
                    callback("uv not available, falling back to pip...")
                self._backend = "pip"  # temporary fallback

        cmd = ["install"]
        if upgrade:
            cmd.append("--upgrade")
        cmd.extend(packages)

        try:
            if callback:
                callback(f"Installing: {', '.join(packages)}...")

            result = self._run_pip(cmd, timeout=300)

            output = result.stdout + result.stderr

            # SSL hatası varsa --trusted-host ile tekrar dene
            if result.returncode != 0 and ("SSL" in output or "ssl" in output or "CERTIFICATE" in output):
                if callback:
                    callback("SSL error detected, retrying with --trusted-host...")
                retry_cmd = cmd + [
                    "--trusted-host", "pypi.org",
                    "--trusted-host", "pypi.python.org",
                    "--trusted-host", "files.pythonhosted.org",
                ]
                result = self._run_pip(retry_cmd, timeout=300)
                output = result.stdout + result.stderr

            if result.returncode == 0:
                return True, output
            else:
                # "Package Not Found" tespiti
                if "No matching distribution" in output or "Could not find" in output:
                    return False, (
                        "One or more packages could not be found on PyPI.\n\n"
                        "Please check the package names and try again.\n"
                        "You can search at: https://pypi.org"
                    )
                return False, f"Installation failed:\n{output}"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out (300s)"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def uninstall_packages(
        self,
        packages: List[str],
        callback=None,
    ) -> Tuple[bool, str]:
        """Uninstall one or more packages."""
        if not packages:
            return False, "No packages specified"

        cmd = ["uninstall", "-y"] + packages

        try:
            if callback:
                callback(f"Uninstalling: {', '.join(packages)}...")

            result = self._run_pip(cmd, timeout=60)
            output = result.stdout + result.stderr

            if result.returncode == 0:
                return True, output
            else:
                return False, f"Uninstall failed:\n{output}"

        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def freeze(self) -> str:
        """Get pip freeze output (requirements.txt format)."""
        try:
            result = self._run_pip(["freeze"])
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, Exception):
            pass
        return ""

    def export_requirements(self, filepath: Path) -> Tuple[bool, str]:
        """Export installed packages to a requirements.txt file."""
        content = self.freeze()
        if not content:
            return False, "No packages to export"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Requirements exported to {filepath}"
        except IOError as e:
            return False, f"Error exporting: {str(e)}"

    def import_requirements(self, filepath: Path, callback=None) -> Tuple[bool, str]:
        """Install packages from a requirements.txt file."""
        if not filepath.exists():
            return False, f"File not found: {filepath}"

        try:
            if callback:
                callback(f"Installing from {filepath.name}...")

            result = self._run_pip(
                ["install", "-r", str(filepath)],
                timeout=600,
            )
            output = result.stdout + result.stderr

            if result.returncode == 0:
                return True, output
            else:
                return False, f"Some installations failed:\n{output}"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out (600s)"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def search_pypi(self, query: str) -> str:
        """
        Search PyPI for packages (pip search is deprecated, so we provide
        a message directing users to pypi.org).
        """
        return f"Visit https://pypi.org/search/?q={query} to search for packages"

    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """Get detailed info about an installed package."""
        try:
            result = self._run_pip(["show", package_name])
            if result.returncode == 0:
                info = {}
                for line in result.stdout.splitlines():
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        info[key.strip()] = value.strip()
                return info
        except (subprocess.TimeoutExpired, Exception):
            pass
        return None
