"""
VenvStudio - Python Downloader
Downloads standalone Python builds from astral-sh/python-build-standalone.
These are the same builds used by uv.
"""

import json
import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from src.utils.platform_utils import get_config_dir, get_platform, subprocess_args

# GitHub API for python-build-standalone releases
GITHUB_API = "https://api.github.com/repos/astral-sh/python-build-standalone/releases"
GITHUB_RELEASES = "https://github.com/astral-sh/python-build-standalone/releases/download"

# Where downloaded Pythons live
PYTHONS_DIR = get_config_dir().parent / "VenvStudio" / "pythons"


def get_pythons_dir() -> Path:
    """Return the directory where standalone Pythons are stored."""
    PYTHONS_DIR.mkdir(parents=True, exist_ok=True)
    return PYTHONS_DIR


def get_target_triple() -> str:
    """Return the target triple for the current platform."""
    system = get_platform()
    machine = platform.machine().lower()

    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "x86_64-pc-windows-msvc"
        elif machine in ("arm64", "aarch64"):
            return "aarch64-pc-windows-msvc"
    elif system == "macos":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    else:  # linux
        if machine in ("x86_64", "amd64"):
            return "x86_64-unknown-linux-gnu"
        elif machine in ("aarch64", "arm64"):
            return "aarch64-unknown-linux-gnu"

    return f"{machine}-unknown-{system}"


def get_available_versions(progress_callback=None) -> list:
    """
    Fetch available Python versions from GitHub releases.
    Returns list of dicts: [{"version": "3.13.12", "release_tag": "20260203", "url": "...", "size": ...}, ...]
    """
    if progress_callback:
        progress_callback("Fetching available Python versions...")

    target = get_target_triple()
    versions = []

    try:
        # Get latest releases from GitHub API
        req = Request(
            f"{GITHUB_API}?per_page=5",
            headers={"User-Agent": "VenvStudio"}
        )
        with urlopen(req, timeout=30) as resp:
            releases = json.loads(resp.read().decode())

        for release in releases:
            tag = release["tag_name"]
            for asset in release.get("assets", []):
                name = asset["name"]
                # We want: cpython-X.Y.Z+TAG-TRIPLE-install_only.tar.gz
                # or:      cpython-X.Y.Z+TAG-TRIPLE-install_only_stripped.tar.gz
                if (target in name
                        and "install_only" in name
                        and "stripped" not in name
                        and not name.endswith(".sha256")
                        and "freethreaded" not in name):
                    # Extract version from filename
                    # e.g. cpython-3.13.12+20260203-x86_64-pc-windows-msvc-install_only.tar.gz
                    try:
                        ver_part = name.split("-")[1]  # "3.13.12+20260203"
                        version = ver_part.split("+")[0]  # "3.13.12"

                        # Skip alpha/beta unless explicitly wanted
                        if "a" in version or "b" in version or "rc" in version:
                            continue

                        versions.append({
                            "version": version,
                            "release_tag": tag,
                            "filename": name,
                            "url": asset["browser_download_url"],
                            "size": asset.get("size", 0),
                        })
                    except (IndexError, ValueError):
                        continue

    except (URLError, json.JSONDecodeError, KeyError) as e:
        if progress_callback:
            progress_callback(f"Error fetching versions: {e}")
        return []

    # Sort by version descending
    versions.sort(key=lambda v: tuple(int(x) for x in v["version"].split(".")), reverse=True)

    # Deduplicate (keep latest release tag for each version)
    seen = set()
    unique = []
    for v in versions:
        if v["version"] not in seen:
            seen.add(v["version"])
            unique.append(v)

    return unique


def get_installed_pythons() -> list:
    """
    List locally installed standalone Pythons.
    Returns list of dicts: [{"version": "3.13.12", "path": Path, "python_exe": Path}, ...]
    """
    pythons_dir = get_pythons_dir()
    installed = []

    for entry in sorted(pythons_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Look for python executable
        if get_platform() == "windows":
            exe = entry / "python" / "python.exe"
            if not exe.exists():
                exe = entry / "python.exe"
        else:
            exe = entry / "python" / "bin" / "python3"
            if not exe.exists():
                exe = entry / "bin" / "python3"

        if exe.exists():
            # Try to get version
            try:
                result = subprocess.run(
                    [str(exe), "--version"],
                    capture_output=True, text=True, timeout=10,
                    **subprocess_args()
                )
                ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                ver = entry.name

            installed.append({
                "version": ver,
                "path": entry,
                "python_exe": exe,
            })

    return installed


def download_python(version_info: dict, progress_callback=None) -> Path:
    """
    Download and extract a standalone Python build.
    version_info: dict from get_available_versions()
    Returns: Path to the installed Python directory.
    """
    url = version_info["url"]
    version = version_info["version"]
    filename = version_info["filename"]
    total_size = version_info.get("size", 0)

    install_dir = get_pythons_dir() / f"cpython-{version}"

    if install_dir.exists():
        if progress_callback:
            progress_callback(f"Python {version} already installed at {install_dir}")
        return install_dir

    if progress_callback:
        size_mb = total_size / (1024 * 1024) if total_size else 0
        progress_callback(f"Downloading Python {version} ({size_mb:.0f} MB)...")

    # Download to temp file
    tmp_dir = tempfile.mkdtemp(prefix="venvstudio_py_")
    tmp_file = os.path.join(tmp_dir, filename)

    try:
        req = Request(url, headers={"User-Agent": "VenvStudio"})
        with urlopen(req, timeout=300) as resp:
            downloaded = 0
            chunk_size = 1024 * 256  # 256KB chunks
            with open(tmp_file, 'wb') as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        pct = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        progress_callback(
                            f"Downloading Python {version}: {mb:.1f}/{total_mb:.0f} MB ({pct:.0f}%)"
                        )

        if progress_callback:
            progress_callback(f"Extracting Python {version}...")

        # Extract
        install_dir.mkdir(parents=True, exist_ok=True)

        if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            with tarfile.open(tmp_file, "r:gz") as tar:
                tar.extractall(path=str(install_dir))
        elif filename.endswith(".tar.zst"):
            # Need zstandard for .zst
            try:
                import zstandard
                with open(tmp_file, 'rb') as compressed:
                    dctx = zstandard.ZstdDecompressor()
                    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp_tar:
                        dctx.copy_stream(compressed, tmp_tar)
                        tmp_tar_path = tmp_tar.name
                with tarfile.open(tmp_tar_path) as tar:
                    tar.extractall(path=str(install_dir))
                os.unlink(tmp_tar_path)
            except ImportError:
                # Fallback: use tar command if available
                result = subprocess.run(
                    ["tar", "-xf", tmp_file, "-C", str(install_dir)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Cannot extract .tar.zst: install 'zstandard' package "
                        f"or ensure 'tar' supports zstd.\n{result.stderr}"
                    )
        elif filename.endswith(".zip"):
            with zipfile.ZipFile(tmp_file, 'r') as z:
                z.extractall(str(install_dir))
        else:
            raise RuntimeError(f"Unknown archive format: {filename}")

        if progress_callback:
            progress_callback(f"✅ Python {version} installed successfully!")

        return install_dir

    except Exception as e:
        # Clean up on failure
        if install_dir.exists():
            shutil.rmtree(str(install_dir), ignore_errors=True)
        raise RuntimeError(f"Download failed: {e}")

    finally:
        # Clean up temp
        shutil.rmtree(tmp_dir, ignore_errors=True)


def remove_python(version_dir: Path, progress_callback=None) -> bool:
    """Remove an installed standalone Python."""
    if not version_dir.exists():
        return False

    if progress_callback:
        progress_callback(f"Removing {version_dir.name}...")

    try:
        shutil.rmtree(str(version_dir))
        if progress_callback:
            progress_callback(f"✅ Removed {version_dir.name}")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Failed to remove: {e}")
        return False


def get_python_exe(install_dir: Path) -> Path | None:
    """Find the python executable in a standalone install."""
    if get_platform() == "windows":
        candidates = [
            install_dir / "python" / "python.exe",
            install_dir / "python.exe",
        ]
    else:
        candidates = [
            install_dir / "python" / "bin" / "python3",
            install_dir / "python" / "bin" / "python",
            install_dir / "bin" / "python3",
            install_dir / "bin" / "python",
        ]

    for c in candidates:
        if c.exists():
            return c
    return None
