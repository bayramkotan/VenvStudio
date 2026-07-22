"""
micromamba installer + MicromambaEnv manager
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ─── micromamba binary management ────────────────────────────────────────────

# Where VenvStudio stores its own micromamba binary
def _get_micromamba_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA",
                    Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME",
                    Path.home() / ".local" / "share"))
    d = base / "VenvStudio" / "micromamba"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_micromamba_exe() -> Path | None:
    """Return path to micromamba binary if available (bundled or system)."""
    # 1. VenvStudio bundled
    bundled = _get_micromamba_dir() / (
        "micromamba.exe" if sys.platform == "win32" else "micromamba"
    )
    if bundled.exists():
        return bundled
    # 2. System PATH
    found = shutil.which("micromamba")
    return Path(found) if found else None


def download_micromamba(progress_cb=None) -> Path:
    """
    Download micromamba single binary into VenvStudio's data dir.
    Returns path to executable.
    """
    from src.utils.platform_utils import get_platform
    import ssl
    from urllib.request import urlopen, Request
    from urllib.error import URLError

    plat = get_platform()
    arch = platform.machine().lower()
    _SSL_CTX = ssl.create_default_context()

    # micromamba release assets use conda platform strings
    plat_map = {
        ("windows", "amd64"): "win-64",
        ("windows", "x86_64"): "win-64",
        ("windows", "arm64"): "win-arm64",
        ("linux", "x86_64"): "linux-64",
        ("linux", "amd64"): "linux-64",
        ("linux", "aarch64"): "linux-aarch64",
        ("linux", "arm64"): "linux-aarch64",
        ("macos", "x86_64"): "osx-64",
        ("macos", "arm64"): "osx-arm64",
        ("macos", "aarch64"): "osx-arm64",
    }
    conda_plat = plat_map.get((plat, arch), "linux-64")

    # Fetch latest release tag via GitHub API
    if progress_cb:
        progress_cb("Fetching latest micromamba version...")
    import json
    try:
        req = Request(
            "https://api.github.com/repos/mamba-org/micromamba-releases/releases/latest",
            headers={"User-Agent": "VenvStudio/1.0"}
        )
        with urlopen(req, timeout=15, context=_SSL_CTX) as r:
            data = json.loads(r.read())
        tag = data["tag_name"]  # e.g. "2.5.0-2"
    except Exception:
        tag = "2.5.0-2"  # fallback to known good version

    # Build download URL
    filename = f"micromamba-{conda_plat}"
    if plat == "windows":
        filename += ".exe"
    url = (
        f"https://github.com/mamba-org/micromamba-releases/releases/download"
        f"/{tag}/{filename}"
    )

    dest_dir = _get_micromamba_dir()
    dest = dest_dir / ("micromamba.exe" if plat == "windows" else "micromamba")

    if dest.exists():
        if progress_cb:
            progress_cb(f"micromamba already downloaded: {dest}")
        return dest

    if progress_cb:
        progress_cb(f"Downloading micromamba {tag} for {conda_plat}...")

    try:
        req = Request(url, headers={"User-Agent": "VenvStudio/1.0"})
        with urlopen(req, timeout=300, context=_SSL_CTX) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 256 * 1024
            with open(dest, "wb") as f:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if progress_cb and total:
                        pct = downloaded / total * 100
                        mb = downloaded / 1_048_576
                        total_mb = total / 1_048_576
                        progress_cb(
                            f"Downloading micromamba: {mb:.1f}/{total_mb:.0f} MB"
                            f" ({pct:.0f}%)"
                        )
        if plat != "windows":
            dest.chmod(0o755)
        if progress_cb:
            progress_cb(f"micromamba ready: {dest}")
        return dest
    except URLError as e:
        raise RuntimeError(f"Failed to download micromamba: {e}")


# ─── Conda env management ─────────────────────────────────────────────────────

_log = logging.getLogger("venvstudio.conda")


def _run_micromamba(args: list, progress_cb=None, timeout=600) -> subprocess.CompletedProcess:
    """Run micromamba with given args, streaming output to progress_cb."""
    exe = get_micromamba_exe()
    if not exe:
        raise RuntimeError(
            "micromamba not found. Call download_micromamba() first."
        )
    cmd = [str(exe)] + args
    if progress_cb:
        progress_cb(f"$ {' '.join(cmd[:6])}...")
    _log.debug(f"🚀 micromamba: {' '.join(cmd)}")

    # Stream output live so the UI shows progress during long installs.
    # subprocess.run(capture_output=True) blocked until completion, so a
    # 4-5 minute conda preset install looked frozen ("is it installing?").
    _env = {**os.environ, "MAMBA_NO_LOW_SPEED_LIMIT": "1"}
    _out_lines, _err_lines = [], []
    try:
        from src.utils.platform_utils import subprocess_args as _spa
        _kw = _spa()
    except Exception:
        _kw = {}
    _proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, env=_env, **_kw,
    )
    import time as _time
    _t0 = _time.time()
    try:
        for _line in _proc.stdout:
            _line = _line.rstrip()
            _out_lines.append(_line)
            if progress_cb and _line.strip():
                progress_cb(_line.strip()[:200])
            if _time.time() - _t0 > timeout:
                _proc.kill()
                raise subprocess.TimeoutExpired(cmd, timeout)
    finally:
        _proc.stdout.close()
        _rc = _proc.wait()
    result = subprocess.CompletedProcess(
        cmd, _rc, "\n".join(_out_lines), "\n".join(_out_lines),
    )
    if result.returncode == 0:
        _log.debug(f"  ↳ ✔ micromamba exit=0")
    else:
        # DEBUG here: a failed first attempt may be rescued by the mirror
        # fallback — create/install log a WARNING with full stderr only
        # when the operation FINALLY fails.
        _log.debug(
            f"  ↳ ✖ micromamba exit={result.returncode}\n"
            f"--- stderr ---\n{(result.stderr or '')[:1500]}"
        )
    # (output already streamed above — no tail replay needed)
    return result


_CONDA_FORGE_MIRROR = "https://repo.prefix.dev/conda-forge"


def _mirror_flag_path():
    """Marker file for the mirror preference.

    Deliberately NOT stored in config.json: these helpers run inside
    worker threads, and writing the shared config concurrently with the
    GUI thread risks corrupting it (suspected intermittent-crash source).
    A dedicated flag file has no such race.
    """
    from pathlib import Path
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"
    d = base / "VenvStudio"
    d.mkdir(parents=True, exist_ok=True)
    return d / "conda_use_mirror.flag"


def _mirror_preferred() -> bool:
    try:
        return _mirror_flag_path().exists()
    except Exception:
        return False


def _remember_mirror_works() -> None:
    try:
        fp = _mirror_flag_path()
        if not fp.exists():
            fp.write_text("prefix.dev conda-forge mirror preferred\n",
                          encoding="utf-8")
            _log.info("🌐 [Conda] prefix.dev mirror works on this "
                      "network — saved as preferred channel host")
    except Exception:
        pass



def _is_mirror_data_error(err: str) -> bool:
    """Mirror served unusable metadata (not a network problem).

    Seen on repo.prefix.dev: "Shard package record for 'libgrpc' is missing
    both md5 and sha256 checksums" — the solver gives up even though the
    same package resolves fine on the canonical conda-forge CDN.
    """
    e = err.lower()
    return ("missing both md5 and sha256" in e
            or "failed to parse package record" in e
            or "shard package record" in e)


def _is_network_error(err: str) -> bool:
    e = err.lower()
    return any(s in e for s in (
        "ssl connect error", "connection was reset", "download error",
        "could not resolve host", "connection timed out", "recv failure",
    ))


def _mirror_channels(channels):
    """Swap conda-forge for its prefix.dev mirror (IDENTICAL content).

    Unlike the removed "defaults" fallback this is safe: same channel,
    same packages — only the CDN hostname changes. Needed because some
    networks reset TLS to conda.anaconda.org while the mirror is fine.
    """
    return [_CONDA_FORGE_MIRROR if c == "conda-forge" else c for c in channels]


def _friendly_conda_error(err: str) -> str:
    """Turn known micromamba failures into actionable messages."""
    if "being used by another process" in err or "file in use" in err.lower():
        return (
            "A file inside the environment is locked by another process.\n"
            "Close any terminals opened for this environment (and any running "
            "Python/Jupyter from it), then retry.\n\n--- details ---\n" + err[:400]
        )
    return err[:500]


def create_conda_env(env_path: Path, python_version: str = "",
                     packages: list | None = None,
                     channels: list | None = None,
                     progress_cb=None) -> bool:
    """
    Create a conda environment at env_path using micromamba.

    Args:
        env_path:       Full path to the environment directory
        python_version: e.g. "3.12" — empty means no Python (tool-only env)
        packages:       Additional packages to install at creation time
        channels:       Conda channels, defaults to ["conda-forge"]
        progress_cb:    Progress callback(str)
    """
    channels = channels or ["conda-forge"]
    packages = packages or []

    if progress_cb:
        progress_cb(f"Creating conda environment at {env_path}...")

    # Build specs
    specs = []
    if python_version:
        specs.append(f"python={python_version}")
    specs.extend(packages)

    def _build_args(chs):
        channel_args = []
        for ch in chs:
            channel_args += ["-c", ch]
        a = [
            "create",
            "--prefix", str(env_path),
            "--yes",
            "--no-rc",
            "--override-channels",
            *channel_args,
            *specs,
        ]
        return a

    # Attempt 1: conda-forge
    try:
        if _mirror_preferred() and "conda-forge" in channels:
            _log.debug("🌐 [Conda] using prefix.dev mirror "
                       "(saved preference for this network)")
            channels = _mirror_channels(channels)
        result = _run_micromamba(_build_args(channels),
                                 progress_cb, timeout=600)
        if result.returncode == 0:
            if progress_cb:
                progress_cb("Conda environment created!")
            return True

        err = result.stderr or ""
        # NOTE: no "defaults" channel fallback. "defaults" is Anaconda's
        # COMMERCIAL channel (ToS!) and mixing it into a conda-forge env makes
        # the solver rip out core packages (python/pip/vc14) — observed on
        # Windows: a simple preset install started unlinking python itself.

        # Network trouble reaching conda.anaconda.org? Retry via the
        # prefix.dev mirror of conda-forge (identical packages).
        if _is_network_error(err) and "conda-forge" in channels:
            _log.info("🌐 [Conda] conda-forge CDN unreachable — "
                      "retrying via prefix.dev mirror (same packages)")
            if progress_cb:
                progress_cb("conda-forge CDN unreachable — retrying via "
                            "prefix.dev mirror (same packages)...")
            result = _run_micromamba(_build_args(_mirror_channels(channels)),
                                     progress_cb, timeout=600)
            if result.returncode == 0:
                _remember_mirror_works()
                if progress_cb:
                    progress_cb("Conda environment created!")
                return True
            err = result.stderr or ""

        _log.warning(f"[Conda] create FAILED\n--- stderr ---\n{err[:1500]}")
        if progress_cb:
            progress_cb(f"Error: {_friendly_conda_error(err)}")
        return False

    except subprocess.TimeoutExpired:
        if progress_cb:
            progress_cb("Timed out creating environment")
        return False
    except Exception as e:
        if progress_cb:
            progress_cb(f"Error: {e}")
        return False


def install_conda_packages(env_path: Path, packages: list,
                           channels: list | None = None,
                           progress_cb=None) -> bool:
    """Install packages into an existing conda environment."""
    channels = channels or ["conda-forge"]

    if progress_cb:
        progress_cb(f"Installing: {', '.join(packages)}...")

    def _build_args(chs):
        channel_args = []
        for ch in chs:
            channel_args += ["-c", ch]
        a = [
            "install",
            "--prefix", str(env_path),
            "--yes",
            "--no-rc",
            "--override-channels",
            *channel_args,
            *packages,
        ]
        return a

    try:
        if _mirror_preferred() and "conda-forge" in channels:
            _log.debug("🌐 [Conda] using prefix.dev mirror "
                       "(saved preference for this network)")
            channels = _mirror_channels(channels)
        result = _run_micromamba(_build_args(channels),
                                 progress_cb, timeout=600)
        if result.returncode == 0:
            if progress_cb:
                progress_cb(f"Installed: {', '.join(packages)}")
            return True

        err = result.stderr or ""
        # NOTE: no "defaults" channel fallback — see create path for rationale.
        if _is_network_error(err) and "conda-forge" in channels:
            _log.info("🌐 [Conda] conda-forge CDN unreachable — "
                      "retrying via prefix.dev mirror (same packages)")
            if progress_cb:
                progress_cb("conda-forge CDN unreachable — retrying via "
                            "prefix.dev mirror (same packages)...")
            result = _run_micromamba(_build_args(_mirror_channels(channels)),
                                     progress_cb, timeout=600)
            if result.returncode == 0:
                _remember_mirror_works()
                if progress_cb:
                    progress_cb(f"Installed: {', '.join(packages)}")
                return True
            err = result.stderr or ""

        # "Shard package record ... missing checksums" comes from a STALE
        # LOCAL CACHE, not from the server: verified that `micromamba clean
        # --all` then the same install succeeds. Clean and retry once
        # (retrying against the canonical CDN is useless on networks where
        # conda.anaconda.org is blocked).
        if _is_mirror_data_error(err):
            _log.info("🧹 [Conda] stale package cache detected — "
                      "cleaning and retrying")
            if progress_cb:
                progress_cb("Package cache looks stale — cleaning and "
                            "retrying (this can take a moment)...")
            try:
                _run_micromamba(["clean", "--all", "--yes"], None, timeout=300)
            except Exception as _ce:
                _log.debug(f"[Conda] cache clean failed: {_ce}")
            result = _run_micromamba(_build_args(channels), progress_cb,
                                     timeout=600)
            if result.returncode == 0:
                if progress_cb:
                    progress_cb(f"Installed: {', '.join(packages)}")
                return True
            err = result.stderr or ""

        _log.warning(f"[Conda] install FAILED\n--- stderr ---\n{err[:1500]}")
        if progress_cb:
            progress_cb(f"Install failed: {_friendly_conda_error(err)}")
        return False

    except subprocess.TimeoutExpired:
        if progress_cb:
            progress_cb("Install timed out")
        return False
    except Exception as e:
        if progress_cb:
            progress_cb(f"Error: {e}")
        return False


def list_conda_packages(env_path: Path) -> list[dict]:
    """List packages installed in a conda env. Returns [{name, version, channel}]."""
    exe = get_micromamba_exe()
    if not exe:
        return []
    try:
        result = subprocess.run(
            [str(exe), "list", "--prefix", str(env_path), "--json",
             "--no-rc"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "MAMBA_NO_LOW_SPEED_LIMIT": "1"},
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def is_conda_env(env_path: Path) -> bool:
    """Check if env_path is a conda/micromamba environment."""
    marker = env_path / ".venvstudio_env"
    if marker.exists():
        try:
            import json
            with open(marker) as f:
                data = json.load(f)
            return data.get("type") == "conda"
        except Exception:
            pass
    # conda envs always have conda-meta/
    return (env_path / "conda-meta").exists()


def write_conda_marker(env_path: Path, python_version: str = "",
                       channels: list | None = None):
    """Write .venvstudio_env marker for a conda env."""
    import json
    import datetime
    marker = env_path / ".venvstudio_env"
    with open(marker, "w") as f:
        json.dump({
            "type": "conda",
            "name": env_path.name,
            "python_version": python_version,
            "channels": channels or ["conda-forge"],
            "created": datetime.datetime.now().isoformat(),
            "manager": "micromamba",
        }, f, indent=2)
