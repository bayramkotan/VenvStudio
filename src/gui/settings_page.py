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

        # Theme
        self.theme_combo = NoScrollComboBox()
        self.theme_combo.addItem("🌙 Dark", "dark")
        self.theme_combo.addItem("☀️ Light", "light")
        appearance_layout.addRow(f"{tr('theme')}", self.theme_combo)

        # Font family
        self.font_combo = QFontComboBox()
        appearance_layout.addRow(f"{tr('font')}", self.font_combo)

        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(13)
        self.font_size_spin.setSuffix(" px")
        appearance_layout.addRow(f"{tr('font_size')}", self.font_size_spin)

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

        # ── 7. CUSTOM CATALOG EDITOR ──
        catalog_group = QGroupBox("📚 Custom Catalog Packages")
        catalog_layout = QVBoxLayout()
        catalog_layout.setSpacing(10)

        catalog_info = QLabel("Add custom packages to the catalog. These appear under '⭐ Custom' category.")
        catalog_info.setWordWrap(True)
        catalog_info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        catalog_layout.addWidget(catalog_info)

        self.custom_catalog_table = QTableWidget()
        self.custom_catalog_table.setColumnCount(3)
        self.custom_catalog_table.setHorizontalHeaderLabels(["Package Name", "Description", "Category"])
        self.custom_catalog_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #313244;
                font-size: 13px;
            }
            QTableWidget::item {
                color: #cdd6f4;
                padding: 4px;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QTableWidget QLineEdit {
                background-color: #313244;
                color: #f5e0dc;
                border: 2px solid #89b4fa;
                padding: 4px 6px;
                font-size: 13px;
                min-height: 24px;
            }
        """)
        self.custom_catalog_table.verticalHeader().setDefaultSectionSize(32)
        self.custom_catalog_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_catalog_table.setSelectionMode(QTableWidget.SingleSelection)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.custom_catalog_table.setColumnWidth(0, 150)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.custom_catalog_table.setColumnWidth(2, 180)
        self.custom_catalog_table.setAlternatingRowColors(True)
        self.custom_catalog_table.verticalHeader().setVisible(False)
        self.custom_catalog_table.setMaximumHeight(180)
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

        diag_btn_layout.addStretch()
        diag_layout.addLayout(diag_btn_layout)
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

        # Font
        font_family = self.config.get("font_family", "Segoe UI")
        self.font_combo.setCurrentFont(QFont(font_family))

        font_size = self.config.get("font_size", 13)
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
                capture_output=True, text=True, timeout=5,
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

    def _load_custom_catalog(self):
        """Load custom catalog packages from config into the table."""
        custom_pkgs = self.config.get("custom_catalog", [])
        self.custom_catalog_table.setRowCount(len(custom_pkgs))
        for i, pkg in enumerate(custom_pkgs):
            self.custom_catalog_table.setItem(i, 0, QTableWidgetItem(pkg.get("name", "")))
            self.custom_catalog_table.setItem(i, 1, QTableWidgetItem(pkg.get("desc", "")))
            self.custom_catalog_table.setItem(i, 2, QTableWidgetItem(pkg.get("category", "⭐ Custom")))

    def _add_custom_catalog_pkg(self):
        """Add a new custom catalog package row."""
        row = self.custom_catalog_table.rowCount()
        self.custom_catalog_table.insertRow(row)
        self.custom_catalog_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_catalog_table.setItem(row, 1, QTableWidgetItem(""))
        self.custom_catalog_table.setItem(row, 2, QTableWidgetItem("⭐ Custom"))
        self.custom_catalog_table.editItem(self.custom_catalog_table.item(row, 0))

    def _remove_custom_catalog_pkg(self):
        """Remove selected custom catalog package."""
        rows = self.custom_catalog_table.selectionModel().selectedRows()
        if rows:
            for r in sorted([r.row() for r in rows], reverse=True):
                self.custom_catalog_table.removeRow(r)
        else:
            # Fallback: use current row
            row = self.custom_catalog_table.currentRow()
            if row >= 0:
                self.custom_catalog_table.removeRow(row)
            else:
                QMessageBox.information(self, "Info", "Select a row to remove.")
                return
        # Auto-save after removal
        self._save_custom_catalog()

    def _save_custom_catalog(self):
        """Save custom catalog table to config."""
        pkgs = []
        for row in range(self.custom_catalog_table.rowCount()):
            name_item = self.custom_catalog_table.item(row, 0)
            desc_item = self.custom_catalog_table.item(row, 1)
            cat_item = self.custom_catalog_table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            if name:
                pkgs.append({
                    "name": name,
                    "desc": desc_item.text().strip() if desc_item else "",
                    "category": cat_item.text().strip() if cat_item else "⭐ Custom",
                })
        self.config.set("custom_catalog", pkgs)

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
        """Show instructions or add Python to system PATH."""
        if get_platform() == "windows":
            msg = (
                "To add Python to your System PATH on Windows:\n\n"
                "1. Open Settings → System → About → Advanced system settings\n"
                "2. Click 'Environment Variables'\n"
                "3. Under 'System variables', find 'Path' and click 'Edit'\n"
                "4. Add the Python installation directory\n\n"
                "Or run this in PowerShell as Administrator:\n"
                '[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\\Python312", "Machine")'
            )
        else:
            msg = (
                "To add Python to your PATH on Linux/macOS:\n\n"
                "Add to ~/.bashrc or ~/.zshrc:\n"
                "  export PATH=\"$HOME/.local/bin:$PATH\"\n\n"
                "Then run: source ~/.bashrc"
            )
        QMessageBox.information(self, "Add Python to PATH", msg)

    def populate_vscode_envs(self, env_list):
        """Populate VS Code env selector from main window."""
        self.vscode_env_combo.blockSignals(True)
        self.vscode_env_combo.clear()
        self.vscode_env_combo.addItem("-- Select Environment --", "")
        for name, path in env_list:
            self.vscode_env_combo.addItem(name, str(path))
        self.vscode_env_combo.blockSignals(False)

    def _save_settings(self):
        """Save all settings."""
        # Theme
        new_theme = self.theme_combo.currentData()
        old_theme = self.config.get("theme", "dark")
        self.config.set("theme", new_theme)
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        # Font
        font_family = self.font_combo.currentFont().family()
        font_size = self.font_size_spin.value()
        self.config.set("font_family", font_family)
        self.config.set("font_size", font_size)
        self.font_changed.emit(font_family, font_size)

        # Language
        new_lang = self.lang_combo.currentData()
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
        # Default Terminal — only save if checkbox is enabled
        if self.terminal_cb.isChecked():
            self.config.set("default_terminal", self.terminal_combo.currentData())
        else:
            self.config.set("default_terminal", "")

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
                import sys, os
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
                os.execv(sys.executable, [sys.executable] + sys.argv)

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
