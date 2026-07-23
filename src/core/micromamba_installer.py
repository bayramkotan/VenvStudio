"""
micromamba installer + MicromambaEnv manager
"""

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
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

# Live micromamba processes, so a cancelled worker can actually stop the
# download instead of only setting a flag. WorkerThread.cancel() used to
# just flip _cancelled, which suppressed the result but left micromamba
# running; the thread then outlived the window and Qt aborted with
# "QThread: Destroyed while thread is still running" on shutdown (B186).
_ACTIVE_PROCS = set()
_ACTIVE_PROCS_LOCK = threading.Lock()


def kill_active_micromamba() -> int:
    """Kill every running micromamba child process.

    Returns the number of processes signalled. Safe to call from any
    thread; the reader loop in _run_micromamba sees the closed pipe and
    unwinds normally, so no thread is killed mid-syscall.
    """
    with _ACTIVE_PROCS_LOCK:
        procs = list(_ACTIVE_PROCS)
    _killed = 0
    for _p in procs:
        try:
            if _p.poll() is None:
                _p.kill()
                _killed += 1
        except Exception:
            pass
    if _killed:
        _log.info(f"\u26d4 [Conda] killed {_killed} running micromamba process(es)")
    return _killed


def _clean_micromamba_line(line: str) -> str:
    """Strip micromamba spinner/progress glyphs from a status line.

    micromamba pads its progress lines with box-drawing and spinner
    characters that the UI font has no glyph for, so they showed up in the
    status bar as empty boxes or mojibake.
    """
    for _g in ("\u29d6", "\u2714", "\u2718", "\u2500", "\u2588", "\u2591",
               "\u2592", "\u2593", "\u25cf", "\u25cb", "\u23f3"):
        line = line.replace(_g, "")
    return " ".join(line.split())


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
        text=True, bufsize=1, env=_env,
        encoding="utf-8", errors="replace", **_kw,
    )
    with _ACTIVE_PROCS_LOCK:
        _ACTIVE_PROCS.add(_proc)
    import time as _time
    _t0 = _time.time()
    try:
        for _line in _proc.stdout:
            _line = _line.rstrip()
            _out_lines.append(_line)
            if progress_cb and _line.strip():
                progress_cb(_clean_micromamba_line(_line)[:200])
            if _skip_was_requested():
                # User pressed "Skip mirror": stop this attempt now so the
                # caller can move to the next mirror in the list.
                _proc.kill()
                break
            if _time.time() - _t0 > timeout:
                _proc.kill()
                raise subprocess.TimeoutExpired(cmd, timeout)
    finally:
        try:
            _proc.stdout.close()
        except Exception:
            pass
        _rc = _proc.wait()
        with _ACTIVE_PROCS_LOCK:
            _ACTIVE_PROCS.discard(_proc)
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

# Ordered conda-forge mirrors. All serve the SAME packages -- only the CDN
# hostname differs -- so switching is always safe. The order is user-editable
# in Settings > Paths > Conda Mirrors; DEFAULT_CONDA_MIRRORS is the reset
# target and the fallback when the config has no list yet.
DEFAULT_CONDA_MIRRORS = [
    "https://repo.prefix.dev/conda-forge",
    "https://conda.anaconda.org/conda-forge",
    "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    "https://mirror.nju.edu.cn/anaconda/cloud/conda-forge",
    "https://mirrors.bfsu.edu.cn/anaconda/cloud/conda-forge",
]


def get_conda_mirrors() -> list:
    """Mirror list from settings, falling back to the defaults."""
    try:
        from src.core.config_manager import ConfigManager
        _m = ConfigManager().get("conda_mirrors")
        if isinstance(_m, list) and _m:
            return [str(x).strip() for x in _m if str(x).strip()]
    except Exception:
        pass
    return list(DEFAULT_CONDA_MIRRORS)


# Set by the UI "Skip mirror" button. _run_micromamba checks it, kills the
# current child and reports the skip so the caller moves to the next mirror
# instead of waiting out a slow one.
_SKIP_REQUESTED = threading.Event()


def request_mirror_skip() -> None:
    """Abandon the running micromamba call and advance to the next mirror."""
    _SKIP_REQUESTED.set()
    kill_active_micromamba()


def _clear_mirror_skip() -> None:
    _SKIP_REQUESTED.clear()


def _skip_was_requested() -> bool:
    return _SKIP_REQUESTED.is_set()


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
    return _channels_for_mirror(channels, _CONDA_FORGE_MIRROR)


def _channels_for_mirror(channels, mirror_url):
    """Point the conda-forge channel at a specific mirror URL."""
    _known = set(DEFAULT_CONDA_MIRRORS) | set(get_conda_mirrors())
    out = []
    for c in channels:
        if c == "conda-forge" or c in _known:
            out.append(mirror_url)
        else:
            out.append(c)
    return out


# PyPI names that differ on conda-forge. Presets/catalog store PyPI names
# (correct for pip envs), so translate before handing them to micromamba.
_PYPI_TO_CONDA = {
    "factory-boy": "factory_boy",          # verified on conda-forge
    "psycopg2-binary": "psycopg2",
    "django-rest-framework": "djangorestframework",
    "opencv-python": "opencv",
    "opencv-python-headless": "opencv",
    "tables": "pytables",
    "torch": "pytorch",
}


def _to_conda_names(packages):
    """Map known PyPI names to their conda-forge equivalents."""
    out, changed = [], []
    for pkg in packages:
        c = _PYPI_TO_CONDA.get(pkg.lower(), pkg)
        out.append(c)
        if c != pkg:
            changed.append(f"{pkg}\u2192{c}")
    if changed:
        _log.info("\U0001f501 [Conda] PyPI\u2192conda-forge name translation: "
                  + ", ".join(changed))
    return out


def _missing_packages(err: str):
    """Extract package names micromamba reported as non-existent."""
    import re as _re
    low = err.lower()
    names = set()
    for pat in (r"\u2514\u2500 ([\w.\-]+) =\* \* does not exist",
                r"([\w.\-]+) =\* \* does not exist",
                r"nothing provides(?: requested)? ([\w.\-]+)"):
        names.update(_re.findall(pat, low))
    return sorted(names)


def _underscore_variants(packages, missing):
    """conda-forge often uses "_" where PyPI uses "-" (factory-boy ->
    factory_boy). Rewrite ONLY the packages reported missing."""
    miss = {m.lower() for m in missing}
    out, changed = [], []
    for pkg in packages:
        if pkg.lower() in miss and "-" in pkg:
            alt = pkg.replace("-", "_")
            out.append(alt)
            changed.append(f"{pkg}\u2192{alt}")
        else:
            out.append(pkg)
    return out, changed


def _friendly_conda_error(err: str) -> str:
    """Turn known micromamba failures into actionable messages."""
    _e = err.lower()
    # Solver conflict: the package exists on conda-forge but not for this
    # Python version / platform. Raw solver output buried this behind pages
    # of unrelated checksum warnings, so the UI only said "install failed".
    if ("could not solve for environment" in _e
            or "is not installable" in _e
            or "packages are incompatible" in _e):
        _pin = ""
        _m = re.search(r"pin on python\s*=?\s*([0-9.]+)", err)
        if _m:
            _pin = f" (this environment is pinned to Python {_m.group(1)})"
        return (
            "No version of this package works with this environment"
            + _pin + ".\n"
            "conda-forge may not ship it for this Python version or "
            "platform. Options: pick an older Python when creating the "
            "environment, or install it with pip instead.\n\n"
            "--- solver output ---\n" + err[:600]
        )
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
        _clear_mirror_skip()
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

        # Mirror rotation -- see install_conda_packages for the rationale.
        if (_skip_was_requested() or _is_mirror_data_error(err)
                or _is_network_error(err)):
            _mirrors = get_conda_mirrors()
            _tried = {c for c in channels if c in set(_mirrors)}
            for _i, _m in enumerate(_mirrors, 1):
                if _m in _tried:
                    continue
                _clear_mirror_skip()
                _host = _m.split("//")[-1].split("/")[0]
                _log.info(f"🌐 [{_i}/{len(_mirrors)}] trying mirror "
                          f"{_host}")
                if progress_cb:
                    progress_cb(f"Trying mirror [{_i}/{len(_mirrors)}] "
                                f"{_host}...")
                result = _run_micromamba(
                    _build_args(_channels_for_mirror(channels, _m)),
                    progress_cb, timeout=600)
                _tried.add(_m)
                if result.returncode == 0:
                    if progress_cb:
                        progress_cb("Conda environment created!")
                    return True
                err = result.stderr or ""
                if not (_skip_was_requested() or _is_mirror_data_error(err)
                        or _is_network_error(err)):
                    break
            _clear_mirror_skip()
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
    # Preset/catalog entries use PyPI names; conda-forge sometimes differs
    # (factory-boy -> factory_boy). Translate known ones up front.
    packages = _to_conda_names(list(packages))

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
        _clear_mirror_skip()
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

        # Mirror rotation. Triggered when the user pressed "Skip mirror" or
        # when the mirror served unusable metadata / was unreachable. Every
        # mirror carries the same packages, so trying the next one costs
        # nothing but time -- and skipping saves exactly that.
        if (_skip_was_requested() or _is_mirror_data_error(err)
                or _is_network_error(err)):
            _mirrors = get_conda_mirrors()
            _tried = {c for c in channels if c in set(_mirrors)}
            for _i, _m in enumerate(_mirrors, 1):
                if _m in _tried:
                    continue
                _clear_mirror_skip()
                _host = _m.split("//")[-1].split("/")[0]
                _log.info(f"🌐 [{_i}/{len(_mirrors)}] trying mirror "
                          f"{_host}")
                if progress_cb:
                    progress_cb(f"Trying mirror [{_i}/{len(_mirrors)}] "
                                f"{_host}...")
                result = _run_micromamba(
                    _build_args(_channels_for_mirror(channels, _m)),
                    progress_cb, timeout=600)
                _tried.add(_m)
                if result.returncode == 0:
                    if progress_cb:
                        progress_cb(f"Installed: {', '.join(packages)}")
                    return True
                err = result.stderr or ""
                if not (_skip_was_requested() or _is_mirror_data_error(err)
                        or _is_network_error(err)):
                    # A real solver error (package not available for this
                    # Python version, etc.) -- another mirror cannot help.
                    break
            _clear_mirror_skip()
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

        # conda-forge frequently uses "_" where PyPI uses "-" (factory-boy →
        # factory_boy). If the solver says a package doesn't exist, retry the
        # missing ones with underscores before giving up.
        _missing = _missing_packages(err)
        if _missing:
            _alt, _changed = _underscore_variants(packages, _missing)
            if _changed:
                _log.info("🔁 [Conda] retrying with conda-style names: "
                          + ", ".join(_changed))
                if progress_cb:
                    progress_cb("Retrying with conda-forge naming ("
                                + ", ".join(_changed) + ")...")
                _orig_pkgs = packages
                packages = _alt
                result = _run_micromamba(_build_args(channels), progress_cb,
                                         timeout=600)
                if result.returncode == 0:
                    _log.info("✅ [Conda] succeeded after name correction")
                    if progress_cb:
                        progress_cb(f"Installed: {', '.join(packages)}")
                    return True
                packages = _orig_pkgs
                err = result.stderr or err

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
