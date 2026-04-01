"""
VenvStudio - System Tools Installer
====================================
Downloads and installs system-level tools into a VenvStudio env folder.

Two installation strategies per tool:
  1. install_portable()  → ZIP/tarball/AppImage → extract into env/apps/<tool>/
  2. install_system()    → silent system-wide installer (NSIS /S, dpkg, hdiutil)

Portable is preferred: no system permissions, env folder contains everything,
deleting the env removes the tool too.

PATH injection:
  write_activation_scripts(env_path) writes activate.bat / activate.sh
  that prepend env/apps/<tool>/bin to PATH.
"""

import glob
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

from src.utils.platform_utils import get_platform, subprocess_args

_SSL_CTX = ssl.create_default_context()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "VenvStudio/1.0"})
    with urlopen(req, timeout=30, context=_SSL_CTX) as r:
        return json.loads(r.read().decode())


def _download(url: str, dest: Path, progress_cb=None, label: str = ""):
    req = Request(url, headers={"User-Agent": "VenvStudio/1.0"})
    try:
        with urlopen(req, timeout=600, context=_SSL_CTX) as resp:
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
                            f"Downloading {label}: {mb:.1f}/{total_mb:.0f} MB ({pct:.0f}%)"
                        )
    except URLError as e:
        raise RuntimeError(f"Download failed: {e}")


def _extract(archive: Path, dest: Path, progress_cb=None):
    """Extract zip / tar.gz / tar.bz2 / tar.xz / AppImage into dest."""
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    if progress_cb:
        progress_cb(f"Extracting {archive.name}...")
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(archive) as t:
            t.extractall(dest)
    elif name.endswith(".appimage"):
        target = dest / archive.name
        shutil.copy2(archive, target)
        target.chmod(0o755)
    else:
        raise RuntimeError(f"Unknown archive format: {archive.name}")


def _apps_dir(env_path: Path) -> Path:
    d = env_path / "apps"
    d.mkdir(exist_ok=True)
    return d


def _strip_single_root(src: Path) -> Path:
    """If extraction produced a single top-level dir, return it."""
    items = list(src.iterdir())
    if len(items) == 1 and items[0].is_dir():
        return items[0]
    return src


# ─── PATH / Activation scripts ────────────────────────────────────────────────

def write_activation_scripts(env_path: Path):
    """
    (Re)generate activate.bat and activate.sh for a system-tools env.
    Prepends every apps/<tool>/bin (or apps/<tool>/) to PATH.
    """
    apps = _apps_dir(env_path)
    bin_paths = []

    for tool_dir in sorted(apps.iterdir()):
        if not tool_dir.is_dir():
            continue
        added = False
        for sub in ("bin", "Scripts"):
            candidate = tool_dir / sub
            if candidate.is_dir():
                bin_paths.append(str(candidate))
                added = True
                break
        if not added:
            bin_paths.append(str(tool_dir))

    # Windows .bat
    bat = env_path / "activate.bat"
    with open(bat, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write(f"set VENVSTUDIO_ENV={env_path}\n")
        for p in bin_paths:
            f.write(f"set PATH={p};%PATH%\n")
        f.write(f'echo Activated: {env_path.name}\n')

    # POSIX .sh
    sh = env_path / "activate.sh"
    with open(sh, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\n")
        f.write(f'export VENVSTUDIO_ENV="{env_path}"\n')
        for p in bin_paths:
            f.write(f'export PATH="{p}:$PATH"\n')
        f.write(f'echo "Activated: {env_path.name}"\n')
    sh.chmod(0o755)


# ─── Base class ───────────────────────────────────────────────────────────────

class BaseInstaller:
    name: str = ""
    icon_key: str = ""

    def is_installed_system(self) -> bool:
        return bool(self.get_system_exe())

    def is_installed_portable(self, env_path: Path) -> bool:
        return (_apps_dir(env_path) / self.icon_key).exists()

    def is_installed(self, env_path: Path | None = None) -> bool:
        if env_path and self.is_installed_portable(env_path):
            return True
        return self.is_installed_system()

    def get_system_exe(self) -> str | None:
        return shutil.which(self.name) or shutil.which(self.name.lower())

    def get_portable_exe(self, env_path: Path) -> str | None:
        tool_dir = _apps_dir(env_path) / self.icon_key
        if not tool_dir.exists():
            return None
        for candidate in (self.name, self.name.lower(), self.name + ".exe"):
            for search in (tool_dir, tool_dir / "bin", tool_dir / "Scripts"):
                exe = search / candidate
                if exe.exists():
                    return str(exe)
        # Fallback: first executable
        for root, dirs, files in os.walk(tool_dir):
            for fn in files:
                fp = Path(root) / fn
                if fp.is_file() and os.access(fp, os.X_OK):
                    return str(fp)
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        raise NotImplementedError

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        raise NotImplementedError

    def install_system(self, progress_cb=None) -> bool:
        return self.install_portable(None, progress_cb)

    def install(self, env_path: Path | None = None, progress_cb=None,
                portable: bool = True) -> bool:
        if env_path and portable:
            ok = self.install_portable(env_path, progress_cb)
            if ok:
                write_activation_scripts(env_path)
            return ok
        return self.install_system(progress_cb)


# ═══════════════════════════════════════════════════════════════════════════════
#  R
# ═══════════════════════════════════════════════════════════════════════════════

class RInstaller(BaseInstaller):
    name = "R"
    icon_key = "r_console"

    def get_system_exe(self) -> str | None:
        exe = shutil.which("R") or shutil.which("R.exe")
        if exe:
            return exe
        if sys.platform == "win32":
            for base in (
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            ):
                matches = sorted(
                    glob.glob(os.path.join(base, "R", "R-*", "bin", "R.exe")),
                    reverse=True
                )
                if matches:
                    return matches[0]
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        plat = get_platform()
        if progress_cb:
            progress_cb("Fetching latest R version from CRAN...")
        import re
        if plat == "windows":
            req = Request("https://cran.r-project.org/bin/windows/base/release.htm",
                          headers={"User-Agent": "VenvStudio/1.0"})
            with urlopen(req, timeout=20, context=_SSL_CTX) as r:
                html = r.read().decode(errors="ignore")
            m = re.search(r"R-([\d.]+)-win\.exe", html)
            if not m:
                raise RuntimeError("Could not parse R version from CRAN")
            version = m.group(1)
            return {"version": version,
                    "url": f"https://cran.r-project.org/bin/windows/base/R-{version}-win.exe",
                    "filename": f"R-{version}-win.exe"}
        elif plat == "linux":
            return {"version": "system", "url": None, "filename": None,
                    "method": "pkg"}
        elif plat == "macos":
            req = Request("https://cran.r-project.org/bin/macosx/",
                          headers={"User-Agent": "VenvStudio/1.0"})
            with urlopen(req, timeout=20, context=_SSL_CTX) as r:
                html = r.read().decode(errors="ignore")
            arch = platform.machine().lower()
            pat = (r"R-([\d.]+)-arm64\.pkg" if arch in ("arm64", "aarch64")
                   else r"R-([\d.]+)(?:-x86_64)?\.pkg")
            m = re.search(pat, html)
            if not m:
                raise RuntimeError("Could not parse R version (macOS)")
            version = m.group(1)
            filename = m.group(0)
            return {"version": version,
                    "url": f"https://cran.r-project.org/bin/macosx/{filename}",
                    "filename": filename}
        raise RuntimeError(f"R: unsupported platform {plat}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        if plat == "linux":
            return self._install_linux(progress_cb)
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_r_"))
        installer = tmp / info["filename"]
        dest_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], installer, progress_cb, f"R {info['version']}")
            if progress_cb:
                progress_cb(f"Installing R {info['version']}...")
            if plat == "windows":
                args = [str(installer), "/VERYSILENT", "/NORESTART",
                        "/SUPPRESSMSGBOXES"]
                if dest_dir:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    args.append(f"/DIR={dest_dir}")
                result = subprocess.run(args, capture_output=True, text=True,
                                        timeout=300, **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"R installer failed ({result.returncode})\n{result.stderr[:300]}")
            elif plat == "macos":
                result = subprocess.run(
                    ["sudo", "installer", "-pkg", str(installer), "-target", "/"],
                    capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(f"R pkg install failed:\n{result.stderr[:300]}")
            if progress_cb:
                progress_cb(f"R {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"R install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def _install_linux(self, progress_cb=None) -> bool:
        try:
            with open("/etc/os-release") as f:
                os_info = f.read().lower()
        except Exception:
            os_info = ""
        if progress_cb:
            progress_cb("Installing R via package manager...")
        try:
            if any(x in os_info for x in ("arch", "manjaro", "cachyos")):
                cmds = [["sudo", "pacman", "-S", "--noconfirm", "r"]]
            elif any(x in os_info for x in ("debian", "ubuntu", "pardus", "mint")):
                cmds = [["sudo", "apt-get", "update", "-y"],
                        ["sudo", "apt-get", "install", "-y", "r-base", "r-base-dev"]]
            elif any(x in os_info for x in ("fedora", "rhel", "centos")):
                cmds = [["sudo", "dnf", "install", "-y", "R"]]
            elif "opensuse" in os_info:
                cmds = [["sudo", "zypper", "install", "-y", "R-base"]]
            else:
                if progress_cb:
                    progress_cb(
                        "Unknown distro — install R manually: https://cran.r-project.org")
                return False
            for cmd in cmds:
                if progress_cb:
                    progress_cb(f"  $ {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr[:400])
            if progress_cb:
                progress_cb("R installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"R install failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
#  RStudio
# ═══════════════════════════════════════════════════════════════════════════════

class RStudioInstaller(BaseInstaller):
    name = "rstudio"
    icon_key = "rstudio"

    def get_system_exe(self) -> str | None:
        exe = shutil.which("rstudio") or shutil.which("rstudio.exe")
        if exe:
            return exe
        if sys.platform == "win32":
            for base in (
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                os.environ.get("LOCALAPPDATA", ""),
            ):
                if not base:
                    continue
                for pattern in (
                    os.path.join(base, "RStudio", "bin", "rstudio.exe"),
                    os.path.join(base, "RStudio", "rstudio.exe"),
                    os.path.join(base, "Posit", "RStudio", "bin", "rstudio.exe"),
                ):
                    if os.path.isfile(pattern):
                        return pattern
                for m in glob.glob(
                        os.path.join(base, "RStudio*", "bin", "rstudio.exe")):
                    return m
        elif sys.platform == "linux":
            for path in (
                "/usr/lib/rstudio/bin/rstudio",
                "/usr/local/lib/rstudio/bin/rstudio",
                "/opt/rstudio/bin/rstudio",
            ):
                if os.path.isfile(path):
                    return path
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Fetching latest RStudio version...")
        plat = get_platform()
        import re
        try:
            req = Request("https://posit.co/download/rstudio-desktop/",
                          headers={"User-Agent": "VenvStudio/1.0"})
            with urlopen(req, timeout=20, context=_SSL_CTX) as r:
                html = r.read().decode(errors="ignore")
            arch = platform.machine().lower()
            if plat == "windows":
                m = re.search(
                    r"(https://download\d+\.rstudio\.org/desktop/windows/"
                    r"RStudio-[\d.\-]+\.exe)", html)
            elif plat == "macos":
                pat = (r"(https://download\d+\.rstudio\.org/desktop/macos/"
                       r"RStudio-[\d.\-]+-arm64\.dmg)"
                       if arch in ("arm64", "aarch64")
                       else r"(https://download\d+\.rstudio\.org/desktop/macos/"
                            r"RStudio-[\d.\-]+\.dmg)")
                m = re.search(pat, html)
            else:
                m = re.search(
                    r"(https://download\d+\.rstudio\.org/desktop/[^\"]+amd64\.deb)",
                    html)
            if not m:
                raise RuntimeError("Could not find RStudio download URL")
            url = m.group(1)
            filename = url.split("/")[-1]
            ver_m = re.search(r"RStudio-([\d.]+(?:-\d+)?)", filename)
            return {"version": ver_m.group(1) if ver_m else "latest",
                    "url": url, "filename": filename}
        except Exception as e:
            raise RuntimeError(f"Could not fetch RStudio info: {e}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_rstudio_"))
        installer = tmp / info["filename"]
        dest_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], installer, progress_cb,
                      f"RStudio {info['version']}")
            if progress_cb:
                progress_cb(f"Installing RStudio {info['version']}...")
            if plat == "windows":
                args = [str(installer), "/S"]
                if dest_dir:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    args.append(f"/D={dest_dir}")
                result = subprocess.run(args, capture_output=True, text=True,
                                        timeout=300, **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"RStudio installer failed ({result.returncode})")
            elif plat == "linux":
                result = subprocess.run(
                    ["sudo", "dpkg", "-i", str(installer)],
                    capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    subprocess.run(["sudo", "apt-get", "install", "-f", "-y"],
                                   capture_output=True, timeout=120)
            elif plat == "macos":
                mount = subprocess.run(
                    ["hdiutil", "attach", str(installer), "-nobrowse", "-quiet"],
                    capture_output=True, text=True, timeout=60)
                mount_point = next(
                    (l.split("\t")[-1].strip()
                     for l in mount.stdout.splitlines() if "/Volumes/" in l),
                    None)
                if mount_point:
                    app_dest = str(dest_dir) if dest_dir else "/Applications"
                    if dest_dir:
                        dest_dir.mkdir(parents=True, exist_ok=True)
                    subprocess.run(
                        ["cp", "-R", f"{mount_point}/RStudio.app", app_dest],
                        capture_output=True, timeout=120)
                    subprocess.run(["hdiutil", "detach", mount_point, "-quiet"],
                                   capture_output=True)
            if progress_cb:
                progress_cb(f"RStudio {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"RStudio install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Ollama
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaInstaller(BaseInstaller):
    name = "ollama"
    icon_key = "ollama"
    _RELEASES_API = "https://api.github.com/repos/ollama/ollama/releases/latest"

    def get_latest_info(self, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Fetching latest Ollama version...")
        data = _fetch_json(self._RELEASES_API)
        tag = data["tag_name"]
        plat = get_platform()
        arch = platform.machine().lower()
        name_map = {
            "windows": "OllamaSetup.exe",
            "macos":   "Ollama-darwin.zip",
            "linux":   ("ollama-linux-amd64.tgz"
                        if arch in ("x86_64", "amd64")
                        else "ollama-linux-arm64.tgz"),
        }
        filename = name_map[plat]
        for asset in data.get("assets", []):
            if asset["name"] == filename:
                return {"version": tag, "url": asset["browser_download_url"],
                        "filename": filename}
        raise RuntimeError(f"Ollama {filename} not found in release {tag}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_ollama_"))
        dest = tmp / info["filename"]
        tool_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], dest, progress_cb, f"Ollama {info['version']}")
            if progress_cb:
                progress_cb("Installing Ollama...")
            if plat == "windows":
                args = [str(dest), "/S"]
                if tool_dir:
                    tool_dir.mkdir(parents=True, exist_ok=True)
                    args.append(f"/D={tool_dir}")
                result = subprocess.run(args, capture_output=True, text=True,
                                        timeout=300, **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"Ollama installer failed ({result.returncode})")
            elif plat == "linux":
                bin_dir = (tool_dir / "bin") if tool_dir else (
                    Path.home() / ".local" / "bin")
                bin_dir.mkdir(parents=True, exist_ok=True)
                with tarfile.open(str(dest), "r:gz") as tar:
                    for member in tar.getmembers():
                        if "ollama" in member.name.lower() and (
                                "/" not in member.name.lstrip("./")):
                            member.name = "ollama"
                            tar.extract(member, path=str(bin_dir))
                            break
                ollama_bin = bin_dir / "ollama"
                if ollama_bin.exists():
                    ollama_bin.chmod(0o755)
            elif plat == "macos":
                extract_tmp = tmp / "extracted"
                _extract(dest, extract_tmp, progress_cb)
                app_dest = str(tool_dir) if tool_dir else "/Applications"
                if tool_dir:
                    tool_dir.mkdir(parents=True, exist_ok=True)
                app = next(extract_tmp.glob("*.app"), None)
                if app:
                    subprocess.run(["cp", "-R", str(app), app_dest],
                                   capture_output=True)
            if progress_cb:
                progress_cb(f"Ollama {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"Ollama install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  DBeaver  (official portable ZIP on Windows + Linux)
# ═══════════════════════════════════════════════════════════════════════════════

class DBeaverInstaller(BaseInstaller):
    name = "dbeaver"
    icon_key = "dbeaver"
    _RELEASES_API = "https://api.github.com/repos/dbeaver/dbeaver/releases/latest"

    def get_system_exe(self) -> str | None:
        exe = shutil.which("dbeaver") or shutil.which("dbeaver.exe")
        if exe:
            return exe
        if sys.platform == "win32":
            for base in (
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            ):
                c = os.path.join(base, "DBeaver", "dbeaver.exe")
                if os.path.isfile(c):
                    return c
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Fetching latest DBeaver version...")
        data = _fetch_json(self._RELEASES_API)
        tag = data["tag_name"]
        version = tag.lstrip("v")
        plat = get_platform()
        arch = platform.machine().lower()

        # Prefer portable ZIP/tarball
        portable_names = {
            "windows": f"dbeaver-ce-{version}-win32.win32.x86_64.zip",
            "linux":   f"dbeaver-ce-{version}-linux.gtk.x86_64.tar.gz",
            "macos":   (f"dbeaver-ce-{version}-macos-aarch64.dmg"
                        if arch in ("arm64", "aarch64")
                        else f"dbeaver-ce-{version}-macos-x86_64.dmg"),
        }
        target = portable_names.get(plat, "")
        for asset in data.get("assets", []):
            if asset["name"] == target:
                return {"version": version, "url": asset["browser_download_url"],
                        "filename": target,
                        "portable": plat in ("windows", "linux")}

        # Fallback to installer
        suf = {"windows": ".exe", "linux": "amd64.deb", "macos": ".dmg"}.get(plat, ".exe")
        for asset in data.get("assets", []):
            if asset["name"].endswith(suf) and "ce" in asset["name"].lower():
                return {"version": version, "url": asset["browser_download_url"],
                        "filename": asset["name"], "portable": False}
        raise RuntimeError(f"DBeaver installer not found for {plat}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_dbeaver_"))
        dest = tmp / info["filename"]
        tool_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], dest, progress_cb, f"DBeaver {info['version']}")
            if progress_cb:
                progress_cb("Installing DBeaver...")

            if info.get("portable") and tool_dir:
                # Extract portable archive directly into tool_dir
                tool_dir.mkdir(parents=True, exist_ok=True)
                extract_tmp = tmp / "extracted"
                _extract(dest, extract_tmp, progress_cb)
                top = _strip_single_root(extract_tmp)
                shutil.copytree(str(top), str(tool_dir), dirs_exist_ok=True)
            elif plat == "windows":
                result = subprocess.run(
                    [str(dest), "/S"],
                    capture_output=True, text=True, timeout=300,
                    **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"DBeaver installer failed ({result.returncode})")
            elif plat == "linux":
                result = subprocess.run(
                    ["sudo", "dpkg", "-i", str(dest)],
                    capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    subprocess.run(["sudo", "apt-get", "install", "-f", "-y"],
                                   capture_output=True, timeout=120)
            elif plat == "macos":
                mount = subprocess.run(
                    ["hdiutil", "attach", str(dest), "-nobrowse", "-quiet"],
                    capture_output=True, text=True, timeout=60)
                mount_point = next(
                    (l.split("\t")[-1].strip()
                     for l in mount.stdout.splitlines() if "/Volumes/" in l),
                    None)
                if mount_point:
                    app_dest = str(tool_dir) if tool_dir else "/Applications"
                    if tool_dir:
                        tool_dir.mkdir(parents=True, exist_ok=True)
                    subprocess.run(
                        ["cp", "-R", f"{mount_point}/DBeaver.app", app_dest],
                        capture_output=True, timeout=120)
                    subprocess.run(["hdiutil", "detach", mount_point, "-quiet"],
                                   capture_output=True)

            if progress_cb:
                progress_cb(f"DBeaver {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"DBeaver install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  jamovi  (AppImage on Linux = fully portable single file)
# ═══════════════════════════════════════════════════════════════════════════════

class JamoviInstaller(BaseInstaller):
    name = "jamovi"
    icon_key = "jamovi"
    _RELEASES_API = "https://api.github.com/repos/jamovi/jamovi/releases/latest"

    def get_system_exe(self) -> str | None:
        exe = shutil.which("jamovi") or shutil.which("jamovi.exe")
        if exe:
            return exe
        if sys.platform == "win32":
            for base in (
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                os.environ.get("LOCALAPPDATA", ""),
            ):
                if not base:
                    continue
                for m in glob.glob(os.path.join(base, "jamovi*", "jamovi.exe")):
                    return m
        elif sys.platform == "linux":
            for m in glob.glob(
                    os.path.expanduser("~/Applications/jamovi*.AppImage")):
                return m
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Fetching latest jamovi version...")
        data = _fetch_json(self._RELEASES_API)
        tag = data["tag_name"]
        version = tag.lstrip("v")
        plat = get_platform()
        matchers = {
            "windows": lambda n: n.endswith(".exe") and "jamovi" in n.lower(),
            "linux":   lambda n: n.endswith(".AppImage") and "jamovi" in n.lower(),
            "macos":   lambda n: n.endswith(".dmg") and "jamovi" in n.lower(),
        }
        matcher = matchers.get(plat, lambda n: False)
        for asset in data.get("assets", []):
            if matcher(asset["name"]):
                return {"version": version, "url": asset["browser_download_url"],
                        "filename": asset["name"],
                        "portable": plat == "linux"}
        raise RuntimeError(f"jamovi release not found for {plat}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_jamovi_"))
        dest = tmp / info["filename"]
        tool_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], dest, progress_cb, f"jamovi {info['version']}")
            if progress_cb:
                progress_cb("Installing jamovi...")

            if plat == "linux":
                # AppImage = single portable file
                bin_dir = tool_dir if tool_dir else (Path.home() / "Applications")
                bin_dir.mkdir(parents=True, exist_ok=True)
                target = bin_dir / info["filename"]
                shutil.copy2(str(dest), str(target))
                target.chmod(0o755)
                # Wrapper script named "jamovi" for PATH convenience
                wrapper = bin_dir / "jamovi"
                with open(wrapper, "w", newline="\n") as f:
                    f.write(f'#!/bin/sh\nexec "{target}" "$@"\n')
                wrapper.chmod(0o755)

            elif plat == "windows":
                args = [str(dest), "/S"]
                if tool_dir:
                    tool_dir.mkdir(parents=True, exist_ok=True)
                    args.append(f"/D={tool_dir}")
                result = subprocess.run(args, capture_output=True, text=True,
                                        timeout=300, **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"jamovi installer failed ({result.returncode})")

            elif plat == "macos":
                mount = subprocess.run(
                    ["hdiutil", "attach", str(dest), "-nobrowse", "-quiet"],
                    capture_output=True, text=True, timeout=60)
                mount_point = next(
                    (l.split("\t")[-1].strip()
                     for l in mount.stdout.splitlines() if "/Volumes/" in l),
                    None)
                if mount_point:
                    app_dest = str(tool_dir) if tool_dir else "/Applications"
                    if tool_dir:
                        tool_dir.mkdir(parents=True, exist_ok=True)
                    apps = glob.glob(f"{mount_point}/*.app")
                    if apps:
                        subprocess.run(["cp", "-R", apps[0], app_dest],
                                       capture_output=True, timeout=120)
                    subprocess.run(["hdiutil", "detach", mount_point, "-quiet"],
                                   capture_output=True)

            if progress_cb:
                progress_cb(f"jamovi {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"jamovi install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  JASP
# ═══════════════════════════════════════════════════════════════════════════════

class JASPInstaller(BaseInstaller):
    name = "JASP"
    icon_key = "jasp"
    _RELEASES_API = "https://api.github.com/repos/jasp-stats/jasp-desktop/releases/latest"

    def get_system_exe(self) -> str | None:
        exe = shutil.which("JASP") or shutil.which("jasp")
        if exe:
            return exe
        if sys.platform == "win32":
            for base in (
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            ):
                for m in glob.glob(os.path.join(base, "JASP*", "JASP.exe")):
                    return m
        elif sys.platform == "linux":
            for m in glob.glob(
                    os.path.expanduser("~/Applications/JASP*.AppImage")):
                return m
        return None

    def get_latest_info(self, progress_cb=None) -> dict:
        if progress_cb:
            progress_cb("Fetching latest JASP version...")
        data = _fetch_json(self._RELEASES_API)
        tag = data["tag_name"]
        version = tag.lstrip("v")
        plat = get_platform()
        matchers = {
            "windows": lambda n: n.endswith(".exe") and "JASP" in n,
            "linux":   lambda n: n.endswith(".AppImage") and "JASP" in n,
            "macos":   lambda n: n.endswith(".dmg") and "JASP" in n,
        }
        matcher = matchers.get(plat, lambda n: False)
        for asset in data.get("assets", []):
            if matcher(asset["name"]):
                return {"version": version, "url": asset["browser_download_url"],
                        "filename": asset["name"],
                        "portable": plat == "linux"}
        raise RuntimeError(f"JASP release not found for {plat}")

    def install_portable(self, env_path: Path | None, progress_cb=None) -> bool:
        plat = get_platform()
        info = self.get_latest_info(progress_cb)
        tmp = Path(tempfile.mkdtemp(prefix="venvstudio_jasp_"))
        dest = tmp / info["filename"]
        tool_dir = _apps_dir(env_path) / self.icon_key if env_path else None
        try:
            _download(info["url"], dest, progress_cb, f"JASP {info['version']}")
            if progress_cb:
                progress_cb("Installing JASP...")

            if plat == "linux":
                bin_dir = tool_dir if tool_dir else (Path.home() / "Applications")
                bin_dir.mkdir(parents=True, exist_ok=True)
                target = bin_dir / info["filename"]
                shutil.copy2(str(dest), str(target))
                target.chmod(0o755)
                wrapper = bin_dir / "JASP"
                with open(wrapper, "w", newline="\n") as f:
                    f.write(f'#!/bin/sh\nexec "{target}" "$@"\n')
                wrapper.chmod(0o755)

            elif plat == "windows":
                args = [str(dest), "/S"]
                if tool_dir:
                    tool_dir.mkdir(parents=True, exist_ok=True)
                    args.append(f"/D={tool_dir}")
                result = subprocess.run(args, capture_output=True, text=True,
                                        timeout=300, **subprocess_args())
                if result.returncode not in (0, 3010):
                    raise RuntimeError(
                        f"JASP installer failed ({result.returncode})")

            elif plat == "macos":
                mount = subprocess.run(
                    ["hdiutil", "attach", str(dest), "-nobrowse", "-quiet"],
                    capture_output=True, text=True, timeout=60)
                mount_point = next(
                    (l.split("\t")[-1].strip()
                     for l in mount.stdout.splitlines() if "/Volumes/" in l),
                    None)
                if mount_point:
                    app_dest = str(tool_dir) if tool_dir else "/Applications"
                    if tool_dir:
                        tool_dir.mkdir(parents=True, exist_ok=True)
                    apps = glob.glob(f"{mount_point}/*.app")
                    if apps:
                        subprocess.run(["cp", "-R", apps[0], app_dest],
                                       capture_output=True, timeout=120)
                    subprocess.run(["hdiutil", "detach", mount_point, "-quiet"],
                                   capture_output=True)

            if progress_cb:
                progress_cb(f"JASP {info['version']} installed!")
            return True
        except Exception as e:
            if progress_cb:
                progress_cb(f"JASP install failed: {e}")
            return False
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════════════════════

INSTALLERS: dict = {
    "r_console": RInstaller(),
    "rstudio":   RStudioInstaller(),
    "ollama":    OllamaInstaller(),
    "dbeaver":   DBeaverInstaller(),
    "jamovi":    JamoviInstaller(),
    "jasp":      JASPInstaller(),
    # quarto → pip install quarto-cli (bundles binary, no system install needed)
}


def get_installer(icon_key: str) -> "BaseInstaller | None":
    return INSTALLERS.get(icon_key)
