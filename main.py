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

# ── B18 diagnostic: faulthandler for the CI AppImage startup hang ──
# CI's smoke-test already sets PYTHONFAULTHANDLER=1, but that env var did
# NOT produce a stack trace on the frozen (PyInstaller) build's SIGABRT --
# only "the monitored command dumped core" showed up, no Python frames.
# faulthandler.enable() called explicitly in code (rather than relying on
# the env var being honoured by the embedded runtime) is more reliable in
# frozen builds. dump_traceback_later() is a second, independent safety
# net: it fires from its own watchdog thread on a plain timer, so it dumps
# every thread's current frame even if the hang is inside a C-level Qt/
# glib loop that never lets a signal (SIGABRT included) get delivered.
# 25s is chosen to land just before the smoke-test's own 30s `timeout`,
# so the dump appears in the log before the process gets killed.
import faulthandler

# N89 (Bayram, 2026-09-02): a windowed PyInstaller build has NO sys.stderr.
#
# faulthandler.enable() writes there by default and raises when it is None:
#
#     RuntimeError: sys.stderr is None
#
# The packaged VenvStudio.exe therefore died on this line before reaching a
# single line of application code, while `vs` from a terminal was fine --
# which is why it went unnoticed. A diagnostic must never be the reason the
# program will not start.
#
# Writing to a FILE instead is also strictly better here: in a windowed build
# nobody could have read stderr anyway, so the crash dumps this was added to
# capture were being thrown away even when it did work.
_fh_file = None
try:
    if sys.stderr is not None:
        faulthandler.enable()
    else:
        import tempfile as _tf
        from pathlib import Path as _P
        try:
            # There is no get_log_dir(); the log directory is derived
            # from the config directory (logger.py builds it the same
            # way). Falling back to temp keeps this working even if the
            # config directory cannot be resolved this early.
            from src.utils.platform_utils import get_config_dir as _gcd
            _dir = _P(_gcd()) / "logs"
        except Exception:
            _dir = _P(_tf.gettempdir()) / "VenvStudio"
        _dir.mkdir(parents=True, exist_ok=True)
        # Kept open deliberately: faulthandler writes to this handle when the
        # process is already dying, so it must outlive this block.
        _fh_file = open(_dir / "faulthandler.log", "a", encoding="utf-8")
        faulthandler.enable(file=_fh_file)
except Exception:
    # No diagnostics is a small loss. Not starting is a total one.
    pass

# The watchdog exists for CI's 30s smoke test. On a user's machine it would
# dump every thread 25 seconds in for no reason, so it is armed only when CI
# asks for it.
if os.environ.get("VENVSTUDIO_WATCHDOG") or os.environ.get("CI"):
    try:
        faulthandler.dump_traceback_later(25, exit=False)
    except Exception:
        pass

# ── Frozen-mode multiprocessing safety (fixes AppImage startup hang) ──
# In a PyInstaller --onedir/AppImage build, sys.executable is VenvStudio
# itself, not a python interpreter. With the default Linux "fork" start
# method, any library that touches multiprocessing (or its resource_tracker
# / semaphore helpers) can cause the frozen executable to re-launch itself.
# Each relaunch re-enters main(), opens another QLocalSocket to the single-
# instance server, spawns more Qt threads, and the whole thing snowballs into
# dozens of processes busy-looping on read() — which is exactly the hang we
# saw (90+ PIDs, 40k+ read() syscalls) before the window ever appears.
#
# freeze_support() MUST run before anything else so a child process started
# by multiprocessing exits immediately instead of falling through to our GUI
# main(). Forcing the "spawn" start method makes child processes start clean
# (re-import, hit freeze_support, exit) instead of fork-cloning all the live
# Qt/thread state. Together these stop the relaunch storm.
multiprocessing.freeze_support()
try:
    if multiprocessing.get_start_method(allow_none=True) != "spawn":
        multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    # Start method already fixed by something else — safe to ignore.
    pass

# Hard guard: if this interpreter was launched *as* a multiprocessing child
# (resource tracker, semaphore tracker, spawned worker, etc.), bail out now
# so we never build a second GUI / single-instance socket from a child.
if getattr(sys, "frozen", False):
    _mp_child_markers = (
        "--multiprocessing-fork",
        "tracker",            # resource_tracker / semaphore_tracker
        "from multiprocessing",
    )
    _argv_blob = " ".join(sys.argv[1:])
    if any(_m in _argv_blob for _m in _mp_child_markers):
        # Let multiprocessing's own machinery handle it, then stop.
        try:
            multiprocessing.freeze_support()
        finally:
            sys.exit(0)

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

    # Find a REAL python interpreter for the `-m pip` / `-m venv` probes
    # below. We must never fall back to sys.executable in a frozen build:
    # there sys.executable is the VenvStudio binary, so `[sys.executable,
    # "-m", "pip", ...]` re-launches the GUI instead of running pip — the
    # same self-replicating relaunch that froze startup. If no system python
    # is found while frozen, skip the probe entirely rather than risk it.
    python_exe = shutil.which("python3") or shutil.which("python")
    if not python_exe:
        if getattr(sys, "frozen", False):
            return
        python_exe = sys.executable
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

    # ── CRITICAL: never run in a frozen build ──
    # This function probes Qt by launching `sys.executable -c "<python>"`.
    # In a PyInstaller/AppImage build sys.executable is the VenvStudio
    # binary itself (NOT a python interpreter), so passing "-c <code>" does
    # not run that snippet — it just re-launches the whole GUI, which
    # re-enters main(), which calls this probe again... a self-replicating
    # fork bomb. (Observed: dozens of
    #   /tmp/.mount_*/usr/bin/VenvStudio -c "from PySide6.QtWidgets import ..."
    # processes spawning every second until the machine froze.) The AppImage
    # already bundles its own Qt + xcb plugins, so this host-dependency probe
    # is meaningless when frozen. Skip it entirely.
    if getattr(sys, "frozen", False):
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


# N92 (Bayram, 2026-09-03): setup_application_font now lives in
# platform_utils, because THIS FILE IS NOT IN THE PyPI PACKAGE.
#
# src/main.py called it as `from main import setup_application_font`, which
# works from a source checkout and fails on every installed copy with
# "No module named 'main'" -- so the font fix reached nobody who had used
# pip. Eyup's log caught it. platform_utils ships with the package, so both
# entry points can reach it there.
from src.utils.platform_utils import (
    setup_application_font,
    install_qt_message_filter,
)

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

        # ── Version-based cache invalidation (B187 follow-up) ──
        # On upgrade, drop env_cache.json so old buggy entries (e.g. from the
        # pre-v1.4.96 pip-list race) don't survive into the new version.
        try:
            from src.utils.platform_utils import get_config_dir
            _cfg_dir = get_config_dir()
            _marker = _cfg_dir / ".venvstudio_last_version"
            _cache_file = _cfg_dir / "env_cache.json"
            _prev = ""
            if _marker.exists():
                try:
                    _prev = _marker.read_text(encoding="utf-8").strip()
                except Exception:
                    _prev = ""
            if _prev != APP_VERSION:
                if _cache_file.exists():
                    try:
                        _cache_file.unlink()
                        logger.info(
                            f"Version change detected ({_prev or '<none>'} -> {APP_VERSION}) "
                            f"- removed stale env cache at {_cache_file}"
                        )
                    except Exception as _ce:
                        logger.warning(f"Could not remove stale cache: {_ce}")
                try:
                    _cfg_dir.mkdir(parents=True, exist_ok=True)
                    _marker.write_text(APP_VERSION, encoding="utf-8")
                except Exception as _ve:
                    logger.warning(f"Could not write version marker: {_ve}")
        except Exception as _e:
            try:
                logger.warning(f"Version-based cache invalidation skipped: {_e}")
            except Exception:
                pass

        # N93 (Bayram, 2026-09-03): the handler lives in platform_utils now,
        # because src/main.py never installed one and therefore never got
        # this filtering. That is the whole reason the setPointSize warning
        # appeared for installed copies and not from a source checkout: the
        # warning happens on BOTH, and only this file was suppressing it.
        install_qt_message_filter()


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

        available_fonts = setup_application_font(app, logger)

        # ── Linux-only: show a friendly warning dialog if no emoji font ──
        # Skip entirely in a frozen build: the AppImage bundles Noto Color
        # Emoji and installs it to the user font dir on launch, so the host
        # doesn't need its own emoji font. The QFontDatabase check here also
        # runs before fontconfig has fully picked up the just-installed font,
        # so it would false-positive and nag the user about a font that IS
        # actually present. Only prompt in a normal (pip/source) run.
        if (not getattr(sys, "frozen", False)) and sys.platform == "linux" and not any(
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

        # B18 diagnostic: the watchdog's job was to catch a hang BEFORE
        # we ever reach the event loop (that's the actual CI failure mode
        # -- startup never gets here at all). Once we're about to call
        # app.exec(), sitting inside it is the correct, healthy state for
        # as long as the app runs -- not a hang. Without cancelling here,
        # the 25s timer fires unconditionally on every run, healthy or
        # not, and always reports "stuck in app.exec()" (confirmed
        # 2026-08-12: fired on a normal, responsive session where the
        # user was actively switching pages).
        try:
            faulthandler.cancel_dump_traceback_later()
        except Exception:
            pass

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
