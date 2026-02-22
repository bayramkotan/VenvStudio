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
    QMenu,
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

        # Linux: use Noto Color Emoji for colored, properly-sized emoji icons
        import platform as _platform
        if _platform.system().lower() == "linux":
            from PySide6.QtGui import QFont as _QFont
            font = self.font()
            font.setFamily("Noto Color Emoji")
            font.setPixelSize(28)  # default; overridden by config in _apply_linux_emoji_fix
            self.setFont(font)


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
    """Background worker to load env details (Python version, package count, size)."""
    env_detail_ready = Signal(int, str, int, str)  # row, python_ver, pkg_count, size
    all_done = Signal()

    def __init__(self, venv_manager, env_names):
        super().__init__()
        self.venv_manager = venv_manager
        self.env_names = env_names

    def run(self):
        for i, name in enumerate(self.env_names):
            info = self.venv_manager.get_venv_info(name)
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
        self._refresh_env_list()

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
        new_env_action = QAction(f"&{tr('new_environment')}", self)
        new_env_action.setShortcut("Ctrl+N")
        new_env_action.triggered.connect(self._create_env)
        file_menu.addAction(new_env_action)
        file_menu.addSeparator()
        quit_action = QAction(tr("quit"), self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu(tr("view"))
        refresh_action = QAction(f"&{tr('refresh')}", self)
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
        about_action = QAction(tr("about"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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

        self.btn_envs = SidebarButton(tr("environments"), "\U0001f4c1")
        self.btn_envs.setChecked(True)
        self.btn_envs.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_envs)
        self.nav_buttons.append(self.btn_envs)

        self.btn_packages = SidebarButton(tr("packages"), "\U0001f4e6")
        self.btn_packages.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_packages)
        self.nav_buttons.append(self.btn_packages)

        self.btn_settings = SidebarButton(tr("settings"), "⚙️")
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))
        sidebar_layout.addWidget(self.btn_settings)
        self.nav_buttons.append(self.btn_settings)

        sidebar_layout.addStretch()

        footer_label = QLabel("  LGPL-3.0 License")
        footer_label.setStyleSheet("color: #585b70; font-size: 10px;")
        sidebar_layout.addWidget(footer_label)
        main_layout.addWidget(sidebar)

        # Content Area
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_env_page())       # Page 0
        self.package_panel = PackagePanel()
        self.package_panel.env_refresh_requested.connect(self._refresh_env_list)
        self.stack.addWidget(self.package_panel)             # Page 1

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
        self.env_table.setColumnCount(5)
        self.env_table.setHorizontalHeaderLabels(["Name", "Python", "Packages", "Size", "Created"])
        self.env_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 5):
            self.env_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
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

    def _refresh_env_list(self):
        """Phase 1: Instantly show env names, then load details in background."""
        self.env_table.setRowCount(0)
        self.statusBar().showMessage("Loading environments...")
        self.loading_label.setVisible(True)

        # Fast load - no subprocess, instant
        envs = self.venv_manager.list_venvs_fast()
        self.env_table.setRowCount(len(envs))

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
            self.env_table.setItem(i, 2, QTableWidgetItem(f"  ..."))
            self.env_table.setItem(i, 3, QTableWidgetItem(f"  ..."))

            created_str = ""
            if env.created:
                try:
                    dt = datetime.fromisoformat(env.created)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_str = env.created[:16]
            self.env_table.setItem(i, 4, QTableWidgetItem(f"  {created_str}"))

        self._update_info_label_fast(len(envs))

        # Update package panel env dropdown
        env_list = [(e.name, self.venv_manager.base_dir / e.name) for e in envs]
        self.package_panel.populate_env_list(env_list)
        self.settings_page.populate_vscode_envs(env_list)

        if not envs:
            self.loading_label.setVisible(False)
            self.statusBar().showMessage("No environments found")
            return

        # Phase 2: Load details in background thread
        self._detail_worker = EnvDetailWorker(self.venv_manager, [e.name for e in envs])
        self._detail_worker.env_detail_ready.connect(self._on_env_detail_ready)
        self._detail_worker.all_done.connect(self._on_all_details_done)
        self._detail_worker.start()

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

        if has_selection:
            row = rows[0].row()
            name = self.env_table.item(row, 0).text().strip()
            self.selected_env = name
            self.statusBar().showMessage(f"Selected: {name}")

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
            self._refresh_env_list()
            self.statusBar().showMessage(message)
        else:
            QMessageBox.critical(self, "Error", message)

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
        self._switch_page(1)

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

    def _apply_linux_emoji_fix(self):
        """On Linux, install Noto Color Emoji as fallback and resize emoji in buttons."""
        import platform as _platform
        if _platform.system().lower() != "linux":
            return

        # Apply saved emoji size to all sidebar buttons
        emoji_size = self.config.get("emoji_icon_size", 28)
        for btn in self.findChildren(QPushButton):
            if btn.parent() and getattr(btn.parent(), "objectName", lambda: "")() == "sidebar":
                font = btn.font()
                font.setFamily("Noto Color Emoji")
                font.setPixelSize(emoji_size)
                btn.setFont(font)


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
        self.statusBar().showMessage("Settings saved")

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>Lightweight Python Virtual Environment Manager</p>"
            f"<p>Create, manage, and organize your Python environments with ease.</p>"
            f"<p><b>License:</b> LGPL-3.0</p>"
            f"<p><b>Platform:</b> {get_platform().title()}</p>"
            f"<p>Built with PySide6 (Qt for Python)</p>"
        )

    def closeEvent(self, event):
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())
        super().closeEvent(event)
