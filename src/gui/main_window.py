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
        self._refresh_env_list()

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        width = self.config.get("window_width", 1100)
        height = self.config.get("window_height", 750)
        self.resize(width, height)
        self.setMinimumSize(900, 600)

    def _setup_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        new_env_action = QAction("&New Environment", self)
        new_env_action.setShortcut("Ctrl+N")
        new_env_action.triggered.connect(self._create_env)
        file_menu.addAction(new_env_action)
        file_menu.addSeparator()
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")
        dark_action = QAction("Dark Theme", self)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(dark_action)
        light_action = QAction("Light Theme", self)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(light_action)
        view_menu.addSeparator()
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_env_list)
        view_menu.addAction(refresh_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
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

        self.btn_envs = SidebarButton("Environments", "\U0001f4c1")
        self.btn_envs.setChecked(True)
        self.btn_envs.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_envs)
        self.nav_buttons.append(self.btn_envs)

        self.btn_packages = SidebarButton("Packages", "\U0001f4e6")
        self.btn_packages.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_packages)
        self.nav_buttons.append(self.btn_packages)

        self.btn_settings = SidebarButton("Settings", "⚙️")
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
        title = QLabel("Virtual Environments")
        title.setObjectName("header")
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("\U0001f504 Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setFixedHeight(40)
        refresh_btn.clicked.connect(self._refresh_env_list)
        header_layout.addWidget(refresh_btn)

        create_btn = QPushButton("  + New Environment  ")
        create_btn.clicked.connect(self._create_env)
        create_btn.setFixedHeight(40)
        header_layout.addWidget(create_btn)
        layout.addLayout(header_layout)

        self.info_label = QLabel()
        self.info_label.setObjectName("subheader")
        self._update_info_label()
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
        self.env_table.doubleClicked.connect(self._on_env_double_click)
        self.env_table.selectionModel().selectionChanged.connect(self._on_env_selected)
        layout.addWidget(self.env_table)

        action_layout = QHBoxLayout()

        self.btn_manage_pkgs = QPushButton("\U0001f4e6 Manage Packages")
        self.btn_manage_pkgs.clicked.connect(self._open_package_manager)
        self.btn_manage_pkgs.setEnabled(False)
        action_layout.addWidget(self.btn_manage_pkgs)

        self.btn_terminal = QPushButton("\U0001f5a5\ufe0f Open Terminal")
        self.btn_terminal.setObjectName("secondary")
        self.btn_terminal.clicked.connect(self._open_terminal)
        self.btn_terminal.setEnabled(False)
        action_layout.addWidget(self.btn_terminal)

        self.btn_clone = QPushButton("\U0001f4cb Clone")
        self.btn_clone.setObjectName("secondary")
        self.btn_clone.clicked.connect(self._clone_env)
        self.btn_clone.setEnabled(False)
        action_layout.addWidget(self.btn_clone)

        self.btn_rename = QPushButton("✏️ Rename")
        self.btn_rename.setObjectName("secondary")
        self.btn_rename.clicked.connect(self._rename_env)
        self.btn_rename.setEnabled(False)
        action_layout.addWidget(self.btn_rename)

        action_layout.addStretch()

        self.btn_delete = QPushButton("\U0001f5d1\ufe0f Delete")
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

        # Phase 2: Load details in background thread
        if envs:
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
            f"Enter new name for '{name}':",
            text=name,
        )
        if not ok or not new_name.strip() or new_name.strip() == name:
            return

        new_name = new_name.strip()
        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in new_name):
            QMessageBox.warning(self, "Warning", "Name contains invalid characters.")
            return

        success, msg = self.venv_manager.rename_venv(name, new_name)
        if success:
            self._refresh_env_list()
            self.statusBar().showMessage(msg)
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)

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
            success, msg = self.venv_manager.delete_venv(name)
            if success:
                self._refresh_env_list()
                self.statusBar().showMessage(msg)
            else:
                QMessageBox.critical(self, "Error", msg)

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
        open_terminal_at(venv_path)
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
        font = QFont(family, size)
        QApplication.instance().setFont(font)

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
