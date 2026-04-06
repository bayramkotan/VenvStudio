"""
VenvStudio - Environment Creation Dialog
With progress bar, status messages, and cancel support
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread

from src.utils.platform_utils import find_system_pythons

class CreateWorker(QThread):
    """Worker thread for async environment creation."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, name, python_path, with_pip, system_site_packages):
        super().__init__()
        self.venv_manager = venv_manager
        self.name = name
        self.python_path = python_path
        self.with_pip = with_pip
        self.system_site_packages = system_site_packages
        self._cancelled = False

    def run(self):
        success, msg = self.venv_manager.create_venv(
            name=self.name,
            python_path=self.python_path,
            with_pip=self.with_pip,
            system_site_packages=self.system_site_packages,
            callback=self._on_progress,
        )
        if self._cancelled:
            import shutil
            venv_path = self.venv_manager.base_dir / self.name
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            self.finished.emit(False, "Creation cancelled by user")
        else:
            self.finished.emit(success, msg)

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True

class EnvCreateDialog(QDialog):
    """Dialog for creating a new virtual environment."""

    env_created = Signal(str)

    def __init__(self, venv_manager, config_manager, parent=None):
        super().__init__(parent)
        self.venv_manager = venv_manager
        self.config = config_manager
        self.pythons = find_system_pythons()
        self.worker = None

        self.setWindowTitle("Create New Environment")
        self.setMinimumSize(920, 420)  # min size, not fixed — allows DPI scaling
        self.resize(960, 460)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        # Title
        title = QLabel("Create New Environment")
        title.setObjectName("header")
        root.addWidget(title)

        self.subtitle_label = QLabel("Set up a fresh Python virtual environment")
        subtitle = self.subtitle_label
        subtitle.setObjectName("subheader")
        root.addWidget(subtitle)

        # Horizontal body
        body = QHBoxLayout()
        body.setSpacing(16)

        # LEFT: form + options
        left = QVBoxLayout()
        left.setSpacing(10)

        form_group = QGroupBox("Environment Settings")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., my-project, data-science, web-api")
        self.name_input.returnPressed.connect(self._create)
        self._name_form_label = QLabel("Name:")
        form_layout.addRow(self._name_form_label, self.name_input)

        loc_layout = QHBoxLayout()
        loc_layout.setSpacing(8)
        self.location_label = QLabel(str(self.config.get_venv_base_dir()))
        self.location_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.location_label.setMinimumWidth(120)
        loc_layout.addWidget(self.location_label, 1)
        change_btn = QPushButton("Browse")
        change_btn.setObjectName("secondary")
        change_btn.setFixedHeight(28)
        change_btn.setFixedWidth(80)
        change_btn.setToolTip("Browse for a different folder")
        change_btn.setFocusPolicy(Qt.NoFocus)
        change_btn.setDefault(False)
        change_btn.setAutoDefault(False)
        change_btn.clicked.connect(self._change_location)
        loc_layout.addWidget(change_btn)
        form_layout.addRow("Location:", loc_layout)

        # ── Environment Type ──────────────────────────────────────────────
        from PySide6.QtWidgets import QComboBox as _QCB
        self.env_type_combo = _QCB()
        self.env_type_combo.addItem("🐍 Python Virtual Environment", "venv")
        self.env_type_combo.addItem("⚡ uv Environment", "uv")
        self.env_type_combo.addItem("📜 Poetry Environment", "poetry")
        # Rye removed — no longer maintained, users redirected to uv
        self.env_type_combo.addItem("📦 pipx App", "pipx")
        self.env_type_combo.addItem("🦎 Conda Environment (micromamba)", "conda")
        # Tool Environment removed — system apps accessible from all env types
        self.env_type_combo.setToolTip(
            "Python venv: isolated Python environment with pip\n"
            "uv: fast Rust-powered environment (10-100× faster)\n"
            "Poetry: dependency management with pyproject.toml\n"
            "Conda: micromamba-powered — R, RStudio, scientific packages\n"
            "pipx: install isolated CLI apps globally"
        )
        self.env_type_combo.currentIndexChanged.connect(self._on_env_type_changed)
        form_layout.addRow("Type:", self.env_type_combo)

        # Pre-select default env type from settings
        try:
            default_et = self.config.get("default_env_type", "venv")
            et_idx = self.env_type_combo.findData(default_et)
            if et_idx >= 0:
                self.env_type_combo.setCurrentIndex(et_idx)
        except Exception:
            pass

        # ── Conda options row (hidden by default) ─────────────────────────
        from PySide6.QtWidgets import QWidget as _QW2
        self.conda_row_widget = _QW2()
        _conda_layout = QVBoxLayout(self.conda_row_widget)
        _conda_layout.setContentsMargins(0, 0, 0, 4)
        _conda_layout.setSpacing(4)

        # Python version for conda env
        _conda_py_row = QHBoxLayout()
        _conda_py_label = QLabel("Python:")
        _conda_py_label.setMinimumWidth(80)
        _conda_py_row.addWidget(_conda_py_label)
        self.conda_python_combo = _QCB()
        self.conda_python_combo.addItem("No Python (tools only)", "")
        for pyver in ("3.13", "3.12", "3.11", "3.10", "3.9"):
            self.conda_python_combo.addItem(f"Python {pyver}", pyver)
        self.conda_python_combo.setCurrentIndex(1)  # default 3.13
        _conda_py_row.addWidget(self.conda_python_combo, 1)
        _conda_layout.addLayout(_conda_py_row)

        # Conda channels info
        _conda_note = QLabel(
            "📦 Uses conda-forge channel — installs R, RStudio, jamovi,\n"
            "JASP, DBeaver and 25,000+ scientific packages.\n"
            "micromamba (~10 MB) will be downloaded automatically."
        )
        _conda_note.setStyleSheet("color: #a6adc8; font-size: 11px;")
        _conda_note.setWordWrap(True)
        _conda_layout.addWidget(_conda_note)

        self.conda_row_label = QLabel("Conda:")
        self.conda_row_widget.setVisible(False)
        self.conda_row_label.setVisible(False)
        form_layout.addRow(self.conda_row_label, self.conda_row_widget)
        # ─────────────────────────────────────────────────────────────────

        self.python_combo = QComboBox()
        self.python_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        import os
        seen_real = {}
        for version, path in self.pythons:
            norm = os.path.normpath(path)
            try:
                real = os.path.realpath(path)
            except OSError:
                real = norm
            if real in seen_real:
                if len(norm) < len(seen_real[real][1]):
                    seen_real[real] = (version, norm)
            else:
                seen_real[real] = (version, norm)

        listed_paths = set()
        first_version = None
        for _real, (version, norm) in seen_real.items():
            self.python_combo.addItem(f"Python {version}", norm)
            listed_paths.add(os.path.normcase(norm))
            if first_version is None:
                first_version = version

        # System Default — en başa ekle
        import shutil, sys, subprocess
        _sys_py = shutil.which("python") or shutil.which("python3") or sys.executable
        _sys_ver = ""
        try:
            r = subprocess.run([_sys_py, "--version"], capture_output=True, text=True, timeout=3)
            _sys_ver = (r.stdout.strip() or r.stderr.strip()).replace("Python ", "")
        except Exception:
            pass
        _sys_label = f"System Default (Python {_sys_ver})" if _sys_ver else "System Default"
        self.python_combo.insertItem(0, _sys_label, "")
        self.python_combo.setCurrentIndex(0)

        custom_pythons = self.config.get("custom_pythons", [])
        print(f"[DEBUG] EnvDialog custom_pythons from config: {custom_pythons}")
        for entry in custom_pythons:
            raw_path = entry.get("path", "")
            if not raw_path:
                continue
            norm = os.path.normpath(raw_path)
            norm_case = os.path.normcase(norm)
            ver = entry.get("version", "?")
            if norm_case in listed_paths:
                print(f"[DEBUG] Skipped duplicate: {norm}")
                continue
            listed_paths.add(norm_case)
            self.python_combo.addItem(f"Python {ver} (Custom)", norm)
            print(f"[DEBUG] Added custom python to env dialog: {ver} -> {norm}")

        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                exe_case = os.path.normcase(exe_path)
                if exe_case in listed_paths:
                    continue
                listed_paths.add(exe_case)
                ver = py.get("version", "?")
                self.python_combo.addItem(f"Python {ver} (Downloaded)", exe_path)
                print(f"[DEBUG] Added downloaded python to env dialog: {ver} -> {exe_path}")
        except Exception as e:
            print(f"[DEBUG] Could not load downloaded pythons: {e}")

        # Python row — back in form_layout but using QLabel widget (not string)
        # so setVisible on the label works reliably
        from PySide6.QtWidgets import QWidget as _QW
        self.python_label_widget = QLabel("Python:")

        _py_inner = _QW()
        _py_inner_layout = QVBoxLayout(_py_inner)
        _py_inner_layout.setContentsMargins(0, 0, 0, 0)
        _py_inner_layout.setSpacing(2)
        _py_inner_layout.addWidget(self.python_combo)

        self.python_path_label = QLabel("")
        self.python_path_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.python_path_label.setWordWrap(False)
        self.python_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        _py_inner_layout.addWidget(self.python_path_label)

        form_layout.addRow(self.python_label_widget, _py_inner)

        form_group.setLayout(form_layout)
        left.addWidget(form_group)

        self.python_combo.currentIndexChanged.connect(self._on_python_changed)
        self._on_python_changed(0)  # İlk seçimi göster

        self.options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        self.upgrade_pip_cb = QCheckBox("Upgrade pip after creation")
        self.upgrade_pip_cb.setChecked(True)
        options_layout.addWidget(self.upgrade_pip_cb)
        self.system_packages_cb = QCheckBox("Include system site-packages")
        self.system_packages_cb.setChecked(False)
        options_layout.addWidget(self.system_packages_cb)
        self.options_group.setLayout(options_layout)
        left.addWidget(self.options_group)
        left.addStretch()

        body.addLayout(left, stretch=4)

        # RIGHT: terminal (always visible, never causes resize)
        right_group = QGroupBox("Progress")
        right_inner = QVBoxLayout()
        right_inner.setSpacing(8)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #585b70; font-size: 12px;")
        right_inner.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        right_inner.addWidget(self.progress_bar)

        self.cmd_label = QLabel(
            "💡 Equivalent terminal commands\nwill appear here when creation starts."
        )
        self.cmd_label.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 14px; color: #585b70; "
            "font-family: Consolas, monospace; font-size: 14px;"
        )
        self.cmd_label.setWordWrap(True)
        self.cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.cmd_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.cmd_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_inner.addWidget(self.cmd_label, stretch=1)

        right_group.setLayout(right_inner)
        right_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(right_group, stretch=5)

        root.addLayout(body, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("  Create Environment  ")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._create)
        btn_layout.addWidget(self.create_btn)

        root.addLayout(btn_layout)

    def _on_env_type_changed(self, index):
        """Show/hide rows based on env type."""
        env_type = self.env_type_combo.currentData()
        is_venv  = env_type == "venv"
        is_conda = env_type == "conda"
        is_pipx  = env_type == "pipx"
        is_pip_like = env_type in ("venv", "uv", "poetry", "pipx")  # types that use Python combo

        # ── Name label + placeholder per env type ─────────────────────────
        if is_pipx:
            if hasattr(self, "_name_form_label"):
                self._name_form_label.setText("Name:")
            self.name_input.setPlaceholderText("e.g., my-pipx-apps, cli-tools, dev-tools")
            self.name_input.setToolTip(
                "Enter an environment name for managing pipx apps.\n"
                "You can install CLI apps later from the Installed/Catalog tabs."
            )
        else:
            if hasattr(self, "_name_form_label"):
                self._name_form_label.setText("Name:")
            self.name_input.setPlaceholderText("e.g., my-project, data-science, web-api")
            self.name_input.setToolTip("")

        # Python row (venv + uv)
        if hasattr(self, "python_label_widget"):
            self.python_label_widget.setVisible(is_pip_like)
        if hasattr(self, "python_combo"):
            self.python_combo.setVisible(is_pip_like)
        if hasattr(self, "python_path_label"):
            self.python_path_label.setVisible(is_pip_like)
        if hasattr(self, "python_combo") and self.python_combo.parent():
            self.python_combo.parent().setVisible(is_pip_like)

        # Conda row
        if hasattr(self, "conda_row_widget"):
            self.conda_row_widget.setVisible(is_conda)
        if hasattr(self, "conda_row_label"):
            self.conda_row_label.setVisible(is_conda)

        # Options (venv + uv only)
        if hasattr(self, "options_group"):
            self.options_group.setVisible(is_pip_like)

        # Subtitles per env type
        subtitles = {
            "venv":   "Set up a fresh Python virtual environment",
            "uv":     "Create a fast uv virtual environment (Rust-powered pip)",
            "poetry": "Create a Poetry project environment",
            "pipx":   "Install an isolated Python CLI application",
            "conda":  "Create a conda environment powered by micromamba",
        }
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setText(subtitles.get(env_type, subtitles["venv"]))

        # Progress panel hints
        hints = {
            "venv": (
                "💡  Equivalent terminal commands:\n"
                "will appear here when creation starts."
            ),
            "uv": (
                "⚡  uv is 10-100x faster than pip.\n\n"
                "uv will be downloaded automatically\n"
                "if not already installed (~5 MB).\n\n"
                "Equivalent: uv venv <name>"
            ),
            "poetry": (
                "📜  Poetry manages dependencies and\n"
                "virtual environments together.\n\n"
                "Poetry will be installed automatically\n"
                "if not already available.\n\n"
                "Equivalent: poetry new <name>"
            ),
            "pipx": (
                "📦  pipx installs Python CLI apps\n"
                "into isolated environments.\n\n"
                "Enter the package name (e.g. 'httpie',\n"
                "'black', 'poetry', 'ruff').\n\n"
                "Equivalent: pipx install <package>"
            ),
            "conda": (
                "🦎  A Conda Environment will be created\n"
                "    using micromamba + conda-forge.\n\n"
                "You can install R, RStudio, jamovi, JASP,\n"
                "DBeaver and 25,000+ packages from the\n"
                "Launch tab after creation."
            ),
        }
        self.cmd_label.setText(hints.get(env_type, hints["venv"]))

    def _on_python_changed(self, index):
        """Seçili Python'un tam yolunu göster."""
        import shutil, sys
        data = self.python_combo.currentData()
        if data:
            self.python_path_label.setText(f"📍 {data}")
        else:
            py = shutil.which("python") or shutil.which("python3") or sys.executable
            self.python_path_label.setText(f"📍 {py}")

    def _change_location(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Base Directory",
            str(self.config.get_venv_base_dir()),
        )
        if directory:
            self.config.set_venv_base_dir(directory)
            self.venv_manager.set_base_dir(Path(directory))
            self.location_label.setText(directory)

    def _create(self):
        name = self.name_input.text().strip()

        # ── Determine env type early for pipx-specific validation ─────
        env_type = self.env_type_combo.currentData() if hasattr(self, "env_type_combo") else "venv"

        if not name:
            QMessageBox.warning(self, "Warning", "Please enter an environment name.")
            return

        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in name):
            QMessageBox.warning(
                self, "Warning",
                "Environment name contains invalid characters.\n"
                "Avoid: spaces, /, \\, :, *, ?, \", <, >, |"
            )
            return

        # ── Empty folder env ──────────────────────────────────────────────

        # ── Conda env ─────────────────────────────────────────────────────
        if env_type == "conda":
            import os
            location = self.location_label.text()
            env_path = Path(os.path.join(location, name))
            python_version = self.conda_python_combo.currentData() \
                if hasattr(self, "conda_python_combo") else "3.12"

            self.progress_bar.setVisible(True)
            self.create_btn.setEnabled(False)
            self.create_btn.setText("Creating...")
            self.name_input.setEnabled(False)
            self.env_type_combo.setEnabled(False)
            self.status_label.setText("Preparing micromamba...")

            def _do_conda_create(callback=None):
                from src.core.micromamba_installer import (
                    get_micromamba_exe, download_micromamba,
                    create_conda_env, write_conda_marker,
                )
                import datetime, json
                # Step 1: ensure micromamba available
                if not get_micromamba_exe():
                    if callback:
                        callback("Downloading micromamba...")
                    download_micromamba(progress_cb=callback)

                if not get_micromamba_exe():
                    return False, "Could not download micromamba"

                # Step 2: create env
                ok = create_conda_env(
                    env_path=env_path,
                    python_version=python_version,
                    progress_cb=callback,
                )
                if not ok:
                    return False, "conda env creation failed"

                # Step 3: write marker
                write_conda_marker(env_path, python_version=python_version)

                return True, f"Conda environment '{name}' created!"

            def _on_conda_done(success, message):
                self.progress_bar.setVisible(False)
                self.create_btn.setEnabled(True)
                self.create_btn.setText("Create Environment")
                self.name_input.setEnabled(True)
                self.env_type_combo.setEnabled(True)
                if success:
                    self.status_label.setText(f"✅ {message}")
                    self.env_created.emit(name)
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(800, self.accept)
                else:
                    self.status_label.setText(f"❌ {message}")
                    QMessageBox.critical(self, "Error", message)

            from src.gui.package_panel import WorkerThread
            self.worker = WorkerThread(_do_conda_create)
            self.worker.progress.connect(
                lambda msg: self.cmd_label.setText(msg))
            self.worker.finished.connect(_on_conda_done)
            self.worker.start()
            return
        # ── conda end ─────────────────────────────────────────────────────

        # ── uv / Poetry / Rye / pipx ──────────────────────────────────────
        if env_type in ("uv", "poetry", "pipx"):
            import os, shutil as _shutil
            location = self.location_label.text()
            env_path = Path(os.path.join(location, name))
            python_path = self.python_combo.currentData() or None

            # ── Pre-check: is the required tool available? ────────────
            from src.core.tool_registry import ToolRegistry
            _registry = ToolRegistry()

            _tool_checks = {
                "uv":     ("uv",     "pip install uv"),
                "poetry": ("poetry", "pip install poetry"),
                "pipx":   ("pipx",   "pip install --user pipx"),
            }
            _tool_name, _tool_install = _tool_checks.get(env_type, ("", ""))

            # Use registry first, then shutil.which, then python -m
            _tool_path = _registry.find(_tool_name)
            _tool_found = bool(_tool_path)

            if not _tool_found and env_type in ("uv", "poetry", "pipx"):
                import sys as _sys, subprocess as _sp
                try:
                    _t = _sp.run(
                        [_sys.executable, "-m", _tool_name, "--version"],
                        capture_output=True, text=True, timeout=5
                    )
                    if _t.returncode == 0:
                        _tool_found = True
                        _ver = _t.stdout.strip().split()[-1] if _t.stdout.strip() else ""
                        _registry.register(_tool_name,
                                           f"python -m {_tool_name}",
                                           version=_ver,
                                           installed_by="python_module")
                except Exception:
                    pass

            if not _tool_found:
                _msg = (
                    f"'{_tool_name}' is not installed on your system.\n\n"
                    f"VenvStudio can try to install it automatically.\n"
                    f"Manual install: {_tool_install}\n\n"
                    f"Install '{_tool_name}' now?"
                )
                reply = QMessageBox.question(
                    self, f"{_tool_name} Not Found",
                    _msg,
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
            # ── End pre-check ─────────────────────────────────────────

            self.progress_bar.setVisible(True)
            self.create_btn.setEnabled(False)
            self.create_btn.setText("Creating...")
            self.name_input.setEnabled(False)
            self.env_type_combo.setEnabled(False)
            self.status_label.setText(f"Creating {env_type} environment...")

            _env_path = env_path
            _python  = python_path
            _name    = name
            _etype   = env_type

            def _do_alt_create(callback=None):
                import subprocess, shutil, sys, json, datetime
                from src.utils.platform_utils import get_platform, subprocess_args
                plat = get_platform()

                def _cb(msg):
                    if callback: callback(msg)

                # Registry for tracking tool paths
                from src.core.tool_registry import ToolRegistry
                _reg = ToolRegistry()

                def _find_tool_registered(name_):
                    """Find tool: registry → shutil.which → Scripts dir."""
                    # 1. Registry
                    reg_path = _reg.find(name_)
                    if reg_path and os.path.isfile(reg_path):
                        return reg_path
                    # 2. shutil.which
                    found = shutil.which(name_) or shutil.which(name_ + ".exe")
                    if found:
                        _reg.register(name_, found, installed_by="system")
                        return found
                    # 3. Scripts dir
                    scripts = os.path.join(os.path.dirname(sys.executable),
                        "Scripts" if sys.platform == "win32" else "bin")
                    for n in (name_, name_ + ".exe"):
                        cand = os.path.join(scripts, n)
                        if os.path.isfile(cand):
                            _reg.register(name_, cand, installed_by="system")
                            return cand
                    return None

                if _etype == "uv":
                    # ── uv ───────────────────────────────────────────────
                    def _find_tool(name_):
                        return _find_tool_registered(name_)

                    uv_exe = _find_tool("uv")
                    if not uv_exe:
                        _cb("Installing uv...")
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", "uv", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        uv_exe = _find_tool("uv")
                        if uv_exe:
                            _reg.register("uv", uv_exe, installed_by="venvstudio")
                        elif not uv_exe:
                            # Try python -m uv
                            t = subprocess.run([sys.executable, "-m", "uv", "--version"],
                                               capture_output=True, **subprocess_args())
                            if t.returncode == 0:
                                uv_exe = f"{sys.executable} -m uv"
                            else:
                                return False, "Could not install uv — try: pip install uv"

                    if " -m " in str(uv_exe):
                        cmd = uv_exe.split() + ["venv", str(_env_path)]
                    else:
                        cmd = [uv_exe, "venv", str(_env_path)]
                    if _python:
                        cmd += ["--python", _python]
                    _cb(f"$ {' '.join(cmd)}")
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=120, **subprocess_args())
                    if r.returncode != 0:
                        return False, r.stderr[:400] or "uv venv failed"
                    # Detect Python version in new env
                    _uv_pyver = ""
                    try:
                        if plat == "windows":
                            _uv_py = _env_path / "Scripts" / "python.exe"
                        else:
                            _uv_py = _env_path / "bin" / "python"
                        if _uv_py.exists():
                            _vr = subprocess.run(
                                [str(_uv_py), "--version"],
                                capture_output=True, text=True, timeout=5,
                                **subprocess_args()
                            )
                            _uv_pyver = (_vr.stdout.strip() or _vr.stderr.strip()
                                          ).replace("Python ", "")
                    except Exception:
                        pass
                    # Write marker
                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({"type": "uv", "name": _name,
                                   "python_version": _uv_pyver,
                                   "created": datetime.datetime.now().isoformat()}, f, indent=2)
                    _cb(f"✅ uv environment '{_name}' created!")
                    return True, f"uv environment '{_name}' created"

                elif _etype == "poetry":
                    # ── Poetry ───────────────────────────────────────────
                    poetry_exe = _find_tool("poetry")
                    if not poetry_exe:
                        _cb("Installing Poetry...")
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", "poetry", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        poetry_exe = _find_tool("poetry")
                        if poetry_exe:
                            _reg.register("poetry", poetry_exe, installed_by="venvstudio")
                        elif not poetry_exe:
                            return False, (
                                "Could not install Poetry automatically.\n\n"
                                "Install manually:\n"
                                "  pip install poetry\n\n"
                                "Or visit: https://python-poetry.org/docs/#installation"
                            )
                    _env_path.mkdir(parents=True, exist_ok=True)
                    cmd = [poetry_exe, "new", str(_env_path)]
                    _cb(f"$ {' '.join(cmd)}")
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=120, cwd=str(_env_path.parent),
                                       **subprocess_args())
                    if r.returncode != 0:
                        # poetry new fails if dir exists — try init
                        cmd2 = [poetry_exe, "init", "--no-interaction",
                                "--name", _name]
                        r2 = subprocess.run(cmd2, capture_output=True, text=True,
                                            timeout=60, cwd=str(_env_path),
                                            **subprocess_args())
                        if r2.returncode != 0:
                            return False, r.stderr[:400] or "poetry new failed"

                    # Use selected Python if specified
                    if _python:
                        _cb(f"Setting Python: poetry env use {_python}")
                        _env_cmd = [poetry_exe, "env", "use", _python]
                        subprocess.run(_env_cmd, capture_output=True, text=True,
                                       timeout=60, cwd=str(_env_path),
                                       **subprocess_args())

                    # Detect Python version
                    _po_pyver = ""
                    try:
                        if _python:
                            _po_py = Path(_python)
                        else:
                            _po_py = (_env_path / ".venv" / ("Scripts" if plat == "windows" else "bin")
                                      / ("python.exe" if plat == "windows" else "python"))
                        if not _po_py.exists():
                            _po_py_str = shutil.which("python3") or shutil.which("python") or sys.executable
                            _po_py = Path(_po_py_str)
                        if _po_py.exists():
                            _vr = subprocess.run(
                                [str(_po_py), "--version"],
                                capture_output=True, text=True, timeout=5,
                                **subprocess_args()
                            )
                            _po_pyver = (_vr.stdout.strip() or _vr.stderr.strip()
                                          ).replace("Python ", "")
                    except Exception:
                        pass
                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({"type": "poetry", "name": _name,
                                   "python_version": _po_pyver,
                                   "created": datetime.datetime.now().isoformat()}, f, indent=2)
                    _cb(f"✅ Poetry environment '{_name}' created!")
                    return True, f"Poetry environment '{_name}' created"

                elif _etype == "pipx":
                    # ── pipx ─────────────────────────────────────────────
                    # Just create a marker folder — pipx apps are managed
                    # from Installed/Catalog tabs after env creation.
                    def _find_pipx():
                        # 1. shutil.which
                        found = shutil.which("pipx") or shutil.which("pipx.exe")
                        if found:
                            return found
                        # 2. Scripts/bin dir next to current python
                        import os
                        scripts = os.path.join(os.path.dirname(sys.executable),
                                               "Scripts" if sys.platform == "win32" else "bin")
                        for name_ in ("pipx", "pipx.exe"):
                            cand = os.path.join(scripts, name_)
                            if os.path.isfile(cand):
                                return cand
                        # 3. User base Scripts
                        import site
                        user_scripts = os.path.join(site.getusersitepackages(),
                                                     "..", "..", "Scripts" if sys.platform == "win32" else "bin")
                        for name_ in ("pipx", "pipx.exe"):
                            cand = os.path.normpath(os.path.join(user_scripts, name_))
                            if os.path.isfile(cand):
                                return cand
                        return None

                    # Ensure pipx is available on the system
                    pipx_exe = _find_pipx()
                    if not pipx_exe:
                        _cb("Installing pipx...")
                        r = subprocess.run(
                            [sys.executable, "-m", "pip", "install", "--user", "pipx", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        pipx_exe = _find_pipx()
                        if pipx_exe:
                            _reg.register("pipx", pipx_exe, installed_by="venvstudio")

                    if not pipx_exe:
                        # Test python -m pipx works
                        test = subprocess.run(
                            [sys.executable, "-m", "pipx", "--version"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        if test.returncode != 0:
                            return False, (
                                "Could not install pipx.\n\n"
                                "Install manually:\n  pip install pipx\n"
                                "Then: pipx ensurepath"
                            )

                    # Get Python version from selected Python
                    _pipx_python = _python or sys.executable
                    _pipx_pyver = ""
                    try:
                        _pv = subprocess.run(
                            [_pipx_python, "--version"],
                            capture_output=True, text=True, timeout=5,
                            **subprocess_args()
                        )
                        _pipx_pyver = (
                            _pv.stdout.strip() or _pv.stderr.strip()
                        ).replace("Python ", "")
                    except Exception:
                        pass

                    # Create marker folder in venv base dir
                    _env_path.mkdir(parents=True, exist_ok=True)
                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({
                            "type": "pipx",
                            "name": _name,
                            "python_version": _pipx_pyver,
                            "python_path": _pipx_python,
                            "created": datetime.datetime.now().isoformat(),
                        }, f, indent=2)

                    _cb(f"✅ pipx environment '{_name}' created!")
                    return True, f"pipx environment '{_name}' created"

                return False, f"Unknown env type: {_etype}"

            def _on_alt_done(success, message):
                self.progress_bar.setVisible(False)
                self.create_btn.setEnabled(True)
                self.create_btn.setText("Create Environment")
                self.name_input.setEnabled(True)
                self.env_type_combo.setEnabled(True)
                if success:
                    self.status_label.setText(f"✅ {message}")
                    self.env_created.emit(_name)
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(800, self.accept)
                else:
                    self.status_label.setText(f"❌ Failed")
                    QMessageBox.critical(self, "Error", message)

            from src.gui.package_panel import WorkerThread
            self.worker = WorkerThread(_do_alt_create)
            self.worker.progress.connect(lambda msg: self.cmd_label.setText(msg))
            self.worker.finished.connect(_on_alt_done)
            self.worker.start()
            return
        # ── alt env types end ─────────────────────────────────────────────

        python_path = self.python_combo.currentData() or None

        self.progress_bar.setVisible(True)
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        self.name_input.setEnabled(False)
        self.python_combo.setEnabled(False)
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.status_label.setText("Initializing environment...")
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setStyleSheet("")

        py_exe = python_path or "python"
        location = self.location_label.text()
        import os
        venv_path = os.path.join(location, name)

        from src.utils.platform_utils import get_platform
        cmds = ["💡  Equivalent terminal commands:", ""]
        cmds.append(f"$ {py_exe} -m venv {venv_path}")
        if get_platform() == "windows":
            cmds.append(f"$ {venv_path}\\Scripts\\Activate.ps1")
        else:
            cmds.append(f"$ source {venv_path}/bin/activate")
        cmds.append("$ pip install --upgrade pip")

        self.cmd_label.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 14px; color: #a6e3a1; "
            "font-family: Consolas, monospace; font-size: 14px;"
        )
        self.cmd_label.setText("\n".join(cmds))

        self.worker = CreateWorker(
            self.venv_manager, name, python_path,
            with_pip=True,
            system_site_packages=self.system_packages_cb.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message):
        self.status_label.setText(f"⏳ {message}")

    def _on_finished(self, success, message):
        self.worker = None
        self._reset_ui()

        if success:
            name = self.name_input.text().strip()
            self.config.add_recent_env(name)
            self.env_created.emit(name)
            self.status_label.setText("✅ " + message)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            self.status_label.setText("❌ " + message[:200])
            QMessageBox.critical(self, "Error", message)

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel",
                "Are you sure you want to cancel environment creation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.status_label.setText("⛔ Cancelling...")
                self.worker.cancel()
                self.worker.wait(5000)
                self._reset_ui()
                self.status_label.setText("⛔ Creation cancelled")
        else:
            self.reject()

    def _reset_ui(self):
        self.create_btn.setEnabled(True)
        self.create_btn.setText("  Create Environment  ")
        self.name_input.setEnabled(True)
        self.python_combo.setEnabled(True)
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setStyleSheet("")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        super().closeEvent(event)
