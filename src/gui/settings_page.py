"""
VenvStudio - Settings Page
Main SettingsPage class.
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
import os, subprocess, shutil
from pathlib import Path

from .settings_appearance import AppearanceMixin
from .settings_python import PythonMixin
from .settings_catalog import CatalogMixin
from .settings_advanced import AdvancedMixin
from .settings_toolchain import ToolchainMixin
from .settings_python_download import (
    _DownloadWorker, _UpdateCheckWorker, _FetchWorker, PythonDownloadDialog
)

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



class SettingsPage(AppearanceMixin, PythonMixin, CatalogMixin, AdvancedMixin, ToolchainMixin, QWidget):
    """Full settings page with all configuration options."""

    theme_changed = Signal(str)
    font_changed = Signal(str, int)
    language_changed = Signal(str)
    settings_saved = Signal()

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

        self._setup_appearance_section(layout)
        self._setup_language_section(layout)
        self._setup_python_ui_section(layout)
        self._setup_toolchain_ui_section(layout)
        self._setup_general_section(layout)
        self._setup_vscode_ui_section(layout)
        self._setup_catalog_ui_section(layout)
        self._setup_diagnostics_section(layout)
        self._setup_cli_ui_section(layout)
        self._setup_launch_section(layout)

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

    def _setup_appearance_section(self, layout):
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
        ROW_H = 32  # fixed height for all font row widgets
        for level_id, label, hint, default_size in font_levels:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            cb = QCheckBox()
            cb.setChecked(False)
            cb.setFixedHeight(ROW_H)
            row.addWidget(cb)

            font_combo = QFontComboBox()
            font_combo.setEnabled(False)
            font_combo.setFocusPolicy(Qt.StrongFocus)
            font_combo.setFixedHeight(ROW_H)
            cb.toggled.connect(font_combo.setEnabled)
            row.addWidget(font_combo, 1)

            size_spin = QSpinBox()
            size_spin.setRange(8, 48)
            size_spin.setValue(default_size)
            size_spin.setSuffix(" px")
            size_spin.setEnabled(False)
            size_spin.setFixedWidth(80)
            size_spin.setFixedHeight(ROW_H)
            cb.toggled.connect(size_spin.setEnabled)
            row.addWidget(size_spin)

            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic;")
            hint_lbl.setMinimumWidth(200)
            hint_lbl.setFixedHeight(ROW_H)
            hint_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
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


    def _setup_language_section(self, layout):
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


    def _setup_python_ui_section(self, layout):
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


    def _setup_toolchain_ui_section(self, layout):
        # ── 5b. TOOLCHAIN MANAGER ──────────────────────────────────────────
        if not hasattr(self, "_tc_built"):
            self._tc_built = True
            self._build_toolchain_ui(layout)


    def _setup_general_section(self, layout):
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


    def _setup_vscode_ui_section(self, layout):
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


    def _setup_catalog_ui_section(self, layout):
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


    def _setup_diagnostics_section(self, layout):
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


    def _setup_cli_ui_section(self, layout):
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

    def _setup_launch_section(self, layout):
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

