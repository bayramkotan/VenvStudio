"""VenvStudio - MainWindow: Linux-specific Fixes Mixin
Linux venv module detection, distro detection, emoji-font fix
(moved from main_window.py).
"""
from PySide6.QtWidgets import QMessageBox


class LinuxFixesMixin:
    """Mixin for MainWindow: Linux distro/venv-module/emoji-font fixes."""

    def _check_linux_venv_module(self):
        """On Linux, check if venv module is available. If not, offer to install
        using the correct distro package manager.
        """
        import platform as _platform
        if _platform.system().lower() != "linux":
            return

        import subprocess, shutil
        from src.utils.platform_utils import subprocess_args
        # Resolve Python executable — Arch/CachyOS has `python` but often no
        # `python3` symlink; Debian/Ubuntu has both.
        py_exe = shutil.which("python3") or shutil.which("python")
        if not py_exe:
            return  # no Python — different problem, not our concern here

        # Check if venv module works
        try:
            result = subprocess.run(
                [py_exe, "-m", "venv", "--help"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            if result.returncode == 0:
                return  # Already installed — this is the happy path
        except Exception:
            pass

        # venv not available — detect distro and build correct install command
        distro_info = self._detect_linux_distro()
        pkg_manager = distro_info["pkg_manager"]
        pkg_name = distro_info["pkg_name"]
        install_cmd = distro_info["install_cmd"]

        # venv not available — ask user to install
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Python venv module missing",
            f"The Python venv module is required to create virtual environments\n"
            f"but it is not available on your system.\n\n"
            f"Detected distro: {distro_info['name']}\n"
            f"Would run: {' '.join(install_cmd)}\n\n"
            f"Install it now? (requires admin password)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Try pkexec first (GUI password prompt), then sudo
        for sudo_cmd in [["pkexec"], ["sudo"]]:
            exe = sudo_cmd[0]
            if not shutil.which(exe):
                continue
            try:
                r = subprocess.run(
                    sudo_cmd + install_cmd,
                    **subprocess_args(timeout=180)
                )
                if r.returncode == 0:
                    QMessageBox.information(
                        self, "Success",
                        f"{pkg_name} installed successfully!\n"
                        "You can now create virtual environments."
                    )
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        # All attempts failed — show distro-aware manual instructions
        manual_commands = [
            "  sudo apt install python3-venv         (Debian / Ubuntu / Pardus)",
            "  sudo dnf install python3-virtualenv   (Fedora / RHEL)",
            "  sudo pacman -S python                 (Arch / CachyOS — venv is bundled)",
            "  sudo zypper install python3-virtualenv (openSUSE)",
        ]
        QMessageBox.warning(
            self, "Installation Failed",
            f"Could not install {pkg_name} automatically.\n\n"
            "Please run manually for your distribution:\n" +
            "\n".join(manual_commands)
        )

    def _detect_linux_distro(self) -> dict:
        """Inspect /etc/os-release to pick the right package manager + package name
        for the venv module. Returns a dict with: name, pkg_manager, pkg_name, install_cmd.
        """
        import os, shutil
        info = {"name": "unknown", "pkg_manager": "", "pkg_name": "python3-venv",
                "install_cmd": ["apt", "install", "-y", "python3-venv"]}
        try:
            with open("/etc/os-release") as f:
                data = {}
                for line in f:
                    if "=" in line:
                        k, _, v = line.strip().partition("=")
                        data[k] = v.strip('"').lower()
            id_ = data.get("ID", "")
            id_like = data.get("ID_LIKE", "")
            info["name"] = data.get("PRETTY_NAME", id_).replace('"', '')

            # Arch family — CachyOS, Manjaro, EndeavourOS: venv ships with `python`
            if id_ in ("arch", "cachyos", "manjaro", "endeavouros") or "arch" in id_like:
                info["pkg_manager"] = "pacman"
                info["pkg_name"] = "python"
                info["install_cmd"] = ["pacman", "-S", "--needed", "--noconfirm", "python"]
            # Fedora / RHEL family
            elif id_ in ("fedora", "rhel", "centos", "rocky", "almalinux") or "fedora" in id_like or "rhel" in id_like:
                info["pkg_manager"] = "dnf"
                info["pkg_name"] = "python3-virtualenv"
                # Fedora ships venv in `python3-libs`, but python3-virtualenv is safer fallback
                info["install_cmd"] = ["dnf", "install", "-y", "python3-virtualenv"]
            # openSUSE
            elif id_ in ("opensuse", "opensuse-tumbleweed", "opensuse-leap", "sles") or "suse" in id_like:
                info["pkg_manager"] = "zypper"
                info["pkg_name"] = "python3-virtualenv"
                info["install_cmd"] = ["zypper", "install", "-y", "python3-virtualenv"]
            # Debian / Ubuntu / Pardus / Mint — default
            elif id_ in ("debian", "ubuntu", "pardus", "linuxmint", "pop") or "debian" in id_like or "ubuntu" in id_like:
                info["pkg_manager"] = "apt"
                info["pkg_name"] = "python3-venv"
                info["install_cmd"] = ["apt", "install", "-y", "python3-venv"]
            # Fallback — sniff which package manager is on PATH
            else:
                for cmd, pm, pkg, install in [
                    ("pacman", "pacman", "python",               ["pacman", "-S", "--needed", "--noconfirm", "python"]),
                    ("apt",    "apt",    "python3-venv",         ["apt", "install", "-y", "python3-venv"]),
                    ("dnf",    "dnf",    "python3-virtualenv",   ["dnf", "install", "-y", "python3-virtualenv"]),
                    ("zypper", "zypper", "python3-virtualenv",   ["zypper", "install", "-y", "python3-virtualenv"]),
                ]:
                    if shutil.which(cmd):
                        info["pkg_manager"] = pm
                        info["pkg_name"] = pkg
                        info["install_cmd"] = install
                        break
        except Exception:
            pass
        return info

    def _apply_linux_emoji_fix(self):
        """On Linux, check and offer to install Noto Color Emoji font."""
        import sys as _sys
        import platform as _platform
        if _platform.system().lower() != "linux":
            return

        # Skip entirely in a frozen build (AppImage). The AppImage bundles
        # Noto Color Emoji and installs it to the user's font dir on launch,
        # so the host doesn't need its own copy. Worse, this probe runs an
        # `fc-list` that may not yet see the freshly-installed font, so it
        # false-positives and nags the user with an "Emoji Font Missing"
        # dialog for a font that IS present. Only run in a normal pip/source
        # install, where prompting to install a system font makes sense.
        if getattr(_sys, "frozen", False):
            return

        import shutil, subprocess
        # Check if Noto Color Emoji is installed, offer to install if missing
        try:
            result = subprocess.run(
                ["fc-list", ":family=Noto Color Emoji"],
                capture_output=True, text=True, timeout=5
            )
            emoji_available = bool(result.stdout.strip())
        except Exception:
            emoji_available = False

        if not emoji_available:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Emoji Font Missing",
                "Noto Color Emoji font is not installed.\n"
                "Without it, icons in buttons will appear grey/black.\n\n"
                "Install now? (requires admin password)",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                for sudo in [["pkexec"], ["sudo"]]:
                    try:
                        r = subprocess.run(
                            sudo + ["apt-get", "install", "-y", "fonts-noto-color-emoji"],
                            capture_output=True, text=True, timeout=120
                        )
                        if r.returncode == 0:
                            # Rebuild font cache
                            subprocess.run(["fc-cache", "-f"], timeout=30)
                            emoji_available = True
                            break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

