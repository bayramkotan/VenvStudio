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
    QProgressBar, QListWidget, QListWidgetItem, QTextEdit,
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

    def _c(self) -> dict:
        """Return current theme color palette with font hierarchy."""
        from src.gui.styles import get_colors
        return get_colors(
            self.config.get("theme", "dark"),
            self.config.get("font_secondary_size", 13) or self.config.get("font_size", 13),
            self.config.get("font_primary_size", 22),
            self.config.get("font_tertiary_size", 11),
        )

    def _table_style(self, font_size=13):
        c = self._c()
        return (
            f"QTableWidget {{ background-color: {c['card']}; color: {c['fg']}; "
            f"gridline-color: {c['border']}; font-size: {font_size}px; }}"
            f"QTableWidget::item:selected {{ background-color: {c['active']}; color: {c['fg']}; }}"
            f"QTableWidget QLineEdit {{ background-color: {c['input_bg']}; color: {c['fg']}; "
            f"border: 2px solid {c['accent']}; padding: 2px 4px; font-size: {font_size}px; }}"
            f"QComboBox {{ background-color: {c['input_bg']}; color: {c['fg']}; "
            f"border: 1px solid {c['border']}; padding: 3px; font-size: {self._c()['fs_small']}px; }}"
            f"QHeaderView::section {{ background-color: {c['sidebar']}; color: {c['fg_muted']}; "
            f"border: none; border-bottom: 1px solid {c['border']}; padding: 4px; }}"
        )

    def _log_style(self):
        c = self._c()
        return (
            f"QTextEdit {{ background: {c['sidebar']}; color: {c['fg']}; "
            f"border: 1px solid {c['border']}; border-radius: 6px; "
            f"font-family: 'Cascadia Code', 'JetBrains Mono', monospace; font-size: {self._c()['fs_small']}px; }}"
        )

    def _frame_style(self):
        c = self._c()
        return (
            f"QFrame {{ background: {c['card']}; border: 1px solid {c['border']}; "
            f"border-radius: 8px; padding: 12px; }}"
        )

    def _refresh_styles(self):
        """Re-apply theme-dependent inline styles on all tracked widgets."""
        try:
            from PySide6.QtWidgets import QFrame, QLabel, QCheckBox
            c = self._c()

            # 1) Tablolar
            tables = [
                ("builtin_cats_table", 12),
                ("custom_categories_list", 13),
                ("builtin_presets_table", 12),
                ("custom_presets_table", 13),
                ("custom_catalog_table", 13),
                ("custom_terminals_table", 13),
            ]
            for attr, size in tables:
                w = getattr(self, attr, None)
                if w:
                    w.setStyleSheet(self._table_style(size))

            # 2) CLI log alanı
            if hasattr(self, "cli_log"):
                self.cli_log.setStyleSheet(self._log_style())

            # 3) Kayıtlı CLI/pip kartları (_theme_frames)
            for frame in self._theme_frames:
                try:
                    frame.setStyleSheet(self._frame_style())
                    # Kart içindeki label'ları güncelle
                    for lbl in frame.findChildren(QLabel):
                        ss = lbl.styleSheet()
                        if "font-weight: bold" in ss:
                            lbl.setStyleSheet(f"font-weight: bold; font-size: {c['fs_base']}px; color: {c['fg']};")
                        elif "font-size:" in ss and "color:" in ss:
                            # status veya desc label — rengi koru ama fg_muted güncelle
                            if c['success'] in ss or c['danger'] in ss or "✅" in lbl.text() or "❌" in lbl.text():
                                pass  # status label, rengi değişmesin
                            else:
                                lbl.setStyleSheet(f"color: {c['fg_muted']}; font-size: {c['fs_tiny']}px;")
                    # Kart içindeki checkbox'ları güncelle
                    for cb in frame.findChildren(QCheckBox):
                        cb.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {c['fg']};")
                except RuntimeError:
                    pass  # widget deleted

            # 4) Fallback: objectName'siz QFrame'ler (eski kartlar)
            for frame in self.findChildren(QFrame):
                obj = frame.objectName()
                if obj and (obj.startswith("cli_card_") or obj.startswith("pip_card_")):
                    continue  # zaten yukarıda güncellendi
                ss = frame.styleSheet()
                if ss and "border-radius" in ss and "border" in ss:
                    frame.setStyleSheet(self._frame_style())
        except Exception:
            pass

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._theme_frames = []  # CLI/pip card frame attribute names
        self._setup_ui()
        self._load_current_settings()

    # ── Helper: ℹ️ info button ──────────────────────────────────────────────
    def _make_info_btn(self, tooltip: str):
        """Return a small ℹ️ QToolButton that shows a tooltip on hover/click."""
        from PySide6.QtWidgets import QToolButton
        from PySide6.QtCore import QSize
        btn = QToolButton()
        btn.setText("ℹ️")
        btn.setToolTip(tooltip)
        btn.setToolTipDuration(8000)
        btn.setFixedSize(QSize(26, 26))
        btn.setCursor(Qt.WhatsThisCursor)
        btn.setStyleSheet(
            f"QToolButton {{ border: none; background: transparent; "
            f"font-size: {self._c()['fs_small']}px; }}"
            f"QToolButton:hover {{ background: {self._c()['border']}; border-radius: 4px; }}"
        )
        # Also show a QMessageBox on click for accessibility
        btn.clicked.connect(lambda: __import__('PySide6.QtWidgets', fromlist=['QToolTip']).QToolTip.showText(
            btn.mapToGlobal(btn.rect().bottomLeft()), tooltip, btn, btn.rect(), 6000
        ))
        return btn

    def _make_section_reset_btn(self, label: str, callback):
        """Return a small 'Reset' QPushButton for a settings section."""
        btn = QPushButton(f"↩ {label}")
        btn.setObjectName("secondary")
        btn.setToolTip(f"Reset {label.lower()} to defaults")
        btn.clicked.connect(callback)
        return btn

    def _make_group_title_row(self, icon_title: str, tooltip: str, reset_label: str = None, reset_fn=None):
        """
        Returns (outer_widget, inner_layout) — a QWidget with a horizontal
        header row (icon+title | stretch | ℹ️ [Reset]) to place above a section.
        The outer_widget should be added to the scroll layout; then add the
        QGroupBox immediately after.
        """
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        title_lbl = QLabel(icon_title)
        title_lbl.setStyleSheet(
            f"font-size: {self._c()['fs_base']}px; font-weight: bold; color: {self._c()['fg']};"
        )
        row.addWidget(title_lbl)
        row.addStretch()

        info_btn = self._make_info_btn(tooltip)
        row.addWidget(info_btn)

        if reset_label and reset_fn:
            reset_btn = self._make_section_reset_btn(reset_label, reset_fn)
            row.addWidget(reset_btn)

        wrapper = QWidget()
        wrapper.setLayout(row)
        wrapper.setContentsMargins(0, 4, 0, 0)
        return wrapper

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
        layout.addWidget(self._make_group_title_row(
            f"🎨 {tr('appearance')}",
            "Control the visual look of VenvStudio: theme, fonts, and display scaling.\n"
            "• Theme: Switch between dark/light colour schemes\n"
            "• Fonts: Set separate sizes for headings, UI elements and detail labels\n"
            "• Changes take effect immediately (no restart needed)",
            "Reset Appearance", self._reset_appearance,
        ))
        appearance_group = QGroupBox()
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(12)

        # Theme — protected by checkbox
        theme_row = QHBoxLayout()
        self.theme_cb = QCheckBox()
        self.theme_cb.setChecked(False)
        self.theme_cb.toggled.connect(lambda on: self._on_theme_cb_toggled(on))
        theme_row.addWidget(self.theme_cb)
        self.theme_combo = NoScrollComboBox()
        from src.gui.styles import THEME_OPTIONS
        for theme_id, theme_label in THEME_OPTIONS:
            self.theme_combo.addItem(theme_label, theme_id)
        self.theme_combo.setEnabled(False)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_live_preview)
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addRow(f"{tr('theme')}", theme_row)

        # ── 3-Level Font System ──
        font_levels = [
            ("primary", "🔤 Headings", "Page titles, section headers, group labels", 22),
            ("secondary", "🔡 UI & Menus", "Buttons, menus, tables, inputs, normal text", 13),
            ("tertiary", "🔹 Details", "Info labels, hints, status text, tooltips", 11),
        ]
        for level_id, label, hint, default_size in font_levels:
            row = QHBoxLayout()
            row.setSpacing(6)

            cb = QCheckBox()
            cb.setChecked(False)
            row.addWidget(cb)

            font_combo = QFontComboBox()
            font_combo.setEnabled(False)
            font_combo.setFocusPolicy(Qt.StrongFocus)
            cb.toggled.connect(font_combo.setEnabled)
            row.addWidget(font_combo, 1)

            size_spin = QSpinBox()
            size_spin.setRange(8, 48)
            size_spin.setValue(default_size)
            size_spin.setSuffix(" px")
            size_spin.setEnabled(False)
            size_spin.setMinimumWidth(80)
            cb.toggled.connect(size_spin.setEnabled)
            row.addWidget(size_spin)

            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic;")
            hint_lbl.setMinimumWidth(200)
            row.addWidget(hint_lbl)

            # Store references
            setattr(self, f"font_{level_id}_cb", cb)
            setattr(self, f"font_{level_id}_combo", font_combo)
            setattr(self, f"font_{level_id}_size", size_spin)

            appearance_layout.addRow(label, row)

        # Reset Fonts button
        reset_font_row = QHBoxLayout()
        reset_font_btn = QPushButton("↩️ Reset Fonts to Default")
        reset_font_btn.setObjectName("secondary")
        reset_font_btn.setToolTip("Reset all font settings to system defaults")
        reset_font_btn.clicked.connect(self._reset_fonts)
        reset_font_row.addWidget(reset_font_btn)
        reset_font_row.addStretch()
        appearance_layout.addRow("", reset_font_row)

        # UI Scale info
        scale_label = QLabel("UI scaling follows your system display settings.")
        scale_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        appearance_layout.addRow("", scale_label)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # ── 2. LANGUAGE ──
        layout.addWidget(self._make_group_title_row(
            f"🌍 {tr('language')}",
            "Change the interface language of VenvStudio.\n"
            "• Enable the checkbox to unlock the language selector\n"
            "• 11 languages supported: EN, TR, DE, FR, ES, PT, RU, ZH, JA, KO, AR\n"
            "• The application will restart automatically after saving",
            "Reset Language", self._reset_language,
        ))
        lang_group = QGroupBox()
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
        lang_note.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        lang_layout.addRow("", lang_note)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # ── 3. PYTHON VERSIONS ──
        layout.addWidget(self._make_group_title_row(
            f"🐍 {tr('python_versions')}",
            "Manage Python installations used for creating virtual environments.\n"
            "• Scan: Auto-detect all Python versions on your system\n"
            "• Add Custom Path: Register a Python executable not found by scan\n"
            "• Download Python: Fetch a standalone Python from python-build-standalone\n"
            "• Set as default: The selected Python is used when creating new environments\n"
            "• Verify pip & venv: Check modules are present and functional",
        ))
        python_group = QGroupBox()
        python_layout = QVBoxLayout()
        python_layout.setSpacing(12)

        python_info = QLabel(tr("python_info"))
        python_info.setWordWrap(True)
        python_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        python_layout.addWidget(python_info)

        # Python versions table
        self.python_table = QTableWidget()
        self.python_table.setColumnCount(3)
        self.python_table.setHorizontalHeaderLabels(["Version", "Path", "Source"])
        self.python_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.python_table.setColumnWidth(0, 100)
        self.python_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.python_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.python_table.setColumnWidth(2, 130)
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

        download_py_btn = QPushButton("⬇️ Download Python")
        download_py_btn.setObjectName("secondary")
        download_py_btn.setToolTip("Download standalone Python from python-build-standalone")
        download_py_btn.clicked.connect(self._download_python)
        py_btn_layout.addWidget(download_py_btn)

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

        verify_btn = QPushButton("🔍 Verify pip & venv")
        verify_btn.setObjectName("secondary")
        verify_btn.setToolTip("Check if pip and venv are installed and working for selected Python")
        verify_btn.clicked.connect(self._verify_pip_venv)
        py_btn_layout.addWidget(verify_btn)

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
        layout.addWidget(self._make_group_title_row(
            f"📂 {tr('paths')}",
            "Configure where VenvStudio stores virtual environments.\n"
            "• Environment Directory: All new venvs are created inside this folder\n"
            "• Browse: Pick any folder on your system\n"
            "• Reset: Restore the default location (~/.venvstudio/envs)",
        ))
        paths_group = QGroupBox()
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
        path_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        paths_layout.addRow("", path_info)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        # ── 5. PACKAGE MANAGER & ENVIRONMENT DEFAULTS ──
        layout.addWidget(self._make_group_title_row(
            "📦 Package Manager & Defaults",
            "Configure the default environment type and package backend.\n"
            "• Default env type: Pre-selects the environment type when creating new environments\n"
            "• pip backend: Override pip with uv for faster installs (applies to venv type)\n"
            "• uv is auto-installed if not present on your system",
        ))
        pkg_mgr_group = QGroupBox()
        pkg_mgr_layout = QFormLayout()
        pkg_mgr_layout.setSpacing(12)

        # Default Environment Type
        default_env_type_row = QHBoxLayout()
        self.default_env_type_cb = QCheckBox()
        self.default_env_type_cb.setChecked(False)
        self.default_env_type_cb.toggled.connect(lambda on: self.default_env_type_combo.setEnabled(on))
        default_env_type_row.addWidget(self.default_env_type_cb)

        self.default_env_type_combo = NoScrollComboBox()
        self.default_env_type_combo.addItem("🐍 Python venv (default)", "venv")
        self.default_env_type_combo.addItem("⚡ uv (fast, Rust-powered)", "uv")
        self.default_env_type_combo.addItem("📜 Poetry (lock file)", "poetry")
        self.default_env_type_combo.addItem("📦 pipx (CLI apps)", "pipx")
        self.default_env_type_combo.addItem("🦎 Conda (micromamba)", "conda")
        self.default_env_type_combo.setEnabled(False)
        default_env_type_row.addWidget(self.default_env_type_combo, 1)
        pkg_mgr_layout.addRow("Default Env Type:", default_env_type_row)

        env_type_note = QLabel(
            "This pre-selects the environment type in the 'New Environment' dialog.\n"
            "You can always change it when creating a new environment."
        )
        env_type_note.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        env_type_note.setWordWrap(True)
        pkg_mgr_layout.addRow("", env_type_note)

        # pip/uv backend override (for venv type)
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
        pkg_mgr_layout.addRow("pip Backend:", pkg_mgr_row)

        # uv auto-install info
        uv_note = QLabel(
            "Override pip with uv for venv environments (10-100× faster).\n"
            "Note: uv environments always use uv regardless of this setting."
        )
        uv_note.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        uv_note.setWordWrap(True)
        pkg_mgr_layout.addRow("", uv_note)

        pkg_mgr_group.setLayout(pkg_mgr_layout)
        layout.addWidget(pkg_mgr_group)

        # ── 5b. TOOLCHAIN MANAGER ──────────────────────────────────────────
        if not hasattr(self, "_tc_built"):
            self._tc_built = True
            self._build_toolchain_ui(layout)

        # ── 6. GENERAL ──
        layout.addWidget(self._make_group_title_row(
            f"⚙️ {tr('general')}",
            "Miscellaneous behaviour settings for VenvStudio.\n"
            "• Auto-upgrade pip: Runs pip install --upgrade pip after each env is created\n"
            "• Confirm delete: Shows a dialog before permanently removing an environment\n"
            "• Show hidden packages: Includes pip/setuptools/wheel in the package list\n"
            "• Check updates: Polls PyPI for a new VenvStudio release on startup\n"
            "• Remember window: Saves and restores window size/position between sessions\n"
            "• Default terminal: Terminal app used by Open Terminal buttons",
            "Reset General", self._reset_general,
        ))
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

        # ── CUSTOM TERMINALS ──
        custom_term_group = QGroupBox("🖥️ Custom Terminals")
        custom_term_layout = QVBoxLayout()
        custom_term_layout.setSpacing(8)

        info_lbl = QLabel("Add custom terminal commands. Use {path} for env path and {activate} for activate script.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        custom_term_layout.addWidget(info_lbl)

        # Table
        self.custom_term_table = QTableWidget(0, 3)
        self.custom_term_table.setHorizontalHeaderLabels(["Name", "Command", "Enabled"])
        self.custom_term_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.custom_term_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_term_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.custom_term_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_term_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.custom_term_table.setMaximumHeight(180)
        custom_term_layout.addWidget(self.custom_term_table)

        # Buttons
        btn_row = QHBoxLayout()
        add_term_btn = QPushButton("➕ Add")
        add_term_btn.setObjectName("secondary")
        add_term_btn.clicked.connect(self._add_custom_terminal)
        edit_term_btn = QPushButton("✏️ Edit")
        edit_term_btn.setObjectName("secondary")
        edit_term_btn.clicked.connect(self._edit_custom_terminal)
        del_term_btn = QPushButton("🗑️ Remove")
        del_term_btn.setObjectName("danger")
        del_term_btn.clicked.connect(self._remove_custom_terminal)
        btn_row.addWidget(add_term_btn)
        btn_row.addWidget(edit_term_btn)
        btn_row.addWidget(del_term_btn)
        btn_row.addStretch()
        custom_term_layout.addLayout(btn_row)

        custom_term_group.setLayout(custom_term_layout)
        layout.addWidget(custom_term_group)

        # ── 6. VS CODE INTEGRATION ──
        vscode_group = QGroupBox("💻 VS Code Integration")
        vscode_layout = QVBoxLayout()
        vscode_layout.setSpacing(10)

        vscode_info = QLabel("Set the selected environment's Python as VS Code interpreter.")
        vscode_info.setWordWrap(True)
        vscode_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
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
        self.builtin_cats_table.setStyleSheet(self._table_style(12))
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
        self.builtin_cats_table.setStyleSheet(self._table_style(12))
        self.builtin_cats_table.setStyleSheet(self._table_style(12))
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
        cat_mgr_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        cat_mgr_layout.addWidget(cat_mgr_info)

        self.custom_categories_list = QTableWidget()
        self.custom_categories_list.setStyleSheet(self._table_style(13))
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
        self.custom_categories_list.setStyleSheet(self._table_style(13))
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

        # ── PRESET MANAGER ──
        preset_group = QGroupBox("⚡ Preset Manager")
        preset_layout = QVBoxLayout()
        preset_layout.setSpacing(8)

        preset_info = QLabel("Add, edit or remove package presets. Built-in presets are shown read-only. Custom presets appear in the Packages → Presets tab.")
        preset_info.setWordWrap(True)
        preset_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        preset_layout.addWidget(preset_info)

        # Built-in presets (read-only)
        self.show_builtin_presets_cb = QCheckBox("Show built-in presets (read-only)")
        self.show_builtin_presets_cb.setChecked(False)
        self.show_builtin_presets_cb.toggled.connect(self._toggle_builtin_presets)
        preset_layout.addWidget(self.show_builtin_presets_cb)

        self.builtin_presets_table = QTableWidget(0, 2)
        self.builtin_presets_table.setHorizontalHeaderLabels(["Preset Name", "Packages"])
        self.builtin_presets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.builtin_presets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.builtin_presets_table.setMaximumHeight(150)
        self.builtin_presets_table.verticalHeader().setVisible(False)
        self.builtin_presets_table.verticalHeader().setDefaultSectionSize(26)
        self.builtin_presets_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.builtin_presets_table.setVisible(False)
        self.builtin_presets_table.setStyleSheet(self._table_style(12))
        from src.utils.constants import PRESETS
        self.builtin_presets_table.setRowCount(len(PRESETS))
        for i, (name, pkgs) in enumerate(PRESETS.items()):
            self.builtin_presets_table.setItem(i, 0, QTableWidgetItem(name))
            self.builtin_presets_table.setItem(i, 1, QTableWidgetItem(", ".join(pkgs)))
        preset_layout.addWidget(self.builtin_presets_table)

        # Custom presets table
        custom_preset_lbl = QLabel("Custom Presets:")
        custom_preset_lbl.setStyleSheet(f"color: {self._c()['fg']}; font-size: {self._c()['fs_small']}px; font-weight: bold;")
        preset_layout.addWidget(custom_preset_lbl)

        self.custom_presets_table = QTableWidget(0, 2)
        self.custom_presets_table.setHorizontalHeaderLabels(["Preset Name", "Packages (comma separated)"])
        self.custom_presets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.custom_presets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_presets_table.setMaximumHeight(160)
        self.custom_presets_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_presets_table.setSelectionMode(QTableWidget.SingleSelection)
        self.custom_presets_table.verticalHeader().setVisible(False)
        self.custom_presets_table.verticalHeader().setDefaultSectionSize(28)
        self.custom_presets_table.setStyleSheet(self._table_style(13))
        preset_layout.addWidget(self.custom_presets_table)

        preset_btn_row = QHBoxLayout()
        add_preset_btn = QPushButton("➕ Add Preset")
        add_preset_btn.setObjectName("secondary")
        add_preset_btn.clicked.connect(self._add_custom_preset)
        edit_preset_btn = QPushButton("✏️ Edit")
        edit_preset_btn.setObjectName("secondary")
        edit_preset_btn.clicked.connect(self._edit_custom_preset)
        del_preset_btn = QPushButton("🗑️ Remove")
        del_preset_btn.setObjectName("danger")
        del_preset_btn.clicked.connect(self._remove_custom_preset)
        preset_btn_row.addWidget(add_preset_btn)
        preset_btn_row.addWidget(edit_preset_btn)
        preset_btn_row.addWidget(del_preset_btn)
        preset_btn_row.addStretch()
        preset_layout.addLayout(preset_btn_row)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # ── 8. CUSTOM CATALOG PACKAGES ──
        catalog_group = QGroupBox("📚 Custom Catalog Packages")
        catalog_layout = QVBoxLayout()
        catalog_layout.setSpacing(10)

        catalog_info = QLabel("Add custom packages. Category column uses a dropdown from built-in + custom categories.")
        catalog_info.setWordWrap(True)
        catalog_info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        catalog_layout.addWidget(catalog_info)

        self.custom_catalog_table = QTableWidget()
        self.custom_catalog_table.setStyleSheet(self._table_style(13))
        self.custom_catalog_table.setColumnCount(3)
        self.custom_catalog_table.setHorizontalHeaderLabels(["Package Name", "Description", "Category"])
        self.custom_catalog_table.setStyleSheet(self._table_style(13))
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

        # ── CLI/TUI TOOLS ──
        cli_group = QGroupBox("🖥️ CLI/TUI Tools")
        cli_layout = QVBoxLayout()
        cli_layout.setSpacing(12)

        cli_desc = QLabel(
            "Enhance your terminal experience with modern CLI/TUI tools. "
            "Starship & Oh My Posh require a Nerd Font for proper rendering."
        )
        cli_desc.setWordWrap(True)
        cli_desc.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        cli_layout.addWidget(cli_desc)

        # Output log for CLI tools
        self.cli_log = QTextEdit()
        self.cli_log.setStyleSheet(self._log_style())
        self.cli_log.setReadOnly(True)
        self.cli_log.setMaximumHeight(100)
        self.cli_log.setStyleSheet(self._log_style())
        self.cli_log.setPlaceholderText("Installation output will appear here...")
        cli_layout.addWidget(self.cli_log)

        # ── Nerd Fonts ──
        font_group = QGroupBox("🖋️ Nerd Fonts")
        font_inner = QHBoxLayout()
        font_inner.setSpacing(8)

        from src.core.cli_tools_manager import NERD_FONTS
        self.nerd_font_cb = QCheckBox("Font:")
        self.nerd_font_cb.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg']};")
        font_inner.addWidget(self.nerd_font_cb)

        self.nerd_font_combo = QComboBox()
        for font_id, font_name in NERD_FONTS:
            self.nerd_font_combo.addItem(font_name, font_id)
        self.nerd_font_combo.setEnabled(False)
        self.nerd_font_cb.toggled.connect(self.nerd_font_combo.setEnabled)
        font_inner.addWidget(self.nerd_font_combo, 1)

        install_font_btn = QPushButton("⬇️ Download & Install Font")
        install_font_btn.setObjectName("secondary")
        install_font_btn.clicked.connect(self._install_nerd_font)
        font_inner.addWidget(install_font_btn)
        font_group.setLayout(font_inner)
        cli_layout.addWidget(font_group)

        # ── Tool cards ──
        from src.core.cli_tools_manager import (
            STARSHIP_PRESETS, STARSHIP_PRESET_NAMES, OMP_THEMES, PIP_TOOLS, is_tool_installed
        )

        # Starship
        cli_layout.addWidget(self._make_cli_card(
            "starship", "🚀 Starship",
            "The minimal, blazing-fast, and infinitely customizable prompt for any shell",
            "Preset:", STARSHIP_PRESET_NAMES, "preset",
            preset_descriptions=STARSHIP_PRESETS
        ))

        # Oh My Posh
        cli_layout.addWidget(self._make_cli_card(
            "oh-my-posh", "🎨 Oh My Posh",
            "A prompt theme engine for any shell",
            "Theme:", OMP_THEMES, "theme"
        ))

        # Rich
        cli_layout.addWidget(self._make_pip_card(
            "rich", "✨ Rich",
            "Rich text and beautiful formatting in the terminal",
        ))

        # Textual
        cli_layout.addWidget(self._make_pip_card(
            "textual", "🖼️ Textual",
            "Rapid framework for terminal-based user interfaces (TUI)",
        ))

        # Prompt Toolkit
        cli_layout.addWidget(self._make_pip_card(
            "prompt_toolkit", "⌨️ Prompt Toolkit",
            "Library for building interactive CLI applications",
        ))

        cli_group.setLayout(cli_layout)
        layout.addWidget(cli_group)

        layout.addStretch()

        # ── LAUNCH SETTINGS ──
        launch_group = QGroupBox("🚀 Launch Settings")
        launch_layout = QFormLayout()
        launch_layout.setSpacing(12)

        # Jupyter Working Directory — protected by checkbox
        jupyter_dir_row = QHBoxLayout()
        self.jupyter_workdir_cb = QCheckBox()
        self.jupyter_workdir_cb.setChecked(False)
        self.jupyter_workdir_cb.toggled.connect(lambda on: self.jupyter_workdir_combo.setEnabled(on))
        jupyter_dir_row.addWidget(self.jupyter_workdir_cb)

        self.jupyter_workdir_combo = NoScrollComboBox()
        self.jupyter_workdir_combo.addItem("🏠 Home Directory", "home")
        self.jupyter_workdir_combo.addItem("📁 Environment Folder", "env")
        self.jupyter_workdir_combo.addItem("📂 Custom Path...", "custom")
        self.jupyter_workdir_combo.setEnabled(False)
        self.jupyter_workdir_combo.currentIndexChanged.connect(self._on_jupyter_workdir_changed)
        jupyter_dir_row.addWidget(self.jupyter_workdir_combo, 1)

        self.jupyter_custom_path_btn = QPushButton("📂")
        self.jupyter_custom_path_btn.setFixedWidth(36)
        self.jupyter_custom_path_btn.setToolTip("Pick custom folder")
        self.jupyter_custom_path_btn.setEnabled(False)
        self.jupyter_custom_path_btn.clicked.connect(self._pick_jupyter_workdir)
        jupyter_dir_row.addWidget(self.jupyter_custom_path_btn)

        launch_layout.addRow("Jupyter Working Dir:", jupyter_dir_row)

        self.jupyter_custom_path_label = QLabel("")
        self.jupyter_custom_path_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self.jupyter_custom_path_label.setVisible(False)
        launch_layout.addRow("", self.jupyter_custom_path_label)

        launch_group.setLayout(launch_layout)
        layout.addWidget(launch_group)



        # ── ABOUT (always at bottom) ──
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

        update_row = QHBoxLayout()
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet(f"font-size: {self._c()['fs_small']}px;")
        update_row.addWidget(self.update_status_label, 1)

        check_update_btn = QPushButton("🔄 Check for Updates")
        check_update_btn.setObjectName("secondary")
        check_update_btn.clicked.connect(self._check_for_updates)
        update_row.addWidget(check_update_btn)

        about_layout.addLayout(update_row)
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── SAVE / RESET BUTTONS (scroll dışında, üstte sabit) ──
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(12, 6, 12, 6)

        save_btn = QPushButton(f"  💾 {tr('save_settings')}  ")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()

        reset_all_btn = QPushButton(tr("reset_defaults"))
        reset_all_btn.setObjectName("danger")
        reset_all_btn.clicked.connect(self._reset_all)
        btn_layout.addWidget(reset_all_btn)

        main_layout.addLayout(btn_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {self._c()['border']}; max-height: 1px;")
        main_layout.addWidget(sep)

        main_layout.addWidget(scroll)

    # ── CLI/TUI Tools helpers ─────────────────────────────────────────────────

    def _reset_fonts(self):
        """Reset all font settings to system defaults."""
        _defaults = {"primary": 22, "secondary": 13, "tertiary": 11}
        for level_id, def_size in _defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            cb.setChecked(False)
            combo.setEnabled(False)
            combo.setCurrentFont(QFont("Segoe UI"))
            spin.setEnabled(False)
            spin.setValue(def_size)
            self.config.set(f"font_{level_id}_family", "")
            self.config.set(f"font_{level_id}_size", def_size)
        self.config.set("font_family", "")
        self.config.set("font_size", 13)
        self.font_changed.emit("Segoe UI", 13)



    def _on_theme_cb_toggled(self, on):
        """Enable/disable theme combo and apply theme live."""
        self.theme_combo.setEnabled(on)
        if on:
            self._on_theme_live_preview()
        else:
            # Checkbox unchecked → revert to dark
            self.config.set("theme", "dark")
            self.theme_changed.emit("dark")

    def _on_theme_live_preview(self, _idx=None):
        """Apply theme instantly when dropdown changes — no Save needed."""
        if not self.theme_cb.isChecked():
            return
        theme = self.theme_combo.currentData()
        if theme:
            self.config.set("theme", theme)
            self.theme_changed.emit(theme)
            self._refresh_styles()

    def _cli_log_append(self, text: str):
        import html as _html
        c = self._c()
        for line in text.split("\n"):
            t = line.strip()
            if not t:
                continue
            escaped = _html.escape(t)
            if t.startswith("✅"):
                color = c['success']
            elif t.startswith("❌"):
                color = c['danger']
            elif t.startswith("⬇️") or t.startswith("📦"):
                color = c['accent']
            elif t.startswith("⚠️"):
                color = c.get('warning', '#f9e2af')
            else:
                color = c['fg']
            self.cli_log.append(f'<span style="color:{color};">{escaped}</span>')

    def _make_cli_card(self, tool_id, title, desc, preset_label, presets, preset_key,
                        preset_descriptions=None):
        """Create a card widget for binary CLI tools (starship, oh-my-posh)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"cli_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Title + status
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"\u2705 {version}" if installed else "\u274c Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        status_lbl.setObjectName(f"status_{tool_id.replace('-','_')}")
        header.addWidget(status_lbl)
        header.addStretch()
        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Preset selector + buttons
        controls = QHBoxLayout()
        controls.setSpacing(6)

        cb_key = f"cb_preset_{tool_id.replace('-','_')}"
        preset_cb = QCheckBox(preset_label)
        preset_cb.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg']};")
        preset_cb.setObjectName(cb_key)
        controls.addWidget(preset_cb)

        combo = QComboBox()
        combo.setMaximumWidth(200)
        for p in presets:
            label = p
            if preset_descriptions and p in preset_descriptions:
                label = f"{p}  \u2014  {preset_descriptions[p]}"
            combo.addItem(label, p)
        combo.setObjectName(f"preset_{tool_id.replace('-','_')}")
        combo.setEnabled(False)
        preset_cb.toggled.connect(combo.setEnabled)
        controls.addWidget(combo)

        # Preset description label (updates on selection)
        desc_hint = None
        if preset_descriptions:
            desc_hint = QLabel("")
            desc_hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic;")
            desc_hint.setFixedHeight(16)

            def _update_preset_hint(idx, _dh=desc_hint, _c=combo, _pd=preset_descriptions):
                key = _c.itemData(idx)
                if key and key in _pd:
                    _dh.setText(_pd[key])
                else:
                    _dh.setText("")

            combo.currentIndexChanged.connect(_update_preset_hint)
            _update_preset_hint(0)

        controls.addStretch()

        install_btn = QPushButton("\u2b07\ufe0f Install" if not installed else "\U0001f504 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        controls.addWidget(install_btn)

        if installed:
            cfg_btn = QPushButton("\u2699\ufe0f Configure Shell")
            cfg_btn.setObjectName("secondary")
            cfg_btn
            cfg_btn.clicked.connect(lambda _, t=tool_id, c=combo, pk=preset_key: self._cli_configure(t, c, pk))
            controls.addWidget(cfg_btn)

            # Starship-specific: Edit Config + Test buttons
            if tool_id == "starship":
                edit_btn = QPushButton("\U0001f4dd Edit Config")
                edit_btn.setObjectName("secondary")
                edit_btn
                edit_btn.setToolTip("Open starship.toml inline editor")
                edit_btn.clicked.connect(self._open_starship_editor)
                controls.addWidget(edit_btn)

                test_btn = QPushButton("\u25b6\ufe0f Test")
                test_btn.setObjectName("secondary")
                test_btn
                test_btn.setToolTip("Open a terminal to test your Starship prompt")
                test_btn.clicked.connect(self._test_starship_in_terminal)
                controls.addWidget(test_btn)

            uninst_btn = QPushButton("\U0001f5d1\ufe0f Uninstall")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            controls.addWidget(uninst_btn)

        layout.addLayout(controls)

        # Preset description below controls
        if desc_hint:
            layout.addWidget(desc_hint)

        return card

    def _make_pip_card(self, tool_id, title, desc):
        """Create a card widget for pip-based tools (rich, textual, prompt_toolkit)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"pip_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        header.addWidget(status_lbl)
        header.addStretch()

        install_btn = QPushButton("⬇️ Install" if not installed else "🔄 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        header.addWidget(install_btn)

        if installed:
            uninst_btn = QPushButton("🗑️")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.setMinimumWidth(32)
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            header.addWidget(uninst_btn)

        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(desc_lbl)
        return card

    def _cli_install(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        btn.setEnabled(False)
        btn.setText("⏳ Installing...")
        self.cli_log.clear()
        self._cli_worker = CliToolWorker("install", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_uninstall(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        reply = QMessageBox.question(self, "Uninstall", f"Uninstall {tool_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._cli_worker = CliToolWorker("uninstall", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_configure(self, tool_id, combo, preset_key):
        from src.core.cli_tools_manager import CliToolWorker
        theme = combo.currentData() or combo.currentText()
        self._cli_worker = CliToolWorker("configure", tool_id, {preset_key: theme}, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()


    def _open_starship_editor(self):
        """Open inline editor for starship.toml."""
        from src.core.cli_tools_manager import read_starship_toml, write_starship_toml, get_starship_toml_path
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel, QMessageBox
        from PySide6.QtGui import QFont

        dlg = QDialog(self)
        dlg.setWindowTitle("📝 Starship Config Editor — starship.toml")
        dlg.resize(700, 500)
        dlg.setStyleSheet(
            f"QDialog {{ background: {self._c()['bg']}; }}"
            f"QPlainTextEdit {{ background: {self._c()['sidebar']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"border-radius: 4px; font-family: 'Consolas', 'JetBrains Mono', monospace; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton {{ padding: 6px 16px; border-radius: 4px; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton#save {{ background: {self._c()['success']}; color: {self._c()['accent_fg']}; font-weight: bold; }}"
            "QPushButton#save:hover { background: #94d89d; }"
            f"QPushButton#secondary {{ background: {self._c()['secondary']}; color: {self._c()['fg']}; }}"
            "QPushButton#secondary:hover { background: #45475a; }"
            f"QLabel {{ color: #6c7086; font-size: {self._c()['fs_tiny']}px; }}"
        )

        layout = QVBoxLayout(dlg)

        path_label = QLabel(f"📂 {get_starship_toml_path()}")
        layout.addWidget(path_label)

        editor = QPlainTextEdit()
        editor.setFont(QFont("Consolas", 12))
        editor.setPlainText(read_starship_toml())
        editor.setTabStopDistance(28)
        layout.addWidget(editor)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.setObjectName("secondary")
        reload_btn.clicked.connect(lambda: editor.setPlainText(read_starship_toml()))
        btn_row.addWidget(reload_btn)

        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setObjectName("secondary")
        open_folder_btn.clicked.connect(lambda: __import__("subprocess").Popen(
            ["explorer" if __import__("sys").platform == "win32" else "xdg-open",
             str(get_starship_toml_path().parent)]
        ))
        btn_row.addWidget(open_folder_btn)

        save_btn = QPushButton("💾 Save")
        save_btn.setObjectName("save")
        def _do_save():
            if write_starship_toml(editor.toPlainText()):
                self._cli_log_append("✅ starship.toml saved")
                QMessageBox.information(dlg, "Saved", "starship.toml saved successfully! ✅\n\nOpen a new terminal to see changes.")
            else:
                QMessageBox.critical(dlg, "Error", "Failed to save starship.toml")
        save_btn.clicked.connect(_do_save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        dlg.exec()

    def _test_starship_in_terminal(self):
        """Open a terminal so user can see their Starship prompt in action."""
        import sys as _sys
        from src.core.cli_tools_manager import is_tool_installed
        if not is_tool_installed("starship"):
            QMessageBox.warning(self, "Starship", "Starship is not installed.")
            return
        try:
            if _sys.platform == "win32":
                import subprocess
                # Open PowerShell with starship init
                subprocess.Popen(
                    ["powershell", "-NoExit", "-Command",
                     "Invoke-Expression (&starship init powershell)"],
                    creationflags=0x00000010  # CREATE_NEW_CONSOLE
                )
            elif _sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal"])
            else:
                import subprocess
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    import shutil
                    if shutil.which(term):
                        subprocess.Popen([term])
                        break
            self._cli_log_append("✅ Terminal opened — check your Starship prompt!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open terminal:\n{e}")

    def _cli_done(self, ok, msg, btn, status_lbl, tool_id):
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        self._cli_log_append(msg)
        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl.setText(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        btn.setEnabled(True)
        btn.setText("🔄 Reinstall" if installed else "⬇️ Install")

    def _install_nerd_font(self):
        from src.core.cli_tools_manager import CliToolWorker
        if not self.nerd_font_cb.isChecked():
            QMessageBox.information(self, "Info", "Enable the Font checkbox first to select a font.")
            return
        font_id   = self.nerd_font_combo.currentData()
        font_name = self.nerd_font_combo.currentText()
        self.cli_log.clear()
        self._cli_worker = CliToolWorker(
            "install_font", "font",
            {"font_id": font_id, "font_name": font_name},
            parent=self
        )
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()

    def _verify_pip_venv(self):
        """Check pip and venv for selected Python, offer to fix if missing."""
        import os, subprocess
        from src.utils.platform_utils import subprocess_args as sp_args, get_platform

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()
        is_windows = get_platform() == "windows"
        scripts_dir = os.path.join(os.path.dirname(python_path), "Scripts" if is_windows else "bin")


        # ── pip check ──
        pip_version_str = ""
        pip_runnable = False
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "--version"],
                **sp_args(capture_output=True, text=True, timeout=10)
            )
            if result.returncode == 0:
                pip_runnable = True
                pip_version_str = result.stdout.strip()
        except Exception:
            pass

        # ── venv check ──
        venv_available = False
        try:
            result = subprocess.run(
                [python_path, "-c", "import venv; print(venv.__name__)"],
                **sp_args(capture_output=True, text=True, timeout=10)
            )
            if result.returncode == 0 and "venv" in result.stdout:
                venv_available = True
        except Exception:
            pass

        current_path = os.environ.get("PATH", "")
        scripts_in_path = scripts_dir.lower() in current_path.lower()

        pip_status = "✅ Working" if pip_runnable else "❌ Not working"
        venv_status = "✅ Available" if venv_available else "❌ Not available"
        path_status = "✅ Yes" if scripts_in_path else "⚠️ Not in current session"

        msg = (
            f"Python: {version}\n"
            f"Path:   {python_path}\n\n"
            f"pip:              {pip_status}\n"
            f"venv:            {venv_status}\n"
            f"Scripts in PATH: {path_status}"
        )
        if pip_runnable and pip_version_str:
            msg += "\n\n" + pip_version_str

        issues = []
        if not pip_runnable:
            issues.append("pip is not working — python -m pip failed.")
        if not venv_available:
            if is_windows:
                issues.append("venv module not available — try reinstalling Python with 'pip' option enabled.")
            else:
                issues.append("venv module not available — install python3-venv:\n"
                              "    Debian/Ubuntu: sudo apt install python3-venv\n"
                              "    Arch: included in python package")
        if not scripts_in_path:
            issues.append("Scripts folder not in current PATH — open a new terminal after Set Default.")

        if issues:
            msg += "\n\nIssues found:\n" + "\n".join("  * " + i for i in issues)
            fix_actions = []
            if not pip_runnable:
                fix_actions.append("reinstall pip")
            if not venv_available and not is_windows:
                fix_actions.append("install python3-venv (requires sudo)")

            if fix_actions:
                msg += "\n\nWould you like to fix now? (" + ", ".join(fix_actions) + ")"
                reply = QMessageBox.question(self, "pip & venv Status", msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if not pip_runnable:
                        self._fix_pip(python_path, version)
                    if not venv_available and not is_windows:
                        self._fix_venv()
            else:
                QMessageBox.warning(self, "pip & venv Status", msg)
        else:
            QMessageBox.information(self, "✅ pip & venv OK", msg)

    def _fix_venv(self):
        """Attempt to install python3-venv on Linux."""
        import subprocess, shutil
        if shutil.which("apt"):
            cmd = "sudo apt install -y python3-venv"
        elif shutil.which("pacman"):
            QMessageBox.information(self, "venv", "On Arch, venv is included in the python package.\nTry: sudo pacman -S python")
            return
        elif shutil.which("dnf"):
            cmd = "sudo dnf install -y python3-venv"
        else:
            QMessageBox.information(self, "venv", "Please install python3-venv using your package manager.")
            return
        try:
            subprocess.Popen(["sh", "-c", f"x-terminal-emulator -e '{cmd}' || xterm -e '{cmd}'"])
        except Exception as e:
            QMessageBox.warning(self, "venv Install", f"Could not start terminal:\n{e}\n\nRun manually: {cmd}")

    def _fix_pip(self, python_path, version):
        """Reinstall pip for the given Python executable."""
        import subprocess
        from src.utils.platform_utils import subprocess_args as sp_args

        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pip"],
                **sp_args(capture_output=True, text=True, timeout=60)
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "pip Fixed",
                    "pip reinstalled for Python " + version + "!\n\n"
                    "Open a new terminal and run: pip --version"
                )
            else:
                err = result.stderr.strip() or result.stdout.strip()
                QMessageBox.critical(
                    self, "pip Fix Failed",
                    "Could not reinstall pip.\n\n" + err + "\n\n"
                    "Try manually (as admin):\n"
                    '  "' + python_path + '" -m pip install --upgrade --force-reinstall pip'
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to run pip fix:\n" + str(e))
        self._scan_pythons()

    def _set_python_default_unix(self, version, python_path, scope):
        """Set default Python on Linux/macOS using update-alternatives or symlinks."""
        import subprocess, shutil

        platform = get_platform()
        ver_short = ".".join(version.split(".")[:2])  # e.g. "3.12"
        ver_nodot = ver_short.replace(".", "")          # e.g. "312"

        if platform == "linux":
            # Use update-alternatives if available
            if shutil.which("update-alternatives"):
                priority = 100

                reply = QMessageBox.question(
                    self, f"Set Default Python",
                    f"Register Python {version} as system default?\n\n"
                    f"  python3   → {python_path}\n"
                    f"  python3.{ver_short.split('.')[-1]} → {python_path}\n\n"
                    f"Uses update-alternatives (requires admin password).",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                cmds = [
                    ["update-alternatives", "--install",
                     "/usr/bin/python3", "python3", python_path, str(priority)],
                    ["update-alternatives", "--install",
                     "/usr/bin/python", "python", python_path, str(priority)],
                    ["update-alternatives", "--set", "python3", python_path],
                    ["update-alternatives", "--set", "python", python_path],
                ]

                success = True
                for cmd in cmds:
                    for sudo in [["pkexec"], ["sudo"]]:
                        try:
                            r = subprocess.run(
                                sudo + cmd,
                                capture_output=True, text=True, timeout=30
                            )
                            if r.returncode == 0:
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    else:
                        success = False
                        break

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Python {version} set as system default!\n\n"
                        f"Verify with:  python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not set default Python.\n\n"
                        f"Try manually:\n"
                        f"  sudo update-alternatives --install /usr/bin/python3 python3 {python_path} 100\n"
                        f"  sudo update-alternatives --set python3 {python_path}"
                    )
            else:
                # No update-alternatives — create symlink in /usr/local/bin
                reply = QMessageBox.question(
                    self, "Set Default Python",
                    f"Create symlinks for Python {version}?\n\n"
                    f"  /usr/local/bin/python3  → {python_path}\n"
                    f"  /usr/local/bin/python   → {python_path}\n\n"
                    f"Requires admin password.",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                script = (
                    f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                    f"ln -sf '{python_path}' /usr/local/bin/python"
                )
                success = False
                for sudo in [["pkexec", "bash", "-c"], ["sudo", "bash", "-c"]]:
                    try:
                        r = subprocess.run(sudo + [script], capture_output=True, text=True, timeout=30)
                        if r.returncode == 0:
                            success = True
                            break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not create symlinks.\n\nTry manually:\n"
                        f"  sudo ln -sf {python_path} /usr/local/bin/python3"
                    )

        elif platform == "macos":
            # macOS: symlink in /usr/local/bin
            reply = QMessageBox.question(
                self, "Set Default Python",
                f"Create symlinks for Python {version}?\n\n"
                f"  /usr/local/bin/python3  → {python_path}\n"
                f"  /usr/local/bin/python   → {python_path}\n\n"
                f"Requires admin password.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            script = (
                f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                f"ln -sf '{python_path}' /usr/local/bin/python"
            )
            try:
                r = subprocess.run(
                    ["osascript", "-e",
                     f'do shell script "{script}" with administrator privileges'],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(self, "❌ Failed", f"Could not create symlinks:\n{r.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_custom_terminals(self):
        """Load custom terminals from config into table."""
        terminals = self.config.get("custom_terminals", [])
        self.custom_term_table.setRowCount(0)
        for t in terminals:
            row = self.custom_term_table.rowCount()
            self.custom_term_table.insertRow(row)
            self.custom_term_table.setItem(row, 0, QTableWidgetItem(t.get("name", "")))
            self.custom_term_table.setItem(row, 1, QTableWidgetItem(t.get("command", "")))
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked if t.get("enabled", True) else Qt.Unchecked)
            self.custom_term_table.setItem(row, 2, chk)
            # Also add to terminal_combo if enabled
            if t.get("enabled", True):
                name = t.get("name", "")
                if self.terminal_combo.findData(f"custom:{name}") < 0:
                    self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _save_custom_terminals(self):
        """Save custom terminals from table to config."""
        terminals = []
        for row in range(self.custom_term_table.rowCount()):
            name = self.custom_term_table.item(row, 0).text() if self.custom_term_table.item(row, 0) else ""
            cmd = self.custom_term_table.item(row, 1).text() if self.custom_term_table.item(row, 1) else ""
            chk = self.custom_term_table.item(row, 2)
            enabled = chk.checkState() == Qt.Checked if chk else True
            if name and cmd:
                terminals.append({"name": name, "command": cmd, "enabled": enabled})
        self.config.set("custom_terminals", terminals)

    def _add_custom_terminal(self):
        """Add a new custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. My Terminal")
        cmd_edit = QLineEdit()
        cmd_edit.setPlaceholderText('e.g. wt -d "{path}" cmd /k "{activate}"')

        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")

        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            cmd = cmd_edit.text().strip()
            if name and cmd:
                row = self.custom_term_table.rowCount()
                self.custom_term_table.insertRow(row)
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(cmd))
                chk = QTableWidgetItem()
                chk.setCheckState(Qt.Checked)
                self.custom_term_table.setItem(row, 2, chk)
                # Add to combo
                self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _edit_custom_terminal(self):
        """Edit selected custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a terminal to edit.")
            return
        old_name = self.custom_term_table.item(row, 0).text()
        old_cmd = self.custom_term_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        cmd_edit = QLineEdit(old_cmd)
        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            new_name = name_edit.text().strip()
            new_cmd = cmd_edit.text().strip()
            if new_name and new_cmd:
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(new_name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(new_cmd))
                # Update combo
                idx = self.terminal_combo.findData(f"custom:{old_name}")
                if idx >= 0:
                    self.terminal_combo.setItemText(idx, f"⚡ {new_name}")
                    self.terminal_combo.setItemData(idx, f"custom:{new_name}")

    def _remove_custom_terminal(self):
        """Remove selected custom terminal."""
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a terminal to remove.")
            return
        name = self.custom_term_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Terminal",
            f"Remove '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_term_table.removeRow(row)
            idx = self.terminal_combo.findData(f"custom:{name}")
            if idx >= 0:
                self.terminal_combo.removeItem(idx)

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

        # Font — 3-level system load
        _font_defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        _sys_fonts = ("", "Segoe UI", "Yu Gothic UI", "MS Shell Dlg 2", "Arial", "Tahoma")
        for level_id, (def_family, def_size) in _font_defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            saved_family = self.config.get(f"font_{level_id}_family", "")
            saved_size = self.config.get(f"font_{level_id}_size", def_size)
            if saved_family and saved_family not in _sys_fonts:
                cb.setChecked(True)
                combo.setEnabled(True)
                combo.setCurrentFont(QFont(saved_family))
                spin.setEnabled(True)
                spin.setValue(saved_size)
            elif saved_size != def_size and saved_size > 0:
                cb.setChecked(True)
                combo.setEnabled(True)
                spin.setEnabled(True)
                spin.setValue(saved_size)
            else:
                cb.setChecked(False)
                combo.setEnabled(False)
                spin.setEnabled(False)
                spin.setValue(def_size)

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

        # Default environment type
        if hasattr(self, "default_env_type_combo"):
            default_et = self.config.get("default_env_type", "venv")
            et_idx = self.default_env_type_combo.findData(default_et)
            if et_idx >= 0:
                self.default_env_type_combo.setCurrentIndex(et_idx)
            is_custom_et = bool(default_et and default_et != "venv")
            if hasattr(self, "default_env_type_cb"):
                self.default_env_type_cb.setChecked(is_custom_et)
                self.default_env_type_combo.setEnabled(is_custom_et)

        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb") and hasattr(self, "_tc_py_combo"):
            tc_py_on = self.config.get("tc_py_cb_checked", False)
            self._tc_py_cb.setChecked(tc_py_on)
            self._tc_py_combo.setEnabled(tc_py_on)

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

        # Load custom terminals into table and combo
        self._load_custom_terminals()

        # Load custom presets
        self._load_custom_presets()

        # Scan pythons
        self._scan_pythons()

        # Load custom categories
        self._load_custom_categories()

        # Load custom catalog
        self._load_custom_catalog()

        # Jupyter working dir
        jwd = self.config.get("jupyter_workdir", "home")
        jwd_custom = self.config.get("jupyter_workdir_custom", "")
        idx_jwd = self.jupyter_workdir_combo.findData(jwd)
        if idx_jwd >= 0:
            self.jupyter_workdir_combo.setCurrentIndex(idx_jwd)
        if jwd != "home":
            self.jupyter_workdir_cb.setChecked(True)
            self.jupyter_workdir_combo.setEnabled(True)
        if jwd == "custom" and jwd_custom:
            self.jupyter_custom_path_label.setText(jwd_custom)
            self.jupyter_custom_path_label.setVisible(True)
            self.jupyter_custom_path_btn.setEnabled(True)

    def _on_jupyter_workdir_changed(self, idx):
        """Enable/disable custom path button based on selection."""
        data = self.jupyter_workdir_combo.currentData()
        is_custom = data == "custom" and self.jupyter_workdir_cb.isChecked()
        self.jupyter_custom_path_btn.setEnabled(is_custom)
        self.jupyter_custom_path_label.setVisible(is_custom)

    def _pick_jupyter_workdir(self):
        """Open folder picker for custom Jupyter working directory."""
        import os
        current = self.jupyter_custom_path_label.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Jupyter Working Directory", current)
        if folder:
            self.jupyter_custom_path_label.setText(folder)
            self.jupyter_custom_path_label.setVisible(True)

    def _scan_pythons(self):
        """Scan system for Python installations."""
        import os
        import shutil
        self.python_table.setRowCount(0)
        self.default_python_combo.clear()
        self.default_python_combo.addItem("System Default", "")

        excluded_pythons = {
            os.path.normcase(os.path.normpath(p))
            for p in self.config.get("excluded_pythons", [])
        }

        # Which Python is system default — detect from PATH directly (registry on Windows)
        default_norm = ""
        try:
            if os.name == "nt":
                import subprocess as _sp
                _CNW = 0x08000000  # CREATE_NO_WINDOW
                # Read System PATH from registry (fresh, not cached process env)
                sys_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'Machine')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                usr_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                # User PATH takes priority (prepended by Set Default)
                for p in (usr_path + ";" + sys_path).split(";"):
                    p = p.strip()
                    if not p:
                        continue
                    candidate = os.path.join(p, "python.exe")
                    if os.path.isfile(candidate) and "windowsapps" not in p.lower():
                        default_norm = os.path.normcase(os.path.normpath(candidate))
                        break
            else:
                import shutil
                exe = shutil.which("python") or shutil.which("python3") or ""
                default_norm = os.path.normcase(os.path.normpath(exe)) if exe else ""
        except Exception:
            # Fallback: use saved config value
            saved_default = self.config.get("system_default_python", "")
            default_norm = os.path.normcase(os.path.normpath(saved_default)) if saved_default else ""

        # All pythons from system scan — deduplicate symlinks
        system_pythons = find_system_pythons()
        listed_paths = set()
        c = self._c()

        # ── System Default Python'u tabloya garanti olarak ilk satıra ekle ──
        if default_norm and os.path.isfile(default_norm):
            try:
                import subprocess as _sp
                result = _sp.run(
                    [default_norm, "--version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000 if __import__('os').name == "nt" else 0
                )
                sys_version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                sys_version = "?"
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(sys_version))
            _dn_norm = os.path.normpath(default_norm)
            if len(_dn_norm) >= 2 and _dn_norm[1] == ":":
                _dn_norm = _dn_norm[0].upper() + _dn_norm[1:]
            self.python_table.setItem(row, 1, QTableWidgetItem(_dn_norm))
            source_item = QTableWidgetItem("System Default")
            source_item.setForeground(QColor(c['success']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {sys_version} (System Default)", _dn_norm)
            listed_paths.add(default_norm)

        # Resolve symlinks: group by real binary, keep shortest path
        seen_real = {}  # realpath -> (version, norm_path)
        for version, path in system_pythons:
            norm_path = os.path.normpath(path)
            norm_case = os.path.normcase(norm_path)
            if norm_case in excluded_pythons:
                continue
            try:
                real = os.path.realpath(path)
            except OSError:
                real = norm_path
            if real in seen_real:
                # Keep the shorter/cleaner path (e.g. /usr/bin/python over /usr/bin/python3.14)
                existing = seen_real[real]
                if len(norm_path) < len(existing[1]):
                    seen_real[real] = (version, norm_path)
            else:
                seen_real[real] = (version, norm_path)

        for _real, (version, norm_path) in seen_real.items():
            norm_case = os.path.normcase(norm_path)
            if norm_case in listed_paths:
                continue
            listed_paths.add(norm_case)

            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            if len(norm_path) >= 2 and norm_path[1] == ":":
                norm_path = norm_path[0].upper() + norm_path[1:]
            self.python_table.setItem(row, 0, QTableWidgetItem(version))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))

            # Source label: System / User Install / Custom
            import os as _os
            import sys as _sys
            _home = _os.path.expanduser("~").lower()
            _localappdata = _os.environ.get("LOCALAPPDATA", "").lower()
            _appdata = _os.environ.get("APPDATA", "").lower()
            _progfiles = _os.environ.get("PROGRAMFILES", "C:\\Program Files").lower()
            _progfiles86 = _os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)").lower()
            _windir = _os.environ.get("WINDIR", "C:\\Windows").lower()
            _norm_lower = norm_path.lower()

            _this_exe = _os.path.normcase(_os.path.normpath(_sys.executable)).lower()
            _is_this_python = (_os.path.normcase(norm_path).lower() == _this_exe)

            if _is_this_python and getattr(_sys, "frozen", False):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_progfiles and _norm_lower.startswith(_progfiles)) or
                (_progfiles86 and _norm_lower.startswith(_progfiles86)) or
                (_windir and _norm_lower.startswith(_windir)) or
                "/usr/" in _norm_lower or
                "/opt/" in _norm_lower or
                _norm_lower.startswith("/bin/") or
                _norm_lower.startswith("/usr/bin/")
            ):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_home and _norm_lower.startswith(_home)) or
                (_localappdata and _norm_lower.startswith(_localappdata)) or
                (_appdata and _norm_lower.startswith(_appdata)) or
                "/.local/" in _norm_lower or
                "/.pyenv/" in _norm_lower or
                "/home/" in _norm_lower
            ):
                source_item = QTableWidgetItem("User Install")
                source_item.setForeground(QColor(c['accent']))
            else:
                source_item = QTableWidgetItem("Custom")
                source_item.setForeground(QColor(c['fg_muted']))

            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {version}", norm_path)

        # Custom pythons from config (skip already listed)
        custom_pythons = self.config.get("custom_pythons", [])
        cleaned_custom = []
        for entry in custom_pythons:
            norm_path = os.path.normpath(entry.get("path", ""))
            norm_case = os.path.normcase(norm_path)
            if norm_case in listed_paths:
                continue  # already shown above
            cleaned_custom.append(entry)
            listed_paths.add(norm_case)
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(entry.get("version", "?")))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))
            source_item = QTableWidgetItem("Custom")
            source_item.setForeground(QColor(c['accent']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(
                f"Python {entry.get('version', '?')} (Custom)", norm_path
            )

        if len(cleaned_custom) != len(custom_pythons):
            self.config.set("custom_pythons", cleaned_custom)

        # Standalone (downloaded) Pythons
        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                if os.path.normcase(exe_path) in listed_paths:
                    continue
                listed_paths.add(os.path.normcase(exe_path))
                row = self.python_table.rowCount()
                self.python_table.insertRow(row)
                self.python_table.setItem(row, 0, QTableWidgetItem(py["version"]))
                self.python_table.setItem(row, 1, QTableWidgetItem(exe_path))
                source_item = QTableWidgetItem("Downloaded")
                source_item.setForeground(QColor(c['success']))
                self.python_table.setItem(row, 2, source_item)
                self.default_python_combo.addItem(
                    f"Python {py['version']} (Downloaded)", exe_path
                )
        except Exception:
            pass

        # Set default python combo selection
        default_py = self.config.get("default_python", "")
        if default_py and default_py.strip():
            default_py_norm = os.path.normpath(default_py)
            found_idx = -1
            for i in range(self.default_python_combo.count()):
                item_data = self.default_python_combo.itemData(i) or ""
                if item_data and os.path.normpath(item_data).lower() == default_py_norm.lower():
                    found_idx = i
                    break
            if found_idx > 0:
                self.default_py_cb.setChecked(True)
                self.default_python_combo.setEnabled(True)
                self.default_python_combo.setCurrentIndex(found_idx)
            else:
                self.default_py_cb.setChecked(False)
                self.default_python_combo.setEnabled(False)
                self.default_python_combo.setCurrentIndex(0)
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
        """Remove a custom or downloaded Python path."""
        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version to remove.")
            return

        row = rows[0].row()
        source = self.python_table.item(row, 2).text()
        version = self.python_table.item(row, 0).text()
        path = self.python_table.item(row, 1).text()

        if source == "System":
            QMessageBox.information(
                self, "Info",
                "System-detected Python installations cannot be removed here.\n"
                "Use your system package manager to uninstall them."
            )
            return

        if source == "User Install":
            reply = QMessageBox.question(
                self, "Remove User Install",
                f"Remove Python {version} from the list?\n\n"
                f"  {path}\n\n"
                f"Note: This only removes it from VenvStudio's list.\n"
                f"To fully uninstall, use: pip uninstall python (or your package manager).",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                # Save to config as excluded path so it won't reappear on next scan
                excluded = self.config.get("excluded_pythons", [])
                if path not in excluded:
                    excluded.append(path)
                    self.config.set("excluded_pythons", excluded)
                self._scan_pythons()
            return

        if source == "Downloaded":
            reply = QMessageBox.question(
                self, "Remove Downloaded Python",
                f"Permanently delete Python {version}?\n\n"
                f"  {path}\n\n"
                f"This will remove the downloaded files from disk.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                from src.core.python_downloader import get_installed_pythons, remove_python
                for py in get_installed_pythons():
                    if py["version"] == version or os.path.normpath(str(py.get("python_exe", ""))) == os.path.normpath(path):
                        remove_python(py["path"])
                        break
                self._scan_pythons()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove Python {version}:\n{e}")
            return

        # source == "Custom"
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

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()

        platform = get_platform()

        # ── Linux / macOS ──
        if platform != "windows":
            self._set_python_default_unix(version, python_path, scope)
            return

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
            """Find PATH entries that belong to OTHER Python installations.
            ONLY removes dirs where python.exe exists directly,
            or Scripts dirs whose PARENT contains python.exe AND pip.exe.
            Never touches non-Python dirs like winget, oh-my-posh, etc.
            """
            exclude_set = {os.path.normcase(d.rstrip("\\")) for d in exclude_dirs}
            found = []
            for p in path_str.split(";"):
                p = p.strip()
                if not p:
                    continue
                p_norm = os.path.normcase(p.rstrip("\\"))
                if p_norm in exclude_set:
                    continue
                # Must have python.exe directly in this dir
                if os.path.exists(os.path.join(p, "python.exe")):
                    found.append(p)
                    continue
                # Scripts dir — ONLY if parent has BOTH python.exe AND pip.exe
                if os.path.basename(p).lower() == "scripts":
                    parent = os.path.dirname(p)
                    has_python = os.path.exists(os.path.join(parent, "python.exe"))
                    has_pip = os.path.exists(os.path.join(p, "pip.exe"))
                    if has_python and has_pip:
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

        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_path_result.txt")

        # SAFE approach: only PREPEND selected Python to PATH — never delete anything else
        # This avoids accidentally removing winget, oh-my-posh, or other tools from PATH.
        # Users with multiple Python versions can use `py -3.x` launcher to choose.
        if scope == "user":
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from User PATH (to avoid duplicates), then prepend
    $uPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $uParts = ($uPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newUser = ('{python_dir};{scripts_dir};' + ($uParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newUser, 'User')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        else:  # system
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from System PATH (to avoid duplicates), then prepend
    $sPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $sParts = ($sPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newSys = ('{python_dir};{scripts_dir};' + ($sParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newSys, 'Machine')

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
                with open(result_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
                    result_text = f.read().strip()
                if "OK" in result_text:
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
                # Verify pip.exe actually exists in Scripts dir
                pip_status = ""
                if not os.path.isfile(pip_exe):
                    pip_status = (
                        f"\n\n⚠️ pip.exe not found in Scripts folder!\n"
                        f"   Run: python -m pip install --upgrade pip\n"
                        f"   (in an admin terminal)"
                    )
                else:
                    pip_status = f"\n\n✅ pip.exe found in Scripts folder."

                QMessageBox.information(
                    self, "✅ Success",
                    f"Python {version} is now the {scope_label} default!\n\n"
                    f"📂 Added to PATH:\n"
                    f"   {python_dir}\n"
                    f"   {scripts_dir}"
                    f"{pip_status}\n\n"
                    f"Open a new terminal and type:\n"
                    f"  python --version\n"
                    f"  pip --version"
                )
                self.config.set("system_default_python", python_path)
                # Save as system default so _scan_pythons shows correct Source
                self.config.set("system_default_python", python_path)
                self._scan_pythons()
            else:
                QMessageBox.warning(
                    self, "⚠️ Partial",
                    f"Could not verify the change.\n"
                    f"Admin permission may have been denied.\n\n"
                    f"Check Environment Variables manually."
                )
                self._scan_pythons()

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

    def _toggle_builtin_presets(self, visible: bool):
        self.builtin_presets_table.setVisible(visible)

    def _load_custom_presets(self):
        """Load custom presets from config into table."""
        presets = self.config.get("custom_presets", {})
        self.custom_presets_table.setRowCount(0)
        for name, pkgs in presets.items():
            row = self.custom_presets_table.rowCount()
            self.custom_presets_table.insertRow(row)
            self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
            self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _save_custom_presets(self):
        """Save custom presets from table to config."""
        presets = {}
        for row in range(self.custom_presets_table.rowCount()):
            name_item = self.custom_presets_table.item(row, 0)
            pkgs_item = self.custom_presets_table.item(row, 1)
            if name_item and pkgs_item:
                name = name_item.text().strip()
                pkgs = [p.strip() for p in pkgs_item.text().split(",") if p.strip()]
                if name and pkgs:
                    presets[name] = pkgs
        self.config.set("custom_presets", presets)

    def _add_custom_preset(self):
        """Add a new custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. 🚀 My Stack")
        pkgs_edit = QLineEdit()
        pkgs_edit.setPlaceholderText("e.g. numpy, pandas, matplotlib, scikit-learn")

        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                pkgs = [p.strip() for p in pkgs_raw.split(",") if p.strip()]
                row = self.custom_presets_table.rowCount()
                self.custom_presets_table.insertRow(row)
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _edit_custom_preset(self):
        """Edit selected custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a preset to edit.")
            return
        old_name = self.custom_presets_table.item(row, 0).text()
        old_pkgs = self.custom_presets_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        pkgs_edit = QLineEdit(old_pkgs)
        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(pkgs_raw))

    def _remove_custom_preset(self):
        """Remove selected custom preset."""
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a preset to remove.")
            return
        name = self.custom_presets_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Preset",
            f"Remove preset '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_presets_table.removeRow(row)

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
            f"background-color: {self._c()['input_bg']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"padding: 3px; font-size: {self._c()['fs_small']}px;"
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
        import os
        import subprocess
        from pathlib import Path
        # Try to get log dir from logger module, fall back to known path
        try:
            from src.utils.logger import get_log_dir
            log_dir = get_log_dir()
        except ImportError:
            import os
            log_dir = Path(os.environ.get("APPDATA", "~")) / "VenvStudio" / "logs"
            log_dir = log_dir.expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        if get_platform() == "windows":
            os.startfile(str(log_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(log_dir)])
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])

    def _open_config_folder(self):
        """Open the config directory in file manager."""
        import os
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
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
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
        self.update_status_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")

        # Run in background thread
        self._update_worker = _UpdateCheckWorker(parent=self)
        self._update_worker.finished.connect(self._on_update_check_done)
        self._update_worker.start()

    def _on_update_check_done(self, result):
        """Handle update check result."""
        if result.get("error"):
            self.update_status_label.setText(f"⚠️ {result['error']}")
            self.update_status_label.setStyleSheet(f"color: {self._c()['accent']}; font-size: {self._c()['fs_small']}px;")
            return

        if result["update_available"]:
            self.update_status_label.setText(
                f"🆕 New version available: v{result['latest_version']} (current: v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

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
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

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
        # Use batch mode to avoid writing JSON 30+ times
        self.config.begin_batch()
        # Theme
        if self.theme_cb.isChecked():
            new_theme = self.theme_combo.currentData()
        else:
            new_theme = "dark"
        old_theme = self.config.get("theme", "dark")
        self.config.set("theme", new_theme)
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        # Font — 3-level system
        _defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        for level_id, (def_family, def_size) in _defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            if cb.isChecked():
                self.config.set(f"font_{level_id}_family", combo.currentFont().family())
                self.config.set(f"font_{level_id}_size", spin.value())
            else:
                self.config.set(f"font_{level_id}_family", "")
                self.config.set(f"font_{level_id}_size", def_size)

        # Backward compat
        self.config.set("font_family", self.config.get("font_secondary_family", ""))
        self.config.set("font_size", self.config.get("font_secondary_size", 13))
        font_family = self.config.get("font_secondary_family", "") or "Segoe UI"
        font_size = self.config.get("font_secondary_size", 13)
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

        # Default environment type
        if hasattr(self, "default_env_type_combo"):
            cb_et = getattr(self, "default_env_type_cb", None)
            et_val = self.default_env_type_combo.currentData() if (cb_et and cb_et.isChecked()) else "venv"
            self.config.set("default_env_type", et_val or "venv")
        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb"):
            self.config.set("tc_py_cb_checked", self._tc_py_cb.isChecked())
        if self.terminal_cb.isChecked():
            self.config.set("default_terminal", self.terminal_combo.currentData())
        else:
            self.config.set("default_terminal", "")

        # Jupyter Working Directory
        if self.jupyter_workdir_cb.isChecked():
            self.config.set("jupyter_workdir", self.jupyter_workdir_combo.currentData() or "home")
            if self.jupyter_workdir_combo.currentData() == "custom":
                self.config.set("jupyter_workdir_custom", self.jupyter_custom_path_label.text())
            else:
                self.config.set("jupyter_workdir_custom", "")
        else:
            self.config.set("jupyter_workdir", "home")
            self.config.set("jupyter_workdir_custom", "")

        # Save custom terminals
        self._save_custom_terminals()

        # Save custom presets
        self._save_custom_presets()

        # Save custom categories
        self._save_custom_categories()

        # Save custom catalog
        self._save_custom_catalog()

        # End batch — single disk write for all settings
        self.config.end_batch()
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

    def _reset_appearance(self):
        """Reset Appearance section to defaults."""
        self.theme_cb.setChecked(False)
        self.theme_combo.setEnabled(False)
        idx = self.theme_combo.findData("dark")
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.config.set("theme", "dark")
        self.theme_changed.emit("dark")
        self._reset_fonts()

    def _reset_language(self):
        """Reset Language section to defaults."""
        self.lang_enabled_cb.setChecked(False)
        idx = self.lang_combo.findData("en")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.config.set("language", "en")

    def _reset_general(self):
        """Reset General section to defaults."""
        from src.core.config_manager import DEFAULT_SETTINGS
        general_keys = [
            "auto_upgrade_pip", "confirm_delete", "show_hidden_packages",
            "check_updates", "remember_window", "default_terminal",
        ]
        for key in general_keys:
            if key in DEFAULT_SETTINGS:
                self.config.set(key, DEFAULT_SETTINGS[key])
        self._load_current_settings()


    # ── Package Manager helpers ───────────────────────────────────────────────

    def _make_pm_tool_row(self, tool: str, pkg: str, label: str):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        status = QLabel("🔍 Checking...")
        status.setStyleSheet("font-size: 11px; color: #a6adc8;")
        rl.addWidget(status, 1)
        user_btn = QPushButton(f"Install {tool} (User)")
        user_btn.setObjectName("secondary")
        user_btn.setFixedHeight(26)
        user_btn.setVisible(False)
        user_btn.clicked.connect(lambda checked=False, t=tool, p=pkg, st=status, b=user_btn: self._pm_install_tool(t, p, "user", st, b))
        rl.addWidget(user_btn)
        sys_btn = QPushButton(f"Install {tool} (System 🔒)")
        sys_btn.setObjectName("secondary")
        sys_btn.setFixedHeight(26)
        sys_btn.setVisible(False)
        sys_btn.setToolTip("Install system-wide — requires Administrator / sudo")
        sys_btn.clicked.connect(lambda checked=False, t=tool, p=pkg, st=status, b=sys_btn: self._pm_install_tool(t, p, "system", st, b))
        rl.addWidget(sys_btn)
        uninstall_btn = QPushButton("Uninstall")
        uninstall_btn.setObjectName("secondary")
        uninstall_btn.setFixedHeight(26)
        uninstall_btn.setVisible(False)
        uninstall_btn.clicked.connect(lambda checked=False, t=tool, p=pkg, st=status, b=uninstall_btn: self._pm_uninstall_tool(t, p, st, b))
        rl.addWidget(uninstall_btn)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._pm_check_tool(tool, status, user_btn, sys_btn, uninstall_btn))
        return row

    def _make_pm_conda_row(self):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        status = QLabel("🔍 Checking...")
        status.setStyleSheet("font-size: 11px; color: #a6adc8;")
        rl.addWidget(status, 1)
        dl_btn = QPushButton("⬇ Download micromamba")
        dl_btn.setObjectName("secondary")
        dl_btn.setFixedHeight(26)
        dl_btn.setVisible(False)
        dl_btn.clicked.connect(lambda checked=False, st=status, b=dl_btn: self._pm_download_micromamba(st, b))
        rl.addWidget(dl_btn)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(250, lambda: self._pm_check_conda(status, dl_btn))
        return row

    def _pm_check_tool(self, tool, status_label, user_btn, sys_btn, uninstall_btn):
        import shutil, os, sys, site
        candidates = []
        for n in (tool, tool + ".exe"):
            w = shutil.which(n)
            if w: candidates.append(w)
        try:
            ub = site.getuserbase()
            scripts = os.path.join(ub, "Scripts" if sys.platform == "win32" else "bin")
            for n in (tool, tool + ".exe"):
                candidates.append(os.path.join(scripts, n))
        except Exception:
            pass
        py_scripts = os.path.join(os.path.dirname(sys.executable), "Scripts" if sys.platform == "win32" else "bin")
        for n in (tool, tool + ".exe"):
            candidates.append(os.path.join(py_scripts, n))
        if sys.platform == "win32":
            py_appdata = os.path.join(os.environ.get("APPDATA", ""), "Python")
            if os.path.isdir(py_appdata):
                for sub in os.listdir(py_appdata):
                    s = os.path.join(py_appdata, sub, "Scripts")
                    for n in (tool, tool + ".exe"):
                        candidates.append(os.path.join(s, n))
        found = next((c for c in candidates if c and os.path.isfile(c)), "")
        if found:
            try:
                from src.core.tool_registry import ToolRegistry
                ToolRegistry().register(tool, found, installed_by="system")
            except Exception:
                pass
            status_label.setText(f"✅ {found}")
            status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
            uninstall_btn.setVisible(True)
        else:
            status_label.setText("❌ Not installed")
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
            user_btn.setVisible(True)
            sys_btn.setVisible(True)

    def _pm_check_conda(self, status_label, dl_btn):
        try:
            from src.core.micromamba_installer import get_micromamba_exe
            exe = get_micromamba_exe()
        except Exception:
            exe = None
        if exe:
            status_label.setText(f"✅ {exe}")
            status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
        else:
            status_label.setText("❌ Not installed")
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
            dl_btn.setVisible(True)

    def _pm_install_tool(self, tool, pkg, scope, status_label, btn):
        import sys
        btn.setEnabled(False)
        btn.setText("Installing...")
        status_label.setText(f"⏳ Installing {tool}...")
        status_label.setStyleSheet("font-size: 11px; color: #89b4fa;")
        def _do(callback=None):
            import subprocess, shutil, os, site
            if scope == "system" and sys.platform == "win32":
                try:
                    import ctypes
                    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f"-m pip install {pkg} -q", None, 1)
                    if ret <= 32: return False, f"UAC failed (code {ret})"
                    import time; time.sleep(4)
                except Exception as e:
                    return False, f"UAC error: {e}"
            elif scope == "system":
                r = subprocess.run(["sudo", sys.executable, "-m", "pip", "install", pkg, "-q"], capture_output=True, text=True, timeout=120)
                if r.returncode != 0: return False, (r.stderr or "failed")[:200]
            else:
                r = subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--user", "-q"], capture_output=True, text=True, timeout=120)
                if r.returncode != 0: return False, (r.stderr or "failed")[:200]
            if tool == "pipx":
                try: subprocess.run([sys.executable, "-m", "pipx", "ensurepath"], capture_output=True, timeout=30)
                except Exception: pass
            candidates = []
            for n in (tool, tool + ".exe"):
                w = shutil.which(n)
                if w: candidates.append(w)
            try:
                ub = site.getuserbase()
                s = os.path.join(ub, "Scripts" if sys.platform == "win32" else "bin")
                for n in (tool, tool + ".exe"):
                    c = os.path.join(s, n)
                    if os.path.isfile(c): candidates.append(c)
            except Exception: pass
            if sys.platform == "win32":
                pa = os.path.join(os.environ.get("APPDATA", ""), "Python")
                if os.path.isdir(pa):
                    for sub in os.listdir(pa):
                        s = os.path.join(pa, sub, "Scripts")
                        for n in (tool, tool + ".exe"):
                            c = os.path.join(s, n)
                            if os.path.isfile(c): candidates.append(c)
            found = next((c for c in candidates if c and os.path.isfile(c)), None)
            if found: return True, found
            return False, "Installed but not found in PATH — restart may be needed"
        def _done(success, result):
            if success:
                status_label.setText(f"✅ {result}")
                status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
                btn.setVisible(False)
                try:
                    from src.core.tool_registry import ToolRegistry
                    ToolRegistry().register(tool, result, installed_by="venvstudio")
                except Exception: pass
            else:
                status_label.setText(f"❌ {result}")
                status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
                btn.setEnabled(True)
                btn.setText(f"Install {tool} ({'User' if scope == 'user' else 'System 🔒'})")
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do)
        w.finished.connect(_done)
        w.start()
        self._pm_worker = w

    def _pm_uninstall_tool(self, tool, pkg, status_label, btn):
        import sys, subprocess
        btn.setEnabled(False)
        r = subprocess.run([sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q"], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            status_label.setText("❌ Not installed")
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
            try:
                from src.core.tool_registry import ToolRegistry
                ToolRegistry().remove(tool)
            except Exception: pass
        btn.setEnabled(True)

    def _pm_download_micromamba(self, status_label, btn):
        btn.setEnabled(False)
        btn.setText("Downloading...")
        status_label.setText("⏳ Downloading micromamba...")
        status_label.setStyleSheet("font-size: 11px; color: #89b4fa;")
        def _do(callback=None):
            try:
                from src.core.micromamba_installer import download_micromamba
                path = download_micromamba(progress_cb=callback)
                return True, str(path)
            except Exception as e:
                return False, str(e)
        def _done(success, result):
            if success:
                status_label.setText(f"✅ {result}")
                status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
                btn.setVisible(False)
            else:
                status_label.setText(f"❌ {result[:100]}")
                status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
                btn.setEnabled(True)
                btn.setText("⬇ Download micromamba")
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do)
        w.finished.connect(_done)
        w.start()
        self._pm_worker = w


    # ════════════════════════════════════════════════════════
    # TOOLCHAIN MANAGER
    # Per-Python: pip | venv | uv | poetry | pipx | conda
    # ════════════════════════════════════════════════════════

    _TC_TOOLS = [
        # (id,          pip_pkg,   label,    icon)
        ("pip",         "pip",     "pip",    "📦"),
        ("venv",        None,      "venv",   "🐍"),
        ("uv",          "uv",      "uv",     "⚡"),
        ("poetry",      "poetry",  "Poetry", "📜"),
        ("pipx",        "pipx",    "pipx",   "📦"),
        ("micromamba",  None,      "Conda",  "🦎"),
    ]

    def _build_toolchain_ui(self, layout):
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
            QHeaderView, QAbstractItemView, QGroupBox, QSizePolicy,
        )
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QFont, QColor

        layout.addWidget(self._make_group_title_row(
            "🛠️ Toolchain Manager",
            "Install, remove and verify tools per Python version.\n"
            "Select a Python from the dropdown, then use the action buttons.\n\n"
            "pip / venv: upgrade with User or System\n"
            "uv / poetry / pipx: User (no admin) or System (admin)\n"
            "Conda (micromamba): download binary",
        ))

        grp = QGroupBox()
        grp.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {self._c().get('border', '#444')}; "
            f"border-radius: 6px; padding: 8px; margin-top: 4px; "
            f"background: {self._c().get('bg_secondary', '#1e1e2e')}; }}"
        )
        vl = QVBoxLayout(grp)
        vl.setSpacing(8)
        vl.setContentsMargins(10, 10, 10, 10)

        # ── Python selector row ──────────────────────────────────────────
        sel_row = QHBoxLayout()
        self._tc_py_cb = QCheckBox()
        self._tc_py_cb.setChecked(False)
        sel_row.addWidget(self._tc_py_cb)
        self._tc_py_combo = QComboBox()
        self._tc_py_combo.setEnabled(False)
        sel_row.addWidget(self._tc_py_combo, 1)
        vl.addLayout(sel_row)

        self._tc_py_cb.toggled.connect(self._tc_py_combo.setEnabled)
        self._tc_py_cb.toggled.connect(
            lambda on: on and self._tc_load_table(
                self._tc_py_combo.currentData() or ""))

        # Note + Refresh button row
        note_row = QHBoxLayout()
        py_note = QLabel("Enable checkbox to select Python and load tool status.")
        py_note.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self._tc_py_note = py_note
        note_row.addWidget(py_note, 1)
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.setToolTip("Reload tool status for selected Python")
        refresh_btn.clicked.connect(lambda: self._tc_load_table(
            self._tc_py_combo.currentData() or "") if self._tc_py_cb.isChecked() else None)
        note_row.addWidget(refresh_btn)
        vl.addLayout(note_row)

        # ── Tool table ───────────────────────────────────────────────────
        tbl = QTableWidget(len(self._TC_TOOLS), 5)
        tbl.setHorizontalHeaderLabels(["Tool", "Status", "Version", "Path", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        tbl.setColumnWidth(3, 380)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionMode(QAbstractItemView.NoSelection)
        tbl.setShowGrid(False)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            f"QTableWidget {{ font-size: {self._c()['fs_base']}px; }}"
            f"QTableWidget::item {{ padding: 4px 8px; }}"
        )
        for row, (tid, pkg, lbl, icon) in enumerate(self._TC_TOOLS):
            tbl.setRowHeight(row, 38)
            name = QTableWidgetItem(f"{icon}  {lbl}")
            _f = QFont(); _f.setWeight(QFont.Medium); name.setFont(_f)
            tbl.setItem(row, 0, name)
            for col in (1, 2, 3):
                ph = QTableWidgetItem("—")
                ph.setForeground(QColor(self._c()["fg_muted"]))
                tbl.setItem(row, col, ph)
            tbl.setCellWidget(row, 4, self._tc_row_btns(tid, pkg, tbl, row))
        self._tc_table = tbl
        # Size table to show all rows without scrolling
        row_h = 40
        header_h = 28
        total_h = len(self._TC_TOOLS) * row_h + header_h + 4
        tbl.setMinimumHeight(total_h)
        tbl.setMaximumHeight(total_h + 20)
        from PySide6.QtCore import Qt
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vl.addWidget(tbl)

        layout.addWidget(grp)

        # Populate combo from python_table, then auto-load
        self._tc_py_combo.currentIndexChanged.connect(
            lambda: self._tc_py_cb.isChecked() and self._tc_load_table(
                self._tc_py_combo.currentData() or ""))
        # Auto-enable and load on startup
        def _auto_load():
            self._tc_scan_pythons()
            if self._tc_py_cb.isChecked() and self._tc_py_combo.count():
                self._tc_load_table(self._tc_py_combo.currentData() or "")
        QTimer.singleShot(300, _auto_load)

    def _tc_row_btns(self, tool, pkg, tbl, row):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMenu
        from PySide6.QtGui import QAction
        from PySide6.QtCore import Qt
        w = QWidget()
        w.setAttribute(Qt.WA_TranslucentBackground)
        hl = QHBoxLayout(w)
        hl.setContentsMargins(2, 1, 2, 1)
        hl.setSpacing(4)

        def _b(text, tip="", danger=False, name=""):
            b = QPushButton(text)
            b.setMinimumHeight(26)
            b.setMinimumWidth(110)
            b.setObjectName("danger" if danger else "secondary")
            b.setToolTip(tip)
            b.setAccessibleName(name)
            b.setFocusPolicy(Qt.NoFocus)
            b.setDefault(False); b.setAutoDefault(False)
            return b

        def _ask_scope(parent_btn, cb_user, cb_system):
            """Show User/System popup menu under button."""
            menu = QMenu(parent_btn)
            a_user   = menu.addAction("👤 User  (no admin)")
            a_system = menu.addAction("🖥 System  (admin/sudo)")
            chosen = menu.exec(parent_btn.mapToGlobal(
                parent_btn.rect().bottomLeft()))
            if chosen == a_user:    cb_user()
            elif chosen == a_system: cb_system()

        if tool == "micromamba":
            # Micromamba: Download only (standalone binary)
            install_btn = _b("⬇ Install", "Download micromamba binary", name="install_user")
            install_btn.setVisible(True)
            upgrade_btn = _b("⬆ Upgrade", "Re-download micromamba",     name="upgrade_user")
            upgrade_btn.setVisible(False)
            hl.addWidget(install_btn)
            hl.addWidget(upgrade_btn)
            install_btn.clicked.connect(lambda: self._tc_download_mamba(tbl, row))
            upgrade_btn.clicked.connect(lambda: self._tc_download_mamba(tbl, row))
        else:
            install_btn = _b("⬇ Install", "Install this tool",   name="install_user")
            upgrade_btn = _b("⬆ Upgrade", "Upgrade this tool",   name="upgrade_user")
            remove_btn  = _b("🗑 Remove",  "Uninstall this tool", True, name="rm_user")
            upgrade_btn.setVisible(False)
            remove_btn.setVisible(False)
            hl.addWidget(install_btn)
            hl.addWidget(upgrade_btn)
            hl.addWidget(remove_btn)

            if tool in ("pip", "venv"):
                install_btn.setText("⬆ Upgrade")
                install_btn.setToolTip("Upgrade pip/venv")
                install_btn.setAccessibleName("upgrade_user")
                remove_btn.setVisible(False)

            install_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row, b=install_btn:
                _ask_scope(b,
                    lambda: self._tc_do_install(t, p, "user",   tb, r),
                    lambda: self._tc_do_install(t, p, "system", tb, r)))
            upgrade_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row, b=upgrade_btn:
                _ask_scope(b,
                    lambda: self._tc_do_install(t, p, "user",   tb, r),
                    lambda: self._tc_do_install(t, p, "system", tb, r)))
            remove_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row, b=remove_btn:
                _ask_scope(b,
                    lambda: self._tc_do_remove(t, p, "user",   tb, r),
                    lambda: self._tc_do_remove(t, p, "system", tb, r)))
        return w

    def _tc_update_row_btns(self, tbl, row, installed: bool):
        """Update button visibility based on install status."""
        w = tbl.cellWidget(row, 4)
        if not w: return
        from PySide6.QtWidgets import QPushButton
        btns = {b.accessibleName(): b for b in w.findChildren(QPushButton)}
        # pip/venv always show upgrade (install_user repurposed as upgrade)
        tid = self._TC_TOOLS[row][0] if row < len(self._TC_TOOLS) else ""
        if tid in ("pip", "venv"):
            # Always show upgrade only
            for n in ("install_user", "upgrade_user"): 
                if n in btns: btns[n].setVisible(True)
            if "rm_user" in btns: btns["rm_user"].setVisible(False)
        elif installed:
            if "install_user" in btns: btns["install_user"].setVisible(False)
            for n in ("upgrade_user", "rm_user"):
                if n in btns: btns[n].setVisible(True)
        else:
            if "install_user" in btns: btns["install_user"].setVisible(True)
            for n in ("upgrade_user", "rm_user"):
                if n in btns: btns[n].setVisible(False)

    def _tc_scan_pythons(self):
        """Populate combo from existing Python Versions table (no re-scan)."""
        combo = self._tc_py_combo
        combo.blockSignals(True)
        current_data = combo.currentData()
        combo.clear()

        import sys, subprocess

        # Read from the already-populated python_table
        added = set()
        if hasattr(self, "python_table"):
            tbl = self.python_table
            for row in range(tbl.rowCount()):
                ver_item  = tbl.item(row, 0)
                path_item = tbl.item(row, 1)
                src_item  = tbl.item(row, 2)
                if not path_item: continue
                path = path_item.text().strip()
                ver  = ver_item.text().strip() if ver_item else "?"
                src  = src_item.text().strip() if src_item else "System"
                if not path or path in added: continue
                added.add(path)
                combo.addItem(f"Python {ver}  [{src}]  {path}", path)

        # Always ensure current Python is present (skip if frozen exe)
        import os
        if not getattr(sys, "frozen", False):
            cur = os.path.normcase(sys.executable)
            if cur not in {os.path.normcase(combo.itemData(i) or "")
                           for i in range(combo.count())}:
                try:
                    r = subprocess.run([sys.executable, "--version"],
                        capture_output=True, text=True, timeout=3,
                        creationflags=0x08000000 if sys.platform == "win32" else 0)
                    ver = (r.stdout or r.stderr).strip().replace("Python ","")
                except Exception:
                    ver = "?"
                combo.insertItem(0, f"Python {ver}  [Current]  {sys.executable}",
                                 sys.executable)

        combo.blockSignals(False)

        note = getattr(self, "_tc_py_note", None)
        if note:
            note.setText(f"{combo.count()} Python installation(s) available.")

        # Restore previous selection or use first
        idx = 0
        if current_data:
            for i in range(combo.count()):
                if os.path.normcase(combo.itemData(i) or "") == os.path.normcase(current_data):
                    idx = i; break
        if combo.count():
            combo.setCurrentIndex(idx)
            self._tc_load_table(combo.itemData(idx) or "")


    def _tc_find_tool(self, tool, py_exe):
        """Find tool exe for given Python. Returns path or ''."""
        import os, sys, shutil, site
        cands = []
        for n in (tool, tool+".exe"):
            w = shutil.which(n)
            if w: cands.append(w)
        py_sc = os.path.join(os.path.dirname(py_exe),
            "Scripts" if sys.platform=="win32" else "bin")
        for n in (tool,tool+".exe"):
            cands.append(os.path.join(py_sc,n))
        try:
            ub = site.getuserbase()
            sc = os.path.join(ub,"Scripts" if sys.platform=="win32" else "bin")
            for n in (tool,tool+".exe"): cands.append(os.path.join(sc,n))
        except Exception: pass
        if sys.platform=="win32":
            pa = os.path.join(os.environ.get("APPDATA",""),"Python")
            if os.path.isdir(pa):
                for sub in os.listdir(pa):
                    sc = os.path.join(pa,sub,"Scripts")
                    for n in (tool,tool+".exe"): cands.append(os.path.join(sc,n))
        return next((c for c in cands if c and os.path.isfile(c)),"")

    def _tc_load_table(self, py_exe):
        """Reload table rows for the selected Python."""
        import os
        if not py_exe or not hasattr(self,"_tc_table"):
            return
        import subprocess, sys
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTableWidgetItem
        tbl = self._tc_table

        def _do(callback=None):
            rows = []
            for tid, pkg, lbl, icon in self._TC_TOOLS:
                if tid == "micromamba":
                    try:
                        from src.core.micromamba_installer import get_micromamba_exe
                        path = str(get_micromamba_exe() or "")
                    except Exception: path = ""
                elif tid in ("pip", "venv"):
                    try:
                        if tid == "venv":
                            # venv has no --version; check if module exists
                            r = subprocess.run(
                                [py_exe, "-c", "import venv; print(venv.__version__ if hasattr(venv,'__version__') else 'ok')"],
                                capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
                            path = py_exe if r.returncode == 0 else ""
                        else:
                            r = subprocess.run([py_exe, "-m", tid, "--version"],
                                capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
                            path = py_exe if r.returncode == 0 else ""
                    except Exception: path = ""
                else:
                    path = self._tc_find_tool(tid, py_exe)

                ver = "—"
                if path:
                    try:
                        if tid == "venv":
                            r = subprocess.run([py_exe, "--version"],
                                capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
                            ver = (r.stdout or r.stderr).strip().replace("Python ", "")
                        elif tid == "pip":
                            r = subprocess.run([py_exe, "-m", "pip", "--version"],
                                capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
                            out = (r.stdout or r.stderr).strip()
                            for p in out.split():
                                if p and p[0].isdigit():
                                    ver = p.rstrip(","); break
                        else:
                            r = subprocess.run([path, "--version"],
                                capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
                            out = (r.stdout or r.stderr).strip()
                            for p in out.split():
                                if p and p[0].isdigit():
                                    ver = p.rstrip(","); break
                            if ver == "—": ver = out[:20]
                    except Exception:
                        pass
                rows.append((path, ver))
            import json
            return True, json.dumps({"py": py_exe, "rows": rows})

        def _done(ok, result):
            import json, os
            if not ok:
                print(f"[TC] _done called with ok=False, result={result[:120]!r}")
                return
            try:
                data = json.loads(result)
                _py = data["py"]
                rows = data["rows"]
            except Exception as e:
                print(f"[TC] JSON parse error: {e!r}, result={result[:120]!r}")
                return
            print(f"[TC] _done: {len(rows)} rows loaded for {_py[:40]}")
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QTableWidgetItem
            import os as _os
            _py_scripts = _os.path.dirname(_py)  # Python's own Scripts/bin dir
            for row, item in enumerate(rows):
                path, ver = item[0], item[1]
                ok2 = bool(path)
                # Detect if tool is global (not in selected Python's Scripts dir)
                _is_global = (ok2 and
                    _py_scripts and
                    not path.lower().startswith(_py_scripts.lower()))
                # col 1: Status
                if ok2:
                    st_text = "🌐 Global" if _is_global else "✅ Installed"
                    st_color = "#89b4fa" if _is_global else "#a6e3a1"
                else:
                    st_text = "❌ Not found"
                    st_color = "#f38ba8"
                si = QTableWidgetItem(st_text)
                si.setForeground(QColor(st_color))
                si.setData(256, path)
                si.setData(257, _py)
                tbl.setItem(row, 1, si)

                # col 2: Version
                vi = QTableWidgetItem(ver if ok2 else "—")
                vi.setForeground(QColor(self._c()["fg"]))
                tbl.setItem(row, 2, vi)

                # col 3: Path
                pi = QTableWidgetItem(path if ok2 else "—")
                pi.setForeground(QColor(self._c()["fg_muted"]))
                pi.setToolTip(path)
                tbl.setItem(row, 3, pi)

                # Update action buttons
                self._tc_update_row_btns(tbl, row, ok2)

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do); w.finished.connect(_done); w.start()
        if not hasattr(self,"_tc_ws"): self._tc_ws=[]
        self._tc_ws.append(w)

    def _tc_do_install(self, tool, pkg, scope, tbl, row):
        import sys, os
        from PySide6.QtGui import QColor
        si = tbl.item(row, 1)
        py_exe = (si.data(257) if si else "") or ""
        if not py_exe and hasattr(self, "_tc_py_combo"):
            py_exe = self._tc_py_combo.currentData() or sys.executable
        if not py_exe:
            py_exe = sys.executable
        if si: si.setText("⏳ Installing..."); si.setForeground(QColor("#89b4fa"))

        # Pre-import subprocess_args outside worker thread
        try:
            from src.utils.platform_utils import subprocess_args as _spa_fn
        except Exception:
            _spa_fn = lambda: {}

        def _do(callback=None):
            import subprocess, time, shutil as _sh
            _spa = _spa_fn
            _is_win = sys.platform == "win32"
            _is_linux = sys.platform == "linux"
            _home = os.path.expanduser("~")

            # Build install command based on tool and scope
            # uv, poetry, pipx are standalone tools — install via pipx or pip --user
            _standalone = tool in ("uv", "poetry", "pipx")

            if _is_win:
                if scope == "system":
                    try:
                        import ctypes
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", py_exe, f"-m pip install {pkg} -q", None, 1)
                        if ret <= 32: return False, f"UAC failed ({ret})"
                        time.sleep(4)
                    except Exception as e:
                        return False, str(e)
                else:
                    # User install
                    r = subprocess.run(
                        [py_exe, "-m", "pip", "install", pkg, "--user", "-q"],
                        capture_output=True, text=True, timeout=120,
                        cwd=_home, **_spa())
                    if r.returncode != 0:
                        return False, (r.stderr or r.stdout or "failed")[:300]
            else:
                # Linux / macOS
                if scope == "system":
                    # Try pkexec pip install, then sudo pip install --break-system-packages
                    _pip_cmd = [py_exe, "-m", "pip", "install", pkg, "-q",
                                "--break-system-packages"]
                    _installed = False
                    for _sudo in (["pkexec"], ["sudo"]):
                        try:
                            r = subprocess.run(_sudo + _pip_cmd,
                                capture_output=True, text=True, timeout=120, cwd=_home)
                            if r.returncode == 0:
                                _installed = True
                                break
                        except FileNotFoundError:
                            continue
                    if not _installed:
                        return False, "System install failed — try User install instead"
                else:
                    # User install — prefer pipx for standalone tools
                    if _standalone and tool != "pipx":
                        # Install via pipx if available, else pip --user
                        _pipx = _sh.which("pipx")
                        if _pipx:
                            r = subprocess.run([_pipx, "install", pkg],
                                capture_output=True, text=True, timeout=120,
                                cwd=_home, **_spa())
                        else:
                            r = subprocess.run(
                                [py_exe, "-m", "pip", "install", pkg, "--user", "-q"],
                                capture_output=True, text=True, timeout=120,
                                cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    elif tool == "pipx":
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", "pipx", "--user", "-q"],
                            capture_output=True, text=True, timeout=120,
                            cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    else:
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", pkg, "--user", "-q"],
                            capture_output=True, text=True, timeout=120,
                            cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]

            # Post-install: ensurepath for pipx
            if tool == "pipx":
                _pipx2 = _sh.which("pipx") or (py_exe.replace("python", "pipx") if "python" in py_exe else "")
                if _pipx2:
                    try:
                        subprocess.run([_pipx2, "ensurepath"],
                            capture_output=True, timeout=30, cwd=_home)
                    except Exception:
                        pass
            return True, "ok"

        def _done(ok, res):
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QMessageBox
            si2 = tbl.item(row, 1)
            if not ok:
                if si2:
                    si2.setText(f"❌ Failed")
                    si2.setForeground(QColor("#f38ba8"))
                QMessageBox.warning(None, f"Install Failed — {tool}", str(res))
                return
            QTimer.singleShot(500, lambda: self._tc_load_table(py_exe))

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do); w.finished.connect(_done); w.start()
        if not hasattr(self, "_tc_ws"): self._tc_ws = []
        self._tc_ws.append(w)

    def _tc_do_remove(self, tool, pkg, scope, tbl, row):
        import sys, shutil as _shutil
        from PySide6.QtGui import QColor
        si = tbl.item(row, 1)
        py_exe = (si.data(257) if si else "") or ""
        if not py_exe and hasattr(self, "_tc_py_combo"):
            py_exe = self._tc_py_combo.currentData() or sys.executable
        if not py_exe: py_exe = sys.executable
        if si: si.setText("⏳ Removing..."); si.setForeground(QColor("#89b4fa"))
        _home = __import__("os").path.expanduser("~")

        def _do(callback=None):
            import subprocess, os
            from src.utils.platform_utils import subprocess_args
            # Build correct remove command per tool
            # Find the tool's own executable first
            _tool_exe = _shutil.which(tool) or _shutil.which(tool + ".exe")
            if tool == "uv":
                if not _tool_exe:
                    return False, "uv not found in PATH"
                cmd = [py_exe, "-m", "pip", "uninstall", "uv", "-y", "-q"]
            elif tool == "pipx":
                if not _tool_exe:
                    return False, "pipx not found in PATH"
                # pipx may be installed via pip or standalone
                # Try pip uninstall first, then inform user
                cmd = [py_exe, "-m", "pip", "uninstall", "pipx", "-y", "-q"]
            elif tool == "poetry":
                if not _tool_exe:
                    return False, "poetry not found in PATH"
                cmd = [py_exe, "-m", "pip", "uninstall", "poetry", "-y", "-q"]
            elif tool in ("pip", "venv"):
                return False, f"{tool} cannot be removed — it is a core Python component"
            elif tool == "micromamba":
                return False, "micromamba is a standalone binary — delete it manually from its install path"
            else:
                cmd = [py_exe, "-m", "pip", "uninstall", pkg, "-y", "-q"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                               cwd=_home, **subprocess_args())
            if r.returncode != 0:
                return False, (r.stderr or r.stdout)[:200]
            return True, f"{tool} removed successfully"

        def _done(ok, res):
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QMessageBox
            si2 = tbl.item(row, 1)
            if not ok:
                if si2:
                    si2.setText(f"❌ {res[:40]}")
                    si2.setForeground(QColor("#f38ba8"))
                QMessageBox.warning(None, "Remove Failed", res)
                return
            QTimer.singleShot(300, lambda: self._tc_load_table(py_exe))

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do); w.finished.connect(_done); w.start()
        if not hasattr(self, "_tc_ws"): self._tc_ws = []
        self._tc_ws.append(w)

    def _tc_do_verify(self, tool, tbl, row):
        import sys, subprocess
        from PySide6.QtWidgets import QMessageBox
        si = tbl.item(row, 1)
        exe = (si.data(256) if si else "") or ""
        py  = (si.data(257) if si else "") or sys.executable
        try:
            if tool == "venv":
                r = subprocess.run(
                    [py, "-c", "import venv, sys; print('venv OK - Python', sys.version.split()[0])"],
                    capture_output=True, text=True, timeout=8, cwd=__import__('os').path.expanduser('~'))
            elif tool == "pip":
                r = subprocess.run([py, "-m", "pip", "--version"],
                    capture_output=True, text=True, timeout=8, cwd=__import__('os').path.expanduser('~'))
            elif tool == "micromamba":
                # micromamba is a standalone binary, not a Python module
                mamba_exe = exe
                if not mamba_exe:
                    try:
                        from src.core.micromamba_installer import get_micromamba_exe
                        mamba_exe = str(get_micromamba_exe() or "")
                    except Exception:
                        pass
                if mamba_exe:
                    r = subprocess.run([mamba_exe, "--version"],
                        capture_output=True, text=True, timeout=8, cwd=__import__('os').path.expanduser('~'))
                else:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Not Found", "micromamba not installed. Use Download.")
                    return
            elif exe:
                r = subprocess.run([exe, "--version"],
                    capture_output=True, text=True, timeout=8, cwd=__import__('os').path.expanduser('~'))
            else:
                r = subprocess.run([py, "-m", tool, "--version"],
                    capture_output=True, text=True, timeout=8, cwd=__import__('os').path.expanduser('~'))
            out = (r.stdout or r.stderr).strip()
            if r.returncode == 0:
                QMessageBox.information(None, f"\u2705 {tool} OK",
                    f"{tool} is working correctly.\n\nOutput: {out}")
            else:
                QMessageBox.warning(None, f"\u274c {tool} Failed", out)
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))

    def _tc_do_default(self, tool, tbl, row):
        import os, sys
        from PySide6.QtWidgets import QMessageBox
        si = tbl.item(row,1)
        exe = (si.data(256) if si else "") or ""
        if not exe:
            QMessageBox.warning(None,"Not Installed",
                f"{tool} is not installed. Install it first.")
            return
        scripts_dir = os.path.dirname(exe)
        if sys.platform=="win32":
            try:
                import winreg,ctypes
                key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Environment",0,winreg.KEY_ALL_ACCESS)
                try: curr,_=winreg.QueryValueEx(key,"PATH")
                except FileNotFoundError: curr=""
                if scripts_dir.lower() not in curr.lower():
                    new_p=curr+";"+scripts_dir if curr else scripts_dir
                    winreg.SetValueEx(key,"PATH",0,winreg.REG_EXPAND_SZ,new_p)
                    ctypes.windll.user32.SendMessageTimeoutW(
                        0xFFFF,0x001A,0,"Environment",0,5000,None)
                    QMessageBox.information(None,"✅ PATH Updated",
                        f"Added to user PATH:\n{scripts_dir}\n\n"
                        "Restart terminal to apply.")
                else:
                    QMessageBox.information(None,"Already in PATH",
                        f"{scripts_dir}\nis already in PATH.")
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(None,"Error",f"Failed:\n{e}")
        else:
            QMessageBox.information(None,"Manual Step Required",
                f"Add to ~/.bashrc or ~/.zshrc:\n\nexport PATH=\"{scripts_dir}:$PATH\"")

    def _tc_download_mamba(self, tbl, row):
        from PySide6.QtGui import QColor
        si=tbl.item(row,1)
        if si: si.setText("⏳ Downloading..."); si.setForeground(QColor("#89b4fa"))
        def _do(callback=None):
            try:
                from src.core.micromamba_installer import download_micromamba
                p=download_micromamba(progress_cb=callback)
                return True,str(p)
            except Exception as e: return False,str(e)
        def _done(ok,res):
            si=tbl.item(row,1)
            if not si: return
            from PySide6.QtGui import QColor; from PySide6.QtWidgets import QTableWidgetItem
            if ok:
                si.setText("✅ Installed"); si.setForeground(QColor("#a6e3a1"))
                pi=tbl.item(row,3)
                if pi: pi.setText(res)
            else:
                si.setText(f"❌ {res[:40]}"); si.setForeground(QColor("#f38ba8"))
        from src.gui.package_panel import WorkerThread
        w=WorkerThread(_do); w.finished.connect(_done); w.start()
        if not hasattr(self,"_tc_ws"): self._tc_ws=[]
        self._tc_ws.append(w)


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

    def _c(self) -> dict:
        """Return current theme color palette."""
        from src.gui.styles import get_colors
        p = self.parent()
        if p and hasattr(p, "config"):
            return get_colors(p.config.get("theme", "dark"))
        return get_colors("dark")

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
            "Download standalone Python builds for local use"
        )
        header.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        header.setWordWrap(True)
        layout.addWidget(header)

        # Version list
        self.version_list = QListWidget()
        self.version_list.setStyleSheet(
            f"QListWidget {{ font-size: {self._c()['fs_base']}px; }}"
            f"QListWidget::item {{ padding: 6px; }}"
            f"QListWidget::item:selected {{ background-color: {self._c()['accent']}; color: {self._c()['accent_fg']}; }}"
        )
        layout.addWidget(self.version_list)

        # Progress
        self.progress_label = QLabel("Fetching available versions...")
        self.progress_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Install locations
        import os as _os
        from src.core.python_downloader import get_pythons_dir
        user_dir = get_pythons_dir()
        if _os.name == "nt":
            system_dir = _os.path.join(_os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Python")
        else:
            system_dir = "/usr/local/bin"
        loc_label = QLabel(
            f"🖥️ System location: {system_dir}\n"
            f"👤 User location: {user_dir}"
        )
        loc_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
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
                item.setForeground(QColor(self._c()['success']))
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

        # ── LAUNCH SETTINGS ──
        launch_group = QGroupBox("🚀 Launch Settings")
        launch_layout = QFormLayout()
        launch_layout.setSpacing(12)

        # Jupyter Working Directory — protected by checkbox
        jupyter_dir_row = QHBoxLayout()
        self.jupyter_workdir_cb = QCheckBox()
        self.jupyter_workdir_cb.setChecked(False)
        self.jupyter_workdir_cb.toggled.connect(lambda on: self.jupyter_workdir_combo.setEnabled(on))
        jupyter_dir_row.addWidget(self.jupyter_workdir_cb)

        self.jupyter_workdir_combo = NoScrollComboBox()
        self.jupyter_workdir_combo.addItem("🏠 Home Directory", "home")
        self.jupyter_workdir_combo.addItem("📁 Environment Folder", "env")
        self.jupyter_workdir_combo.addItem("📂 Custom Path...", "custom")
        self.jupyter_workdir_combo.setEnabled(False)
        self.jupyter_workdir_combo.currentIndexChanged.connect(self._on_jupyter_workdir_changed)
        jupyter_dir_row.addWidget(self.jupyter_workdir_combo, 1)

        self.jupyter_custom_path_btn = QPushButton("📂")
        self.jupyter_custom_path_btn.setFixedWidth(36)
        self.jupyter_custom_path_btn.setToolTip("Pick custom folder")
        self.jupyter_custom_path_btn.setEnabled(False)
        self.jupyter_custom_path_btn.clicked.connect(self._pick_jupyter_workdir)
        jupyter_dir_row.addWidget(self.jupyter_custom_path_btn)

        launch_layout.addRow("Jupyter Working Dir:", jupyter_dir_row)

        self.jupyter_custom_path_label = QLabel("")
        self.jupyter_custom_path_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self.jupyter_custom_path_label.setVisible(False)
        launch_layout.addRow("", self.jupyter_custom_path_label)

        launch_group.setLayout(launch_layout)
        layout.addWidget(launch_group)
        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── SAVE / RESET BUTTONS (scroll dışında, üstte sabit) ──
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(12, 6, 12, 6)

        save_btn = QPushButton(f"  💾 {tr('save_settings')}  ")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()

        reset_all_btn = QPushButton(tr("reset_defaults"))
        reset_all_btn.setObjectName("danger")
        reset_all_btn.clicked.connect(self._reset_all)
        btn_layout.addWidget(reset_all_btn)

        main_layout.addLayout(btn_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {self._c()['border']}; max-height: 1px;")
        main_layout.addWidget(sep)

        main_layout.addWidget(scroll)

    # ── CLI/TUI Tools helpers ─────────────────────────────────────────────────


    def _on_theme_cb_toggled(self, on):
        """Enable/disable theme combo and apply theme live."""
        self.theme_combo.setEnabled(on)
        if on:
            self._on_theme_live_preview()
        else:
            # Checkbox unchecked → revert to dark
            self.config.set("theme", "dark")
            self.theme_changed.emit("dark")

    def _on_theme_live_preview(self, _idx=None):
        """Apply theme instantly when dropdown changes — no Save needed."""
        if not self.theme_cb.isChecked():
            return
        theme = self.theme_combo.currentData()
        if theme:
            self.config.set("theme", theme)
            self.theme_changed.emit(theme)
            self._refresh_styles()

    def _cli_log_append(self, text: str):
        import html as _html
        c = self._c()
        for line in text.split("\n"):
            t = line.strip()
            if not t:
                continue
            escaped = _html.escape(t)
            if t.startswith("✅"):
                color = c['success']
            elif t.startswith("❌"):
                color = c['danger']
            elif t.startswith("⬇️") or t.startswith("📦"):
                color = c['accent']
            elif t.startswith("⚠️"):
                color = c.get('warning', '#f9e2af')
            else:
                color = c['fg']
            self.cli_log.append(f'<span style="color:{color};">{escaped}</span>')

    def _make_cli_card(self, tool_id, title, desc, preset_label, presets, preset_key,
                        preset_descriptions=None):
        """Create a card widget for binary CLI tools (starship, oh-my-posh)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"cli_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Title + status
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"\u2705 {version}" if installed else "\u274c Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        status_lbl.setObjectName(f"status_{tool_id.replace('-','_')}")
        header.addWidget(status_lbl)
        header.addStretch()
        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Preset selector + buttons
        controls = QHBoxLayout()
        controls.setSpacing(6)

        cb_key = f"cb_preset_{tool_id.replace('-','_')}"
        preset_cb = QCheckBox(preset_label)
        preset_cb.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg']};")
        preset_cb.setObjectName(cb_key)
        controls.addWidget(preset_cb)

        combo = QComboBox()
        combo.setMaximumWidth(200)
        for p in presets:
            label = p
            if preset_descriptions and p in preset_descriptions:
                label = f"{p}  \u2014  {preset_descriptions[p]}"
            combo.addItem(label, p)
        combo.setObjectName(f"preset_{tool_id.replace('-','_')}")
        combo.setEnabled(False)
        preset_cb.toggled.connect(combo.setEnabled)
        controls.addWidget(combo)

        # Preset description label (updates on selection)
        desc_hint = None
        if preset_descriptions:
            desc_hint = QLabel("")
            desc_hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic;")
            desc_hint.setFixedHeight(16)

            def _update_preset_hint(idx, _dh=desc_hint, _c=combo, _pd=preset_descriptions):
                key = _c.itemData(idx)
                if key and key in _pd:
                    _dh.setText(_pd[key])
                else:
                    _dh.setText("")

            combo.currentIndexChanged.connect(_update_preset_hint)
            _update_preset_hint(0)

        controls.addStretch()

        install_btn = QPushButton("\u2b07\ufe0f Install" if not installed else "\U0001f504 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        controls.addWidget(install_btn)

        if installed:
            cfg_btn = QPushButton("\u2699\ufe0f Configure Shell")
            cfg_btn.setObjectName("secondary")
            cfg_btn
            cfg_btn.clicked.connect(lambda _, t=tool_id, c=combo, pk=preset_key: self._cli_configure(t, c, pk))
            controls.addWidget(cfg_btn)

            # Starship-specific: Edit Config + Test buttons
            if tool_id == "starship":
                edit_btn = QPushButton("\U0001f4dd Edit Config")
                edit_btn.setObjectName("secondary")
                edit_btn
                edit_btn.setToolTip("Open starship.toml inline editor")
                edit_btn.clicked.connect(self._open_starship_editor)
                controls.addWidget(edit_btn)

                test_btn = QPushButton("\u25b6\ufe0f Test")
                test_btn.setObjectName("secondary")
                test_btn
                test_btn.setToolTip("Open a terminal to test your Starship prompt")
                test_btn.clicked.connect(self._test_starship_in_terminal)
                controls.addWidget(test_btn)

            uninst_btn = QPushButton("\U0001f5d1\ufe0f Uninstall")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            controls.addWidget(uninst_btn)

        layout.addLayout(controls)

        # Preset description below controls
        if desc_hint:
            layout.addWidget(desc_hint)

        return card

    def _make_pip_card(self, tool_id, title, desc):
        """Create a card widget for pip-based tools (rich, textual, prompt_toolkit)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"pip_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        header.addWidget(status_lbl)
        header.addStretch()

        install_btn = QPushButton("⬇️ Install" if not installed else "🔄 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        header.addWidget(install_btn)

        if installed:
            uninst_btn = QPushButton("🗑️")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.setMinimumWidth(32)
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            header.addWidget(uninst_btn)

        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(desc_lbl)
        return card

    def _cli_install(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        btn.setEnabled(False)
        btn.setText("⏳ Installing...")
        self.cli_log.clear()
        self._cli_worker = CliToolWorker("install", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_uninstall(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        reply = QMessageBox.question(self, "Uninstall", f"Uninstall {tool_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._cli_worker = CliToolWorker("uninstall", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_configure(self, tool_id, combo, preset_key):
        from src.core.cli_tools_manager import CliToolWorker
        theme = combo.currentData() or combo.currentText()
        self._cli_worker = CliToolWorker("configure", tool_id, {preset_key: theme}, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()


    def _open_starship_editor(self):
        """Open inline editor for starship.toml."""
        from src.core.cli_tools_manager import read_starship_toml, write_starship_toml, get_starship_toml_path
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel, QMessageBox
        from PySide6.QtGui import QFont

        dlg = QDialog(self)
        dlg.setWindowTitle("📝 Starship Config Editor — starship.toml")
        dlg.resize(700, 500)
        dlg.setStyleSheet(
            f"QDialog {{ background: {self._c()['bg']}; }}"
            f"QPlainTextEdit {{ background: {self._c()['sidebar']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"border-radius: 4px; font-family: 'Consolas', 'JetBrains Mono', monospace; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton {{ padding: 6px 16px; border-radius: 4px; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton#save {{ background: {self._c()['success']}; color: {self._c()['accent_fg']}; font-weight: bold; }}"
            "QPushButton#save:hover { background: #94d89d; }"
            f"QPushButton#secondary {{ background: {self._c()['secondary']}; color: {self._c()['fg']}; }}"
            "QPushButton#secondary:hover { background: #45475a; }"
            f"QLabel {{ color: #6c7086; font-size: {self._c()['fs_tiny']}px; }}"
        )

        layout = QVBoxLayout(dlg)

        path_label = QLabel(f"📂 {get_starship_toml_path()}")
        layout.addWidget(path_label)

        editor = QPlainTextEdit()
        editor.setFont(QFont("Consolas", 12))
        editor.setPlainText(read_starship_toml())
        editor.setTabStopDistance(28)
        layout.addWidget(editor)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.setObjectName("secondary")
        reload_btn.clicked.connect(lambda: editor.setPlainText(read_starship_toml()))
        btn_row.addWidget(reload_btn)

        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setObjectName("secondary")
        open_folder_btn.clicked.connect(lambda: __import__("subprocess").Popen(
            ["explorer" if __import__("sys").platform == "win32" else "xdg-open",
             str(get_starship_toml_path().parent)]
        ))
        btn_row.addWidget(open_folder_btn)

        save_btn = QPushButton("💾 Save")
        save_btn.setObjectName("save")
        def _do_save():
            if write_starship_toml(editor.toPlainText()):
                self._cli_log_append("✅ starship.toml saved")
                QMessageBox.information(dlg, "Saved", "starship.toml saved successfully! ✅\n\nOpen a new terminal to see changes.")
            else:
                QMessageBox.critical(dlg, "Error", "Failed to save starship.toml")
        save_btn.clicked.connect(_do_save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        dlg.exec()

    def _test_starship_in_terminal(self):
        """Open a terminal so user can see their Starship prompt in action."""
        import sys as _sys
        from src.core.cli_tools_manager import is_tool_installed
        if not is_tool_installed("starship"):
            QMessageBox.warning(self, "Starship", "Starship is not installed.")
            return
        try:
            if _sys.platform == "win32":
                import subprocess
                # Open PowerShell with starship init
                subprocess.Popen(
                    ["powershell", "-NoExit", "-Command",
                     "Invoke-Expression (&starship init powershell)"],
                    creationflags=0x00000010  # CREATE_NEW_CONSOLE
                )
            elif _sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal"])
            else:
                import subprocess
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    import shutil
                    if shutil.which(term):
                        subprocess.Popen([term])
                        break
            self._cli_log_append("✅ Terminal opened — check your Starship prompt!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open terminal:\n{e}")

    def _cli_done(self, ok, msg, btn, status_lbl, tool_id):
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        self._cli_log_append(msg)
        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl.setText(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        btn.setEnabled(True)
        btn.setText("🔄 Reinstall" if installed else "⬇️ Install")

    def _install_nerd_font(self):
        from src.core.cli_tools_manager import CliToolWorker
        if not self.nerd_font_cb.isChecked():
            QMessageBox.information(self, "Info", "Enable the Font checkbox first to select a font.")
            return
        font_id   = self.nerd_font_combo.currentData()
        font_name = self.nerd_font_combo.currentText()
        self.cli_log.clear()
        self._cli_worker = CliToolWorker(
            "install_font", "font",
            {"font_id": font_id, "font_name": font_name},
            parent=self
        )
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()

    def _verify_pip_venv(self):
        """Check pip and venv for selected Python, offer to fix if missing."""
        import os, subprocess
        from src.utils.platform_utils import subprocess_args as sp_args, get_platform

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()
        is_windows = get_platform() == "windows"
        scripts_dir = os.path.join(os.path.dirname(python_path), "Scripts" if is_windows else "bin")


        # ── pip check ──
        pip_version_str = ""
        pip_runnable = False
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "--version"],
                **sp_args(capture_output=True, text=True, timeout=10, cwd=__import__('os').path.expanduser('~'))
            )
            if result.returncode == 0:
                pip_runnable = True
                pip_version_str = result.stdout.strip()
        except Exception:
            pass

        # ── venv check ──
        venv_available = False
        try:
            result = subprocess.run(
                [python_path, "-c", "import venv; print(venv.__name__)"],
                **sp_args(capture_output=True, text=True, timeout=10, cwd=__import__('os').path.expanduser('~'))
            )
            if result.returncode == 0 and "venv" in result.stdout:
                venv_available = True
        except Exception:
            pass

        current_path = os.environ.get("PATH", "")
        scripts_in_path = scripts_dir.lower() in current_path.lower()

        pip_status = "✅ Working" if pip_runnable else "❌ Not working"
        venv_status = "✅ Available" if venv_available else "❌ Not available"
        path_status = "✅ Yes" if scripts_in_path else "⚠️ Not in current session"

        msg = (
            f"Python: {version}\n"
            f"Path:   {python_path}\n\n"
            f"pip:              {pip_status}\n"
            f"venv:            {venv_status}\n"
            f"Scripts in PATH: {path_status}"
        )
        if pip_runnable and pip_version_str:
            msg += "\n\n" + pip_version_str

        issues = []
        if not pip_runnable:
            issues.append("pip is not working — python -m pip failed.")
        if not venv_available:
            if is_windows:
                issues.append("venv module not available — try reinstalling Python with 'pip' option enabled.")
            else:
                issues.append("venv module not available — install python3-venv:\n"
                              "    Debian/Ubuntu: sudo apt install python3-venv\n"
                              "    Arch: included in python package")
        if not scripts_in_path:
            issues.append("Scripts folder not in current PATH — open a new terminal after Set Default.")

        if issues:
            msg += "\n\nIssues found:\n" + "\n".join("  * " + i for i in issues)
            fix_actions = []
            if not pip_runnable:
                fix_actions.append("reinstall pip")
            if not venv_available and not is_windows:
                fix_actions.append("install python3-venv (requires sudo)")

            if fix_actions:
                msg += "\n\nWould you like to fix now? (" + ", ".join(fix_actions) + ")"
                reply = QMessageBox.question(self, "pip & venv Status", msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if not pip_runnable:
                        self._fix_pip(python_path, version)
                    if not venv_available and not is_windows:
                        self._fix_venv()
            else:
                QMessageBox.warning(self, "pip & venv Status", msg)
        else:
            QMessageBox.information(self, "✅ pip & venv OK", msg)

    def _fix_venv(self):
        """Attempt to install python3-venv on Linux."""
        import subprocess, shutil
        if shutil.which("apt"):
            cmd = "sudo apt install -y python3-venv"
        elif shutil.which("pacman"):
            QMessageBox.information(self, "venv", "On Arch, venv is included in the python package.\nTry: sudo pacman -S python")
            return
        elif shutil.which("dnf"):
            cmd = "sudo dnf install -y python3-venv"
        else:
            QMessageBox.information(self, "venv", "Please install python3-venv using your package manager.")
            return
        try:
            subprocess.Popen(["sh", "-c", f"x-terminal-emulator -e '{cmd}' || xterm -e '{cmd}'"])
        except Exception as e:
            QMessageBox.warning(self, "venv Install", f"Could not start terminal:\n{e}\n\nRun manually: {cmd}")

    def _fix_pip(self, python_path, version):
        """Reinstall pip for the given Python executable."""
        import subprocess
        from src.utils.platform_utils import subprocess_args as sp_args

        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pip"],
                **sp_args(capture_output=True, text=True, timeout=60, cwd=__import__('os').path.expanduser('~'))
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "pip Fixed",
                    "pip reinstalled for Python " + version + "!\n\n"
                    "Open a new terminal and run: pip --version"
                )
            else:
                err = result.stderr.strip() or result.stdout.strip()
                QMessageBox.critical(
                    self, "pip Fix Failed",
                    "Could not reinstall pip.\n\n" + err + "\n\n"
                    "Try manually (as admin):\n"
                    '  "' + python_path + '" -m pip install --upgrade --force-reinstall pip'
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to run pip fix:\n" + str(e))
        self._scan_pythons()

    def _set_python_default_unix(self, version, python_path, scope):
        """Set default Python on Linux/macOS using update-alternatives or symlinks."""
        import subprocess, shutil

        platform = get_platform()
        ver_short = ".".join(version.split(".")[:2])  # e.g. "3.12"
        ver_nodot = ver_short.replace(".", "")          # e.g. "312"

        if platform == "linux":
            # Use update-alternatives if available
            if shutil.which("update-alternatives"):
                priority = 100

                reply = QMessageBox.question(
                    self, f"Set Default Python",
                    f"Register Python {version} as system default?\n\n"
                    f"  python3   → {python_path}\n"
                    f"  python3.{ver_short.split('.')[-1]} → {python_path}\n\n"
                    f"Uses update-alternatives (requires admin password).",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                cmds = [
                    ["update-alternatives", "--install",
                     "/usr/bin/python3", "python3", python_path, str(priority)],
                    ["update-alternatives", "--install",
                     "/usr/bin/python", "python", python_path, str(priority)],
                    ["update-alternatives", "--set", "python3", python_path],
                    ["update-alternatives", "--set", "python", python_path],
                ]

                success = True
                for cmd in cmds:
                    for sudo in [["pkexec"], ["sudo"]]:
                        try:
                            r = subprocess.run(
                                sudo + cmd,
                                capture_output=True, text=True, timeout=30
                            )
                            if r.returncode == 0:
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    else:
                        success = False
                        break

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Python {version} set as system default!\n\n"
                        f"Verify with:  python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not set default Python.\n\n"
                        f"Try manually:\n"
                        f"  sudo update-alternatives --install /usr/bin/python3 python3 {python_path} 100\n"
                        f"  sudo update-alternatives --set python3 {python_path}"
                    )
            else:
                # No update-alternatives — create symlink in /usr/local/bin
                reply = QMessageBox.question(
                    self, "Set Default Python",
                    f"Create symlinks for Python {version}?\n\n"
                    f"  /usr/local/bin/python3  → {python_path}\n"
                    f"  /usr/local/bin/python   → {python_path}\n\n"
                    f"Requires admin password.",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                script = (
                    f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                    f"ln -sf '{python_path}' /usr/local/bin/python"
                )
                success = False
                for sudo in [["pkexec", "bash", "-c"], ["sudo", "bash", "-c"]]:
                    try:
                        r = subprocess.run(sudo + [script], capture_output=True, text=True, timeout=30, cwd=__import__('os').path.expanduser('~'))
                        if r.returncode == 0:
                            success = True
                            break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not create symlinks.\n\nTry manually:\n"
                        f"  sudo ln -sf {python_path} /usr/local/bin/python3"
                    )

        elif platform == "macos":
            # macOS: symlink in /usr/local/bin
            reply = QMessageBox.question(
                self, "Set Default Python",
                f"Create symlinks for Python {version}?\n\n"
                f"  /usr/local/bin/python3  → {python_path}\n"
                f"  /usr/local/bin/python   → {python_path}\n\n"
                f"Requires admin password.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            script = (
                f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                f"ln -sf '{python_path}' /usr/local/bin/python"
            )
            try:
                r = subprocess.run(
                    ["osascript", "-e",
                     f'do shell script "{script}" with administrator privileges'],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(self, "❌ Failed", f"Could not create symlinks:\n{r.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_custom_terminals(self):
        """Load custom terminals from config into table."""
        terminals = self.config.get("custom_terminals", [])
        self.custom_term_table.setRowCount(0)
        for t in terminals:
            row = self.custom_term_table.rowCount()
            self.custom_term_table.insertRow(row)
            self.custom_term_table.setItem(row, 0, QTableWidgetItem(t.get("name", "")))
            self.custom_term_table.setItem(row, 1, QTableWidgetItem(t.get("command", "")))
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked if t.get("enabled", True) else Qt.Unchecked)
            self.custom_term_table.setItem(row, 2, chk)
            # Also add to terminal_combo if enabled
            if t.get("enabled", True):
                name = t.get("name", "")
                if self.terminal_combo.findData(f"custom:{name}") < 0:
                    self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _save_custom_terminals(self):
        """Save custom terminals from table to config."""
        terminals = []
        for row in range(self.custom_term_table.rowCount()):
            name = self.custom_term_table.item(row, 0).text() if self.custom_term_table.item(row, 0) else ""
            cmd = self.custom_term_table.item(row, 1).text() if self.custom_term_table.item(row, 1) else ""
            chk = self.custom_term_table.item(row, 2)
            enabled = chk.checkState() == Qt.Checked if chk else True
            if name and cmd:
                terminals.append({"name": name, "command": cmd, "enabled": enabled})
        self.config.set("custom_terminals", terminals)

    def _add_custom_terminal(self):
        """Add a new custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. My Terminal")
        cmd_edit = QLineEdit()
        cmd_edit.setPlaceholderText('e.g. wt -d "{path}" cmd /k "{activate}"')

        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")

        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            cmd = cmd_edit.text().strip()
            if name and cmd:
                row = self.custom_term_table.rowCount()
                self.custom_term_table.insertRow(row)
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(cmd))
                chk = QTableWidgetItem()
                chk.setCheckState(Qt.Checked)
                self.custom_term_table.setItem(row, 2, chk)
                # Add to combo
                self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _edit_custom_terminal(self):
        """Edit selected custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a terminal to edit.")
            return
        old_name = self.custom_term_table.item(row, 0).text()
        old_cmd = self.custom_term_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        cmd_edit = QLineEdit(old_cmd)
        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            new_name = name_edit.text().strip()
            new_cmd = cmd_edit.text().strip()
            if new_name and new_cmd:
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(new_name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(new_cmd))
                # Update combo
                idx = self.terminal_combo.findData(f"custom:{old_name}")
                if idx >= 0:
                    self.terminal_combo.setItemText(idx, f"⚡ {new_name}")
                    self.terminal_combo.setItemData(idx, f"custom:{new_name}")

    def _remove_custom_terminal(self):
        """Remove selected custom terminal."""
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a terminal to remove.")
            return
        name = self.custom_term_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Terminal",
            f"Remove '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_term_table.removeRow(row)
            idx = self.terminal_combo.findData(f"custom:{name}")
            if idx >= 0:
                self.terminal_combo.removeItem(idx)

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

        # Font — 3-level system load
        _font_defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        _sys_fonts = ("", "Segoe UI", "Yu Gothic UI", "MS Shell Dlg 2", "Arial", "Tahoma")
        for level_id, (def_family, def_size) in _font_defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            saved_family = self.config.get(f"font_{level_id}_family", "")
            saved_size = self.config.get(f"font_{level_id}_size", def_size)
            if saved_family and saved_family not in _sys_fonts:
                cb.setChecked(True)
                combo.setEnabled(True)
                combo.setCurrentFont(QFont(saved_family))
                spin.setEnabled(True)
                spin.setValue(saved_size)
            elif saved_size != def_size and saved_size > 0:
                cb.setChecked(True)
                combo.setEnabled(True)
                spin.setEnabled(True)
                spin.setValue(saved_size)
            else:
                cb.setChecked(False)
                combo.setEnabled(False)
                spin.setEnabled(False)
                spin.setValue(def_size)

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

        # Default environment type
        if hasattr(self, "default_env_type_combo"):
            default_et = self.config.get("default_env_type", "venv")
            et_idx = self.default_env_type_combo.findData(default_et)
            if et_idx >= 0:
                self.default_env_type_combo.setCurrentIndex(et_idx)
            is_custom_et = bool(default_et and default_et != "venv")
            if hasattr(self, "default_env_type_cb"):
                self.default_env_type_cb.setChecked(is_custom_et)
                self.default_env_type_combo.setEnabled(is_custom_et)

        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb") and hasattr(self, "_tc_py_combo"):
            tc_py_on = self.config.get("tc_py_cb_checked", False)
            self._tc_py_cb.setChecked(tc_py_on)
            self._tc_py_combo.setEnabled(tc_py_on)

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

        # Load custom terminals into table and combo
        self._load_custom_terminals()

        # Load custom presets
        self._load_custom_presets()

        # Scan pythons
        self._scan_pythons()

        # Load custom categories
        self._load_custom_categories()

        # Load custom catalog
        self._load_custom_catalog()

        # Jupyter working dir
        jwd = self.config.get("jupyter_workdir", "home")
        jwd_custom = self.config.get("jupyter_workdir_custom", "")
        idx_jwd = self.jupyter_workdir_combo.findData(jwd)
        if idx_jwd >= 0:
            self.jupyter_workdir_combo.setCurrentIndex(idx_jwd)
        if jwd != "home":
            self.jupyter_workdir_cb.setChecked(True)
            self.jupyter_workdir_combo.setEnabled(True)
        if jwd == "custom" and jwd_custom:
            self.jupyter_custom_path_label.setText(jwd_custom)
            self.jupyter_custom_path_label.setVisible(True)
            self.jupyter_custom_path_btn.setEnabled(True)

    def _on_jupyter_workdir_changed(self, idx):
        """Enable/disable custom path button based on selection."""
        data = self.jupyter_workdir_combo.currentData()
        is_custom = data == "custom" and self.jupyter_workdir_cb.isChecked()
        self.jupyter_custom_path_btn.setEnabled(is_custom)
        self.jupyter_custom_path_label.setVisible(is_custom)

    def _pick_jupyter_workdir(self):
        """Open folder picker for custom Jupyter working directory."""
        import os
        current = self.jupyter_custom_path_label.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Jupyter Working Directory", current)
        if folder:
            self.jupyter_custom_path_label.setText(folder)
            self.jupyter_custom_path_label.setVisible(True)

    def _scan_pythons(self):
        """Scan system for Python installations."""
        import os
        import shutil
        self.python_table.setRowCount(0)
        self.default_python_combo.clear()
        self.default_python_combo.addItem("System Default", "")

        excluded_pythons = {
            os.path.normcase(os.path.normpath(p))
            for p in self.config.get("excluded_pythons", [])
        }

        # Which Python is system default — detect from PATH directly (registry on Windows)
        default_norm = ""
        try:
            if os.name == "nt":
                import subprocess as _sp
                _CNW = 0x08000000  # CREATE_NO_WINDOW
                # Read System PATH from registry (fresh, not cached process env)
                sys_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'Machine')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                usr_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                # User PATH takes priority (prepended by Set Default)
                for p in (usr_path + ";" + sys_path).split(";"):
                    p = p.strip()
                    if not p:
                        continue
                    candidate = os.path.join(p, "python.exe")
                    if os.path.isfile(candidate) and "windowsapps" not in p.lower():
                        default_norm = os.path.normcase(os.path.normpath(candidate))
                        break
            else:
                import shutil
                exe = shutil.which("python") or shutil.which("python3") or ""
                default_norm = os.path.normcase(os.path.normpath(exe)) if exe else ""
        except Exception:
            # Fallback: use saved config value
            saved_default = self.config.get("system_default_python", "")
            default_norm = os.path.normcase(os.path.normpath(saved_default)) if saved_default else ""

        # All pythons from system scan — deduplicate symlinks
        system_pythons = find_system_pythons()
        listed_paths = set()
        c = self._c()

        # ── System Default Python'u tabloya garanti olarak ilk satıra ekle ──
        if default_norm and os.path.isfile(default_norm):
            try:
                import subprocess as _sp
                result = _sp.run(
                    [default_norm, "--version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000 if __import__('os').name == "nt" else 0
                )
                sys_version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                sys_version = "?"
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(sys_version))
            _dn_norm = os.path.normpath(default_norm)
            if len(_dn_norm) >= 2 and _dn_norm[1] == ":":
                _dn_norm = _dn_norm[0].upper() + _dn_norm[1:]
            self.python_table.setItem(row, 1, QTableWidgetItem(_dn_norm))
            source_item = QTableWidgetItem("System Default")
            source_item.setForeground(QColor(c['success']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {sys_version} (System Default)", _dn_norm)
            listed_paths.add(default_norm)

        # Resolve symlinks: group by real binary, keep shortest path
        seen_real = {}  # realpath -> (version, norm_path)
        for version, path in system_pythons:
            norm_path = os.path.normpath(path)
            norm_case = os.path.normcase(norm_path)
            if norm_case in excluded_pythons:
                continue
            try:
                real = os.path.realpath(path)
            except OSError:
                real = norm_path
            if real in seen_real:
                # Keep the shorter/cleaner path (e.g. /usr/bin/python over /usr/bin/python3.14)
                existing = seen_real[real]
                if len(norm_path) < len(existing[1]):
                    seen_real[real] = (version, norm_path)
            else:
                seen_real[real] = (version, norm_path)

        for _real, (version, norm_path) in seen_real.items():
            norm_case = os.path.normcase(norm_path)
            if norm_case in listed_paths:
                continue
            listed_paths.add(norm_case)

            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            if len(norm_path) >= 2 and norm_path[1] == ":":
                norm_path = norm_path[0].upper() + norm_path[1:]
            self.python_table.setItem(row, 0, QTableWidgetItem(version))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))

            # Source label: System / User Install / Custom
            import os as _os
            import sys as _sys
            _home = _os.path.expanduser("~").lower()
            _localappdata = _os.environ.get("LOCALAPPDATA", "").lower()
            _appdata = _os.environ.get("APPDATA", "").lower()
            _progfiles = _os.environ.get("PROGRAMFILES", "C:\\Program Files").lower()
            _progfiles86 = _os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)").lower()
            _windir = _os.environ.get("WINDIR", "C:\\Windows").lower()
            _norm_lower = norm_path.lower()

            _this_exe = _os.path.normcase(_os.path.normpath(_sys.executable)).lower()
            _is_this_python = (_os.path.normcase(norm_path).lower() == _this_exe)

            if _is_this_python and getattr(_sys, "frozen", False):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_progfiles and _norm_lower.startswith(_progfiles)) or
                (_progfiles86 and _norm_lower.startswith(_progfiles86)) or
                (_windir and _norm_lower.startswith(_windir)) or
                "/usr/" in _norm_lower or
                "/opt/" in _norm_lower or
                _norm_lower.startswith("/bin/") or
                _norm_lower.startswith("/usr/bin/")
            ):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_home and _norm_lower.startswith(_home)) or
                (_localappdata and _norm_lower.startswith(_localappdata)) or
                (_appdata and _norm_lower.startswith(_appdata)) or
                "/.local/" in _norm_lower or
                "/.pyenv/" in _norm_lower or
                "/home/" in _norm_lower
            ):
                source_item = QTableWidgetItem("User Install")
                source_item.setForeground(QColor(c['accent']))
            else:
                source_item = QTableWidgetItem("Custom")
                source_item.setForeground(QColor(c['fg_muted']))

            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {version}", norm_path)

        # Custom pythons from config (skip already listed)
        custom_pythons = self.config.get("custom_pythons", [])
        cleaned_custom = []
        for entry in custom_pythons:
            norm_path = os.path.normpath(entry.get("path", ""))
            norm_case = os.path.normcase(norm_path)
            if norm_case in listed_paths:
                continue  # already shown above
            cleaned_custom.append(entry)
            listed_paths.add(norm_case)
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(entry.get("version", "?")))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))
            source_item = QTableWidgetItem("Custom")
            source_item.setForeground(QColor(c['accent']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(
                f"Python {entry.get('version', '?')} (Custom)", norm_path
            )

        if len(cleaned_custom) != len(custom_pythons):
            self.config.set("custom_pythons", cleaned_custom)

        # Standalone (downloaded) Pythons
        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                if os.path.normcase(exe_path) in listed_paths:
                    continue
                listed_paths.add(os.path.normcase(exe_path))
                row = self.python_table.rowCount()
                self.python_table.insertRow(row)
                self.python_table.setItem(row, 0, QTableWidgetItem(py["version"]))
                self.python_table.setItem(row, 1, QTableWidgetItem(exe_path))
                source_item = QTableWidgetItem("Downloaded")
                source_item.setForeground(QColor(c['success']))
                self.python_table.setItem(row, 2, source_item)
                self.default_python_combo.addItem(
                    f"Python {py['version']} (Downloaded)", exe_path
                )
        except Exception:
            pass

        # Set default python combo selection
        default_py = self.config.get("default_python", "")
        if default_py and default_py.strip():
            default_py_norm = os.path.normpath(default_py)
            found_idx = -1
            for i in range(self.default_python_combo.count()):
                item_data = self.default_python_combo.itemData(i) or ""
                if item_data and os.path.normpath(item_data).lower() == default_py_norm.lower():
                    found_idx = i
                    break
            if found_idx > 0:
                self.default_py_cb.setChecked(True)
                self.default_python_combo.setEnabled(True)
                self.default_python_combo.setCurrentIndex(found_idx)
            else:
                self.default_py_cb.setChecked(False)
                self.default_python_combo.setEnabled(False)
                self.default_python_combo.setCurrentIndex(0)
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
                **sp_args(capture_output=True, text=True, timeout=5, cwd=__import__('os').path.expanduser('~'))
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
        """Remove a custom or downloaded Python path."""
        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version to remove.")
            return

        row = rows[0].row()
        source = self.python_table.item(row, 2).text()
        version = self.python_table.item(row, 0).text()
        path = self.python_table.item(row, 1).text()

        if source == "System":
            QMessageBox.information(
                self, "Info",
                "System-detected Python installations cannot be removed here.\n"
                "Use your system package manager to uninstall them."
            )
            return

        if source == "User Install":
            reply = QMessageBox.question(
                self, "Remove User Install",
                f"Remove Python {version} from the list?\n\n"
                f"  {path}\n\n"
                f"Note: This only removes it from VenvStudio's list.\n"
                f"To fully uninstall, use: pip uninstall python (or your package manager).",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                # Save to config as excluded path so it won't reappear on next scan
                excluded = self.config.get("excluded_pythons", [])
                if path not in excluded:
                    excluded.append(path)
                    self.config.set("excluded_pythons", excluded)
                self._scan_pythons()
            return

        if source == "Downloaded":
            reply = QMessageBox.question(
                self, "Remove Downloaded Python",
                f"Permanently delete Python {version}?\n\n"
                f"  {path}\n\n"
                f"This will remove the downloaded files from disk.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                from src.core.python_downloader import get_installed_pythons, remove_python
                for py in get_installed_pythons():
                    if py["version"] == version or os.path.normpath(str(py.get("python_exe", ""))) == os.path.normpath(path):
                        remove_python(py["path"])
                        break
                self._scan_pythons()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove Python {version}:\n{e}")
            return

        # source == "Custom"
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

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()

        platform = get_platform()

        # ── Linux / macOS ──
        if platform != "windows":
            self._set_python_default_unix(version, python_path, scope)
            return

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
            """Find PATH entries that belong to OTHER Python installations.
            ONLY removes dirs where python.exe exists directly,
            or Scripts dirs whose PARENT contains python.exe AND pip.exe.
            Never touches non-Python dirs like winget, oh-my-posh, etc.
            """
            exclude_set = {os.path.normcase(d.rstrip("\\")) for d in exclude_dirs}
            found = []
            for p in path_str.split(";"):
                p = p.strip()
                if not p:
                    continue
                p_norm = os.path.normcase(p.rstrip("\\"))
                if p_norm in exclude_set:
                    continue
                # Must have python.exe directly in this dir
                if os.path.exists(os.path.join(p, "python.exe")):
                    found.append(p)
                    continue
                # Scripts dir — ONLY if parent has BOTH python.exe AND pip.exe
                if os.path.basename(p).lower() == "scripts":
                    parent = os.path.dirname(p)
                    has_python = os.path.exists(os.path.join(parent, "python.exe"))
                    has_pip = os.path.exists(os.path.join(p, "pip.exe"))
                    if has_python and has_pip:
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

        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_path_result.txt")

        # SAFE approach: only PREPEND selected Python to PATH — never delete anything else
        # This avoids accidentally removing winget, oh-my-posh, or other tools from PATH.
        # Users with multiple Python versions can use `py -3.x` launcher to choose.
        if scope == "user":
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from User PATH (to avoid duplicates), then prepend
    $uPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $uParts = ($uPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newUser = ('{python_dir};{scripts_dir};' + ($uParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newUser, 'User')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        else:  # system
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from System PATH (to avoid duplicates), then prepend
    $sPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $sParts = ($sPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newSys = ('{python_dir};{scripts_dir};' + ($sParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newSys, 'Machine')

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
                with open(result_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
                    result_text = f.read().strip()
                if "OK" in result_text:
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
                # Verify pip.exe actually exists in Scripts dir
                pip_status = ""
                if not os.path.isfile(pip_exe):
                    pip_status = (
                        f"\n\n⚠️ pip.exe not found in Scripts folder!\n"
                        f"   Run: python -m pip install --upgrade pip\n"
                        f"   (in an admin terminal)"
                    )
                else:
                    pip_status = f"\n\n✅ pip.exe found in Scripts folder."

                QMessageBox.information(
                    self, "✅ Success",
                    f"Python {version} is now the {scope_label} default!\n\n"
                    f"📂 Added to PATH:\n"
                    f"   {python_dir}\n"
                    f"   {scripts_dir}"
                    f"{pip_status}\n\n"
                    f"Open a new terminal and type:\n"
                    f"  python --version\n"
                    f"  pip --version"
                )
                self.config.set("system_default_python", python_path)
                # Save as system default so _scan_pythons shows correct Source
                self.config.set("system_default_python", python_path)
                self._scan_pythons()
            else:
                QMessageBox.warning(
                    self, "⚠️ Partial",
                    f"Could not verify the change.\n"
                    f"Admin permission may have been denied.\n\n"
                    f"Check Environment Variables manually."
                )
                self._scan_pythons()

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

    def _toggle_builtin_presets(self, visible: bool):
        self.builtin_presets_table.setVisible(visible)

    def _load_custom_presets(self):
        """Load custom presets from config into table."""
        presets = self.config.get("custom_presets", {})
        self.custom_presets_table.setRowCount(0)
        for name, pkgs in presets.items():
            row = self.custom_presets_table.rowCount()
            self.custom_presets_table.insertRow(row)
            self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
            self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _save_custom_presets(self):
        """Save custom presets from table to config."""
        presets = {}
        for row in range(self.custom_presets_table.rowCount()):
            name_item = self.custom_presets_table.item(row, 0)
            pkgs_item = self.custom_presets_table.item(row, 1)
            if name_item and pkgs_item:
                name = name_item.text().strip()
                pkgs = [p.strip() for p in pkgs_item.text().split(",") if p.strip()]
                if name and pkgs:
                    presets[name] = pkgs
        self.config.set("custom_presets", presets)

    def _add_custom_preset(self):
        """Add a new custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. 🚀 My Stack")
        pkgs_edit = QLineEdit()
        pkgs_edit.setPlaceholderText("e.g. numpy, pandas, matplotlib, scikit-learn")

        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                pkgs = [p.strip() for p in pkgs_raw.split(",") if p.strip()]
                row = self.custom_presets_table.rowCount()
                self.custom_presets_table.insertRow(row)
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _edit_custom_preset(self):
        """Edit selected custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a preset to edit.")
            return
        old_name = self.custom_presets_table.item(row, 0).text()
        old_pkgs = self.custom_presets_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        pkgs_edit = QLineEdit(old_pkgs)
        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(pkgs_raw))

    def _remove_custom_preset(self):
        """Remove selected custom preset."""
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a preset to remove.")
            return
        name = self.custom_presets_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Preset",
            f"Remove preset '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_presets_table.removeRow(row)

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
            f"background-color: {self._c()['input_bg']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"padding: 3px; font-size: {self._c()['fs_small']}px;"
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
        import os
        import subprocess
        from pathlib import Path
        # Try to get log dir from logger module, fall back to known path
        try:
            from src.utils.logger import get_log_dir
            log_dir = get_log_dir()
        except ImportError:
            import os
            log_dir = Path(os.environ.get("APPDATA", "~")) / "VenvStudio" / "logs"
            log_dir = log_dir.expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        if get_platform() == "windows":
            os.startfile(str(log_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(log_dir)])
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])

    def _open_config_folder(self):
        """Open the config directory in file manager."""
        import os
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
                    **subprocess_args(capture_output=True, text=True, timeout=15, cwd=__import__('os').path.expanduser('~'))
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
                **subprocess_args(capture_output=True, text=True, timeout=10, cwd=__import__('os').path.expanduser('~'))
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
                    **subprocess_args(capture_output=True, text=True, timeout=15, cwd=__import__('os').path.expanduser('~'))
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
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
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
        self.update_status_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")

        # Run in background thread
        self._update_worker = _UpdateCheckWorker(parent=self)
        self._update_worker.finished.connect(self._on_update_check_done)
        self._update_worker.start()

    def _on_update_check_done(self, result):
        """Handle update check result."""
        if result.get("error"):
            self.update_status_label.setText(f"⚠️ {result['error']}")
            self.update_status_label.setStyleSheet(f"color: {self._c()['accent']}; font-size: {self._c()['fs_small']}px;")
            return

        if result["update_available"]:
            self.update_status_label.setText(
                f"🆕 New version available: v{result['latest_version']} (current: v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

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
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

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
        # Use batch mode to avoid writing JSON 30+ times
        self.config.begin_batch()
        # Theme
        if self.theme_cb.isChecked():
            new_theme = self.theme_combo.currentData()
        else:
            new_theme = "dark"
        old_theme = self.config.get("theme", "dark")
        self.config.set("theme", new_theme)
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        # Font — 3-level system
        _defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        for level_id, (def_family, def_size) in _defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            if cb.isChecked():
                self.config.set(f"font_{level_id}_family", combo.currentFont().family())
                self.config.set(f"font_{level_id}_size", spin.value())
            else:
                self.config.set(f"font_{level_id}_family", "")
                self.config.set(f"font_{level_id}_size", def_size)

        # Backward compat
        self.config.set("font_family", self.config.get("font_secondary_family", ""))
        self.config.set("font_size", self.config.get("font_secondary_size", 13))
        font_family = self.config.get("font_secondary_family", "") or "Segoe UI"
        font_size = self.config.get("font_secondary_size", 13)
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

        # Default environment type
        if hasattr(self, "default_env_type_combo"):
            cb_et = getattr(self, "default_env_type_cb", None)
            et_val = self.default_env_type_combo.currentData() if (cb_et and cb_et.isChecked()) else "venv"
            self.config.set("default_env_type", et_val or "venv")
        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb"):
            self.config.set("tc_py_cb_checked", self._tc_py_cb.isChecked())
        if self.terminal_cb.isChecked():
            self.config.set("default_terminal", self.terminal_combo.currentData())
        else:
            self.config.set("default_terminal", "")

        # Jupyter Working Directory
        if self.jupyter_workdir_cb.isChecked():
            self.config.set("jupyter_workdir", self.jupyter_workdir_combo.currentData() or "home")
            if self.jupyter_workdir_combo.currentData() == "custom":
                self.config.set("jupyter_workdir_custom", self.jupyter_custom_path_label.text())
            else:
                self.config.set("jupyter_workdir_custom", "")
        else:
            self.config.set("jupyter_workdir", "home")
            self.config.set("jupyter_workdir_custom", "")

        # Save custom terminals
        self._save_custom_terminals()

        # Save custom presets
        self._save_custom_presets()

        # Save custom categories
        self._save_custom_categories()

        # Save custom catalog
        self._save_custom_catalog()

        # End batch — single disk write for all settings
        self.config.end_batch()
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

