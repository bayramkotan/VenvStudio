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
from src.utils.constants import PACKAGE_CATALOG, PRESETS, COMMAND_HINTS
from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args

from pathlib import Path
import subprocess
import os
import sys


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
            self.finished.emit(False, str(e))

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
        info.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(info)

        cmd_frame = QFrame()
        cmd_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 8px; padding: 12px;"
        )
        cmd_layout = QVBoxLayout(cmd_frame)
        cmd_label = QLabel(f"<code style='font-size:14px; color:#a6e3a1;'>{command}</code>")
        cmd_label.setTextFormat(Qt.RichText)
        cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cmd_layout.addWidget(cmd_label)
        layout.addWidget(cmd_frame)

        tip = QLabel("💡 You can copy this command and run it in any terminal.")
        tip.setStyleSheet("font-size: 11px; color: #6c7086;")
        layout.addWidget(tip)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PackagePanel(QWidget):
    """Package management panel with catalog browsing and pip operations."""
    env_refresh_requested = Signal()  # Signal to refresh env list in main window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pip_manager = None
        self.current_worker = None
        self.installed_package_names = set()
        self._catalog_initial_state = {}  # Track original checkbox states
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Environment selector at top (2-row bar)
        self.env_bar = QFrame()
        self.env_bar.setFixedHeight(72)
        self.env_bar.setStyleSheet(
            "QFrame { background-color: #181825; "
            "border-bottom: 2px solid #313244; }"
        )
        env_bar_outer = QVBoxLayout(self.env_bar)
        env_bar_outer.setContentsMargins(16, 6, 16, 4)
        env_bar_outer.setSpacing(2)

        # ── Row 1: Environment selector + Python version ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        env_lbl = QLabel(f"🐍 {tr('environment')}")
        env_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        row1.addWidget(env_lbl)

        self.env_selector = QComboBox()
        self.env_selector.setMinimumWidth(280)
        self.env_selector.setMaximumWidth(500)
        self.env_selector.setFixedHeight(34)
        # Disable mouse wheel scrolling on env selector to prevent accidental switches
        self.env_selector.wheelEvent = lambda e: e.ignore()
        self.env_selector.setStyleSheet(
            "QComboBox {"
            "  font-size: 14px; font-weight: bold; padding: 4px 12px;"
            "  background-color: #1e1e2e; color: #cdd6f4;"
            "  border: 2px solid #89b4fa; border-radius: 6px;"
            "}"
            "QComboBox:hover { border-color: #b4befe; }"
            "QComboBox::drop-down { border: none; width: 30px; }"
            "QComboBox QAbstractItemView {"
            "  background-color: #1e1e2e; color: #cdd6f4;"
            "  selection-background-color: #89b4fa; selection-color: #1e1e2e;"
            "  font-size: 14px; font-weight: bold;"
            "  border: 1px solid #89b4fa;"
            "}"
        )
        self.env_selector.addItem(tr("select_environment"), "")
        self.env_selector.currentIndexChanged.connect(self._on_env_selector_changed)
        row1.addWidget(self.env_selector)

        # Python version label (bold, large)
        self.python_version_label = QLabel("")
        self.python_version_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #a6e3a1; padding-left: 8px;"
        )
        row1.addWidget(self.python_version_label)

        row1.addStretch()

        self.env_pkg_count = QLabel("")
        self.env_pkg_count.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold;")
        row1.addWidget(self.env_pkg_count)

        env_bar_outer.addLayout(row1)

        # ── Row 2: Info bar — path | disk size | backend | last used ──
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        info_style = "color: #6c7086; font-size: 11px;"
        separator_style = "color: #45475a; font-size: 11px;"

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

        layout.addWidget(self.env_bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_launcher_tab(), f"🚀 {tr('app_launcher')}")
        self.tabs.addTab(self._create_installed_tab(), f"📦 {tr('installed')}")
        self.tabs.addTab(self._create_catalog_tab(), f"🛒 {tr('catalog')}")
        self.tabs.addTab(self._create_presets_tab(), f"⚡ {tr('presets')}")
        self.tabs.addTab(self._create_manual_tab(), f"⌨️ {tr('manual_install')}")
        layout.addWidget(self.tabs)

        # Status bar with cancel button
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(44)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(12, 4, 12, 4)

        self.status_label = QLabel("Select an environment to manage packages")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
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
        info.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(info)

        # App cards grid
        self.launcher_grid = QGridLayout()
        self.launcher_grid.setSpacing(16)

        self.app_definitions = [
            {
                "name": "JupyterLab",
                "icon": "🔬",
                "icon_key": "jupyterlab",
                "package": "jupyterlab",
                "command": ["-m", "jupyter", "lab"],
                "desc": "Next-generation notebook interface for interactive computing",
            },
            {
                "name": "Jupyter Notebook",
                "icon": "📓",
                "icon_key": "jupyter_notebook",
                "package": "notebook",
                "command": ["-m", "jupyter", "notebook"],
                "desc": "Classic Jupyter Notebook — simple, document-centric interface",
            },
            {
                "name": "Orange Data Mining",
                "icon": "🍊",
                "icon_key": "orange3",
                "package": "orange3",
                "command": ["-m", "Orange.canvas"],
                "desc": "Visual programming for data mining and machine learning",
                "min_python": "3.9",
                "note": "PyQt and Orange3 version selected automatically based on Python version.",
            },
            {
                "name": "Spyder IDE",
                "icon": "🕷️",
                "icon_key": "spyder",
                "package": "spyder",
                "command": ["-m", "spyder.app.start"],
                "desc": "Scientific Python development environment",
            },
            {
                "name": "IPython",
                "icon": "🐍",
                "icon_key": "ipython",
                "package": "ipython",
                "command": ["-m", "IPython"],
                "desc": "Enhanced interactive Python shell",
                "needs_console": True,
            },
            {
                "name": "Streamlit",
                "icon": "🎈",
                "icon_key": "streamlit",
                "package": "streamlit",
                "command": ["-m", "streamlit", "hello"],
                "desc": "Build data apps in minutes — launches demo app",
            },
        ]

        self.launcher_cards = {}
        for i, app in enumerate(self.app_definitions):
            card = self._create_app_card(app)
            self.launcher_grid.addWidget(card, i // 3, i % 3)
            self.launcher_cards[app["name"]] = card

        layout.addLayout(self.launcher_grid)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_app_card(self, app_def: dict) -> QFrame:
        """Create a single app launcher card."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(200)
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

        # Icon + Name
        header = QHBoxLayout()
        icon_label = QLabel(app_def["icon"])
        icon_label.setFont(QFont("Segoe UI", 28))
        header.addWidget(icon_label)

        name_label = QLabel(app_def["name"])
        name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header.addWidget(name_label, 1)
        layout.addLayout(header)

        # Description
        desc = QLabel(app_def["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(desc)

        # Status label
        status = QLabel("")
        status.setObjectName(f"status_{app_def['name']}")
        status.setStyleSheet("font-size: 11px;")
        layout.addWidget(status)

        layout.addStretch()

        # Buttons row 1: Launch
        btn_layout = QHBoxLayout()

        launch_btn = QPushButton(f"▶ {tr('launch_app').format(app=app_def['name'])}"
                                 if '{app}' in tr('launch_app') else f"▶ Launch")
        launch_btn.setObjectName("success")
        launch_btn.clicked.connect(lambda checked, a=app_def: self._launch_app(a))
        btn_layout.addWidget(launch_btn)

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

        return card

    def _update_launcher_status(self):
        """Update launcher cards to show installed/not-installed status."""
        # Get current env Python version once
        env_py_version = None
        if self.pip_manager:
            try:
                python_exe = get_python_executable(self.pip_manager.venv_path)
                from src.utils.platform_utils import subprocess_args
                result = subprocess.run(
                    [str(python_exe), "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=5)
                )
                ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                env_py_version = tuple(int(x) for x in ver_str.split(".")[:2])
            except Exception:
                pass

        for name, card in self.launcher_cards.items():
            app_def = card._app_def
            pkg = app_def["package"].lower()
            is_installed = pkg in self.installed_package_names

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
                status.setStyleSheet("color: #f9e2af; font-size: 11px;")
                card._launch_btn.setEnabled(False)
                card._launch_btn.setStyleSheet("background-color: #45475a; color: #6c7086;")
                card._uninstall_btn.setVisible(False)
                card._shortcut_btn.setVisible(False)
            elif is_installed:
                status.setText("✅ Installed")
                status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
                card._launch_btn.setEnabled(True)
                card._launch_btn.setStyleSheet("")
                card._uninstall_btn.setVisible(True)
                card._shortcut_btn.setVisible(True)
            else:
                status.setText(f"❌ Not installed — click Launch to install first")
                status.setStyleSheet("color: #f38ba8; font-size: 11px;")
                card._launch_btn.setEnabled(True)  # Will prompt install
                card._launch_btn.setStyleSheet("")
                card._uninstall_btn.setVisible(False)
                card._shortcut_btn.setVisible(False)

    def _get_orange3_packages(self, python_exe) -> list:
        """Return the right Orange3 + PyQt packages based on Python version."""
        try:
            from src.utils.platform_utils import subprocess_args
            result = subprocess.run(
                [str(python_exe), "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            ver_parts = tuple(int(x) for x in ver_str.split(".")[:2])
        except Exception:
            ver_parts = (3, 12)  # safe default

        if ver_parts <= (3, 9):
            # Orange3 v3.40+ dropped cp39 wheels, use older version
            return ["PyQt6", "PyQt6-WebEngine", "orange3<=3.36.2"]
        else:
            # 3.10+: latest Orange3 with PyQt6
            return ["PyQt6", "PyQt6-WebEngine", "orange3"]

    def _launch_app(self, app_def: dict):
        """Launch an app from the selected environment."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)

        pkg_name = app_def["package"].lower()
        is_installed = pkg_name in self.installed_package_names

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
        cmd = [str(python_exe)] + app_def["command"]

        # Check if app needs console (e.g. IPython)
        show_console = app_def.get("needs_console", False)

        # Working directory: user's home, not venv path
        if get_platform() == "windows":
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
                    # Open in terminal
                    cmd_str = " ".join(f'"{c}"' for c in cmd)
                    try:
                        subprocess.Popen(
                            ["x-terminal-emulator", "-e", f"bash -c '{cmd_str}; read -p Press_Enter'"],
                            cwd=work_dir,
                        )
                    except FileNotFoundError:
                        subprocess.Popen(cmd, cwd=work_dir)
                else:
                    subprocess.Popen(
                        cmd, cwd=work_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )

            self.status_label.setText(f"🚀 Launched {app_def['name']}")
        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                f"Failed to launch {app_def['name']}:\n{e}"
            )

    def _on_app_install_finished(self, success, message, app_def):
        """After installing an app package, refresh and launch."""
        self._set_busy(False)
        if success:
            self.refresh_packages()
            self.status_label.setText(f"✅ {app_def['package']} installed. Launching...")
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

        uninstall_btn = QPushButton(f"🗑️ {tr('uninstall_selected')}")
        uninstall_btn.setObjectName("danger")
        uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(uninstall_btn)

        layout.addLayout(toolbar)

        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(3)
        self.packages_table.setHorizontalHeaderLabels(["Package", "Version", ""])
        self.packages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.packages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.packages_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.packages_table.setColumnWidth(2, 40)
        self.packages_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.packages_table.setAlternatingRowColors(True)
        self.packages_table.verticalHeader().setVisible(False)
        layout.addWidget(self.packages_table)

        bottom = QHBoxLayout()
        self.pkg_count_label = QLabel("0 packages")
        self.pkg_count_label.setStyleSheet("color: #a6adc8;")
        bottom.addWidget(self.pkg_count_label)
        bottom.addStretch()

        # Export dropdown button
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
        bottom.addWidget(export_btn)

        import_btn = QPushButton("📥 Import requirements.txt")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_requirements)
        bottom.addWidget(import_btn)

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
            _cfg = ConfigManager()
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
        legend.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(legend)

        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(4)
        self.catalog_table.setHorizontalHeaderLabels(["Install", "Package", "Description", "Category"])
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.catalog_table.setColumnWidth(0, 55)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.verticalHeader().setVisible(False)
        layout.addWidget(self.catalog_table)

        # Bottom: changes summary + Apply button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.changes_label = QLabel("")
        self.changes_label.setStyleSheet("color: #f9e2af; font-size: 12px;")
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

    def _create_presets_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self._presets_grid = QGridLayout(container)
        self._presets_grid.setSpacing(12)
        self._presets_grid.setContentsMargins(12, 12, 12, 12)

        self._preset_cards = {}
        row = 0
        for preset_name, packages in PRESETS.items():
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)

            # Header with name + installed badge
            header = QHBoxLayout()
            name_label = QLabel(preset_name)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            header.addWidget(name_label, 1)

            badge = QLabel("")
            badge.setStyleSheet("color: #a6e3a1; font-size: 11px; font-weight: bold;")
            header.addWidget(badge)
            card_layout.addLayout(header)

            pkg_text = ", ".join(packages)
            pkg_label = QLabel(pkg_text)
            pkg_label.setWordWrap(True)
            pkg_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
            card_layout.addWidget(pkg_label)

            install_btn = QPushButton(f"{tr('install')} ({len(packages)} packages)")
            install_btn.setObjectName("success")
            install_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._install_packages(pkgs, hint_name=name)
            )
            card_layout.addWidget(install_btn)

            uninstall_btn = QPushButton(f"🗑 {tr('uninstall') if tr('uninstall') != 'uninstall' else 'Uninstall'}")
            uninstall_btn.setObjectName("danger")
            uninstall_btn.setVisible(False)
            uninstall_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._uninstall_preset(pkgs, name)
            )
            card_layout.addWidget(uninstall_btn)

            copy_btn = QPushButton(f"📋 {tr('copy_command')}")
            copy_btn.setObjectName("secondary")
            copy_btn.clicked.connect(
                lambda checked, pkgs=packages: self._copy_preset_command(pkgs)
            )
            card_layout.addWidget(copy_btn)

            self._preset_cards[preset_name] = {
                "badge": badge,
                "install_btn": install_btn,
                "uninstall_btn": uninstall_btn,
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
                badge.setStyleSheet("color: #a6e3a1; font-size: 12px; font-weight: bold;")
                install_btn.setText(f"✅ {tr('installed') if tr('installed') != 'installed' else 'Installed'}")
                install_btn.setEnabled(False)
                install_btn.setStyleSheet("background-color: #313244; color: #a6e3a1; font-weight: bold;")
                if uninstall_btn:
                    uninstall_btn.setVisible(True)
            elif installed_count > 0:
                badge.setText(f"⚡ {installed_count}/{len(packages)}")
                badge.setStyleSheet("color: #f9e2af; font-size: 12px; font-weight: bold;")
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

        info = QLabel(
            "Enter package names separated by spaces or newlines.\n"
            "You can specify versions like: numpy==1.24.0 or pandas>=2.0"
        )
        info.setObjectName("subheader")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.manual_input = QTextEdit()
        self.manual_input.setPlaceholderText(
            "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28"
        )
        layout.addWidget(self.manual_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.manual_input.clear)
        btn_layout.addWidget(clear_btn)

        install_btn = QPushButton("Install Packages")
        install_btn.setObjectName("success")
        install_btn.clicked.connect(self._install_manual)
        btn_layout.addWidget(install_btn)

        layout.addLayout(btn_layout)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(200)
        self.output_log.setPlaceholderText("Installation output will appear here...")
        layout.addWidget(self.output_log)

        return widget

    # ── Public Methods ──

    def set_venv(self, venv_path: Path):
        backend = "pip"
        try:
            from src.core.config_manager import ConfigManager
            backend = ConfigManager().get("package_manager", "pip")
        except Exception:
            pass
        self.pip_manager = PipManager(venv_path, backend=backend)
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
        # Async refresh — UI hemen görünür, paketler arka planda yüklenir
        self._async_refresh_packages()

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

        if not restored and self.env_selector.count() > 1:
            self.env_selector.setCurrentIndex(1)

        self.env_selector.blockSignals(False)

        # Always trigger load for selected env
        current_idx = self.env_selector.currentIndex()
        if current_idx > 0:
            self._on_env_selector_changed(current_idx)

    def _on_env_selector_changed(self, index):
        """Handle env dropdown change."""
        path_str = self.env_selector.currentData()
        if path_str:
            backend = "pip"
            try:
                from src.core.config_manager import ConfigManager
                backend = ConfigManager().get("package_manager", "pip")
            except Exception:
                pass
            self.pip_manager = PipManager(Path(path_str), backend=backend)
            self.status_label.setText(f"Loading packages...")
            self._update_env_info_bar(Path(path_str), backend)
            self._async_refresh_packages()
        else:
            self.pip_manager = None
            self.packages_table.setRowCount(0)
            self.env_pkg_count.setText("")
            self.python_version_label.setText("")
            self._hide_env_info_bar()

    def _update_env_info_bar(self, venv_path, backend="pip"):
        """Update all info labels for the selected environment."""
        # Show info labels
        for lbl in self._info_labels:
            lbl.setVisible(True)

        # 1) Python version
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
            self.python_version_label.setText("")

        # 2) Shortened path
        try:
            full_path = str(venv_path)
            home = str(Path.home())
            if full_path.startswith(home):
                display_path = "~" + full_path[len(home):]
            else:
                display_path = full_path
            # Truncate if too long
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.env_path_label.setText(f"📂 {display_path}")
            self.env_path_label.setToolTip(full_path)
        except Exception:
            self.env_path_label.setText("")

        # 3) Disk size (async-friendly but quick for most envs)
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(str(venv_path)):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
                # Limit depth to avoid very slow scans
                if total_size > 10 * 1024 * 1024 * 1024:  # cap at 10GB scan
                    break
            if total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.0f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            self.env_disk_label.setText(f"💾 {size_str}")
        except Exception:
            self.env_disk_label.setText("💾 ?")

        # 4) Backend (pip/uv)
        backend_display = backend.upper() if backend else "PIP"
        self.env_backend_label.setText(f"⚙️ {backend_display}")

        # 5) Last used (modification time of pyvenv.cfg or activate script)
        try:
            candidates = [
                venv_path / "pyvenv.cfg",
                venv_path / "Scripts" / "activate.bat",
                venv_path / "bin" / "activate",
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
                self.env_last_used_label.setText("")
                self._info_sep3.setVisible(False)
        except Exception:
            self.env_last_used_label.setText("")
            self._info_sep3.setVisible(False)

    def _hide_env_info_bar(self):
        """Hide all info bar labels when no env is selected."""
        for lbl in self._info_labels:
            lbl.setVisible(False)

    def _async_refresh_packages(self):
        """Load packages in background — UI stays responsive."""
        if not self.pip_manager:
            return

        # Cancel / wait for any previous loader to avoid QThread crash
        if hasattr(self, '_pkg_loader') and self._pkg_loader is not None:
            if self._pkg_loader.isRunning():
                self._pkg_loader.done.disconnect()
                self._pkg_loader.wait(2000)  # wait up to 2s

        # Show loading state immediately
        self.packages_table.setRowCount(1)
        loading_item = QTableWidgetItem("Loading...")
        loading_item.setFlags(loading_item.flags() & ~Qt.ItemIsEditable)
        self.packages_table.setItem(0, 0, loading_item)
        self.packages_table.setItem(0, 1, QTableWidgetItem(""))
        self.pkg_count_label.setText("Loading...")
        self.env_pkg_count.setText("Loading packages...")

        # Use QThread for background loading
        class PkgLoader(QThread):
            done = Signal(list)
            def __init__(self, pip_mgr, parent=None):
                super().__init__(parent)
                self.pip_mgr = pip_mgr
            def run(self):
                try:
                    pkgs = self.pip_mgr.list_packages()
                    self.done.emit(pkgs)
                except Exception:
                    self.done.emit([])

        self._pkg_loader = PkgLoader(self.pip_manager, parent=self)
        self._pkg_loader.done.connect(self._on_packages_loaded)
        self._pkg_loader.start()

    def _on_packages_loaded(self, packages):
        """Called when async package loading finishes."""
        if not self.pip_manager:
            return

        self.installed_package_names = {pkg.name.lower() for pkg in packages}

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

    def refresh_packages(self):
        """Refresh installed packages list - shows ALL packages."""
        if not self.pip_manager:
            return

        packages = self.pip_manager.list_packages()
        self.installed_package_names = {pkg.name.lower() for pkg in packages}

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
            config = ConfigManager()
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

        # Show command hint
        cmds = []
        if to_uninstall:
            cmds.append(COMMAND_HINTS["uninstall"].format(packages=" ".join(to_uninstall)))
        if to_install:
            cmds.append(COMMAND_HINTS["install"].format(packages=" ".join(to_install)))
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
            self.output_log.append(f"❌ Uninstall failed: {uninstall_msg[:300]}")
        self.output_log.append("✅ Uninstall done. Starting install...")
        self._do_install(to_install)

    # ── Install / Uninstall ──

    def _install_packages(self, packages: list, hint_name: str = ""):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.\nPlease select an environment first.")
            return

        # Show ALL package names in confirm dialog
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following {len(packages)} package(s)?\n\n• " + "\n• ".join(packages),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint
        cmd = COMMAND_HINTS["install"].format(packages=" ".join(packages))
        self._show_command_hint(hint_name or "Install Packages", cmd)

        self._do_install(packages)

    def _do_install(self, packages):
        """Actually start install worker (no confirm dialog)."""
        self._set_busy(True)
        self.output_log.clear()
        self.current_worker = WorkerThread(self.pip_manager.install_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _install_manual(self):
        text = self.manual_input.toPlainText().strip()
        if not text:
            return

        # Noise words to filter out
        noise = {"pip", "pip3", "python", "python3", "-m", "install", "uninstall",
                 "--upgrade", "--user", "-U", "-r", "--force-reinstall", "--no-cache-dir",
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
            # Replace commas with spaces so "seaborn, numpy, baby" works
            line = line.replace(",", " ").replace(";", " ").replace("|", " ")
            for token in line.split():
                t = token.strip()
                # Skip empty
                if not t:
                    continue
                # Skip noise words
                if t.lower() in noise:
                    continue
                # Skip pure numbers
                if t.isdigit():
                    continue
                # Skip flags (--something, -x)
                if t.startswith("-"):
                    continue
                # Skip tokens that are only special chars (###, **, //, etc)
                import re
                if not re.search(r'[a-zA-Z]', t):
                    continue
                # Valid package name: must start with letter/digit, can have -, _, ., ==, >=, etc.
                # Skip if it looks like garbage (no alphanumeric at all)
                pkg_name = re.split(r'[><=!~;]', t)[0]
                if not pkg_name or not re.match(r'^[a-zA-Z0-9]', pkg_name):
                    continue
                # Deduplicate (case-insensitive)
                key = t.lower()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(t)

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

        cmd = COMMAND_HINTS["uninstall"].format(packages=" ".join(packages))
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
            self._show_command_hint("Export Requirements", COMMAND_HINTS["freeze"])
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
            self._show_command_hint("Import Requirements", COMMAND_HINTS["import_req"])
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.import_requirements, Path(filepath)
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _filter_installed(self, text: str):
        for row in range(self.packages_table.rowCount()):
            item = self.packages_table.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.packages_table.setRowHidden(row, not match)

    # ── Helpers ──

    def _show_command_hint(self, title, command):
        """Show educational command hint dialog."""
        dlg = CommandHintDialog(title, command, self)
        dlg.exec()

    def _on_progress(self, message: str):
        self.status_label.setText(message)
        self.output_log.append(message)

    def _on_install_finished(self, success: bool, message: str):
        self._set_busy(False)
        self.output_log.append(f"\n{'✅ Success' if success else '❌ Failed'}: {message[:500]}")

        if success:
            self.status_label.setText("Operation completed successfully")
            self.refresh_packages()
            self.env_refresh_requested.emit()
        else:
            if "cancelled" not in message.lower():
                # Friendly log message instead of popup
                if "no matching distribution" in message.lower() or "could not find" in message.lower():
                    self.status_label.setText("⚠️ Some packages could not be found on PyPI")
                    self.output_log.append(
                        "\n⚠️ Some packages could not be found on PyPI.\n"
                        "Please check the package names and try again.\n"
                        "You can search at: https://pypi.org"
                    )
                else:
                    self.status_label.setText("❌ Operation failed")
                    self.output_log.append(f"\n❌ {message[:500]}")
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
                self.output_log.append("\n⛔ Operation cancelled by user")

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
        """Copy pip install command to clipboard."""
        cmd = f"pip install {' '.join(packages)}"
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(cmd)
        self.status_label.setText(f"📋 {tr('command_copied')}")

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
