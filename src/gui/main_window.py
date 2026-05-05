"""
VenvStudio - Main Application Window
Modern sidebar-based layout with environment management and package panel
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog,
    QStackedWidget, QInputDialog, QApplication, QProgressDialog,
    QMenu, QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QAction, QColor

from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.gui.styles import get_theme
# Heavy GUI modules imported lazily in _setup_ui to speed up startup
from src.utils.platform_utils import (
    get_activate_command, open_terminal_at, get_platform,
)
from src.utils.constants import APP_NAME, APP_VERSION, UI_TOOLTIPS
from src.utils.i18n import tr


class SidebarButton(QPushButton):
    """Custom sidebar navigation button."""

    def __init__(self, text, icon_text="", parent=None):
        display = f"  {icon_text}  {text}" if icon_text else f"  {text}"
        super().__init__(display, parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)




class CloneWorker(QThread):
    """Worker thread for cloning environments with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, source, target):
        super().__init__()
        self.venv_manager = venv_manager
        self.source = source
        self.target = target
        self._cancelled = False

    def run(self):
        success, msg = self.venv_manager.clone_venv(
            self.source, self.target, callback=self._on_progress
        )
        if self._cancelled:
            import shutil
            target_path = self.venv_manager.base_dir / self.target
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            self.finished.emit(False, "Clone cancelled by user")
        else:
            self.finished.emit(success, msg)

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True


class EnvDetailWorker(QThread):
    """Background worker to load env details only for envs missing cache.
    Uses ThreadPoolExecutor so large envs don't block each other.
    """
    env_detail_ready = Signal(int, str, int, str)  # row, python_ver, pkg_count, size
    all_done = Signal()

    def __init__(self, venv_manager, env_names):
        super().__init__()
        self.venv_manager = venv_manager
        self.env_names = env_names

    def _fetch_one(self, args):
        i, name = args
        venv_path = self.venv_manager.base_dir / name
        # Skip marker-based envs — already resolved by list_venvs_fast
        marker = venv_path / ".venvstudio_env"
        if marker.exists():
            return None
        cached = self.venv_manager._read_cache(venv_path)
        if cached:
            return None  # already loaded by list_venvs_fast
        info = self.venv_manager.get_venv_info(name, use_cache=False)
        if info:
            return (i, info.python_version, info.package_count, info.size)
        return None

    def run(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        args = list(enumerate(self.env_names))
        # Max 4 threads — avoids hammering disk with too many simultaneous pip list calls
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._fetch_one, a): a for a in args}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    self.env_detail_ready.emit(*result)
        self.all_done.emit()


class DeleteWorker(QThread):
    """Worker thread for deleting environments with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, name, env_path=None, env_type="venv"):
        super().__init__()
        self.venv_manager = venv_manager
        self.name = name
        self.env_path = env_path
        self.env_type = env_type

    def run(self):
        success, msg = self.venv_manager.delete_venv(
            self.name, callback=self.progress.emit,
            env_path=self.env_path, env_type=self.env_type
        )
        self.finished.emit(success, msg)


class RenameOnlyWorker(QThread):
    """Worker thread for fast rename — folder rename only."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, old_name, new_name):
        super().__init__()
        self.venv_manager = venv_manager
        self.old_name = old_name
        self.new_name = new_name

    def run(self):
        self.progress.emit(f"Renaming '{self.old_name}' → '{self.new_name}'...")
        success, msg = self.venv_manager.rename_venv(self.old_name, self.new_name)
        self.finished.emit(success, msg)


class RenameFullWorker(QThread):
    """Worker thread for full rename — clone + delete with same packages."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, old_name, new_name):
        super().__init__()
        self.venv_manager = venv_manager
        self.old_name = old_name
        self.new_name = new_name

    def run(self):
        success, msg = self.venv_manager.rename_full_venv(
            self.old_name, self.new_name, callback=self.progress.emit
        )
        self.finished.emit(success, msg)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        # ── Logger — must be first so all subsequent calls are covered ──
        from src.utils.logger import get_logger
        self._log = get_logger("venvstudio.main_window")
        self._log.info("MainWindow.__init__ started")

        self.config = ConfigManager()
        # B184 v2: legacy "light" config values get auto-upgraded to a real
        # theme id. Older builds saved bare "light" which the styles module
        # silently treated as dark.
        try:
            _t = self.config.get("theme", "")
            if _t == "light":
                self.config.set("theme", "light-latte")
                self._log.info("migrated config theme: 'light' → 'light-latte'")
        except Exception as _e:
            self._log.debug(f"theme migration skipped: {_e}")
        self.venv_manager = VenvManager(self.config.get_venv_base_dir())
        self.selected_env = None
        self._applying_theme = False  # Guard against re-entrant / screen-change crashes

        self._setup_window()
        self._setup_menubar()
        self._setup_ui()
        self._apply_theme()

        # ── Screen change safety: re-apply theme when moving between monitors ──
        self._connect_screen_changed()

        self.venv_manager.sync_cache_with_disk()
        self.venv_manager.ensure_pipx_env()
        self._apply_linux_emoji_fix()
        self._check_linux_venv_module()
        self._refresh_env_list()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self._open_default_env)

        if self.config.get("check_updates", False):
            QTimer.singleShot(3000, self._auto_check_update)

        self._log.info("MainWindow.__init__ complete")


    def _auto_check_update(self):
        """Silently check for updates on startup — runs in background thread."""
        class _UpdateWorker(QThread):
            update_found = Signal(dict)
            def run(self):
                try:
                    from src.core.updater import check_for_update
                    result = check_for_update()
                    if result.get("update_available"):
                        self.update_found.emit(result)
                except Exception:
                    pass

        self._update_worker = _UpdateWorker()
        self._update_worker.update_found.connect(self._on_update_found)
        self._update_worker.start()

    def _on_update_found(self, result: dict):
        """Called on main thread when an update is available."""
        reply = QMessageBox.information(
            self, "🆕 Update Available",
            f"VenvStudio v{result['latest_version']} is available!\n"
            f"You have v{result['current_version']}.\n\n"
            f"Update: pip install --upgrade venvstudio\n\n"
            f"Open download page?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import webbrowser
            webbrowser.open(result["release_url"])

    def _c(self) -> dict:
        """Return current theme color palette with font hierarchy."""
        from src.gui.styles import get_colors
        return get_colors(
            self.config.get("theme", "dark"),
            self.config.get("font_secondary_size", 13) or self.config.get("font_size", 13),
            self.config.get("font_primary_size", 22),
            self.config.get("font_tertiary_size", 11),
        )

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(900, 600)

        width  = self.config.get("window_width",  1100)
        height = self.config.get("window_height", 700)
        saved_x = self.config.get("window_x", None)
        saved_y = self.config.get("window_y", None)

        # Find the screen that contains the saved position, fallback to primary
        target_screen = None
        if saved_x is not None and saved_y is not None:
            for scr in QApplication.screens():
                if scr.geometry().contains(saved_x + width // 2, saved_y + height // 2):
                    target_screen = scr
                    break

        if target_screen is None:
            target_screen = QApplication.primaryScreen()

        avail = target_screen.availableGeometry()

        # Clamp size to available screen
        width  = min(width,  avail.width()  - 40)
        height = min(height, avail.height() - 40)
        self.resize(width, height)

        if saved_x is not None and saved_y is not None:
            # Clamp position so window is fully on screen
            x = max(avail.x(), min(saved_x, avail.x() + avail.width()  - width))
            y = max(avail.y(), min(saved_y, avail.y() + avail.height() - height))
            self.move(x, y)
        else:
            # First run — center on primary screen
            x = avail.x() + (avail.width()  - width)  // 2
            y = avail.y() + (avail.height() - height) // 2
            self.move(x, y)

    def _setup_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu(tr("file"))
        new_env_action = QAction(f"➕ &{tr('new_environment')}", self)
        new_env_action.setShortcut("Ctrl+N")
        new_env_action.triggered.connect(self._create_env)
        file_menu.addAction(new_env_action)
        file_menu.addSeparator()

        # ── Recent Environments submenu ───────────────────────────────────
        self._recent_menu = QMenu("🕐 Recent Environments", self)
        file_menu.addMenu(self._recent_menu)
        self._populate_recent_menu()
        file_menu.addSeparator()
        # ─────────────────────────────────────────────────────────────────

        quit_action = QAction(f"❌ {tr('quit')}", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu(tr("view"))
        refresh_action = QAction(f"🔄 {tr('refresh')}", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_env_list)
        view_menu.addAction(refresh_action)
        view_menu.addSeparator()
        dark_action = QAction(f"🌙 {tr('dark_theme')}", self)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(dark_action)
        light_action = QAction(f"☀️ {tr('light_theme')}", self)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(light_action)
        view_menu.addSeparator()
        settings_view_action = QAction(f"⚙️ {tr('settings')}", self)
        settings_view_action.triggered.connect(self._open_settings)
        view_menu.addAction(settings_view_action)

        tools_menu = menubar.addMenu("Tools")
        shortcut_action = QAction("🖥️ Create Desktop Shortcut", self)
        shortcut_action.triggered.connect(self._create_desktop_shortcut)
        tools_menu.addAction(shortcut_action)

        help_menu = menubar.addMenu(tr("help"))
        about_action = QAction(f"ℹ️ {tr('about')}", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        update_action = QAction("🔄 Check for Updates", self)
        update_action.triggered.connect(self._check_for_updates)
        help_menu.addAction(update_action)

        help_menu.addSeparator()

        github_action = QAction("⭐ GitHub Repository", self)
        github_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/bayramkotan/VenvStudio"))
        help_menu.addAction(github_action)

        pypi_action = QAction("📦 PyPI Page", self)
        pypi_action.triggered.connect(lambda: __import__("webbrowser").open("https://pypi.org/project/venvstudio/"))
        help_menu.addAction(pypi_action)

        issues_action = QAction("🐛 Report a Bug", self)
        issues_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/bayramkotan/VenvStudio/issues"))
        help_menu.addAction(issues_action)



    def _create_desktop_shortcut(self):
        """Create a desktop shortcut that runs 'venvstudio' command (pip-installed).
        If venvstudio is not found in PATH, installs it first via pip.
        No terminal window opens when the shortcut is launched.
        """
        import sys, os, shutil, platform, subprocess
        from PySide6.QtWidgets import QMessageBox, QProgressDialog
        from PySide6.QtCore import Qt

        system = platform.system()
        app_name = "VenvStudio"

        # ── Step 1: Find venvstudio executable ──────────────────────────────
        vs_exe = shutil.which("venvstudio")

        if not vs_exe:
            # Not in PATH — offer to install
            reply = QMessageBox.question(
                self, "VenvStudio Not Found",
                "⚠️  The 'venvstudio' command was not found in PATH.\n\n"
                "This usually means VenvStudio was not installed via pip.\n\n"
                "Install now with pip? (requires internet connection)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # Show progress
            prog = QProgressDialog("Installing VenvStudio via pip...", None, 0, 0, self)
            prog.setWindowTitle("Installing...")
            prog.setWindowModality(Qt.WindowModal)
            prog.show()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade",
                     "venvstudio", "--break-system-packages"],
                    capture_output=True, text=True, timeout=120
                )
                prog.close()
                if result.returncode != 0:
                    # Try without --break-system-packages
                    result2 = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", "venvstudio"],
                        capture_output=True, text=True, timeout=120
                    )
                    if result2.returncode != 0:
                        QMessageBox.critical(self, "Install Failed",
                            f"pip install failed:\n{result2.stderr[:500]}")
                        return
            except Exception as e:
                prog.close()
                QMessageBox.critical(self, "Error", str(e))
                return

            # Re-check
            vs_exe = shutil.which("venvstudio")
            if not vs_exe:
                # Try Scripts / bin path
                scripts_dir = os.path.join(os.path.dirname(sys.executable),
                                           "Scripts" if system == "Windows" else "bin")
                candidate = os.path.join(scripts_dir,
                                         "venvstudio.exe" if system == "Windows" else "venvstudio")
                if os.path.isfile(candidate):
                    vs_exe = candidate
                else:
                    QMessageBox.warning(self, "Not Found",
                        "Installed but 'venvstudio' still not found.\n"
                        f"Scripts dir: {scripts_dir}\n"
                        "Try adding it to PATH and running this again.")
                    return

        # ── Step 2: Create shortcut using vs_exe ────────────────────────────
        try:
            if system == "Windows":
                self._create_shortcut_windows(vs_exe, app_name)
            elif system == "Linux":
                self._create_shortcut_linux(vs_exe, app_name)
            elif system == "Darwin":
                self._create_shortcut_macos(vs_exe, app_name)
            else:
                QMessageBox.warning(self, "Unsupported",
                    f"Desktop shortcut not supported on {system}.")
                return

            QMessageBox.information(self, "Done",
                f"✅ Desktop shortcut created!\n\n"
                f"Command: {vs_exe}\n\n"
                "You can now launch VenvStudio from your desktop\n"
                "without opening a terminal.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create shortcut:\n{e}")

    def _create_shortcut_windows(self, vs_exe, app_name):
        """Create a .lnk on Windows Desktop using PowerShell."""
        import os, subprocess

        desktop = os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop"
        )
        lnk_path = os.path.join(desktop, f"{app_name}.lnk")
        scripts_dir = os.path.dirname(vs_exe)

        icon_candidate = os.path.join(scripts_dir, "venvstudio.ico")
        icon_line = f'$s.IconLocation = "{icon_candidate}";' if os.path.isfile(icon_candidate) else ""

        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s  = $ws.CreateShortcut("{lnk_path}"); '
            f'$s.TargetPath     = "{vs_exe}"; '
            f'$s.WorkingDirectory = "{scripts_dir}"; '
            f'$s.Description    = "VenvStudio — Python Virtual Environment Manager"; '
            f'{icon_line} '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, timeout=15, capture_output=True)


    def _create_shortcut_linux(self, vs_exe, app_name):
        """Create a .desktop file on Linux — Terminal=false."""
        import os, subprocess

        # Find icon
        icon_path = vs_exe  # fallback
        for candidate in [
            os.path.join(os.path.dirname(vs_exe), "..", "share", "pixmaps", "venvstudio.png"),
            os.path.expanduser("~/.local/share/icons/venvstudio.png"),
        ]:
            if os.path.isfile(candidate):
                icon_path = os.path.abspath(candidate)
                break

        content = (
            "[Desktop Entry]\n"
            "Version=1.0\n"
            f"Name={app_name}\n"
            "Comment=Python Virtual Environment Manager\n"
            f"Exec={vs_exe}\n"
            f"Icon={icon_path}\n"
            "Terminal=false\n"
            "Type=Application\n"
            "Categories=Development;\n"
            "StartupNotify=true\n"
        )

        # XDG applications dir
        apps_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(apps_dir, exist_ok=True)
        xdg_path = os.path.join(apps_dir, "venvstudio.desktop")
        with open(xdg_path, "w") as f:
            f.write(content)
        os.chmod(xdg_path, 0o755)

        # Desktop dir — try xdg-user-dir first, then fallbacks
        desktop_dir = None
        try:
            desktop_dir = subprocess.check_output(
                ["xdg-user-dir", "DESKTOP"], text=True, timeout=5
            ).strip()
        except Exception:
            pass
        if not desktop_dir or not os.path.isdir(desktop_dir):
            for d in [os.path.expanduser("~/Desktop"),
                      os.path.expanduser("~/Masaüstü")]:
                if os.path.isdir(d):
                    desktop_dir = d
                    break

        if desktop_dir and os.path.isdir(desktop_dir):
            dest = os.path.join(desktop_dir, "venvstudio.desktop")
            with open(dest, "w") as f:
                f.write(content)
            os.chmod(dest, 0o755)
            try:
                subprocess.run(["gio", "set", dest, "metadata::trusted", "true"],
                               timeout=5, capture_output=True)
            except Exception:
                pass

    def _create_shortcut_macos(self, vs_exe, app_name):
        """Create a .command launcher on macOS Desktop."""
        import os, stat
        script = os.path.expanduser(f"~/Desktop/{app_name}.command")
        with open(script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'"{vs_exe}"\n')
        os.chmod(script, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

    def _populate_recent_menu(self):
        """Rebuild the Recent Environments submenu from recent_envs.json."""
        self._recent_menu.clear()
        try:
            from src.core.recent_envs import RecentEnvsManager
            mgr = RecentEnvsManager()
            entries = mgr.load()
        except Exception:
            entries = []

        if not entries:
            empty_action = QAction("  (No recent environments)", self)
            empty_action.setEnabled(False)
            self._recent_menu.addAction(empty_action)
            return

        # TYPE icons
        _icons = {
            "venv": "🐍", "uv": "⚡", "poetry": "📜",
            "pipx": "📦", "conda": "🦎",
        }
        for entry in entries:
            name       = entry.get("name", "?")
            path       = entry.get("path", "")
            env_type   = entry.get("type", "venv")
            last_opened = entry.get("last_opened", "")[:16].replace("T", "  ")
            icon       = _icons.get(env_type, "🐍")
            label      = f"{icon} {name}   —   {last_opened}"
            action = QAction(label, self)
            action.setToolTip(path)
            action.triggered.connect(
                lambda checked=False, p=path, n=name: self._open_recent_env(n, p)
            )
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()
        clear_action = QAction("🗑️ Clear Recent List", self)
        clear_action.triggered.connect(self._clear_recent_envs)
        self._recent_menu.addAction(clear_action)

    def _open_recent_env(self, name: str, path: str):
        """Select env in table by path; show Packages panel."""
        import os
        # Find row in env table matching this path
        model = self.env_table.model() if hasattr(self, "env_table") else None
        if model is None:
            return
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            item_path = model.data(idx, Qt.UserRole)  # env path stored as UserRole
            if item_path and os.path.normcase(str(item_path)) == os.path.normcase(path):
                self.env_table.selectRow(row)
                self._on_env_selected(row)
                # Update recency
                try:
                    from src.core.recent_envs import RecentEnvsManager
                    RecentEnvsManager().touch(name, path)
                    self._populate_recent_menu()
                except Exception:
                    pass
                return
        # Env not found in table (deleted) — remove from recent list
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().remove(path)
            self._populate_recent_menu()
        except Exception:
            pass
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Not Found",
            f"Environment '{name}' could not be found.\n"
            f"It may have been deleted or moved.\n\n{path}"
        )

    def _clear_recent_envs(self):
        """Clear the recent environments list."""
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().clear()
            self._populate_recent_menu()
        except Exception:
            pass

    def _track_recent(self, name: str, path: str, env_type: str):
        """Write recent env entry and refresh menu (called deferred)."""
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().touch(name, path, env_type=env_type)
            if hasattr(self, "_recent_menu"):
                self._populate_recent_menu()
        except Exception:
            pass

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 16, 8, 16)
        sidebar_layout.setSpacing(4)

        logo_label = QLabel(f"  \U0001f40d {APP_NAME}")
        logo_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo_label.setFixedHeight(48)
        sidebar_layout.addWidget(logo_label)

        version_label = QLabel(f"      v{APP_VERSION}")
        version_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        sidebar_layout.addWidget(version_label)
        sidebar_layout.addSpacing(20)

        self.nav_buttons = []

        self.btn_packages = SidebarButton(tr("packages"), "\U0001f4e6")
        self.btn_packages.setChecked(True)
        self.btn_packages.setToolTip(UI_TOOLTIPS.get("sidebar_packages", ""))
        self.btn_packages.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_packages)
        self.nav_buttons.append(self.btn_packages)

        self.btn_envs = SidebarButton(tr("environments"), "\U0001f4c1")
        self.btn_envs.setToolTip(UI_TOOLTIPS.get("sidebar_environments", ""))
        self.btn_envs.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_envs)
        self.nav_buttons.append(self.btn_envs)

        self.btn_settings = SidebarButton(tr("settings"), "⚙️")
        self.btn_settings.setToolTip(UI_TOOLTIPS.get("sidebar_settings", ""))
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))
        sidebar_layout.addWidget(self.btn_settings)
        self.nav_buttons.append(self.btn_settings)

        self.btn_learn = SidebarButton("Learn", "📚")
        self.btn_learn.setToolTip("Browse tutorials, code snippets, and learning resources")
        self.btn_learn.clicked.connect(lambda: self._switch_page(3))
        sidebar_layout.addWidget(self.btn_learn)
        self.nav_buttons.append(self.btn_learn)

        # ── Quick Launch section (visible only on Packages page) ──
        self.quick_launch_frame = QFrame()
        self.quick_launch_frame.setVisible(True)
        ql_layout = QVBoxLayout(self.quick_launch_frame)
        ql_layout.setContentsMargins(4, 8, 4, 4)
        ql_layout.setSpacing(4)

        self.ql_sep = QFrame()
        self.ql_sep.setFrameShape(QFrame.HLine)
        self.ql_sep.setStyleSheet(f"background-color: {self._c()['border']}; max-height: 1px;")
        ql_layout.addWidget(self.ql_sep)

        self.ql_title = QLabel("  ⚡ Quick Launch")
        self.ql_title.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 2px 0;")
        self.ql_title.setToolTip(UI_TOOLTIPS.get("ql_section", ""))
        ql_layout.addWidget(self.ql_title)

        # Env selector for quick launch
        self.ql_env_selector = QComboBox()
        self.ql_env_selector.setFixedHeight(28)
        self.ql_env_selector.setStyleSheet(
            f"QComboBox {{ font-size: {self._c()['fs_small']}px; padding: 2px 8px; "
            f"background-color: {self._c()['input_bg']}; color: {self._c()['fg']}; "
            f"border: 1px solid {self._c()['border']}; border-radius: 4px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {self._c()['card']}; color: {self._c()['fg']}; "
            f"selection-background-color: {self._c()['accent']}; selection-color: {self._c()['accent_fg']}; }}"
        )
        self.ql_env_selector.currentIndexChanged.connect(self._on_ql_env_changed)
        ql_layout.addWidget(self.ql_env_selector)

        # App buttons container
        self.ql_buttons_widget = QWidget()
        self.ql_buttons_layout = QVBoxLayout(self.ql_buttons_widget)
        self.ql_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.ql_buttons_layout.setSpacing(2)
        ql_layout.addWidget(self.ql_buttons_widget)

        sidebar_layout.addWidget(self.quick_launch_frame)

        # ── Bookmark frame — shown only on Learn page ─────────────────────────
        self.bookmark_frame = QFrame()
        bm_layout = QVBoxLayout(self.bookmark_frame)
        bm_layout.setContentsMargins(4, 8, 4, 4)
        bm_layout.setSpacing(4)

        bm_sep = QFrame()
        bm_sep.setFrameShape(QFrame.HLine)
        bm_sep.setStyleSheet(f"background-color: {self._c()['border']}; max-height: 1px;")
        bm_layout.addWidget(bm_sep)

        bm_title = QLabel("  📌 Bookmarks")
        bm_title.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; "
            "padding: 2px 0; font-weight: bold;"
        )
        bm_layout.addWidget(bm_title)

        self.bm_list_widget = QWidget()
        self.bm_list_layout = QVBoxLayout(self.bm_list_widget)
        self.bm_list_layout.setContentsMargins(0, 0, 0, 0)
        self.bm_list_layout.setSpacing(2)
        bm_layout.addWidget(self.bm_list_widget)

        self._bm_empty_lbl = QLabel("  No bookmarks yet.\n  Use 'Bookmark this'\n  inside any topic.")
        self._bm_empty_lbl.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 4px 8px;"
        )
        self._bm_empty_lbl.setWordWrap(True)
        self.bm_list_layout.addWidget(self._bm_empty_lbl)

        self.bookmark_frame.hide()
        sidebar_layout.addWidget(self.bookmark_frame)
        sidebar_layout.addStretch()

        self.footer_label = QLabel("  LGPL-3.0 License")
        self.footer_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        sidebar_layout.addWidget(self.footer_label)
        main_layout.addWidget(sidebar)

        # Content Area
        self.stack = QStackedWidget()
        from src.gui.package_panel import PackagePanel
        self.package_panel = PackagePanel(config=self.config)
        # B182 follow-up: when a package / launch app / preset finishes
        # installing, refresh ONLY the current env's row (package count,
        # size, runtime) — don't kick off a full re-scan of every env on
        # disk. The full _refresh_env_list shows a "Refreshing..." banner
        # for several seconds because it re-runs subprocess scans.
        self.package_panel.env_refresh_requested.connect(self._refresh_current_env_row)
        self.package_panel._ql_update_callback = self._update_ql_buttons
        self.package_panel._ql_env_changed_callback = self._sync_ql_selector
        self.stack.addWidget(self.package_panel)             # Page 0
        self.stack.addWidget(self._create_env_page())       # Page 1

        # Settings page
        from src.gui.settings_page import SettingsPage
        self.settings_page = SettingsPage(self.config)
        self.settings_page.theme_changed.connect(self._on_theme_changed)
        self.settings_page.font_changed.connect(self._on_font_changed)
        self.settings_page.settings_saved.connect(self._on_settings_saved)
        self.stack.addWidget(self.settings_page)             # Page 2

        # Learn page
        from src.gui.learn_page import LearnPage
        self.learn_page = LearnPage(self._c, config=self.config)
        self.learn_page.install_packages_requested.connect(self._on_learn_install)
        self.learn_page.bookmark_changed.connect(self._refresh_bookmarks)
        self.stack.addWidget(self.learn_page)               # Page 3
        # Load existing bookmarks into sidebar on startup
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._refresh_bookmarks(
            list(self.learn_page._bookmarks)
        ))

        main_layout.addWidget(self.stack, 1)

        self.statusBar().showMessage("Ready")

    def _create_env_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title = QLabel(tr("virtual_environments"))
        title.setObjectName("header")
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton(f"\U0001f504 {tr('refresh')}")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setFixedHeight(40)
        refresh_btn.setToolTip(UI_TOOLTIPS.get("btn_refresh", ""))
        refresh_btn.clicked.connect(lambda: self._refresh_env_list(force=True))
        self._refresh_btn = refresh_btn
        header_layout.addWidget(refresh_btn)

        create_btn = QPushButton(f"  + {tr('new_environment')}  ")
        create_btn.setToolTip(UI_TOOLTIPS.get("btn_new_env", ""))
        create_btn.clicked.connect(self._create_env)
        create_btn.setFixedHeight(40)
        header_layout.addWidget(create_btn)
        layout.addLayout(header_layout)

        self.info_label = QLabel()
        self.info_label.setObjectName("subheader")
        self.info_label.setText(f"\U0001f4c2 {self.config.get_venv_base_dir()}")
        layout.addWidget(self.info_label)

        self.env_table = QTableWidget()
        self.env_table.setColumnCount(8)
        self.env_table.setHorizontalHeaderLabels(["Name", "Type", "Path", "Runtime", "Packages", "Size", "Created", "Default"])
        # Column resize modes — Interactive+minWidth instead of Stretch
        # so horizontal scrollbar works properly at low resolutions
        self.env_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.env_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.env_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for col in range(3, 7):
            self.env_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.env_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.env_table.setColumnWidth(7, 70)
        self.env_table.horizontalHeader().setStretchLastSection(False)
        self.env_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.env_table.setSelectionMode(QTableWidget.SingleSelection)
        self.env_table.setAlternatingRowColors(True)
        self.env_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.env_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.env_table.verticalHeader().setVisible(False)
        self.env_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.env_table.verticalHeader().setDefaultSectionSize(48)  # daha yüksek satır
        # B183: previous fs_base / fs_subheader sizes were too small —
        # user repeatedly asked for a bigger, bolder env table. Hardcode
        # a comfortable reading size and bold every cell via QSS so a
        # forgotten setFont() call can't dilute it.
        self.env_table.setStyleSheet(
            f"QTableWidget {{ font-size: 16px; "
            f"color: {self._c()['fg']}; }}"
            f"QTableWidget::item {{ padding: 8px 12px; font-weight: bold; font-size: 16px; }}"
            f"QHeaderView::section {{ font-size: 15px; font-weight: bold; padding: 10px; }}"
        )
        self.env_table.doubleClicked.connect(self._on_env_double_click)
        self.env_table.selectionModel().selectionChanged.connect(self._on_env_selected)
        # Manual user interaction (mouse click / keyboard) — hides educational cmd panel
        # if user moves to a different env. Programmatic selection (refresh) is not affected.
        self.env_table.clicked.connect(self._on_env_user_interaction)
        self.env_table.installEventFilter(self)
        self.env_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.env_table.customContextMenuRequested.connect(self._show_env_context_menu)
        layout.addWidget(self.env_table)

        # Loading indicator (shown during refresh)
        self.loading_label = QLabel(f"⏳ {tr('loading_environments')}")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFixedHeight(40)
        self.loading_label.setStyleSheet(
            f"color: {self._c()['fg']}; font-size: {self._c()['fs_base']}px; font-weight: bold; padding: 8px; "
            "background-color: #f9e2af; "
            "border-radius: 6px;"
        )
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # ── Persistent educational command panel (ABOVE action buttons) ────
        # Hidden by default. Shown on Delete/Clone/Rename. Hidden on env change or tab switch.
        from PySide6.QtWidgets import QTextEdit as _QTE, QWidget as _QW_panel
        self._cmd_panel_widget = _QW_panel()
        _panel_layout = QVBoxLayout(self._cmd_panel_widget)
        _panel_layout.setContentsMargins(0, 0, 0, 0)
        _panel_layout.setSpacing(6)

        self._cmd_panel_title = QLabel("💡 Command Reference")
        self._cmd_panel_title.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #89b4fa; "
            "padding: 4px 2px 2px 2px;"
        )
        _panel_layout.addWidget(self._cmd_panel_title)

        self._cmd_panel_live = QLabel("▶")
        self._cmd_panel_live.setWordWrap(True)
        self._cmd_panel_live.setStyleSheet(
            "color: #f9e2af; font-size: 20px; font-weight: bold; "
            "font-family: Consolas, monospace; padding: 10px 12px; "
            "background: #181825; border: 2px solid #f9e2af; border-radius: 6px;"
        )
        _panel_layout.addWidget(self._cmd_panel_live)

        self._cmd_panel_hints = _QTE()
        self._cmd_panel_hints.setReadOnly(True)
        self._cmd_panel_hints.setFixedHeight(200)
        self._cmd_panel_hints.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244; "
            "border-radius: 8px; padding: 8px; color: #cdd6f4; "
            "font-family: Consolas, monospace; font-size: 18px; font-weight: bold;"
        )
        _panel_layout.addWidget(self._cmd_panel_hints)

        self._cmd_panel_widget.setVisible(False)
        layout.addWidget(self._cmd_panel_widget)

        action_layout = QHBoxLayout()

        self.btn_manage_pkgs = QPushButton(f"\U0001f4e6 {tr('manage_packages')}")
        self.btn_manage_pkgs.setToolTip(UI_TOOLTIPS.get("btn_manage_pkgs", ""))
        self.btn_manage_pkgs.clicked.connect(self._open_package_manager)
        self.btn_manage_pkgs.setEnabled(False)
        action_layout.addWidget(self.btn_manage_pkgs)

        self.btn_terminal = QPushButton(f"🖥 {tr('open_terminal')}")
        self.btn_terminal.setObjectName("secondary")
        self.btn_terminal.setToolTip(UI_TOOLTIPS.get("btn_terminal", ""))
        self.btn_terminal.clicked.connect(self._open_terminal)
        self.btn_terminal.setEnabled(False)
        self.btn_terminal.setMinimumWidth(120)
        action_layout.addWidget(self.btn_terminal)

        self.btn_clone = QPushButton(f"\U0001f4cb {tr('clone')}")
        self.btn_clone.setObjectName("secondary")
        self.btn_clone.setToolTip(UI_TOOLTIPS.get("btn_clone", ""))
        self.btn_clone.clicked.connect(self._clone_env)
        self.btn_clone.setEnabled(False)
        action_layout.addWidget(self.btn_clone)

        self.btn_rename = QPushButton("✏️ Rename (Name)")
        self.btn_rename.setObjectName("secondary")
        self.btn_rename.setToolTip("Rename folder only — fast, but pip/python paths may break on Windows")
        self.btn_rename.clicked.connect(self._rename_env_only)
        self.btn_rename.setEnabled(False)
        action_layout.addWidget(self.btn_rename)

        self.btn_rename_full = QPushButton("🔄 Rename (Full)")
        self.btn_rename_full.setObjectName("secondary")
        self.btn_rename_full.setToolTip("Clone with new name + delete old — slow but safe, all packages reinstalled")
        self.btn_rename_full.clicked.connect(self._rename_env_full)
        self.btn_rename_full.setEnabled(False)
        action_layout.addWidget(self.btn_rename_full)

        self.btn_export = QPushButton("📤 Export ▾")
        self.btn_export.setObjectName("secondary")
        self.btn_export.setToolTip(UI_TOOLTIPS.get("btn_export", ""))
        self.btn_export.setEnabled(False)
        export_menu = QMenu(self.btn_export)
        export_menu.addAction("📄 requirements.txt", self._export_requirements)
        export_menu.addAction("📄 requirements-frozen.txt", self._export_frozen)
        export_menu.addSeparator()
        export_menu.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_menu.addAction("📦 pyproject.toml", self._export_pyproject)
        export_menu.addAction("📊 JSON", self._export_json)
        export_menu.addSeparator()
        export_menu.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_menu.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_menu.addSeparator()
        export_menu.addAction("📋 Copy to Clipboard", self._export_clipboard)
        self.btn_export.setMenu(export_menu)
        action_layout.addWidget(self.btn_export)

        self.btn_make_default = QPushButton("⭐ Make Default")
        self.btn_make_default.setObjectName("secondary")
        self.btn_make_default.setToolTip(UI_TOOLTIPS.get("btn_make_default", ""))
        self.btn_make_default.clicked.connect(self._make_default_env)
        self.btn_make_default.setEnabled(False)
        action_layout.addWidget(self.btn_make_default)

        action_layout.addStretch()

        self.btn_delete = QPushButton(f"\U0001f5d1\ufe0f {tr('delete')}")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.setToolTip(UI_TOOLTIPS.get("btn_delete", ""))
        self.btn_delete.clicked.connect(self._delete_env)
        self.btn_delete.setEnabled(False)
        action_layout.addWidget(self.btn_delete)

        layout.addLayout(action_layout)
        return page

    def _hide_cmd_panel(self):
        """Hide the persistent educational command panel."""
        if hasattr(self, "_cmd_panel_widget"):
            self._cmd_panel_widget.setVisible(False)
        self._cmd_panel_env_name = None
        self._cmd_panel_sticky = False

    def _on_env_user_interaction(self, *args):
        """Called on manual user interaction (mouse click / key press) with env table.
        Hides the educational cmd panel if user moved to a different env.
        Programmatic selection changes (e.g. after refresh) do NOT trigger this.
        """
        if not hasattr(self, "_cmd_panel_env_name"):
            return
        _panel_env = self._cmd_panel_env_name
        if _panel_env is None:
            return
        # What env is currently selected?
        rows = self.env_table.selectionModel().selectedRows()
        if not rows:
            return
        try:
            cur_name = self.env_table.item(rows[0].row(), 0).text().strip()
        except Exception:
            return
        if cur_name != _panel_env:
            self._hide_cmd_panel()

    def eventFilter(self, obj, event):
        """Detect keyboard arrow navigation on env_table for panel hiding."""
        from PySide6.QtCore import QEvent
        if hasattr(self, "env_table") and obj is self.env_table:
            if event.type() == QEvent.KeyRelease:
                # After key release, Qt has updated selection — check if it moved
                self._on_env_user_interaction()
        return super().eventFilter(obj, event)

    def _update_cmd_panel(self, action, env_type, name, env_path=""):
        """Update the persistent educational command panel on the env page."""
        if not hasattr(self, "_cmd_panel_live"):
            return
        # Show the panel (hidden by default and on env/tab changes)
        if hasattr(self, "_cmd_panel_widget"):
            self._cmd_panel_widget.setVisible(True)
        # Remember which env this panel is for — used to decide when to hide
        self._cmd_panel_env_name = name
        # Sticky: keep panel visible through auto-selection changes (e.g. post-refresh).
        # Only manual env switch (different env clicked) or tab switch hides it.
        self._cmd_panel_sticky = True
        is_win = get_platform() == "windows"

        # Build live command
        live = ""
        if action == "delete":
            if env_type == "pipx":
                live = "pipx uninstall-all  →  pipx ensurepath"
            elif env_type == "conda":
                live = f"micromamba env remove -p {env_path} --yes"
            else:
                live = (f'Remove-Item -Recurse -Force "{env_path}"'
                        if is_win else f"rm -rf {env_path}")
        elif action == "clone":
            if env_type == "pipx":
                live = f"pipx install {name}  (or pipx reinstall-all)"
            elif env_type == "poetry":
                live = "poetry lock && poetry install  (from project dir)"
            elif env_type == "conda":
                live = f"micromamba create -p <new_path> --clone {env_path} --yes"
            elif env_type == "uv":
                live = f"uv pip freeze → uv venv <new_path> → uv pip install -r"
            else:
                live = (f'Copy-Item -Recurse "{env_path}" "{env_path}-clone"'
                        if is_win else f"cp -r {env_path} {env_path}-clone")
        elif action == "rename":
            if env_type == "pipx":
                live = f"pipx uninstall {name} && pipx install <new_name>"
            elif env_type == "poetry":
                live = "edit pyproject.toml → poetry env remove --all → poetry install"
            elif env_type == "conda":
                live = f"micromamba env export -n {name} > env.yml"
            else:
                live = (f'Rename-Item "{env_path}" "<new_name>"'
                        if is_win else f"mv {env_path} <new_path>")
        elif action == "rename_display":
            live = "# VenvStudio-only label change — no shell command (writes .venvstudio_display_name)"
        self._cmd_panel_live.setText(f"▶ {live}")

        # HTML helpers
        def _c(t): return f"<span style='color:#89b4fa;font-family:Consolas,monospace;font-size:18px;font-weight:bold;'>{t}</span>"
        def _p(t): return f"<span style='color:#a6e3a1;font-family:Consolas,monospace;font-size:18px;font-weight:bold;'>{t}</span>"
        def _k(t): return f"<span style='color:#cba6f7;font-family:Consolas,monospace;font-weight:bold;font-size:18px;'>{t}</span>"
        def _ttl(icon, txt, col): return f"<p style='font-size:18px;font-weight:bold;color:{col};margin:6px 0 4px 0;'>{icon}&nbsp; {txt}</p>"
        def _ln(t): return f"<p style='margin:3px 0;font-size:17px;font-weight:bold;font-family:Consolas,monospace;color:#cdd6f4;background:#11111b;padding:5px 10px;border-radius:4px;'>{t}</p>"
        def _nt(t): return f"<p style='margin:6px 0 2px 0;font-size:12px;color:#6c7086;font-style:italic;'>{t}</p>"

        html = ""
        if action == "delete":
            if env_type == "pipx":
                html = (
                    _ttl("📦", "Reset pipx environment", "#a6e3a1") +
                    _nt("Uninstall ALL pipx apps:") +
                    _ln(_c("pipx") + " uninstall-all") +
                    _nt("Ensure PATH is set up (fresh pipx):") +
                    _ln(_c("pipx") + " ensurepath") +
                    _nt("Install new CLI apps:") +
                    _ln(_c("pipx") + " install " + _k("<package>")) +
                    _nt("List installed apps:") +
                    _ln(_c("pipx") + " list")
                )
            elif env_type == "conda":
                html = (
                    _ttl("🦎", f"Remove conda env '{name}'", "#89dceb") +
                    _nt("Remove by path:") +
                    _ln(_c("micromamba") + " env remove -p " + _p(env_path) + " --yes") +
                    _nt("Clean cache + unused packages:") +
                    _ln(_c("micromamba") + " clean --all --yes")
                )
            else:
                if is_win:
                    rm_main = _c("Remove-Item") + " -Recurse -Force " + _p(f'"{env_path}"')
                    rm_alt_note = "Classic cmd.exe alternative:"
                    rm_alt = _c("rmdir") + " /S /Q " + _p(f'"{env_path}"')
                else:
                    rm_main = _c("rm") + " -rf " + _p(env_path)
                    rm_alt_note = "Verbose (show each deleted file):"
                    rm_alt = _c("rm") + " -rfv " + _p(env_path)
                html = (
                    _ttl("🗑️", f"Delete {env_type} env '{name}'", "#f38ba8") +
                    _nt("Deactivate first (if active):") +
                    _ln(_c("deactivate")) +
                    _nt("Delete the environment folder:") +
                    _ln(rm_main) +
                    _nt(rm_alt_note) +
                    _ln(rm_alt)
                )
        elif action == "clone":
            if env_type == "pipx":
                html = (
                    _ttl("📦", f"Clone pipx app '{name}' — Not directly supported", "#f9e2af") +
                    _nt("pipx apps are isolated per CLI tool. To replicate on another machine:") +
                    _ln(_c("pipx") + " install " + _k(name)) +
                    _nt("Or reinstall everything (e.g. after Python upgrade):") +
                    _ln(_c("pipx") + " reinstall-all") +
                    _nt("List all installed apps:") +
                    _ln(_c("pipx") + " list")
                )
            elif env_type == "poetry":
                html = (
                    _ttl("📜", f"Clone Poetry env '{name}' — Not directly supported", "#f9e2af") +
                    _nt("Poetry envs are tied to pyproject.toml. To replicate:") +
                    _ln(_c("cd") + " " + _p("<your-project-dir>")) +
                    _ln(_c("poetry") + " lock") +
                    _ln(_c("poetry") + " install") +
                    _nt("Or copy pyproject.toml + poetry.lock to a new project dir and run:") +
                    _ln(_c("poetry") + " install")
                )
            elif env_type == "conda":
                html = (
                    _ttl("🦎", f"Clone conda env '{name}'", "#89dceb") +
                    _nt("What VenvStudio runs:") +
                    _ln(_c("micromamba") + " create -p " + _p("<new_path>") + " --clone " + _p(env_path) + " --yes") +
                    _nt("Alternative — export/import via YAML:") +
                    _ln(_c("micromamba") + " env export -p " + _p(env_path) + " &gt; env.yml") +
                    _ln(_c("micromamba") + " create -p " + _p("<new_path>") + " --file env.yml")
                )
            elif env_type == "uv":
                if is_win:
                    _src_py = f"{env_path}\\Scripts\\python.exe"
                    _tgt_py = "<new_path>\\Scripts\\python.exe"
                else:
                    _src_py = f"{env_path}/bin/python"
                    _tgt_py = "<new_path>/bin/python"
                html = (
                    _ttl("⚡", f"Clone uv env '{name}'", "#f9e2af") +
                    _nt("What VenvStudio runs:") +
                    _ln(_c("uv") + " pip freeze --python " + _p(_src_py) + " &gt; req.txt") +
                    _ln(_c("uv") + " venv " + _p("<new_path>") + " --python " + _p(_src_py)) +
                    _ln(_c("uv") + " pip install -r req.txt --python " + _p(_tgt_py))
                )
            elif is_win:
                html = (
                    _ttl("📋", f"Clone env '{name}'", "#89b4fa") +
                    _nt("PowerShell:") +
                    _ln(_c("Copy-Item") + " -Recurse " + _p(f'"{env_path}"') + " " + _p(f'"{env_path}-clone"')) +
                    _nt("Reinstall packages after clone (recommended):") +
                    _ln(_c("pip") + " freeze &gt; requirements.txt &amp;&amp; " +
                        _c("pip") + " install -r requirements.txt")
                )
            else:
                html = (
                    _ttl("📋", f"Clone env '{name}'", "#89b4fa") +
                    _nt("Copy the folder:") +
                    _ln(_c("cp") + " -r " + _p(env_path) + " " + _p(f"{env_path}-clone")) +
                    _nt("Reinstall packages after clone (recommended):") +
                    _ln(_c("pip") + " freeze &gt; requirements.txt &amp;&amp; " +
                        _c("pip") + " install -r requirements.txt")
                )
        elif action == "rename":
            if env_type == "pipx":
                html = (
                    _ttl("📦", f"Rename pipx app '{name}' — Not directly supported", "#f9e2af") +
                    _nt("pipx apps are identified by their package name. To 'rename', uninstall and reinstall:") +
                    _ln(_c("pipx") + " uninstall " + _k(name)) +
                    _ln(_c("pipx") + " install " + _p("<new_name>"))
                )
            elif env_type == "poetry":
                html = (
                    _ttl("📜", f"Rename Poetry env '{name}' — Not directly supported", "#f9e2af") +
                    _nt("Poetry env names come from pyproject.toml. Edit the 'name' field, then:") +
                    _ln(_c("poetry") + " env remove --all") +
                    _ln(_c("poetry") + " install") +
                    _nt("Alternative: move the project folder to a new name, Poetry regenerates env.")
                )
            elif env_type == "conda":
                html = (
                    _ttl("🦎", f"Rename conda env '{name}'", "#89dceb") +
                    _nt("micromamba can't rename in place. Export → recreate → remove:") +
                    _ln(_c("micromamba") + " env export -n " + _p(name) + " &gt; env.yml") +
                    _ln(_c("micromamba") + " create -n " + _p("<new_name>") + " --file env.yml") +
                    _ln(_c("micromamba") + " env remove -n " + _p(name) + " --yes")
                )
            elif is_win:
                html = (
                    _ttl("✏️", f"Rename env '{name}'", "#f9e2af") +
                    _nt("Rename folder (fast — but pip/python paths may break):") +
                    _ln(_c("Rename-Item") + " " + _p(f'"{env_path}"') + " " + _p('"<new_name>"')) +
                    _nt("Safer: clone with new name + delete old:") +
                    _ln(_c("Copy-Item") + " -Recurse " + _p(f'"{env_path}"') + " " + _p('"<new_path>"'))
                )
            else:
                html = (
                    _ttl("✏️", f"Rename env '{name}'", "#f9e2af") +
                    _nt("Rename folder (fast — but pip/python paths may break):") +
                    _ln(_c("mv") + " " + _p(env_path) + " " + _p("<new_path>")) +
                    _nt("Safer: clone with new name + delete old:") +
                    _ln(_c("cp") + " -r " + _p(env_path) + " " + _p("<new_path>"))
                )
        self._cmd_panel_hints.setHtml(html)

    def _switch_page(self, index):
        page_names = {0: "Packages", 1: "Environments", 2: "Settings", 3: "Learn"}
        self._log.debug(f"_switch_page → {page_names.get(index, index)} (index={index})")

        # Lazy-build PackagePanel on first visit
        if index == 0 and self.package_panel is None:
            from src.gui.package_panel import PackagePanel
            self.package_panel = PackagePanel(config=self.config)
            self.package_panel.env_refresh_requested.connect(self._refresh_current_env_row)
            self.package_panel._ql_update_callback = self._update_ql_buttons
            self.package_panel._ql_env_changed_callback = self._sync_ql_selector
            self.stack.removeWidget(self._packages_placeholder)
            self.stack.insertWidget(0, self.package_panel)
            self._packages_placeholder.deleteLater()
            # Load env list into panel
            if hasattr(self, '_last_env_list'):
                if self.package_panel is not None: self.package_panel.populate_env_list(self._last_env_list)
            # Open selected env if any
            if self.selected_env:
                from pathlib import Path as _Path
                _env = _Path(self.selected_env) if isinstance(self.selected_env, str) else self.selected_env
                self.package_panel.set_venv(_env)
            # Force repaint so panel is visible immediately
            self.package_panel.update()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        # Lazy-build Settings page on first visit
        if index == 2 and self.settings_page is None:
            from src.gui.settings_page import SettingsPage
            self.settings_page = SettingsPage(self.config)
            self.settings_page.theme_changed.connect(self._on_theme_changed)
            self.settings_page.font_changed.connect(self._on_font_changed)
            self.settings_page.settings_saved.connect(self._on_settings_saved)
            self.stack.removeWidget(self._settings_placeholder)
            self.stack.insertWidget(2, self.settings_page)
            self._settings_placeholder.deleteLater()

        # Lazy-build Learn page on first visit
        if index == 3 and self.learn_page is None:
            from src.gui.learn_page import LearnPage
            self.learn_page = LearnPage(self._c, config=self.config)
            self.learn_page.install_packages_requested.connect(self._on_learn_install)
            self.learn_page.bookmark_changed.connect(self._refresh_bookmarks)
            self.stack.removeWidget(self._learn_placeholder)
            self.stack.insertWidget(3, self.learn_page)
            self._learn_placeholder.deleteLater()
            # Load bookmarks
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._refresh_bookmarks(
                list(self.learn_page._bookmarks)
            ))

        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        # Quick launch only on Packages page
        if hasattr(self, "quick_launch_frame"):
            self.quick_launch_frame.setVisible(index == 0)
        if hasattr(self, "bookmark_frame"):
            if index == 3:
                self.bookmark_frame.show()
            else:
                self.bookmark_frame.hide()

        # Educational cmd panel — hide on any tab switch (re-shown on next action)
        if hasattr(self, "_hide_cmd_panel"):
            self._hide_cmd_panel()

    def _on_learn_install(self, packages: list):
        """Called when Learn page requests package install — show LearnInstallDialog."""
        from PySide6.QtCore import QTimer
        from src.gui.learn_install_dialog import LearnInstallDialog, LearnInstallDecision
        if not packages:
            return

        # Build env list for dialog
        envs = []
        for row in range(self.env_table.rowCount()):
            _ni = self.env_table.item(row, 0)
            _ti = self.env_table.item(row, 1)
            _pi = self.env_table.item(row, 2)
            if _ni:
                _name = _ni.text().strip()
                _type = (_ti.data(Qt.UserRole) or _ti.text().strip()) if _ti else "venv"
                _path_str = _ni.toolTip() if _ni.toolTip() else ""
                _python = _pi.text().strip() if _pi else "?"
                envs.append({
                    "name": _name,
                    "type": _type,
                    "path": Path(_path_str) if _path_str else None,
                    "python": _python,
                })

        if not envs:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Environments",
                                "No environments found. Create one first.")
            return

        _current = self._get_selected_env_name() or ""
        _default = self.config.get("default_env", "") if hasattr(self, "config") else ""
        _colors = self._c() if hasattr(self, "_c") else None

        dlg = LearnInstallDialog(
            packages=packages,
            envs=envs,
            current_env_name=_current,
            default_env_name=_default,
            colors=_colors,
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted or dlg.decision is None:
            return

        d = dlg.decision

        if d.mode == LearnInstallDecision.MODE_NEW_VENV:
            # Open create env dialog pre-filled, then install after creation
            if hasattr(self, "_new_env"):
                self._new_env()
            return

        if d.mode == LearnInstallDecision.MODE_PIPX:
            # Switch to package panel — pipx env — and install
            for row in range(self.env_table.rowCount()):
                _ti = self.env_table.item(row, 1)
                if _ti and (_ti.data(Qt.UserRole) or _ti.text()).strip() == "pipx":
                    self.env_table.selectRow(row)
                    self._on_env_selected(row)
                    break
            if d.switch_after:
                self._switch_page(0)
            if hasattr(self, "package_panel"):
                QTimer.singleShot(400, lambda: self.package_panel._install_packages(packages) if self.package_panel else None)
            return

        # MODE_EXISTING — switch to target env then install
        target = d.env_name
        for row in range(self.env_table.rowCount()):
            _ni = self.env_table.item(row, 0)
            if _ni and _ni.text().strip() == target:
                self.env_table.selectRow(row)
                self._on_env_selected(row)
                break

        if d.switch_after:
            self._switch_page(0)
        if hasattr(self, "package_panel"):
            QTimer.singleShot(400, lambda: self.package_panel._install_packages(packages) if self.package_panel else None)

    def _refresh_bookmarks(self, bookmarks: list):
        """Update Quick Launch bookmark buttons."""
        if not hasattr(self, 'bm_list_layout'):
            return
        # Clear existing
        while self.bm_list_layout.count():
            item = self.bm_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not bookmarks:
            self._bm_empty_lbl = QLabel("  No bookmarks yet.\n  Use 🏷️ in Learn to bookmark topics.")
            self._bm_empty_lbl.setStyleSheet(
                f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 4px 8px;"
            )
            self._bm_empty_lbl.setWordWrap(True)
            self.bm_list_layout.addWidget(self._bm_empty_lbl)
            return

        for title in bookmarks:
            btn = QPushButton(f"  🔖 {title}")
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {self._c()['fg']}; "
                f"border: none; border-radius: 6px; text-align: left; "
                f"font-size: {self._c()['fs_tiny']}px; padding: 0 8px; }}"
                f"QPushButton:hover {{ background: {self._c()['accent']}22; }}"
            )
            btn.setCursor(Qt.PointingHandCursor)
            # Navigate to Learn page on click
            btn.clicked.connect(lambda _, t=title: self._open_bookmark(t))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, t=title, b=btn: self._bookmark_context_menu(b, t)
            )
            self.bm_list_layout.addWidget(btn)

    def _open_bookmark(self, topic_title: str):
        """Switch to Learn page and navigate to the topic."""
        self._switch_page(3)
        if hasattr(self, 'learn_page'):
            self.learn_page._jump_to_topic(topic_title)

    def _bookmark_context_menu(self, btn, title: str):
        """Right-click context menu on a bookmark button."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_go     = menu.addAction("📖 Go to topic")
        menu.addSeparator()
        act_remove = menu.addAction("🗑 Remove bookmark")
        chosen = menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        if chosen == act_go:
            self._open_bookmark(title)
        elif chosen == act_remove:
            if hasattr(self, 'learn_page'):
                self.learn_page.remove_bookmark(title)

    def _on_ql_env_changed(self, idx):
        """Sol sidebar QL dropdown değişti — her şeyi sync et."""
        if not hasattr(self, "ql_env_selector"):
            return
        venv_name = self.ql_env_selector.itemData(idx)
        if not venv_name:
            self._rebuild_ql_buttons(set())
            return
        venv_path = self._get_env_path(venv_name) or self.venv_manager.base_dir / venv_name
        if not venv_path.exists() and not (venv_path.parent / ".venvstudio_env").exists():
            pass  # pipx path may not have standard structure
        # Env tablosunda ilgili satırı seç
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == venv_name:
                self.env_table.blockSignals(True)
                self.env_table.selectRow(row)
                self.env_table.blockSignals(False)
                break
        # package_panel sync (sayfa değiştirme!)
        if self.package_panel is not None: self.package_panel.set_venv(venv_path)

    def _ql_load_env_packages(self, venv_name: str):
        """Sadece QL için paket listesi yükle — sağ paneli değiştirme."""
        from pathlib import Path
        from src.core.pip_manager import PipManager
        from src.core.venv_manager import VenvManager
        import json

        venv_path = self._get_env_path(venv_name) or self.venv_manager.base_dir / venv_name
        if not venv_path.exists() and not (venv_path.parent / ".venvstudio_env").exists():
            pass  # pipx path may not have standard structure

        class _QLWorker(QThread):
            done = Signal(str, list)
            def __init__(self, venv_path, parent=None):
                super().__init__(parent)
                self._vp = venv_path
            def run(self):
                try:
                    import subprocess, sys
                    python = self._vp / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                    # B151: suppress console flash on Windows
                    _kw = dict(capture_output=True, text=True, timeout=30)
                    if sys.platform == "win32":
                        _kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                    r = subprocess.run(
                        [str(python), "-m", "pip", "list", "--format=json"],
                        **_kw
                    )
                    if r.returncode == 0:
                        pkgs = json.loads(r.stdout)
                        self.done.emit(self._vp.name, pkgs)
                except Exception:
                    self.done.emit(self._vp.name, [])

        def _on_done(env_name, pkgs):
            # Cache'e kaydet
            try:
                vm = VenvManager(self.config.get_venv_base_dir())
                all_cache = vm._load_all_cache()
                key = "pkg_list:" + str(self.venv_manager.base_dir / env_name).replace("\\", "/")
                all_cache[key] = {"packages": [{"name": p["name"], "version": p["version"]} for p in pkgs], "needs_refresh": 0}
                vm._save_all_cache(all_cache)
            except Exception:
                pass
            # Sadece QL hâlâ bu env'i gösteriyorsa güncelle
            if hasattr(self, "ql_env_selector") and self.ql_env_selector.currentData() == env_name:
                installed = {p["name"].lower() for p in pkgs}
                self._rebuild_ql_buttons(installed)

        self._ql_worker = _QLWorker(venv_path, parent=self)
        self._ql_worker.done.connect(_on_done)
        self._ql_worker.start()

    def _get_installed_from_cache(self, env_name: str) -> set:
        """Cache'den paket isimlerini oku — subprocess yok."""
        try:
            from src.core.venv_manager import VenvManager
            vm = VenvManager(self.config.get_venv_base_dir())
            all_cache = vm._load_all_cache()
            venv_path = self.venv_manager.base_dir / env_name
            our_path = str(venv_path).lower().replace("\\", "/")
            for key, entry in all_cache.items():
                if not key.startswith("pkg_list:"):
                    continue
                key_path = key[len("pkg_list:"):].lower().replace("\\", "/")
                if key_path == our_path and entry.get("needs_refresh", 1) == 0:
                    pkgs = entry.get("packages", [])
                    if pkgs:
                        return {p["name"].lower() for p in pkgs}
        except Exception:
            pass
        return set()

    def _sync_ql_selector(self, env_name: str):
        """Üst dropdown değişince QL + env tablosunu sync et."""
        # QL selector
        if hasattr(self, "ql_env_selector"):
            idx = self.ql_env_selector.findData(env_name)
            if idx >= 0:
                self.ql_env_selector.blockSignals(True)
                self.ql_env_selector.setCurrentIndex(idx)
                self.ql_env_selector.blockSignals(False)
        # Env tablosu satırı
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == env_name:
                self.env_table.blockSignals(True)
                self.env_table.selectRow(row)
                self.env_table.blockSignals(False)
                break

    def _update_ql_buttons(self, env_name: str = ""):
        """package_panel'deki yükleme bittikten sonra çağrılır — fresh data kullan."""
        # installed_package_names her zaman şu anki package_panel env'ine aittir
        installed = getattr(self.package_panel, "installed_package_names", set())
        self._rebuild_ql_buttons(installed)
        # QL selector'ı package_panel'in env'iyle sync et
        if hasattr(self, "ql_env_selector") and self.package_panel is not None and self.package_panel.pip_manager:
            current_env = self.package_panel.pip_manager.venv_path.name
            self._sync_ql_selector(current_env)

    def _rebuild_ql_buttons(self, installed: set):
        """Verilen installed set'e göre QL butonlarını yeniden oluştur."""
        if not hasattr(self, "ql_buttons_layout"):
            return
        while self.ql_buttons_layout.count():
            item = self.ql_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        c = self._c()
        app_defs = getattr(self.package_panel, "app_definitions", [])
        has_any = False
        for app in app_defs:
            if app["package"].lower() not in installed:
                continue
            has_any = True
            btn = QPushButton(f"{app['icon']} {app['name']}")
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ font-size: {self._c()['fs_small']}px; text-align: left; padding: 2px 8px; "
                f"background-color: {c['sidebar']}; color: {c['fg']}; "
                f"border: 1px solid {c['border']}; border-radius: 4px; }}"
                f"QPushButton:hover {{ background-color: {c['hover']}; border-color: {c['accent']}; }}"
            )
            btn.clicked.connect(lambda checked, a=app: self.package_panel._launch_app(a) if self.package_panel else None)
            self.ql_buttons_layout.addWidget(btn)
        if not has_any:
            lbl = QLabel("  No apps installed")
            lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 4px;")
            self.ql_buttons_layout.addWidget(lbl)

    def _refresh_env_list(self, force: bool = False):
        """Phase 1: Load from cache instantly. Phase 2: fetch missing in background.
        If force=True (manual Refresh button), invalidates all caches first.
        """
        self._log.debug(f"_refresh_env_list called (force={force})")
        self.env_table.setRowCount(0)

        # Manual refresh: invalidate all caches, show overlay, disable button
        if force:
            self.venv_manager.invalidate_all_caches()
            # Disable refresh button
            if hasattr(self, "_refresh_btn"):
                self._refresh_btn.setEnabled(False)
                self._refresh_btn.setText("⏳ Refreshing...")
            # Show prominent banner immediately
            self.loading_label.setText("🔄  Refreshing environments — please wait...")
            self.loading_label.setVisible(True)
            self.statusBar().showMessage("Refreshing environments...")
            # Force UI update so banner appears before heavy work starts
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        # Fast load — never skip_calc (pyvenv.cfg reading is fast, no subprocess)
        envs = self.venv_manager.list_venvs_fast(skip_calc=False)
        # Sort: base_dir envs first (alphabetic), then poetry (alphabetic), then pipx
        def _env_sort_key(e):
            if e.env_type == "pipx":
                return (2, e.name.lower())
            elif e.env_type == "poetry":
                return (1, e.name.lower())
            else:
                return (0, e.name.lower())
        envs = sorted(envs, key=_env_sort_key)

        # Also show loading if some envs are missing cache in normal load
        has_missing_cache = any(e.python_version == "..." for e in envs)
        if not force:
            self.loading_label.setVisible(has_missing_cache)
            if has_missing_cache:
                self.statusBar().showMessage("Loading environments...")
        self.env_table.setRowCount(len(envs))

        # Sync quick launch env selector
        if hasattr(self, "ql_env_selector"):
            current_ql = self.ql_env_selector.currentData()
            self.ql_env_selector.blockSignals(True)
            self.ql_env_selector.clear()
            self.ql_env_selector.addItem(tr("select_environment"), "")
            for env in envs:
                if env.is_valid:
                    self.ql_env_selector.addItem(f"  {env.name}", env.name)
            idx = self.ql_env_selector.findData(current_ql)
            if idx >= 0:
                self.ql_env_selector.setCurrentIndex(idx)
            else:
                # Previously selected env no longer exists — clear QL buttons
                self.ql_env_selector.setCurrentIndex(0)
                self._rebuild_ql_buttons(set())
            self.ql_env_selector.blockSignals(False)

        _type_labels = {
            "venv":         "🐍 venv",
            "uv":           "⚡ uv",
            "poetry":       "📜 Poetry",
            "pipx":         "📦 pipx",
            "conda":        "🦎 Conda",
            "system_tools": "🗂 Tools",
        }
        # B183: previously hardcoded pastel Catppuccin Mocha colours, which
        # were illegible on a light background. Pick darker, saturated
        # versions for light themes and the original pastels for dark
        # themes. We detect light vs dark by looking at the active 'bg'
        # palette colour — light themes have a near-white bg.
        _is_light_theme = False
        try:
            _bg = (self._c().get("bg") or "").lower()
            _bg_hex = _bg.lstrip("#")
            if len(_bg_hex) >= 6:
                _r = int(_bg_hex[0:2], 16)
                _g = int(_bg_hex[2:4], 16)
                _b = int(_bg_hex[4:6], 16)
                _is_light_theme = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            self._log.debug(
                f"env_table colours: bg={_bg!r} → light_theme={_is_light_theme}"
            )
        except Exception as _e:
            self._log.debug(f"env_table colour detection failed: {_e}")
        if _is_light_theme:
            _type_colors = {
                "uv":           "#8a6d00",  # darker amber, more contrast on white
                "poetry":       "#5b2c6f",  # very deep purple
                "pipx":         "#0c5a72",  # very dark teal
                "conda":        "#1b5e20",  # dark forest green
                "system_tools": None,
            }
            _path_color_default = "#333333"  # nearly black
        else:
            _type_colors = {
                "uv":           "#f9e2af",
                "poetry":       "#cba6f7",
                "pipx":         "#89dceb",
                "conda":        "#a6e3a1",
                "system_tools": None,
            }
            _path_color_default = "#bac2de"

        # Bold font used for ALL columns (B183 — previously only name was
        # bold, other columns looked anaemic next to it on light themes)
        _row_font = QFont()
        _row_font.setBold(True)

        for i, env in enumerate(envs):
            etype = getattr(env, "env_type", "venv")

            # ── Name column ──
            name_item = QTableWidgetItem(f"  {env.name}")
            _color = _type_colors.get(etype)
            if etype == "system_tools":
                name_item.setForeground(QColor(self._c().get("accent", "#89b4fa")))
                name_item.setToolTip("System tools environment — install R, RStudio, Ollama, DBeaver etc. from Launch tab")
            elif _color:
                name_item.setForeground(QColor(_color))
                name_item.setToolTip(f"{_type_labels.get(etype, etype)} environment")
            elif not env.is_valid:
                name_item.setForeground(Qt.red)
                name_item.setToolTip("Invalid environment (Python not found)")
            elif _is_light_theme:
                # Default venv on light theme — needs a dark fg too
                name_item.setForeground(QColor("#1f2937"))
            name_item.setFont(_row_font)
            self.env_table.setItem(i, 0, name_item)

            # ── Type column ──
            type_item = QTableWidgetItem(f"  {_type_labels.get(etype, '🐍 venv')}")
            type_item.setData(Qt.UserRole, etype)  # store raw env_type for deletion etc.
            if _color:
                type_item.setForeground(QColor(_color))
            elif etype == "system_tools":
                type_item.setForeground(QColor(self._c().get("accent", "#89b4fa")))
            elif _is_light_theme:
                type_item.setForeground(QColor("#1f2937"))
            type_item.setFont(_row_font)
            self.env_table.setItem(i, 1, type_item)

            # ── Path column ──
            _full_path = str(env.path)
            _display_path = _full_path
            path_item = QTableWidgetItem(f"  {_display_path}")
            path_item.setToolTip(_full_path)
            path_item.setForeground(QColor(_path_color_default))
            path_item.setFont(_row_font)
            self.env_table.setItem(i, 2, path_item)

            # ── Runtime column: Python version or "----" ──
            _rv = str(env.python_version).strip()
            _runtime_str = f"  Python {_rv}" if (_rv and _rv not in ("Unknown", "?", "...")) else "  ----"
            _runtime_item = QTableWidgetItem(_runtime_str)
            _runtime_item.setFont(_row_font)
            if _is_light_theme:
                _runtime_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 3, _runtime_item)

            pkg = str(env.package_count) if env.package_count else "0"
            _pkg_item = QTableWidgetItem(f"  {pkg}")
            _pkg_item.setFont(_row_font)
            if _is_light_theme:
                _pkg_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 4, _pkg_item)

            _size = env.size if env.size and env.size not in ("N/A", "?", "...") else "0 MB"
            _size_item = QTableWidgetItem(f"  {_size}")
            _size_item.setFont(_row_font)
            if _is_light_theme:
                _size_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 5, _size_item)

            created_str = ""
            if env.created:
                try:
                    dt = datetime.fromisoformat(env.created)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_str = env.created[:16]
            _created_item = QTableWidgetItem(f"  {created_str}")
            _created_item.setFont(_row_font)
            if _is_light_theme:
                _created_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 6, _created_item)

            # Default column
            default_env = self.config.get("default_env", "")
            default_item = QTableWidgetItem("⭐" if env.name == default_env else "")
            default_item.setTextAlignment(Qt.AlignCenter)
            default_item.setFlags(default_item.flags() & ~Qt.ItemIsEditable)
            self.env_table.setItem(i, 7, default_item)

        # Group envs by location
        _base_dir = str(self.venv_manager.base_dir)
        _home = str(Path.home())
        _base_envs = [e for e in envs if str(e.path).startswith(_base_dir)]
        _poetry_envs = [e for e in envs if e.env_type == "poetry"]
        _pipx_envs = [e for e in envs if e.env_type == "pipx"]
        # Remove poetry and pipx from base count (they have their own paths)
        _base_envs = [e for e in _base_envs if e.env_type not in ("poetry", "pipx")]

        def _fmt_size(envs_list):
            total = 0
            for e in envs_list:
                s = e.size or "0 MB"
                try:
                    n, u = s.strip().split()
                    n = float(n)
                    mult = {"B":1,"KB":1024,"MB":1024**2,"GB":1024**3,"TB":1024**4}.get(u,1)
                    total += n * mult
                except Exception:
                    pass
            for unit in ["B","KB","MB","GB","TB"]:
                if total < 1024:
                    return f"{total:.1f} {unit}"
                total /= 1024
            return "?"

        parts = []
        _total_all = _fmt_size(envs)
        parts.append(f"📂 {self.venv_manager.base_dir}  •  {len(_base_envs)} env(s)  •  {_fmt_size(_base_envs)}")
        if _poetry_envs:
            parts.append(f"📜 poetry  •  {len(_poetry_envs)} env(s)  •  {_fmt_size(_poetry_envs)}")
        if _pipx_envs:
            parts.append(f"📦 pipx  •  {len(_pipx_envs)} env(s)  •  {_fmt_size(_pipx_envs)}")
        parts.append(f"🗂 total  •  {_total_all}")
        self.info_label.setText("        ".join(parts))

        # Update package panel env dropdown
        env_list = [(e.name, e.path) for e in envs]
        self._last_env_list = env_list
        if self.package_panel is not None:
            if self.package_panel is not None: self.package_panel.populate_env_list(env_list)
        if self.settings_page is not None:
            self.settings_page.populate_vscode_envs(env_list)

        if not envs:
            self.loading_label.setVisible(False)
            self.statusBar().showMessage("No environments found")
            return

        # Start background worker for any envs with missing data ("...")
        missing_names = [
            self.env_table.item(i, 0).text().strip()
            for i in range(self.env_table.rowCount())
            if self.env_table.item(i, 2) and self.env_table.item(i, 2).text().strip() in ("...", "", "----")
        ]

        if missing_names:
            # Stop previous worker if running
            if hasattr(self, "_detail_worker") and self._detail_worker.isRunning():
                self._detail_worker.quit()
                self._detail_worker.wait(2000)

            self._detail_worker = EnvDetailWorker(
                self.venv_manager,
                [e.name for e in envs]  # pass all when force=True so worker checks needs_refresh
            )
            self._detail_worker.env_detail_ready.connect(self._on_env_detail_ready)
            self._detail_worker.all_done.connect(self._on_all_details_done)
            self._detail_worker.start()
        else:
            self._on_all_details_done()

    def _on_env_detail_ready(self, row, python_version, package_count, size):
        """Update a single row with detailed info from background thread."""
        if row < self.env_table.rowCount():
            _rv = str(python_version).strip()
            if _rv and _rv not in ("Unknown", "?", "..."):
                if _rv[0].isdigit():
                    _runtime_str = f"  Python {_rv}"
                else:
                    _runtime_str = f"  Python {_rv}"
            else:
                _runtime_str = "  ----"
            self.env_table.setItem(row, 3, QTableWidgetItem(_runtime_str))
            self.env_table.setItem(row, 4, QTableWidgetItem(f"  {package_count}"))
            _size = size if size and size not in ("N/A", "?", "...") else "0 MB"
            self.env_table.setItem(row, 5, QTableWidgetItem(f"  {_size}"))

    def _on_all_details_done(self):
        self.loading_label.setVisible(False)
        self.loading_label.setText("Loading environments...")  # reset text
        count = self.env_table.rowCount()
        self.statusBar().showMessage(f"Found {count} environment(s)")
        # Re-enable refresh button
        if hasattr(self, "_refresh_btn"):
            self._refresh_btn.setEnabled(True)
            self._refresh_btn.setText(f"🔄 {tr('refresh')}")

    def _update_info_label_fast(self, count):
        base_dir = self.config.get_venv_base_dir()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _update_info_label(self):
        base_dir = self.config.get_venv_base_dir()
        count = self.env_table.rowCount()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _on_env_selected(self):
        rows = self.env_table.selectionModel().selectedRows()
        has_selection = bool(rows)
        _sel_name = self.env_table.item(rows[0].row(), 0).text().strip() if has_selection else "(none)"
        self._log.debug(f"_on_env_selected: env={_sel_name!r} has_selection={has_selection}")
        self.btn_manage_pkgs.setEnabled(has_selection)
        self.btn_terminal.setEnabled(has_selection)
        # Resolve env_type for button visibility rules
        _sel_type = ""
        if has_selection:
            _rows = self.env_table.selectionModel().selectedRows()
            if _rows:
                _ti = self.env_table.item(_rows[0].row(), 1)
                if _ti:
                    _sel_type = _ti.data(Qt.UserRole) or _ti.text().strip().lower()
        _is_pipx   = _sel_type == "pipx"
        _is_poetry = _sel_type == "poetry"
        # Clone: hide for pipx
        self.btn_clone.setVisible(not _is_pipx)
        self.btn_clone.setEnabled(has_selection)
        # Rename: hide for pipx and poetry
        _show_rename = not _is_pipx and not _is_poetry
        self.btn_rename.setVisible(_show_rename)
        self.btn_rename.setEnabled(has_selection and _show_rename)
        if hasattr(self, "btn_rename_full"):
            self.btn_rename_full.setVisible(_show_rename)
            self.btn_rename_full.setEnabled(has_selection and _show_rename)
        self.btn_delete.setEnabled(has_selection)
        self.btn_export.setEnabled(has_selection)
        if hasattr(self, "btn_make_default"):
            self.btn_make_default.setEnabled(has_selection)

        if has_selection:
            row = rows[0].row()
            name = self.env_table.item(row, 0).text().strip()
            self.selected_env = name
            self.statusBar().showMessage(f"Selected: {name}")
            # Sync QL dropdown
            if hasattr(self, "ql_env_selector"):
                idx = self.ql_env_selector.findData(name)
                if idx >= 0:
                    self.ql_env_selector.blockSignals(True)
                    self.ql_env_selector.setCurrentIndex(idx)
                    self.ql_env_selector.blockSignals(False)
            # Sync package_panel — use actual path (handles pipx, poetry etc.)
            venv_path = self._get_env_path(name) or self.venv_manager.base_dir / name
            if venv_path.exists():
                if self.package_panel is not None: self.package_panel.set_venv(venv_path)
                # ── Track in recent envs (deferred — no UI blocking) ─────
                try:
                    type_item = self.env_table.item(row, 1)
                    raw_type = type_item.text().strip() if type_item else "venv"
                    env_type = "venv"
                    for k in ("uv", "poetry", "pipx", "conda", "venv"):
                        if k in raw_type.lower():
                            env_type = k
                            break
                    _vp = str(venv_path)
                    _nm = name
                    _et = env_type
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(300, lambda: self._track_recent(_nm, _vp, _et))
                except Exception:
                    pass
                # ─────────────────────────────────────────────────────

    def _open_default_env(self):
        """On startup, open default env in Packages if set."""
        default_env = self.config.get("default_env", "")
        if not default_env:
            return
        venv_path = self.venv_manager.base_dir / default_env
        if not venv_path.exists():
            return
        if self.package_panel is not None:
            self.package_panel.set_venv(venv_path)
        self._switch_page(0)
        # Sync env table selection
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == default_env:
                self.env_table.selectRow(row)
                break

    def _show_env_context_menu(self, pos):
        """Show right-click context menu on environment table."""
        self._log.debug(f"_show_env_context_menu at pos={pos.x()},{pos.y()}")
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        index = self.env_table.indexAt(pos)

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ font-size: {self._c()['fs_base']}px; }} QMenu::item {{ padding: 6px 20px; }}")

        if not index.isValid():
            # Boş alana sağ tık — genel işlemler
            a_new = QAction("➕ New Environment", self)
            a_new.triggered.connect(self._create_env)
            menu.addAction(a_new)

            a_refresh = QAction("🔄 Refresh", self)
            a_refresh.triggered.connect(lambda: self._refresh_env_list(force=True))
            menu.addAction(a_refresh)

            menu.exec(self.env_table.viewport().mapToGlobal(pos))
            return

        # Satırı seç
        self.env_table.selectRow(index.row())
        name = self._get_selected_env_name()
        if not name:
            return

        # Resolve env_type for this row
        _ctx_type = ""
        _type_item = self.env_table.item(index.row(), 1)
        if _type_item:
            _ctx_type = _type_item.data(Qt.UserRole) or _type_item.text().strip().lower()
        _ctx_is_pipx   = _ctx_type == "pipx"
        _ctx_is_poetry = _ctx_type == "poetry"

        a_manage = QAction("📦 Manage Packages", self)
        a_manage.triggered.connect(self._on_env_double_click)
        menu.addAction(a_manage)

        menu.addSeparator()

        a_terminal = QAction("🖥️ Open Terminal", self)
        a_terminal.triggered.connect(self._open_terminal)
        menu.addAction(a_terminal)

        a_folder = QAction("📁 Open Folder", self)
        a_folder.setToolTip("Open the environment folder in your file manager")
        a_folder.triggered.connect(self._open_env_folder)
        menu.addAction(a_folder)

        a_default = QAction("⭐ Make Default", self)
        a_default.triggered.connect(self._make_default_env)
        menu.addAction(a_default)

        menu.addSeparator()

        if not _ctx_is_pipx:
            a_clone = QAction("📋 Clone", self)
            a_clone.triggered.connect(self._clone_env)
            menu.addAction(a_clone)

        if not _ctx_is_pipx and not _ctx_is_poetry:
            a_rename = QAction("✏️ Rename (Name Only)", self)
            a_rename.setToolTip("Rename folder only — fast, but pip/python paths may break on Windows")
            a_rename.triggered.connect(self._rename_env_only)
            menu.addAction(a_rename)

            a_rename_full = QAction("🔄 Rename (Full)", self)
            a_rename_full.setToolTip("Clone with new name + delete old — slow but safe, all packages reinstalled")
            a_rename_full.triggered.connect(self._rename_env_full)
            menu.addAction(a_rename_full)

        export_sub = menu.addMenu("📤 Export")
        export_sub.addAction("📄 requirements.txt", self._export_requirements)
        export_sub.addAction("📄 requirements-frozen.txt", self._export_frozen)
        export_sub.addSeparator()
        export_sub.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_sub.addAction("📦 pyproject.toml", self._export_pyproject)
        export_sub.addAction("📊 JSON", self._export_json)
        export_sub.addSeparator()
        export_sub.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_sub.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_sub.addSeparator()
        export_sub.addAction("📋 Copy to Clipboard", self._export_clipboard)

        menu.addSeparator()

        a_delete = QAction("🗑️ Delete", self)
        a_delete.setObjectName("danger")
        a_delete.triggered.connect(self._delete_env)
        menu.addAction(a_delete)

        menu.exec(self.env_table.viewport().mapToGlobal(pos))

    def _make_default_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        current_default = self.config.get("default_env", "")
        if name == current_default:
            QMessageBox.information(self, "Default Env", f"'{name}' is already the default environment.")
            return
        reply = QMessageBox.question(
            self, "Make Default Environment",
            f"Set '{name}' as the default environment?\n\nVenvStudio will open this environment on startup.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config.set("default_env", name)
            self._refresh_env_list()
            self.statusBar().showMessage(f"✅ '{name}' set as default environment")

    def _on_env_double_click(self):
        self._open_package_manager()

    def _get_env_path(self, name: str) -> "Path | None":
        """Return actual path for env — handles pipx, poetry etc."""
        # 1. Check table Path column tooltip (fast)
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == name:
                path_item = self.env_table.item(row, 2)
                if path_item and path_item.toolTip():
                    return Path(path_item.toolTip())
                break
        # 2. Fallback: scan venv list (handles pipx home)
        try:
            for env in self.venv_manager.list_venvs_fast(skip_calc=True):
                if env.name == name:
                    return env.path
        except Exception:
            pass
        return self.venv_manager.base_dir / name

    def _get_selected_env_name(self):
        rows = self.env_table.selectionModel().selectedRows()
        if rows:
            return self.env_table.item(rows[0].row(), 0).text().strip()
        return ""

    def _create_env(self):
        from src.gui.env_dialog import EnvCreateDialog
        dialog = EnvCreateDialog(self.venv_manager, self.config, self)
        def _on_env_created(name):
            self._log.info(f"env_created: name={name!r} → invalidating cache + refreshing list")
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()
        dialog.env_created.connect(_on_env_created)
        dialog.exec()
        self._log.debug("_create_env: dialog closed → final cache invalidate + refresh")
        self.venv_manager.invalidate_all_caches()
        self._refresh_env_list()

    def _get_new_name_for_rename(self, name):
        """Yeni isim giriş dialog'u — ortak kullanım."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Environment",
            f"Enter new name for '{name}':",
            text=name,
        )
        if not ok or not new_name.strip() or new_name.strip() == name:
            return None
        new_name = new_name.strip()
        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in new_name):
            QMessageBox.warning(self, "Warning", "Name contains invalid characters.")
            return None
        return new_name

    def _rename_env_only(self):
        """Rename (Name Only) — sadece klasör rename, hızlı."""
        name = self._get_selected_env_name()
        if not name:
            return
        new_name = self._get_new_name_for_rename(name)
        if not new_name:
            return

        # Get env type and path from selected row for cmd panel display
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / name)

        # Update educational cmd panel
        self._update_cmd_panel(action="rename", env_type=_env_type, name=name, env_path=_display_path)

        self.rename_progress = QProgressDialog(
            f"Renaming '{name}' → '{new_name}'...", None, 0, 0, self
        )
        self.rename_progress.setWindowTitle("Renaming Environment")
        self.rename_progress.setMinimumWidth(400)
        self.rename_progress.setWindowModality(Qt.WindowModal)
        self.rename_progress.show()

        self._rename_worker = RenameOnlyWorker(self.venv_manager, name, new_name)
        self._rename_worker.progress.connect(
            lambda msg: self.rename_progress.setLabelText(f"⏳ {msg}")
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    def _rename_env_full(self):
        """Rename (Full) — clone + delete, tüm paketler yeniden kurulur."""
        name = self._get_selected_env_name()
        if not name:
            return
        new_name = self._get_new_name_for_rename(name)
        if not new_name:
            return

        reply = QMessageBox.question(
            self, "Rename (Full)",
            f"This will create '{new_name}' with all packages from '{name}', then delete '{name}'.\n\n"
            f"This may take a while. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Get env type and path from selected row for cmd panel display
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / name)

        # Update educational cmd panel
        self._update_cmd_panel(action="rename", env_type=_env_type, name=name, env_path=_display_path)

        self.rename_progress = QProgressDialog(
            f"Renaming '{name}' → '{new_name}'...", "Cancel", 0, 0, self
        )
        self.rename_progress.setWindowTitle("Renaming Environment (Full)")
        self.rename_progress.setMinimumWidth(400)
        self.rename_progress.setWindowModality(Qt.WindowModal)
        self.rename_progress.show()

        self._rename_worker = RenameFullWorker(self.venv_manager, name, new_name)
        self._rename_worker.progress.connect(
            lambda msg: self.rename_progress.setLabelText(f"⏳ {msg}")
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    # Eski fonksiyon — geriye dönük uyumluluk
    def _rename_env(self):
        self._rename_env_only()

    def _on_rename_finished(self, success, message):
        self.rename_progress.close()
        if success:
            # Force memory cache clear so deleted env disappears immediately
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            first_line = message.splitlines()[0] if message else "Failed"
            QMessageBox.critical(self, "Error", message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _delete_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        # B182 fix: figure out env type BEFORE the confirm dialog, so pipx
        # users see a meaningful warning. The previous wording suggested
        # the "environment" would be deleted along with all its packages
        # — for pipx that would mean wiping pipx itself plus every app
        # the user installed outside VenvStudio. Be explicit instead.
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"

        if _env_type == "pipx":
            confirm_msg = (
                f"Stop tracking the '{name}' pipx installation?\n\n"
                f"This will remove the row from VenvStudio's environment list.\n\n"
                f"⚠ Your installed pipx apps and pipx itself will NOT be removed.\n"
                f"To uninstall a specific app, use the package panel "
                f"or run: pipx uninstall <app>"
            )
        else:
            confirm_msg = (
                f"Are you sure you want to delete '{name}'?\n\n"
                f"This will permanently remove the environment and all installed packages."
            )

        reply = QMessageBox.warning(
            self, "Delete Environment", confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # No popup — progress shown in Command Reference panel below

            self._deleting_env_name = name
            _display_path = _env_path or str(self.venv_manager.base_dir / name)
            # B182: remember the real env path/type for cache invalidation in
            # _on_delete_finished — pipx/poetry/uv envs live OUTSIDE
            # venv_manager.base_dir, so the old code that built the cache key
            # from `base_dir / name` was looking up the wrong key and the
            # stale entry survived a delete.
            self._deleting_env_path = _env_path
            self._deleting_env_type = _env_type

            # Update the educational command panel at the bottom of the env page
            self._update_cmd_panel(action="delete", env_type=_env_type, name=name, env_path=_display_path)

            self._delete_worker = DeleteWorker(self.venv_manager, name, env_path=_env_path, env_type=_env_type)
            def _on_del_progress(msg):
                if hasattr(self, "_cmd_panel_live"):
                    self._cmd_panel_live.setText(f"▶ {msg}")
            self._delete_worker.progress.connect(_on_del_progress)
            self._delete_worker.finished.connect(self._on_delete_finished)
            self._delete_worker.start()

    def _on_delete_finished(self, success, message):
        deleted_name = getattr(self, "_deleting_env_name", "")
        deleted_path = getattr(self, "_deleting_env_path", None)
        deleted_type = getattr(self, "_deleting_env_type", "venv")
        if success:
            self._log.info(
                f"env_deleted: name={deleted_name!r} type={deleted_type!r} "
                f"path={deleted_path!r} → cleaning cache + removing row"
            )
            # Remove pkg_list cache entry for the deleted env
            try:
                from src.core.venv_manager import VenvManager
                from pathlib import Path as _P
                vm = VenvManager(_P(self.config.get_venv_base_dir()))
                all_cache = vm._load_all_cache()
                # B182: pipx/poetry/uv envs live OUTSIDE base_dir — use the
                # actual env path captured in _delete_env, not the assumed
                # `base_dir / name`. Falls back to base_dir/name only if the
                # real path is missing (legacy / classic venv path).
                real_path = _P(deleted_path) if deleted_path else (self.venv_manager.base_dir / deleted_name)
                if deleted_name:
                    # Cache key uses the same normalisation as venv_manager
                    try:
                        norm_path = vm._cache_key(real_path)
                    except Exception:
                        norm_path = str(real_path).replace("\\", "/")
                    pkg_key = "pkg_list:" + norm_path
                    if pkg_key in all_cache:
                        all_cache.pop(pkg_key, None)
                        self._log.debug(f"env_deleted: removed pkg_list cache key={pkg_key!r}")
                    # Also remove env meta cache entry by the same normalised key
                    if norm_path in all_cache:
                        all_cache.pop(norm_path, None)
                        self._log.debug(f"env_deleted: removed env meta cache key={norm_path!r}")
                    vm._save_all_cache(all_cache)
                    vm.invalidate_cache(real_path)
            except Exception as e:
                self._log.warning(f"env_deleted: cache cleanup error: {e}")
            # Clear package panel launcher state
            if self.package_panel is not None:
                self.package_panel._launcher_py_version_cache.clear()
                self.package_panel._update_launcher_status()
            # B182: previously called _refresh_env_list(force=True) here, which
            # re-scanned every env on disk and ran subprocess calls for each.
            # Even though only one row changed, the user saw a "Refreshing
            # environments — please wait..." banner stuck for several seconds.
            # Now we do a surgical update: remove the row from the table and
            # purge the in-memory env list cache for this env. Anything else
            # the user is looking at stays exactly as it was.
            self._remove_env_row_inplace(deleted_name, deleted_path)

            # B182: for pipx, the user expects the row to come back as a
            # fresh empty pipx tracker (zero apps installed via VenvStudio).
            # Re-create the marker file and add the row back to the table
            # in one shot — no full _refresh_env_list, no "Refreshing..."
            # banner, no subprocess scans.
            if deleted_type == "pipx":
                try:
                    self._readd_empty_pipx_row()
                except Exception as _e:
                    self._log.warning(f"pipx readd skipped: {_e}")

            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            self._log.warning(f"env_delete_failed: name={deleted_name!r} error={message!r}")
            first_line = message.splitlines()[0] if message else "Failed"
            QMessageBox.critical(self, "Error", message)
            # Failure path: do a normal refresh (no force) so the user sees
            # the actual current state without a heavy re-scan.
            self._refresh_env_list()
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _refresh_current_env_row(self) -> None:
        """Update only the active env's row after a package / launch app /
        preset install or uninstall finishes. We invalidate the env's
        cache (so package_count + size are recomputed), then re-read the
        single row in place. The other rows in the table aren't touched
        and the user doesn't see a "Refreshing..." banner.

        Falls back to a normal _refresh_env_list if anything goes wrong —
        the user always ends up with a current view, just maybe not as
        snappy.
        """
        try:
            # Find the active env path from the package panel
            pp = getattr(self, "package_panel", None)
            if pp is None:
                self._refresh_env_list()
                return
            cur_path = getattr(pp, "_current_venv_path", None)
            if not cur_path:
                self._refresh_env_list()
                return
            from pathlib import Path as _P
            cur_path = _P(str(cur_path))

            # 1) Drop cache entries for this env so the next read recomputes
            try:
                self.venv_manager.invalidate_cache(cur_path)
            except Exception as _e:
                self._log.debug(f"refresh_current_row: invalidate_cache: {_e}")

            # Also drop pkg_list and any meta cache entries from the on-disk cache
            try:
                from src.core.venv_manager import VenvManager
                vm = VenvManager(_P(self.config.get_venv_base_dir()))
                all_cache = vm._load_all_cache()
                try:
                    norm_path = vm._cache_key(cur_path)
                except Exception:
                    norm_path = str(cur_path).replace("\\", "/")
                changed = False
                for _k in (norm_path, "pkg_list:" + norm_path):
                    if _k in all_cache:
                        all_cache.pop(_k, None)
                        changed = True
                if changed:
                    vm._save_all_cache(all_cache)
            except Exception as _e:
                self._log.debug(f"refresh_current_row: cache prune: {_e}")

            # 2) Locate the row in the env table by path or name
            row = -1
            for r in range(self.env_table.rowCount()):
                _path_item = self.env_table.item(r, 2)
                _row_path = ""
                if _path_item:
                    _row_path = _path_item.toolTip() or _path_item.text().strip()
                if _row_path and _P(_row_path).resolve() == cur_path.resolve():
                    row = r
                    break
            if row < 0:
                # Couldn't pinpoint the row; do a normal (light) refresh
                self._refresh_env_list()
                return

            # 3) Re-read the env's metadata and update the row's cells in-place
            env_info = None
            try:
                # list_venvs_fast returns all envs; pick the one with a matching path
                _envs = self.venv_manager.list_venvs_fast(skip_calc=False)
                for _e in _envs:
                    try:
                        if _P(str(_e.path)).resolve() == cur_path.resolve():
                            env_info = _e
                            break
                    except Exception:
                        pass
            except Exception as _e:
                self._log.debug(f"refresh_current_row: list_venvs_fast: {_e}")

            if env_info is None:
                # Last resort — a normal refresh will rebuild the whole table
                self._refresh_env_list()
                return

            # Update only the cells that change: runtime (3), packages (4),
            # size (5). Name / type / path / created stay the same.
            from PySide6.QtWidgets import QTableWidgetItem
            from PySide6.QtGui import QFont as _QFont, QColor as _QColor

            _is_light = False
            try:
                _bg = (self._c().get("bg") or "").lstrip("#")
                if len(_bg) >= 6:
                    _r = int(_bg[0:2], 16)
                    _g = int(_bg[2:4], 16)
                    _b = int(_bg[4:6], 16)
                    _is_light = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            except Exception:
                pass
            _bold = _QFont()
            _bold.setBold(True)
            _fg_dark = _QColor("#1f2937") if _is_light else None

            _rv = str(env_info.python_version).strip()
            _runtime_str = (
                f"  Python {_rv}" if (_rv and _rv not in ("Unknown", "?", "...")) else "  ----"
            )
            _runtime_item = QTableWidgetItem(_runtime_str)
            _runtime_item.setFont(_bold)
            if _fg_dark is not None:
                _runtime_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 3, _runtime_item)

            _pkg = str(env_info.package_count) if env_info.package_count else "0"
            _pkg_item = QTableWidgetItem(f"  {_pkg}")
            _pkg_item.setFont(_bold)
            if _fg_dark is not None:
                _pkg_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 4, _pkg_item)

            _size = (
                env_info.size if env_info.size and env_info.size not in ("N/A", "?", "...")
                else "0 MB"
            )
            _size_item = QTableWidgetItem(f"  {_size}")
            _size_item.setFont(_bold)
            if _fg_dark is not None:
                _size_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 5, _size_item)

            # Refresh the header summary strip (e.g. "3 env(s) · 2.4 GB")
            try:
                if hasattr(self, "_update_env_summary"):
                    self._update_env_summary()
            except Exception:
                pass
            self._log.debug(
                f"refresh_current_row: updated row {row} "
                f"(pkgs={_pkg}, size={_size})"
            )
        except Exception as e:
            self._log.warning(f"_refresh_current_env_row failed: {e} — fallback to list refresh")
            try:
                self._refresh_env_list()
            except Exception:
                pass

    def _remove_env_row_inplace(self, name: str, path: str = None) -> None:
        """B182: surgically drop a single row from the env table without
        triggering a full _refresh_env_list. Also drops the env from the
        VenvManager's in-memory list cache so a later normal refresh
        (e.g. switching pages) won't bring it back from the in-process
        cache.

        Falls back to a normal (non-force) refresh if the row can't be
        located by name+path — that path still avoids the heavy
        force=True rescan that put a "Refreshing..." banner on screen.
        """
        try:
            removed_row = -1
            for r in range(self.env_table.rowCount()):
                name_item = self.env_table.item(r, 0)
                path_item = self.env_table.item(r, 2)
                row_name = (name_item.text().strip() if name_item else "")
                row_path = ""
                if path_item:
                    row_path = path_item.toolTip() or path_item.text().strip()
                if row_name == name and (not path or row_path == path or not row_path):
                    removed_row = r
                    break
            if removed_row >= 0:
                self.env_table.removeRow(removed_row)
                self._log.debug(f"env_deleted: removed row {removed_row} from table")
            else:
                # Fallback — couldn't pinpoint the row, do a light refresh
                self._log.debug(
                    f"env_deleted: row not found for name={name!r} path={path!r} "
                    f"→ falling back to light refresh"
                )
                self._refresh_env_list()
                return

            # Drop the env from the in-memory list cache for this base_dir
            try:
                from src.core.venv_manager import VenvManager
                base_key = getattr(self.venv_manager, "_base_key", None)
                if base_key and base_key in VenvManager._mem_envs:
                    VenvManager._mem_envs[base_key] = [
                        e for e in VenvManager._mem_envs[base_key]
                        if e.name != name
                    ]
            except Exception as e:
                self._log.debug(f"env_deleted: in-memory cache prune skipped: {e}")

            # Also sync the quick-launch env selector if present
            if hasattr(self, "ql_env_selector"):
                idx = self.ql_env_selector.findData(name)
                if idx >= 0:
                    self.ql_env_selector.removeItem(idx)

            # Update header counters (e.g. "3 env(s) · 2.4 GB"). These come
            # from the venv_manager's list, so re-render that strip only.
            try:
                if hasattr(self, "_update_env_summary"):
                    self._update_env_summary()
            except Exception:
                pass
        except Exception as e:
            self._log.warning(f"_remove_env_row_inplace failed: {e} — falling back")
            self._refresh_env_list()

    def _readd_empty_pipx_row(self) -> None:
        """B182: re-create the pipx tracker marker and insert a fresh row
        into the env table — without calling _refresh_env_list (which
        would re-scan every env on disk and freeze the UI for seconds).

        We assume the user just deleted the pipx row, which removed the
        ``.venvstudio_env`` marker but left ``~/.local/share/pipx``
        (or ``%LOCALAPPDATA%\\pipx`` on Windows) intact. We write a new
        empty marker, then add a row with package_count=0 to the table.
        Real package counts and python versions will be picked up on the
        next natural refresh — by then it's irrelevant because the row
        is already on screen.
        """
        from pathlib import Path as _P
        import json as _json
        import sys as _sys
        import os as _os
        from datetime import datetime as _dt

        # 1) Locate pipx home (same logic as venv_manager.list_venvs_fast)
        try:
            from src.utils.platform_utils import get_pipx_home
            pipx_home = get_pipx_home()
        except Exception:
            pipx_home = None
        if not pipx_home:
            if _sys.platform == "win32":
                pipx_home = _os.path.join(_os.environ.get("LOCALAPPDATA", ""), "pipx")
            else:
                pipx_home = _os.path.join(_os.path.expanduser("~"), ".local", "share", "pipx")
        pipx_path = _P(pipx_home)
        if not pipx_path.exists():
            self._log.debug(f"pipx readd: pipx_home not found at {pipx_path} — nothing to track")
            return

        # 2) Re-create the marker so VenvStudio recognises it again next start
        marker = pipx_path / ".venvstudio_env"
        try:
            marker_data = {
                "name": "pipx",
                "env_type": "pipx",
                "created": _dt.now().strftime("%Y-%m-%d %H:%M"),
                "python_version": f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}",
            }
            with open(marker, "w", encoding="utf-8") as f:
                _json.dump(marker_data, f, indent=2)
            self._log.info(f"pipx readd: wrote marker at {marker}")
        except Exception as e:
            self._log.warning(f"pipx readd: marker write failed: {e}")
            return

        # 3) Add row to the env table directly — no subprocess, no rescan
        try:
            row = self.env_table.rowCount()
            self.env_table.insertRow(row)

            from PySide6.QtWidgets import QTableWidgetItem
            from PySide6.QtCore import Qt as _Qt
            from PySide6.QtGui import QColor as _QColor, QFont as _QFont

            # Detect light theme for colour choices (matches _refresh_env_list)
            _is_light = False
            try:
                _bg = (self._c().get("bg") or "").lstrip("#")
                if len(_bg) >= 6:
                    _r = int(_bg[0:2], 16)
                    _g = int(_bg[2:4], 16)
                    _b = int(_bg[4:6], 16)
                    _is_light = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            except Exception:
                pass
            _pipx_color = "#0e7490" if _is_light else "#89dceb"
            _path_color = (self._c().get("fg_secondary")
                           or self._c().get("fg")
                           or ("#444" if _is_light else "#bac2de"))
            _bold = _QFont()
            _bold.setBold(True)

            # Column 0: Name
            name_item = QTableWidgetItem("  pipx")
            name_item.setFlags(name_item.flags() & ~_Qt.ItemIsEditable)
            name_item.setForeground(_QColor(_pipx_color))
            name_item.setFont(_bold)
            self.env_table.setItem(row, 0, name_item)

            # Column 1: Type — store env_type in UserRole so other code paths
            # (clone, delete, etc.) can read it back.
            type_item = QTableWidgetItem("  📦 pipx")
            type_item.setData(_Qt.UserRole, "pipx")
            type_item.setFlags(type_item.flags() & ~_Qt.ItemIsEditable)
            type_item.setForeground(_QColor(_pipx_color))
            type_item.setFont(_bold)
            self.env_table.setItem(row, 1, type_item)

            # Column 2: Path
            path_item = QTableWidgetItem(f"  {pipx_path}")
            path_item.setToolTip(str(pipx_path))
            path_item.setFlags(path_item.flags() & ~_Qt.ItemIsEditable)
            path_item.setForeground(_QColor(_path_color))
            self.env_table.setItem(row, 2, path_item)

            # Column 3: Runtime (Python version)
            py_ver = marker_data["python_version"]
            runtime_item = QTableWidgetItem(py_ver)
            runtime_item.setFlags(runtime_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 3, runtime_item)

            # Column 4: Packages — empty pipx == 0
            pkg_item = QTableWidgetItem("0")
            pkg_item.setFlags(pkg_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 4, pkg_item)

            # Column 5: Size — unknown, leave blank
            size_item = QTableWidgetItem("—")
            size_item.setFlags(size_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 5, size_item)

            # Column 6: Created
            created_item = QTableWidgetItem(marker_data["created"])
            created_item.setFlags(created_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 6, created_item)

            self._log.info(f"pipx readd: row inserted at index {row}")
        except Exception as e:
            self._log.warning(f"pipx readd: table insert failed: {e}")
            # Last resort: just trigger a light refresh, no force
            self._refresh_env_list()

    def _clone_env(self):
        source = self._get_selected_env_name()
        if not source:
            return
        new_name, ok = QInputDialog.getText(
            self, "Clone Environment",
            f"Enter name for the clone of '{source}':",
            text=f"{source}-clone",
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        # Get env type and path for educational cmd panel
        _src_env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _src_env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / source)

        # Update educational cmd panel
        self._update_cmd_panel(action="clone", env_type=_src_env_type, name=source, env_path=_display_path)

        # Progress dialog
        self.clone_progress = QProgressDialog(
            f"Cloning '{source}' to '{new_name}'...", "Cancel", 0, 0, self
        )
        self.clone_progress.setWindowTitle("Cloning Environment")
        self.clone_progress.setMinimumWidth(400)
        self.clone_progress.setWindowModality(Qt.WindowModal)
        self.clone_progress.show()

        # Worker
        self.clone_worker = CloneWorker(self.venv_manager, source, new_name)
        def _on_clone_progress(msg):
            self.clone_progress.setLabelText(f"⏳ {msg}")
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"▶ {msg}")
        self.clone_worker.progress.connect(_on_clone_progress)
        self.clone_worker.finished.connect(self._on_clone_finished)
        self.clone_progress.canceled.connect(self._on_clone_cancel)
        self.clone_worker.start()

    def _on_clone_finished(self, success, message):
        self.clone_progress.close()
        if success:
            # Force memory cache clear so deleted env disappears immediately
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            if "cancelled" not in message.lower():
                QMessageBox.critical(self, "Error", message)
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                first_line = message.splitlines()[0] if message else "Failed"
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _on_clone_cancel(self):
        if hasattr(self, 'clone_worker') and self.clone_worker.isRunning():
            self.clone_worker.cancel()
            self.clone_worker.wait(5000)
            self._refresh_env_list()

    # ── Export helpers (Environments page) ──

    def _get_env_pip_manager(self):
        """Get PipManager for the selected environment."""
        name = self._get_selected_env_name()
        if not name:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return None
        from src.core.pip_manager import PipManager
        venv_path = self.venv_manager.base_dir / name
        return PipManager(venv_path)

    def _get_env_freeze_and_version(self):
        """Helper: get freeze content and python version for selected env."""
        import subprocess
        from src.utils.platform_utils import get_python_executable, subprocess_args
        pm = self._get_env_pip_manager()
        if not pm:
            return None, None
        freeze = pm.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", "No packages to export.")
            return None, None
        py_ver = "3.12"
        try:
            exe = get_python_executable(pm.venv_path)
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10,
                **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            py_ver = ".".join(ver.split(".")[:2])
        except Exception:
            pass
        return freeze, py_ver

    def _export_requirements(self):
        freeze, _ = self._get_env_freeze_and_version()
        if not freeze:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_dockerfile(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        dockerfile = (
            f"# Auto-generated by VenvStudio\n"
            f"FROM python:{py_ver}-slim\n\n"
            f"WORKDIR /app\n\n"
            f"RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
            f"    gcc \\\n"
            f"    && rm -rf /var/lib/apt/lists/*\n\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n\n"
            f"COPY . .\n\n"
            f"# CMD [\"python\", \"main.py\"]\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Dockerfile", "Dockerfile", "All Files (*)"
        )
        if filepath:
            req_path = Path(filepath).parent / "requirements.txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported:\n  📄 {filepath}\n  📄 {req_path}\n\n"
                    f"Build: docker build -t myapp ."
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_docker_compose(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        compose = (
            f"# Auto-generated by VenvStudio\n"
            f"version: '3.8'\n\n"
            f"services:\n"
            f"  app:\n"
            f"    build: .\n"
            f"    container_name: myapp\n"
            f"    ports:\n"
            f"      - \"8000:8000\"\n"
            f"    volumes:\n"
            f"      - .:/app\n"
            f"    environment:\n"
            f"      - PYTHONUNBUFFERED=1\n"
        )
        dockerfile = (
            f"FROM python:{py_ver}-slim\n"
            f"WORKDIR /app\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n"
            f"COPY . .\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export docker-compose.yml", "docker-compose.yml",
            "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            base = Path(filepath).parent
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(compose)
                with open(base / "Dockerfile", "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(base / "requirements.txt", "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported 3 files to {base}\n\nRun: docker-compose up --build"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_pyproject(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        deps = "\n".join(f'    "{l.strip()}",' for l in freeze.strip().splitlines()
                         if l.strip() and not l.startswith("#"))
        content = (
            f'[build-system]\nrequires = ["setuptools>=68.0", "wheel"]\n'
            f'build-backend = "setuptools.backends._legacy:_Backend"\n\n'
            f'[project]\nname = "myproject"\nversion = "0.1.0"\n'
            f'requires-python = ">={py_ver}"\n'
            f'dependencies = [\n{deps}\n]\n'
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export pyproject.toml", "pyproject.toml",
            "TOML Files (*.toml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_conda_yml(self):
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        pip_deps = "\n".join(f"    - {l.strip()}" for l in freeze.strip().splitlines()
                             if l.strip() and not l.startswith("#"))
        content = (
            f"name: myenv\nchannels:\n  - defaults\n  - conda-forge\n"
            f"dependencies:\n  - python={py_ver}\n  - pip\n  - pip:\n{pip_deps}\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export environment.yml", "environment.yml",
            "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported to:\n{filepath}\n\nCreate: conda env create -f environment.yml"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_clipboard(self):
        freeze, _ = self._get_env_freeze_and_version()
        if not freeze:
            return
        QApplication.clipboard().setText(freeze)
        count = len(freeze.strip().splitlines())
        self.statusBar().showMessage(f"📋 {count} packages copied to clipboard!")
        QMessageBox.information(self, "✅ Copied", f"{count} packages copied to clipboard.")

    def _export_frozen(self):
        """Export requirements with SHA-256 hashes (--require-hashes compatible)."""
        name = self._get_selected_env_name()
        if not name:
            return
        venv_path = self.venv_manager.base_dir / name
        import subprocess, os, tempfile, hashlib, glob
        from src.utils.platform_utils import subprocess_args
        if os.name == "nt":
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            pip_exe = venv_path / "bin" / "pip"
        if not pip_exe.exists():
            QMessageBox.warning(self, "Error", "pip not found in this environment.")
            return

        # Step 1: get plain freeze list
        try:
            result = subprocess.run(
                [str(pip_exe), "freeze"],
                **subprocess_args(capture_output=True, text=True, timeout=30)
            )
            freeze_lines = [l for l in result.stdout.strip().splitlines() if l and not l.startswith("#")]
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if not freeze_lines:
            QMessageBox.information(self, "Info", "No packages installed.")
            return

        # Step 2: download wheels into tmp dir and hash them
        progress = QMessageBox(self)
        progress.setWindowTitle("Generating Hashes")
        progress.setText(f"Downloading {len(freeze_lines)} packages to compute hashes...\nThis may take a moment.")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        hashed_lines = []
        failed = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for pkg_spec in freeze_lines:
                try:
                    dl = subprocess.run(
                        [str(pip_exe), "download", "--no-deps", "--dest", tmp_dir, pkg_spec],
                        **subprocess_args(capture_output=True, text=True, timeout=120)
                    )
                    # Find the downloaded file(s) for this package
                    pkg_name = pkg_spec.split("==")[0].strip() if "==" in pkg_spec else pkg_spec.strip()
                    downloaded = glob.glob(os.path.join(tmp_dir, f"{pkg_name.replace('-','_')}*")) + \
                                 glob.glob(os.path.join(tmp_dir, f"{pkg_name}*"))
                    # Pick the newest file
                    downloaded = sorted(set(downloaded), key=os.path.getmtime, reverse=True)
                    if downloaded:
                        fpath = downloaded[0]
                        sha256 = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
                        hashed_lines.append(f"{pkg_spec} \\\n    --hash=sha256:{sha256}")
                        os.remove(fpath)
                    else:
                        # Download failed or not found — add without hash with comment
                        hashed_lines.append(f"{pkg_spec}  # hash unavailable")
                        failed.append(pkg_spec)
                except Exception:
                    hashed_lines.append(f"{pkg_spec}  # hash unavailable")
                    failed.append(pkg_spec)

        progress.close()

        header = (
            "# Generated by VenvStudio — requirements with SHA-256 hashes\n"
            "# Install with: pip install --require-hashes -r requirements-frozen.txt\n"
            "#\n"
        )
        content = header + "\n".join(hashed_lines) + "\n"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Frozen Requirements", "requirements-frozen.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                msg = f"Exported {len(freeze_lines)} packages to:\n{filepath}"
                if failed:
                    msg += f"\n\n⚠️ {len(failed)} package(s) could not be hashed (marked in file)."
                QMessageBox.information(self, "✅ Success", msg)
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))



    def _export_json(self):
        """Export environment info as JSON."""
        import json
        name = self._get_selected_env_name()
        if not name:
            return
        freeze, py_ver = self._get_env_freeze_and_version()
        if not freeze:
            return
        packages = []
        for line in freeze.strip().splitlines():
            if "==" in line:
                pkg, ver = line.split("==", 1)
                packages.append({"name": pkg.strip(), "version": ver.strip()})
            else:
                packages.append({"name": line.strip(), "version": ""})
        data = {
            "environment": name,
            "python_version": py_ver,
            "package_count": len(packages),
            "packages": packages,
        }
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", f"{name}.json", "JSON Files (*.json)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_package_manager(self):
        name = self._get_selected_env_name()
        if not name:
            return
        # Use real path (handles pipx: ~/.local/share/pipx, poetry: ~/.cache/pypoetry/...)
        venv_path = self._get_env_path(name) or (self.venv_manager.base_dir / name)
        if self.package_panel is not None: self.package_panel.set_venv(venv_path)
        self._switch_page(0)

    def _open_terminal(self):
        name = self._get_selected_env_name()
        if not name:
            return
        self._log.info(f"_open_terminal: env={name!r}")
        # Ensure package_panel has the correct real path for this env before
        # delegating (pipx/poetry live outside base_dir).
        real_path = self._get_env_path(name) or (self.venv_manager.base_dir / name)
        cur = getattr(self.package_panel, "_current_venv_path", None)
        if cur is None or Path(cur) != Path(real_path):
            self._log.debug(f"_open_terminal: syncing package_panel to {real_path}")
            if self.package_panel is not None: self.package_panel.set_venv(real_path)
        # Delegate to package_panel which handles all env types correctly
        if self.package_panel is not None: self.package_panel._open_terminal_here()
        self.statusBar().showMessage(f"Opened terminal for '{name}'")

    def _open_env_folder(self):
        """Open the selected environment's folder in the system file manager."""
        name = self._get_selected_env_name()
        if not name:
            return
        real_path = self._get_env_path(name) or (self.venv_manager.base_dir / name)
        self._log.info(f"_open_env_folder: env={name!r} path={real_path}")
        try:
            from src.utils.platform_utils import open_folder
            ok, msg = open_folder(real_path)
            if ok:
                self.statusBar().showMessage(f"📁 {msg}")
            else:
                self._log.warning(f"_open_env_folder failed: {msg}")
                QMessageBox.warning(self, "Open Folder", msg)
        except Exception as e:
            self._log.error(f"_open_env_folder error: {e}")
            QMessageBox.critical(self, "Error", f"Could not open folder:\n{e}")

    def _open_settings(self):
        """Navigate to the settings page."""
        self._switch_page(2)

    def _set_theme(self, theme_name):
        # B184 fix: ConfigManager.set() already auto-saves to disk, but
        # call save() explicitly anyway as a belt-and-suspenders move.
        # The real bug for this issue was in AppearanceMixin's
        # _on_theme_cb_toggled, which silently reset the theme to "dark"
        # whenever the Settings page loaded with the theme checkbox off.
        #
        # B184 v2: View menu sends "light"/"dark", but the styles module
        # only registers specific names like "light-latte", "light-github",
        # "dark" (= Catppuccin Mocha). A bare "light" silently fell back
        # to dark on the next app start. Map the menu shortcut to a real
        # theme id here so what's saved is what's loaded.
        _menu_alias = {
            "light": "light-latte",  # default light variant
        }
        theme_name = _menu_alias.get(theme_name, theme_name)
        self.config.set("theme", theme_name)
        for _save_attr in ("save", "_save", "save_config", "flush", "write"):
            _fn = getattr(self.config, _save_attr, None)
            if callable(_fn):
                try:
                    _fn()
                    break
                except Exception:
                    continue
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme. Guarded against re-entrant calls and
        RuntimeError during screen transitions (dual-monitor DPI changes).
        """
        if self._applying_theme:
            return  # prevent re-entrant calls during screen change
        self._applying_theme = True
        try:
            theme = self.config.get("theme", "dark")
            font_family = self.config.get("font_secondary_family", "") or self.config.get("font_family", "")
            font_size = self.config.get("font_secondary_size", 13) or self.config.get("font_size", 13)
            primary_family = self.config.get("font_primary_family", "")
            primary_size = self.config.get("font_primary_size", 22)
            tertiary_family = self.config.get("font_tertiary_family", "")
            tertiary_size = self.config.get("font_tertiary_size", 11)
            self.setStyleSheet(get_theme(
                theme, font_family=font_family, font_size=font_size,
                primary_family=primary_family, primary_size=primary_size,
                tertiary_family=tertiary_family, tertiary_size=tertiary_size
            ))
            if hasattr(self, "package_panel"):
                if self.package_panel is not None: self.package_panel.apply_theme(theme)
            if hasattr(self, "settings_page"):
                if self.settings_page is not None:
                    try:
                        self.settings_page._refresh_styles()
                    except Exception:
                        pass
            # B183 fix: learn_page was previously skipped during theme switch,
            # so it stayed in dark colours when the user picked light theme.
            # Try multiple known refresh entry points to stay compatible if
            # the LearnPage API changes.
            if hasattr(self, "learn_page") and self.learn_page is not None:
                try:
                    if hasattr(self.learn_page, "apply_theme"):
                        self.learn_page.apply_theme(theme)
                    elif hasattr(self.learn_page, "_refresh_styles"):
                        self.learn_page._refresh_styles()
                    else:
                        # Last resort: re-apply the global stylesheet to force a repaint
                        self.learn_page.setStyleSheet(self.learn_page.styleSheet())
                except Exception:
                    pass
            # B183 fix: env_table item colours (uv yellow, poetry purple, etc.)
            # are baked into items at refresh time. Without re-running
            # _refresh_env_list after a theme switch, items keep the old
            # palette's pastel colours and look unreadable on light themes.
            if hasattr(self, "env_table") and self.env_table is not None:
                try:
                    self.env_table.setStyleSheet(
                        f"QTableWidget {{ font-size: 16px; "
                        f"color: {self._c()['fg']}; }}"
                        f"QTableWidget::item {{ padding: 8px 12px; font-weight: bold; font-size: 16px; }}"
                        f"QHeaderView::section {{ font-size: 15px; "
                        f"font-weight: bold; padding: 10px; }}"
                    )
                    # Re-render rows with the new theme's colours. Use the
                    # cached env list so this is cheap (no subprocess).
                    self._refresh_env_list(force=False)
                except Exception:
                    pass
            self._refresh_sidebar_styles()
        except RuntimeError:
            # Widget may be in an unstable state during screen transition
            pass
        finally:
            self._applying_theme = False

    def _refresh_sidebar_styles(self):
        """Re-apply inline styles on sidebar widgets that don't inherit QSS."""
        try:
            c = self._c()
            if hasattr(self, "ql_sep"):
                self.ql_sep.setStyleSheet(f"background-color: {c['border']}; max-height: 1px;")
            if hasattr(self, "ql_title"):
                self.ql_title.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 2px 0;")
            if hasattr(self, "ql_env_selector"):
                self.ql_env_selector.setStyleSheet(
                    f"background-color: {c['input_bg']}; color: {c['fg']}; "
                    f"border: 1px solid {c['border']}; border-radius: 6px; padding: 4px 8px; "
                    f"QComboBox QAbstractItemView {{ background-color: {c['card']}; color: {c['fg']}; "
                    f"selection-background-color: {c['accent']}; selection-color: {c['accent_fg']}; }}"
                )
            if hasattr(self, "ql_buttons_widget"):
                for btn in self.ql_buttons_widget.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton):
                    btn.setStyleSheet(
                        f"QPushButton {{ text-align: left; padding: 6px 10px; border-radius: 6px; "
                        f"background-color: {c['sidebar']}; color: {c['fg']}; "
                        f"border: 1px solid {c['border']}; }}"
                        f"QPushButton:hover {{ background-color: {c['hover']}; border-color: {c['accent']}; }}"
                    )
            if hasattr(self, "version_label"):
                self.version_label.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
            if hasattr(self, "footer_label"):
                self.footer_label.setStyleSheet(f"color: {c['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        except Exception:
            pass

    def _connect_screen_changed(self):
        """Connect to windowHandle().screenChanged so theme is re-applied
        safely when the window moves between monitors with different DPI.
        """
        try:
            handle = self.windowHandle()
            if handle:
                handle.screenChanged.connect(self._on_screen_changed)
        except Exception:
            pass  # windowHandle() can return None before show()

    def _on_screen_changed(self, new_screen):
        """Re-apply theme after a short delay so Qt finishes its internal
        DPI recalculation before we touch stylesheets.
        """
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._apply_theme)

    def _on_theme_changed(self, theme_name):
        """Handle theme change from settings page."""
        self._apply_theme()

    def _on_font_changed(self, family, size):
        """Handle font change from settings page — rebuild stylesheet with new font."""
        self._apply_theme()

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
        import platform as _platform
        if _platform.system().lower() != "linux":
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

    def _on_settings_saved(self):
        """Handle settings saved - refresh env list with potentially new base dir."""
        new_dir = self.config.get_venv_base_dir()
        self.venv_manager.set_base_dir(new_dir)
        self._refresh_env_list()
        # Reload presets tab so custom presets appear immediately
        if hasattr(self, "package_panel"):
            if self.package_panel is not None: self.package_panel.reload_presets_tab()
        self.statusBar().showMessage("Settings saved")

    def _show_about(self):
        import sys as _sys
        from PySide6.QtCore import __version__ as qt_ver
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p><b>Lightweight Python Virtual Environment Manager</b></p>"
            f"<p>Create, manage, and organize your Python virtual environments with ease.</p>"
            f"<hr>"
            f"<p><b>Author:</b> Bayram Kotan</p>"
            f"<p><b>License:</b> LGPL-3.0</p>"
            f"<p><b>Platform:</b> {get_platform().title()}</p>"
            f"<p><b>Python:</b> {_sys.version.split()[0]}</p>"
            f"<p><b>Qt:</b> {qt_ver}</p>"
            f"<hr>"
            f"<p>"
            f"<a href='https://github.com/bayramkotan/VenvStudio'>GitHub</a> &nbsp;|&nbsp; "
            f"<a href='https://pypi.org/project/venvstudio/'>PyPI</a> &nbsp;|&nbsp; "
            f"<a href='https://github.com/bayramkotan'>github.com/bayramkotan</a> &nbsp;|&nbsp; "
            f"<a href='https://www.linkedin.com/in/bayramkotan'>LinkedIn</a>"
            f"</p>"
        )

    def _check_for_updates(self):
        """Manually check for updates from Help menu."""
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        progress = QProgressDialog("Checking for updates...", None, 0, 0, self)
        progress.setWindowTitle("Check for Updates")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumWidth(300)
        progress.show()
        QApplication.processEvents()

        try:
            from src.core.updater import check_for_update
            result = check_for_update()
            progress.close()

            if result.get("update_available"):
                reply = QMessageBox.information(
                    self, "🆕 Update Available",
                    f"<b>VenvStudio v{result['latest_version']}</b> is available!<br>"
                    f"You have <b>v{result['current_version']}</b>.<br><br>"
                    f"Update command:<br>"
                    f"<code>pip install --upgrade venvstudio</code><br><br>"
                    f"Open download page?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open(result.get("release_url", "https://github.com/bayramkotan/VenvStudio/releases"))
            else:
                QMessageBox.information(
                    self, "✅ Up to Date",
                    f"You are running the latest version: <b>v{APP_VERSION}</b>"
                )
        except Exception as e:
            progress.close()
            QMessageBox.warning(
                self, "Update Check Failed",
                f"Could not check for updates.<br><br>"
                f"Check manually: <a href='https://pypi.org/project/venvstudio/'>pypi.org/project/venvstudio</a><br><br>"
                f"Error: {e}"
            )

    def closeEvent(self, event):
        self.config.set("window_width",  self.width())
        self.config.set("window_height", self.height())
        self.config.set("window_x", self.x())
        self.config.set("window_y", self.y())

        # B45 fix: wait for ALL background workers before closing
        workers = []
        for attr in ("_detail_worker", "_ql_worker", "_delete_worker",
                      "_rename_worker", "clone_worker"):
            w = getattr(self, attr, None)
            if w is not None and hasattr(w, "isRunning") and w.isRunning():
                workers.append((attr, w))

        for attr, w in workers:
            try:
                w.quit()
                if not w.wait(3000):
                    w.terminate()
                    w.wait(1000)
            except RuntimeError:
                pass  # already destroyed

        super().closeEvent(event)

    def showEvent(self, event):
        """Re-connect screenChanged after window handle becomes available."""
        super().showEvent(event)
        self._connect_screen_changed()
