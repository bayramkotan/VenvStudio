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
        # Get Python version for versioned packages (e.g. python3.13-venv, python3.13-pip)
        py_ver = ""
        try:
            r = subprocess.run(
                [python_exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=5,
            )
            py_ver = r.stdout.strip()
        except Exception:
            pass

        if "pip" in missing:
            if py_ver:
                packages.append(f"python{py_ver}-pip")  # e.g. python3.13-pip
            packages.append("python3-pip")
        if "venv" in missing:
            if py_ver:
                packages.append(f"python{py_ver}-venv")  # e.g. python3.13-venv
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


def _ensure_single_instance():
    """Prevent multiple instances using QLocalServer/QLocalSocket."""
    from PySide6.QtNetwork import QLocalSocket, QLocalServer
    socket = QLocalSocket()
    socket.connectToServer("VenvStudio_SingleInstance")
    if socket.waitForConnected(500):
        # Already running — send raise signal and exit
        socket.write(b"raise")
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return None  # Signal to exit
    # Not running — start server
    server = QLocalServer()
    QLocalServer.removeServer("VenvStudio_SingleInstance")
    server.listen("VenvStudio_SingleInstance")
    return server  # Keep reference alive


def _detect_linux_distro() -> str:
    """Return a short distro family name: fedora, suse, ubuntu, debian, arch, etc.
    Reads /etc/os-release. Falls back to 'linux' if unknown.
    """
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            data = f.read()
    except Exception:
        return "linux"

    info = {}
    for line in data.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip()] = v.strip().strip('"').strip("'")

    like = (info.get("ID_LIKE", "") + " " + info.get("ID", "")).lower()

    if "fedora" in like or "rhel" in like or "centos" in like:
        return "fedora"
    if "suse" in like or "opensuse" in like:
        return "suse"
    if "ubuntu" in like or "debian" in like or "mint" in like or "pardus" in like:
        return "debian"
    if "arch" in like or "manjaro" in like or "cachyos" in like:
        return "arch"
    if "alpine" in like:
        return "alpine"
    return info.get("ID", "linux") or "linux"


def _emoji_install_command_for_distro(distro: str) -> str:
    """Return the shell command to install an emoji font for the given distro."""
    commands = {
        "fedora":  "sudo dnf install -y google-noto-color-emoji-fonts",
        "suse":    "sudo zypper install -y noto-coloremoji-fonts",
        "debian":  "sudo apt install -y fonts-noto-color-emoji",
        "arch":    "sudo pacman -S --noconfirm noto-fonts-emoji",
        "alpine":  "sudo apk add font-noto-emoji",
    }
    return commands.get(distro, "Install a package named 'noto-color-emoji' or 'fonts-noto-color-emoji'")


def _check_qt_xcb_deps():
    """Check and install Qt xcb platform plugin dependencies on Linux."""
    import subprocess, shutil

    if sys.platform != "linux":
        return

    # Quick test: can Qt load xcb platform?
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "from PySide6.QtWidgets import QApplication; "
             "import sys; sys.argv=['t']; "
             "a=QApplication.instance() or QApplication(sys.argv)"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "QT_QPA_PLATFORM": "xcb",
                 "DISPLAY": os.environ.get("DISPLAY", ":0")}
        )
        if result.returncode == 0:
            return  # Qt xcb works fine
        # Check if it's actually an xcb error
        err = result.stderr + result.stdout
        if "xcb" not in err.lower() and "platform plugin" not in err.lower():
            return
    except Exception:
        return

    # Detect distro and build package list
    distro = _detect_distro()
    pkg_map = {
        "debian": [
            "libxcb-xinerama0", "libxcb-cursor0", "libxcb-icccm4",
            "libxcb-image0", "libxcb-keysyms1", "libxcb-render-util0",
            "libxcb-shape0", "libxkbcommon-x11-0",
        ],
        "arch": [
            "xcb-util-cursor", "xcb-util-icccm", "xcb-util-image",
            "xcb-util-keysyms", "xcb-util-renderutil", "libxkbcommon-x11",
        ],
        "fedora": [
            "libxcb", "xcb-util-cursor", "xcb-util-icccm", "xcb-util-image",
            "xcb-util-keysyms", "xcb-util-renderutil", "libxkbcommon-x11",
        ],
        "suse": [
            "libxcb-cursor0", "libxcb-icccm4", "libxcb-image0",
            "libxcb-keysyms1", "libxcb-render-util0", "libxkbcommon-x11-0",
        ],
    }
    install_cmd_map = {
        "debian": ["apt", "install", "-y"],
        "arch":   ["pacman", "-S", "--noconfirm", "--needed"],
        "fedora": ["dnf", "install", "-y"],
        "suse":   ["zypper", "--non-interactive", "install"],
    }

    packages = pkg_map.get(distro)
    base_cmd = install_cmd_map.get(distro)
    if not packages or not base_cmd:
        return

    # Try to show a dialog — if Qt can't start, fall back to terminal prompt
    pkg_str = "  " + "\n  ".join(packages)
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        _app = QApplication.instance() or QApplication(sys.argv)
        reply = QMessageBox.question(
            None,
            "VenvStudio — Missing Qt Dependencies",
            f"VenvStudio needs system libraries to display its window:\n\n"
            f"{pkg_str}\n\n"
            f"Install now? (admin password required)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
    except Exception:
        # Qt can't even show a dialog — ask in terminal
        print("\nVenvStudio needs Qt xcb libraries:")
        print(pkg_str)
        ans = input("\nInstall now? [Y/n]: ").strip().lower()
        if ans not in ("", "y", "yes"):
            return

    # Install via pkexec or sudo
    full_cmd = base_cmd + packages
    for prefix in (["pkexec"], ["sudo"]):
        try:
            r = subprocess.run(prefix + full_cmd,
                               capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                print("✅ Qt dependencies installed. Restarting VenvStudio...")
                # Restart
                os.execv(sys.executable, [sys.executable] + sys.argv)
                return
        except FileNotFoundError:
            continue
        except Exception:
            continue

    print("Could not install automatically. Run manually:")
    print(f"  sudo {' '.join(full_cmd)}")


def main():
    logger = None
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
        from PySide6.QtGui import QFont

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager
        from src.utils.i18n import set_language
        from src.utils.logger import setup_logging, get_logger

        # ── Initialize logging FIRST ──
        logger = setup_logging()
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

        # ── Qt message handler → route to logger ──
        qt_log = get_logger("venvstudio.qt")

        def _qt_message_handler(mode, context, message):
            # Suppress noisy QFont::setPointSize warnings (caused by px-based stylesheets)
            if "QFont::setPointSize" in message:
                return
            # Suppress QWindowsWindow::setGeometry positioning warnings
            if "QWindowsWindow::setGeometry" in message:
                qt_log.debug(f"Qt geometry: {message}")
                return

            if mode == QtMsgType.QtDebugMsg:
                qt_log.debug(f"Qt: {message}")
            elif mode == QtMsgType.QtInfoMsg:
                qt_log.info(f"Qt: {message}")
            elif mode == QtMsgType.QtWarningMsg:
                qt_log.warning(f"Qt: {message}")
            elif mode == QtMsgType.QtCriticalMsg:
                qt_log.error(f"Qt CRITICAL: {message}")
            elif mode == QtMsgType.QtFatalMsg:
                qt_log.critical(f"Qt FATAL: {message}")

        # Install handler early — will be re-installed after QApplication
        qInstallMessageHandler(_qt_message_handler)

        # ── GLOBAL EXCEPTION HOOK ─────────────────────────────────────────
        # Qt event loop (resize/move/paint) sometimes swallows Python exceptions
        # silently in release builds. This hook ensures every traceback hits
        # the log AND the console so crashes can be diagnosed.
        def _global_excepthook(exc_type, exc_value, exc_tb):
            # B180/B181 yan etki: Python 3.13 + PySide6 6.10.2 kombinasyonunda
            # `traceback.format_exception` ve `traceback.format_tb` shibokensupport
            # signature loader ile sonsuz döngüye giriyor (RecursionError).
            # Manuel olarak frame frame walk yapmak güvenli — ast import etmiyor.
            type_name = getattr(exc_type, "__name__", str(exc_type))
            try:
                frames = []
                _tb = exc_tb
                _depth = 0
                while _tb is not None and _depth < 50:
                    _f = _tb.tb_frame
                    frames.append(
                        f'  File "{_f.f_code.co_filename}", line {_tb.tb_lineno}, in {_f.f_code.co_name}'
                    )
                    _tb = _tb.tb_next
                    _depth += 1
                tb_text = "Traceback (most recent call last):\n" + "\n".join(frames) + f"\n{type_name}: {exc_value}\n"
            except Exception as _fe:
                tb_text = f"{type_name}: {exc_value}\n(manual tb walk failed: {_fe})\n"
            full_msg = (
                f"\n{'='*70}\n"
                f"UNHANDLED EXCEPTION — {type_name}: {exc_value}\n"
                f"{'='*70}\n{tb_text}{'='*70}\n"
            )
            try:
                logger.critical(f"UNHANDLED: {type_name}: {exc_value}\n{tb_text}")
            except Exception:
                pass
            # Always also print to stderr (visible in terminal / debug EXE)
            print(full_msg, file=sys.stderr, flush=True)
            # Write crash report
            try:
                from src.utils.logger import _write_crash_report, get_log_dir
                _write_crash_report(get_log_dir(), tb_text, context="runtime")
            except Exception:
                pass

        sys.excepthook = _global_excepthook

        # PyQt/PySide does NOT call sys.excepthook for exceptions raised inside
        # Qt slots/events by default — install a threading hook and also
        # wrap Qt's exception path via custom event filter if needed.
        try:
            import threading
            threading.excepthook = lambda args: _global_excepthook(
                args.exc_type, args.exc_value, args.exc_traceback
            )
        except Exception:
            pass

        # ── Load config and language ──
        config = ConfigManager()
        lang = config.get("language", "en")
        set_language(lang)
        logger.info(f"Language: {lang}")

        # ── Linux: check Qt xcb dependencies before creating QApplication ──
        if sys.platform == "linux":
            _check_qt_xcb_deps()

        # ── High DPI support ──
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        # Re-install after QApplication so startup font warnings are also suppressed
        qInstallMessageHandler(_qt_message_handler)
        app.setApplicationName(APP_NAME)

        # ── B155: Allow Ctrl+C / Ctrl+D to close VenvStudio when launched from
        # a terminal. Qt's event loop normally blocks Python's signal handling,
        # so we (a) wire SIGINT/SIGTERM to QApplication.quit and (b) wake the
        # interpreter periodically so incoming signals actually get processed.
        import signal as _signal
        try:
            _signal.signal(_signal.SIGINT,  lambda *_: app.quit())
            _signal.signal(_signal.SIGTERM, lambda *_: app.quit())
        except (ValueError, OSError):
            # Not in main thread (e.g. embedded) — skip silently
            pass
        # Noop timer forces Qt back to the Python interpreter every 200ms so
        # pending signals (Ctrl+C) are delivered. Without this the handler may
        # only run after the next UI event.
        from PySide6.QtCore import QTimer as _QTimer
        _sigtimer = _QTimer()
        _sigtimer.start(200)
        _sigtimer.timeout.connect(lambda: None)

        # ── Single instance check ──
        _single_instance_server = _ensure_single_instance()
        if _single_instance_server is None:
            logger.info("Another instance is already running — exiting")
            sys.exit(0)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("VenvStudio")

        # ── Log screen info after QApplication creation ──
        for screen in app.screens():
            geo = screen.geometry()
            logger.info(
                f"Screen: {screen.name()} {geo.width()}x{geo.height()} "
                f"@{screen.devicePixelRatio()}x DPI={screen.logicalDotsPerInch():.0f}"
            )

        # ── Font setup with emoji fallback ─────────────────────────────
        # Detect the best UI font (Segoe UI on Windows, Inter/Cantarell on Linux
        # if available, Helvetica on macOS) and make sure at least ONE emoji
        # font is in the fallback chain so icons like 🔄 ⭐ 📁 render.
        from PySide6.QtGui import QFontDatabase

        # QFontDatabase methods are static since Qt 6 — no instance needed.
        try:
            available_fonts = set(QFontDatabase.families())
        except Exception:
            available_fonts = set()

        # Pick the best UI font for the platform
        if sys.platform == "darwin":
            ui_font_candidates = ["SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"]
        elif sys.platform == "win32":
            ui_font_candidates = ["Segoe UI Variable Display", "Segoe UI", "Tahoma", "Arial"]
        else:  # linux / bsd
            ui_font_candidates = ["Inter", "Cantarell", "Ubuntu", "Noto Sans",
                                  "DejaVu Sans", "Liberation Sans", "Arial"]

        ui_font_family = None
        for candidate in ui_font_candidates:
            if not available_fonts or candidate in available_fonts:
                ui_font_family = candidate
                break
        ui_font_family = ui_font_family or "sans-serif"

        # Detect an emoji-capable font
        emoji_font_candidates = [
            "Noto Color Emoji",      # Linux standard (Fedora/openSUSE may lack it)
            "Segoe UI Emoji",        # Windows
            "Apple Color Emoji",     # macOS
            "Twemoji Mozilla",       # Firefox / older distros
            "EmojiOne Color",        # Community
            "JoyPixels",             # Community
            "Symbola",               # Monochrome unicode fallback
            "DejaVu Sans",           # Basic unicode (last resort, no color)
        ]
        emoji_font_family = None
        for candidate in emoji_font_candidates:
            if not available_fonts or candidate in available_fonts:
                emoji_font_family = candidate
                break

        if not emoji_font_family:
            logger.warning(
                "No emoji-capable font detected. Emoji (🔄 ⭐ 📁) may render as boxes. "
                "Install 'noto-fonts-emoji' (Linux) or equivalent."
            )
            # Still set Symbola as safe fallback target
            emoji_font_family = "Symbola"

        logger.info(f"UI font: {ui_font_family}  |  Emoji font: {emoji_font_family}")

        # Qt font substitution: when the primary font is missing a glyph, Qt
        # walks the substitute chain. Register emoji font as substitute for
        # the main UI font so icons in labels/buttons fall back correctly.
        try:
            QFont.insertSubstitution(ui_font_family, emoji_font_family)
            # Also register common fallbacks so Qt can find SOMETHING for any glyph
            for fb in ("DejaVu Sans", "Noto Sans"):
                if fb != emoji_font_family and (not available_fonts or fb in available_fonts):
                    QFont.insertSubstitution(ui_font_family, fb)
        except Exception as _e:
            logger.debug(f"Font substitution failed: {_e}")

        # Build application font
        font = QFont(ui_font_family, 10)
        font.setStyleHint(QFont.SansSerif)
        # Use PreferDefault → Qt applies substitutions; PreferMatch would skip them
        try:
            font.setStyleStrategy(QFont.PreferDefault)
        except Exception:
            pass
        app.setFont(font)

        # ── Linux-only: show a friendly warning dialog if no emoji font ──
        if sys.platform == "linux" and not any(
            f in available_fonts for f in (
                "Noto Color Emoji", "Twemoji Mozilla", "EmojiOne Color",
                "JoyPixels", "Symbola"
            )
        ):
            try:
                distro = _detect_linux_distro()
                install_cmd = _emoji_install_command_for_distro(distro)
                show_emoji = config.get("show_emoji_missing_warning", True)
                if show_emoji and install_cmd:
                    from PySide6.QtWidgets import QMessageBox
                    box = QMessageBox(
                        QMessageBox.Warning,
                        "Emoji Font Missing",
                        "VenvStudio uses emoji characters (🔄 ⭐ 📁 🐍) for icons, "
                        "but no emoji font was detected on your system.\n\n"
                        f"Install now? (requires admin password)\n\n"
                        f"Command: {install_cmd}",
                    )
                    yes_btn = box.addButton("Yes", QMessageBox.AcceptRole)
                    no_btn = box.addButton("No", QMessageBox.RejectRole)
                    box.exec()
                    clicked = box.clickedButton()
                    if clicked is yes_btn:
                        # Run install command
                        try:
                            import subprocess as _sp
                            _sp.Popen(
                                ["bash", "-c", install_cmd],
                                start_new_session=True,
                            )
                        except Exception as _ie:
                            logger.warning(f"Emoji font install failed: {_ie}")
                        config.set("show_emoji_missing_warning", False)
                    elif clicked is no_btn:
                        # Don't ask again
                        config.set("show_emoji_missing_warning", False)
            except Exception as _e:
                logger.debug(f"Emoji warning dialog failed: {_e}")

        logger.info("Creating MainWindow...")
        window = MainWindow()
        logger.info("MainWindow created successfully")

        # ── Linux: check pip/venv on first launch ──
        if sys.platform == "linux":
            _check_and_install_linux_deps(app, config, logger)

        window.show()
        logger.info("MainWindow shown — entering event loop")

        # ── Raise window when another instance tries to start ──
        def _on_new_connection():
            conn = _single_instance_server.nextPendingConnection()
            if conn:
                conn.waitForReadyRead(300)
                conn.disconnectFromServer()
            window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
            window.raise_()
            window.activateWindow()
        _single_instance_server.newConnection.connect(_on_new_connection)

        exit_code = app.exec()
        logger.info(f"Application exiting with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        # ── Startup crash — log + show error ──
        error_msg = f"VenvStudio Startup Error:\n\n{type(e).__name__}: {e}\n\n{traceback.format_exc()}"

        if logger:
            logger.critical(f"STARTUP CRASH:\n{error_msg}")
        else:
            print(error_msg, file=sys.stderr)

        # Write crash report even if logger failed
        try:
            from src.utils.logger import _write_crash_report, get_log_dir
            _write_crash_report(get_log_dir(), traceback.format_exc(), context="startup")
        except Exception:
            pass

        # Show error dialog
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "VenvStudio — Startup Error", error_msg)
        except Exception:
            pass

        # Konsol açıksa kullanıcı okuyabilsin (sadece debug/console build)
        if getattr(sys, 'frozen', False) and not getattr(sys, 'frozen_windowed', True):
            input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
