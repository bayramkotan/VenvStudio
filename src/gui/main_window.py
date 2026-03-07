"""
VenvStudio - Main Application Window
Modern sidebar-based layout with environment management and package panel
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog,
    QStackedWidget, QInputDialog, QApplication, QProgressDialog,
    QMenu, QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QAction

from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.gui.env_dialog import EnvCreateDialog
from src.gui.package_panel import PackagePanel
from src.gui.settings_page import SettingsPage
from src.gui.styles import get_theme
from src.utils.platform_utils import (
    get_activate_command, open_terminal_at, get_platform,
)
from src.utils.constants import APP_NAME, APP_VERSION
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
    """Background worker to load env details only for envs missing cache."""
    env_detail_ready = Signal(int, str, int, str)  # row, python_ver, pkg_count, size
    all_done = Signal()

    def __init__(self, venv_manager, env_names):
        super().__init__()
        self.venv_manager = venv_manager
        self.env_names = env_names

    def run(self):
        for i, name in enumerate(self.env_names):
            venv_path = self.venv_manager.base_dir / name
            # Skip if cache already exists — list_venvs_fast already loaded it
            cached = self.venv_manager._read_cache(venv_path)
            if cached:
                continue
            # No cache — fetch and write cache
            info = self.venv_manager.get_venv_info(name, use_cache=False)
            if info:
                self.env_detail_ready.emit(
                    i, info.python_version, info.package_count, info.size
                )
        self.all_done.emit()


class DeleteWorker(QThread):
    """Worker thread for deleting environments with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, name):
        super().__init__()
        self.venv_manager = venv_manager
        self.name = name

    def run(self):
        success, msg = self.venv_manager.delete_venv(self.name, callback=self.progress.emit)
        self.finished.emit(success, msg)


class RenameWorker(QThread):
    """Worker thread for renaming environments (clone+delete) with progress."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, old_name, new_name):
        super().__init__()
        self.venv_manager = venv_manager
        self.old_name = old_name
        self.new_name = new_name

    def run(self):
        success, msg = self.venv_manager.rename_venv(
            self.old_name, self.new_name, callback=self.progress.emit
        )
        self.finished.emit(success, msg)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.venv_manager = VenvManager(self.config.get_venv_base_dir())
        self.selected_env = None

        self._setup_window()
        self._setup_menubar()
        self._setup_ui()
        self._apply_theme()
        self._apply_linux_emoji_fix()
        self._check_linux_venv_module()
        self.venv_manager.sync_cache_with_disk()
        self._refresh_env_list()

        # Open default env on startup
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, self._open_default_env)

        # Auto-check for updates on startup (if enabled)
        if self.config.get("check_updates", False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self._auto_check_update)

    def _auto_check_update(self):
        """Silently check for updates on startup."""
        try:
            from src.core.updater import check_for_update
            result = check_for_update()
            if result.get("update_available"):
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
        except Exception:
            pass  # Silent fail on startup

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        width = self.config.get("window_width", 1100)
        height = self.config.get("window_height", 700)

        # Clamp to screen size
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            width = min(width, avail.width() - 80)
            height = min(height, avail.height() - 80)

        self.resize(width, height)
        self.setMinimumSize(900, 600)

        # Center on screen
        if screen:
            avail = screen.availableGeometry()
            x = avail.x() + (avail.width() - width) // 2
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
        version_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        sidebar_layout.addWidget(version_label)
        sidebar_layout.addSpacing(20)

        self.nav_buttons = []

        self.btn_packages = SidebarButton(tr("packages"), "\U0001f4e6")
        self.btn_packages.setChecked(True)
        self.btn_packages.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_packages)
        self.nav_buttons.append(self.btn_packages)

        self.btn_envs = SidebarButton(tr("environments"), "\U0001f4c1")
        self.btn_envs.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_envs)
        self.nav_buttons.append(self.btn_envs)

        self.btn_settings = SidebarButton(tr("settings"), "⚙️")
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))
        sidebar_layout.addWidget(self.btn_settings)
        self.nav_buttons.append(self.btn_settings)

        # ── Quick Launch section (visible only on Packages page) ──
        self.quick_launch_frame = QFrame()
        self.quick_launch_frame.setVisible(True)
        ql_layout = QVBoxLayout(self.quick_launch_frame)
        ql_layout.setContentsMargins(4, 8, 4, 4)
        ql_layout.setSpacing(4)

        ql_sep = QFrame()
        ql_sep.setFrameShape(QFrame.HLine)
        ql_sep.setStyleSheet("background-color: #313244; max-height: 1px;")
        ql_layout.addWidget(ql_sep)

        ql_title = QLabel("  ⚡ Quick Launch")
        ql_title.setStyleSheet("color: #6c7086; font-size: 10px; padding: 2px 0;")
        ql_layout.addWidget(ql_title)

        # Env selector for quick launch
        self.ql_env_selector = QComboBox()
        self.ql_env_selector.setFixedHeight(28)
        self.ql_env_selector.setStyleSheet(
            "QComboBox { font-size: 12px; padding: 2px 8px; "
            "background-color: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 4px; }"
            "QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4; "
            "selection-background-color: #89b4fa; selection-color: #1e1e2e; }"
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
        sidebar_layout.addStretch()

        footer_label = QLabel("  LGPL-3.0 License")
        footer_label.setStyleSheet("color: #585b70; font-size: 10px;")
        sidebar_layout.addWidget(footer_label)
        main_layout.addWidget(sidebar)

        # Content Area
        self.stack = QStackedWidget()
        self.package_panel = PackagePanel()
        self.package_panel.env_refresh_requested.connect(self._refresh_env_list)
        self.package_panel._ql_update_callback = self._update_ql_buttons
        self.package_panel._ql_env_changed_callback = self._sync_ql_selector
        self.stack.addWidget(self.package_panel)             # Page 0
        self.stack.addWidget(self._create_env_page())       # Page 1

        # Settings page
        self.settings_page = SettingsPage(self.config)
        self.settings_page.theme_changed.connect(self._on_theme_changed)
        self.settings_page.font_changed.connect(self._on_font_changed)
        self.settings_page.settings_saved.connect(self._on_settings_saved)
        self.stack.addWidget(self.settings_page)             # Page 2

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
        refresh_btn.clicked.connect(self._refresh_env_list)
        header_layout.addWidget(refresh_btn)

        create_btn = QPushButton(f"  + {tr('new_environment')}  ")
        create_btn.clicked.connect(self._create_env)
        create_btn.setFixedHeight(40)
        header_layout.addWidget(create_btn)
        layout.addLayout(header_layout)

        self.info_label = QLabel()
        self.info_label.setObjectName("subheader")
        self.info_label.setText(f"\U0001f4c2 {self.config.get_venv_base_dir()}")
        layout.addWidget(self.info_label)

        self.env_table = QTableWidget()
        self.env_table.setColumnCount(6)
        self.env_table.setHorizontalHeaderLabels(["Name", "Python", "Packages", "Size", "Created", "Default"])
        self.env_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            self.env_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.env_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.env_table.setColumnWidth(5, 70)
        self.env_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.env_table.setSelectionMode(QTableWidget.SingleSelection)
        self.env_table.setAlternatingRowColors(True)
        self.env_table.verticalHeader().setVisible(False)
        self.env_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.env_table.verticalHeader().setDefaultSectionSize(38)
        self.env_table.setStyleSheet(
            "QTableWidget { font-size: 14px; }"
            "QTableWidget::item { padding: 4px 8px; }"
            "QHeaderView::section { font-size: 13px; font-weight: bold; padding: 6px; }"
        )
        self.env_table.doubleClicked.connect(self._on_env_double_click)
        self.env_table.selectionModel().selectionChanged.connect(self._on_env_selected)
        layout.addWidget(self.env_table)

        # Loading indicator (shown during refresh)
        self.loading_label = QLabel(f"⏳ {tr('loading_environments')}")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(
            "color: #f9e2af; font-size: 13px; padding: 8px; "
            "background-color: rgba(249, 226, 175, 0.1); "
            "border-radius: 6px;"
        )
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        action_layout = QHBoxLayout()

        self.btn_manage_pkgs = QPushButton(f"\U0001f4e6 {tr('manage_packages')}")
        self.btn_manage_pkgs.clicked.connect(self._open_package_manager)
        self.btn_manage_pkgs.setEnabled(False)
        action_layout.addWidget(self.btn_manage_pkgs)

        self.btn_terminal = QPushButton(f"\U0001f5a5\ufe0f {tr('open_terminal')}")
        self.btn_terminal.setObjectName("secondary")
        self.btn_terminal.clicked.connect(self._open_terminal)
        self.btn_terminal.setEnabled(False)
        action_layout.addWidget(self.btn_terminal)

        self.btn_clone = QPushButton(f"\U0001f4cb {tr('clone')}")
        self.btn_clone.setObjectName("secondary")
        self.btn_clone.clicked.connect(self._clone_env)
        self.btn_clone.setEnabled(False)
        action_layout.addWidget(self.btn_clone)

        self.btn_rename = QPushButton(f"✏️ {tr('rename')}")
        self.btn_rename.setObjectName("secondary")
        self.btn_rename.clicked.connect(self._rename_env)
        self.btn_rename.setEnabled(False)
        action_layout.addWidget(self.btn_rename)

        self.btn_export = QPushButton("📤 Export ▾")
        self.btn_export.setObjectName("secondary")
        self.btn_export.setEnabled(False)
        export_menu = QMenu(self.btn_export)
        export_menu.addAction("📄 requirements.txt", self._export_requirements)
        export_menu.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_menu.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_menu.addAction("📦 pyproject.toml", self._export_pyproject)
        export_menu.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_menu.addSeparator()
        export_menu.addAction("📋 Copy to Clipboard", self._export_clipboard)
        self.btn_export.setMenu(export_menu)
        action_layout.addWidget(self.btn_export)

        self.btn_make_default = QPushButton("⭐ Make Default")
        self.btn_make_default.setObjectName("secondary")
        self.btn_make_default.clicked.connect(self._make_default_env)
        self.btn_make_default.setEnabled(False)
        action_layout.addWidget(self.btn_make_default)

        action_layout.addStretch()

        self.btn_delete = QPushButton(f"\U0001f5d1\ufe0f {tr('delete')}")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self._delete_env)
        self.btn_delete.setEnabled(False)
        action_layout.addWidget(self.btn_delete)

        layout.addLayout(action_layout)
        return page

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        # Quick launch always visible (not on Settings page)
        if hasattr(self, "quick_launch_frame"):
            self.quick_launch_frame.setVisible(index != 2)

    def _on_ql_env_changed(self, idx):
        """Sol sidebar QL dropdown değişti — her şeyi sync et."""
        if not hasattr(self, "ql_env_selector"):
            return
        venv_name = self.ql_env_selector.itemData(idx)
        if not venv_name:
            self._rebuild_ql_buttons(set())
            return
        venv_path = self.venv_manager.base_dir / venv_name
        if not venv_path.exists():
            return
        # Env tablosunda ilgili satırı seç
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == venv_name:
                self.env_table.blockSignals(True)
                self.env_table.selectRow(row)
                self.env_table.blockSignals(False)
                break
        # package_panel sync (sayfa değiştirme!)
        self.package_panel.set_venv(venv_path)

    def _ql_load_env_packages(self, venv_name: str):
        """Sadece QL için paket listesi yükle — sağ paneli değiştirme."""
        from pathlib import Path
        from src.core.pip_manager import PipManager
        from src.core.venv_manager import VenvManager
        import json

        venv_path = self.venv_manager.base_dir / venv_name
        if not venv_path.exists():
            return

        class _QLWorker(QThread):
            done = Signal(str, list)
            def __init__(self, venv_path, parent=None):
                super().__init__(parent)
                self._vp = venv_path
            def run(self):
                try:
                    import subprocess, sys
                    python = self._vp / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                    r = subprocess.run(
                        [str(python), "-m", "pip", "list", "--format=json"],
                        capture_output=True, text=True, timeout=30
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
        if hasattr(self, "ql_env_selector") and self.package_panel.pip_manager:
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
        app_defs = getattr(self.package_panel, "app_definitions", [])
        has_any = False
        for app in app_defs:
            if app["package"].lower() not in installed:
                continue
            has_any = True
            btn = QPushButton(f"{app['icon']} {app['name']}")
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                "QPushButton { font-size: 12px; text-align: left; padding: 2px 8px; "
                "background-color: #1e1e2e; color: #cdd6f4; "
                "border: 1px solid #313244; border-radius: 4px; }"
                "QPushButton:hover { background-color: #313244; border-color: #89b4fa; }"
            )
            btn.clicked.connect(lambda checked, a=app: self.package_panel._launch_app(a))
            self.ql_buttons_layout.addWidget(btn)
        if not has_any:
            lbl = QLabel("  No apps installed")
            lbl.setStyleSheet("color: #45475a; font-size: 11px; padding: 4px;")
            self.ql_buttons_layout.addWidget(lbl)

    def _refresh_env_list(self):
        """Phase 1: Load from cache instantly. Phase 2: only fetch missing caches."""
        self.env_table.setRowCount(0)

        # Fast load - reads cache, no subprocess
        envs = self.venv_manager.list_venvs_fast()

        # Only show loading if some envs are missing cache
        has_missing_cache = any(
            e.python_version == "..." for e in envs
        )
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

        for i, env in enumerate(envs):
            name_item = QTableWidgetItem(f"  {env.name}")
            if not env.is_valid:
                name_item.setForeground(Qt.red)
                name_item.setToolTip("Invalid environment (Python not found)")
            name_font = QFont()
            name_font.setBold(True)
            name_item.setFont(name_font)
            self.env_table.setItem(i, 0, name_item)
            self.env_table.setItem(i, 1, QTableWidgetItem(f"  {env.python_version}"))
            pkg = str(env.package_count) if env.package_count else "..."
            self.env_table.setItem(i, 2, QTableWidgetItem(f"  {pkg}"))
            self.env_table.setItem(i, 3, QTableWidgetItem(f"  {env.size}"))

            created_str = ""
            if env.created:
                try:
                    dt = datetime.fromisoformat(env.created)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_str = env.created[:16]
            self.env_table.setItem(i, 4, QTableWidgetItem(f"  {created_str}"))

            # Default column
            default_env = self.config.get("default_env", "")
            default_item = QTableWidgetItem("⭐" if env.name == default_env else "")
            default_item.setTextAlignment(Qt.AlignCenter)
            default_item.setFlags(default_item.flags() & ~Qt.ItemIsEditable)
            self.env_table.setItem(i, 5, default_item)

        self._update_info_label_fast(len(envs))

        # Update package panel env dropdown
        env_list = [(e.name, self.venv_manager.base_dir / e.name) for e in envs]
        self.package_panel.populate_env_list(env_list)
        self.settings_page.populate_vscode_envs(env_list)

        if not envs:
            self.loading_label.setVisible(False)
            self.statusBar().showMessage("No environments found")
            return

        # All data already loaded from cache in list_venvs_fast
        self._on_all_details_done()

    def _on_env_detail_ready(self, row, python_version, package_count, size):
        """Update a single row with detailed info from background thread."""
        if row < self.env_table.rowCount():
            self.env_table.setItem(row, 1, QTableWidgetItem(f"  {python_version}"))
            self.env_table.setItem(row, 2, QTableWidgetItem(f"  {package_count}"))
            self.env_table.setItem(row, 3, QTableWidgetItem(f"  {size}"))

    def _on_all_details_done(self):
        self.loading_label.setVisible(False)
        count = self.env_table.rowCount()
        self.statusBar().showMessage(f"Found {count} environment(s)")

    def _update_info_label_fast(self, count):
        base_dir = self.config.get_venv_base_dir()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _update_info_label(self):
        base_dir = self.config.get_venv_base_dir()
        count = self.env_table.rowCount()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _on_env_selected(self):
        rows = self.env_table.selectionModel().selectedRows()
        has_selection = len(rows) > 0
        self.btn_manage_pkgs.setEnabled(has_selection)
        self.btn_terminal.setEnabled(has_selection)
        self.btn_clone.setEnabled(has_selection)
        self.btn_rename.setEnabled(has_selection)
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
            # Sync package_panel
            venv_path = self.venv_manager.base_dir / name
            if venv_path.exists():
                self.package_panel.set_venv(venv_path)

    def _open_default_env(self):
        """On startup, open default env in Packages if set."""
        default_env = self.config.get("default_env", "")
        if not default_env:
            return
        venv_path = self.venv_manager.base_dir / default_env
        if not venv_path.exists():
            return
        self.package_panel.set_venv(venv_path)
        self._switch_page(0)
        # Sync env table selection
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == default_env:
                self.env_table.selectRow(row)
                break

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

    def _get_selected_env_name(self):
        rows = self.env_table.selectionModel().selectedRows()
        if rows:
            return self.env_table.item(rows[0].row(), 0).text().strip()
        return ""

    def _create_env(self):
        dialog = EnvCreateDialog(self.venv_manager, self.config, self)
        dialog.env_created.connect(lambda name: self._refresh_env_list())
        dialog.exec()

    def _rename_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Environment",
            f"Enter new name for '{name}':\n\n(This will create a new environment with the same packages\nand remove the old one.)",
            text=name,
        )
        if not ok or not new_name.strip() or new_name.strip() == name:
            return

        new_name = new_name.strip()
        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in new_name):
            QMessageBox.warning(self, "Warning", "Name contains invalid characters.")
            return

        self.rename_progress = QProgressDialog(
            f"Renaming '{name}' → '{new_name}'...", "Cancel", 0, 0, self
        )
        self.rename_progress.setWindowTitle("Renaming Environment")
        self.rename_progress.setMinimumWidth(400)
        self.rename_progress.setWindowModality(Qt.WindowModal)
        self.rename_progress.show()

        self._rename_worker = RenameWorker(self.venv_manager, name, new_name)
        self._rename_worker.progress.connect(
            lambda msg: self.rename_progress.setLabelText(f"⏳ {msg}")
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    def _on_rename_finished(self, success, message):
        self.rename_progress.close()
        if success:
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def _delete_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        reply = QMessageBox.warning(
            self, "Delete Environment",
            f"Are you sure you want to delete '{name}'?\n\nThis will permanently remove the environment and all installed packages.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_progress = QProgressDialog(
                f"Deleting '{name}'...", None, 0, 0, self
            )
            self.delete_progress.setWindowTitle("Deleting Environment")
            self.delete_progress.setMinimumWidth(350)
            self.delete_progress.setWindowModality(Qt.WindowModal)
            self.delete_progress.setCancelButton(None)
            self.delete_progress.show()

            self._delete_worker = DeleteWorker(self.venv_manager, name)
            self._delete_worker.progress.connect(
                lambda msg: self.delete_progress.setLabelText(f"⏳ {msg}")
            )
            self._delete_worker.finished.connect(self._on_delete_finished)
            self._delete_worker.start()

    def _on_delete_finished(self, success, message):
        self.delete_progress.close()
        if success:
            # Clear package panel so launcher doesn't show stale installed state
            self.package_panel.installed_package_names.clear()
            self.package_panel._update_launcher_status()
            self._refresh_env_list()
            self.statusBar().showMessage(message)
        else:
            QMessageBox.critical(self, "Error", message)
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
        self.clone_worker.progress.connect(
            lambda msg: self.clone_progress.setLabelText(f"⏳ {msg}")
        )
        self.clone_worker.finished.connect(self._on_clone_finished)
        self.clone_progress.canceled.connect(self._on_clone_cancel)
        self.clone_worker.start()

    def _on_clone_finished(self, success, message):
        self.clone_progress.close()
        if success:
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            QMessageBox.information(self, "Success", message)
        else:
            if "cancelled" not in message.lower():
                QMessageBox.critical(self, "Error", message)
            self.statusBar().showMessage(message)

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

    def _open_package_manager(self):
        name = self._get_selected_env_name()
        if not name:
            return
        venv_path = self.venv_manager.base_dir / name
        self.package_panel.set_venv(venv_path)
        self._switch_page(0)

    def _open_terminal(self):
        name = self._get_selected_env_name()
        if not name:
            return
        venv_path = self.venv_manager.base_dir / name
        terminal_type = self.config.get("default_terminal", "")
        open_terminal_at(venv_path, terminal_type)
        self.statusBar().showMessage(f"Opened terminal for '{name}'")

    def _open_settings(self):
        """Navigate to the settings page."""
        self._switch_page(2)

    def _set_theme(self, theme_name):
        self.config.set("theme", theme_name)
        self._apply_theme()

    def _apply_theme(self):
        theme = self.config.get("theme", "dark")
        self.setStyleSheet(get_theme(theme))
        if hasattr(self, "package_panel"):
            self.package_panel.apply_theme(theme)

    def _on_theme_changed(self, theme_name):
        """Handle theme change from settings page."""
        self._apply_theme()

    def _on_font_changed(self, family, size):
        """Handle font change from settings page."""
        from PySide6.QtWidgets import QApplication
        if not family or size <= 0:
            return
        font = QFont(family, max(8, size))
        QApplication.instance().setFont(font)

    def _check_linux_venv_module(self):
        """On Linux, check if python3-venv is installed. If not, offer to install it."""
        import platform as _platform
        if _platform.system().lower() != "linux":
            return

        import subprocess
        # Check if venv module works
        try:
            result = subprocess.run(
                ["python3", "-m", "venv", "--help"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return  # Already installed
        except Exception:
            pass

        # venv not available — ask user to install
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "python3-venv Missing",
            "The 'python3-venv' package is required to create virtual environments\n"
            "but it is not installed on your system.\n\n"
            "Install it now? (requires admin password)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Try pkexec first, then sudo
        import shutil
        for sudo_cmd in [["pkexec"], ["sudo"]]:
            exe = sudo_cmd[0]
            if not shutil.which(exe):
                continue
            try:
                r = subprocess.run(
                    sudo_cmd + ["apt-get", "install", "-y", "python3-venv"],
                    timeout=120
                )
                if r.returncode == 0:
                    QMessageBox.information(
                        self, "Success",
                        "python3-venv installed successfully!\n"
                        "You can now create virtual environments."
                    )
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        QMessageBox.warning(
            self, "Installation Failed",
            "Could not install python3-venv automatically.\n\n"
            "Please run manually:\n"
            "  sudo apt-get install python3-venv\n\n"
            "Or for other distributions:\n"
            "  sudo dnf install python3-venv   (Fedora)\n"
            "  sudo pacman -S python-virtualenv  (Arch)"
        )

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
            self.package_panel.reload_presets_tab()
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
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())
        # Wait for background worker to finish writing cache
        if hasattr(self, "_detail_worker") and self._detail_worker.isRunning():
            self._detail_worker.wait(5000)
        super().closeEvent(event)
