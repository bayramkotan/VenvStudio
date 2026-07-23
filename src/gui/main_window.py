"""
VenvStudio - Main Application Window
Modern sidebar-based layout with environment management and package panel

UI construction, env list/CRUD/export, quick launch, theming, menu bar, and
Linux-specific fixes live in the corresponding mixin files
(env_list.py, env_operations.py, env_export.py, quicklaunch.py,
window_theme.py, window_menu.py, linux_fixes.py); this file holds __init__,
core UI setup, page switching, and top-level window lifecycle.
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
    QMenu, QComboBox, QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QAction, QColor

from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.gui.styles import get_theme
from src.gui.workers import (
    CloneWorker, EnvDetailWorker, DeleteWorker,
    RenameOnlyWorker, RenameFullWorker,
)
# Heavy GUI modules imported lazily in _setup_ui to speed up startup
from src.utils.platform_utils import (
    get_activate_command, open_terminal_at, get_platform,
)
from src.utils.constants import APP_NAME, APP_VERSION, UI_TOOLTIPS
from src.utils.i18n import tr

from .widgets import PathElideMiddleDelegate, SidebarButton
from .env_list import EnvListMixin
from .env_operations import EnvOperationsMixin
from .env_export import EnvExportMixin
from .quicklaunch import QuickLaunchMixin
from .window_theme import WindowThemeMixin
from .window_menu import WindowMenuMixin
from .linux_fixes import LinuxFixesMixin


class MainWindow(EnvListMixin, EnvOperationsMixin, EnvExportMixin, QuickLaunchMixin,
                  WindowThemeMixin, WindowMenuMixin, LinuxFixesMixin, QMainWindow):
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
            # B186 — keep timer as a member so closeEvent can stop() pending
            # fires. Plain QTimer.singleShot() can't be cancelled, and if the
            # user closes the window before the 3s elapse the callback may
            # still fire during teardown and start an orphaned QThread.
            self._check_update_timer = QTimer(self)
            self._check_update_timer.setSingleShot(True)
            self._check_update_timer.timeout.connect(self._auto_check_update)
            self._check_update_timer.start(3000)

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

        # B186 — pass parent=self so the worker becomes a QObject child of
        # MainWindow. Without this, findChildren(QThread) in closeEvent can't
        # see it, and Python interpreter teardown destroys the QThread C++
        # object while the network call is still running ("QThread: Destroyed
        # while thread '' is still running" FATAL).
        self._update_worker = _UpdateWorker(self)
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
            from src.utils.platform_utils import open_url
            open_url(result["release_url"])

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
        # Path column uses middle-elision so long Poetry/pipx paths stay readable:
        # both the drive letter at the start and the env name at the end remain
        # visible (full path is in the cell's tooltip).
        self._path_elide_delegate = PathElideMiddleDelegate(self.env_table)
        self.env_table.setItemDelegateForColumn(2, self._path_elide_delegate)
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
                    from src.utils.platform_utils import open_url
                    open_url(result.get("release_url", "https://github.com/bayramkotan/VenvStudio/releases"))
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

        # B45 / B185 / B186 — clean shutdown of all background workers.
        #
        # Workers run blocking subprocess.run() or os.walk() with no Qt event
        # loop, so quit() is a no-op. requestInterruption() lets cooperative
        # workers (e.g. _EnvSizeWorker checks isInterruptionRequested in its
        # walk loop) bail out early. wait() is the only reliable join.
        #
        # Without this, Python interpreter teardown destroys QThread C++
        # objects while threads are still running ("QThread: Destroyed while
        # thread '' is still running" FATAL).

        # B186 — stop pending update-check timer so it doesn't fire during
        # teardown and spawn an orphaned QThread after closeEvent has run.
        try:
            if hasattr(self, "_check_update_timer") and self._check_update_timer is not None:
                if self._check_update_timer.isActive():
                    self._check_update_timer.stop()
        except RuntimeError:
            pass

        # Step 1 — collect known workers from MainWindow + PackagePanel by name.
        workers = []
        for attr in ("_detail_worker", "_ql_worker", "_delete_worker",
                      "_rename_worker", "clone_worker", "_update_worker"):
            w = getattr(self, attr, None)
            if w is not None and hasattr(w, "isRunning") and w.isRunning():
                workers.append(w)
        if hasattr(self, "package_panel") and self.package_panel is not None:
            for attr in ("_pkg_loader", "_size_worker", "_outdated_worker", "current_worker"):
                w = getattr(self.package_panel, attr, None)
                if w is not None and hasattr(w, "isRunning") and w.isRunning():
                    workers.append(w)

        # Step 2 — sweep the QObject tree for any QThread we don't track by
        # name (anonymous/inline threads, settings-page workers, etc.).
        try:
            from PySide6.QtCore import QThread
            _seen = {id(w) for w in workers}
            for child in self.findChildren(QThread):
                if child is None or id(child) in _seen:
                    continue
                if hasattr(child, "isRunning") and child.isRunning():
                    workers.append(child)
                    _seen.add(id(child))
        except Exception:
            pass

        # Step 3 — interrupt + quit cooperatively.
        #
        # Kill any live micromamba child first: those workers block
        # inside subprocess I/O and ignore requestInterruption(), so
        # without this they survive the wait below and Qt aborts with
        # "QThread: Destroyed while thread is still running" (B186).
        if workers:
            try:
                from src.core.micromamba_installer import (
                    kill_active_micromamba,
                )
                kill_active_micromamba()
            except Exception:
                pass
        for w in workers:
            try:
                w.requestInterruption()
            except Exception:
                pass
            try:
                w.quit()
            except Exception:
                pass

        # Step 4 — wait, then let stragglers go.
        #
        # terminate() used to be the escalation here, but these workers
        # block inside subprocess.communicate() and killing the OS
        # thread at that point corrupts interpreter state -> Windows
        # access violation on shutdown (same crash class as the
        # env_state.py package loader). A worker that has not finished
        # is left alone: the process is exiting anyway, and its child
        # processes were already asked to stop in step 3.
        for w in workers:
            try:
                if w.wait(1500):
                    continue
                try:
                    from src.utils.logger import get_logger
                    get_logger("venvstudio.main_window").debug(
                        f"closeEvent: worker {type(w).__name__} still "
                        f"running, leaving it to exit with the process"
                    )
                except Exception:
                    pass
            except RuntimeError:
                pass  # already destroyed

        super().closeEvent(event)

    def showEvent(self, event):
        """Re-connect screenChanged after window handle becomes available."""
        super().showEvent(event)
        self._connect_screen_changed()
