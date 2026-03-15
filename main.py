#!/usr/bin/env python3
"""
VenvStudio - Lightweight Python Virtual Environment Manager
A modern, cross-platform virtual environment manager.

Usage:
    python main.py
"""

import sys
import os
import traceback
import multiprocessing

# PyInstaller freeze support — Windows'ta subprocess yeni pencere açmasını engeller
multiprocessing.freeze_support()

# PyInstaller ile paketlendiğinde doğru path'i bul
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    sys.path.insert(0, BASE_DIR)

    # Qt plugin path — PyInstaller bundle içindeki doğru yolu ayarla
    qt_plugin_path = os.path.join(BASE_DIR, "PySide6", "Qt", "plugins")
    if not os.path.isdir(qt_plugin_path):
        qt_plugin_path = os.path.join(BASE_DIR, "PySide6", "plugins")
    if os.path.isdir(qt_plugin_path):
        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path

    # Linux'ta xcb platform plugin sorunları için
    if sys.platform == "linux":
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
        # libxcb-cursor0 yoksa offscreen dene
        platform_dir = os.path.join(qt_plugin_path, "platforms") if os.path.isdir(qt_plugin_path) else ""
        if platform_dir and os.path.isdir(platform_dir):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platform_dir
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

# ── High DPI: env variables MUST be set before QApplication ──
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")


def _check_and_install_linux_deps(app, config, logger):
    """Check if pip and venv are available on Linux. If not, offer to install them."""
    import subprocess
    import shutil

    # Skip if already checked and installed
    if config.get("linux_deps_checked", False):
        return

    python_exe = shutil.which("python3") or shutil.which("python") or sys.executable
    missing = []

    # Check pip
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            missing.append("pip")
    except Exception:
        missing.append("pip")

    # Check venv
    try:
        result = subprocess.run(
            [python_exe, "-m", "venv", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            missing.append("venv")
    except Exception:
        missing.append("venv")

    # Check python-is-python3 (is /usr/bin/python available?)
    if not shutil.which("python") and shutil.which("python3"):
        missing.append("python-is-python3")

    if not missing:
        config.set("linux_deps_checked", True)
        return

    logger.warning(f"Missing Linux packages: {missing}")

    # Detect distro
    distro = _detect_distro()

    # Build package list and install command
    if distro == "debian":
        packages = []
        if "pip" in missing:
            packages.append("python3-pip")
        if "venv" in missing:
            # Get Python version for versioned package
            try:
                r = subprocess.run(
                    [python_exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                    capture_output=True, text=True, timeout=5,
                )
                py_ver = r.stdout.strip()
                if py_ver:
                    packages.append(f"python{py_ver}-venv")
            except Exception:
                pass
            packages.append("python3-venv")
        if "python-is-python3" in missing:
            packages.append("python-is-python3")
        install_cmd = ["apt", "install", "-y"] + packages
    elif distro == "arch":
        packages = []
        if "pip" in missing:
            packages.append("python-pip")
        # venv is included in python package on Arch
        if not packages:
            config.set("linux_deps_checked", True)
            return
        install_cmd = ["pacman", "-S", "--noconfirm"] + packages
    elif distro == "fedora":
        packages = []
        if "pip" in missing:
            packages.append("python3-pip")
        # venv is included in python3 on Fedora
        if not packages:
            config.set("linux_deps_checked", True)
            return
        install_cmd = ["dnf", "install", "-y"] + packages
    elif distro == "suse":
        packages = []
        if "pip" in missing:
            packages.append("python3-pip")
        if "venv" in missing:
            packages.append("python3-venv")
        if not packages:
            config.set("linux_deps_checked", True)
            return
        install_cmd = ["zypper", "--non-interactive", "install"] + packages
    else:
        # Unknown distro — skip auto-install
        logger.info(f"Unknown distro, skipping auto-install for: {missing}")
        return

    # Ask user
    from PySide6.QtWidgets import QMessageBox
    pkg_list = ", ".join(packages)
    reply = QMessageBox.question(
        None,
        "VenvStudio — Missing Packages",
        f"VenvStudio needs the following system packages to work properly:\n\n"
        f"  {pkg_list}\n\n"
        f"Would you like to install them now?\n"
        f"(Root/admin password will be required)",
        QMessageBox.Yes | QMessageBox.No,
    )

    if reply != QMessageBox.Yes:
        logger.info("User declined package installation")
        return

    # Try pkexec (graphical sudo), then sudo
    sudo_methods = [
        ["pkexec"] + install_cmd,
        ["sudo"] + install_cmd,
    ]

    for cmd in sudo_methods:
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                logger.info(f"Successfully installed: {pkg_list}")
                config.set("linux_deps_checked", True)
                QMessageBox.information(
                    None,
                    "VenvStudio",
                    f"✅ Packages installed successfully:\n{pkg_list}",
                )
                return
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            continue

    logger.error("Failed to install packages")
    QMessageBox.warning(
        None,
        "VenvStudio",
        f"Could not install packages automatically.\n\n"
        f"Please install manually:\n"
        f"  sudo {' '.join(install_cmd)}",
    )


def _detect_distro() -> str:
    """Detect Linux distro family from /etc/os-release."""
    import shutil
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
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
    if shutil.which("apt"):
        return "debian"
    if shutil.which("dnf"):
        return "fedora"
    if shutil.which("pacman"):
        return "arch"
    if shutil.which("zypper"):
        return "suse"
    return "unknown"


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
        from PySide6.QtGui import QFont

        # Suppress noisy QFont::setPointSize warnings (caused by px-based stylesheets)
        def _qt_message_handler(mode, context, message):
            if "QFont::setPointSize" in message:
                return  # suppress
            if mode == QtMsgType.QtWarningMsg:
                print(f"[Qt Warning] {message}")
            elif mode == QtMsgType.QtCriticalMsg:
                print(f"[Qt Critical] {message}")
            elif mode == QtMsgType.QtFatalMsg:
                print(f"[Qt Fatal] {message}")

        qInstallMessageHandler(_qt_message_handler)

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager
        from src.utils.i18n import set_language
        from src.utils.logger import setup_logging

        # Initialize logging
        logger = setup_logging()
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

        # Load language setting before creating UI
        config = ConfigManager()
        lang = config.get("language", "en")
        set_language(lang)
        logger.info(f"Language: {lang}")

        # High DPI support
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("VenvStudio")

        # Set default font
        font = QFont("Segoe UI", 10)
        font.setStyleHint(QFont.SansSerif)
        app.setFont(font)

        window = MainWindow()

        # ── Linux: check pip/venv on first launch ──
        if sys.platform == "linux":
            _check_and_install_linux_deps(app, config, logger)

        window.show()

        sys.exit(app.exec())

    except Exception as e:
        # EXE'de hata olursa göster
        error_msg = f"VenvStudio Başlatma Hatası:\n\n{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)

        # Eğer GUI henüz başlamadıysa, basit bir hata penceresi göster
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "VenvStudio - Hata", error_msg)
        except Exception:
            pass

        # Konsol açıksa kullanıcı okuyabilsin
        if getattr(sys, 'frozen', False):
            input("\nDevam etmek için Enter'a bas...")
        sys.exit(1)


if __name__ == "__main__":
    main()
