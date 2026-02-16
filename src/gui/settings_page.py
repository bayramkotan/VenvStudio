"""
VenvStudio - Settings Page
Full settings panel: Language, Theme, Font, Python Management, Paths, General
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QFontComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.utils.platform_utils import find_system_pythons, get_platform
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
        self.lang_combo.setEnabled(False)  # Disabled until checkbox is checked
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

        # ── 5. GENERAL ──
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
            self.terminal_combo.addItem("xterm", "xterm")
        terminal_row.addWidget(self.terminal_combo, 1)
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
        # If non-default language, enable the checkbox
        if lang != "en":
            self.lang_enabled_cb.setChecked(True)

        # Venv dir
        self.venv_dir_input.setText(str(self.config.get_venv_base_dir()))

        # General options
        self.auto_pip_cb.setChecked(self.config.get("auto_upgrade_pip", True))
        self.confirm_delete_cb.setChecked(self.config.get("confirm_delete", True))
        self.show_hidden_cb.setChecked(self.config.get("show_hidden_packages", False))
        self.check_updates_cb.setChecked(self.config.get("check_updates", False))
        self.save_window_cb.setChecked(self.config.get("save_window_geometry", True))

        # Terminal — only enable if explicitly set to non-default
        terminal = self.config.get("default_terminal", "")
        if terminal and terminal.strip():
            idx = self.terminal_combo.findData(terminal)
            if idx > 0:  # index 0 is first/default terminal
                self.terminal_cb.setChecked(True)
                self.terminal_combo.setEnabled(True)
                self.terminal_combo.setCurrentIndex(idx)
            else:
                self.terminal_cb.setChecked(False)
                self.terminal_combo.setEnabled(False)
                self.terminal_combo.setCurrentIndex(0)
                self.config.set("default_terminal", "")
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
        for version, path in system_pythons:
            norm_path = os.path.normpath(path)
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(version))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))
            self.python_table.setItem(row, 2, QTableWidgetItem("System"))
            self.default_python_combo.addItem(f"Python {version}", norm_path)

        # Custom pythons from config
        custom_pythons = self.config.get("custom_pythons", [])
        for entry in custom_pythons:
            norm_path = os.path.normpath(entry.get("path", ""))
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
        if get_platform() == "windows":
            filter_str = "Python Executable (python.exe);;All Files (*)"
        else:
            filter_str = "All Files (*)"

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Python Executable", "", filter_str
        )
        if not filepath:
            return

        # Normalize path for current OS
        import os
        filepath = os.path.normpath(filepath)

        # Verify it's a valid Python
        import subprocess
        try:
            result = subprocess.run(
                [filepath, "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Not a valid Python executable:\n{e}")
            return

        # Save to config
        custom_pythons = self.config.get("custom_pythons", [])
        # Check duplicate
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
        if get_platform() != "windows":
            QMessageBox.information(
                self, "Add Python to PATH",
                "On Linux/macOS, add to ~/.bashrc or ~/.zshrc:\n\n"
                '  export PATH="$HOME/.local/bin:$PATH"\n\n'
                "Then run: source ~/.bashrc"
            )
            return

        # Collect all known Python paths
        python_paths = []
        for row in range(self.python_table.rowCount()):
            path_item = self.python_table.item(row, 1)
            ver_item = self.python_table.item(row, 0)
            if path_item and ver_item:
                exe_path = path_item.text()
                folder = os.path.dirname(exe_path)
                scripts = os.path.join(folder, "Scripts")
                python_paths.append({
                    "version": ver_item.text(),
                    "folder": folder,
                    "scripts": scripts,
                })

        if not python_paths:
            QMessageBox.warning(self, "Warning", "No Python installations found. Run Scan System first.")
            return

        # Let user choose which one
        items = [f"Python {p['version']}  —  {p['folder']}" for p in python_paths]
        item, ok = QInputDialog.getItem(
            self, "Add Python to PATH",
            "Select which Python to add to your User PATH:",
            items, 0, False,
        )
        if not ok or not item:
            return

        idx = items.index(item)
        selected = python_paths[idx]

        # Confirm
        reply = QMessageBox.question(
            self, "Confirm",
            f"Add these folders to your User PATH?\n\n"
            f"  {selected['folder']}\n"
            f"  {selected['scripts']}\n\n"
            f"This modifies your user environment variables.\n"
            f"A restart of your terminal/apps may be needed.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Add to User PATH on Windows via PowerShell
        import subprocess
        folder = selected['folder']
        scripts = selected['scripts']
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
                    self, "Success",
                    f"Python {selected['version']} added to User PATH!\n\n"
                    f"  {folder}\n  {scripts}\n\n"
                    f"Restart your terminal or apps for the change to take effect."
                )
            else:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to update PATH:\n{result.stderr}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run PowerShell:\n{e}")

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
        print(f"[DEBUG] Language: old={old_lang}, new={new_lang}, checkbox={self.lang_enabled_cb.isChecked()}")
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
