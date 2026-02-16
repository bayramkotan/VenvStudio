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

from src.utils.platform_utils import subprocess_args

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

        # Ensure base directory exists
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Cannot create directory '{self.base_dir}': {e}"

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
                **subprocess_args(capture_output=True, text=True, timeout=120)
                )

            if result.returncode != 0:
                # Clean up on failure
                if venv_path.exists():
                    shutil.rmtree(venv_path, ignore_errors=True)
                return False, f"Failed to create environment:\n{result.stderr}"

            # Upgrade pip if requested
            pip_exe = get_pip_executable(venv_path)
            python_in_venv = get_python_executable(venv_path)
            if with_pip and pip_exe.exists():
                if callback:
                    callback("Upgrading pip...")
                # SSL olmayabilir — trusted-host ekle
                pip_upgrade_cmd = [
                    str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip",
                    "--trusted-host", "pypi.org",
                    "--trusted-host", "pypi.python.org",
                    "--trusted-host", "files.pythonhosted.org",
                ]
                subprocess.run(
                    pip_upgrade_cmd,
                    **subprocess_args(capture_output=True, text=True, timeout=60)
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

    def delete_venv(self, name: str, callback=None) -> tuple[bool, str]:
        """Delete a virtual environment."""
        venv_path = self.base_dir / name

        if not venv_path.exists():
            return False, f"Environment '{name}' not found"

        try:
            if callback:
                callback(f"Deleting '{name}'...")
            shutil.rmtree(venv_path)
            return True, f"Environment '{name}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting environment: {str(e)}"

    def list_venvs_fast(self) -> List[VenvInfo]:
        """Fast list - only check directory names and validity, no subprocess calls."""
        venvs = []
        if not self.base_dir.exists():
            return venvs

        for item in sorted(self.base_dir.iterdir()):
            if item.is_dir():
                python_exe = get_python_executable(item)
                is_valid = python_exe.exists()

                info = VenvInfo(
                    name=item.name,
                    path=item,
                    is_valid=is_valid,
                    python_version="..." if is_valid else "N/A",
                    size="...",
                    package_count=0,
                )

                # Creation date (no subprocess needed)
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
                        stat = item.stat()
                        info.created = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    except OSError:
                        pass

                venvs.append(info)

        return venvs

    def list_venvs(self) -> List[VenvInfo]:
        """Full list with all details (slow - calls subprocess for each env)."""
        venvs = []

        if not self.base_dir.exists():
            return venvs

        for item in sorted(self.base_dir.iterdir()):
            if item.is_dir():
                info = self.get_venv_info(item.name)
                if info:
                    venvs.append(info)

        return venvs

    def get_venv_info(self, name: str) -> Optional[VenvInfo]:
        """Get detailed information about a virtual environment."""
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

        # Get Python version
        if is_valid:
            try:
                result = subprocess.run(
                    [str(python_exe), "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=5)
                )
                ver = result.stdout.strip() or result.stderr.strip()
                info.python_version = ver.replace("Python ", "")
            except (subprocess.TimeoutExpired, Exception):
                info.python_version = "Unknown"

        # Get size
        info.size = get_venv_size(venv_path)

        # Get creation date
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
                stat = venv_path.stat()
                info.created = datetime.fromtimestamp(stat.st_ctime).isoformat()
            except OSError:
                pass

        # Get package count
        if is_valid:
            pip_exe = get_pip_executable(venv_path)
            if pip_exe.exists():
                try:
                    result = subprocess.run(
                        [str(pip_exe), "list", "--format=json"],
                        **subprocess_args(capture_output=True, text=True, timeout=10)
                    )
                    if result.returncode == 0:
                        packages = json.loads(result.stdout)
                        info.package_count = len(packages)
                except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
                    pass

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
                **subprocess_args(capture_output=True, text=True, timeout=15)
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
                    [str(target_pip), "install", "--no-cache-dir", "-r", str(req_file)],
                    **subprocess_args(capture_output=True, text=True, timeout=300)
                )
                req_file.unlink(missing_ok=True)

                if result.returncode != 0:
                    return False, f"Created env but failed to install some packages:\n{result.stderr}"

            return True, f"Environment '{source_name}' cloned to '{target_name}' successfully"

        except Exception as e:
            return False, f"Error cloning environment: {str(e)}"

    def rename_venv(self, old_name: str, new_name: str, callback=None) -> tuple[bool, str]:
        """Rename environment via clone + delete for reliable pip support."""
        old_path = self.base_dir / old_name
        new_path = self.base_dir / new_name

        if not old_path.exists():
            return False, f"Environment '{old_name}' not found"
        if new_path.exists():
            return False, f"Environment '{new_name}' already exists"

        try:
            if callback:
                callback(f"Getting packages from '{old_name}'...")

            # 1. Freeze packages from old env
            pip_exe = get_pip_executable(old_path)
            requirements = ""
            if pip_exe.exists():
                result = subprocess.run(
                    [str(pip_exe), "freeze"],
                    **subprocess_args(capture_output=True, text=True, timeout=15)
                )
                requirements = result.stdout

            # 2. Create new env
            if callback:
                callback(f"Creating '{new_name}'...")
            success, msg = self.create_venv(new_name, callback=callback)
            if not success:
                return False, msg

            # 3. Install packages into new env
            if requirements.strip():
                req_file = new_path / "_rename_requirements.txt"
                with open(req_file, "w") as f:
                    f.write(requirements)

                target_pip = get_pip_executable(new_path)
                if callback:
                    callback(f"Installing packages into '{new_name}'...")

                result = subprocess.run(
                    [str(target_pip), "install", "-r", str(req_file)],
                    **subprocess_args(capture_output=True, text=True, timeout=300)
                )
                req_file.unlink(missing_ok=True)

                if result.returncode != 0:
                    # New env created but packages failed — keep both, warn user
                    return False, (
                        f"Created '{new_name}' but failed to install some packages.\n"
                        f"Original '{old_name}' preserved.\n{result.stderr[:300]}"
                    )

            # 4. Copy metadata
            old_meta = old_path / ".venvstudio_meta.json"
            new_meta = new_path / ".venvstudio_meta.json"
            if old_meta.exists():
                try:
                    with open(old_meta) as f:
                        meta = json.load(f)
                    meta["name"] = new_name
                    meta["renamed_from"] = old_name
                    with open(new_meta, "w") as f:
                        json.dump(meta, f, indent=2)
                except Exception:
                    pass

            # 5. Delete old env
            if callback:
                callback(f"Removing old '{old_name}'...")
            shutil.rmtree(old_path, ignore_errors=True)

            return True, f"Environment '{old_name}' renamed to '{new_name}'"

        except Exception as e:
            return False, f"Error renaming environment: {str(e)}"
