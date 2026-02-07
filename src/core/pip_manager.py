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
    """Manages pip operations for a specific virtual environment."""

    def __init__(self, venv_path: Path):
        self.venv_path = venv_path
        self.pip_exe = get_pip_executable(venv_path)
        self.python_exe = get_python_executable(venv_path)

    def _run_pip(self, args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
        """Run a pip command and return the result."""
        cmd = [str(self.python_exe), "-m", "pip"] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
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

        cmd = ["install"]
        if upgrade:
            cmd.append("--upgrade")
        cmd.extend(packages)

        try:
            if callback:
                callback(f"Installing: {', '.join(packages)}...")

            result = self._run_pip(cmd, timeout=300)

            output = result.stdout + result.stderr
            if result.returncode == 0:
                return True, output
            else:
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
