"""
VenvStudio - Package Management Panel
Full featured: cancel, catalog status, command hints, apply changes toggle
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTabWidget, QCheckBox, QFileDialog, QMessageBox,
    QTextEdit, QComboBox, QProgressBar, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QSizePolicy, QDialog, QDialogButtonBox,
    QToolButton, QMenu,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QProcess
from PySide6.QtGui import QFont, QColor, QIcon

from src.core.pip_manager import PipManager
from src.utils.constants import (
    PACKAGE_CATALOG, PRESETS, COMMAND_HINTS,
    PRESET_DESCRIPTIONS, LAUNCHER_TOOLTIPS, UI_TOOLTIPS,
)

# Docs URLs for popular packages
_PACKAGE_DOCS = {
    "numpy": "https://numpy.org/doc/",
    "pandas": "https://pandas.pydata.org/docs/",
    "matplotlib": "https://matplotlib.org/stable/",
    "scipy": "https://docs.scipy.org/doc/scipy/",
    "scikit-learn": "https://scikit-learn.org/stable/documentation.html",
    "tensorflow": "https://www.tensorflow.org/api_docs",
    "torch": "https://pytorch.org/docs/stable/",
    "keras": "https://keras.io/api/",
    "xgboost": "https://xgboost.readthedocs.io/",
    "lightgbm": "https://lightgbm.readthedocs.io/",
    "seaborn": "https://seaborn.pydata.org/",
    "plotly": "https://plotly.com/python/",
    "bokeh": "https://docs.bokeh.org/",
    "altair": "https://altair-viz.github.io/",
    "dash": "https://dash.plotly.com/",
    "streamlit": "https://docs.streamlit.io/",
    "gradio": "https://www.gradio.app/docs/",
    "panel": "https://panel.holoviz.org/",
    "voila": "https://voila.readthedocs.io/",
    "mlflow": "https://mlflow.org/docs/latest/index.html",
    "tensorboard": "https://www.tensorflow.org/tensorboard",
    "datasette": "https://docs.datasette.io/",
    "fastapi": "https://fastapi.tiangolo.com/",
    "flask": "https://flask.palletsprojects.com/",
    "django": "https://docs.djangoproject.com/",
    "sqlalchemy": "https://docs.sqlalchemy.org/",
    "requests": "https://requests.readthedocs.io/",
    "httpx": "https://www.python-httpx.org/",
    "aiohttp": "https://docs.aiohttp.org/",
    "pydantic": "https://docs.pydantic.dev/",
    "celery": "https://docs.celeryq.dev/",
    "redis": "https://redis-py.readthedocs.io/",
    "pillow": "https://pillow.readthedocs.io/",
    "opencv-python": "https://docs.opencv.org/",
    "nltk": "https://www.nltk.org/",
    "spacy": "https://spacy.io/api",
    "transformers": "https://huggingface.co/docs/transformers/",
    "pytest": "https://docs.pytest.org/",
    "black": "https://black.readthedocs.io/",
    "mypy": "https://mypy.readthedocs.io/",
    "jupyter": "https://jupyter.org/documentation",
    "jupyterlab": "https://jupyterlab.readthedocs.io/",
    "ipython": "https://ipython.readthedocs.io/",
    "rich": "https://rich.readthedocs.io/",
    "click": "https://click.palletsprojects.com/",
    "typer": "https://typer.tiangolo.com/",
    "pyside6": "https://doc.qt.io/qtforpython/",
    "pyqt6": "https://www.riverbankcomputing.com/static/Docs/PyQt6/",
    "sqlmodel": "https://sqlmodel.tiangolo.com/",
    "alembic": "https://alembic.sqlalchemy.org/",
    "paramiko": "https://www.paramiko.org/",
    "cryptography": "https://cryptography.io/en/latest/",
    "arrow": "https://arrow.readthedocs.io/",
    "pendulum": "https://pendulum.eustace.io/docs/",
    "dask": "https://docs.dask.org/",
    "polars": "https://docs.pola.rs/",
    "pyarrow": "https://arrow.apache.org/docs/python/",
    "numba": "https://numba.readthedocs.io/",
    "sympy": "https://docs.sympy.org/",
    "statsmodels": "https://www.statsmodels.org/stable/",
    "networkx": "https://networkx.org/documentation/",
    "scrapy": "https://docs.scrapy.org/",
    "beautifulsoup4": "https://www.crummy.com/software/BeautifulSoup/bs4/doc/",
    "selenium": "https://selenium-python.readthedocs.io/",
    "playwright": "https://playwright.dev/python/docs/intro",
    "pymongo": "https://pymongo.readthedocs.io/",
    "motor": "https://motor.readthedocs.io/",
    "psycopg2": "https://www.psycopg.org/docs/",
    "aiomysql": "https://aiomysql.readthedocs.io/",
    "boto3": "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html",
    "google-cloud-storage": "https://cloud.google.com/python/docs/reference/storage/latest",
    "azure-storage-blob": "https://learn.microsoft.com/en-us/python/api/azure-storage-blob/",
    "docker": "https://docker-py.readthedocs.io/",
    "fabric": "https://docs.fabfile.org/",
    "ansible": "https://docs.ansible.com/",
    # CLI/TUI
    "rich": "https://rich.readthedocs.io/",
    "textual": "https://textual.textualize.io/",
    "prompt_toolkit": "https://python-prompt-toolkit.readthedocs.io/",
    "questionary": "https://questionary.readthedocs.io/",
    "blessed": "https://blessed.readthedocs.io/",
    "urwid": "http://urwid.org/",
    "asciimatics": "https://asciimatics.readthedocs.io/",
    "tqdm": "https://tqdm.github.io/",
    "alive-progress": "https://github.com/rsalmei/alive-progress",
    "colorama": "https://github.com/tartley/colorama",
    "click": "https://click.palletsprojects.com/",
    "typer": "https://typer.tiangolo.com/",
    "tabulate": "https://github.com/astanin/python-tabulate",
    "prettytable": "https://prettytable.readthedocs.io/",
}
from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args

from pathlib import Path
import subprocess
import os
import sys


class _EnvSizeWorker(QThread):
    """Background worker that totals the on-disk size of a venv directory.

    Runs os.walk + getsize off the UI thread (B175). Emits ``done(path, size_str)``
    when finished. ``size_str`` is empty on failure. The walk respects
    interruption requests so the worker can be cancelled when the user
    selects a different env.
    """
    done = Signal(str, str)

    _SIZE_CAP_BYTES = 10 * 1024 * 1024 * 1024

    def __init__(self, venv_path_str: str, parent=None):
        super().__init__(parent)
        self._venv_path_str = venv_path_str

    def run(self):
        total = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(self._venv_path_str):
                if self.isInterruptionRequested():
                    self.done.emit(self._venv_path_str, "")
                    return
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
                if total > self._SIZE_CAP_BYTES:
                    break
            if total < 1024 * 1024:
                size_str = f"{total / 1024:.0f} KB"
            elif total < 1024 * 1024 * 1024:
                size_str = f"{total / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total / (1024 * 1024 * 1024):.2f} GB"
            self.done.emit(self._venv_path_str, size_str)
        except Exception:
            self.done.emit(self._venv_path_str, "")


class WorkerThread(QThread):
    """Worker thread with cancel support."""
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False

    def run(self):
        try:
            self.kwargs["callback"] = self._on_progress
            success, msg = self.func(*self.args, **self.kwargs)
            if self._cancelled:
                self.finished.emit(False, "Operation cancelled by user")
            else:
                self.finished.emit(success, msg)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.worker").error(f"WorkerThread CRASH:\n{tb}")
            except Exception:
                print(f"[WorkerThread ERROR] {tb}")
            self.finished.emit(False, f"Error: {e}")

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True

class CommandHintDialog(QDialog):
    """Shows the equivalent pip command for educational purposes."""

    def __init__(self, title, command, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"💡 {title}")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        info = QLabel("Equivalent terminal command:")
        info.setStyleSheet(f"font-size: {self._c()['fs_small']}px; color: {self._c()['fg_muted']};")
        layout.addWidget(info)

        cmd_frame = QFrame()
        cmd_frame.setStyleSheet(
            "background-color: " + self._c()['sidebar'] + "; border: 1px solid " + self._c()['border'] + "; "
            "border-radius: 8px; padding: 12px;"
        )
        cmd_layout = QVBoxLayout(cmd_frame)
        cmd_label = QLabel(f"<code style='font-size:{self._c()['fs_subheader']}px; color:{self._c()['success']};'>{command}</code>")
        cmd_label.setTextFormat(Qt.RichText)
        cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cmd_layout.addWidget(cmd_label)
        layout.addWidget(cmd_frame)

        tip = QLabel("💡 You can copy this command and run it in any terminal.")
        tip.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg_muted']};")
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy Command")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(lambda: (
            QApplication.clipboard().setText(command),
            copy_btn.setText("✅ Copied!"),
        ))
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        ok_btn = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn.accepted.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

class PackagePanel(QWidget):
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

    # ── Tab Builders ──

    def _create_launcher_tab(self) -> QWidget:
        """App Launcher tab — launch Orange, JupyterLab, Notebook from the env."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        info = QLabel(
            "Launch applications installed in the selected environment.\n"
            "If an app is not installed, you can install it with one click."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        layout.addWidget(info)

        # App cards grid
        self.launcher_grid = QGridLayout()
        self.launcher_grid.setSpacing(16)
        self.launcher_grid.setAlignment(Qt.AlignTop)

        self.app_definitions = [
            {
                "name": "JupyterLab",
                "icon": "🔬",
                "icon_key": "jupyterlab",
                "env_types": ["venv"],
                "package": "jupyterlab",
                "command": ["-m", "jupyter", "lab"],
                "desc": "Next-generation notebook interface for interactive computing",
                "needs_console": True,
                            },
            {
                "name": "Jupyter Notebook",
                "icon": "📓",
                "icon_key": "jupyter_notebook",
                "env_types": ["venv"],
                "package": "notebook",
                "command": ["-m", "jupyter", "notebook"],
                "desc": "Classic Jupyter Notebook — simple, document-centric interface",
                "needs_console": True,
                            },
            {
                "name": "Orange Data Mining",
                "icon": "🍊",
                "icon_key": "orange3",
                "env_types": ["venv"],
                "package": "orange3",
                "command": ["-m", "Orange.canvas"],
                "desc": "Visual programming for data mining and machine learning",
                "note": "Installs PyQt5 + orange3. chardet<4.0 applied automatically.",
                            },
            {
                "name": "Spyder IDE",
                "icon": "🕷️",
                "icon_key": "spyder",
                "env_types": ["venv"],
                "package": "spyder",
                "command": ["-m", "spyder.app.start"],
                "desc": "Scientific Python development environment",
                            },
            {
                "name": "IPython",
                "icon": "🐍",
                "icon_key": "ipython",
                "env_types": ["venv"],
                "package": "ipython",
                "command": ["-m", "IPython"],
                "desc": "Enhanced interactive Python shell",
                "needs_console": True,
                            },
            {
                "name": "Streamlit",
                "icon": "🎈",
                "icon_key": "streamlit",
                "env_types": ["venv"],
                "package": "streamlit",
                "command": ["-m", "streamlit", "hello", "--server.headless", "true"],
                "desc": "Build data apps in minutes — launches demo app",
                "needs_console": True,
                "open_browser": "http://localhost:8501",
                "browser_delay": 3,
                            },
            {
                "name": "Gradio",
                "icon": "🤗",
                "icon_key": "gradio",
                "env_types": ["venv"],
                "package": "gradio",
                "command": ["-c", "import gradio as gr; gr.Interface(lambda x: x, 'text', 'text', title='Gradio Demo').launch()"],
                "desc": "Build ML model demos & web apps",
                "needs_console": True,
                "open_browser": "http://localhost:7860",
                "browser_delay": 4,
                            },
            {
                "name": "Dash",
                "icon": "📊",
                "icon_key": "dash",
                "env_types": ["venv"],
                "package": "dash",
                "command": ["-c", "import dash; from dash import html; app=dash.Dash(); app.layout=html.H1('Dash is running!'); app.run(debug=False)"],
                "desc": "Interactive dashboards by Plotly",
                "needs_console": True,
                "open_browser": "http://localhost:8050",
                "browser_delay": 3,
                            },
            {
                "name": "Panel",
                "icon": "🔲",
                "icon_key": "panel",
                "env_types": ["venv"],
                "package": "panel",
                "command": ["-m", "panel", "serve", "--show"],
                "desc": "HoloViz dashboards & data apps",
                "needs_console": True,
                            },
            {
                "name": "Voilà",
                "icon": "📓",
                "icon_key": "voila",
                "env_types": ["venv"],
                "package": "voila",
                "command": ["-m", "voila", "--no-browser"],
                "desc": "Turn notebooks into standalone web apps",
                "needs_console": True,
                "open_browser": "http://localhost:8866",
                "browser_delay": 3,
                            },
            {
                "name": "MLflow UI",
                "icon": "🧪",
                "icon_key": "mlflow",
                "env_types": ["venv"],
                "package": "mlflow",
                "command": ["-m", "mlflow", "ui"],
                "desc": "ML experiment tracking & model registry",
                "needs_console": True,
                "open_browser": "http://localhost:5000",
                "browser_delay": 3,
                            },
            {
                "name": "TensorBoard",
                "script_launcher": True,
                "icon": "📈",
                "icon_key": "tensorboard",
                "env_types": ["venv"],
                "package": "tensorboard",
                "command": ["-m", "tensorboard.main", "--logdir", "."],
                "desc": "Visualize training metrics — pick a log directory",
                "needs_console": True,
                "open_browser": "http://localhost:6006",
                "browser_delay": 6,
                "pick_logdir": True,
                            },
            {
                "name": "FastAPI",
                "icon": "⚡",
                "icon_key": "fastapi",
                "package": "fastapi",
                "command": ["-c", "import uvicorn; from fastapi import FastAPI; app=FastAPI(); uvicorn.run(app, host='127.0.0.1', port=8000)"],
                "desc": "Modern fast web API framework — launches demo",
                "needs_console": True,
                "open_browser": "http://localhost:8000/docs",
                "browser_delay": 3,
                            },
            {
                "name": "Datasette",
                "icon": "🗄️",
                "icon_key": "datasette",
                "package": "datasette",
                "command": ["-m", "datasette", "--open"],
                "desc": "Explore & publish SQLite databases",
                "needs_console": True,
                "open_browser": "http://localhost:8001",
                "browser_delay": 3,
                            },
            # ── pip-based: Marimo ─────────────────────────────────────────────
            {
                "name": "Marimo",
                "icon": "🌊",
                "icon_key": "marimo",
                "env_types": ["venv"],
                "package": "marimo",
                "command": ["-m", "marimo", "edit"],
                "desc": "Reactive notebook — next-gen Jupyter alternative",
                "needs_console": True,
                "open_browser": "http://localhost:2718",
                "browser_delay": 3,
                            },
            # ── System-level apps (detect & launch, no pip install) ───────────
            {
                "name": "R Console",
                "icon": "📐",
                "icon_key": "r_console",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "conda_packages": ["r-base"],
                "conda_channels": ["conda-forge"],
                "system_commands": {
                    "windows": ["R.exe", "--no-save"],
                    "linux":   ["R", "--no-save"],
                    "macos":   ["R", "--no-save"],
                },
                "system_search_paths": {
                    "windows": [
                        r"C:\Program Files\R",
                        r"C:\Program Files (x86)\R",
                    ],
                },
                "system_exe_glob": {
                    "windows": r"R-*\bin\R.exe",
                },
                "desc": "R statistical computing language — open R console",
                "needs_console": True,
                            },
            {
                "name": "RStudio",
                "icon": "🎯",
                "icon_key": "rstudio",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "conda_packages": ["rstudio"],
                "conda_channels": ["conda-forge"],
                "system_commands": {
                    "windows": ["rstudio.exe"],
                    "linux":   ["rstudio"],
                    "macos":   ["open", "-a", "RStudio"],
                },
                "system_search_paths": {
                    "windows": [
                        r"C:\Program Files\RStudio\bin",
                        r"C:\Program Files (x86)\RStudio\bin",
                    ],
                    "linux": [
                        "/usr/lib/rstudio/bin",
                        "/usr/local/lib/rstudio/bin",
                        "/opt/rstudio/bin",
                    ],
                },
                "desc": "RStudio IDE — full R development environment",
                            },
            {
                "name": "Ollama",
                "icon": "🦙",
                "icon_key": "ollama",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "system_commands": {
                    "windows": ["ollama.exe", "serve"],
                    "linux":   ["ollama", "serve"],
                    "macos":   ["ollama", "serve"],
                },
                "desc": "Run local LLMs (Llama, Mistral, Gemma…) — starts Ollama server",
                "needs_console": True,
                "open_browser": "http://localhost:11434",
                "browser_delay": 3,
                            },
            {
                "name": "DBeaver",
                "icon": "🦫",
                "icon_key": "dbeaver",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "conda_packages": ["dbeaver-ce"],
                "conda_channels": ["conda-forge"],
                "system_commands": {
                    "windows": ["dbeaver.exe"],
                    "linux":   ["dbeaver"],
                    "macos":   ["open", "-a", "DBeaver"],
                },
                "system_search_paths": {
                    "windows": [
                        r"C:\Program Files\DBeaver",
                        r"C:\Program Files (x86)\DBeaver",
                    ],
                    "linux": [
                        "/usr/share/dbeaver",
                        "/opt/dbeaver",
                        "/snap/bin",
                    ],
                },
                "desc": "Universal database manager — explore SQLite, PostgreSQL, MySQL…",
                            },
            {
                "name": "Quarto",
                "icon": "📝",
                "icon_key": "quarto",
                "env_types": ["venv"],
                "package": "quarto-cli",
                "command": ["-m", "quarto_cli.quarto", "preview"],
                "desc": "Publish documents, reports & dashboards from Python/R notebooks",
                "needs_console": True,
                "note": "Installs Quarto binary inside the environment (~100MB). No system install needed.",
                            },
            {
                "name": "jamovi",
                "icon": "🧩",
                "icon_key": "jamovi",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "conda_packages": ["jamovi"],
                "conda_channels": ["conda-forge"],
                "system_commands": {
                    "windows": ["jamovi.exe"],
                    "linux":   ["jamovi"],
                    "macos":   ["open", "-a", "jamovi"],
                },
                "desc": "Point-and-click statistics — SPSS alternative, free & open source",
                            },
            {
                "name": "JASP",
                "icon": "📊",
                "icon_key": "jasp",
                "env_types": ["conda"],
                "package": "__system__",
                "system_app": True,
                "conda_packages": ["jasp"],
                "conda_channels": ["conda-forge"],
                "system_commands": {
                    "windows": ["JASP.exe"],
                    "linux":   ["JASP"],
                    "macos":   ["open", "-a", "JASP"],
                },
                "desc": "Bayesian & frequentist statistics — beautiful, free, open source",
                            },
        ]

        self.launcher_cards = {}
        self.launcher_grid_widget = QWidget()
        self.launcher_grid_widget.setLayout(self.launcher_grid)
        for i, app in enumerate(self.app_definitions):
            card = self._create_app_card(app)
            self.launcher_grid.addWidget(card, i // 3, i % 3)
            self.launcher_cards[app["name"]] = card
        self._launcher_container_layout = layout  # keep ref for rebuild
        layout.addWidget(self.launcher_grid_widget)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_app_card(self, app_def: dict) -> QFrame:
        """Create a single app launcher card."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(200)
        card.setMaximumHeight(280)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet("""
            QFrame#card {
                background-color: rgba(137, 180, 250, 0.05);
                border: 1px solid #313244;
                border-radius: 12px;
                padding: 12px;
            }
            QFrame#card:hover {
                border: 1px solid #89b4fa;
                background-color: rgba(137, 180, 250, 0.1);
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Educational: Build tooltip from LAUNCHER_TOOLTIPS
        tooltip_text = LAUNCHER_TOOLTIPS.get(app_def.get("icon_key", ""), app_def["desc"])

        # Icon + Name
        header = QHBoxLayout()
        icon_label = QLabel(app_def["icon"])
        icon_label.setFont(QFont("Segoe UI", 28))
        icon_label.setToolTip(tooltip_text)
        header.addWidget(icon_label)

        name_label = QLabel(app_def["name"])
        name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        name_label.setToolTip(tooltip_text)
        header.addWidget(name_label, 1)
        layout.addLayout(header)

        # Description
        desc = QLabel(app_def["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        desc.setToolTip(tooltip_text)
        layout.addWidget(desc)

        # Links toggle — lazy load from JSON only on first click
        _app_name_for_links = app_def["name"]
        _link_defs = [
            ("site",     "🌐 Site",    "#a6e3a1"),
            ("docs",     "📖 Docs",    "#89b4fa"),
            ("youtube",  "▶ YouTube",  "#f38ba8"),
            ("github",   "🐙 GitHub",  "#cba6f7"),
            ("twitter",  "𝕏",          "#74c7ec"),
            ("linkedin", "in",         "#89dceb"),
            ("discord",  "💬 Discord", "#b4befe"),
            ("pypi",     "📦 PyPI",    "#fab387"),
        ]
        _links_container = QWidget()
        _links_container.setVisible(False)
        _lc_layout = QHBoxLayout(_links_container)
        _lc_layout.setContentsMargins(0, 2, 0, 0)
        _lc_layout.setSpacing(3)
        _lc_layout.addStretch()  # placeholder until loaded

        _toggle_row = QHBoxLayout()
        _toggle_row.setContentsMargins(0, 0, 0, 0)
        _toggle_btn = QPushButton("🔗 Links ›")
        _toggle_btn.setFixedHeight(18)
        _toggle_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {self._c()['fg_muted']}; "
            f"border: none; font-size: 11px; padding: 0; }}"
            f"QPushButton:hover {{ color: {self._c()['fg']}; }}"
        )
        _toggle_btn.setCursor(Qt.PointingHandCursor)

        def _make_lazy_toggle(btn, container, app_name, defs):
            _loaded = [False]
            def _toggle():
                _vis = not container.isVisible()
                # Lazy load: only read JSON on first open
                if _vis and not _loaded[0]:
                    _loaded[0] = True
                    try:
                        import json as _j, os as _o
                        _p = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)),
                                          "launcher_links.json")
                        with open(_p, "r", encoding="utf-8") as _f:
                            _all = _j.load(_f)
                        _links = _all.get(app_name, {})
                    except Exception:
                        _links = {}
                    # Clear placeholder stretch
                    while container.layout().count():
                        _item = container.layout().takeAt(0)
                        if _item.widget():
                            _item.widget().deleteLater()
                    # Add link buttons
                    _has_any = False
                    for _key, _label, _color in defs:
                        _url = _links.get(_key)
                        if not _url:
                            continue
                        _has_any = True
                        _lb = QPushButton(_label)
                        _lb.setFixedHeight(19)
                        _lb.setStyleSheet(
                            f"QPushButton {{ background: transparent; color: {_color}; "
                            f"border: none; font-size: 11px; padding: 0 3px; }}"
                            f"QPushButton:hover {{ text-decoration: underline; color: white; }}"
                        )
                        _lb.setCursor(Qt.PointingHandCursor)
                        _lb.clicked.connect(lambda _, u=_url: __import__('webbrowser').open(u))
                        container.layout().addWidget(_lb)
                    container.layout().addStretch()
                    if not _has_any:
                        # No links for this app — hide toggle button
                        btn.setVisible(False)
                        return
                container.setVisible(_vis)
                btn.setText("🔗 Links ∨" if _vis else "🔗 Links ›")
            return _toggle

        _toggle_btn.clicked.connect(
            _make_lazy_toggle(_toggle_btn, _links_container, _app_name_for_links, _link_defs)
        )
        _toggle_row.addWidget(_toggle_btn)
        _toggle_row.addStretch()
        layout.addLayout(_toggle_row)
        layout.addWidget(_links_container)

        # Set card-level tooltip too
        card.setToolTip(tooltip_text)

        # Status label
        status = QLabel("")
        status.setObjectName(f"status_{app_def['name']}")
        status.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(status)

        layout.addStretch()

        # Buttons row 1: Launch + Copy Command
        btn_layout = QHBoxLayout()

        launch_btn = QPushButton(f"▶ {tr('launch_app').format(app=app_def['name'])}"
                                 if '{app}' in tr('launch_app') else f"▶ Launch")
        launch_btn.setObjectName("success")
        launch_btn.clicked.connect(lambda checked, a=app_def: self._launch_app(a))
        btn_layout.addWidget(launch_btn)

        # "Open Script" button for framework apps (Dash, Gradio, FastAPI etc.)
        if app_def.get("script_launcher", False):
            script_btn = QPushButton("📂 Open Script")
            script_btn.setObjectName("secondary")
            script_btn.setToolTip("Select a .py file to run with this framework")
            script_btn.clicked.connect(lambda checked, a=app_def: self._launch_script(a))
            btn_layout.addWidget(script_btn)

        # Educational: Copy Command button — compact, visible icon button
        copy_cmd_btn = QPushButton("📋")
        copy_cmd_btn.setFixedWidth(38)
        copy_cmd_btn.setFixedHeight(32)
        copy_cmd_btn.setStyleSheet(
            "QPushButton { background-color: #313244; border: 1px solid #45475a; "
            "border-radius: 6px; font-size: 16px; padding: 0px; }"
            "QPushButton:hover { background-color: #45475a; border-color: #89b4fa; }"
        )

        # Build install + run commands (env-type aware)
        pkg_name = app_def["package"]
        _env_type = getattr(self, "_current_env_type", "venv")
        is_system_app = app_def.get("system_app", False)

        if is_system_app:
            # System apps: show system-level commands, not pip
            from src.utils.platform_utils import get_platform as _gp
            _plat = _gp()
            _sys_cmds = app_def.get("system_commands", {})
            _cmd_list = _sys_cmds.get(_plat, _sys_cmds.get("linux", []))
            _conda_pkgs = app_def.get("conda_packages", [])

            if _conda_pkgs and _env_type == "conda":
                _channels = app_def.get("conda_channels", ["conda-forge"])
                _ch_flag = " ".join(f"-c {c}" for c in _channels)
                install_cmd = f"conda install {_ch_flag} {' '.join(_conda_pkgs)}"
            elif _conda_pkgs:
                _channels = app_def.get("conda_channels", ["conda-forge"])
                _ch_flag = " ".join(f"-c {c}" for c in _channels)
                install_cmd = f"conda install {_ch_flag} {' '.join(_conda_pkgs)}"
            else:
                install_cmd = f"Install {app_def['name']} from official website"

            run_cmd = " ".join(_cmd_list) if _cmd_list else app_def["name"].lower()
        else:
            _install_prefixes = {
                "venv": "pip install", "uv": "uv pip install",
                "poetry": "poetry add",
                "conda": "conda install", "pipx": "pipx install",
            }
            install_cmd = f"{_install_prefixes.get(_env_type, 'pip install')} {pkg_name}"
            run_parts = app_def.get("command", [])
            if run_parts:
                run_cmd = "python " + " ".join(run_parts)
            else:
                run_cmd = f"python -m {pkg_name}"

        copy_cmd_btn.setToolTip(
            f"<p style='font-size:13px; font-weight:bold; color:#a6e3a1;'>"
            f"💡 Terminal commands for {app_def['name']}:</p>"
            f"<p style='font-size:15px; font-family:Consolas,monospace; color:#cdd6f4; "
            f"background-color:#1e1e2e; padding:6px; border-radius:4px;'>"
            f"1️⃣ {install_cmd}<br>"
            f"2️⃣ {run_cmd}</p>"
            f"<p style='font-size:11px; color:#6c7086;'>Click to copy both commands</p>"
        )
        copy_cmd_btn.clicked.connect(
            lambda checked, ic=install_cmd, rc=run_cmd, nm=app_def["name"]: self._copy_launcher_commands(ic, rc, nm)
        )
        btn_layout.addWidget(copy_cmd_btn)

        layout.addLayout(btn_layout)

        # Buttons row 2: Uninstall + Shortcut
        btn_layout2 = QHBoxLayout()

        uninstall_btn = QPushButton(f"🗑 {tr('uninstall') if tr('uninstall') != 'uninstall' else 'Uninstall'}")
        uninstall_btn.setObjectName("danger")
        uninstall_btn.setVisible(False)
        uninstall_btn.clicked.connect(lambda checked, a=app_def: self._uninstall_app(a))
        btn_layout2.addWidget(uninstall_btn)

        shortcut_btn = QPushButton(f"📌 {tr('create_shortcut') if tr('create_shortcut') != 'create_shortcut' else 'Shortcut'}")
        shortcut_btn.setObjectName("secondary")
        shortcut_btn.setVisible(False)
        shortcut_btn.clicked.connect(lambda checked, a=app_def: self._create_desktop_shortcut(a))
        btn_layout2.addWidget(shortcut_btn)

        layout.addLayout(btn_layout2)

        # Store refs
        card._app_def = app_def
        card._status_label = status
        card._launch_btn = launch_btn
        card._uninstall_btn = uninstall_btn
        card._shortcut_btn = shortcut_btn
        card._copy_cmd_btn = copy_cmd_btn

        return card

    def _update_launcher_status(self):
        """Update launcher cards to show installed/not-installed status."""
        # Get current env Python version — use cache to avoid subprocess on every call
        env_py_version = None
        if self.pip_manager:
            venv_key = str(self.pip_manager.venv_path)
            if venv_key in self._launcher_py_version_cache:
                env_py_version = self._launcher_py_version_cache[venv_key]
            else:
                try:
                    python_exe = get_python_executable(self.pip_manager.venv_path)
                    from src.utils.platform_utils import subprocess_args
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        **subprocess_args(capture_output=True, text=True, timeout=5)
                    )
                    ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                    env_py_version = tuple(int(x) for x in ver_str.split(".")[:2])
                    self._launcher_py_version_cache[venv_key] = env_py_version
                except Exception:
                    pass

        for name, card in self.launcher_cards.items():
            app_def = card._app_def
            pkg = app_def["package"].lower()
            is_system_app = app_def.get("system_app", False)

            # Update copy command tooltip for current env type
            _env_type = getattr(self, "_current_env_type", "venv")
            if hasattr(card, "_copy_cmd_btn"):
                _pkg_name = app_def["package"]
                if is_system_app:
                    from src.utils.platform_utils import get_platform as _gp_upd
                    _plat_upd = _gp_upd()
                    _sys_cmds_upd = app_def.get("system_commands", {})
                    _cmd_list_upd = _sys_cmds_upd.get(_plat_upd, _sys_cmds_upd.get("linux", []))
                    _conda_pkgs_upd = app_def.get("conda_packages", [])
                    if _conda_pkgs_upd:
                        _channels_upd = app_def.get("conda_channels", ["conda-forge"])
                        _ch_flag_upd = " ".join(f"-c {c}" for c in _channels_upd)
                        _ic = f"conda install {_ch_flag_upd} {' '.join(_conda_pkgs_upd)}"
                    else:
                        _ic = f"Install {app_def['name']} from official website"
                    _rc = " ".join(_cmd_list_upd) if _cmd_list_upd else app_def["name"].lower()
                else:
                    _ip = {
                        "venv": "pip install", "uv": "uv pip install",
                        "poetry": "poetry add",
                        "conda": "conda install", "pipx": "pipx install",
                    }
                    _ic = f"{_ip.get(_env_type, 'pip install')} {_pkg_name}"
                    _rp = app_def.get("command", [])
                    _rc = ("python " + " ".join(_rp)) if _rp else f"python -m {_pkg_name}"
                card._copy_cmd_btn.setToolTip(
                    f"<p style='font-size:13px; font-weight:bold; color:#a6e3a1;'>"
                    f"💡 Terminal commands for {app_def['name']}:</p>"
                    f"<p style='font-size:15px; font-family:Consolas,monospace; color:#cdd6f4; "
                    f"background-color:#1e1e2e; padding:6px; border-radius:4px;'>"
                    f"1️⃣ {_ic}<br>"
                    f"2️⃣ {_rc}</p>"
                    f"<p style='font-size:11px; color:#6c7086;'>Click to copy both commands</p>"
                )
                # Update click handler with new commands
                try:
                    card._copy_cmd_btn.clicked.disconnect()
                except Exception:
                    pass
                card._copy_cmd_btn.clicked.connect(
                    lambda checked, ic=_ic, rc=_rc, nm=app_def["name"]: self._copy_launcher_commands(ic, rc, nm)
                )

            # System apps: detect via installer's get_exe_path (more thorough than shutil.which)
            if is_system_app:
                # ── Conda env: check conda packages ──────────────────────
                _env_type = getattr(self, "_current_env_type", "venv")
                _env_path = (self.pip_manager.venv_path
                             if self.pip_manager else None)
                if _env_type == "conda" and _env_path:
                    from src.core.micromamba_installer import list_conda_packages
                    _conda_pkgs = app_def.get("conda_packages", [])
                    if _conda_pkgs:
                        # Use cached set to avoid repeated subprocess per card
                        _cache_key = f"_conda_installed_cache_{_env_path}"
                        if not hasattr(self, _cache_key):
                            setattr(self, _cache_key,
                                    {p.get("name", "").lower()
                                     for p in list_conda_packages(_env_path)})
                        _installed = getattr(self, _cache_key)
                        _found = _conda_pkgs[0].lower() in _installed
                        status = card._status_label
                        card._launch_btn.setEnabled(True)
                        card._launch_btn.setStyleSheet("")
                        card._uninstall_btn.setVisible(False)
                        card._shortcut_btn.setVisible(False)
                        if _found:
                            status.setText("✅ Installed (conda-forge)")
                            status.setStyleSheet(
                                f"color: {self._c()['success']};"
                                f" font-size: {self._c()['fs_tiny']}px;")
                        else:
                            status.setText("❌ Not installed — click Launch to install")
                            status.setStyleSheet(
                                f"color: {self._c()['danger']};"
                                f" font-size: {self._c()['fs_tiny']}px;")
                        continue
                    else:
                        # No conda package defined — check if available on system
                        _env_name = self.env_selector.currentText()
                        import shutil as _shutil
                        from src.utils.platform_utils import get_platform as _gp
                        _sys_cmds = app_def.get("system_commands", {})
                        _exe = (_sys_cmds.get(_gp()) or _sys_cmds.get("linux", [""]))[0]
                        _sys_found = bool(_shutil.which(_exe)) if _exe else False
                        status = card._status_label
                        if _sys_found:
                            status.setText(f"✅ Detected on system, not in {_env_name} env")
                            status.setStyleSheet(
                                f"color: {self._c()['success']};"
                                f" font-size: {self._c()['fs_tiny']}px;")
                            card._launch_btn.setEnabled(True)
                        else:
                            status.setText("❌ Not installed — click Launch to install")
                            status.setStyleSheet(
                                f"color: {self._c()['danger']};"
                                f" font-size: {self._c()['fs_tiny']}px;")
                            card._launch_btn.setEnabled(True)
                        continue
                # ─────────────────────────────────────────────────────────

                from src.core.system_tools_installer import get_installer as _get_installer
                _icon_key = app_def.get("icon_key", "")
                # Use cache to avoid shutil.which on every status update
                if _icon_key and _icon_key in self._system_tool_cache:
                    system_found = self._system_tool_cache[_icon_key]
                else:
                    _installer = _get_installer(_icon_key)
                    if _installer:
                        system_found = _installer.is_installed()
                    else:
                        import shutil as _shutil
                        from src.utils.platform_utils import get_platform as _gp
                        _sys_cmds = app_def.get("system_commands", {})
                        _exe = (_sys_cmds.get(_gp()) or _sys_cmds.get("linux", [""]))[0]
                        system_found = bool(_shutil.which(_exe))
                    if _icon_key:
                        self._system_tool_cache[_icon_key] = system_found

                status = card._status_label
                card._launch_btn.setEnabled(True)
                card._launch_btn.setStyleSheet("")
                card._uninstall_btn.setVisible(False)
                card._shortcut_btn.setVisible(False)
                _env_name = self.env_selector.currentText()
                if system_found:
                    status.setText(f"✅ Detected on system, not in {_env_name} env")
                    status.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_tiny']}px;")
                else:
                    status.setText("⚠️ Not found on system — install separately")
                    status.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_tiny']}px;")
                continue

            pkg_alt = pkg.replace("-", "_") if "-" in pkg else pkg.replace("_", "-")
            is_installed = pkg in self.installed_package_names or pkg_alt in self.installed_package_names

            # Check Python version compatibility
            py_incompatible = False
            if env_py_version:
                max_py = app_def.get("max_python")
                min_py = app_def.get("min_python")
                if max_py:
                    max_parts = tuple(int(x) for x in max_py.split(".")[:2])
                    if env_py_version > max_parts:
                        py_incompatible = True
                if min_py:
                    min_parts = tuple(int(x) for x in min_py.split(".")[:2])
                    if env_py_version < min_parts:
                        py_incompatible = True

            status = card._status_label
            if py_incompatible and not is_installed:
                py_range = ""
                if min_py and max_py:
                    py_range = f"Python {min_py}–{max_py}"
                elif max_py:
                    py_range = f"Python ≤{max_py}"
                elif min_py:
                    py_range = f"Python ≥{min_py}"
                status.setText(f"⚠️ Requires {py_range}")
                status.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_tiny']}px;")
                card._launch_btn.setEnabled(False)
                card._launch_btn.setStyleSheet(f"background-color: {self._c()['disabled_bg']}; color: {self._c()['disabled_fg']};")
                card._uninstall_btn.setVisible(False)
                card._shortcut_btn.setVisible(False)
            elif is_installed:
                status.setText("✅ Installed")
                status.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_tiny']}px;")
                card._launch_btn.setEnabled(True)
                card._launch_btn.setStyleSheet("")
                card._uninstall_btn.setVisible(True)
                card._shortcut_btn.setVisible(True)
            else:
                status.setText(f"❌ Not installed — click Launch to install first")
                status.setStyleSheet(f"color: {self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
                card._launch_btn.setEnabled(True)  # Will prompt install
                card._launch_btn.setStyleSheet("")
                card._uninstall_btn.setVisible(False)
                card._shortcut_btn.setVisible(False)

        # Update quick sidebar
        self._update_quick_sidebar()

    def _update_quick_sidebar(self):
        """Update sidebar buttons — show only installed apps."""
        if not hasattr(self, "_sidebar_buttons"):
            return
        # Remove old buttons
        for btn in self._sidebar_buttons.values():
            self._sidebar_layout.removeWidget(btn)
            btn.deleteLater()
        self._sidebar_buttons = {}

        for name, card in self.launcher_cards.items():
            app_def = card._app_def
            pkg = app_def["package"].lower()
            # System apps: show in sidebar if detected on system
            if app_def.get("system_app"):
                from src.core.system_tools_installer import get_installer as _get_installer
                _installer = _get_installer(app_def.get("icon_key", ""))
                if _installer:
                    if not _installer.is_installed():
                        continue
                else:
                    import shutil as _shutil
                    from src.utils.platform_utils import get_platform as _gp
                    _sys_cmds = app_def.get("system_commands", {})
                    _exe = (_sys_cmds.get(_gp()) or _sys_cmds.get("linux", [""]))[0]
                    if not _shutil.which(_exe):
                        continue  # not found — skip sidebar
            elif pkg not in self.installed_package_names:
                continue
            btn = QPushButton(app_def["icon"])
            btn.setFixedSize(48, 48)
            btn.setToolTip(f"Launch {name}")
            # B183: was hardcoded Catppuccin Mocha #1e1e2e/#313244/#89b4fa
            # which kept these tiles dark even on a light theme. Use
            # palette colours so they follow the active theme.
            _c = self._c()
            _bg = _c.get("input_bg", "#1e1e2e")
            _border = _c.get("border", "#313244")
            _hover_bg = _c.get("active", _c.get("secondary", "#313244"))
            _hover_border = _c.get("accent", "#89b4fa")
            _pressed_bg = _c.get("muted", "#45475a")
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  font-size: 22px;"
                f"  background-color: {_bg};"
                f"  border: 1px solid {_border};"
                f"  border-radius: 8px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {_hover_bg};"
                f"  border-color: {_hover_border};"
                f"}}"
                f"QPushButton:pressed {{"
                f"  background-color: {_pressed_bg};"
                f"}}"
            )
            btn.clicked.connect(lambda checked, a=app_def: self._launch_app(a))
            self._sidebar_layout.addWidget(btn)
            self._sidebar_buttons[name] = btn

        # Show/hide sidebar based on installed count
        self.quick_sidebar.setVisible(len(self._sidebar_buttons) > 0)

    def _launch_system_app(self, app_def: dict):
        """
        Detect and launch a system-level application.
        Checks: (1) conda install if in conda env, (2) portable install, (3) system PATH.
        Offers appropriate install if not found.
        """
        import shutil as _shutil
        from src.utils.platform_utils import get_platform
        from src.core.system_tools_installer import get_installer

        plat = get_platform()
        name = app_def["name"]
        icon_key = app_def.get("icon_key", "")
        installer = get_installer(icon_key)

        # Detect env type
        env_path = None
        env_type = getattr(self, "_current_env_type", "venv")
        if self.pip_manager:
            vp = self.pip_manager.venv_path
            marker = vp / ".venvstudio_env"
            if marker.exists():
                env_path = vp

        # ── Conda env: use micromamba to install ─────────────────────────
        if env_type == "conda" and env_path:
            conda_pkgs = app_def.get("conda_packages", [])
            conda_channels = app_def.get("conda_channels", ["conda-forge"])

            if not conda_pkgs:
                QMessageBox.information(
                    self, name,
                    f"{name} is not available as a conda package.\n"
                    f"Try switching to a Python or Tool Environment."
                )
                return

            # Check if already installed via conda
            from src.core.micromamba_installer import (
                list_conda_packages, install_conda_packages,
                get_micromamba_exe, download_micromamba,
            )
            installed_pkgs = {p.get("name", "").lower()
                              for p in list_conda_packages(env_path)}
            primary_pkg = conda_pkgs[0].lower()

            if primary_pkg not in installed_pkgs:
                reply = QMessageBox.question(
                    self, f"Install {name}?",
                    f"{name} is not installed in this conda environment.\n\n"
                    f"Install via conda-forge:\n"
                    f"  {', '.join(conda_pkgs)}\n\n"
                    f"Install now?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                self._set_busy(True)
                self.status_label.setText(f"Installing {name} via conda-forge...")

                _env_path = env_path
                _pkgs = conda_pkgs
                _channels = conda_channels

                def _do_conda_install(callback=None):
                    if not get_micromamba_exe():
                        if callback:
                            callback("Downloading micromamba...")
                        download_micromamba(progress_cb=callback)
                    ok = install_conda_packages(
                        _env_path, _pkgs,
                        channels=_channels,
                        progress_cb=callback,
                    )
                    return (ok,
                            f"{name} installed!" if ok
                            else f"{name} conda install failed")

                self.current_worker = WorkerThread(_do_conda_install)
                self.current_worker.progress.connect(self._on_progress)
                self.current_worker.finished.connect(
                    lambda ok, msg, a=app_def:
                        self._on_system_install_finished(ok, msg, a)
                )
                self.current_worker.start()
                return

            # Already installed — find exe in conda env and launch
            conda_bin = env_path / ("Scripts" if plat == "windows" else "bin")
            exe_candidates = [name, name.lower(), name + ".exe",
                              name.upper(), name.upper() + ".exe"]
            exe_path = None
            for candidate in exe_candidates:
                p = conda_bin / candidate
                if p.exists():
                    exe_path = str(p)
                    break
            if not exe_path:
                exe_path = _shutil.which(name) or _shutil.which(name.lower())

            if exe_path:
                self._launch_exe(exe_path, app_def)
            else:
                QMessageBox.information(
                    self, name,
                    f"{name} is installed but executable not found.\n"
                    f"Try launching from terminal:\n"
                    f"  {conda_bin / name.lower()}"
                )
            return
        # ─────────────────────────────────────────────────────────────────

        # 1. Check portable install in env
        exe_path = None
        if installer and env_path:
            exe_path = installer.get_portable_exe(env_path)

        # 2. Check system PATH / known locations
        if not exe_path and installer:
            exe_path = installer.get_system_exe()

        # 3. Fallback: shutil.which using system_commands
        if not exe_path:
            sys_cmds = app_def.get("system_commands", {})
            cmd_parts = sys_cmds.get(plat) or sys_cmds.get("linux", [])
            if cmd_parts:
                exe_path = _shutil.which(cmd_parts[0])

        # 4. Not found — offer install
        if not exe_path:
            if installer is None:
                QMessageBox.information(
                    self, f"{name} — Not Found",
                    f"{name} is not installed.\n\nPlease install it manually."
                )
                return

            # Choose install mode
            if env_path:
                msg = (
                    f"{name} is not installed.\n\n"
                    f"VenvStudio can install it portably into this environment:\n"
                    f"  {env_path / 'apps' / icon_key}\n\n"
                    f"No system-wide changes will be made.\n"
                    f"Install {name} now?"
                )
            else:
                msg = (
                    f"{name} is not installed.\n\n"
                    f"VenvStudio can download and install it automatically.\n"
                    f"Install {name} now?"
                )

            reply = QMessageBox.question(
                self, f"Install {name}?", msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            self._set_busy(True)
            self.status_label.setText(f"Installing {name}...")

            _env_path = env_path  # capture for closure

            def _do_install(callback=None):
                ok = installer.install(
                    env_path=_env_path,
                    progress_cb=callback,
                    portable=(_env_path is not None),
                )
                return (ok,
                        f"{name} installed successfully" if ok
                        else f"{name} installation failed")

            self.current_worker = WorkerThread(_do_install)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(
                lambda ok, msg, a=app_def: self._on_system_install_finished(ok, msg, a)
            )
            self.current_worker.start()
            return

        # 5. Found — launch
        self._launch_exe(exe_path, app_def)

    def _launch_exe(self, exe_path: str, app_def: dict):
        """Launch an executable with proper detach/console flags."""
        from src.utils.platform_utils import get_platform
        plat = get_platform()
        name = app_def["name"]
        sys_cmds = app_def.get("system_commands", {})
        cmd_parts = sys_cmds.get(plat) or sys_cmds.get("linux", [exe_path])
        cmd = [exe_path] + list(cmd_parts[1:])
        work_dir = os.path.expanduser("~")
        try:
            show_console = app_def.get("needs_console", False)
            if plat == "windows":
                if show_console:
                    subprocess.Popen(cmd, cwd=work_dir,
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(cmd, cwd=work_dir,
                                     creationflags=0x00000008 | 0x08000000,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            else:
                if show_console:
                    from src.gui.platform_utils import launch_in_terminal
                    terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                    launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)
                else:
                    from src.utils.platform_utils import appimage_clean_env
                    _ai_env = appimage_clean_env()
                    _popen_kw2 = dict(cwd=work_dir, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, start_new_session=True)
                    if _ai_env is not None:
                        _popen_kw2["env"] = _ai_env
                    subprocess.Popen(cmd, **_popen_kw2)
            self.status_label.setText(f"✅ {name} launched")
            url = app_def.get("open_browser")
            if url:
                from PySide6.QtCore import QTimer
                import webbrowser
                delay = app_def.get("browser_delay", 2)
                QTimer.singleShot(delay * 1000, lambda: webbrowser.open(url))
        except Exception as e:
            QMessageBox.critical(self, f"{name} — Launch Error", str(e))

    def _on_system_install_finished(self, success: bool, message: str, app_def: dict):
        """Called after a system tool silent install completes."""
        self._set_busy(False)
        # Invalidate system tool cache so is_installed re-checks
        self._system_tool_cache.clear()
        name = app_def["name"]
        if success:
            self.status_label.setText(f"✅ {name} installed. Launching...")
            # Invalidate conda package cache so status refreshes correctly
            if self.pip_manager:
                _cache_key = f"_conda_installed_cache_{self.pip_manager.venv_path}"
                if hasattr(self, _cache_key):
                    delattr(self, _cache_key)
                # B141: refresh env table too (conda pkg count changes)
                try:
                    from src.core.venv_manager import VenvManager
                    _vm = self._get_venv_manager(self.pip_manager.venv_path.parent)
                    _vm.invalidate_cache(self.pip_manager.venv_path)
                except Exception:
                    pass
            # B182 follow-up: refresh the Packages page header (size + pkg
            # count) after a system tool install. Without this the badge
            # at the top would stay stale until the user navigates away.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            self.env_refresh_requested.emit(-1)
            # Refresh card states then launch
            self._update_launcher_status()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._launch_system_app(app_def))
        else:
            self.status_label.setText(f"❌ {name} install failed")
            QMessageBox.critical(
                self, f"{name} — Install Failed",
                f"Could not install {name} automatically.\n\n"
                f"{message}\n\n"
                f"Please install it manually and try again.\n"
            )

    def _get_orange3_packages(self, python_exe) -> list:
        """Return the right Orange3 packages based on Python version.
        Orange3 requires PyQt5 + PyQtWebEngine (uses AnyQt, does not support PySide6).
        chardet<4.0 required for Orange.data.io_util compatibility.
        """
        try:
            from src.utils.platform_utils import subprocess_args
            result = subprocess.run(
                [str(python_exe), "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            ver_parts = tuple(int(x) for x in ver_str.split(".")[:2])
        except Exception:
            ver_parts = (3, 11)  # safe default

        if ver_parts <= (3, 9):
            return ["PyQt5", "PyQtWebEngine", "chardet<4.0", "orange3<=3.36.2"]
        else:
            return ["PyQt5", "PyQtWebEngine", "chardet<4.0", "orange3"]

    def _launch_script(self, app_def: dict):
        """Let user pick a .py file and run it with the selected framework."""
        import os
        from PySide6.QtWidgets import QFileDialog

        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, f"Select Python script for {app_def['name']}", "",
            "Python Files (*.py);;All Files (*)"
        )
        if not filepath:
            return

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)
        work_dir = os.path.dirname(filepath)
        pkg = app_def["package"].lower()

        # Build command based on framework
        if pkg == "streamlit":
            cmd = [str(python_exe), "-m", "streamlit", "run", filepath, "--server.headless", "true"]
            url = "http://localhost:8501"
        elif pkg == "dash":
            cmd = [str(python_exe), filepath]
            url = "http://localhost:8050"
        elif pkg == "gradio":
            cmd = [str(python_exe), filepath]
            url = "http://localhost:7860"
        elif pkg == "fastapi":
            # Extract module name for uvicorn
            module = os.path.splitext(os.path.basename(filepath))[0]
            cmd = [str(python_exe), "-m", "uvicorn", f"{module}:app", "--reload"]
            url = "http://localhost:8000/docs"
        elif pkg == "panel":
            cmd = [str(python_exe), "-m", "panel", "serve", filepath, "--show"]
            url = ""
        elif pkg == "voila":
            cmd = [str(python_exe), "-m", "voila", filepath]
            url = "http://localhost:8866"
        elif pkg == "mlflow":
            cmd = [str(python_exe), filepath]
            url = ""
        elif pkg == "tensorboard":
            cmd = [str(python_exe), "-m", "tensorboard.main", "--logdir", work_dir]
            url = "http://localhost:6006"
        elif pkg == "datasette":
            cmd = [str(python_exe), "-m", "datasette", filepath]
            url = "http://localhost:8001"
        else:
            cmd = [str(python_exe), filepath]
            url = ""

        try:
            from src.utils.platform_utils import get_platform
            import subprocess
            if get_platform() == "windows":
                subprocess.Popen(cmd, cwd=work_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                from src.gui.platform_utils import launch_in_terminal
                terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)

            self.status_label.setText(f"🚀 Running {os.path.basename(filepath)}")

            if url:
                import threading, webbrowser, time as _t
                def _open(u):
                    _t.sleep(3)
                    webbrowser.open(u)
                threading.Thread(target=_open, args=(url,), daemon=True).start()

        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"Failed to launch script:\n{e}")

    def _launch_app(self, app_def: dict):
        """Launch an app from the selected environment."""
        import os
        from PySide6.QtWidgets import QFileDialog

        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        # ── System-level app (R, RStudio, Ollama, DBeaver, Quarto…) ─────────
        if app_def.get("system_app"):
            self._launch_system_app(app_def)
            return

        # TensorBoard and similar tools need a log directory
        if app_def.get("pick_logdir", False):
            logdir = QFileDialog.getExistingDirectory(
                self,
                f"Select log directory for {app_def['name']}",
                os.path.expanduser("~")
            )
            if not logdir:
                return
            # Replace "." in command with chosen dir
            app_def = dict(app_def)
            app_def["command"] = [
                c if c != "." else logdir for c in app_def["command"]
            ]

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)

        pkg_name = app_def["package"].lower()
        # pip normalizes package names: quarto-cli ↔ quarto_cli — check both
        pkg_name_alt = pkg_name.replace("-", "_") if "-" in pkg_name else pkg_name.replace("_", "-")
        is_installed = pkg_name in self.installed_package_names or pkg_name_alt in self.installed_package_names

        if not is_installed:
            # Check min/max Python version if specified
            min_py = app_def.get("min_python")
            max_py = app_def.get("max_python")
            note = app_def.get("note", "")
            if min_py or max_py:
                try:
                    from src.utils.platform_utils import subprocess_args
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        **subprocess_args(capture_output=True, text=True, timeout=5)
                    )
                    ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                    ver_parts = tuple(int(x) for x in ver_str.split(".")[:2])

                    if min_py:
                        min_parts = tuple(int(x) for x in min_py.split(".")[:2])
                        if ver_parts < min_parts:
                            QMessageBox.warning(
                                self, app_def["name"],
                                f"{app_def['name']} requires Python ≥{min_py}\n"
                                f"This environment uses Python {ver_str}.\n\n"
                                f"Create a new environment with Python ≥{min_py} and try again."
                            )
                            return

                    if max_py:
                        max_parts = tuple(int(x) for x in max_py.split(".")[:2])
                        if ver_parts > max_parts:
                            QMessageBox.warning(
                                self, app_def["name"],
                                f"{app_def['name']} supports Python {min_py or '3.x'}–{max_py} only.\n"
                                f"This environment uses Python {ver_str}.\n\n"
                                f"Create a new environment with Python ≤{max_py} and try again."
                            )
                            return
                except Exception:
                    pass

            msg = f"{app_def['name']} is not installed in this environment.\n\nInstall '{app_def['package']}' now?"
            if note:
                msg += f"\n\nNote: {note}"

            reply = QMessageBox.question(
                self, app_def["name"], msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            # Install it — determine packages to install
            pkgs_to_install = app_def.get("install_packages", [app_def["package"]])

            # Dynamic package resolution for Orange3 based on Python version
            if app_def["package"] == "orange3":
                pkgs_to_install = self._get_orange3_packages(python_exe)
            self._set_busy(True)
            self.status_label.setText(f"Installing {', '.join(pkgs_to_install)}...")

            # pipx env: use pipx install instead of pip
            if getattr(self, "_current_env_type", "venv") == "pipx":
                import shutil as _shutil
                _pipx_bin = _shutil.which("pipx")
                _pipx_python = None
                if self.pip_manager and self.pip_manager.venv_path:
                    _marker = self.pip_manager.venv_path / ".venvstudio_env"
                    if _marker.exists():
                        try:
                            import json as _json
                            with open(_marker) as _mf:
                                _mdata = _json.load(_mf)
                            _pipx_python = _mdata.get("python_path", "")
                        except Exception:
                            pass
                def _do_pipx_launch_install(callback=None):
                    import subprocess, sys
                    from src.utils.platform_utils import subprocess_args
                    failed = []
                    for pkg in pkgs_to_install:
                        if callback:
                            callback(f"pipx install {pkg}...")
                        cmd = [_pipx_bin, "install", pkg] if _pipx_bin else [sys.executable, "-m", "pipx", "install", pkg]
                        if _pipx_python:
                            cmd += ["--python", _pipx_python]
                        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, **subprocess_args())
                        if r.returncode != 0:
                            failed.append(pkg)
                    if failed:
                        return (False, f"pipx install failed for: {', '.join(failed)}")
                    return (True, f"pipx installed: {', '.join(pkgs_to_install)}")
                self.current_worker = WorkerThread(_do_pipx_launch_install)
            else:
                self.current_worker = WorkerThread(
                    self.pip_manager.install_packages, pkgs_to_install
                )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(
                lambda ok, msg, a=app_def: self._on_app_install_finished(ok, msg, a)
            )
            self.current_worker.start()
            return

        # Launch the app — check console toggle
        # pipx env: find app executable in pipx venv or local bin
        if getattr(self, "_current_env_type", "venv") == "pipx":
            from src.utils.platform_utils import get_pipx_home, get_platform as _gp
            import os as _os, shutil as _sh
            _pipx_home = get_pipx_home()
            _pkg = app_def["package"].lower()
            _app_cmd = app_def.get("command", [])
            _is_win = _gp() == "windows"
            _exe_suffix = ".exe" if _is_win else ""
            _scripts_dir = "Scripts" if _is_win else "bin"
            # Package -> primary executable name mapping
            _pipx_exe_map = {
                "jupyterlab":  "jupyter-lab",
                "notebook":    "jupyter-notebook",
                "orange3":     "orange-canvas",
                "spyder":      "spyder",
                "ipython":     "ipython",
                "streamlit":   "streamlit",
                "gradio":      "gradio",
                "dash":        "dash",
                "panel":       "panel",
                "voila":       "voila",
                "mlflow":      "mlflow",
                "tensorboard": "tensorboard",
                "marimo":      "marimo",
                "datasette":   "datasette",
            }
            _exe_name = _pipx_exe_map.get(_pkg)
            if not _exe_name:
                # fallback: derive from command "-m jupyter lab" -> "jupyter"
                if len(_app_cmd) >= 2 and _app_cmd[0] == "-m":
                    _exe_name = _app_cmd[1].split(".")[0]
                else:
                    _exe_name = _pkg
            _exe_path = None
            # 1. pipx venvs/<pkg>/Scripts/<exe>
            if _pipx_home:
                _venv_exe = _os.path.join(_pipx_home, "venvs", _pkg,
                    _scripts_dir, _exe_name + _exe_suffix)
                if _os.path.isfile(_venv_exe):
                    _exe_path = _venv_exe
            # 2. ~/.local/bin/<exe> (pipx exposed apps)
            if not _exe_path:
                _local_bin = _os.path.join(_os.path.expanduser("~"), ".local", "bin", _exe_name + _exe_suffix)
                if _os.path.isfile(_local_bin):
                    _exe_path = _local_bin
            # 3. shutil.which (PATH)
            if not _exe_path:
                _exe_path = _sh.which(_exe_name)
            if _exe_path:
                cmd = [_exe_path]
            else:
                # fallback: python -m ...
                cmd = [str(python_exe)] + _app_cmd
        else:
            cmd = [str(python_exe)] + app_def["command"]

        # Check if app needs console (e.g. IPython)
        show_console = app_def.get("needs_console", False)

        # Working directory — Jupyter uses config setting, others use home
        is_jupyter = any("jupyter" in str(c).lower() for c in app_def.get("command", []))
        if is_jupyter:
            jwd = self.config.get("jupyter_workdir", "home") if hasattr(self, "config") and self.config else "home"
            jwd_custom = self.config.get("jupyter_workdir_custom", "") if hasattr(self, "config") and self.config else ""
            if jwd == "custom" and jwd_custom and os.path.isdir(jwd_custom):
                notebook_dir = jwd_custom
            elif jwd == "env":
                notebook_dir = str(venv_path)
            else:
                notebook_dir = os.path.expanduser("~")
            work_dir = notebook_dir
            # Pass --notebook-dir so Jupyter actually opens in the chosen folder
            app_def = dict(app_def)
            app_def["command"] = list(app_def["command"]) + ["--notebook-dir", notebook_dir]
        elif get_platform() == "windows":
            work_dir = os.environ.get("USERPROFILE", "C:\\")
        else:
            work_dir = os.environ.get("HOME", os.path.expanduser("~"))

        try:
            if get_platform() == "windows":
                if show_console:
                    subprocess.Popen(
                        cmd, cwd=work_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                else:
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NO_WINDOW = 0x08000000
                    subprocess.Popen(
                        cmd, cwd=work_dir,
                        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                    )
            else:
                if show_console:
                    from src.gui.platform_utils import launch_in_terminal
                    terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                    launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)
                else:
                    from src.utils.platform_utils import appimage_clean_env
                    _ai_env = appimage_clean_env()
                    _popen_kw = dict(
                        cwd=work_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    if _ai_env is not None:
                        _popen_kw["env"] = _ai_env
                    subprocess.Popen(cmd, **_popen_kw)

            self.status_label.setText(f"🚀 Launched {app_def['name']}")

            # Open browser if app requested it (e.g. Streamlit, Jupyter)
            open_browser_url = app_def.get("open_browser", "")
            if open_browser_url:
                import threading, webbrowser, time as _time
                delay = app_def.get("browser_delay", 3)
                def _open_browser(url, d):
                    _time.sleep(d)
                    webbrowser.open(url)
                threading.Thread(target=_open_browser, args=(open_browser_url, delay), daemon=True).start()

        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                f"Failed to launch {app_def['name']}:\n{e}"
            )

    def _on_app_install_finished(self, success, message, app_def):
        """After installing an app package, refresh and launch."""
        self._set_busy(False)
        if success:
            # ── Orange3 AppImage post-install verification ──────────────────
            # On AppImage, PyQt5/.so links can be broken even when pip reports
            # success. Verify with a clean-env import test before launching.
            if app_def.get("package") == "orange3" and self.pip_manager:
                import os, sys
                from src.utils.platform_utils import subprocess_args, get_platform
                if os.environ.get("APPIMAGE") or getattr(sys, "frozen", False):
                    python_exe = get_python_executable(self.pip_manager.venv_path)
                    sp_kw = subprocess_args(capture_output=True, text=True, timeout=20)
                    # subprocess_args already strips LD_LIBRARY_PATH etc on AppImage
                    try:
                        verify = subprocess.run(
                            [str(python_exe), "-c",
                             "import PyQt5; import Orange; print('OK')"],
                            **sp_kw
                        )
                        if verify.returncode != 0 or "OK" not in verify.stdout:
                            err = verify.stderr.strip() or verify.stdout.strip()
                            QMessageBox.warning(
                                self, "Orange3 — Import Check Failed",
                                "Orange3 was installed but could not be imported.\n\n"
                                "This usually means a library conflict with the AppImage "
                                "environment.\n\n"
                                f"Details:\n{err[:600]}\n\n"
                                "Workaround: install VenvStudio via pip instead of AppImage, "
                                "or run Orange3 directly from its own conda environment."
                            )
                            self.status_label.setText("⚠️ Orange3 installed but import failed — see warning")
                            self._invalidate_pkg_cache()
                            self._async_refresh_packages(force=True)
                            return
                    except Exception:
                        pass  # verification failed silently — proceed optimistically
            # ────────────────────────────────────────────────────────────────
            self.status_label.setText(f"✅ {app_def['package']} installed. Launching...")
            # Must wait for package list to refresh before launching,
            # otherwise installed_package_names won't contain the new package
            # and _launch_app will show the install dialog again.
            self._invalidate_pkg_cache()

            # ── B141: Tell main_window to refresh the env table ─────────────
            # When installing to a pipx env (and any other env type), the env
            # row in the main table shows stale package count / size. Signal
            # the parent so it re-queries list_venvs_fast with force=True.
            try:
                from src.core.venv_manager import VenvManager
                _vm = self._get_venv_manager(self.pip_manager.venv_path.parent)  # base_dir
                _vm.invalidate_cache(self.pip_manager.venv_path)
                # For pipx we also invalidate the shared pipx tree — many apps share
                # /pipx cache state.
                venv_path_str = str(self.pip_manager.venv_path)
                if "pipx" in venv_path_str.lower():
                    _vm.invalidate_all_caches()
            except Exception:
                pass
            # B182 follow-up: refresh the Packages page header (size + pkg
            # count) after a launch app install. Without this the badge
            # at the top would stay stale until the user navigates away.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            self.env_refresh_requested.emit(-1)
            # ─────────────────────────────────────────────────────────────────

            self._async_refresh_packages(force=True)
            # Connect one-shot signal to launch after refresh completes
            def _launch_after_refresh():
                try:
                    self._pkg_loader.done.disconnect(_launch_after_refresh)
                except Exception:
                    pass
                self._launch_app(app_def)
            if self._pkg_loader:
                self._pkg_loader.done.connect(_launch_after_refresh)
            else:
                self._launch_app(app_def)
        else:
            self.status_label.setText(tr("operation_failed"))
            from src.utils.platform_utils import get_platform
            platform = get_platform()

            # Detect Python version for better error messages
            py_ver_str = ""
            try:
                python_exe = get_python_executable(self.pip_manager.venv_path)
                from src.utils.platform_utils import subprocess_args
                result = subprocess.run(
                    [str(python_exe), "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=5)
                )
                py_ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                pass

            short_msg = f"Failed to install {app_def['package']}.\n\n"

            if "No matching distribution" in message or "Could not find" in message:
                short_msg += (
                    f"No compatible version found for Python {py_ver_str}.\n\n"
                    f"This package may not support your Python version yet.\n"
                    f"Try creating an environment with Python 3.12 or 3.13."
                )
            elif "error: subprocess-exited-with-error" in message or "build" in message.lower():
                if platform == "windows":
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install Visual C++ Build Tools:\n"
                        "https://visualstudio.microsoft.com/visual-cpp-build-tools/"
                    )
                elif platform == "macos":
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install Xcode Command Line Tools:\n"
                        "xcode-select --install"
                    )
                else:
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install build tools:\n"
                        "sudo apt install build-essential python3-dev"
                    )
                if py_ver_str and tuple(int(x) for x in py_ver_str.split(".")[:2]) >= (3, 14):
                    short_msg += (
                        f"\n\n⚠️ Python {py_ver_str} is very new.\n"
                        f"Many packages don't have pre-built wheels yet.\n"
                        f"Consider using Python 3.12 or 3.13."
                    )
            elif "Permission" in message:
                short_msg += "Permission denied. Try running as administrator."
            else:
                lines = [l.strip() for l in message.strip().splitlines() if l.strip()]
                tail = "\n".join(lines[-5:]) if len(lines) > 5 else "\n".join(lines)
                short_msg += tail

            note = app_def.get("note", "")
            if note:
                short_msg += f"\n\nNote: {note}"

            QMessageBox.critical(self, tr("error"), short_msg)

    def _uninstall_app(self, app_def: dict):
        """Uninstall an app from the selected environment with confirmation."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        pkg_name = app_def["package"]
        # Get all packages to uninstall
        pkgs_to_remove = app_def.get("install_packages", [pkg_name])

        reply = QMessageBox.question(
            self, f"Uninstall {app_def['name']}",
            f"Are you sure you want to uninstall {app_def['name']}?\n\n"
            f"Packages to remove: {', '.join(pkgs_to_remove)}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.status_label.setText(f"Uninstalling {app_def['name']}...")
        self.current_worker = WorkerThread(
            self.pip_manager.uninstall_packages, pkgs_to_remove
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _get_app_icon_path(self, app_def: dict) -> str | None:
        """Return the absolute path to the app's .ico (Windows) or .png (Linux/macOS) icon."""
        icon_key = app_def.get("icon_key", "")
        if not icon_key:
            return None

        # Determine base dir: frozen (PyInstaller) vs source
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS) / "assets" / "app_icons"
        else:
            base = Path(__file__).resolve().parent.parent.parent / "assets" / "app_icons"

        platform = get_platform()
        if platform == "windows":
            icon = base / f"{icon_key}.ico"
        else:
            icon = base / f"{icon_key}_256.png"

        return str(icon) if icon.exists() else None

    def _create_desktop_shortcut(self, app_def: dict):
        """Create a desktop shortcut for the app — .lnk (Windows), .desktop (Linux), .command (macOS)."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)
        app_name = app_def["name"]
        env_name = venv_path.name
        shortcut_name = f"{app_name} ({env_name})"
        icon_path = self._get_app_icon_path(app_def)
        needs_console = app_def.get("needs_console", False)

        platform = get_platform()
        desktop = Path.home() / "Desktop"

        try:
            if platform == "windows":
                self._create_windows_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, needs_console, venv_path
                )
            elif platform == "linux":
                self._create_linux_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, venv_path
                )
            elif platform == "macos":
                self._create_macos_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, venv_path
                )

            # Show success
            QMessageBox.information(
                self, tr("success"),
                tr("shortcut_created").format(app=app_name) + f"\n\n📁 Desktop / {shortcut_name}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                f"Failed to create shortcut:\n{e}"
            )

    def _create_windows_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, needs_console, venv_path):
        """Create Windows .lnk shortcut via PowerShell (no COM dependency)."""
        args_str = " ".join(cmd_args)
        lnk_path = desktop / f"{name}.lnk"

        # Use PowerShell to create .lnk — works without pywin32
        # WindowStyle: 1=Normal, 7=Minimized; for GUI apps we hide console
        window_style = 1 if needs_console else 7
        icon_line = f'$s.IconLocation = "{icon_path}"' if icon_path else ""

        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{lnk_path}")
$s.TargetPath = "{python_exe}"
$s.Arguments = "{args_str}"
$s.WorkingDirectory = "{venv_path}"
$s.WindowStyle = {window_style}
{icon_line}
$s.Description = "Launched via VenvStudio"
$s.Save()
'''
        # Write temp .ps1 and execute
        ps_file = desktop / f"_venvstudio_shortcut_tmp.ps1"
        ps_file.write_text(ps_script, encoding="utf-8")
        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_file)],
                capture_output=True, text=True, timeout=15,
                **subprocess_args()
            )
            if result.returncode != 0:
                raise RuntimeError(f"PowerShell error: {result.stderr.strip()}")
        finally:
            ps_file.unlink(missing_ok=True)

        # For GUI apps, also create a hidden-console .bat wrapper
        if not needs_console:
            bat_path = venv_path / "scripts" / f"launch_{name.replace(' ', '_')}.bat"
            bat_path.parent.mkdir(parents=True, exist_ok=True)
            bat_content = f'@echo off\nstart "" /B "{python_exe}" {args_str}\n'
            bat_path.write_text(bat_content, encoding="utf-8")

    def _create_linux_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, venv_path):
        """Create Linux .desktop file with icon."""
        desktop_file = desktop / f"{name}.desktop"
        args_str = " ".join(cmd_args)

        icon_line = f"Icon={icon_path}" if icon_path else ""
        content = (
            f"[Desktop Entry]\n"
            f"Type=Application\n"
            f"Name={name}\n"
            f"Exec={python_exe} {args_str}\n"
            f"Path={venv_path}\n"
            f"Terminal=false\n"
            f"{icon_line}\n"
            f"Comment=Launched via VenvStudio\n"
        )
        desktop_file.write_text(content, encoding="utf-8")
        os.chmod(str(desktop_file), 0o755)

    def _create_macos_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, venv_path):
        """Create macOS .command script."""
        sh_path = desktop / f"{name}.command"
        args_str = " ".join(cmd_args)
        content = f'#!/bin/bash\ncd "{venv_path}"\n"{python_exe}" {args_str}\n'
        sh_path.write_text(content, encoding="utf-8")
        os.chmod(str(sh_path), 0o755)

    def _create_installed_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter installed packages...")
        self.search_input.textChanged.connect(self._filter_installed)
        toolbar.addWidget(self.search_input, 1)

        refresh_btn = QPushButton(f"🔄 {tr('refresh')}")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh_packages)
        toolbar.addWidget(refresh_btn)

        self.update_btn = QPushButton(f"⬆️ {tr('check_outdated')}")
        self.update_btn.setObjectName("secondary")
        self.update_btn.clicked.connect(self._check_outdated)
        toolbar.addWidget(self.update_btn)

        self.uninstall_btn = QPushButton(f"🗑️ {tr('uninstall_selected')}")
        self.uninstall_btn.setObjectName("danger")
        self.uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(self.uninstall_btn)

        # Export dropdown button (in toolbar for visibility)
        export_btn = QPushButton("📤 Export ▾")
        export_btn.setObjectName("secondary")
        export_menu = QMenu(export_btn)
        export_menu.addAction("📄 requirements.txt", self._export_requirements)
        export_menu.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_menu.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_menu.addAction("📦 pyproject.toml", self._export_pyproject)
        export_menu.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_menu.addSeparator()
        export_menu.addAction("📋 Copy to Clipboard", self._export_clipboard)
        export_btn.setMenu(export_menu)
        toolbar.addWidget(export_btn)

        import_btn = QPushButton("📥 Import")
        import_btn.setObjectName("secondary")
        import_btn.setToolTip("Import packages from requirements.txt")
        import_btn.clicked.connect(self._import_requirements)
        toolbar.addWidget(import_btn)

        layout.addLayout(toolbar)

        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(3)
        self.packages_table.setHorizontalHeaderLabels(["Package", "Version", ""])
        # B180: PySide6 6.10.2 + Python 3.13.x has a C-level enum→int
        # conversion bug that crashes ANY Qt enum call with the short
        # deprecated form (e.g. Qt.ScrollBarAsNeeded, QHeaderView.Stretch)
        # with `SystemError: longobject.c:1481`. The fix is to use the
        # explicit nested enum path (Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        # QHeaderView.ResizeMode.Stretch) AND wrap in try/except for safety.
        try:
            _hdr = self.packages_table.horizontalHeader()
            _hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            _hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.packages_table.setColumnWidth(2, 40)
            _hdr.setStretchLastSection(False)
            self.packages_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.packages_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.packages_table.setAlternatingRowColors(True)
            self.packages_table.verticalHeader().setVisible(False)
            self.packages_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        except (SystemError, TypeError, AttributeError) as _e:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.qt").warning(
                    f"[B180] Installed table enum setup failed (PySide6/Python 3.13 compat): {_e} "
                    f"— table will use default Qt behaviour"
                )
            except Exception:
                pass
        self.packages_table.customContextMenuRequested.connect(self._pkg_table_context_menu)
        layout.addWidget(self.packages_table)

        bottom = QHBoxLayout()
        self.pkg_count_label = QLabel("0 packages")
        self.pkg_count_label.setStyleSheet("color: #a6adc8;")
        bottom.addWidget(self.pkg_count_label)
        bottom.addStretch()

        layout.addLayout(bottom)
        return widget

    def _create_catalog_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem(tr("all_categories"), "all")
        for cat_name in PACKAGE_CATALOG:
            self.category_combo.addItem(cat_name, cat_name)
        # Add custom categories from config
        from src.core.config_manager import ConfigManager
        try:
            _cfg = self.config if self.config else __import__("src.core.config_manager", fromlist=["ConfigManager"]).ConfigManager()
            custom_cats = _cfg.get("custom_categories", [])
            for c in custom_cats:
                name = c.get("name", "")
                icon = c.get("icon", "⭐")
                full = f"{icon} {name}"
                if full not in [self.category_combo.itemData(i) for i in range(self.category_combo.count())]:
                    self.category_combo.addItem(full, full)
        except Exception:
            pass
        if self.category_combo.findData("⭐ Custom") < 0:
            self.category_combo.addItem("⭐ Custom", "⭐ Custom")
        self.category_combo.currentIndexChanged.connect(self._populate_catalog)
        cat_layout.addWidget(self.category_combo, 1)

        self.catalog_search = QLineEdit()
        self.catalog_search.setPlaceholderText("🔍 Search catalog...")
        self.catalog_search.setFixedWidth(200)
        self.catalog_search.textChanged.connect(self._filter_catalog)
        cat_layout.addWidget(self.catalog_search)

        layout.addLayout(cat_layout)

        legend = QLabel("☑ installed  |  Check→install  Uncheck→remove")
        legend.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self._legend_label = legend
        layout.addWidget(legend)

        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(5)
        self.catalog_table.setHorizontalHeaderLabels(["Install", "Package", "Description", "Category", "Links"])
        # B180: see Installed tab — same PySide6 6.10.2/Python 3.13 enum bug
        try:
            _hdr = self.catalog_table.horizontalHeader()
            _hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            self.catalog_table.setColumnWidth(0, 28)
            _hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            _hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            _hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.catalog_table.setColumnWidth(4, 80)
            _hdr.setStretchLastSection(False)
            self.catalog_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except (SystemError, TypeError, AttributeError) as _e:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.qt").warning(
                    f"[B180] catalog table enum setup failed: {_e}"
                )
            except Exception:
                pass
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.verticalHeader().setVisible(False)
        try:
            self.catalog_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        except (SystemError, TypeError, AttributeError):
            pass
        self.catalog_table.customContextMenuRequested.connect(self._catalog_table_context_menu)
        layout.addWidget(self.catalog_table)

        # Bottom: changes summary + Apply button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.changes_label = QLabel("")
        self.changes_label.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_small']}px;")
        bottom_layout.addWidget(self.changes_label)

        self.apply_btn = QPushButton("  ✅ Apply Changes  ")
        self.apply_btn.setObjectName("success")
        self.apply_btn.setFixedHeight(38)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_catalog_changes)
        bottom_layout.addWidget(self.apply_btn)

        layout.addLayout(bottom_layout)

        self._populate_catalog()
        return widget

    def reload_presets_tab(self):
        """Reload presets tab — called after settings saved to show new custom presets."""
        new_widget = self._create_presets_tab()
        new_label = f"⚡ {tr('presets')}"
        new_tooltip = UI_TOOLTIPS.get("tab_presets", "")

        # Update _tab_defs
        if hasattr(self, "_tab_defs"):
            for idx, (key, label, widget, tooltip) in enumerate(self._tab_defs):
                if key == "presets":
                    old_widget = widget
                    self._tab_defs[idx] = ("presets", new_label, new_widget, new_tooltip)
                    if old_widget:
                        old_widget.deleteLater()
                    break

        # Re-apply tab visibility (will rebuild tabs with new presets widget)
        self._update_tabs_for_env_type()
        self._update_preset_badges()

    def _create_presets_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self._presets_grid = QGridLayout(container)
        self._presets_grid.setSpacing(12)
        self._presets_grid.setContentsMargins(12, 12, 12, 12)

        # Merge built-in + custom presets
        from src.core.config_manager import ConfigManager
        _custom_presets = self._get_config("custom_presets", {})
        _all_presets = {**PRESETS, **_custom_presets}

        self._preset_cards = {}
        row = 0
        for preset_name, packages in _all_presets.items():
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)

            # Header with name + installed badge
            header = QHBoxLayout()
            name_label = QLabel(preset_name)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            header.addWidget(name_label, 1)

            badge = QLabel("")
            badge.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_tiny']}px; font-weight: bold;")
            header.addWidget(badge)
            card_layout.addLayout(header)

            # Educational: Preset description — explains what this preset is for
            preset_desc = PRESET_DESCRIPTIONS.get(preset_name, "")
            if preset_desc:
                desc_label = QLabel(preset_desc)
                desc_label.setWordWrap(True)
                desc_label.setStyleSheet(
                    f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic; "
                    "padding: 4px 0px; line-height: 1.3;"
                )
                card_layout.addWidget(desc_label)

            pkg_text = ", ".join(packages)
            pkg_label = QLabel(pkg_text)
            pkg_label.setWordWrap(True)
            pkg_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
            card_layout.addWidget(pkg_label)

            install_btn = QPushButton(f"{tr('install')} ({len(packages)} packages)")
            install_btn.setObjectName("success")
            install_btn.setToolTip(f"Install all {len(packages)} packages in this preset into the selected environment")
            install_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._install_packages(pkgs, hint_name=name)
            )
            card_layout.addWidget(install_btn)

            uninstall_btn = QPushButton(f"🗑 {tr('uninstall') if tr('uninstall') != 'uninstall' else 'Uninstall'}")
            uninstall_btn.setObjectName("danger")
            uninstall_btn.setVisible(False)
            uninstall_btn.setToolTip("Remove all packages in this preset from the selected environment")
            uninstall_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._uninstall_preset(pkgs, name)
            )
            card_layout.addWidget(uninstall_btn)

            copy_btn = QPushButton(f"📋 {tr('copy_command')}")
            copy_btn.setObjectName("secondary")
            copy_btn._preset_packages = packages  # store for dynamic tooltip update
            copy_btn.clicked.connect(
                lambda checked, pkgs=packages: self._copy_preset_command(pkgs)
            )
            card_layout.addWidget(copy_btn)

            self._preset_cards[preset_name] = {
                "badge": badge,
                "install_btn": install_btn,
                "uninstall_btn": uninstall_btn,
                "copy_btn": copy_btn,
                "packages": packages,
            }

            self._presets_grid.addWidget(card, row // 2, row % 2)
            row += 1

        self._presets_grid.setRowStretch(row // 2 + 1, 1)
        scroll.setWidget(container)
        return scroll

    def _update_preset_badges(self):
        """Update 'Installed' badge on presets."""
        if not hasattr(self, '_preset_cards'):
            return

        # Normalize installed names once
        if self.installed_package_names:
            normalized_installed = set()
            for p in self.installed_package_names:
                normalized_installed.add(p.lower().replace("-", "_").replace(".", "_"))
        else:
            normalized_installed = set()

        for preset_name, info in self._preset_cards.items():
            packages = info["packages"]
            badge = info["badge"]
            install_btn = info["install_btn"]
            uninstall_btn = info.get("uninstall_btn")

            if not normalized_installed:
                badge.setText("")
                install_btn.setText(f"{tr('install')} ({len(packages)} packages)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(False)
                continue

            installed_count = sum(
                1 for p in packages
                if p.lower().replace("-", "_").replace(".", "_") in normalized_installed
            )

            if installed_count == len(packages):
                badge.setText("✅ Installed")
                badge.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px; font-weight: bold;")
                install_btn.setText(f"✅ {tr('installed') if tr('installed') != 'installed' else 'Installed'}")
                install_btn.setEnabled(False)
                # B183: was hardcoded "background:#313244; color:#a6e3a1"
                # (Catppuccin Mocha surface + pastel green) which stayed
                # dark on light themes. Use palette `secondary` (slightly
                # darker than card) + `success` (theme's "good" colour).
                _bg = self._c().get("secondary", "#313244")
                _fg = self._c().get("success", "#a6e3a1")
                install_btn.setStyleSheet(
                    f"background-color: {_bg}; color: {_fg}; "
                    f"font-weight: bold; border: 1px solid {self._c().get('border', _bg)}; "
                    f"border-radius: 6px; padding: 6px 12px;"
                )
                if uninstall_btn:
                    uninstall_btn.setVisible(True)
            elif installed_count > 0:
                badge.setText(f"⚡ {installed_count}/{len(packages)}")
                badge.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_small']}px; font-weight: bold;")
                remaining = len(packages) - installed_count
                install_btn.setText(f"{tr('install')} ({remaining} remaining)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(True)
            else:
                badge.setText("")
                install_btn.setText(f"{tr('install')} ({len(packages)} packages)")
                install_btn.setEnabled(True)
                install_btn.setObjectName("success")
                install_btn.setStyleSheet("")
                if uninstall_btn:
                    uninstall_btn.setVisible(False)

    def _create_manual_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        self.manual_info_label = QLabel(
            "Enter package names separated by spaces or newlines.\n"
            "You can specify versions like: numpy==1.24.0 or pandas>=2.0"
        )
        self.manual_info_label.setObjectName("subheader")
        self.manual_info_label.setWordWrap(True)
        layout.addWidget(self.manual_info_label)

        self.manual_input = QTextEdit()
        self.manual_input.setPlaceholderText(
            "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28"
        )
        layout.addWidget(self.manual_input)

        btn_layout = QHBoxLayout()

        copy_cmd_btn = QPushButton("📋 Copy Command")
        copy_cmd_btn.setObjectName("secondary")
        copy_cmd_btn.setToolTip("Copy the install command to clipboard")
        copy_cmd_btn.clicked.connect(self._copy_install_command)
        btn_layout.addWidget(copy_cmd_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.manual_input.clear)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        install_btn = QPushButton("⚡ Install Packages")
        install_btn.setObjectName("success")
        install_btn.clicked.connect(self._install_manual)
        btn_layout.addWidget(install_btn)

        layout.addLayout(btn_layout)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(200)
        self.output_log.setPlaceholderText("Installation output will appear here...")
        self.output_log.setStyleSheet(
            f"QTextEdit {{ background-color: {self._c()['card']}; color: {self._c()['fg']}; "
            f"font-family: 'Consolas', 'Courier New', monospace; font-size: {self._c()['fs_small']}px; "
            f"border: 1px solid {self._c()['border']}; border-radius: 4px; padding: 4px; }}"
        )
        layout.addWidget(self.output_log)

        # Copy log button
        copy_log_row = QHBoxLayout()
        self._copy_log_btn = QPushButton("📋 Copy Log")
        self._copy_log_btn.setObjectName("secondary")
        self._copy_log_btn.setFixedHeight(26)
        self._copy_log_btn.clicked.connect(self._copy_output_log)
        copy_log_row.addWidget(self._copy_log_btn)
        copy_log_row.addStretch()
        layout.addLayout(copy_log_row)

        return widget

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

    def set_venv(self, venv_path: Path):
        # B175 perf fix: skip the entire reload if the same env is selected again.
        try:
            _prev = getattr(self, "_current_venv_path", None)
            if _prev is not None and Path(_prev) == Path(venv_path):
                return
        except Exception:
            pass

        backend = "pip"
        try:
            from src.core.config_manager import ConfigManager
            backend = self._get_config("package_manager", "pip")
        except Exception:
            pass

        # Detect env type from marker FIRST — needed to choose backend
        self._current_env_type = "venv"  # default
        marker = venv_path / ".venvstudio_env"
        if marker.exists():
            try:
                import json as _json
                with open(marker) as f:
                    _m = _json.load(f)
                self._current_env_type = _m.get("type", "system_tools")
            except Exception:
                self._current_env_type = "system_tools"
        else:
            # No marker — check if this is a poetry venv (inside pypoetry cache)
            _vp_str = str(venv_path)
            if "pypoetry" in _vp_str and "virtualenvs" in _vp_str:
                self._current_env_type = "poetry"
            elif "pipx" in _vp_str:
                self._current_env_type = "pipx"

        # Override backend based on env type
        if self._current_env_type == "uv":
            backend = "uv"
        elif self._current_env_type == "poetry":
            backend = "poetry"
        elif self._current_env_type == "conda":
            backend = "conda"
        elif self._current_env_type == "pipx":
            backend = "pipx"

        # B182 follow-up: remember the active backend so post-install
        # callbacks can refresh the env info bar without guessing.
        self._current_backend = backend

        self.pip_manager = PipManager(venv_path, backend=backend)
        self._current_venv_path = venv_path
        # Inject shared cache dir if enabled (pip/uv only)
        if self.pip_manager and self._current_env_type in ("venv", "uv"):
            try:
                _cfg = getattr(self, "config", None)
                if _cfg and _cfg.get("shared_cache_enabled", False):
                    from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
                    _cp = _cfg.get("shared_cache_dir", "") or DEFAULT_SHARED_CACHE_DIR
                    self.pip_manager._shared_cache_dir = _cp
            except Exception:
                pass

        if hasattr(self, "_env_bar_terminal_btn"):
            self._env_bar_terminal_btn.setEnabled(True)
        # Select in dropdown
        name = venv_path.name
        idx = self.env_selector.findData(str(venv_path))
        if idx < 0:
            self.env_selector.addItem(name, str(venv_path))
            idx = self.env_selector.count() - 1
        self.env_selector.blockSignals(True)
        self.env_selector.setCurrentIndex(idx)
        self.env_selector.blockSignals(False)
        self.status_label.setText(f"Loading packages for {name}...")
        self._update_env_info_bar(venv_path, backend)
        self._update_tabs_for_env_type()

        # ── Fast path: if cache exists, populate instantly before async ──
        cached = self._load_pkg_cache()
        if cached is not None:
            self.installed_package_names = set()
            for p in cached:
                n = p["name"].lower()
                self.installed_package_names.add(n)
                self.installed_package_names.add(n.replace("-", "_"))
                self.installed_package_names.add(n.replace("_", "-"))
            self._update_launcher_status()   # show installed/not-installed instantly
            self.pkg_count_label.setText(f"{len(cached)} packages")
            self.env_pkg_count.setText(f"{len(cached)} packages installed")
            self.status_label.setText(f"Environment: {name}")

        # Async refresh (updates if cache stale, runs pip list in background)
        self._async_refresh_packages()

    def _update_tabs_for_env_type(self):
        """
        Show/hide tabs based on current env type using removeTab/insertTab.
        All env types get full tabs except system_tools (launcher + manual).
        """
        if not hasattr(self, "_tab_defs"):
            return
        # Ensure visible tabs are built
        current = self.tabs.currentIndex()
        if current >= 0:
            self._ensure_tab_built(current)

        env_type = getattr(self, "_current_env_type", "venv")

        # Update manual tab description and placeholder per env type
        if True:
            _manual_descriptions = {
                "venv":   "Enter package names separated by spaces or newlines.\nYou can specify versions like: numpy==1.24.0 or pandas>=2.0",
                "uv":    "Enter package names separated by spaces or newlines.\nUses uv pip install (10-100× faster than pip).",
                "poetry": "Enter package names to add.\nUses poetry add command.",
                "conda":  "Enter package names separated by spaces or newlines.\nPackages will be installed from conda-forge.",
                "pipx":   "Enter CLI app names to install globally.\nEach app gets its own isolated environment via pipx.",
            }
            _manual_placeholders = {
                "venv":   "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28",
                "uv":     "numpy pandas matplotlib\nscikit-learn==1.3.0",
                "poetry": "numpy pandas matplotlib",
                "conda":  "numpy pandas matplotlib\nscipy r-base",
                "pipx":   "httpie black ruff poetry cowsay",
            }
            self.manual_info_label.setText(_manual_descriptions.get(env_type, _manual_descriptions["venv"]))
            self.manual_input.setPlaceholderText(_manual_placeholders.get(env_type, _manual_placeholders["venv"]))

        # Which tab keys should be visible?
        visible_keys = {
            "venv":         {"launcher", "installed", "catalog", "presets", "manual"},
            "uv":           {"launcher", "installed", "catalog", "presets", "manual"},
            "poetry":       {"launcher", "installed", "catalog", "presets", "manual"},
            "conda":        {"launcher", "installed", "catalog", "presets", "manual"},
            "pipx":         {"launcher", "installed", "catalog", "presets", "manual"},
        }.get(env_type, {"launcher", "installed", "catalog", "presets", "manual"})

        # Remember current tab key before we remove tabs
        cur_widget = self.tabs.currentWidget()
        cur_key = None
        for key, label, widget, tooltip in self._tab_defs:
            if widget is cur_widget:
                cur_key = key
                break

        # Block signals to prevent feedback loops
        self.tabs.blockSignals(True)

        # Remove all tabs (widgets are kept alive, just removed from tab bar)
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)

        # Re-add only visible tabs in original order with env-type-aware tooltips
        _manual_tooltips = {
            "venv":   "📝 Manually install packages by name.\nYou can paste from pip install commands.",
            "uv":     "📝 Manually install packages by name.\nUses uv pip install (10-100× faster).",
            "poetry": "📝 Manually add packages.\nUses poetry add command.",
            "conda":  "📝 Manually install packages by name.\nUses conda install command.",
            "pipx":   "📝 Install CLI apps by name.\nUses pipx install command.",
        }
        _installed_tooltips = {
            "venv":   "📦 View and manage installed pip packages.",
            "uv":     "📦 View and manage installed packages (uv backend).",
            "poetry": "📦 View installed packages (Poetry environment).",
            "conda":  "📦 View installed conda packages.",
        }
        _catalog_tooltips = {
            "conda":  "🛒 Browse popular packages.\nInstalls via conda-forge channel.",
        }
        for key, label, widget, tooltip in self._tab_defs:
            if key in visible_keys:
                # Override tooltip for env-type awareness
                if key == "manual":
                    tooltip = _manual_tooltips.get(env_type, tooltip)
                elif key == "installed":
                    tooltip = _installed_tooltips.get(env_type, tooltip)
                elif key == "catalog":
                    tooltip = _catalog_tooltips.get(env_type, tooltip)
                # Build widget lazily if not yet created
                if widget is None:
                    tab_index = next((i for i, d in enumerate(self._tab_defs) if d[0] == key), -1)
                    if tab_index >= 0:
                        self._ensure_tab_built(tab_index)
                        widget = self._tab_defs[tab_index][2]
                if widget is not None:
                    idx = self.tabs.addTab(widget, label)
                    self.tabs.setTabToolTip(idx, tooltip)

        self.tabs.blockSignals(False)

        # Restore current tab if still visible, else go to Launch
        restored = False
        if cur_key and cur_key in visible_keys:
            for i, (key, label, widget, tooltip) in enumerate(self._tab_defs):
                if key == cur_key and key in visible_keys:
                    # Find its actual index in the new tab order
                    for j in range(self.tabs.count()):
                        if self.tabs.widget(j) is widget:
                            self.tabs.setCurrentIndex(j)
                            restored = True
                            break
                    break
        if not restored:
            self.tabs.setCurrentIndex(0)

        # Installed tab toolbar: disable pip-only actions for non-pip envs
        is_pip_like = env_type in ("venv", "uv", "poetry")
        if hasattr(self, "update_btn"):
            self.update_btn.setEnabled(is_pip_like)
            self.update_btn.setToolTip(
                "" if is_pip_like else f"Not available for {env_type} environments"
            )
        if hasattr(self, "uninstall_btn"):
            self.uninstall_btn.setEnabled(is_pip_like)
            self.uninstall_btn.setToolTip(
                "" if is_pip_like else f"Not available for {env_type} environments"
            )

        # Rebuild launcher grid — remove gaps from hidden cards
        if hasattr(self, "launcher_cards") and hasattr(self, "launcher_grid"):
            # Collect visible apps for this env type
            # pip-based env types share the same launcher apps as venv
            _filter_type = "venv" if env_type in ("uv", "poetry", "pipx") else env_type
            visible_apps = [
                app for app in self.app_definitions
                if _filter_type in app.get("env_types",
                    ["venv"] if not app.get("system_app")
                    else ["conda", "system_tools"])
            ]

            # Hide all cards first
            for card in self.launcher_cards.values():
                card.setVisible(False)
                self.launcher_grid.removeWidget(card)

            # Re-add only visible cards in order (no gaps)
            col_count = 3
            for idx, app in enumerate(visible_apps):
                card = self.launcher_cards.get(app["name"])
                if card:
                    row, col = divmod(idx, col_count)
                    self.launcher_grid.addWidget(card, row, col)
                    card.setVisible(True)

        # Update preset copy button tooltips for current env type
        _cmd_prefixes = {
            "venv":   "pip install",
            "uv":     "uv pip install",
            "poetry": "poetry add",
            "conda":  "conda install",
            "pipx":   "pipx install",
        }
        _prefix = _cmd_prefixes.get(env_type, "pip install")
        if hasattr(self, "_preset_cards"):
            for pname, pdata in self._preset_cards.items():
                copy_btn = pdata.get("copy_btn")
                if copy_btn and hasattr(copy_btn, "_preset_packages"):
                    _pkgs = copy_btn._preset_packages
                    _cmd = f"{_prefix} {' '.join(_pkgs)}"
                    copy_btn.setToolTip(
                        f"<p style='font-size:14px; font-weight:bold; color:#a6e3a1;'>"
                        f"💡 Equivalent terminal command:</p>"
                        f"<p style='font-size:16px; font-family:Consolas,monospace; color:#cdd6f4; "
                        f"background-color:#1e1e2e; padding:8px; border-radius:4px;'>"
                        f"{_cmd}</p>"
                        f"<p style='font-size:11px; color:#6c7086;'>Click to copy to clipboard</p>"
                    )

    def populate_env_list(self, env_list):
        """Populate the environment dropdown from main window."""
        self.env_selector.blockSignals(True)
        current_data = self.env_selector.currentData()
        self.env_selector.clear()
        self.env_selector.addItem(tr("select_environment"), "")
        for name, path in env_list:
            self.env_selector.addItem(name, str(path))

        # Restore previous selection or auto-select first env
        restored = False
        if current_data:
            idx = self.env_selector.findData(current_data)
            if idx >= 0:
                self.env_selector.setCurrentIndex(idx)
                restored = True
            else:
                # Previously selected env was deleted — clear state safely
                self._safe_clear_env_state()

        if not restored and self.env_selector.count() > 1:
            self.env_selector.setCurrentIndex(1)
        elif not restored:
            self.env_selector.setCurrentIndex(0)

        self.env_selector.blockSignals(False)

        # Always trigger load for selected env
        current_idx = self.env_selector.currentIndex()
        if current_idx > 0:
            self._on_env_selector_changed(current_idx)
        else:
            self._safe_clear_env_state()

    def _safe_clear_env_state(self):
        """Safely clear all env-related state when no env is selected or env was deleted."""
        # Stop any running loader thread first
        if hasattr(self, '_pkg_loader') and self._pkg_loader is not None:
            if self._pkg_loader.isRunning():
                try:
                    self._pkg_loader.done.disconnect()
                except Exception:
                    pass
                self._pkg_loader.quit()
                if not self._pkg_loader.wait(2000):
                    self._pkg_loader.terminate()
                    self._pkg_loader.wait(500)
            self._pkg_loader = None

        self.pip_manager = None
        self.installed_package_names = set()
        self._launcher_py_version_cache.clear()
        if hasattr(self, "packages_table"):
            self.packages_table.setRowCount(0)
        if hasattr(self, "pkg_count_label"):
            self.pkg_count_label.setText("0 packages")
        if hasattr(self, "env_pkg_count"):
            self.env_pkg_count.setText("")
        if hasattr(self, "python_version_label"):
            self.python_version_label.setText("")
        if hasattr(self, "_env_bar_terminal_btn"):
            self._env_bar_terminal_btn.setEnabled(False)
        self.status_label.setText("Select an environment to manage packages")
        self._hide_env_info_bar()

    def _on_env_selector_changed(self, index):
        """Handle env dropdown change."""
        path_str = self.env_selector.currentData()
        if path_str:
            backend = "pip"
            try:
                from src.core.config_manager import ConfigManager
                backend = self._get_config("package_manager", "pip")
            except Exception:
                pass
            venv_path = Path(path_str)
            self._current_venv_path = venv_path

            # Detect env type from marker — same as set_venv
            self._current_env_type = "venv"
            marker = venv_path / ".venvstudio_env"
            if marker.exists():
                try:
                    import json as _json
                    with open(marker) as f:
                        _m = _json.load(f)
                    self._current_env_type = _m.get("type", "system_tools")
                except Exception:
                    self._current_env_type = "system_tools"
            else:
                _vp_str = str(venv_path)
                if "pypoetry" in _vp_str and "virtualenvs" in _vp_str:
                    self._current_env_type = "poetry"
                elif "pipx" in _vp_str:
                    self._current_env_type = "pipx"

            # Override backend based on env type
            if self._current_env_type == "uv":
                backend = "uv"
            elif self._current_env_type == "poetry":
                backend = "poetry"
            elif self._current_env_type == "conda":
                backend = "conda"
            elif self._current_env_type == "pipx":
                backend = "pipx"

            self.pip_manager = PipManager(venv_path, backend=backend)
            # B182 follow-up: remember the active backend so post-install
            # callbacks can refresh the env info bar without guessing.
            self._current_backend = backend

            # Inject shared cache dir if enabled (pip/uv only)
            if self.pip_manager and self._current_env_type in ("venv", "uv"):
                try:
                    _cfg = getattr(self, "config", None)
                    if _cfg and _cfg.get("shared_cache_enabled", False):
                        from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
                        _cp = _cfg.get("shared_cache_dir", "") or DEFAULT_SHARED_CACHE_DIR
                        self.pip_manager._shared_cache_dir = _cp
                except Exception:
                    pass

            # B182 fix: previously the rest of this method (info bar update,
            # tabs refresh, async pkg load, QL callback) was nested inside
            # the "venv/uv only" if-block above, so poetry/pipx/conda envs
            # silently skipped it — leaving the info bar (path, size,
            # backend, last_used) blank in the UI when those envs were
            # selected from the dropdown. Move it back out to the common
            # path.
            if hasattr(self, "_env_bar_terminal_btn"):
                self._env_bar_terminal_btn.setEnabled(True)
            self.status_label.setText("Loading packages...")
            self._update_env_info_bar(venv_path, backend)
            self._update_tabs_for_env_type()
            # Notify main window to sync QL selector immediately
            if hasattr(self, "_ql_env_changed_callback") and callable(self._ql_env_changed_callback):
                self._ql_env_changed_callback(venv_path.name)
            self._async_refresh_packages()
        else:
            self._safe_clear_env_state()

    def _update_env_info_bar(self, venv_path, backend="pip"):
        """Update all info labels for the selected environment — uses cache."""
        # Show info labels
        for lbl in self._info_labels:
            lbl.setVisible(True)

        # Try cache first for python version and size
        python_ver = ""
        size_str = ""
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            cached = vm._read_cache(venv_path)
            if cached:
                python_ver = cached.get("python_version", "")
                size_str = cached.get("size", "")
        except Exception:
            pass

        # 1) Python version — from cache, marker, or subprocess
        if python_ver:
            self.python_version_label.setText(f"🐍 Python {python_ver}")
        else:
            # Try marker first (for pipx, conda, system_tools envs)
            _marker_pyver = ""
            _marker_file = venv_path / ".venvstudio_env"
            if _marker_file.exists():
                try:
                    import json as _json
                    with open(_marker_file) as _mf:
                        _mdata = _json.load(_mf)
                    _marker_pyver = _mdata.get("python_version", "")
                except Exception:
                    pass
            if _marker_pyver:
                self.python_version_label.setText(f"🐍 Python {_marker_pyver}")
            else:
                try:
                    python_exe = get_python_executable(venv_path)
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        capture_output=True, text=True, timeout=10,
                        **subprocess_args()
                    )
                    ver_text = result.stdout.strip() or result.stderr.strip()
                    self.python_version_label.setText(f"🐍 {ver_text}")
                except Exception:
                    # Last fallback: system Python
                    try:
                        import sys as _sys
                        result = subprocess.run(
                            [_sys.executable, "--version"],
                            capture_output=True, text=True, timeout=5,
                            **subprocess_args()
                        )
                        ver_text = result.stdout.strip() or result.stderr.strip()
                        self.python_version_label.setText(f"🐍 {ver_text}")
                    except Exception:
                        self.python_version_label.setText("")

        # 2) Shortened path
        try:
            full_path = str(venv_path)
            home = str(Path.home())
            if full_path.startswith(home):
                display_path = "~" + full_path[len(home):]
            else:
                display_path = full_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.env_path_label.setText(f"📂 {display_path}")
            self.env_path_label.setToolTip(full_path)
        except Exception:
            self.env_path_label.setText("")

        # 3) Disk size — from cache or calculate
        if size_str:
            self.env_disk_label.setText(f"💾 {size_str}")
        else:
            # B175 perf fix: never run os.walk on the UI thread.
            self.env_disk_label.setText("💾 …")
            self._start_size_calc_async(venv_path)

        # 4) Backend (pip/uv/conda/poetry/pipx)
        _env_type = getattr(self, "_current_env_type", "venv")
        _backend_names = {
            "venv": backend.upper() if backend else "PIP",
            "uv": "UV",
            "poetry": "Poetry",
            "pipx": "pipx",
            "conda": "Conda",
        }
        backend_display = _backend_names.get(_env_type, backend.upper() if backend else "PIP")
        self.env_backend_label.setText(f"⚙️ {backend_display}")

        # 5) Last used (modification time of pyvenv.cfg or activate script)
        try:
            candidates = [
                venv_path / "pyvenv.cfg",
                venv_path / "Scripts" / "activate.bat",
                venv_path / "bin" / "activate",
                venv_path / "conda-meta" / "history",
            ]
            latest_mtime = 0
            for c in candidates:
                if c.exists():
                    mt = c.stat().st_mtime
                    if mt > latest_mtime:
                        latest_mtime = mt
            if latest_mtime > 0:
                from datetime import datetime
                dt = datetime.fromtimestamp(latest_mtime)
                self.env_last_used_label.setText(f"🕐 {dt.strftime('%Y-%m-%d %H:%M')}")
            else:
                # Fallback: use marker created date (e.g. pipx has no activate/pyvenv.cfg)
                _marker = venv_path / ".venvstudio_env"
                _created = ""
                if _marker.exists():
                    try:
                        import json as _j
                        _created = _j.loads(_marker.read_text()).get("created", "")
                    except Exception:
                        pass
                if not _created:
                    # For poetry venvs, use dir ctime
                    try:
                        from datetime import datetime
                        _created = datetime.fromtimestamp(venv_path.stat().st_ctime).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                if _created:
                    try:
                        from datetime import datetime
                        if "T" in _created:
                            dt = datetime.fromisoformat(_created)
                            _created = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                    self.env_last_used_label.setText(f"🕐 {_created}")
                else:
                    self.env_last_used_label.setText("")
                    self._info_sep3.setVisible(False)
        except Exception:
            self.env_last_used_label.setText("")
            self._info_sep3.setVisible(False)

    def _hide_env_info_bar(self):
        """Hide all info bar labels when no env is selected."""
        for lbl in self._info_labels:
            lbl.setVisible(False)

    # B175: background env-size calculation
    def _start_size_calc_async(self, venv_path):
        try:
            prev = getattr(self, "_size_worker", None)
            if prev is not None and prev.isRunning():
                try:
                    prev.done.disconnect()
                except Exception:
                    pass
                prev.requestInterruption()
                prev.quit()
                prev.wait(500)
            self._size_worker = _EnvSizeWorker(str(venv_path), parent=self)
            _expected = str(venv_path)

            def _on_size_done(path_str: str, size_str: str):
                cur = getattr(self, "_current_venv_path", None)
                if cur is not None and str(cur) != _expected:
                    return
                if size_str:
                    self.env_disk_label.setText(f"💾 {size_str}")
                    try:
                        from pathlib import Path as _P
                        vm = self._get_venv_manager()
                        all_cache = vm._load_all_cache()
                        key = vm._cache_key(_P(path_str))
                        entry = all_cache.get(key, {}) or {}
                        entry["size"] = size_str
                        all_cache[key] = entry
                        vm._save_all_cache(all_cache)
                    except Exception:
                        pass
                else:
                    self.env_disk_label.setText("💾 ?")

            self._size_worker.done.connect(_on_size_done)
            self._size_worker.start()
        except Exception:
            try:
                self.env_disk_label.setText("💾 ?")
            except Exception:
                pass

    def _async_refresh_packages(self, force: bool = False):
        """Load packages — from cache if available, otherwise background subprocess."""
        if not self.pip_manager:
            return

        # Try cache first (unless force=True)
        if not force:
            cached = self._load_pkg_cache()
            if cached is not None:
                try:
                    from src.utils.logger import get_logger
                    get_logger("venvstudio.pkg_cache").debug(
                        f"[PkgCache] HIT key={self._get_pkg_cache_key()!r} count={len(cached)}"
                    )
                except Exception:
                    pass
                class _Pkg:
                    def __init__(self, name, version):
                        self.name = name
                        self.version = version
                pkgs = [_Pkg(p["name"], p["version"]) for p in cached]
                self._on_packages_loaded(pkgs)
                return
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.pkg_cache").debug(
                    f"[PkgCache] MISS key={self._get_pkg_cache_key()!r} force={force} → starting pip list"
                )
            except Exception:
                pass

        # Cancel / wait for any previous loader to avoid QThread crash
        if hasattr(self, '_pkg_loader') and self._pkg_loader is not None:
            if self._pkg_loader.isRunning():
                try:
                    self._pkg_loader.done.disconnect()
                except Exception:
                    pass
                self._pkg_loader.quit()
                if not self._pkg_loader.wait(3000):
                    self._pkg_loader.terminate()
                    self._pkg_loader.wait(1000)
            self._pkg_loader = None

        # Show loading state immediately
        self.packages_table.setRowCount(1)
        loading_item = QTableWidgetItem("Loading...")
        loading_item.setFlags(loading_item.flags() & ~Qt.ItemIsEditable)
        self.packages_table.setItem(0, 0, loading_item)
        self.packages_table.setItem(0, 1, QTableWidgetItem(""))
        self.pkg_count_label.setText("Loading...")
        self.env_pkg_count.setText("Loading packages...")

        # Capture pip_manager reference (env may change before thread finishes)
        pip_mgr_snapshot = self.pip_manager
        _env_type = getattr(self, "_current_env_type", "venv")
        _venv_path = self._current_venv_path if hasattr(self, "_current_venv_path") else None

        # Use QThread for background loading
        class PkgLoader(QThread):
            done = Signal(list)
            def __init__(self, pip_mgr, env_type, venv_path, parent=None):
                super().__init__(parent)
                self.pip_mgr = pip_mgr
                self.env_type = env_type
                self.venv_path = venv_path
            def run(self):
                try:
                    if self.env_type == "conda" and self.venv_path:
                        from src.core.micromamba_installer import list_conda_packages
                        raw = list_conda_packages(self.venv_path)
                        class _Pkg:
                            def __init__(self, name, version):
                                self.name = name
                                self.version = version
                        pkgs = [_Pkg(p.get("name",""), p.get("version",""))
                                for p in raw]
                    elif self.env_type == "pipx":
                        # List globally installed pipx apps
                        import subprocess, sys, json as _json
                        from src.utils.platform_utils import subprocess_args
                        class _Pkg:
                            def __init__(self, name, version):
                                self.name = name
                                self.version = version
                        pkgs = []
                        try:
                            from src.utils.platform_utils import get_pipx_executable as _get_pipx
                            _pipx_exe = _get_pipx()
                            _pipx_cmd = [_pipx_exe, "list", "--json"] if _pipx_exe else [sys.executable, "-m", "pipx", "list", "--json"]
                            r = subprocess.run(
                                _pipx_cmd,
                                capture_output=True, text=True, timeout=30,
                                **subprocess_args()
                            )
                            if r.returncode == 0 and r.stdout.strip():
                                data = _json.loads(r.stdout)
                                venvs = data.get("venvs", {})
                                for pkg_name, info in venvs.items():
                                    meta = info.get("metadata", {})
                                    ver = meta.get("main_package", {}).get("package_version", "")
                                    pkgs.append(_Pkg(pkg_name, ver))
                        except Exception:
                            pass
                    else:
                        pkgs = self.pip_mgr.list_packages()
                    self.done.emit(pkgs)
                except Exception:
                    self.done.emit([])

        self._pkg_loader = PkgLoader(pip_mgr_snapshot, _env_type, _venv_path, parent=self)
        self._pkg_loader.done.connect(self._on_packages_loaded)
        self._pkg_loader.start()


    def _get_catalog_lookup(self) -> dict:
        """Build {pkg_name_lower: (desc, category)} from PACKAGE_CATALOG.
        Uses EXACTLY the same iteration as _populate_catalog.
        """
        lookup = {}
        for cat_name, cat_data in PACKAGE_CATALOG.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                name = pkg["name"]
                desc = pkg["desc"]
                lookup[name.lower()] = (desc, cat_name)
                lookup[name.lower().replace("-", "_")] = (desc, cat_name)
                lookup[name.lower().replace("_", "-")] = (desc, cat_name)
        return lookup

    def _on_packages_loaded(self, packages):
        """Called when async package loading finishes."""
        try:
            from src.utils.logger import get_logger
            get_logger("venvstudio.pkg_cache").debug(
                f"[PkgCache] _on_packages_loaded called count={len(packages) if packages else 0}"
            )
        except Exception:
            pass
        if not self.pip_manager:
            return

        # Save to cache
        self._save_pkg_cache(packages)

        # Store both dash and underscore variants for robust matching (e.g. quarto-cli ↔ quarto_cli)
        self.installed_package_names = set()
        for pkg in packages:
            n = pkg.name.lower()
            self.installed_package_names.add(n)
            self.installed_package_names.add(n.replace("-", "_"))
            self.installed_package_names.add(n.replace("_", "-"))

        self.packages_table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        count = len(packages)
        self.pkg_count_label.setText(f"{count} packages")
        self.env_pkg_count.setText(f"{count} packages installed")
        env_name = self.env_selector.currentText()
        self.status_label.setText(f"Environment: {env_name}")

        self._populate_catalog()
        self._update_launcher_status()
        self._update_preset_badges()
        # Notify main window to update quick launch buttons
        if hasattr(self, "_ql_update_callback") and callable(self._ql_update_callback):
            _current_env = self.pip_manager.venv_path.name if self.pip_manager else ""
            self._ql_update_callback(env_name=_current_env)

        # B182 race fix: if an install/uninstall just finished and asked us
        # to notify MainWindow when the new pkg count is known, emit now.
        # The cache was just written above by _save_pkg_cache(packages), so
        # MainWindow's _refresh_current_env_row will see the fresh value
        # instead of racing with the async load.
        if getattr(self, "_emit_env_refresh_after_load", False):
            self._emit_env_refresh_after_load = False
            try:
                self.env_refresh_requested.emit(len(packages))
            except Exception:
                pass

    def refresh_packages(self):
        """Refresh installed packages list - invalidates cache and async reloads."""
        self._invalidate_pkg_cache()
        self._async_refresh_packages(force=True)
        return

    def _refresh_packages_sync_legacy(self):
        """Legacy sync refresh - kept for internal use only."""
        if not self.pip_manager:
            return

        packages = self.pip_manager.list_packages()
        # Store both dash and underscore variants for robust matching (e.g. quarto-cli ↔ quarto_cli)
        self.installed_package_names = set()
        for pkg in packages:
            n = pkg.name.lower()
            self.installed_package_names.add(n)
            self.installed_package_names.add(n.replace("-", "_"))
            self.installed_package_names.add(n.replace("_", "-"))

        self.packages_table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        count = len(packages)
        self.pkg_count_label.setText(f"{count} packages")
        self.env_pkg_count.setText(f"{count} packages installed")

        # Update catalog checkboxes
        self._populate_catalog()
        # Update launcher app status
        self._update_launcher_status()
        # Update preset badges
        self._update_preset_badges()

    # ── Catalog ──

    def _populate_catalog(self):
        selected = self.category_combo.currentData()
        self.catalog_table.setRowCount(0)
        self._catalog_initial_state = {}

        categories = PACKAGE_CATALOG if selected == "all" else {selected: PACKAGE_CATALOG.get(selected, {})}

        # Include custom catalog packages from config
        from src.core.config_manager import ConfigManager
        try:
            config = self.config if self.config else __import__("src.core.config_manager", fromlist=["ConfigManager"]).ConfigManager()
            custom_pkgs = config.get("custom_catalog", [])
        except Exception:
            custom_pkgs = []

        if custom_pkgs:
            # Group custom packages by category
            custom_groups = {}
            for p in custom_pkgs:
                cat = p.get("category", "⭐ Custom")
                if cat not in custom_groups:
                    custom_groups[cat] = {"icon": "⭐", "packages": []}
                custom_groups[cat]["packages"].append({"name": p["name"], "desc": p.get("desc", "")})

            for cat_name, cat_data in custom_groups.items():
                if selected == "all" or selected == cat_name:
                    if cat_name not in categories:
                        categories[cat_name] = cat_data
                    else:
                        # Merge into existing category
                        categories[cat_name]["packages"].extend(cat_data["packages"])

        row = 0
        for cat_name, cat_data in categories.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                self.catalog_table.insertRow(row)

                is_installed = pkg["name"].lower() in self.installed_package_names

                cb = QCheckBox()
                cb.setChecked(is_installed)
                cb.stateChanged.connect(self._on_catalog_checkbox_changed)
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.catalog_table.setCellWidget(row, 0, cb_widget)

                name_item = QTableWidgetItem(pkg["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_font = QFont()
                name_font.setBold(True)
                name_item.setFont(name_font)
                if is_installed:
                    name_item.setForeground(QColor("#a6e3a1"))
                self.catalog_table.setItem(row, 1, name_item)

                desc_item = QTableWidgetItem(pkg["desc"])
                desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 2, desc_item)

                cat_item = QTableWidgetItem(cat_name)
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 3, cat_item)

                self._catalog_initial_state[row] = is_installed

                # Links column: PyPI + optional Docs
                links_widget = QWidget()
                links_layout = QHBoxLayout(links_widget)
                links_layout.setContentsMargins(2, 1, 2, 1)
                links_layout.setSpacing(3)
                pkg_name_for_link = pkg["name"]
                docs_url = _PACKAGE_DOCS.get(pkg_name_for_link.lower())

                pypi_btn = QPushButton("PyPI")
                pypi_btn.setFixedSize(34, 20)
                pypi_btn.setStyleSheet(
                    f"QPushButton {{ font-size: {self._c()['fs_tiny']}px; padding: 0; background: {self._c()['secondary']}; "
                    "color: #89b4fa; border: 1px solid #45475a; border-radius: 3px; }"
                    "QPushButton:hover { background: #45475a; }"
                )
                pypi_btn.clicked.connect(lambda _, n=pkg_name_for_link: self._open_pypi(n))
                links_layout.addWidget(pypi_btn)

                if docs_url:
                    docs_btn = QPushButton("Docs")
                    docs_btn.setFixedSize(34, 20)
                    docs_btn.setStyleSheet(
                        f"QPushButton {{ font-size: {self._c()['fs_tiny']}px; padding: 0; background: {self._c()['secondary']}; "
                        "color: #a6e3a1; border: 1px solid #45475a; border-radius: 3px; }"
                        "QPushButton:hover { background: #45475a; }"
                    )
                    docs_btn.clicked.connect(lambda _, u=docs_url: __import__("webbrowser").open(u))
                    links_layout.addWidget(docs_btn)

                links_layout.addStretch()
                self.catalog_table.setCellWidget(row, 4, links_widget)

                row += 1

        self._update_apply_button()

    def _on_catalog_checkbox_changed(self):
        self._update_apply_button()

    def _update_apply_button(self):
        """Enable Apply button only if there are actual changes."""
        to_install, to_uninstall = self._get_catalog_changes()
        has_changes = bool(to_install or to_uninstall)
        self.apply_btn.setEnabled(has_changes)

        if has_changes:
            parts = []
            if to_install:
                parts.append(f"+{len(to_install)} install")
            if to_uninstall:
                parts.append(f"-{len(to_uninstall)} remove")
            self.changes_label.setText(" | ".join(parts))
        else:
            self.changes_label.setText("")

    def _get_catalog_changes(self):
        to_install = []
        to_uninstall = []

        for row in range(self.catalog_table.rowCount()):
            cb_widget = self.catalog_table.cellWidget(row, 0)
            if not cb_widget:
                continue
            cb = cb_widget.findChild(QCheckBox)
            if not cb:
                continue
            name_item = self.catalog_table.item(row, 1)
            if not name_item:
                continue

            pkg_name = name_item.text()
            is_checked = cb.isChecked()
            was_installed = self._catalog_initial_state.get(row, False)

            if is_checked and not was_installed:
                to_install.append(pkg_name)
            elif not is_checked and was_installed:
                to_uninstall.append(pkg_name)

        return to_install, to_uninstall

    def _apply_catalog_changes(self):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return

        to_install, to_uninstall = self._get_catalog_changes()

        if not to_install and not to_uninstall:
            QMessageBox.information(self, "No Changes", "No changes detected.")
            return

        # Build detailed confirm message
        msg_parts = []
        if to_uninstall:
            msg_parts.append(f"🗑️ Remove ({len(to_uninstall)}):\n  • " + "\n  • ".join(to_uninstall))
        if to_install:
            msg_parts.append(f"📦 Install ({len(to_install)}):\n  • " + "\n  • ".join(to_install))

        reply = QMessageBox.question(
            self, "Apply Changes",
            "Apply the following changes?\n\n" + "\n\n".join(msg_parts),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint (env-type aware)
        _env_type = getattr(self, "_current_env_type", "venv")
        _install_cmds = {
            "venv": "pip install {packages}", "uv": "uv pip install {packages}",
            "poetry": "poetry add {packages}",
            "conda": "conda install {packages}", "pipx": "pipx install {packages}",
        }
        _uninstall_cmds = {
            "venv": "pip uninstall -y {packages}", "uv": "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda": "conda remove {packages}", "pipx": "pipx uninstall {packages}",
        }
        cmds = []
        if to_uninstall:
            cmds.append(_uninstall_cmds.get(_env_type, COMMAND_HINTS["uninstall"]).format(packages=" ".join(to_uninstall)))
        if to_install:
            cmds.append(_install_cmds.get(_env_type, COMMAND_HINTS["install"]).format(packages=" ".join(to_install)))
        self._show_command_hint("Apply Changes", " && ".join(cmds))

        self._set_busy(True)
        self.output_log.clear()

        if to_uninstall:
            self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, to_uninstall)
            self.current_worker.progress.connect(self._on_progress)
            if to_install:
                self.current_worker.finished.connect(
                    lambda ok, msg: self._chain_install(ok, msg, to_install)
                )
            else:
                self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
        elif to_install:
            self._do_install(to_install)

    def _chain_install(self, uninstall_ok, uninstall_msg, to_install):
        if not uninstall_ok:
            self._append_log(f"❌ Uninstall failed: {uninstall_msg[:300]}")
        self._append_log("✅ Uninstall done. Starting install...")
        self._do_install(to_install)

    # ── Install / Uninstall ──

    def _install_packages(self, packages: list, hint_name: str = ""):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.\nPlease select an environment first.")
            return

        # Kurulu paketleri filtrele — sadece kurulu olmayanları kur
        try:
            installed = {p.name.lower() for p in self.pip_manager.list_packages()}
            import re
            not_installed = []
            already_installed = []
            for pkg in packages:
                pkg_name = re.split(r'[><=!~;]', pkg)[0].lower().replace("-", "_")
                pkg_name2 = pkg_name.replace("_", "-")
                if pkg_name in installed or pkg_name2 in installed:
                    already_installed.append(pkg)
                else:
                    not_installed.append(pkg)
            if not not_installed:
                QMessageBox.information(self, "Info", "All packages are already installed.")
                return
            packages = not_installed
        except Exception:
            pass  # Filtreleme başarısız olursa tüm paketlerle devam et

        # Check Python version — warn if old (some packages may not have pre-built wheels)
        py_warning = ""
        if self.pip_manager:
            try:
                venv_key = str(self.pip_manager.venv_path)
                env_py_version = self._launcher_py_version_cache.get(venv_key)
                if not env_py_version:
                    python_exe = get_python_executable(self.pip_manager.venv_path)
                    from src.utils.platform_utils import subprocess_args
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        **subprocess_args(capture_output=True, text=True, timeout=5)
                    )
                    ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                    env_py_version = tuple(int(x) for x in ver_str.split(".")[:2])
                    self._launcher_py_version_cache[venv_key] = env_py_version
                if env_py_version and env_py_version < (3, 10):
                    py_warning = (
                        f"\n\n⚠️ Warning: This environment uses Python {env_py_version[0]}.{env_py_version[1]}.\n"
                        f"Some packages (e.g. spacy, torch) may fail to install because\n"
                        f"pre-built wheels are not available for older Python versions.\n"
                        f"Consider creating a new environment with Python 3.11+."
                    )
            except Exception:
                pass

        # Show ALL package names in confirm dialog
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following {len(packages)} package(s)?\n\n• " + "\n• ".join(packages) + py_warning,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint based on env type
        _env_type = getattr(self, "_current_env_type", "venv")
        _install_cmds = {
            "venv":   "pip install {packages}",
            "uv":     "uv pip install {packages}",
            "poetry": "poetry add {packages}",
            "conda":  "conda install {packages}",
            "pipx":   "pipx install {packages}",
        }
        _cmd_template = _install_cmds.get(_env_type, COMMAND_HINTS["install"])
        cmd = _cmd_template.format(packages=" ".join(packages))
        self._show_command_hint(hint_name or "Install Packages", cmd)

        self._do_install(packages)

    def _do_install(self, packages):
        """Actually start install worker (no confirm dialog)."""
        self._set_busy(True)
        self.output_log.clear()

        _env_type = getattr(self, "_current_env_type", "venv")
        if _env_type == "conda" and self.pip_manager and self.pip_manager.venv_path:
            # Use conda install instead of pip for conda environments
            _env_path = self.pip_manager.venv_path
            _pkgs = list(packages)

            def _do_conda_install(callback=None):
                from src.core.micromamba_installer import (
                    install_conda_packages, get_micromamba_exe, download_micromamba,
                )
                if not get_micromamba_exe():
                    if callback:
                        callback("Downloading micromamba...")
                    download_micromamba(progress_cb=callback)
                ok = install_conda_packages(
                    _env_path, _pkgs,
                    channels=["conda-forge"],
                    progress_cb=callback,
                )
                return (ok,
                        f"Installed: {', '.join(_pkgs)}" if ok
                        else f"conda install failed for: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_conda_install)
        elif _env_type == "pipx":
            # Use pipx install for each package — with selected Python from marker
            _pkgs = list(packages)
            _pipx_python = None
            if self.pip_manager and self.pip_manager.venv_path:
                _marker = self.pip_manager.venv_path / ".venvstudio_env"
                if _marker.exists():
                    try:
                        import json as _json
                        with open(_marker) as _mf:
                            _mdata = _json.load(_mf)
                        _pipx_python = _mdata.get("python_path", "")
                    except Exception:
                        pass

            def _do_pipx_install(callback=None):
                import subprocess, sys, shutil
                from src.utils.platform_utils import subprocess_args
                # Find pipx executable — prefer direct binary over python -m pipx
                _pipx_bin = shutil.which("pipx")
                installed = []
                failed = []
                for pkg in _pkgs:
                    if callback:
                        callback(f"pipx install {pkg}...")
                    if _pipx_bin:
                        cmd = [_pipx_bin, "install", pkg]
                    else:
                        _pipx_exe2 = shutil.which("pipx")
                        cmd = [_pipx_exe2, "install", pkg] if _pipx_exe2 else [sys.executable, "-m", "pipx", "install", pkg]
                    if _pipx_python:
                        cmd += ["--python", _pipx_python]
                    r = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=300,
                        **subprocess_args()
                    )
                    if r.returncode == 0:
                        installed.append(pkg)
                    else:
                        failed.append(pkg)
                if failed:
                    return (False, f"pipx install failed for: {', '.join(failed)}")
                return (True, f"pipx installed: {', '.join(installed)}")

            self.current_worker = WorkerThread(_do_pipx_install)
        else:
            self.current_worker = WorkerThread(self.pip_manager.install_packages, packages)

        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _copy_install_command(self):
        """Copy the install command for entered packages (env-type aware)."""
        text = self.manual_input.toPlainText().strip()
        if not text:
            self.status_label.setText("⚠️ No packages entered")
            return

        # Clean the input (same logic as _install_manual)
        import re
        noise = {"pip", "pip3", "python", "python3", "-m", "install", "uninstall",
                 "--upgrade", "--user", "-U", "-r", "--force-reinstall", "--no-cache-dir",
                 "--break-system-packages", "sudo", "&&", "||", "|", ";"}
        cleaned = []
        seen = set()
        for line in text.splitlines():
            line = line.strip().replace(",", " ")
            if not line or line.startswith("#"):
                continue
            for token in line.split():
                t = token.strip()
                if not t or t.lower() in noise or t.startswith("-") or t.isdigit():
                    continue
                if not re.search(r'[a-zA-Z]', t):
                    continue
                key = t.lower()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(t)

        if cleaned:
            _env_type = getattr(self, "_current_env_type", "venv")
            _cmd_prefixes = {
                "venv":   "pip install",
                "uv":     "uv pip install",
                "poetry": "poetry add",
                "conda":  "conda install",
                "pipx":   "pipx install",
            }
            _prefix = _cmd_prefixes.get(_env_type, "pip install")
            cmd = f"{_prefix} {' '.join(cleaned)}"
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(cmd)
            self.status_label.setText(f"📋 Copied: {cmd}")
        else:
            self.status_label.setText("⚠️ No valid package names found")

    def _install_manual(self):
        text = self.manual_input.toPlainText().strip()
        if not text:
            return

        # Normalize non-ASCII characters → ASCII equivalents
        # Türkçe ve diğer dillerdeki harfler → İngilizce karşılıkları
        import unicodedata
        _char_map = str.maketrans({
            'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ş': 's', 'Ş': 'S', 'ç': 'c', 'Ç': 'C',
            'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
            'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'õ': 'o',
        })
        text = text.translate(_char_map)

        # Normalize version separators: == = => >=, kurulum => install
        # "numpy=1.0" veya "numpy =1.0" → "numpy==1.0"
        import re
        # Boşluklu versiyon: "numpy == 1.0" → "numpy==1.0"
        text = re.sub(r'\s*([><=!~]+)\s*', r'\1', text)
        # Tek = (atama değil paket versiyonu): "numpy=1.0" → "numpy==1.0"
        text = re.sub(r'(?<![=<>!~])=(?!=)', '==', text)

        # Noise words to filter out
        noise = {"pip", "pip3", "python", "python3", "-m", "install", "uninstall",
                 "--upgrade", "--user", "-u", "-r", "--force-reinstall", "--no-cache-dir",
                 "--break-system-packages", "sudo", "&&", "||", "|", ";",
                 "list", "freeze", "show", "search", "check", "download",
                 "wheel", "hash", "config", "cache", "debug", "index",
                 "requirements.txt", "setup.py", "pyproject.toml"}

        cleaned = []
        seen = set()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Replace commas, semicolons, pipes with spaces
            line = line.replace(",", " ").replace(";", " ").replace("|", " ")
            for token in line.split():
                t = token.strip()
                if not t:
                    continue
                # Küçük harfe çevir (paket adı kısmını)
                pkg_and_ver = re.split(r'([><=!~;])', t, maxsplit=1)
                pkg_name_raw = pkg_and_ver[0].lower()
                rest = "".join(pkg_and_ver[1:]) if len(pkg_and_ver) > 1 else ""
                t_normalized = pkg_name_raw + rest

                # Skip noise words
                if pkg_name_raw in noise:
                    continue
                # Skip pure numbers
                if t_normalized.isdigit():
                    continue
                # Skip flags
                if t_normalized.startswith("-"):
                    continue
                # Skip tokens with no letters
                if not re.search(r'[a-zA-Z]', t_normalized):
                    continue
                # Valid package name check
                pkg_name = re.split(r'[><=!~;]', t_normalized)[0]
                if not pkg_name or not re.match(r'^[a-z0-9]', pkg_name):
                    continue
                # Deduplicate
                key = pkg_name_raw
                if key not in seen:
                    seen.add(key)
                    cleaned.append(t_normalized)

        if not cleaned:
            QMessageBox.information(
                self, "Info",
                "No valid package names found.\n\n"
                "Just enter package names, e.g.:\n"
                "numpy pandas matplotlib"
            )
            return

        self._install_packages(cleaned)

    def _uninstall_selected(self):
        if not self.pip_manager:
            return

        packages = []
        for row in range(self.packages_table.rowCount()):
            cb_widget = self.packages_table.cellWidget(row, 2)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.packages_table.item(row, 0)
                    if item:
                        packages.append(item.text())

        if not packages:
            QMessageBox.information(self, "Info", "No packages selected for uninstall.")
            return

        reply = QMessageBox.warning(
            self, "Confirm Uninstall",
            f"Uninstall {len(packages)} package(s)?\n\n• " + "\n• ".join(packages),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        _env_type = getattr(self, "_current_env_type", "venv")
        _uninstall_cmds = {
            "venv":   "pip uninstall -y {packages}",
            "uv":     "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda":  "conda remove {packages}",
            "pipx":   "pipx uninstall {packages}",
        }
        cmd = _uninstall_cmds.get(_env_type, COMMAND_HINTS["uninstall"]).format(packages=" ".join(packages))
        self._show_command_hint("Uninstall Packages", cmd)

        self._set_busy(True)
        self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _export_requirements(self):
        if not self.pip_manager:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            success, msg = self.pip_manager.export_requirements(Path(filepath))
            self._show_command_hint("Export Requirements", {
                "venv": "pip freeze > requirements.txt",
                "uv": "uv pip freeze > requirements.txt",
                "poetry": "poetry export -f requirements.txt",
                "conda": "conda list --export > requirements.txt",
            }.get(getattr(self, "_current_env_type", "venv"), COMMAND_HINTS["freeze"]))
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)

    def _get_freeze_and_version(self):
        """Helper: get freeze content and python version for export."""
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return None, None
        freeze = self.pip_manager.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", "No packages to export.")
            return None, None
        # Get python version
        py_ver = "3.12"
        try:
            python_exe = get_python_executable(self.pip_manager.venv_path)
            result = subprocess.run(
                [str(python_exe), "--version"],
                capture_output=True, text=True, timeout=10,
                **subprocess_args()
            )
            ver_text = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            py_ver = ".".join(ver_text.split(".")[:2])  # "3.14"
        except Exception:
            pass
        return freeze, py_ver

    def _export_dockerfile(self):
        """Export as Dockerfile."""
        freeze, py_ver = self._get_freeze_and_version()
        if not freeze:
            return

        packages = [line.strip() for line in freeze.strip().splitlines() if line.strip() and not line.startswith("#")]

        dockerfile = f"""# Auto-generated by VenvStudio
FROM python:{py_ver}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run application
# CMD ["python", "main.py"]
"""

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Dockerfile", "Dockerfile", "All Files (*)"
        )
        if filepath:
            # Also save requirements.txt alongside
            req_path = Path(filepath).parent / "requirements.txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported:\n  📄 {filepath}\n  📄 {req_path}\n\n"
                    f"Build with:\n  docker build -t myapp ."
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_docker_compose(self):
        """Export as docker-compose.yml + Dockerfile."""
        freeze, py_ver = self._get_freeze_and_version()
        if not freeze:
            return

        compose = f"""# Auto-generated by VenvStudio
version: '3.8'

services:
  app:
    build: .
    container_name: myapp
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - PYTHONUNBUFFERED=1
    # command: python main.py
"""

        dockerfile = f"""# Auto-generated by VenvStudio
FROM python:{py_ver}-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD ["python", "main.py"]
"""

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export docker-compose.yml", "docker-compose.yml", "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            base_dir = Path(filepath).parent
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(compose)
                with open(base_dir / "Dockerfile", "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(base_dir / "requirements.txt", "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported:\n"
                    f"  📄 {filepath}\n"
                    f"  📄 {base_dir / 'Dockerfile'}\n"
                    f"  📄 {base_dir / 'requirements.txt'}\n\n"
                    f"Run with:\n  docker-compose up --build"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_pyproject(self):
        """Export as pyproject.toml."""
        freeze, py_ver = self._get_freeze_and_version()
        if not freeze:
            return

        packages = []
        for line in freeze.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                packages.append(f'    "{line}",')

        deps_str = "\n".join(packages)

        pyproject = f"""# Auto-generated by VenvStudio
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "myproject"
version = "0.1.0"
description = ""
requires-python = ">={py_ver}"
dependencies = [
{deps_str}
]

[project.optional-dependencies]
dev = [
    "pytest",
    "black",
    "ruff",
]
"""

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export pyproject.toml", "pyproject.toml", "TOML Files (*.toml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(pyproject)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_conda_yml(self):
        """Export as Conda environment.yml."""
        freeze, py_ver = self._get_freeze_and_version()
        if not freeze:
            return

        pip_packages = []
        for line in freeze.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pip_packages.append(f"    - {line}")

        pip_str = "\n".join(pip_packages)

        conda_yml = f"""# Auto-generated by VenvStudio
name: myenv
channels:
  - defaults
  - conda-forge
dependencies:
  - python={py_ver}
  - pip
  - pip:
{pip_str}
"""

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export environment.yml", "environment.yml", "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(conda_yml)
                QMessageBox.information(
                    self, "✅ Success",
                    f"Exported to:\n{filepath}\n\n"
                    f"Create with:\n  conda env create -f environment.yml"
                )
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_clipboard(self):
        """Copy freeze output to clipboard."""
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return
        freeze = self.pip_manager.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", "No packages to export.")
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(freeze)
        self.status_label.setText("📋 Package list copied to clipboard!")
        QMessageBox.information(
            self, "✅ Copied",
            f"Copied {len(freeze.strip().splitlines())} packages to clipboard."
        )

    def _import_requirements(self):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Requirements", "", "Text Files (*.txt);;All Files (*)"
        )
        if filepath:
            self._show_command_hint("Import Requirements", {
                "venv": "pip install -r requirements.txt",
                "uv": "uv pip install -r requirements.txt",
                "poetry": "poetry install",
                "conda": "conda install --file requirements.txt",
            }.get(getattr(self, "_current_env_type", "venv"), COMMAND_HINTS["import_req"]))
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.import_requirements, Path(filepath)
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _pkg_table_context_menu(self, position):
        """Right-click context menu for packages table."""
        rows = self.packages_table.selectionModel().selectedRows()
        if not rows:
            return

        menu = QMenu(self)
        _env_type = getattr(self, "_current_env_type", "venv")
        _prefixes = {
            "venv": "pip install", "uv": "uv pip install",
            "poetry": "poetry add",
            "conda": "conda install", "pipx": "pipx install",
        }
        _prefix = _prefixes.get(_env_type, "pip install")

        # Gather selected package names
        selected_pkgs = []
        for idx in rows:
            item = self.packages_table.item(idx.row(), 0)
            ver_item = self.packages_table.item(idx.row(), 1)
            if item:
                pkg = item.text().strip()
                ver = ver_item.text().strip() if ver_item else ""
                selected_pkgs.append((pkg, ver))

        if len(selected_pkgs) == 1:
            pkg, ver = selected_pkgs[0]
            menu.addAction(f"ℹ️ Package Info", lambda: self._show_pip_info(pkg))
            menu.addSeparator()
            menu.addAction(f"📋 Copy: {_prefix} {pkg}", lambda p=pkg: self._copy_to_clipboard(f"{_prefix} {p}"))
            menu.addAction(f"📋 Copy: {_prefix} {pkg}=={ver}", lambda p=pkg, v=ver: self._copy_to_clipboard(f"{_prefix} {p}=={v}"))
            menu.addSeparator()
            menu.addAction(f"📋 Copy package name", lambda: self._copy_to_clipboard(pkg))
            menu.addAction(f"🌐 Open on PyPI", lambda: self._open_pypi(pkg))
        else:
            names = " ".join(p for p, _ in selected_pkgs)
            menu.addAction(f"📋 Copy: {_prefix} {names}", lambda: self._copy_to_clipboard(f"{_prefix} {names}"))
            pinned = " ".join(f"{p}=={v}" for p, v in selected_pkgs if v)
            if pinned:
                menu.addAction(f"📋 Copy with versions", lambda: self._copy_to_clipboard(f"{_prefix} {pinned}"))

        menu.exec(self.packages_table.viewport().mapToGlobal(position))

    def _catalog_table_context_menu(self, position):
        """Right-click context menu for catalog table — same style as Installed."""
        row = self.catalog_table.rowAt(position.y())
        if row < 0:
            return

        pkg_item = self.catalog_table.item(row, 1)
        desc_item = self.catalog_table.item(row, 2)
        if not pkg_item:
            return

        pkg = pkg_item.text().strip()
        is_installed = pkg.lower() in self.installed_package_names

        menu = QMenu(self)
        _env_type = getattr(self, "_current_env_type", "venv")
        _prefixes = {
            "venv": "pip install", "uv": "uv pip install",
            "poetry": "poetry add",
            "conda": "conda install", "pipx": "pipx install",
        }
        _prefix = _prefixes.get(_env_type, "pip install")

        menu.addAction(f"ℹ️ Package Info", lambda: self._show_pip_info(pkg))
        if not is_installed:
            menu.addAction(f"⬇️ Install {pkg}", lambda: self._install_packages([pkg], hint_name=pkg))
        menu.addSeparator()
        menu.addAction(f"📋 Copy: {_prefix} {pkg}", lambda: self._copy_to_clipboard(f"{_prefix} {pkg}"))
        menu.addAction(f"📋 Copy package name", lambda: self._copy_to_clipboard(pkg))
        menu.addSeparator()
        menu.addAction(f"🌐 Open on PyPI", lambda: self._open_pypi(pkg))
        menu.exec(self.catalog_table.viewport().mapToGlobal(position))

    def _show_pip_info(self, pkg_name: str):
        """Show package info — pip show if installed, PyPI API if not."""
        if not self.pip_manager:
            return

        info_text = ""
        from_pypi = False

        # Try pip show first (installed packages)
        try:
            python_exe = get_python_executable(self.pip_manager.venv_path)
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "show", pkg_name],
                **subprocess_args(capture_output=True, text=True, timeout=10)
            )
            output = result.stdout.strip()
            if output and "WARNING" not in output.split("\n")[0]:
                info_text = output
        except Exception:
            pass

        # Not installed — fetch from PyPI JSON API
        if not info_text:
            from_pypi = True
            try:
                import socket, ssl, json as _json
                host = "pypi.org"
                path = f"/pypi/{pkg_name}/json"
                ctx = ssl.create_default_context()
                with socket.create_connection((host, 443), timeout=8) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        req = (
                            f"GET {path} HTTP/1.1\r\n"
                            f"Host: {host}\r\n"
                            f"User-Agent: VenvStudio\r\n"
                            f"Accept: application/json\r\n"
                            f"Connection: close\r\n\r\n"
                        )
                        ssock.sendall(req.encode("utf-8"))
                        chunks = []
                        while True:
                            chunk = ssock.recv(4096)
                            if not chunk:
                                break
                            chunks.append(chunk)
                raw = b"".join(chunks).decode("utf-8", errors="replace")
                body = raw.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in raw else raw
                data = _json.loads(body)
                info = data.get("info", {})
                deps = info.get("requires_dist") or []
                info_text = (
                    f"Name: {info.get('name', pkg_name)}\n"
                    f"Version: {info.get('version', '?')}\n"
                    f"Summary: {info.get('summary', '')}\n"
                    f"Author: {info.get('author', '') or info.get('author_email', '')}\n"
                    f"License: {info.get('license', '')}\n"
                    f"Home-page: {info.get('home_page', '') or info.get('project_url', '')}\n"
                    f"Requires-Python: {info.get('requires_python', '')}\n"
                    f"Requires-Dist: {', '.join(deps[:15])}"
                )
            except Exception:
                info_text = f"Name: {pkg_name}\nStatus: Not installed — could not fetch info from PyPI"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"📦 {pkg_name} — Package Info")
        dialog.setMinimumSize(520, 400)
        dialog.resize(600, 450)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)

        # Source indicator
        if from_pypi:
            source_lbl = QLabel("⚠️ Not installed — info fetched from PyPI")
            source_lbl.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_tiny']}px; padding: 2px 0;")
            layout.addWidget(source_lbl)

        # Scrollable info area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"QFrame {{ background-color: {self._c()['card']}; border: 1px solid {self._c()['border']}; border-radius: 6px; padding: 4px; }}"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        pypi_url = None
        for line in info_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()

                display_val = val
                if len(val) > 200:
                    display_val = val[:200] + "…"

                row = QHBoxLayout()
                key_lbl = QLabel(f"{key}:")
                key_lbl.setFixedWidth(120)
                key_lbl.setStyleSheet(f"color: {self._c()['accent']}; font-weight: bold; font-size: {self._c()['fs_small']}px;")
                key_lbl.setAlignment(Qt.AlignTop)
                val_lbl = QLabel(display_val)
                val_lbl.setWordWrap(True)
                val_lbl.setStyleSheet(f"color: {self._c()['fg']}; font-size: {self._c()['fs_small']}px;")
                val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                if val != display_val:
                    val_lbl.setToolTip(val)
                row.addWidget(key_lbl)
                row.addWidget(val_lbl, 1)
                info_layout.addLayout(row)
                if key.lower() == "home-page" and val.startswith("http"):
                    pypi_url = val

        info_layout.addStretch()
        scroll.setWidget(info_frame)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        if from_pypi:
            install_btn = QPushButton(f"⬇️ Install")
            install_btn.setObjectName("success")
            install_btn.setToolTip(f"Install {pkg_name}")
            install_btn.clicked.connect(
                lambda: (dialog.accept(), self._install_packages([pkg_name], hint_name=pkg_name))
            )
            btn_row.addWidget(install_btn)
        if pypi_url:
            home_btn = QPushButton("🌐 Home")
            home_btn.setObjectName("secondary")
            home_btn.setToolTip("Open Homepage")
            home_btn.clicked.connect(lambda: __import__("webbrowser").open(pypi_url))
            btn_row.addWidget(home_btn)
        pypi_btn = QPushButton("📦 PyPI")
        pypi_btn.setObjectName("secondary")
        pypi_btn.setToolTip(f"Open {pkg_name} on PyPI")
        pypi_btn.clicked.connect(lambda: __import__("webbrowser").open(f"https://pypi.org/project/{pkg_name}/"))
        btn_row.addWidget(pypi_btn)
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.setToolTip("Copy all info to clipboard")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(info_text))
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec()

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_label.setText(f"📋 Copied: {text}")

    def _open_pypi(self, package_name):
        """Open package page on PyPI."""
        import webbrowser
        webbrowser.open(f"https://pypi.org/project/{package_name}/")

    def _filter_installed(self, text: str):
        for row in range(self.packages_table.rowCount()):
            item = self.packages_table.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.packages_table.setRowHidden(row, not match)

    # ── Helpers ──

    def _show_command_hint(self, title, command):
        """Show command hint in output log instead of blocking dialog."""
        if hasattr(self, "output_log"):
            self._append_log("\n💡 Equivalent command:")
            self._append_log(f"   {command}\n")

    def _on_progress(self, message: str):
        self.status_label.setText(message)
        self._append_log(message)

    def _on_install_finished(self, success: bool, message: str):
        self._set_busy(False)
        self._append_log(f"\n{'✅ Success' if success else '❌ Failed'}: {message[:500]}")

        # Log for debugging (especially EXE/AppImage builds)
        try:
            from src.utils.logger import get_logger
            log = get_logger("venvstudio.install")
            if success:
                log.info(f"Install OK: {message[:200]}")
            else:
                log.warning(f"Install FAILED: {message[:500]}")
        except Exception:
            pass

        if success:
            self.status_label.setText("Operation completed successfully")
            # Invalidate all caches so next read is fresh
            self._invalidate_cache()
            self._invalidate_env_cache()
            # B182 follow-up: refresh the env info bar at the top of the
            # Packages page (size + package count badges). Without this
            # the header still shows the pre-install values until the
            # user navigates away and back.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            # B182 race fix: refresh_packages() runs subprocess async.
            # Emitting env_refresh_requested *now* would race with the
            # cache write in _on_packages_loaded — MainWindow would read
            # the OLD pkg count from cache. Set a flag instead so
            # _on_packages_loaded emits *after* the new count is saved.
            self._emit_env_refresh_after_load = True
            self.refresh_packages()
        else:
            if "cancelled" not in message.lower():
                # Friendly log message instead of popup
                if "no matching distribution" in message.lower() or "could not find" in message.lower():
                    self.status_label.setText("⚠️ Some packages could not be found on PyPI")
                    self._append_log(
                        "\n⚠️ Some packages could not be found on PyPI.\n"
                        "Please check the package names and try again.\n"
                        "You can search at: https://pypi.org"
                    )
                else:
                    self.status_label.setText("❌ Operation failed")
                    self._append_log(f"\n❌ {message[:500]}")
            else:
                self.status_label.setText("⛔ Operation cancelled")

    def _cancel_operation(self):
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Operation",
                "Are you sure you want to cancel the current operation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.status_label.setText("⛔ Cancelling...")
                self.current_worker.cancel()
                if not self.current_worker.wait(3000):
                    self.current_worker.terminate()
                self._set_busy(False)
                self.status_label.setText("⛔ Operation cancelled")
                self._append_log("\n⛔ Operation cancelled by user")

    def _check_outdated(self):
        """Check for outdated packages and show update option."""
        if not self.pip_manager:
            return
        self._set_busy(True)
        self.status_label.setText("Checking for updates...")

        class OutdatedWorker(QThread):
            finished = Signal(list)
            def __init__(self, pip_mgr):
                super().__init__()
                self.pip_mgr = pip_mgr
            def run(self):
                outdated = self.pip_mgr.list_outdated()
                self.finished.emit(outdated)

        self._outdated_worker = OutdatedWorker(self.pip_manager)
        self._outdated_worker.finished.connect(self._on_outdated_result)
        self._outdated_worker.start()

    def _on_outdated_result(self, outdated):
        self._set_busy(False)
        if not outdated:
            self.status_label.setText(tr("no_updates"))
            QMessageBox.information(self, tr("updates"), tr("no_updates"))
            return

        self.status_label.setText(tr("outdated_packages").format(n=len(outdated)))

        msg = tr("outdated_packages").format(n=len(outdated)) + "\n\n"
        for pkg in outdated:
            msg += f"  {pkg.name}: {pkg.version} → {pkg.latest_version}\n"
        msg += f"\n{tr('update_all')}?"

        reply = QMessageBox.question(
            self, tr("updates"), msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            pkg_names = [p.name for p in outdated]
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.install_packages, pkg_names, upgrade=True
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _copy_preset_command(self, packages):
        """Copy install command to clipboard (env-type-aware)."""
        _env_type = getattr(self, "_current_env_type", "venv")
        _cmd_prefixes = {
            "venv":   "pip install",
            "uv":     "uv pip install",
            "poetry": "poetry add",
            "conda":  "conda install",
            "pipx":   "pipx install",
        }
        _prefix = _cmd_prefixes.get(_env_type, "pip install")
        cmd = f"{_prefix} {' '.join(packages)}"
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(cmd)
        self.status_label.setText(f"📋 {tr('command_copied')}")

    def _copy_launcher_commands(self, install_cmd: str, run_cmd: str, app_name: str):
        """Copy both install and run commands to clipboard."""
        from PySide6.QtWidgets import QApplication
        full_cmd = f"{install_cmd}\n{run_cmd}"
        QApplication.clipboard().setText(full_cmd)
        self.status_label.setText(f"📋 Copied install + run commands for {app_name}")

    def _uninstall_preset(self, packages: list, preset_name: str):
        """Uninstall all packages in a preset with confirmation."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        # Find which packages are actually installed
        normalized_installed = {p.lower().replace("-", "_").replace(".", "_") for p in self.installed_package_names}
        installed_pkgs = [
            p for p in packages
            if p.lower().replace("-", "_").replace(".", "_") in normalized_installed
        ]

        if not installed_pkgs:
            QMessageBox.information(self, preset_name, "No packages from this preset are installed.")
            return

        reply = QMessageBox.question(
            self, f"Uninstall {preset_name}",
            f"Are you sure you want to uninstall these packages?\n\n"
            f"{', '.join(installed_pkgs)}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.status_label.setText(f"Uninstalling {preset_name}...")
        self.current_worker = WorkerThread(
            self.pip_manager.uninstall_packages, installed_pkgs
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _filter_catalog(self, text: str):
        """Filter catalog rows by search text."""
        for row in range(self.catalog_table.rowCount()):
            name_item = self.catalog_table.item(row, 1)
            desc_item = self.catalog_table.item(row, 2)
            if name_item:
                match = text.lower() in name_item.text().lower()
                if desc_item:
                    match = match or text.lower() in desc_item.text().lower()
                self.catalog_table.setRowHidden(row, not match)

    def _set_busy(self, busy: bool):
        self.progress_bar.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.tabs.setEnabled(not busy)
    def _on_tab_changed(self, index: int):
        """Build tab content lazily on first visit."""
        self._ensure_tab_built(index)

    def _ensure_tab_built(self, index: int):
        """Build tab widget at index if not yet built."""
        if index < 0 or index >= len(self._tab_defs):
            return
        key = self._tab_defs[index][0]
        if self._tab_built.get(key):
            return
        creators = {
            "launcher":  self._create_launcher_tab,
            "installed": self._create_installed_tab,
            "catalog":   self._create_catalog_tab,
            "presets":   self._create_presets_tab,
            "manual":    self._create_manual_tab,
        }
        creator = creators.get(key)
        if not creator:
            return
        # Clear stub widgets so creator assigns fresh ones
        stub_attrs = {
            "installed":  ["packages_table", "pkg_count_label", "search_input",
                           "update_btn", "uninstall_btn"],
            "catalog":    ["catalog_table", "category_combo", "catalog_search",
                           "apply_btn", "changes_label"],
            "presets":    [],
            "manual":     ["manual_input", "manual_info_label", "output_log"],
        }
        for attr in stub_attrs.get(key, []):
            if hasattr(self, attr):
                try:
                    getattr(self, attr).setParent(None)
                except Exception:
                    pass
                delattr(self, attr)
        # B180: build the tab inside try/except so a creator crash does NOT
        # leave the QTabWidget in an inconsistent state (previously the old
        # placeholder was removed first, then insertTab failed → duplicate
        # tabs accumulated on every retry).
        try:
            widget = creator()
        except Exception as _ce:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.tabs").error(
                    f"[B180] Tab '{key}' creator failed: {type(_ce).__name__}: {_ce}"
                )
            except Exception:
                pass
            # Build a minimal error placeholder so the user sees something
            from PySide6.QtWidgets import QWidget as _QW, QVBoxLayout as _QV, QLabel as _QL
            widget = _QW()
            _lay = _QV(widget)
            _lay.addWidget(_QL(
                f"⚠ Could not build the {key.title()} tab.\n"
                f"Error: {type(_ce).__name__}: {_ce}\n\n"
                f"This is usually a PySide6 / Python 3.13 compatibility issue (B180).\n"
                f"Please update to Python 3.13.5+ or report this on GitHub."
            ))
        # Replace placeholder with real widget — both calls always run together.
        # B180: mark the tab as built BEFORE touching tabs.* so any signal that
        # re-enters _on_tab_changed during removeTab/insertTab/setCurrentIndex
        # short-circuits at `if self._tab_built.get(key): return`. Also block
        # tab-change signals while we mutate the QTabWidget — Qt 6.10.2 on
        # Linux/Python 3.13 fires currentChanged on setCurrentIndex even when
        # the index does not actually change, which previously caused the
        # function to recurse until RecursionError.
        self._tab_built[key] = True
        _was_blocked = False
        try:
            _was_blocked = self.tabs.blockSignals(True)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, widget, self._tab_defs[index][1])
            self.tabs.setTabToolTip(index, self._tab_defs[index][3])
            self._tab_defs[index] = (key, self._tab_defs[index][1], widget, self._tab_defs[index][3])
            self.tabs.setCurrentIndex(index)
        except Exception as _re:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.tabs").error(
                    f"[B180] Tab '{key}' replace failed: {_re}"
                )
            except Exception:
                pass
        finally:
            try:
                self.tabs.blockSignals(_was_blocked)
            except Exception:
                pass


