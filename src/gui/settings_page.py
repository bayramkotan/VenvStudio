"""
VenvStudio - Settings Page
Full settings panel: Language, Theme, Font, Python Management, Paths, General
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QFontComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QDialog, QDialogButtonBox,
    QProgressBar, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor

from src.utils.platform_utils import find_system_pythons, get_platform, subprocess_args
from src.utils.constants import APP_NAME, APP_VERSION
from src.utils.i18n import tr

import os
from pathlib import Path


class NoScrollComboBox(QComboBox):
    """ComboBox that ignores mouse wheel events unless explicitly focused by click."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self._clicked = False

    def mousePressEvent(self, event):
        self._clicked = True
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if self._clicked and self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def focusOutEvent(self, event):
        self._clicked = False
        super().focusOutEvent(event)

# Dil tanımları
LANGUAGES = {
    "en": "English",
    "tr": "Türkçe",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
}


class SettingsPage(QWidget):
    """Full settings page with all configuration options."""

    # Signals
    theme_changed = Signal(str)
    font_changed = Signal(str, int)
    language_changed = Signal(str)
    settings_saved = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        title = QLabel(tr("settings_title"))
        title.setObjectName("header")
        layout.addWidget(title)

        subtitle = QLabel(tr("customize_venvstudio"))
        subtitle.setObjectName("subheader")
        layout.addWidget(subtitle)

        # ── 1. APPEARANCE ──
        appearance_group = QGroupBox(f"🎨 {tr('appearance')}")
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(12)

        # Theme — protected by checkbox
        theme_row = QHBoxLayout()
        self.theme_cb = QCheckBox()
        self.theme_cb.setChecked(False)
        self.theme_cb.toggled.connect(lambda on: self.theme_combo.setEnabled(on))
        theme_row.addWidget(self.theme_cb)
        self.theme_combo = NoScrollComboBox()
        self.theme_combo.addItem("🌙 Dark", "dark")
        self.theme_combo.addItem("☀️ Light", "light")
        self.theme_combo.setEnabled(False)
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addRow(f"{tr('theme')}", theme_row)

        # Font family — protected by checkbox
        font_row = QHBoxLayout()
        self.font_cb = QCheckBox()
        self.font_cb.setChecked(False)
        self.font_cb.toggled.connect(lambda on: self.font_combo.setEnabled(on))
        font_row.addWidget(self.font_cb)
        self.font_combo = QFontComboBox()
        self.font_combo.setEnabled(False)
        self.font_combo.setFocusPolicy(Qt.StrongFocus)
        font_row.addWidget(self.font_combo, 1)
        appearance_layout.addRow(f"{tr('font')}", font_row)

        # Font size — protected by checkbox
        size_row = QHBoxLayout()
        self.font_size_cb = QCheckBox()
        self.font_size_cb.setChecked(False)
        self.font_size_cb.toggled.connect(lambda on: self.font_size_spin.setEnabled(on))
        size_row.addWidget(self.font_size_cb)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(13)
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setEnabled(False)
        size_row.addWidget(self.font_size_spin, 1)
        appearance_layout.addRow(f"{tr('font_size')}", size_row)

        # UI Scale info
        scale_label = QLabel("UI scaling follows your system display settings.")
        scale_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        appearance_layout.addRow("", scale_label)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # ── 2. LANGUAGE ──
        lang_group = QGroupBox(f"🌍 {tr('language')}")
        lang_layout = QFormLayout()
        lang_layout.setSpacing(12)

        lang_row = QHBoxLayout()
        self.lang_enabled_cb = QCheckBox()
        self.lang_enabled_cb.setChecked(False)
        self.lang_enabled_cb.toggled.connect(self._toggle_language)
        lang_row.addWidget(self.lang_enabled_cb)

        self.lang_combo = NoScrollComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(f"{name}", code)
        self.lang_combo.setEnabled(False)
        lang_row.addWidget(self.lang_combo, 1)

        lang_layout.addRow(f"{tr('interface_language')}", lang_row)

        lang_note = QLabel(tr("language_note"))
        lang_note.setStyleSheet("color: #6c7086; font-size: 11px;")
        lang_layout.addRow("", lang_note)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # ── 3. PYTHON VERSIONS ──
        python_group = QGroupBox(f"🐍 {tr('python_versions')}")
        python_layout = QVBoxLayout()
        python_layout.setSpacing(12)

        python_info = QLabel(tr("python_info"))
        python_info.setWordWrap(True)
        python_info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        python_layout.addWidget(python_info)

        # Python versions table
        self.python_table = QTableWidget()
        self.python_table.setColumnCount(3)
        self.python_table.setHorizontalHeaderLabels(["Version", "Path", "Source"])
        self.python_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.python_table.setColumnWidth(0, 100)
        self.python_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.python_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.python_table.setColumnWidth(2, 70)
        self.python_table.setAlternatingRowColors(True)
        self.python_table.verticalHeader().setVisible(False)
        self.python_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.python_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.python_table.setSelectionMode(QTableWidget.SingleSelection)
        self.python_table.setMaximumHeight(180)
        self.python_table.setTextElideMode(Qt.ElideMiddle)
        self.python_table.setWordWrap(False)
        python_layout.addWidget(self.python_table)

        # Python action buttons
        py_btn_layout = QHBoxLayout()

        scan_btn = QPushButton(f"🔍 {tr('scan_system')}")
        scan_btn.setObjectName("secondary")
        scan_btn.clicked.connect(self._scan_pythons)
        py_btn_layout.addWidget(scan_btn)

        add_py_btn = QPushButton(f"+ {tr('add_custom_path')}")
        add_py_btn.setObjectName("secondary")
        add_py_btn.clicked.connect(self._add_custom_python)
        py_btn_layout.addWidget(add_py_btn)

        remove_py_btn = QPushButton(tr("remove_selected"))
        remove_py_btn.setObjectName("danger")
        remove_py_btn.clicked.connect(self._remove_custom_python)
        py_btn_layout.addWidget(remove_py_btn)

        set_user_btn = QPushButton("👤 Set User Default")
        set_user_btn.setObjectName("secondary")
        set_user_btn.setToolTip("Add selected Python to User PATH (no admin required)")
        set_user_btn.clicked.connect(lambda: self._set_python_default("user"))
        py_btn_layout.addWidget(set_user_btn)

        set_system_btn = QPushButton("🖥️ Set System Default")
        set_system_btn.setObjectName("secondary")
        set_system_btn.setToolTip("Add selected Python to System PATH (requires admin)")
        set_system_btn.clicked.connect(lambda: self._set_python_default("system"))
        py_btn_layout.addWidget(set_system_btn)

        download_py_btn = QPushButton("⬇️ Download Python")
        download_py_btn.setObjectName("secondary")
        download_py_btn.setToolTip("Download standalone Python from python-build-standalone")
        download_py_btn.clicked.connect(self._download_python)
        py_btn_layout.addWidget(download_py_btn)

        py_btn_layout.addStretch()
        python_layout.addLayout(py_btn_layout)

        # Default Python
        default_py_layout = QHBoxLayout()
        default_py_label = QLabel(f"{tr('default_python')}")
        default_py_layout.addWidget(default_py_label)

        self.default_py_cb = QCheckBox()
        self.default_py_cb.setChecked(False)
        self.default_py_cb.toggled.connect(lambda on: self.default_python_combo.setEnabled(on))
        default_py_layout.addWidget(self.default_py_cb)

        self.default_python_combo = NoScrollComboBox()
        self.default_python_combo.addItem(tr("system_default"), "")
        self.default_python_combo.setEnabled(False)
        default_py_layout.addWidget(self.default_python_combo, 1)
        default_py_layout.addWidget(self.default_python_combo, 1)
        python_layout.addLayout(default_py_layout)

        python_group.setLayout(python_layout)
        layout.addWidget(python_group)

        # ── 4. PATHS ──
        paths_group = QGroupBox(f"📂 {tr('paths')}")
        paths_layout = QFormLayout()
        paths_layout.setSpacing(12)

        # Venv base dir
        venv_dir_layout = QHBoxLayout()
        self.venv_dir_input = QLineEdit()
        self.venv_dir_input.setReadOnly(True)
        venv_dir_layout.addWidget(self.venv_dir_input, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondary")
        browse_btn.setFixedWidth(100)
        browse_btn.clicked.connect(self._browse_venv_dir)
        venv_dir_layout.addWidget(browse_btn)

        reset_dir_btn = QPushButton("Reset")
        reset_dir_btn.setObjectName("secondary")
        reset_dir_btn.setFixedWidth(70)
        reset_dir_btn.clicked.connect(self._reset_venv_dir)
        venv_dir_layout.addWidget(reset_dir_btn)

        paths_layout.addRow("Environment Directory:", venv_dir_layout)

        path_info = QLabel("All new virtual environments will be created in this directory.")
        path_info.setStyleSheet("color: #6c7086; font-size: 11px;")
        paths_layout.addRow("", path_info)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        # ── 5. PACKAGE MANAGER ──
        pkg_mgr_group = QGroupBox("📦 Package Manager")
        pkg_mgr_layout = QFormLayout()
        pkg_mgr_layout.setSpacing(12)

        pkg_mgr_row = QHBoxLayout()
        self.pkg_mgr_cb = QCheckBox()
        self.pkg_mgr_cb.setChecked(False)
        self.pkg_mgr_cb.toggled.connect(lambda on: self.pkg_manager_combo.setEnabled(on))
        pkg_mgr_row.addWidget(self.pkg_mgr_cb)

        self.pkg_manager_combo = NoScrollComboBox()
        self.pkg_manager_combo.setEnabled(False)
        self.pkg_manager_combo.addItem("pip (default)", "pip")
        self.pkg_manager_combo.addItem("uv (fast, pip-compatible)", "uv")
        pkg_mgr_row.addWidget(self.pkg_manager_combo, 1)
        pkg_mgr_layout.addRow("Backend:", pkg_mgr_row)

        # uv auto-install info
        uv_note = QLabel(
            "uv is 10-100x faster than pip.\n"
            "If uv is not installed, VenvStudio will auto-install it."
        )
        uv_note.setStyleSheet("color: #6c7086; font-size: 11px;")
        uv_note.setWordWrap(True)
        pkg_mgr_layout.addRow("", uv_note)

        pkg_mgr_group.setLayout(pkg_mgr_layout)
        layout.addWidget(pkg_mgr_group)

        # ── 6. GENERAL ──
        general_group = QGroupBox(f"⚙️ {tr('general')}")
        general_layout = QFormLayout()
        general_layout.setSpacing(10)

        self.auto_pip_cb = QCheckBox(tr("auto_upgrade_pip"))
        general_layout.addRow(self.auto_pip_cb)

        self.confirm_delete_cb = QCheckBox(tr("confirm_delete"))
        general_layout.addRow(self.confirm_delete_cb)

        self.show_hidden_cb = QCheckBox(tr("show_hidden_packages"))
        general_layout.addRow(self.show_hidden_cb)

        self.check_updates_cb = QCheckBox(tr("check_updates"))
        general_layout.addRow(self.check_updates_cb)

        self.save_window_cb = QCheckBox(tr("remember_window"))
        general_layout.addRow(self.save_window_cb)

        # Default terminal
        terminal_row = QHBoxLayout()
        self.terminal_cb = QCheckBox()
        self.terminal_cb.setChecked(False)
        self.terminal_cb.toggled.connect(lambda on: self.terminal_combo.setEnabled(on))
        terminal_row.addWidget(self.terminal_cb)

        self.terminal_combo = NoScrollComboBox()
        self.terminal_combo.setEnabled(False)
        platform = get_platform()
        if platform == "windows":
            self.terminal_combo.addItem("PowerShell", "powershell")
            self.terminal_combo.addItem("CMD", "cmd")
            self.terminal_combo.addItem("Windows Terminal", "wt")
            self.terminal_combo.addItem("Git Bash", "git-bash")
        elif platform == "macos":
            self.terminal_combo.addItem("Terminal", "terminal")
            self.terminal_combo.addItem("iTerm2", "iterm2")
        else:
            self.terminal_combo.addItem("System Default", "default")
            self.terminal_combo.addItem("GNOME Terminal", "gnome-terminal")
            self.terminal_combo.addItem("Konsole", "konsole")
            self.terminal_combo.addItem("Xfce4 Terminal", "xfce4-terminal")
            self.terminal_combo.addItem("Tilix", "tilix")
            self.terminal_combo.addItem("Mate Terminal", "mate-terminal")
            self.terminal_combo.addItem("Alacritty", "alacritty")
            self.terminal_combo.addItem("Kitty", "kitty")
            self.terminal_combo.addItem("WezTerm", "wezterm")
            self.terminal_combo.addItem("xterm", "xterm")
        terminal_row.addWidget(self.terminal_combo, 1)

        # Detect button (Linux only)
        if platform == "linux":
            detect_btn = QPushButton("🔍 Detect")
            detect_btn.setObjectName("secondary")
            detect_btn.setFixedWidth(90)
            detect_btn.setToolTip("Scan system for installed terminals and install missing ones")
            detect_btn.clicked.connect(self._detect_terminals)
            terminal_row.addWidget(detect_btn)

        general_layout.addRow(f"{tr('default_terminal')}", terminal_row)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # ── 6. VS CODE INTEGRATION ──
        vscode_group = QGroupBox("💻 VS Code Integration")
        vscode_layout = QVBoxLayout()
        vscode_layout.setSpacing(10)

        vscode_info = QLabel("Set the selected environment's Python as VS Code interpreter.")
        vscode_info.setWordWrap(True)
        vscode_info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        vscode_layout.addWidget(vscode_info)

        vscode_btn_layout = QHBoxLayout()
        self.vscode_cb = QCheckBox()
        self.vscode_cb.setChecked(False)
        self.vscode_cb.toggled.connect(lambda on: self.vscode_env_combo.setEnabled(on))
        vscode_btn_layout.addWidget(self.vscode_cb)

        self.vscode_env_combo = NoScrollComboBox()
        self.vscode_env_combo.addItem("-- Select Environment --", "")
        self.vscode_env_combo.setEnabled(False)
        vscode_btn_layout.addWidget(self.vscode_env_combo, 1)

        vscode_set_btn = QPushButton("🔗 Set as VS Code Interpreter")
        vscode_set_btn.setObjectName("secondary")
        vscode_set_btn.clicked.connect(self._set_vscode_interpreter)
        vscode_btn_layout.addWidget(vscode_set_btn)

        vscode_layout.addLayout(vscode_btn_layout)
        vscode_group.setLayout(vscode_layout)
        layout.addWidget(vscode_group)

        # ── 7. CUSTOM CATEGORIES ──
        cat_mgr_group = QGroupBox("📂 Custom Categories")
        cat_mgr_layout = QVBoxLayout()
        cat_mgr_layout.setSpacing(8)

        # Show built-in categories checkbox
        self.show_builtin_cats_cb = QCheckBox("Show built-in categories (editable — changes saved to config)")
        self.show_builtin_cats_cb.setChecked(False)
        self.show_builtin_cats_cb.toggled.connect(self._toggle_builtin_categories)
        cat_mgr_layout.addWidget(self.show_builtin_cats_cb)

        # Built-in categories (hidden by default, editable)
        self.builtin_cats_table = QTableWidget()
        self.builtin_cats_table.setColumnCount(3)
        self.builtin_cats_table.setHorizontalHeaderLabels(["Icon", "Category Name", "Packages"])
        self.builtin_cats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.builtin_cats_table.setColumnWidth(0, 50)
        self.builtin_cats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.builtin_cats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.builtin_cats_table.setColumnWidth(2, 80)
        self.builtin_cats_table.setMaximumHeight(200)
        self.builtin_cats_table.verticalHeader().setVisible(False)
        self.builtin_cats_table.verticalHeader().setDefaultSectionSize(26)
        self.builtin_cats_table.setVisible(False)
        self.builtin_cats_table.setStyleSheet("""
            QTableWidget { background-color: #1e1e2e; color: #cdd6f4; gridline-color: #313244; font-size: 12px; }
            QTableWidget::item { color: #cdd6f4; }
            QTableWidget QLineEdit { background-color: #313244; color: #f5e0dc; border: 2px solid #89b4fa; padding: 2px; font-size: 12px; }
        """)
        # Populate built-in
        from src.utils.constants import PACKAGE_CATALOG
        self.builtin_cats_table.setRowCount(len(PACKAGE_CATALOG))
        for i, cat_name in enumerate(PACKAGE_CATALOG):
            cat_data = PACKAGE_CATALOG[cat_name]
            icon = cat_data.get("icon", "")
            pkg_count = len(cat_data.get("packages", []))
            self.builtin_cats_table.setItem(i, 0, QTableWidgetItem(icon))
            self.builtin_cats_table.setItem(i, 1, QTableWidgetItem(cat_name))
            count_item = QTableWidgetItem(str(pkg_count))
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)
            self.builtin_cats_table.setItem(i, 2, count_item)
        cat_mgr_layout.addWidget(self.builtin_cats_table)

        cat_mgr_info = QLabel("Add your own categories below. These appear in the Catalog dropdown.")
        cat_mgr_info.setWordWrap(True)
        cat_mgr_info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        cat_mgr_layout.addWidget(cat_mgr_info)

        self.custom_categories_list = QTableWidget()
        self.custom_categories_list.setColumnCount(2)
        self.custom_categories_list.setHorizontalHeaderLabels(["Icon", "Category Name"])
        self.custom_categories_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.custom_categories_list.setColumnWidth(0, 60)
        self.custom_categories_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_categories_list.setMaximumHeight(120)
        self.custom_categories_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_categories_list.setSelectionMode(QTableWidget.SingleSelection)
        self.custom_categories_list.verticalHeader().setVisible(False)
        self.custom_categories_list.verticalHeader().setDefaultSectionSize(28)
        self.custom_categories_list.setStyleSheet("""
            QTableWidget { background-color: #1e1e2e; color: #cdd6f4; gridline-color: #313244; font-size: 13px; }
            QTableWidget::item { color: #cdd6f4; padding: 4px; }
            QTableWidget::item:selected { background-color: #45475a; color: #cdd6f4; }
            QTableWidget QLineEdit { background-color: #313244; color: #f5e0dc; border: 2px solid #89b4fa; padding: 2px 4px; font-size: 13px; }
        """)
        cat_mgr_layout.addWidget(self.custom_categories_list)

        cat_mgr_btns = QHBoxLayout()
        add_category_btn = QPushButton("+ Add Category")
        add_category_btn.setObjectName("secondary")
        add_category_btn.clicked.connect(self._add_custom_category)
        cat_mgr_btns.addWidget(add_category_btn)

        remove_category_btn = QPushButton("Remove Category")
        remove_category_btn.setObjectName("danger")
        remove_category_btn.clicked.connect(self._remove_custom_category)
        cat_mgr_btns.addWidget(remove_category_btn)

        cat_mgr_btns.addStretch()
        cat_mgr_layout.addLayout(cat_mgr_btns)
        cat_mgr_group.setLayout(cat_mgr_layout)
        layout.addWidget(cat_mgr_group)

        # ── 8. CUSTOM CATALOG PACKAGES ──
        catalog_group = QGroupBox("📚 Custom Catalog Packages")
        catalog_layout = QVBoxLayout()
        catalog_layout.setSpacing(10)

        catalog_info = QLabel("Add custom packages. Category column uses a dropdown from built-in + custom categories.")
        catalog_info.setWordWrap(True)
        catalog_info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        catalog_layout.addWidget(catalog_info)

        self.custom_catalog_table = QTableWidget()
        self.custom_catalog_table.setColumnCount(3)
        self.custom_catalog_table.setHorizontalHeaderLabels(["Package Name", "Description", "Category"])
        self.custom_catalog_table.setStyleSheet("""
            QTableWidget { background-color: #1e1e2e; color: #cdd6f4; gridline-color: #313244; font-size: 13px; }
            QTableWidget::item { color: #cdd6f4; padding: 4px; font-size: 13px; }
            QTableWidget::item:selected { background-color: #45475a; color: #cdd6f4; }
            QTableWidget QLineEdit { background-color: #313244; color: #f5e0dc; border: 2px solid #89b4fa; padding: 4px 6px; font-size: 13px; min-height: 24px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #585b70; padding: 3px; font-size: 12px; }
        """)
        self.custom_catalog_table.verticalHeader().setDefaultSectionSize(34)
        self.custom_catalog_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_catalog_table.setSelectionMode(QTableWidget.SingleSelection)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.custom_catalog_table.setColumnWidth(0, 160)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.custom_catalog_table.setColumnWidth(2, 200)
        self.custom_catalog_table.setAlternatingRowColors(True)
        self.custom_catalog_table.verticalHeader().setVisible(False)
        self.custom_catalog_table.setMaximumHeight(200)
        catalog_layout.addWidget(self.custom_catalog_table)

        cat_btn_layout = QHBoxLayout()
        add_cat_btn = QPushButton("+ Add Package")
        add_cat_btn.setObjectName("secondary")
        add_cat_btn.clicked.connect(self._add_custom_catalog_pkg)
        cat_btn_layout.addWidget(add_cat_btn)

        remove_cat_btn = QPushButton("Remove Selected")
        remove_cat_btn.setObjectName("danger")
        remove_cat_btn.clicked.connect(self._remove_custom_catalog_pkg)
        cat_btn_layout.addWidget(remove_cat_btn)

        cat_btn_layout.addStretch()
        catalog_layout.addLayout(cat_btn_layout)
        catalog_group.setLayout(catalog_layout)
        layout.addWidget(catalog_group)

        # ── 8. DIAGNOSTICS & LOGGING ──
        diag_group = QGroupBox("🔧 Diagnostics")
        diag_layout = QVBoxLayout()

        diag_btn_layout = QHBoxLayout()
        open_log_btn = QPushButton("📄 Open Log Folder")
        open_log_btn.setObjectName("secondary")
        open_log_btn.clicked.connect(self._open_log_folder)
        diag_btn_layout.addWidget(open_log_btn)

        open_config_btn = QPushButton("📁 Open Config Folder")
        open_config_btn.setObjectName("secondary")
        open_config_btn.clicked.connect(self._open_config_folder)
        diag_btn_layout.addWidget(open_config_btn)

        add_path_btn = QPushButton("🔗 Add Python to System PATH")
        add_path_btn.setObjectName("secondary")
        add_path_btn.clicked.connect(self._add_python_to_path)
        diag_btn_layout.addWidget(add_path_btn)

        add_vs_path_btn = QPushButton("🖥️ Enable 'vs' CLI Commands")
        add_vs_path_btn.setObjectName("secondary")
        add_vs_path_btn.clicked.connect(self._toggle_vs_cli)
        diag_btn_layout.addWidget(add_vs_path_btn)

        diag_btn_layout.addStretch()
        diag_layout.addLayout(diag_btn_layout)

        # Second row — destructive actions
        diag_btn_layout2 = QHBoxLayout()
        clear_all_btn = QPushButton("🗑️ Remove All Settings & Cache")
        clear_all_btn.setObjectName("danger")
        clear_all_btn.clicked.connect(self._clear_all_data)
        diag_btn_layout2.addWidget(clear_all_btn)

        export_settings_btn = QPushButton("📤 Export Settings")
        export_settings_btn.setObjectName("secondary")
        export_settings_btn.clicked.connect(self._export_settings)
        diag_btn_layout2.addWidget(export_settings_btn)

        # Environment Export button (also in Settings for discoverability)
        from PySide6.QtWidgets import QMenu as _QMenu
        env_export_btn = QPushButton("📤 Export Environment ▾")
        env_export_btn.setObjectName("secondary")
        env_export_btn.setToolTip("Export selected environment's packages in various formats")
        env_export_menu = _QMenu(env_export_btn)
        env_export_menu.addAction("📄 requirements.txt", self._export_env_requirements)
        env_export_menu.addAction("🐳 Dockerfile", self._export_env_dockerfile)
        env_export_menu.addAction("🐳 docker-compose.yml", self._export_env_docker_compose)
        env_export_menu.addAction("📦 pyproject.toml", self._export_env_pyproject)
        env_export_menu.addAction("🐍 environment.yml (Conda)", self._export_env_conda_yml)
        env_export_menu.addSeparator()
        env_export_menu.addAction("📋 Copy to Clipboard", self._export_env_clipboard)
        env_export_btn.setMenu(env_export_menu)
        diag_btn_layout2.addWidget(env_export_btn)

        import_settings_btn = QPushButton("📥 Import Settings")
        import_settings_btn.setObjectName("secondary")
        import_settings_btn.clicked.connect(self._import_settings)
        diag_btn_layout2.addWidget(import_settings_btn)

        diag_btn_layout2.addStretch()
        diag_layout.addLayout(diag_btn_layout2)
        diag_group.setLayout(diag_layout)
        layout.addWidget(diag_group)

        # ── 9. ABOUT ──
        about_group = QGroupBox(f"ℹ️ About {APP_NAME}")
        about_layout = QVBoxLayout()
        about_layout.setSpacing(8)

        about_text = QLabel(
            f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            f"<p>Lightweight Python Virtual Environment Manager</p>"
            f"<p>Create, manage, and organize your Python environments with ease.</p>"
            f"<p><b>License:</b> LGPL-3.0</p>"
            f"<p><b>Platform:</b> {get_platform().title()}</p>"
            f"<p><b>Built with:</b> PySide6 (Qt for Python)</p>"
        )
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.RichText)
        about_layout.addWidget(about_text)

        # Update check section
        update_row = QHBoxLayout()
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("font-size: 12px;")
        update_row.addWidget(self.update_status_label, 1)

        check_update_btn = QPushButton("🔄 Check for Updates")
        check_update_btn.setObjectName("secondary")
        check_update_btn.clicked.connect(self._check_for_updates)
        update_row.addWidget(check_update_btn)

        about_layout.addLayout(update_row)

        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()

        # ── SAVE / RESET BUTTONS ──
        btn_layout = QHBoxLayout()

        reset_all_btn = QPushButton(tr("reset_defaults"))
        reset_all_btn.setObjectName("danger")
        reset_all_btn.clicked.connect(self._reset_all)
        btn_layout.addWidget(reset_all_btn)

        btn_layout.addStretch()

        save_btn = QPushButton(f"  💾 {tr('save_settings')}  ")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _detect_terminals(self):
        """Scan for installed terminals on Linux, offer to install missing ones via pkexec."""
        import shutil

        ALL_TERMINALS = [
            ("GNOME Terminal", "gnome-terminal", "gnome-terminal"),
            ("Konsole", "konsole", "konsole"),
            ("Xfce4 Terminal", "xfce4-terminal", "xfce4-terminal"),
            ("Tilix", "tilix", "tilix"),
            ("Mate Terminal", "mate-terminal", "mate-terminal"),
            ("Alacritty", "alacritty", "alacritty"),
            ("Kitty", "kitty", "kitty"),
            ("xterm", "xterm", "xterm"),
        ]

        installed = [(label, data) for label, data, cmd in ALL_TERMINALS if shutil.which(cmd)]
        not_installed = [(label, data, cmd) for label, data, cmd in ALL_TERMINALS if not shutil.which(cmd)]

        # Update dropdown — show only installed + System Default
        current_data = self.terminal_combo.currentData()
        self.terminal_combo.blockSignals(True)
        self.terminal_combo.clear()
        self.terminal_combo.addItem("System Default", "default")
        for label, data in installed:
            self.terminal_combo.addItem(f"✅ {label}", data)
        for label, data, _ in not_installed:
            self.terminal_combo.addItem(f"❌ {label} (not installed)", data)
        # Restore selection
        idx = self.terminal_combo.findData(current_data)
        self.terminal_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.terminal_combo.blockSignals(False)

        if not installed:
            msg = "No supported terminals found on your system.\n\n"
        else:
            names = ", ".join(l for l, _ in installed)
            msg = f"Found: {names}\n\n"

        if not not_installed:
            QMessageBox.information(self, "Terminal Detection", msg + "All supported terminals are installed.")
            return

        missing_names = "\n".join(f"  • {l}" for l, _, _ in not_installed)
        reply = QMessageBox.question(
            self, "Terminal Detection",
            msg + f"Not installed:\n{missing_names}\n\n"
            f"Install a terminal? (requires admin password)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Let user pick which one to install
        items = [l for l, _, _ in not_installed]
        from PySide6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self, "Install Terminal",
            "Select a terminal to install:",
            items, 0, False,
        )
        if not ok or not choice:
            return

        pkg = next((cmd for l, _, cmd in not_installed if l == choice), None)
        if not pkg:
            return

        # Try pkexec first, fallback to sudo
        import subprocess
        success = False
        for sudo_cmd in [["pkexec"], ["sudo"]]:
            try:
                result = subprocess.run(
                    sudo_cmd + ["apt-get", "install", "-y", pkg],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    success = True
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        if success:
            QMessageBox.information(
                self, "✅ Installed",
                f"{choice} installed successfully!\n\nIt has been added to the terminal list.",
            )
            self._detect_terminals()  # Refresh dropdown
        else:
            QMessageBox.critical(
                self, "❌ Failed",
                f"Could not install {choice}.\n\n"
                f"Try manually:\n  sudo apt-get install {pkg}",
            )

    def _toggle_language(self, enabled):
        """Enable/disable language combo based on checkbox."""
        self.lang_combo.setEnabled(enabled)

    def _load_current_settings(self):
        """Load current settings into UI widgets."""
        # Theme
        theme = self.config.get("theme", "dark")
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        if theme != "dark":
            self.theme_cb.setChecked(True)
            self.theme_combo.setEnabled(True)
        else:
            self.theme_cb.setChecked(False)
            self.theme_combo.setEnabled(False)

        # Font — ALWAYS start unticked, only tick if config has explicit non-default
        font_family = self.config.get("font_family", "")
        # Clear old default values from config
        default_fonts = ("", "Segoe UI", "Yu Gothic UI", "MS Shell Dlg 2", "Arial", "Tahoma")
        if not font_family or font_family in default_fonts:
            self.font_cb.setChecked(False)
            self.font_combo.setEnabled(False)
            self.config.set("font_family", "")
        else:
            self.font_cb.setChecked(True)
            self.font_combo.setEnabled(True)
            self.font_combo.setCurrentFont(QFont(font_family))

        font_size = self.config.get("font_size", 13)
        default_sizes = (0, 12, 13, 14)
        if not font_size or font_size in default_sizes:
            self.font_size_cb.setChecked(False)
            self.font_size_spin.setEnabled(False)
            self.font_size_spin.setValue(13)
            self.config.set("font_size", 13)
        else:
            self.font_size_cb.setChecked(True)
            self.font_size_spin.setEnabled(True)
            self.font_size_spin.setValue(font_size)

        # Language
        lang = self.config.get("language", "en")
        idx = self.lang_combo.findData(lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        # Always start unticked — user must tick to change language
        self.lang_enabled_cb.setChecked(False)
        self.lang_combo.setEnabled(False)

        # Venv dir
        self.venv_dir_input.setText(str(self.config.get_venv_base_dir()))

        # General options
        self.auto_pip_cb.setChecked(self.config.get("auto_upgrade_pip", True))
        self.confirm_delete_cb.setChecked(self.config.get("confirm_delete", True))
        self.show_hidden_cb.setChecked(self.config.get("show_hidden_packages", False))
        self.check_updates_cb.setChecked(self.config.get("check_updates", False))
        self.save_window_cb.setChecked(self.config.get("save_window_geometry", True))

        # Package manager
        pkg_mgr = self.config.get("package_manager", "pip")
        idx = self.pkg_manager_combo.findData(pkg_mgr)
        if idx >= 0:
            self.pkg_manager_combo.setCurrentIndex(idx)
        if pkg_mgr != "pip":
            self.pkg_mgr_cb.setChecked(True)
            self.pkg_manager_combo.setEnabled(True)
        else:
            self.pkg_mgr_cb.setChecked(False)
            self.pkg_manager_combo.setEnabled(False)

        # Terminal — only enable if explicitly set to non-default
        terminal = self.config.get("default_terminal", "")
        if terminal and terminal.strip():
            idx = self.terminal_combo.findData(terminal)
            if idx > 0:
                self.terminal_cb.setChecked(True)
                self.terminal_combo.setEnabled(True)
                self.terminal_combo.setCurrentIndex(idx)
            else:
                self.terminal_cb.setChecked(False)
                self.terminal_combo.setEnabled(False)
                self.terminal_combo.setCurrentIndex(0)
        else:
            self.terminal_cb.setChecked(False)
            self.terminal_combo.setEnabled(False)
            self.terminal_combo.setCurrentIndex(0)

        # Scan pythons
        self._scan_pythons()

        # Load custom categories
        self._load_custom_categories()

        # Load custom catalog
        self._load_custom_catalog()

    def _scan_pythons(self):
        """Scan system for Python installations."""
        import os
        self.python_table.setRowCount(0)
        self.default_python_combo.clear()
        self.default_python_combo.addItem("System Default", "")

        # System pythons
        system_pythons = find_system_pythons()
        system_paths = set()
        for version, path in system_pythons:
            norm_path = os.path.normpath(path)
            system_paths.add(os.path.normcase(norm_path))
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(version))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))
            self.python_table.setItem(row, 2, QTableWidgetItem("System"))
            self.default_python_combo.addItem(f"Python {version}", norm_path)

        # Custom pythons from config (skip duplicates of system pythons)
        custom_pythons = self.config.get("custom_pythons", [])
        cleaned_custom = []
        for entry in custom_pythons:
            norm_path = os.path.normpath(entry.get("path", ""))
            if os.path.normcase(norm_path) in system_paths:
                continue  # already listed as System — skip duplicate
            cleaned_custom.append(entry)
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(entry.get("version", "?")))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))

            source_item = QTableWidgetItem("Custom")
            source_item.setForeground(Qt.cyan)
            self.python_table.setItem(row, 2, source_item)

            self.default_python_combo.addItem(
                f"Python {entry.get('version', '?')} (Custom)", norm_path
            )

        # Auto-clean config if duplicates were removed
        if len(cleaned_custom) != len(custom_pythons):
            self.config.set("custom_pythons", cleaned_custom)

        # Standalone (downloaded) Pythons
        try:
            from src.core.python_downloader import get_installed_pythons
            all_listed_paths = system_paths.copy()
            for entry in cleaned_custom:
                all_listed_paths.add(os.path.normcase(os.path.normpath(entry.get("path", ""))))

            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                if os.path.normcase(exe_path) in all_listed_paths:
                    continue
                row = self.python_table.rowCount()
                self.python_table.insertRow(row)
                self.python_table.setItem(row, 0, QTableWidgetItem(py["version"]))
                self.python_table.setItem(row, 1, QTableWidgetItem(exe_path))

                source_item = QTableWidgetItem("Downloaded")
                source_item.setForeground(QColor("#a6e3a1"))
                self.python_table.setItem(row, 2, source_item)

                self.default_python_combo.addItem(
                    f"Python {py['version']} (Downloaded)", exe_path
                )
        except Exception:
            pass  # downloader module may not be available

        # Set default python selection — only enable checkbox if user explicitly changed it
        default_py = self.config.get("default_python", "")
        if default_py and default_py.strip():
            default_py_norm = os.path.normpath(default_py)
            # Find matching index (case-insensitive on Windows)
            found_idx = -1
            for i in range(self.default_python_combo.count()):
                item_data = self.default_python_combo.itemData(i) or ""
                if item_data and os.path.normpath(item_data).lower() == default_py_norm.lower():
                    found_idx = i
                    break
            if found_idx > 0:  # index 0 is "System Default" — don't enable for that
                self.default_py_cb.setChecked(True)
                self.default_python_combo.setEnabled(True)
                self.default_python_combo.setCurrentIndex(found_idx)
            else:
                self.default_py_cb.setChecked(False)
                self.default_python_combo.setEnabled(False)
                self.default_python_combo.setCurrentIndex(0)
                # Clear invalid config value
                self.config.set("default_python", "")
        else:
            self.default_py_cb.setChecked(False)
            self.default_python_combo.setEnabled(False)
            self.default_python_combo.setCurrentIndex(0)

    def _add_custom_python(self):
        """Add a custom Python executable path."""
        import os
        import subprocess
        from src.utils.platform_utils import subprocess_args as sp_args

        if get_platform() == "windows":
            filter_str = "Python Executable (python.exe);;All Files (*)"
        else:
            filter_str = "All Files (*)"

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Python Executable", "", filter_str
        )
        if not filepath:
            return

        filepath = os.path.normpath(filepath)

        # If user selected a directory or a non-exe file, try to find python inside
        if os.path.isdir(filepath):
            candidates = []
            if get_platform() == "windows":
                candidates = [
                    os.path.join(filepath, "python.exe"),
                    os.path.join(filepath, "Scripts", "python.exe"),
                ]
            else:
                candidates = [
                    os.path.join(filepath, "bin", "python3"),
                    os.path.join(filepath, "bin", "python"),
                    os.path.join(filepath, "python3"),
                    os.path.join(filepath, "python"),
                ]
            found = None
            for c in candidates:
                if os.path.isfile(c):
                    found = c
                    break
            if not found:
                QMessageBox.warning(self, "Error", f"Could not find python executable in:\n{filepath}")
                return
            filepath = os.path.normpath(found)

        # If selected file is not named python*, try to find it in parent dir
        basename = os.path.basename(filepath).lower()
        if not basename.startswith("python") and os.path.isfile(filepath):
            parent = os.path.dirname(filepath)
            if get_platform() == "windows":
                alt = os.path.join(parent, "python.exe")
            else:
                alt = os.path.join(parent, "python3")
                if not os.path.isfile(alt):
                    alt = os.path.join(parent, "python")
            if os.path.isfile(alt):
                filepath = os.path.normpath(alt)

        # Verify it's a valid Python
        try:
            result = subprocess.run(
                [filepath, "--version"],
                **sp_args(capture_output=True, text=True, timeout=5)
            )
            if result.returncode != 0:
                QMessageBox.critical(self, "Error", f"Not a valid Python executable:\n{filepath}")
                return
            version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Not a valid Python executable:\n{e}")
            return

        # Save to config
        custom_pythons = self.config.get("custom_pythons", [])
        for entry in custom_pythons:
            if os.path.normpath(entry.get("path", "")) == filepath:
                QMessageBox.information(self, "Info", "This Python path is already added.")
                return

        custom_pythons.append({"version": version, "path": filepath})
        self.config.set("custom_pythons", custom_pythons)
        self._scan_pythons()

        QMessageBox.information(self, "Success", f"Added Python {version}\n{filepath}")

    def _remove_custom_python(self):
        """Remove a custom Python path."""
        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version to remove.")
            return

        row = rows[0].row()
        source = self.python_table.item(row, 2).text()
        if source != "Custom":
            QMessageBox.information(self, "Info", "Only custom Python paths can be removed.\nSystem-detected paths are managed automatically.")
            return

        path = self.python_table.item(row, 1).text()
        custom_pythons = self.config.get("custom_pythons", [])
        custom_pythons = [e for e in custom_pythons if e.get("path") != path]
        self.config.set("custom_pythons", custom_pythons)
        self._scan_pythons()


    def _set_python_default(self, scope="user"):
        """
        Set selected Python as default.
        scope='user'   → Update User PATH (no admin needed if System PATH is clean)
        scope='system' → Update System PATH (admin required)
        Both modes remove OTHER Python entries from BOTH scopes.
        """
        import os, subprocess, tempfile
        from src.utils.platform_utils import get_platform, subprocess_args

        if get_platform() != "windows":
            QMessageBox.information(
                self, "Info",
                "This feature is currently available on Windows only.\n"
                "On Linux/macOS, use your shell config or update-alternatives."
            )
            return

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()
        python_dir = os.path.normpath(os.path.dirname(python_path))
        scripts_dir = os.path.join(python_dir, "Scripts")

        scope_label = "User" if scope == "user" else "System"

        # Read both PATHs
        try:
            user_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            ).stdout.strip() or ""

            system_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('Path', 'Machine')"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            ).stdout.strip() or ""
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read PATH:\n{e}")
            return

        # Find ALL Python dirs in a PATH string (excluding our target)
        def find_python_dirs(path_str, exclude_dirs):
            exclude_set = {os.path.normcase(d.rstrip("\\")) for d in exclude_dirs}
            found = []
            for p in path_str.split(";"):
                p = p.strip()
                if not p:
                    continue
                p_norm = os.path.normcase(p.rstrip("\\"))
                if p_norm in exclude_set:
                    continue
                # Direct python.exe check
                if os.path.exists(os.path.join(p, "python.exe")):
                    found.append(p)
                    continue
                # Scripts dir of a Python installation
                if os.path.basename(p).lower() == "scripts":
                    parent = os.path.dirname(p)
                    if os.path.exists(os.path.join(parent, "python.exe")):
                        found.append(p)
            return found

        target_dirs = [python_dir, scripts_dir]
        other_in_user = find_python_dirs(user_path, target_dirs)
        other_in_system = find_python_dirs(system_path, target_dirs)

        # Build confirmation message
        changes = [f"✅ Add to {scope_label} PATH:\n   📂 {python_dir}\n   📂 {scripts_dir}"]

        if other_in_user:
            changes.append("🗑️ Remove from User PATH:\n" +
                          "\n".join(f"   ❌ {p}" for p in other_in_user))
        if other_in_system:
            changes.append("🗑️ Remove from System PATH:\n" +
                          "\n".join(f"   ❌ {p}" for p in other_in_system))

        needs_admin = scope == "system" or bool(other_in_system)
        admin_note = "\n\n🔒 Admin permission required." if needs_admin else ""

        confirm = QMessageBox.question(
            self, f"Set {scope_label} Default",
            f"Set Python {version} as {scope_label} default?\n\n" +
            "\n\n".join(changes) + admin_note,
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # Build set of ALL dirs to remove (+ their Scripts counterparts)
        all_remove = set()
        for p in other_in_user + other_in_system:
            norm = os.path.normcase(p.rstrip("\\"))
            all_remove.add(norm)
            all_remove.add(os.path.normcase(os.path.join(p, "Scripts").rstrip("\\")))
            if os.path.basename(p).lower() == "scripts":
                all_remove.add(os.path.normcase(os.path.dirname(p).rstrip("\\")))

        # Also include target dirs in removal filter (we re-add them at top)
        all_remove.add(os.path.normcase(python_dir.rstrip("\\")))
        all_remove.add(os.path.normcase(scripts_dir.rstrip("\\")))

        def build_ps_filter(dirs):
            conds = []
            for d in sorted(dirs):
                escaped = d.replace("'", "''")
                conds.append(f"($lower -ne '{escaped}')")
            return " -and ".join(conds) if conds else "$true"

        ps_filter = build_ps_filter(all_remove)
        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_path_result.txt")

        # Target scope gets Python added at top; other scope just gets cleaned
        if scope == "user":
            ps_script = f'''
try {{
    $f = '{ps_filter}'
    # Clean + prepend User PATH
    $uPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $uParts = ($uPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        {ps_filter}
    }}
    $newUser = ('{python_dir};{scripts_dir};' + ($uParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newUser, 'User')

    # Clean System PATH
    $sPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $sParts = ($sPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        {ps_filter}
    }}
    [Environment]::SetEnvironmentVariable('Path', ($sParts -join ';'), 'Machine')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        else:  # system
            ps_script = f'''
try {{
    # Clean + prepend System PATH
    $sPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $sParts = ($sPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        {ps_filter}
    }}
    $newSys = ('{python_dir};{scripts_dir};' + ($sParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newSys, 'Machine')

    # Clean User PATH
    $uPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $uParts = ($uPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        {ps_filter}
    }}
    [Environment]::SetEnvironmentVariable('Path', ($uParts -join ';'), 'User')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''

        # Write and execute
        ps_file = os.path.join(tempfile.gettempdir(), "_venvstudio_set_path.ps1")
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_script)

        if os.path.exists(result_file):
            os.unlink(result_file)

        try:
            if needs_admin:
                subprocess.run(
                    [
                        "powershell", "-NoProfile", "-Command",
                        f"Start-Process -FilePath 'powershell.exe' "
                        f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"{ps_file}\"' "
                        f"-Verb RunAs -Wait"
                    ],
                    capture_output=True, text=True, timeout=120,
                    **subprocess_args()
                )
            else:
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", ps_file],
                    capture_output=True, text=True, timeout=30,
                    **subprocess_args()
                )

            import time
            time.sleep(1)

            success = False
            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_text = f.read().strip()
                if result_text.startswith("OK"):
                    success = True
                else:
                    raise RuntimeError(result_text)

            if not success:
                target_scope_name = 'Machine' if scope == 'system' else 'User'
                verify = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[Environment]::GetEnvironmentVariable('Path', '{target_scope_name}')"],
                    capture_output=True, text=True, timeout=10,
                    **subprocess_args()
                )
                if python_dir.lower() in verify.stdout.strip().lower():
                    success = True

            if success:
                QMessageBox.information(
                    self, "✅ Success",
                    f"Python {version} is now the {scope_label} default!\n\n"
                    f"Other Python entries cleaned from both User and System PATH.\n\n"
                    f"Open a new terminal and type:\n"
                    f"  python --version\n\n"
                    f"It should show: Python {version}"
                )
            else:
                QMessageBox.warning(
                    self, "⚠️ Partial",
                    f"Could not verify the change.\n"
                    f"Admin permission may have been denied.\n\n"
                    f"Check Environment Variables manually."
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update PATH:\n{e}")
        finally:
            for fp in [ps_file, result_file]:
                try:
                    os.unlink(fp)
                except Exception:
                    pass

    def _download_python(self):
        """Open dialog to download a standalone Python version."""
        dlg = PythonDownloadDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._scan_pythons()

    def _browse_venv_dir(self):
        """Browse for environment base directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Base Directory for Environments",
            self.venv_dir_input.text(),
        )
        if directory:
            self.venv_dir_input.setText(directory)

    def _reset_venv_dir(self):
        """Reset venv directory to default."""
        from src.utils.platform_utils import get_default_venv_base_dir
        self.venv_dir_input.setText(str(get_default_venv_base_dir()))

    def _set_vscode_interpreter(self):
        """Set VS Code python interpreter path for the selected env."""
        env_path = self.vscode_env_combo.currentData()
        if not env_path:
            QMessageBox.warning(self, tr("warning"), "Please select an environment first.")
            return

        from src.utils.platform_utils import get_python_executable
        python_exe = get_python_executable(Path(env_path))

        import os
        norm_path = os.path.normpath(str(python_exe))

        # Try to write .vscode/settings.json in current working directory
        vscode_dir = Path.cwd() / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        settings_file = vscode_dir / "settings.json"

        import json
        settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}

        settings["python.defaultInterpreterPath"] = norm_path

        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)

            QMessageBox.information(
                self, tr("success"),
                f"VS Code interpreter set to:\n{norm_path}\n\n"
                f"Settings written to:\n{settings_file}\n\n"
                f"Tip: Install the 'Python' extension in VS Code if not already installed."
            )
        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"Failed to write VS Code settings:\n{e}")

    def _get_all_categories(self):
        """Get built-in + custom category names."""
        from src.utils.constants import PACKAGE_CATALOG
        cats = list(PACKAGE_CATALOG.keys())
        custom_cats = self.config.get("custom_categories", [])
        for c in custom_cats:
            name = c.get("name", "")
            if name:
                icon = c.get("icon", "⭐")
                full = f"{icon} {name}"
                if full not in cats:
                    cats.append(full)
        # Always include ⭐ Custom as fallback
        if "⭐ Custom" not in cats:
            cats.append("⭐ Custom")
        return cats

    def _load_custom_categories(self):
        """Load custom categories from config."""
        custom_cats = self.config.get("custom_categories", [])
        self.custom_categories_list.setRowCount(len(custom_cats))
        for i, c in enumerate(custom_cats):
            self.custom_categories_list.setItem(i, 0, QTableWidgetItem(c.get("icon", "⭐")))
            self.custom_categories_list.setItem(i, 1, QTableWidgetItem(c.get("name", "")))

    def _save_custom_categories(self):
        """Save custom categories to config."""
        self.custom_categories_list.setCurrentItem(None)
        cats = []
        for row in range(self.custom_categories_list.rowCount()):
            icon_item = self.custom_categories_list.item(row, 0)
            name_item = self.custom_categories_list.item(row, 1)
            icon = icon_item.text().strip() if icon_item else "⭐"
            name = name_item.text().strip() if name_item else ""
            if name:
                cats.append({"icon": icon or "⭐", "name": name})
        self.config.set("custom_categories", cats)

    def _add_custom_category(self):
        """Add a new custom category."""
        row = self.custom_categories_list.rowCount()
        self.custom_categories_list.insertRow(row)
        self.custom_categories_list.setItem(row, 0, QTableWidgetItem("⭐"))
        self.custom_categories_list.setItem(row, 1, QTableWidgetItem(""))
        self.custom_categories_list.editItem(self.custom_categories_list.item(row, 1))

    def _remove_custom_category(self):
        """Remove selected custom category."""
        row = self.custom_categories_list.currentRow()
        if row >= 0:
            self.custom_categories_list.removeRow(row)
            self._save_custom_categories()
        else:
            QMessageBox.information(self, "Info", "Select a category to remove.")

    def _make_category_combo(self, current_value="⭐ Custom"):
        """Create a category dropdown for catalog table."""
        combo = QComboBox()
        combo.setStyleSheet(
            "background-color: #313244; color: #cdd6f4; border: 1px solid #585b70; "
            "padding: 3px; font-size: 12px;"
        )
        categories = self._get_all_categories()
        for cat in categories:
            combo.addItem(cat)
        # Set current
        idx = combo.findText(current_value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.addItem(current_value)
            combo.setCurrentIndex(combo.count() - 1)
        return combo

    def _load_custom_catalog(self):
        """Load custom catalog packages from config into the table."""
        custom_pkgs = self.config.get("custom_catalog", [])
        print(f"[DEBUG] Loading custom catalog: {custom_pkgs}")
        self.custom_catalog_table.setRowCount(len(custom_pkgs))
        for i, pkg in enumerate(custom_pkgs):
            self.custom_catalog_table.setItem(i, 0, QTableWidgetItem(pkg.get("name", "")))
            self.custom_catalog_table.setItem(i, 1, QTableWidgetItem(pkg.get("desc", "")))
            # Category as dropdown
            cat_combo = self._make_category_combo(pkg.get("category", "⭐ Custom"))
            self.custom_catalog_table.setCellWidget(i, 2, cat_combo)

    def _add_custom_catalog_pkg(self):
        """Add a new custom catalog package row."""
        row = self.custom_catalog_table.rowCount()
        self.custom_catalog_table.insertRow(row)
        self.custom_catalog_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_catalog_table.setItem(row, 1, QTableWidgetItem(""))
        cat_combo = self._make_category_combo("⭐ Custom")
        self.custom_catalog_table.setCellWidget(row, 2, cat_combo)
        self.custom_catalog_table.editItem(self.custom_catalog_table.item(row, 0))

    def _remove_custom_catalog_pkg(self):
        """Remove selected custom catalog package."""
        rows = self.custom_catalog_table.selectionModel().selectedRows()
        if rows:
            for r in sorted([r.row() for r in rows], reverse=True):
                self.custom_catalog_table.removeRow(r)
        else:
            row = self.custom_catalog_table.currentRow()
            if row >= 0:
                self.custom_catalog_table.removeRow(row)
            else:
                QMessageBox.information(self, "Info", "Select a row to remove.")
                return
        self._save_custom_catalog()

    def _save_custom_catalog(self):
        """Save custom catalog table to config."""
        self.custom_catalog_table.setCurrentItem(None)

        pkgs = []
        for row in range(self.custom_catalog_table.rowCount()):
            name_item = self.custom_catalog_table.item(row, 0)
            desc_item = self.custom_catalog_table.item(row, 1)
            cat_widget = self.custom_catalog_table.cellWidget(row, 2)
            name = name_item.text().strip() if name_item else ""
            desc = desc_item.text().strip() if desc_item else ""
            if isinstance(cat_widget, QComboBox):
                cat = cat_widget.currentText()
            else:
                cat_item = self.custom_catalog_table.item(row, 2)
                cat = cat_item.text().strip() if cat_item else "⭐ Custom"
            if name or desc:
                pkgs.append({
                    "name": name,
                    "desc": desc,
                    "category": cat if cat else "⭐ Custom",
                })
        print(f"[DEBUG] Saving custom catalog: {pkgs}")
        self.config.set("custom_catalog", pkgs)
        verify = self.config.get("custom_catalog", [])
        print(f"[DEBUG] Verify after save: {verify}")

    def _open_log_folder(self):
        """Open the log directory in file manager."""
        from src.utils.logger import get_log_dir
        import subprocess
        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        if get_platform() == "windows":
            os.startfile(str(log_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(log_dir)])
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])

    def _open_config_folder(self):
        """Open the config directory in file manager."""
        import subprocess
        config_dir = self.config.config_file_path.parent
        if get_platform() == "windows":
            os.startfile(str(config_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(config_dir)])
        else:
            subprocess.Popen(["xdg-open", str(config_dir)])

    def _add_python_to_path(self):
        """Add a Python installation to system PATH automatically."""
        import subprocess

        platform = get_platform()

        # Collect all known Python paths from table
        python_paths = []
        for row in range(self.python_table.rowCount()):
            path_item = self.python_table.item(row, 1)
            ver_item = self.python_table.item(row, 0)
            if path_item and ver_item:
                exe_path = path_item.text()
                python_paths.append({
                    "version": ver_item.text(),
                    "exe": exe_path,
                    "folder": os.path.dirname(exe_path),
                })

        if not python_paths:
            QMessageBox.warning(self, "Warning", "No Python installations found. Run Scan System first.")
            return

        # Let user choose which one
        items = [f"Python {p['version']}  —  {p['folder']}" for p in python_paths]
        item, ok = QInputDialog.getItem(
            self, "Add Python to PATH",
            "Select which Python to add to PATH:",
            items, 0, False,
        )
        if not ok or not item:
            return

        selected = python_paths[items.index(item)]
        folder = selected['folder']
        version = selected['version']

        if platform == "windows":
            scripts = os.path.join(folder, "Scripts")
            reply = QMessageBox.question(
                self, "Confirm",
                f"Add to User PATH?\n\n  {folder}\n  {scripts}\n\n"
                f"A terminal restart may be needed.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            ps_cmd = (
                f'$userPath = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'$newPaths = @("{folder}", "{scripts}"); '
                f'foreach ($p in $newPaths) {{ '
                f'  if ($userPath -notlike "*$p*") {{ '
                f'    $userPath = "$userPath;$p" '
                f'  }} '
                f'}}; '
                f'[Environment]::SetEnvironmentVariable("Path", $userPath, "User")'
            )
            try:
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    **subprocess_args(capture_output=True, text=True, timeout=15)
                )
                if result.returncode == 0:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Python {version} added to User PATH!\n\n"
                        f"  {folder}\n  {scripts}\n\n"
                        f"Restart your terminal for the change to take effect."
                    )
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update PATH:\n{result.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to run PowerShell:\n{e}")

        else:
            # Linux / macOS — write export line to shell config files
            export_line = f'export PATH="{folder}:$PATH"'

            # Detect shell config files
            home = Path.home()
            candidates = [home / ".bashrc", home / ".bash_profile", home / ".zshrc", home / ".profile"]
            existing = [str(p) for p in candidates if p.exists()]

            if not existing:
                existing = [str(home / ".bashrc")]  # fallback: create .bashrc

            # Let user pick which file
            file_choice, ok = QInputDialog.getItem(
                self, "Select Shell Config",
                f"Add  {export_line}  to which file?",
                existing, 0, False,
            )
            if not ok or not file_choice:
                return

            reply = QMessageBox.question(
                self, "Confirm",
                f"Append to {file_choice}:\n\n  {export_line}\n\n"
                f"Run  source {file_choice}  or restart terminal after.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            try:
                config_file = Path(file_choice)
                existing_text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""

                # Check if already present
                if folder in existing_text:
                    QMessageBox.information(
                        self, "Already in PATH",
                        f"{folder} is already in {file_choice}.\nNo changes made."
                    )
                    return

                with open(config_file, "a", encoding="utf-8") as f:
                    f.write(f"\n# Added by VenvStudio\n{export_line}\n")

                QMessageBox.information(
                    self, "✅ Success",
                    f"Added to {file_choice}:\n\n  {export_line}\n\n"
                    f"Run the following to apply now:\n"
                    f"  source {file_choice}"
                )
            except PermissionError:
                # Try pkexec as fallback
                import tempfile
                script = f'#!/bin/bash\necho "\n# Added by VenvStudio\n{export_line}" >> "{file_choice}"\n'
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
                    tmp.write(script)
                    tmp_path = tmp.name
                os.chmod(tmp_path, 0o755)
                try:
                    result = subprocess.run(["pkexec", "bash", tmp_path], timeout=30)
                    if result.returncode == 0:
                        QMessageBox.information(self, "✅ Success", f"Added to {file_choice} (admin).\n\nRun: source {file_choice}")
                    else:
                        QMessageBox.critical(self, "Error", f"pkexec failed. Try manually:\n  {export_line} >> {file_choice}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to write to {file_choice}:\n{e}")

    def _toggle_vs_cli(self):
        """Copy vs.bat/vs.py to venv base dir and add that dir to User PATH."""
        import shutil, subprocess

        venv_dir = str(self.config.get_venv_base_dir())
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(project_root)  # up to VenvStudio root

        vs_py_src = os.path.join(project_root, "vs.py")
        vs_bat_src = os.path.join(project_root, "vs.bat")

        if not os.path.isfile(vs_py_src):
            QMessageBox.critical(self, "Error", f"vs.py not found at:\n{vs_py_src}")
            return

        # Copy vs.py and vs.bat to venv base dir
        vs_py_dst = os.path.join(venv_dir, "vs.py")
        vs_bat_dst = os.path.join(venv_dir, "vs.bat")

        try:
            shutil.copy2(vs_py_src, vs_py_dst)
            if os.path.isfile(vs_bat_src):
                shutil.copy2(vs_bat_src, vs_bat_dst)
            else:
                # Create vs.bat pointing to vs.py in same dir
                with open(vs_bat_dst, "w") as f:
                    f.write(f'@echo off\npython "%~dp0vs.py" %*\n')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to copy CLI files:\n{e}")
            return

        if get_platform() == "windows":
            # Check if already in PATH
            ps_check = (
                f'$p = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'$p -like "*{venv_dir}*"'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_check],
                **subprocess_args(capture_output=True, text=True, timeout=10)
            )
            already_in = "True" in result.stdout

            if already_in:
                QMessageBox.information(
                    self, "Already Active",
                    f"'vs' CLI is already active!\n\n"
                    f"Directory: {venv_dir}\n\n"
                    f"Usage:\n  vs list\n  vs create myenv\n  vs install myenv numpy"
                )
                return

            reply = QMessageBox.question(
                self, "Enable 'vs' CLI",
                f"This will:\n\n"
                f"1. Copy vs.py & vs.bat to:\n   {venv_dir}\n\n"
                f"2. Add that folder to your User PATH\n\n"
                f"After this you can use 'vs' from any terminal:\n"
                f"  vs list\n  vs create myenv\n  vs install myenv numpy\n\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            ps_cmd = (
                f'$userPath = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'if ($userPath -notlike "*{venv_dir}*") {{ '
                f'  [Environment]::SetEnvironmentVariable("Path", "$userPath;{venv_dir}", "User") '
                f'}}; '
            )
            try:
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    **subprocess_args(capture_output=True, text=True, timeout=15)
                )
                if result.returncode == 0:
                    self.config.set("vs_cli_enabled", True)
                    QMessageBox.information(
                        self, "Success",
                        f"'vs' CLI enabled! ✅\n\n"
                        f"PATH added: {venv_dir}\n\n"
                        f"Restart your terminal, then try:\n"
                        f"  vs list\n  vs create myenv\n  vs install myenv numpy pandas"
                    )
                else:
                    QMessageBox.critical(self, "Error", f"Failed:\n{result.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed:\n{e}")
        else:
            self.config.set("vs_cli_enabled", True)
            QMessageBox.information(
                self, "Enable 'vs' CLI",
                f"Files copied to: {venv_dir}\n\n"
                f"Add to ~/.bashrc or ~/.zshrc:\n"
                f'  export PATH="{venv_dir}:$PATH"\n\n'
                f"Then: source ~/.bashrc"
            )

    def _clear_all_data(self):
        """Remove all config, log, and cache files."""
        import shutil
        reply = QMessageBox.warning(
            self, "Remove All Data",
            "This will delete ALL VenvStudio settings, logs, and cache.\n\n"
            "Your virtual environments will NOT be deleted.\n\n"
            "The application will close. Are you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        config_dir = self.config.config_file_path.parent
        try:
            # Remove config directory
            if config_dir.exists():
                shutil.rmtree(str(config_dir))
            QMessageBox.information(
                self, "Done",
                f"All data removed from:\n{config_dir}\n\nApplication will now close."
            )
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove data:\n{e}")

    def populate_vscode_envs(self, env_list):
        """Populate VS Code env selector from main window."""
        self.vscode_env_combo.blockSignals(True)
        self.vscode_env_combo.clear()
        self.vscode_env_combo.addItem("-- Select Environment --", "")
        for name, path in env_list:
            self.vscode_env_combo.addItem(name, str(path))
        self.vscode_env_combo.blockSignals(False)

    def _toggle_builtin_categories(self, visible):
        """Show/hide built-in categories table."""
        self.builtin_cats_table.setVisible(visible)

    def _check_for_updates(self):
        """Check PyPI for new version."""
        self.update_status_label.setText("🔍 Checking...")
        self.update_status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")

        # Run in background thread
        self._update_worker = _UpdateCheckWorker(parent=self)
        self._update_worker.finished.connect(self._on_update_check_done)
        self._update_worker.start()

    def _on_update_check_done(self, result):
        """Handle update check result."""
        if result.get("error"):
            self.update_status_label.setText(f"⚠️ {result['error']}")
            self.update_status_label.setStyleSheet("color: #f9e2af; font-size: 12px;")
            return

        if result["update_available"]:
            self.update_status_label.setText(
                f"🆕 New version available: v{result['latest_version']} (current: v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")

            reply = QMessageBox.question(
                self, "🆕 Update Available",
                f"VenvStudio v{result['latest_version']} is available!\n"
                f"You have v{result['current_version']}.\n\n"
                f"Update with:\n  pip install --upgrade venvstudio\n\n"
                f"Or download from GitHub Releases.\n\n"
                f"Open download page?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open(result["release_url"])
        else:
            self.update_status_label.setText(
                f"✅ You're up to date! (v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")

    def _export_settings(self):
        """Export settings to a JSON file."""
        import json
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "venvstudio_settings.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not filepath:
            return
        try:
            # Read current config file
            config_path = self.config.config_file_path
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Success", f"Settings exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _import_settings(self):
        """Import settings from a JSON file."""
        import json
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not filepath:
            return
        reply = QMessageBox.question(
            self, "Import Settings",
            "This will overwrite your current settings.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Write to config
            config_path = self.config.config_file_path
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.config.load()
            self._load_current_settings()
            QMessageBox.information(self, "Success", "Settings imported! Some changes may need a restart.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{e}")

    # ── Environment Export (from Settings page) ──

    def _pick_env_and_freeze(self):
        """Let user pick an environment, return (freeze_text, python_version) or (None, None)."""
        import subprocess
        from src.core.venv_manager import VenvManager
        from src.core.pip_manager import PipManager
        from src.utils.platform_utils import get_python_executable, subprocess_args

        vm = VenvManager(Path(self.config.get_venv_base_dir()))
        envs = vm.list_venvs()
        if not envs:
            QMessageBox.warning(self, "Warning", "No environments found.")
            return None, None

        env_names = [e.name for e in envs]
        name, ok = QInputDialog.getItem(
            self, "Select Environment",
            "Choose an environment to export:", env_names, 0, False
        )
        if not ok or not name:
            return None, None

        venv_path = vm.base_dir / name
        pm = PipManager(venv_path)
        freeze = pm.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", f"No packages in '{name}'.")
            return None, None

        py_ver = "3.12"
        try:
            exe = get_python_executable(venv_path)
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            py_ver = ".".join(ver.split(".")[:2])
        except Exception:
            pass
        return freeze, py_ver

    def _export_env_requirements(self):
        freeze, _ = self._pick_env_and_freeze()
        if not freeze:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export requirements.txt", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_dockerfile(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        dockerfile = (
            f"# Auto-generated by VenvStudio\n"
            f"FROM python:{py_ver}-slim\nWORKDIR /app\n\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n\n"
            f"COPY . .\n# CMD [\"python\", \"main.py\"]\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Dockerfile", "Dockerfile", "All Files (*)")
        if filepath:
            req_path = Path(filepath).parent / "requirements.txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported:\n  {filepath}\n  {req_path}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_docker_compose(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        compose = (
            f"version: '3.8'\nservices:\n  app:\n    build: .\n"
            f"    ports:\n      - \"8000:8000\"\n    volumes:\n      - .:/app\n"
        )
        dockerfile = (
            f"FROM python:{py_ver}-slim\nWORKDIR /app\n"
            f"COPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n"
            f"COPY . .\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export docker-compose.yml", "docker-compose.yml", "YAML Files (*.yml);;All Files (*)"
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
                QMessageBox.information(self, "✅ Success", f"Exported 3 files to {base}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_pyproject(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        deps = "\n".join(f'    "{l.strip()}",' for l in freeze.strip().splitlines()
                         if l.strip() and not l.startswith("#"))
        content = (
            f'[build-system]\nrequires = ["setuptools>=68.0", "wheel"]\n'
            f'build-backend = "setuptools.backends._legacy:_Backend"\n\n'
            f'[project]\nname = "myproject"\nversion = "0.1.0"\n'
            f'requires-python = ">={py_ver}"\ndependencies = [\n{deps}\n]\n'
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export pyproject.toml", "pyproject.toml", "TOML Files (*.toml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_conda_yml(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        pip_deps = "\n".join(f"    - {l.strip()}" for l in freeze.strip().splitlines()
                             if l.strip() and not l.startswith("#"))
        content = (
            f"name: myenv\nchannels:\n  - defaults\n  - conda-forge\n"
            f"dependencies:\n  - python={py_ver}\n  - pip\n  - pip:\n{pip_deps}\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export environment.yml", "environment.yml", "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_clipboard(self):
        freeze, _ = self._pick_env_and_freeze()
        if not freeze:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(freeze)
        count = len(freeze.strip().splitlines())
        QMessageBox.information(self, "✅ Copied", f"{count} packages copied to clipboard.")

    def _save_settings(self):
        """Save all settings."""
        # Theme
        if self.theme_cb.isChecked():
            new_theme = self.theme_combo.currentData()
        else:
            new_theme = "dark"
        old_theme = self.config.get("theme", "dark")
        self.config.set("theme", new_theme)
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        # Font
        if self.font_cb.isChecked():
            font_family = self.font_combo.currentFont().family()
            self.config.set("font_family", font_family)
        else:
            font_family = "Segoe UI"
            self.config.set("font_family", "")  # empty = default

        if self.font_size_cb.isChecked():
            font_size = self.font_size_spin.value()
            self.config.set("font_size", font_size)
        else:
            font_size = 13
            self.config.set("font_size", 13)  # 13 = default

        self.font_changed.emit(font_family, font_size)

        # Language
        new_lang = self.lang_combo.currentData()
        if not new_lang:
            new_lang = "en"
        old_lang = self.config.get("language", "en")
        self.config.set("language", new_lang)
        lang_changed = (new_lang != old_lang and self.lang_enabled_cb.isChecked())
        if lang_changed:
            self.language_changed.emit(new_lang)

        # Default Python
        # Default Python — only save if checkbox is enabled
        if self.default_py_cb.isChecked():
            self.config.set("default_python", self.default_python_combo.currentData() or "")
        else:
            self.config.set("default_python", "")

        # Venv directory
        new_dir = self.venv_dir_input.text()
        self.config.set_venv_base_dir(new_dir)

        # General
        self.config.set("auto_upgrade_pip", self.auto_pip_cb.isChecked())
        self.config.set("confirm_delete", self.confirm_delete_cb.isChecked())
        self.config.set("show_hidden_packages", self.show_hidden_cb.isChecked())
        self.config.set("check_updates", self.check_updates_cb.isChecked())
        self.config.set("save_window_geometry", self.save_window_cb.isChecked())

        # Package manager — only save if checkbox is enabled
        if self.pkg_mgr_cb.isChecked():
            self.config.set("package_manager", self.pkg_manager_combo.currentData() or "pip")
        else:
            self.config.set("package_manager", "pip")
        # Default Terminal — only save if checkbox is enabled
        if self.terminal_cb.isChecked():
            self.config.set("default_terminal", self.terminal_combo.currentData())
        else:
            self.config.set("default_terminal", "")

        # Save custom categories
        self._save_custom_categories()

        # Save custom catalog
        self._save_custom_catalog()

        self.settings_saved.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully! ✅")

        if lang_changed:
            reply = QMessageBox.question(
                self, "Restart Required",
                "Language changed. VenvStudio needs to restart.\n\nRestart now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                import sys, subprocess
                from PySide6.QtWidgets import QApplication
                # Find the main script
                main_script = sys.argv[0] if sys.argv else "main.py"
                subprocess.Popen([sys.executable, main_script])
                QApplication.instance().quit()

    def _reset_all(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.warning(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from src.core.config_manager import DEFAULT_SETTINGS
            for key, value in DEFAULT_SETTINGS.items():
                self.config.set(key, value)
            self.config.set("custom_pythons", [])
            self._load_current_settings()
            self.theme_changed.emit("dark")
            QMessageBox.information(self, "Settings", "All settings reset to defaults.")


class _DownloadWorker(QThread):
    """Background worker for downloading Python."""
    progress = Signal(str)
    finished = Signal(bool, str)  # success, message

    def __init__(self, version_info, parent=None):
        super().__init__(parent)
        self.version_info = version_info

    def run(self):
        try:
            from src.core.python_downloader import download_python
            result = download_python(self.version_info, progress_callback=self.progress.emit)
            self.finished.emit(True, str(result))
        except Exception as e:
            self.finished.emit(False, str(e))


class _UpdateCheckWorker(QThread):
    """Background worker for checking PyPI updates."""
    finished = Signal(dict)

    def run(self):
        try:
            from src.core.updater import check_for_update
            result = check_for_update()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e), "update_available": False})


class _FetchWorker(QThread):
    """Background worker for fetching available versions."""
    progress = Signal(str)
    finished = Signal(list)

    def run(self):
        try:
            from src.core.python_downloader import get_available_versions
            versions = get_available_versions(progress_callback=self.progress.emit)
            self.finished.emit(versions)
        except Exception:
            self.finished.emit([])


class PythonDownloadDialog(QDialog):
    """Dialog for downloading standalone Python builds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⬇️ Download Python")
        self.setMinimumSize(550, 420)
        self._versions = []
        self._setup_ui()
        self._fetch_versions()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "Download standalone Python builds from\n"
            "astral-sh/python-build-standalone (same builds used by uv)"
        )
        header.setStyleSheet("color: #a6adc8; font-size: 12px;")
        header.setWordWrap(True)
        layout.addWidget(header)

        # Version list
        self.version_list = QListWidget()
        self.version_list.setStyleSheet(
            "QListWidget { font-size: 13px; }"
            "QListWidget::item { padding: 6px; }"
            "QListWidget::item:selected { background-color: #89b4fa; color: #1e1e2e; }"
        )
        layout.addWidget(self.version_list)

        # Progress
        self.progress_label = QLabel("Fetching available versions...")
        self.progress_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Install location
        from src.core.python_downloader import get_pythons_dir
        loc_label = QLabel(f"📂 Install location: {get_pythons_dir()}")
        loc_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        loc_label.setWordWrap(True)
        layout.addWidget(loc_label)

        # Buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("👤 User Install")
        self.download_btn.setToolTip("Install to VenvStudio pythons folder (no admin)")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(lambda: self._start_download("user"))
        btn_layout.addWidget(self.download_btn)

        self.system_download_btn = QPushButton("🖥️ System Install")
        self.system_download_btn.setToolTip("Install to Program Files (admin required)")
        self.system_download_btn.setEnabled(False)
        self.system_download_btn.clicked.connect(lambda: self._start_download("system"))
        btn_layout.addWidget(self.system_download_btn)

        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.version_list.currentRowChanged.connect(self._on_selection_changed)

    def _fetch_versions(self):
        """Fetch available versions in background."""
        self._fetch_worker = _FetchWorker(parent=self)
        self._fetch_worker.progress.connect(self._on_progress)
        self._fetch_worker.finished.connect(self._on_versions_fetched)
        self._fetch_worker.start()

    def _on_versions_fetched(self, versions):
        self._versions = versions
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        if not versions:
            self.progress_label.setText("❌ Could not fetch versions. Check your internet connection.")
            return

        # Also get installed versions
        from src.core.python_downloader import get_installed_pythons
        installed = {py["version"] for py in get_installed_pythons()}

        self.version_list.clear()
        for v in versions:
            size_mb = v.get("size", 0) / (1024 * 1024)
            is_installed = v["version"] in installed

            if is_installed:
                text = f"✅ Python {v['version']}  —  {size_mb:.0f} MB  (installed)"
            else:
                text = f"🐍 Python {v['version']}  —  {size_mb:.0f} MB"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, v)
            if is_installed:
                item.setForeground(QColor("#a6e3a1"))
            self.version_list.addItem(item)

        self.progress_label.setText(f"Found {len(versions)} available versions.")
        self.download_btn.setEnabled(True)
        self.system_download_btn.setEnabled(True)

    def _on_selection_changed(self, row):
        if row < 0:
            self.download_btn.setEnabled(False)
            self.system_download_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return
        item = self.version_list.item(row)
        v = item.data(Qt.UserRole)
        from src.core.python_downloader import get_installed_pythons
        installed = {py["version"] for py in get_installed_pythons()}
        is_installed = v["version"] in installed
        self.download_btn.setEnabled(not is_installed)
        self.system_download_btn.setEnabled(not is_installed)
        self.remove_btn.setEnabled(is_installed)

    def _on_progress(self, text):
        self.progress_label.setText(text)
        # Parse percentage if available
        if "%" in text:
            try:
                pct_str = text.split("(")[-1].split("%")[0]
                pct = int(float(pct_str))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(pct)
            except (ValueError, IndexError):
                pass

    def _start_download(self, mode="user"):
        row = self.version_list.currentRow()
        if row < 0:
            return

        item = self.version_list.item(row)
        version_info = item.data(Qt.UserRole).copy()
        version_info["_install_mode"] = mode

        if mode == "system":
            from src.utils.platform_utils import get_platform
            version = version_info["version"]
            plat = get_platform()

            if plat == "windows":
                ver_short = version.replace(".", "")[:3]
                target_dir = f"C:\\Program Files\\Python{ver_short}"
            elif plat == "macos":
                target_dir = f"/usr/local/python/{version}"
            else:  # linux
                target_dir = f"/opt/python/{version}"

            confirm = QMessageBox.question(
                self, "🖥️ System Install",
                f"Install Python {version} to:\n\n"
                f"  📂 {target_dir}\n\n"
                f"This requires {'admin' if plat == 'windows' else 'sudo'} permission.\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        self.download_btn.setEnabled(False)
        self.system_download_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)

        self._dl_worker = _DownloadWorker(version_info, parent=self)
        self._dl_worker.progress.connect(self._on_progress)
        self._dl_worker.finished.connect(
            lambda ok, msg: self._on_download_finished(ok, msg, mode)
        )
        self._dl_worker.start()

    def _on_download_finished(self, success, message, mode="user"):
        self.progress_bar.setRange(0, 100)
        if success:
            if mode == "system":
                # Move from user dir to Program Files via admin
                self._move_to_system(message)
            else:
                self.progress_bar.setValue(100)
                self.progress_label.setText("✅ Download complete!")
                QMessageBox.information(self, "✅ Success", f"Python installed to:\n{message}")
                self._fetch_versions()
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"❌ Download failed")
            QMessageBox.critical(self, "Error", f"Download failed:\n{message}")
            self.download_btn.setEnabled(True)
            self.system_download_btn.setEnabled(True)

    def _move_to_system(self, source_dir):
        """Move downloaded Python to system directory (admin/sudo required)."""
        import subprocess, tempfile, os, shutil
        from src.utils.platform_utils import get_platform, subprocess_args
        from pathlib import Path

        source = Path(source_dir)
        plat = get_platform()

        # Find python executable to detect version
        from src.core.python_downloader import get_python_exe
        exe = get_python_exe(source)
        if not exe:
            QMessageBox.critical(self, "Error", "Could not find python executable in downloaded files.")
            return

        try:
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10,
                **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
        except Exception:
            ver = source.name.replace("cpython-", "")

        # The extracted content has a 'python' subfolder
        python_subdir = source / "python"
        actual_source = str(python_subdir) if python_subdir.exists() else str(source)

        # Determine target based on platform
        if plat == "windows":
            ver_short = ver.replace(".", "")[:3]
            target = Path(f"C:\\Program Files\\Python{ver_short}")
        elif plat == "macos":
            target = Path(f"/usr/local/python/{ver}")
        else:  # linux
            target = Path(f"/opt/python/{ver}")

        self.progress_label.setText(f"Installing to {target}...")

        try:
            if plat == "windows":
                self._system_install_windows(actual_source, target, ver, source)
            else:
                self._system_install_unix(actual_source, target, ver, source, plat)
        except Exception as e:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_label.setText("❌ System install failed")
            QMessageBox.critical(self, "Error", f"System install failed:\n{e}")

    def _system_install_windows(self, actual_source, target, ver, source):
        """Windows system install via PowerShell admin elevation."""
        import subprocess, tempfile, os, shutil
        from src.utils.platform_utils import subprocess_args

        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_result.txt")
        ps_script = f'''
try {{
    if (Test-Path '{target}') {{ Remove-Item -Recurse -Force '{target}' }}
    Copy-Item -Recurse '{actual_source}' '{target}'
    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        ps_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_py.ps1")
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_script)

        if os.path.exists(result_file):
            os.unlink(result_file)

        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f"Start-Process -FilePath 'powershell.exe' "
                    f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"{ps_file}\"' "
                    f"-Verb RunAs -Wait"
                ],
                capture_output=True, text=True, timeout=300,
                **subprocess_args()
            )

            import time
            time.sleep(1)

            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_text = f.read().strip()
                if result_text.startswith("OK"):
                    shutil.rmtree(str(source), ignore_errors=True)
                    self._show_system_install_success(ver, target)
                    return
                else:
                    raise RuntimeError(result_text)

            raise RuntimeError("Admin operation may have been cancelled.")
        finally:
            for fp in [ps_file, result_file]:
                try:
                    os.unlink(fp)
                except Exception:
                    pass

    def _system_install_unix(self, actual_source, target, ver, source, plat):
        """Linux/macOS system install via sudo."""
        import subprocess, shutil

        # Build shell script
        script = f'''#!/bin/bash
set -e
if [ -d "{target}" ]; then
    rm -rf "{target}"
fi
mkdir -p "{target}"
cp -a "{actual_source}/." "{target}/"

# Create symlinks in /usr/local/bin
PYTHON_EXE=""
if [ -f "{target}/bin/python3" ]; then
    PYTHON_EXE="{target}/bin/python3"
elif [ -f "{target}/bin/python" ]; then
    PYTHON_EXE="{target}/bin/python"
fi

if [ -n "$PYTHON_EXE" ]; then
    VER_SHORT=$(echo "{ver}" | cut -d. -f1,2)
    ln -sf "$PYTHON_EXE" "/usr/local/bin/python$VER_SHORT" 2>/dev/null || true
fi

echo "OK"
'''
        import tempfile, os
        script_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_py.sh")
        with open(script_file, 'w') as f:
            f.write(script)
        os.chmod(script_file, 0o755)

        try:
            # Try pkexec first (graphical sudo), fallback to sudo in terminal
            sudo_cmds = [
                ["pkexec", "bash", script_file],
                ["sudo", "bash", script_file],
            ]

            success = False
            for cmd in sudo_cmds:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120
                    )
                    if result.returncode == 0 and "OK" in result.stdout:
                        success = True
                        break
                except FileNotFoundError:
                    continue

            if success:
                shutil.rmtree(str(source), ignore_errors=True)
                symlink_note = ""
                if plat == "linux":
                    ver_short = ".".join(ver.split(".")[:2])
                    symlink_note = f"\n\nSymlink created: /usr/local/bin/python{ver_short}"
                self._show_system_install_success(ver, target, symlink_note)
            else:
                raise RuntimeError(
                    "sudo/pkexec failed. You can manually install with:\n"
                    f"  sudo cp -a {actual_source} {target}"
                )
        finally:
            try:
                os.unlink(script_file)
            except Exception:
                pass

    def _show_system_install_success(self, ver, target, extra_note=""):
        """Show success message after system install."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("✅ System install complete!")
        QMessageBox.information(
            self, "✅ Success",
            f"Python {ver} installed to:\n{target}{extra_note}\n\n"
            f"You may want to add it to PATH or use 'Set System Default'."
        )
        self._fetch_versions()

    def _remove_selected(self):
        row = self.version_list.currentRow()
        if row < 0:
            return

        item = self.version_list.item(row)
        version_info = item.data(Qt.UserRole)
        version = version_info["version"]

        confirm = QMessageBox.question(
            self, "Remove Python",
            f"Remove Python {version}?\nThis will delete the standalone installation.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        from src.core.python_downloader import get_installed_pythons, remove_python
        for py in get_installed_pythons():
            if py["version"] == version:
                remove_python(py["path"])
                break

        self._fetch_versions()
