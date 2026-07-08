"""VenvStudio - Package Panel: Launcher UI Mixin
Launcher tab construction and card rendering (moved from package_panel.py):
_create_launcher_tab, _create_app_card, _update_launcher_status, _update_quick_sidebar.
"""
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.utils.constants import LAUNCHER_TOOLTIPS


class LauncherUIMixin:
    """Mixin for PackagePanel: Launcher tab UI construction."""

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

