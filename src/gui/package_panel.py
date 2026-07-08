"""
VenvStudio - Package Management Panel
Full featured: cancel, catalog status, command hints, apply changes toggle

Tab construction, launcher logic, environment state, package operations,
export, and misc callbacks live in the corresponding mixin files
(launcher_ui.py, launcher_run.py, launcher_shortcuts.py, tab_builders.py,
env_state.py, package_ops.py, package_export.py, package_misc.py); this
file holds __init__, config/theme helpers, cache helpers, and _setup_ui.

`_EnvSizeWorker`, `WorkerThread`, `CommandHintDialog` live in
package_panel_common.py and are re-exported below so
`from src.gui.package_panel import WorkerThread` (used elsewhere in the
codebase) keeps working unchanged.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTabWidget, QCheckBox, QFileDialog, QMessageBox,
    QTextEdit, QComboBox, QProgressBar, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QSizePolicy, QDialog, QDialogButtonBox,
    QToolButton, QMenu, QAbstractItemView, QApplication,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QProcess, QTimer
from PySide6.QtGui import QFont, QColor, QIcon

from src.core.pip_manager import PipManager
from src.core.venv_manager import VenvManager
from src.core.config_manager import ConfigManager
from src.gui.styles import get_colors
from src.utils.constants import (
    PACKAGE_CATALOG, PRESETS, COMMAND_HINTS,
    PRESET_DESCRIPTIONS, LAUNCHER_TOOLTIPS, UI_TOOLTIPS,
)
from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args, open_terminal_at

from pathlib import Path
import subprocess
import os
import sys

from .package_panel_common import _EnvSizeWorker, WorkerThread, CommandHintDialog  # noqa: F401 (re-exported)
from .launcher_ui import LauncherUIMixin
from .launcher_run import LauncherRunMixin
from .launcher_shortcuts import LauncherShortcutsMixin
from .tab_builders import TabBuildersMixin
from .env_state import EnvStateMixin
from .package_ops import PackageOpsMixin
from .package_export import PackageExportMixin
from .package_misc import PackageMiscMixin


class PackagePanel(LauncherUIMixin, LauncherRunMixin, LauncherShortcutsMixin,
                    TabBuildersMixin, EnvStateMixin, PackageOpsMixin,
                    PackageExportMixin, PackageMiscMixin, QWidget):
    """Package management panel with catalog browsing and pip operations."""
    env_refresh_requested = Signal(int)  # pkg_count (-1 = unknown, refresh from cache)

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.pip_manager = None
        self.current_worker = None
        self.installed_package_names = set()
        self._launcher_py_version_cache: dict = {}  # venv_path -> tuple
        self._catalog_initial_state = {}  # Track original checkbox states
        self.config = config  # ConfigManager — for Jupyter workdir etc.

        # ── In-memory cache — reduces repeated disk I/O ──────────────────
        # Invalidated only after install/uninstall/remove operations
        self._cfg_cache: dict = {}          # ConfigManager values
        self._vm_cache: object = None       # VenvManager instance
        self._vm_cache_base: str = ""       # base_dir used for cached vm
        self._system_tool_cache: dict = {}  # icon_key -> bool (is_installed)
        # B183: snapshot the palette currently in use so the *next* call to
        # apply_theme can detect which colour strings to swap out.
        try:
            self._last_palette = {k: v for k, v in self._c().items()
                                  if isinstance(v, str) and v.startswith("#")}
        except Exception:
            self._last_palette = None
        self._setup_ui()
        # Stub widgets — replaced when lazy tabs are built
        # These ensure code outside tab-build never crashes on attribute access
        if not hasattr(self, 'packages_table'):
            from PySide6.QtWidgets import QTableWidget as _TW
            self.packages_table = _TW()
        if not hasattr(self, 'pkg_count_label'):
            from PySide6.QtWidgets import QLabel as _QL
            self.pkg_count_label = _QL()
        if not hasattr(self, 'catalog_table'):
            from PySide6.QtWidgets import QTableWidget as _TW2
            self.catalog_table = _TW2()
        if not hasattr(self, 'category_combo'):
            from PySide6.QtWidgets import QComboBox as _CB
            self.category_combo = _CB()
        if not hasattr(self, 'manual_input'):
            from PySide6.QtWidgets import QPlainTextEdit as _PTE
            self.manual_input = _PTE()
        if not hasattr(self, 'manual_info_label'):
            from PySide6.QtWidgets import QLabel as _QL2
            self.manual_info_label = _QL2()
        if not hasattr(self, 'output_log'):
            from PySide6.QtWidgets import QTextEdit as _TE
            self.output_log = _TE()

    # ── Cache helpers ────────────────────────────────────────────────────────

    def _get_config(self, key: str, default=None):
        """Get a config value from cache, loading from ConfigManager once."""
        if key not in self._cfg_cache:
            if self.config is not None:
                self._cfg_cache[key] = self.config.get(key, default)
            else:
                try:
                    from src.core.config_manager import ConfigManager
                    self._cfg_cache[key] = ConfigManager().get(key, default)
                except Exception:
                    return default
        return self._cfg_cache[key]

    def _get_venv_manager(self, base_dir=None):
        """Return cached VenvManager, creating it only if base_dir changed."""
        if base_dir is None:
            base_dir = str(self._get_config_base_dir())
        if self._vm_cache is None or self._vm_cache_base != str(base_dir):
            from src.core.venv_manager import VenvManager
            # B175 cache fix: VenvManager.__init__ calls base_dir.mkdir(),
            # so it must receive a Path, not a str. Without this, every
            # _save_all_cache call raised "'str' object has no attribute
            # 'mkdir'" silently — pkg_list cache was never written and
            # every env switch fell back to a fresh `pip list` subprocess.
            self._vm_cache = VenvManager(Path(base_dir))
            self._vm_cache_base = str(base_dir)
        return self._vm_cache

    def _get_config_base_dir(self):
        """Return venv base dir from config (cached)."""
        if self.config is not None:
            return self.config.get_venv_base_dir()
        try:
            from src.core.config_manager import ConfigManager
            return ConfigManager().get_venv_base_dir()
        except Exception:
            from pathlib import Path
            return Path.home() / "venv"

    def _invalidate_cache(self):
        """Call after install/uninstall/env-switch to force fresh data."""
        self._cfg_cache.clear()
        self._vm_cache = None
        self._vm_cache_base = ""
        self._system_tool_cache.clear()

    # ── Theme color palettes ──
    DARK = {
        "bar_bg":      "#181825",
        "bar_border":  "#313244",
        "combo_bg":    "#1e1e2e",
        "combo_fg":    "#cdd6f4",
        "combo_border":"#89b4fa",
        "py_ver":      "#a6e3a1",
        "muted":       "#a6adc8",
        "info":        "#6c7086",
        "sep":         "#45475a",
        "installed_bg":"#313244",
        "installed_fg":"#a6e3a1",
    }
    LIGHT = {
        "bar_bg":      "#e6e9ef",
        "bar_border":  "#ccd0da",
        "combo_bg":    "#ffffff",
        "combo_fg":    "#4c4f69",
        "combo_border":"#1e66f5",
        "py_ver":      "#40a02b",
        "muted":       "#6c6f85",
        "info":        "#9ca0b0",
        "sep":         "#ccd0da",
        "installed_bg":"#dce0e8",
        "installed_fg":"#40a02b",
    }

    def apply_theme(self, theme: str = "dark"):
        """Update hardcoded colors when theme changes."""
        c = self.LIGHT if theme.startswith("light") else self.DARK

        if hasattr(self, "env_bar"):
            self.env_bar.setStyleSheet(
                f"QFrame {{ background-color: {c['bar_bg']}; "
                f"border-bottom: 2px solid {c['bar_border']}; }}"
            )
        if hasattr(self, "env_selector"):
            self.env_selector.setStyleSheet(
                f"QComboBox {{ font-size: 14px; font-weight: bold; padding: 4px 12px;"
                f"  background-color: {c['combo_bg']}; color: {c['combo_fg']};"
                f"  border: 2px solid {c['combo_border']}; border-radius: 6px; }}"
                f"QComboBox:hover {{ border-color: {c['combo_border']}; }}"
                f"QComboBox::drop-down {{ border: none; width: 30px; }}"
                f"QComboBox QAbstractItemView {{"
                f"  background-color: {c['combo_bg']}; color: {c['combo_fg']};"
                f"  selection-background-color: {c['combo_border']}; selection-color: {c['combo_bg']};"
                f"  font-size: 14px; font-weight: bold; border: 1px solid {c['combo_border']}; }}"
            )
        if hasattr(self, "python_version_label"):
            self.python_version_label.setStyleSheet(
                f"font-size: 15px; font-weight: bold; color: {c['py_ver']}; padding-left: 8px;"
            )
        if hasattr(self, "env_pkg_count"):
            self.env_pkg_count.setStyleSheet(
                f"color: {c['muted']}; font-size: {self._c()['fs_small']}px; font-weight: bold;"
            )
        info_style = f"color: {c['info']}; font-size: {self._c()['fs_tiny']}px;"
        sep_style  = f"color: {c['sep']}; font-size: {self._c()['fs_tiny']}px;"
        for attr in ("env_path_label", "env_disk_label", "env_backend_label", "env_last_used_label"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(info_style)
        for attr in ("_info_sep1", "_info_sep2", "_info_sep3"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(sep_style)
        if hasattr(self, "status_label"):
            self.status_label.setStyleSheet(f"color: {c['muted']}; font-size: {self._c()['fs_small']}px;")
        if hasattr(self, "pkg_count_label"):
            self.pkg_count_label.setStyleSheet(f"color: {c['muted']};")
        if hasattr(self, "_legend_label"):
            self._legend_label.setStyleSheet(f"color: {c['muted']}; font-size: {self._c()['fs_tiny']}px;")

        # B183: generic sweep — replace stale palette colours in inline
        # stylesheets across every child widget. Without this, tabs (Launch,
        # Installed, Catalog, Presets, Manual Install) and their cards stay
        # in the previous theme's colours after a switch. We track the last
        # set of colours we used so the next call knows what to swap.
        try:
            from PySide6.QtWidgets import QWidget
            new_palette = self._c()
            old_palette = getattr(self, "_last_palette", None)
            if old_palette:
                replacements = []
                for k, v_old in old_palette.items():
                    if not (isinstance(v_old, str) and v_old.startswith("#")):
                        continue
                    v_new = new_palette.get(k)
                    if isinstance(v_new, str) and v_new and v_new != v_old:
                        replacements.append((v_old.lower(), v_new))
                        replacements.append((v_old.upper(), v_new))
                if replacements:
                    for w in self.findChildren(QWidget):
                        try:
                            ss = w.styleSheet()
                            if not ss:
                                continue
                            new_ss = ss
                            changed = False
                            for v_old, v_new in replacements:
                                if v_old in new_ss:
                                    new_ss = new_ss.replace(v_old, v_new)
                                    changed = True
                            if changed:
                                w.setStyleSheet(new_ss)
                        except RuntimeError:
                            pass
            # Snapshot current palette for next switch
            self._last_palette = {k: v for k, v in new_palette.items()
                                  if isinstance(v, str) and v.startswith("#")}
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Environment selector at top (2-row bar)
        self.env_bar = QFrame()
        self.env_bar.setMinimumHeight(90)
        self.env_bar.setMaximumHeight(90)
        self.env_bar.setStyleSheet(
            "QFrame { background-color: " + self._c()['sidebar'] + "; "
            "border-bottom: 2px solid #313244; }"
        )
        env_bar_outer = QVBoxLayout(self.env_bar)
        env_bar_outer.setContentsMargins(16, 6, 16, 4)
        env_bar_outer.setSpacing(2)

        # ── Row 1: Environment selector + Python version ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        env_lbl = QLabel(f"🐍 {tr('environment')}")
        env_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px;")
        row1.addWidget(env_lbl)

        self.env_selector = QComboBox()
        self.env_selector.setMinimumWidth(120)
        self.env_selector.setMaximumWidth(500)
        self.env_selector.setFixedHeight(34)
        self.env_selector.setSizePolicy(
            self.env_selector.sizePolicy().horizontalPolicy(),
            self.env_selector.sizePolicy().verticalPolicy()
        )
        # Disable mouse wheel scrolling on env selector to prevent accidental switches
        # wheelEvent enabled — scroll to switch environments
        # B183: previously hardcoded Catppuccin Mocha colours (#1e1e2e,
        # #cdd6f4, #89b4fa) which made the selector look dark even when
        # the user picked a light theme. Use palette colours so it adapts.
        _c = self._c()
        _bg = _c.get("input_bg", "#1e1e2e")
        _fg = _c.get("fg", "#cdd6f4")
        _accent = _c.get("accent", "#89b4fa")
        _accent_hover = _c.get("accent_hover", _c.get("accent", "#b4befe"))
        self.env_selector.setStyleSheet(
            "QComboBox {"
            "  font-size: 14px; font-weight: bold; padding: 4px 12px;"
            f"  background-color: {_bg}; color: {_fg};"
            f"  border: 2px solid {_accent}; border-radius: 6px;"
            "}"
            f"QComboBox:hover {{ border-color: {_accent_hover}; }}"
            "QComboBox::drop-down { border: none; width: 30px; }"
            "QComboBox QAbstractItemView {"
            f"  background-color: {_bg}; color: {_fg};"
            f"  selection-background-color: {_accent}; selection-color: {_bg};"
            "  font-size: 14px; font-weight: bold;"
            f"  border: 1px solid {_accent};"
            "}"
        )
        self.env_selector.addItem(tr("select_environment"), "")
        self.env_selector.setToolTip(UI_TOOLTIPS.get("env_selector", ""))
        self.env_selector.currentIndexChanged.connect(self._on_env_selector_changed)
        row1.addWidget(self.env_selector)

        # Python version label (bold, large)
        self.python_version_label = QLabel("")
        self.python_version_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #a6e3a1; padding-left: 8px;"
        )
        row1.addWidget(self.python_version_label)

        self._env_bar_terminal_btn = QPushButton("🖥 Open Terminal")
        self._env_bar_terminal_btn.setObjectName("secondary")
        self._env_bar_terminal_btn.setMinimumWidth(110)
        self._env_bar_terminal_btn.setToolTip(UI_TOOLTIPS.get("btn_open_terminal", "Open terminal with this environment activated"))
        self._env_bar_terminal_btn.clicked.connect(self._open_terminal_here)
        self._env_bar_terminal_btn.setEnabled(False)
        row1.addWidget(self._env_bar_terminal_btn)

        self.env_pkg_count = QLabel("")
        self.env_pkg_count.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px; font-weight: bold; padding-left: 12px;")
        row1.addWidget(self.env_pkg_count)

        row1.addStretch()

        env_bar_outer.addLayout(row1)

        # ── Row 2: Info bar — path | disk size | backend | last used ──
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.setContentsMargins(0, 2, 0, 2)

        info_style = f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;"
        separator_style = f"color: {self._c()['border']}; font-size: {self._c()['fs_tiny']}px;"

        self.env_path_label = QLabel("")
        self.env_path_label.setStyleSheet(info_style)
        row2.addWidget(self.env_path_label)

        self._info_sep1 = QLabel("│")
        self._info_sep1.setStyleSheet(separator_style)
        row2.addWidget(self._info_sep1)

        self.env_disk_label = QLabel("")
        self.env_disk_label.setStyleSheet(info_style)
        row2.addWidget(self.env_disk_label)

        self._info_sep2 = QLabel("│")
        self._info_sep2.setStyleSheet(separator_style)
        row2.addWidget(self._info_sep2)

        self.env_backend_label = QLabel("")
        self.env_backend_label.setStyleSheet(info_style)
        row2.addWidget(self.env_backend_label)

        self._info_sep3 = QLabel("│")
        self._info_sep3.setStyleSheet(separator_style)
        row2.addWidget(self._info_sep3)

        self.env_last_used_label = QLabel("")
        self.env_last_used_label.setStyleSheet(info_style)
        row2.addWidget(self.env_last_used_label)

        row2.addStretch()

        # Hide info row initially
        self._info_labels = [
            self.env_path_label, self.env_disk_label,
            self.env_backend_label, self.env_last_used_label,
            self._info_sep1, self._info_sep2, self._info_sep3,
        ]
        for lbl in self._info_labels:
            lbl.setVisible(False)

        env_bar_outer.addLayout(row2)

        # Wrap env_bar in scroll area for low-resolution / small window support
        from PySide6.QtWidgets import QScrollArea as _QSA
        _env_bar_scroll = _QSA()
        _env_bar_scroll.setWidget(self.env_bar)
        _env_bar_scroll.setWidgetResizable(True)
        _env_bar_scroll.setFixedHeight(96)
        _env_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        _env_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        _env_bar_scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(_env_bar_scroll)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(False)

        # Tab definitions — widgets built lazily on first visit
        self._tab_defs = [
            ("launcher",  f"🚀 {tr('app_launcher')}",   None, UI_TOOLTIPS.get("tab_launch", "")),
            ("installed", f"📦 {tr('installed')}",       None, UI_TOOLTIPS.get("tab_installed", "")),
            ("catalog",   f"🛒 {tr('catalog')}",         None, UI_TOOLTIPS.get("tab_catalog", "")),
            ("presets",   f"⚡ {tr('presets')}",         None, UI_TOOLTIPS.get("tab_presets", "")),
            ("manual",    f"⌨️ {tr('manual_install')}",  None, UI_TOOLTIPS.get("tab_manual", "")),
        ]
        self._tab_built = {}

        # Add placeholder tabs immediately
        for i, (key, label, widget, tooltip) in enumerate(self._tab_defs):
            from PySide6.QtWidgets import QWidget as _QW
            self.tabs.addTab(_QW(), label)
            self.tabs.setTabToolTip(i, tooltip)

        # Build launcher tab immediately (first visible tab)
        self._ensure_tab_built(0)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # Status bar with cancel button
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(44)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(12, 4, 12, 4)

        self.status_label = QLabel("Select an environment to manage packages")
        self.status_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        status_layout.addWidget(self.status_label, 1)

        self.cancel_btn = QPushButton("⛔ Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_operation)
        status_layout.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(self.status_bar)

    def _append_log(self, text: str):
        """Append colored HTML lines to output log."""
        def _escape(s):
            """Simple HTML escape — avoids 'import html' which PyInstaller may exclude."""
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        for line in text.split("\n"):
            t = line.rstrip()
            if not t:
                self.output_log.append("")
                continue
            escaped = _escape(t)
            tl = t.lower()
            if t.startswith(("✅", "Successfully")) or "successfully installed" in tl:
                color = "#a6e3a1"
            elif t.startswith(("❌", "ERROR")) or "failed" in tl or "error" in tl:
                color = "#f38ba8"
            elif t.startswith(("⚠️", "WARNING")) or "warning" in tl:
                color = "#f9e2af"
            elif t.startswith("⛔") or "cancel" in tl:
                color = "#fab387"
            elif t.startswith(("💡", "   ", "Collecting")):
                color = "#89dceb"
            elif t.startswith(("📦", "🔄", "⬇", "Downloading", "Installing")):
                color = "#89b4fa"
            elif t.startswith("Requirement already"):
                color = "#6c7086"
            else:
                color = "#cdd6f4"
            self.output_log.append(f'<span style="color:{color};">{escaped}</span>')

    def _copy_output_log(self):
        """Copy output log content to clipboard."""
        text = self.output_log.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self._copy_log_btn.setText("✅ Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self._copy_log_btn.setText("📋 Copy Log"))

    # ── Public Methods ──

    def _get_pkg_cache_key(self) -> str:
        if not self.pip_manager:
            return ""
        # B175 perf fix: use venv_manager's normalised cache key.
        try:
            from src.core.venv_manager import VenvManager  # noqa: F401
            vm = self._get_venv_manager()
            return "pkg_list:" + vm._cache_key(self.pip_manager.venv_path)
        except Exception:
            return "pkg_list:" + str(self.pip_manager.venv_path).replace("\\", "/")

    def _load_pkg_cache(self):
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            entry = vm._load_all_cache().get(self._get_pkg_cache_key())
            if not entry or entry.get("needs_refresh", 1) == 1:
                return None
            return entry.get("packages")
        except Exception:
            return None

    def _save_pkg_cache(self, packages):
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            all_cache = vm._load_all_cache()
            key = self._get_pkg_cache_key()
            all_cache[key] = {
                "packages": [{"name": p.name, "version": p.version} for p in packages],
                "needs_refresh": 0,
            }
            vm._save_all_cache(all_cache)
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.pkg_cache").debug(
                    f"[PkgCache] SAVED key={key!r} count={len(packages)}"
                )
            except Exception:
                pass
        except Exception as _e:
            try:
                import traceback
                from src.utils.logger import get_logger
                _tb = traceback.format_exc()
                get_logger("venvstudio.pkg_cache").warning(
                    f"[PkgCache] SAVE FAILED: {type(_e).__name__}: {_e}\n{_tb}"
                )
            except Exception:
                pass

    def _invalidate_pkg_cache(self):
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            all_cache = vm._load_all_cache()
            key = self._get_pkg_cache_key()
            if key in all_cache:
                all_cache[key]["needs_refresh"] = 1
            else:
                all_cache[key] = {"needs_refresh": 1}
            vm._save_all_cache(all_cache)
        except Exception:
            pass

    def _invalidate_env_cache(self) -> None:
        """Invalidate cache for current env so env list refreshes correctly."""
        if not hasattr(self, "_current_venv_path") or not self._current_venv_path:
            return
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            vm.invalidate_cache(self._current_venv_path)
        except Exception:
            pass

    def _open_terminal_here(self):
        """Open terminal with current venv activated."""
        if not hasattr(self, "_current_venv_path") or not self._current_venv_path:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Environment", "Please select an environment first.")
            return
        try:
            from src.utils.platform_utils import open_terminal_at
            from src.core.config_manager import ConfigManager
            terminal_type = self._get_config("terminal_type", "")
            env_type = getattr(self, "_current_env_type", "venv")
            print(f"[DEBUG] open_terminal_at path={self._current_venv_path} env_type={env_type}")
            open_terminal_at(self._current_venv_path, terminal_type,
                             env_type=env_type)
        except Exception as e:
            print(f"[DEBUG] terminal error: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open terminal:\n{e}")

    def _c(self) -> dict:
        """Return current theme color palette with font hierarchy."""
        from src.gui.styles import get_colors
        from src.core.config_manager import ConfigManager
        cfg = self.config if self.config else __import__("src.core.config_manager", fromlist=["ConfigManager"]).ConfigManager()
        theme = cfg.get("theme", "dark")
        font_size = cfg.get("font_secondary_size", 13) or cfg.get("font_size", 13)
        primary_size = cfg.get("font_primary_size", 22)
        tertiary_size = cfg.get("font_tertiary_size", 11)
        return get_colors(theme, font_size, primary_size, tertiary_size)

