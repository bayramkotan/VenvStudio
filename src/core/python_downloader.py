"""
VenvStudio - Python Downloader
Downloads standalone Python builds for local use.

Supports multiple mirrors with automatic fallback:
  - Astral (python-build-standalone via GitHub Releases)   — default
  - python.org                                             — official CPython source tarballs
  - GitHub Releases (direct)                               — same as Astral, user-friendly URL
  - SourceForge mirror                                     — faster in some regions
  - Custom URL                                             — user-defined

Each mirror backend implements:
  - name
  - list_versions(callback) -> list[dict]
  - The dicts include a 'url' that download_python() can fetch from.

Users select a preferred mirror in Settings. If it fails, the downloader
automatically tries the next mirror (configurable).
"""

import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import tarfile
import zipfile
import tempfile
from pathlib import Path
from typing import Callable, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

from src.utils.platform_utils import get_config_dir, get_platform, subprocess_args

# SSL context — AppImage/EXE'de sertifika sorunlarını önler
_SSL_CTX = ssl.create_default_context()

# ───────────────────────────────────────────────────────────────────────────
# Mirror registry — users pick one in Settings, we fall back to others on error.
# ───────────────────────────────────────────────────────────────────────────

MIRROR_ASTRAL = "astral"
MIRROR_PYTHON_ORG = "python_org"
MIRROR_GITHUB = "github"
MIRROR_SOURCEFORGE = "sourceforge"
MIRROR_CUSTOM = "custom"

# Default fallback chain (tried in order)
DEFAULT_MIRROR_CHAIN = [MIRROR_ASTRAL, MIRROR_GITHUB, MIRROR_PYTHON_ORG]

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


# ═══════════════════════════════════════════════════════════════════════════
#  MIRROR BACKENDS
# ═══════════════════════════════════════════════════════════════════════════

class MirrorBackend:
    """Base class for a Python distribution mirror."""

    id: str = ""
    display_name: str = ""
    description: str = ""

    def list_versions(self, progress_callback: Optional[Callable[[str], None]] = None) -> list:
        """Return a list of available version dicts.

        Each dict must contain at least:
            - version     (str, e.g. '3.13.12')
            - filename    (str, archive name for extraction)
            - url         (str, direct download URL)
            - size        (int, bytes — may be 0 if unknown)
            - mirror      (str, backend id)
            - release_tag (str, optional — for display)
        """
        raise NotImplementedError


# ── Astral (python-build-standalone) via GitHub API ────────────────────────

class AstralBackend(MirrorBackend):
    """Default backend — Astral's python-build-standalone releases.
    Pros: pre-built, includes pip/ssl, runs without system deps.
    Cons: needs GitHub API access (may hit rate limits).
    """
    id = MIRROR_ASTRAL
    display_name = "Astral (python-build-standalone)"
    description = "Pre-built, portable Pythons (recommended). GitHub API."

    API_URL = "https://api.github.com/repos/astral-sh/python-build-standalone/releases"

    def list_versions(self, progress_callback=None) -> list:
        if progress_callback:
            progress_callback(f"Fetching versions from Astral...")

        target = get_target_triple()
        versions: list = []

        try:
            req = Request(
                f"{self.API_URL}?per_page=5",
                headers={"User-Agent": "VenvStudio"}
            )
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                releases = json.loads(resp.read().decode())

            for release in releases:
                tag = release["tag_name"]
                for asset in release.get("assets", []):
                    name = asset["name"]
                    if (target in name
                            and "install_only" in name
                            and "stripped" not in name
                            and not name.endswith(".sha256")
                            and "freethreaded" not in name):
                        try:
                            ver_part = name.split("-")[1]       # "3.13.12+20260203"
                            version = ver_part.split("+")[0]     # "3.13.12"
                            if any(c in version for c in ("a", "b", "rc")):
                                continue
                            versions.append({
                                "version": version,
                                "release_tag": tag,
                                "filename": name,
                                "url": asset["browser_download_url"],
                                "size": asset.get("size", 0),
                                "mirror": self.id,
                            })
                        except (IndexError, ValueError):
                            continue
        except (URLError, json.JSONDecodeError, KeyError) as e:
            if progress_callback:
                progress_callback(f"Astral fetch failed: {e}")
            return []

        versions.sort(
            key=lambda v: tuple(int(x) for x in v["version"].split(".")),
            reverse=True,
        )
        seen: set = set()
        unique: list = []
        for v in versions:
            if v["version"] not in seen:
                seen.add(v["version"])
                unique.append(v)
        return unique


# ── GitHub Releases (direct) — same data as Astral, different navigation ──

class GitHubBackend(AstralBackend):
    """Direct GitHub Releases browser — essentially identical to Astral
    but exposed as a separate choice for users who want to go directly.
    """
    id = MIRROR_GITHUB
    display_name = "GitHub Releases (astral-sh)"
    description = "Same as Astral but labelled separately. Good if Astral blocked."


# ── python.org (official CPython source tarballs) ─────────────────────────

class PythonOrgBackend(MirrorBackend):
    """Official python.org source distribution.
    Pros: canonical source, always available.
    Cons: source only — must be compiled by the user (not portable).
            For Windows: ships an .msi installer per version.
    """
    id = MIRROR_PYTHON_ORG
    display_name = "python.org (official)"
    description = "Official python.org. Source tarballs (Linux/macOS) or MSI (Windows)."

    INDEX_URL = "https://www.python.org/ftp/python/"

    def list_versions(self, progress_callback=None) -> list:
        if progress_callback:
            progress_callback("Fetching versions from python.org...")

        system = get_platform()
        versions: list = []

        try:
            req = Request(self.INDEX_URL, headers={"User-Agent": "VenvStudio"})
            with urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract version dirs like "3.13.12/"
            ver_re = re.compile(r'href="(\d+\.\d+\.\d+)/"')
            all_versions = sorted(
                set(ver_re.findall(html)),
                key=lambda v: tuple(int(x) for x in v.split(".")),
                reverse=True,
            )
            # Limit to recent 10 to avoid overwhelming the UI
            all_versions = all_versions[:10]

            machine = platform.machine().lower()
            for version in all_versions:
                if system == "windows":
                    # e.g. https://www.python.org/ftp/python/3.13.12/python-3.13.12-amd64.exe
                    if machine in ("amd64", "x86_64"):
                        filename = f"python-{version}-amd64.exe"
                    elif machine in ("arm64", "aarch64"):
                        filename = f"python-{version}-arm64.exe"
                    else:
                        filename = f"python-{version}.exe"
                    url = f"{self.INDEX_URL}{version}/{filename}"
                else:
                    # Source tarball (user must compile)
                    filename = f"Python-{version}.tgz"
                    url = f"{self.INDEX_URL}{version}/{filename}"

                versions.append({
                    "version": version,
                    "release_tag": "official",
                    "filename": filename,
                    "url": url,
                    "size": 0,  # python.org HTML listing doesn't expose sizes easily
                    "mirror": self.id,
                })

        except (URLError, Exception) as e:
            if progress_callback:
                progress_callback(f"python.org fetch failed: {e}")
            return []

        return versions


# ── SourceForge mirror — fallback for blocked regions ─────────────────────

class SourceForgeBackend(MirrorBackend):
    """SourceForge mirror for python-build-standalone.
    Pros: faster in some regions, no GitHub API rate limits.
    Cons: community mirror (may be outdated). Best-effort.
    """
    id = MIRROR_SOURCEFORGE
    display_name = "SourceForge (community mirror)"
    description = "Community mirror of python-build-standalone. May be outdated."

    # Community mirrors are generally not reliable. We expose this as a hint
    # that users can add a manual URL later.
    def list_versions(self, progress_callback=None) -> list:
        if progress_callback:
            progress_callback(
                "SourceForge mirror not automatically indexed. "
                "Use Custom URL instead."
            )
        return []


# ── Custom URL — user provides their own download URL ─────────────────────

class CustomUrlBackend(MirrorBackend):
    """User-provided URL for a Python distribution.
    Users paste a direct URL (tar.gz, zip, tar.zst). We treat it as a
    single-version backend — no listing, just the URL.
    """
    id = MIRROR_CUSTOM
    display_name = "Custom URL"
    description = "Paste a direct download URL (tar.gz, zip, tar.zst, exe)."

    def __init__(self, url: str = "", version: str = "custom"):
        self.url = url
        self.version = version

    def list_versions(self, progress_callback=None) -> list:
        if not self.url:
            if progress_callback:
                progress_callback("No custom URL configured.")
            return []

        # Infer filename and version from URL
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        filename = os.path.basename(parsed.path) or "python-custom.tar.gz"

        # Try to infer version from filename (e.g. cpython-3.13.12-...)
        m = re.search(r"(\d+\.\d+\.\d+)", filename)
        version = m.group(1) if m else self.version

        return [{
            "version": version,
            "release_tag": "custom",
            "filename": filename,
            "url": self.url,
            "size": 0,
            "mirror": self.id,
        }]


# ───────────────────────────────────────────────────────────────────────────

_BACKENDS = {
    MIRROR_ASTRAL: AstralBackend,
    MIRROR_GITHUB: GitHubBackend,
    MIRROR_PYTHON_ORG: PythonOrgBackend,
    MIRROR_SOURCEFORGE: SourceForgeBackend,
    MIRROR_CUSTOM: CustomUrlBackend,
}


def get_all_mirror_infos() -> List[dict]:
    """Return metadata for all mirrors — for Settings dropdowns."""
    return [
        {"id": cls.id, "name": cls.display_name, "description": cls.description}
        for cls in _BACKENDS.values()
    ]


def _get_backend(mirror_id: str, **kwargs) -> MirrorBackend:
    """Instantiate a backend by id."""
    cls = _BACKENDS.get(mirror_id, AstralBackend)
    if cls is CustomUrlBackend:
        return cls(url=kwargs.get("custom_url", ""))
    return cls()


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def get_available_versions(
    progress_callback=None,
    mirror: str = MIRROR_ASTRAL,
    custom_url: str = "",
    try_fallbacks: bool = True,
) -> list:
    """
    Fetch available Python versions from the selected mirror.

    If the primary mirror returns no results AND try_fallbacks=True, the
    remaining default-chain mirrors are tried in order.

    Args:
        mirror: primary mirror id (see MIRROR_* constants)
        custom_url: used when mirror == MIRROR_CUSTOM
        try_fallbacks: if True, try other mirrors on failure

    Returns:
        list of version dicts (may be empty if all mirrors fail)
    """
    tried: list = []
    chain = [mirror]
    if try_fallbacks and mirror != MIRROR_CUSTOM:
        for m in DEFAULT_MIRROR_CHAIN:
            if m != mirror and m not in chain:
                chain.append(m)

    for mirror_id in chain:
        backend = _get_backend(mirror_id, custom_url=custom_url)
        tried.append(backend.display_name)
        versions = backend.list_versions(progress_callback=progress_callback)
        if versions:
            if progress_callback and len(tried) > 1:
                progress_callback(f"✅ Using {backend.display_name}")
            return versions

    if progress_callback:
        progress_callback(f"❌ All mirrors failed: {', '.join(tried)}")
    return []


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
        if get_platform() == "windows":
            exe = entry / "python" / "python.exe"
            if not exe.exists():
                exe = entry / "python.exe"
        else:
            exe = entry / "python" / "bin" / "python3"
            if not exe.exists():
                exe = entry / "bin" / "python3"

        if exe.exists():
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
    mirror_id = version_info.get("mirror", "unknown")

    install_dir = get_pythons_dir() / f"cpython-{version}"

    # Only short-circuit if the directory has a working python — earlier
    # broken downloads (e.g. an MSI/EXE that we no longer support, or a
    # partial extract) would leave the directory in place and previously
    # caused "already installed" to lie about the install state.
    if install_dir.exists():
        existing_exe = get_python_exe(install_dir)
        if existing_exe and existing_exe.exists():
            if progress_callback:
                progress_callback(f"Python {version} already installed at {install_dir}")
            return install_dir
        # Stale/broken install — wipe so the fresh download can write here.
        if progress_callback:
            progress_callback(f"Removing stale install at {install_dir}...")
        shutil.rmtree(str(install_dir), ignore_errors=True)

    if progress_callback:
        size_mb = total_size / (1024 * 1024) if total_size else 0
        size_str = f"{size_mb:.0f} MB" if size_mb else "size unknown"
        progress_callback(f"Downloading Python {version} ({size_str}) from {mirror_id}...")

    tmp_dir = tempfile.mkdtemp(prefix="venvstudio_py_")
    tmp_file = os.path.join(tmp_dir, filename)

    try:
        req = Request(url, headers={"User-Agent": "VenvStudio"})
        with urlopen(req, timeout=300, context=_SSL_CTX) as resp:
            # python.org doesn't report Content-Length reliably; try header
            if not total_size:
                try:
                    total_size = int(resp.headers.get("Content-Length", 0))
                except Exception:
                    total_size = 0

            downloaded = 0
            chunk_size = 1024 * 256
            with open(tmp_file, 'wb') as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        mb = downloaded / (1024 * 1024)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            total_mb = total_size / (1024 * 1024)
                            progress_callback(
                                f"Downloading Python {version}: {mb:.1f}/{total_mb:.0f} MB ({pct:.0f}%)"
                            )
                        else:
                            progress_callback(f"Downloading Python {version}: {mb:.1f} MB…")

        if progress_callback:
            progress_callback(f"Extracting Python {version}...")

        install_dir.mkdir(parents=True, exist_ok=True)

        fn_lower = filename.lower()
        if fn_lower.endswith((".tar.gz", ".tgz")):
            with tarfile.open(tmp_file, "r:gz") as tar:
                tar.extractall(path=str(install_dir))
        elif fn_lower.endswith(".tar.zst"):
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
                result = subprocess.run(
                    ["tar", "-xf", tmp_file, "-C", str(install_dir)],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Cannot extract .tar.zst: install 'zstandard' package "
                        f"or ensure 'tar' supports zstd.\n{result.stderr}"
                    )
        elif fn_lower.endswith(".zip"):
            with zipfile.ZipFile(tmp_file, 'r') as z:
                z.extractall(str(install_dir))
        elif fn_lower.endswith(".msi"):
            # python.org Windows MSI — silent per-user install into our
            # install_dir. Uses msiexec quiet mode (/qn) with TargetDir +
            # user-mode properties so no UAC prompt is shown.
            #
            # MSI properties (python.org installer):
            #   TargetDir        — where to install
            #   InstallAllUsers  — 0 = per-user (no UAC)
            #   Include_launcher — 0 = skip global py.exe (no UAC)
            #   PrependPath      — 0 = don't touch %PATH%
            #   Shortcuts        — 0 = no Start Menu entries
            #   Include_test     — 0 = skip test suite (smaller)
            if progress_callback:
                progress_callback(f"Installing Python {version} silently...")
            msi_log = install_dir / "install.log"
            msi_args = [
                "msiexec", "/i", tmp_file,
                "/qn", "/norestart",
                f"TargetDir={install_dir}",
                "InstallAllUsers=0",
                "Include_launcher=0",
                "PrependPath=0",
                "Shortcuts=0",
                "Include_test=0",
                "/L*v", str(msi_log),
            ]
            result = subprocess.run(
                msi_args,
                capture_output=True, text=True, timeout=600,
                **subprocess_args()
            )
            if result.returncode != 0:
                # MSI exit 1602 = user cancel, 1603 = fatal; surface the log path.
                raise RuntimeError(
                    f"MSI install failed (exit={result.returncode}). "
                    f"See log: {msi_log}\n{result.stderr or result.stdout}"
                )
        elif fn_lower.endswith(".exe"):
            # python.org Windows EXE installer — same silent flags as MSI,
            # passed through the EXE's command line.
            if progress_callback:
                progress_callback(f"Installing Python {version} silently...")
            exe_args = [
                tmp_file,
                "/quiet",
                f"TargetDir={install_dir}",
                "InstallAllUsers=0",
                "Include_launcher=0",
                "PrependPath=0",
                "Shortcuts=0",
                "Include_test=0",
            ]
            result = subprocess.run(
                exe_args,
                capture_output=True, text=True, timeout=600,
                **subprocess_args()
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Installer failed (exit={result.returncode}).\n"
                    f"{result.stderr or result.stdout}"
                )
        else:
            raise RuntimeError(f"Unknown archive format: {filename}")

        if progress_callback:
            progress_callback(f"Setting up pip for Python {version}...")

        exe = get_python_exe(install_dir)
        if exe and exe.exists():
            try:
                subprocess.run(
                    [str(exe), "-m", "ensurepip", "--upgrade"],
                    capture_output=True, text=True, timeout=60,
                )
                subprocess.run(
                    [str(exe), "-m", "pip", "install", "--upgrade", "pip"],
                    capture_output=True, text=True, timeout=60,
                )
            except Exception:
                pass

        if progress_callback:
            progress_callback(f"✅ Python {version} installed successfully!")

        return install_dir

    except Exception as e:
        if install_dir.exists():
            shutil.rmtree(str(install_dir), ignore_errors=True)
        raise RuntimeError(f"Download failed from {mirror_id}: {e}")

    finally:
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
