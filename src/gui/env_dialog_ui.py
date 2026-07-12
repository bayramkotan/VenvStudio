"""VenvStudio - Env Create Dialog: UI Mixin
UI construction for EnvCreateDialog (moved from env_dialog.py):
_populate_python_combo, _setup_ui, _on_env_type_changed,
_on_python_changed, _refresh_tool_path_ui.
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QProgressBar, QSizePolicy, QWidget, QTextEdit,
)
from PySide6.QtCore import Qt

# B151: suppress Windows console flash on all subprocess calls
try:
    from src.utils.platform_utils import subprocess_args
except Exception:
    def subprocess_args(**kw): return kw


class EnvDialogUIMixin:
    """Mixin for EnvCreateDialog: UI setup and env-type-driven UI updates."""

    def _populate_python_combo(self):
        """Fill python combo with found Python installations."""
        import os, shutil, sys, subprocess
        self.python_combo.clear()

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
        for _real, (version, norm) in seen_real.items():
            self.python_combo.addItem(f"Python {version}", norm)
            listed_paths.add(os.path.normcase(norm))

        # System Default — insert at top
        _sys_py = shutil.which("python") or shutil.which("python3") or sys.executable
        _sys_ver = ""
        try:
            r = subprocess.run([_sys_py, "--version"],
                               **subprocess_args(capture_output=True, text=True, timeout=3))
            _sys_ver = (r.stdout.strip() or r.stderr.strip()).replace("Python ", "")
        except Exception:
            pass
        _sys_label = f"System Default (Python {_sys_ver})" if _sys_ver else "System Default"
        self.python_combo.insertItem(0, _sys_label, "")
        self.python_combo.setCurrentIndex(0)

        for entry in self.config.get("custom_pythons", []):
            raw_path = entry.get("path", "")
            if not raw_path:
                continue
            norm = os.path.normpath(raw_path)
            if os.path.normcase(norm) in listed_paths:
                continue
            listed_paths.add(os.path.normcase(norm))
            self.python_combo.addItem(f"Python {entry.get('version','?')} (Custom)", norm)

        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                if os.path.normcase(exe_path) in listed_paths:
                    continue
                listed_paths.add(os.path.normcase(exe_path))
                self.python_combo.addItem(
                    f"Python {py.get('version','?')} (Downloaded)", exe_path)
        except Exception:
            pass

        self._on_python_changed(0)

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
        # Live-refresh the example commands card as the user types the name
        self.name_input.textChanged.connect(
            lambda _t: self._on_env_type_changed(self.env_type_combo.currentIndex())
            if hasattr(self, "env_type_combo") else None
        )
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
        # pipx removed from Create dialog — auto-detected and managed automatically
        self.env_type_combo.addItem("🦎 Conda Environment (micromamba)", "conda")
        # Tool Environment removed — system apps accessible from all env types
        self.env_type_combo.setToolTip(
            "Python venv: isolated Python environment with pip\n"
            "uv: fast Rust-powered environment (10-100× faster)\n"
            "Poetry: dependency management with pyproject.toml\n"
            "Conda: micromamba-powered — R, RStudio, scientific packages\n"
            "pipx: auto-detected and shown automatically if installed"
        )
        self.env_type_combo.currentIndexChanged.connect(self._on_env_type_changed)
        form_layout.addRow("Type:", self.env_type_combo)
        # ─────────────────────────────────────────────────────────────────

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
        self.python_combo.addItem("Loading Python installations...", "")

        # Python row
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
        form_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left.addWidget(form_group)

        # ── Tool status note (uv/poetry/pipx only) ────────────────────────
        self.tool_status_widget = QWidget()
        _ts_layout = QHBoxLayout(self.tool_status_widget)
        _ts_layout.setContentsMargins(4, 0, 4, 0)
        _ts_layout.setSpacing(8)

        self.tool_status_label = QLabel("")
        self.tool_status_label.setStyleSheet("font-size: 11px; color: #f9e2af;")
        _ts_layout.addWidget(self.tool_status_label, 1)

        self.tool_install_user_btn = QPushButton("Install for User")
        self.tool_install_user_btn.setObjectName("secondary")
        self.tool_install_user_btn.setFixedHeight(26)
        self.tool_install_user_btn.setFocusPolicy(Qt.NoFocus)
        self.tool_install_user_btn.setDefault(False)
        self.tool_install_user_btn.setAutoDefault(False)
        self.tool_install_user_btn.setVisible(False)
        self.tool_install_user_btn.clicked.connect(
            lambda: self._install_tool("user"))
        _ts_layout.addWidget(self.tool_install_user_btn)

        self.tool_install_system_btn = QPushButton("Install for System 🔒")
        self.tool_install_system_btn.setObjectName("secondary")
        self.tool_install_system_btn.setFixedHeight(26)
        self.tool_install_system_btn.setFocusPolicy(Qt.NoFocus)
        self.tool_install_system_btn.setDefault(False)
        self.tool_install_system_btn.setAutoDefault(False)
        self.tool_install_system_btn.setVisible(False)
        self.tool_install_system_btn.setToolTip(
            "Install system-wide — requires Administrator privileges")
        self.tool_install_system_btn.clicked.connect(
            lambda: self._install_tool("system"))
        _ts_layout.addWidget(self.tool_install_system_btn)

        self.tool_status_widget.setVisible(False)
        left.addWidget(self.tool_status_widget)
        # ─────────────────────────────────────────────────────────────────

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

        body.addLayout(left, stretch=3)

        # RIGHT: terminal (always visible, never causes resize)
        right_group = QGroupBox("Progress")
        right_inner = QVBoxLayout()
        right_inner.setSpacing(8)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #585b70; font-size: 14px; font-weight: bold; padding: 2px 0;")
        right_inner.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        right_inner.addWidget(self.progress_bar)

        # Progress message label (above hints)
        self.progress_msg_label = QLabel("")
        self.progress_msg_label.setWordWrap(True)
        self.progress_msg_label.setStyleSheet(
            "color: #89b4fa; font-size: 16px; font-weight: bold; padding: 3px 4px;"
        )
        self.progress_msg_label.setVisible(False)
        right_inner.addWidget(self.progress_msg_label)

        # Hints panel — rich HTML, stays visible always
        self.cmd_label = QTextEdit()
        self.cmd_label.setReadOnly(True)
        self.cmd_label.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244; "
            "border-radius: 8px; padding: 4px; color: #cdd6f4; "
            "font-family: Consolas, monospace; font-size: 15px;"
        )
        self.cmd_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cmd_label.setHtml(
            "<p style='color:#585b70;font-size:12px;padding:8px;'>"
            "💡 Select an environment type to see terminal commands.</p>"
        )
        right_inner.addWidget(self.cmd_label, stretch=1)

        right_group.setLayout(right_inner)
        right_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(right_group, stretch=7)

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

        # Render the command card for the DEFAULT type immediately.
        # currentIndexChanged never fires for the initial selection, so the
        # panel used to sit on the placeholder until the user changed type.
        self._on_env_type_changed(self.env_type_combo.currentIndex())

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

        # ── Tool status note (uv / poetry / pipx only) ───────────────────
        _tool_types = ("uv", "poetry", "pipx")
        _show_tool_row = env_type in _tool_types
        if hasattr(self, "tool_status_widget"):
            self.tool_status_widget.setVisible(_show_tool_row)
        if _show_tool_row:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self._refresh_tool_path_ui(env_type))
        # ─────────────────────────────────────────────────────────────────

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

        # Progress panel hints — rich HTML with syntax colors
        # Example commands use the ACTUAL name typed by the user (falls
        # back to 'myproject' while the field is empty).
        _name = "myproject"
        if hasattr(self, "name_input"):
            _name = self.name_input.text().strip() or "myproject"
        def _cmd(t): return f"<span style='color:#89b4fa;font-family:Consolas,monospace;font-size:15px;'>{t}</span>"
        def _path(t): return f"<span style='color:#a6e3a1;font-family:Consolas,monospace;font-size:15px;'>{t}</span>"
        def _kw(t): return f"<span style='color:#cba6f7;font-family:Consolas,monospace;font-weight:bold;font-size:15px;'>{t}</span>"
        def _ver(t): return f"<span style='color:#f9e2af;font-family:Consolas,monospace;font-size:15px;'>{t}</span>"
        def _title(icon, text, color='#cdd6f4'): return f"<p style='font-size:20px;font-weight:bold;color:{color};margin:10px 0 6px 0;letter-spacing:0.5px;'>{icon}&nbsp; {text}</p>"
        def _line(t): return f"<p style='margin:4px 0;font-size:15px;font-family:Consolas,monospace;color:#cdd6f4;background:#11111b;padding:4px 10px;border-radius:4px;'>{t}</p>"
        def _note(t): return f"<p style='margin:10px 0 2px 0;font-size:12px;color:#6c7086;font-style:italic;'>{t}</p>"
        hints = {
            "venv": (
                _title("🐍", "Python venv", "#89b4fa") +
                _note("Standard library virtual environment") +
                _line(_kw("python") + " -m " + _cmd("venv") + " " + _path(_name)) +
                _note("Activate — Linux/macOS:") +
                _line(_cmd("source") + " " + _path(_name + "/bin/activate")) +
                _note("Activate — Windows:") +
                _line(_path(_name + "\\Scripts\\activate")) +
                _note("Install packages:") +
                _line(_cmd("pip") + " install " + _kw("numpy") + " " + _kw("pandas")) +
                _note("Deactivate:") +
                _line(_cmd("deactivate"))
            ),
            "uv": (
                _title("⚡", "uv — Ultra Fast", "#f9e2af") +
                _note("10-100x faster than pip. Rust-powered.") +
                _line(_cmd("uv") + " venv " + _path(_name)) +
                _note("With specific Python version:") +
                _line(_cmd("uv") + " venv --python " + _ver("3.12") + " " + _path(_name)) +
                _note("Install packages:") +
                _line(_cmd("uv") + " pip install " + _kw("numpy") + " " + _kw("pandas")) +
                _note("Run without activating:") +
                _line(_cmd("uv") + " run " + _kw("python") + " script.py")
            ),
            "poetry": (
                _title("📜", "Poetry", "#cba6f7") +
                _note("Dependency management + virtual environments") +
                _line(_cmd("pip") + " install " + _kw("poetry")) +
                _note("Create new project:") +
                _line(_cmd("poetry") + " new " + _path(_name)) +
                _line(_cmd("cd") + " " + _path(_name) + " &amp;&amp; " + _cmd("poetry") + " install") +
                _note("Add dependencies:") +
                _line(_cmd("poetry") + " add " + _kw("numpy") + " " + _kw("pandas")) +
                _note("Run scripts:") +
                _line(_cmd("poetry") + " run " + _kw("python") + " script.py")
            ),
            "pipx": (
                _title("📦", "pipx", "#a6e3a1") +
                _note("Install Python CLI apps in isolated environments") +
                _line(_cmd("pip") + " install --user " + _kw("pipx")) +
                _line(_cmd("pipx") + " ensurepath") +
                _note("Install a CLI tool globally:") +
                _line(_cmd("pipx") + " install " + _kw("black")) +
                _note("List installed apps:") +
                _line(_cmd("pipx") + " list") +
                _note("Run without installing:") +
                _line(_cmd("pipx") + " run " + _kw("cowsay") + " Hello!")
            ),
            "conda": (
                _title("🦎", "Conda (micromamba)", "#89dceb") +
                _note("conda-forge — 25,000+ packages incl. R, RStudio") +
                _line(_cmd("micromamba") + " create -n " + _path(_name) + " python=" + _ver("3.12")) +
                _note("Activate:") +
                _line(_cmd("micromamba") + " activate " + _path(_name)) +
                _note("Install packages:") +
                _line(_cmd("micromamba") + " install -c conda-forge " + _kw("numpy") + " " + _kw("r-base")) +
                _note("List environments:") +
                _line(_cmd("micromamba") + " env list")
            ),
        }
        self.cmd_label.setHtml(hints.get(env_type, hints["venv"]))

    def _on_python_changed(self, index):
        """Seçili Python'un tam yolunu göster."""
        import shutil, sys
        data = self.python_combo.currentData()
        if data:
            self.python_path_label.setText(f"📍 {data}")
        else:
            py = shutil.which("python") or shutil.which("python3") or sys.executable
            self.python_path_label.setText(f"📍 {py}")

    def _refresh_tool_path_ui(self, env_type: str):
        """Check if tool is available and update status note."""
        if not hasattr(self, "tool_status_label"):
            return
        found = self._find_tool_exe(env_type)
        # Auto-register if found via extended search
        if found:
            try:
                from src.core.tool_registry import ToolRegistry
                ToolRegistry().register(env_type, found, installed_by="system")
            except Exception:
                pass
        if found:
            self.tool_status_label.setText(f"✅ {env_type} found")
            self.tool_status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
            if hasattr(self, "tool_install_user_btn"):
                self.tool_install_user_btn.setVisible(False)
            if hasattr(self, "tool_install_system_btn"):
                self.tool_install_system_btn.setVisible(False)
        else:
            self.tool_status_label.setText(f"⚠️ {env_type} not found")
            self.tool_status_label.setStyleSheet("font-size: 11px; color: #f9e2af;")
            if hasattr(self, "tool_install_user_btn"):
                self.tool_install_user_btn.setText(f"Install {env_type} (User)")
                self.tool_install_user_btn.setVisible(True)
            if hasattr(self, "tool_install_system_btn"):
                self.tool_install_system_btn.setText(f"Install {env_type} (System 🔒)")
                self.tool_install_system_btn.setVisible(True)

