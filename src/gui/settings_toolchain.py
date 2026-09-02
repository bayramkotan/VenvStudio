"""VenvStudio - Settings: ToolchainMixin"""
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QFontComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QDialog, QDialogButtonBox,
    QProgressBar, QListWidget, QListWidgetItem, QTextEdit,
)

_log = logging.getLogger("venvstudio.gui.toolchain")
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor
from src.utils.platform_utils import find_system_pythons, get_platform, subprocess_args
from src.utils.platform_utils import bold_font_from as _bold_font_from
from src.utils.constants import APP_NAME, APP_VERSION
from src.utils.i18n import tr
import os, sys, subprocess, shutil
from pathlib import Path

from .settings_common import NoScrollComboBox


class ToolchainMixin:
    """Mixin for SettingsPage."""
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
        # N64: the "Install (System)" button is gone. It is kept as a hidden
        # placeholder only so _pm_check_tool's signature and every caller
        # stay untouched; nothing ever shows it. See _pm_install_tool for
        # why system-scope installs were dropped altogether.
        sys_btn = QPushButton("")
        sys_btn.setVisible(False)
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
            sys_btn.setVisible(False)   # N64: user scope only

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

            def _detect_pm():
                for pm in ("apt", "pacman", "dnf", "zypper"):
                    if shutil.which(pm): return pm
                return None

            def _is_ext_managed():
                try:
                    import sysconfig
                    stdlib = sysconfig.get_path("stdlib")
                    return bool(stdlib and os.path.exists(os.path.join(stdlib, "EXTERNALLY-MANAGED")))
                except Exception: return False

            # N64 (2026-08-23): system-scope installs are gone entirely.
            #
            # Supporting them meant elevation, and elevation from a desktop
            # app is where this feature kept breaking: ShellExecuteW returned
            # before pip had finished, so failures read as successes; plain
            # `sudo` asked for a password on a TTY that does not exist and hung
            # until the timeout; pkexec is missing on plenty of systems; and a
            # writability check meant to INFORM the user ended up demanding
            # admin rights for a USER install. A per-user install needs no
            # rights at all, works everywhere, and wins on PATH anyway.
            #
            # Tools already installed system-wide are still listed -- their
            # rows simply carry no action buttons (see _tc_update_row_btns).
            if sys.platform != "win32" and _is_ext_managed():
                # PEP 668 system — strategy depends on scope
                pm = _detect_pm()
                if True:   # user scope is the only scope now
                    # USER install — never use sudo/pkexec, just pip --user or official installer
                    if tool == "uv":
                        r = subprocess.run([sys.executable, "-m", "pip", "install", "uv",
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0:
                            r = subprocess.run(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                                               capture_output=True, text=True, timeout=120)
                            if r.returncode != 0: return False, r.stderr[:200]
                    elif tool == "pixi":
                        # Pixi: always use official installer, never pip
                        # First: remove pip-installed fake pixi if present
                        import shutil as _sh2, subprocess as _sp2
                        _pip_pixi = None
                        try:
                            import importlib.util
                            if importlib.util.find_spec("pixi") is not None:
                                _pip_pixi = True
                        except Exception:
                            pass
                        if _pip_pixi:
                            # Try to remove pip pixi (may need admin on Windows)
                            _sp2.run(
                                [sys.executable, "-m", "pip", "uninstall", "pixi", "-y"],
                                capture_output=True, text=True, timeout=60)
                        if sys.platform == "win32":
                            _winget = _sh2.which("winget")
                            if _winget:
                                r = subprocess.run([_winget, "install", "prefix-dev.pixi",
                                                    "--accept-package-agreements",
                                                    "--accept-source-agreements"],
                                                   capture_output=True, text=True, timeout=300)
                                if r.returncode != 0:
                                    # Fallback: PowerShell installer
                                    r = subprocess.run(
                                        ["powershell", "-NoProfile", "-Command",
                                         "iwr -useb https://pixi.sh/install.ps1 | iex"],
                                        capture_output=True, text=True, timeout=300)
                            else:
                                r = subprocess.run(
                                    ["powershell", "-NoProfile", "-Command",
                                     "iwr -useb https://pixi.sh/install.ps1 | iex"],
                                    capture_output=True, text=True, timeout=300)
                            if r.returncode != 0: return False, r.stderr[:300]
                        else:
                            r = subprocess.run(
                                ["sh", "-c", "curl -fsSL https://pixi.sh/install.sh | bash"],
                                capture_output=True, text=True, timeout=300)
                            if r.returncode != 0: return False, r.stderr[:300]
                    elif tool == "poetry":
                        _pipx = shutil.which("pipx")
                        _done_poetry = False
                        if _pipx:
                            r = subprocess.run([_pipx, "install", "poetry"],
                                               capture_output=True, text=True, timeout=180)
                            _done_poetry = r.returncode == 0
                        if not _done_poetry:
                            r = subprocess.run(["sh", "-c", "curl -sSL https://install.python-poetry.org | python3 -"],
                                               capture_output=True, text=True, timeout=180,
                                               env={**os.environ, "POETRY_HOME": os.path.expanduser("~/.local/share/pypoetry")})
                            if r.returncode != 0: return False, r.stderr[:200]
                    elif tool == "pipx":
                        r = subprocess.run([sys.executable, "-m", "pip", "install", "pipx",
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0: return False, r.stderr[:200]
                    else:
                        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0: return False, r.stderr[:200]
            else:
                r = subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--user", "-q"],
                                   **subprocess_args(capture_output=True, text=True, timeout=120))
                if r.returncode != 0: return False, (r.stderr or "failed")[:200]
            if tool == "pipx":
                try: subprocess.run([sys.executable, "-m", "pipx", "ensurepath"], **subprocess_args(capture_output=True, timeout=30))
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
                btn.setText(f"Install {tool} (User)")
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self)
        w.finished.connect(_done)
        w.start()
        self._pm_worker = w

    def _pm_uninstall_tool(self, tool, pkg, status_label, btn):
        import sys, subprocess, shutil, os
        btn.setEnabled(False)
        status_label.setText(f"⏳ Removing {tool}...")
        status_label.setStyleSheet("font-size: 11px; color: #89b4fa;")

        def _do_remove():
            # uv: prefer self-uninstall or delete binary
            if tool == "uv":
                _uv = shutil.which("uv")
                if _uv and os.path.isfile(_uv):
                    # curl-installed uv → delete binary
                    _local_bins = [
                        os.path.join(os.path.expanduser("~"), ".local", "bin", "uv"),
                        os.path.join(os.path.expanduser("~"), ".cargo", "bin", "uv"),
                    ]
                    if any(_uv == p for p in _local_bins):
                        try:
                            os.remove(_uv)
                            return True
                        except Exception:
                            pass
                # fallback: pip uninstall --break-system-packages
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q",
                     "--break-system-packages"],
                    **subprocess_args(capture_output=True, text=True, timeout=60))
                return r.returncode == 0

            # poetry: use official uninstaller if available
            if tool == "poetry":
                _poetry_uninstall = os.path.join(
                    os.path.expanduser("~"), ".local", "share", "pypoetry",
                    "venv", "bin", "poetry")
                if os.path.exists(_poetry_uninstall):
                    r = subprocess.run(
                        ["python3", "-", "--uninstall"],
                        input=subprocess.run(
                            ["curl", "-sSL", "https://install.python-poetry.org"],
                            capture_output=True, timeout=30).stdout,
                        capture_output=True, text=True, timeout=60)
                    if r.returncode == 0:
                        return True
                # fallback: pip uninstall
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q",
                     "--break-system-packages"],
                    **subprocess_args(capture_output=True, text=True, timeout=60))
                return r.returncode == 0

            # pixi: remove ~/.pixi directory + pip-installed fake if present
            if tool == "pixi":
                import shutil as _sh
                # Remove pip-installed fake pixi
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "pixi", "-y"],
                        capture_output=True, text=True, timeout=60)
                except Exception:
                    pass
                # Remove ~/.pixi (official install location)
                _pixi_home = os.path.expanduser("~/.pixi")
                if not os.path.exists(_pixi_home):
                    _pixi_home = os.path.join(os.environ.get("LOCALAPPDATA", ""), ".pixi")
                if os.path.exists(_pixi_home):
                    try:
                        _sh.rmtree(_pixi_home)
                    except Exception as e:
                        return False
                return True

            # Default: pip uninstall with --break-system-packages fallback
            r = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q"],
                **subprocess_args(capture_output=True, text=True, timeout=60))
            if r.returncode != 0 and "externally-managed" in (r.stderr or r.stdout):
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q",
                     "--break-system-packages"],
                    **subprocess_args(capture_output=True, text=True, timeout=60))
            return r.returncode == 0

        success = _do_remove()
        if success:
            status_label.setText("❌ Not installed")
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
            try:
                from src.core.tool_registry import ToolRegistry
                ToolRegistry().remove(tool)
            except Exception:
                pass
        else:
            status_label.setText(f"❌ Remove failed")
            status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
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
        w = WorkerThread(_do, parent=self)
        w.finished.connect(_done)
        w.start()
        self._pm_worker = w


    # ════════════════════════════════════════════════════════
    # TOOLCHAIN MANAGER
    # Per-Python: pip | venv | uv | poetry | pipx | conda
    # ════════════════════════════════════════════════════════

    # Order matters and is deliberate (Bayram, 2026-08-27): the three that come
    # with Python or underpin everything else go first, in the order you meet
    # them -- pip, venv, then Conda -- and the standalone managers follow
    # alphabetically so a growing list stays predictable to scan.
    #
    # Row index is the link between this list, the cached rows and the table
    # widget, so reordering here reorders all three. The cache stores a
    # fingerprint of these IDs and drops itself when they change, so an old
    # cache cannot paint yesterday's order over today's rows.
    # N79 (Bayram, 2026-08-28): where to read about each tool.
    #
    # His words: "kullanici hatch, uv... nedir diye aramasin". The panel names
    # nine tools and says nothing about what any of them is for, so anyone
    # meeting hatch or pdm for the first time has to leave and search.
    #
    # Right-click rather than a column: the table already has five columns and
    # a name cell is a QTableWidgetItem, which cannot hold a button. This costs
    # no width and no layout change.
    #
    # venv gets one entry only -- it is part of the standard library, so there
    # is no project site and no separate repository, and an empty "GitHub" row
    # would be worse than its absence. The conda row points at mamba because
    # that is what VenvStudio actually runs (v1.6.57 onwards); sending someone
    # to Anaconda would describe a different program from the one installed.
    _TC_LINKS = {
        "pip": [
            ("\U0001f310 pip.pypa.io", "https://pip.pypa.io"),
            ("\U0001f4d6 Documentation", "https://pip.pypa.io/en/stable/"),
            ("\U0001f419 GitHub", "https://github.com/pypa/pip"),
        ],
        "venv": [
            ("\U0001f4d6 Python docs \u2014 venv",
             "https://docs.python.org/3/library/venv.html"),
        ],
        "micromamba": [
            ("\U0001f310 mamba.readthedocs.io", "https://mamba.readthedocs.io"),
            ("\U0001f4d6 micromamba guide",
             "https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html"),
            ("\U0001f419 GitHub", "https://github.com/mamba-org/mamba"),
        ],
        "hatch": [
            ("\U0001f310 hatch.pypa.io", "https://hatch.pypa.io"),
            ("\U0001f4d6 Documentation", "https://hatch.pypa.io/latest/"),
            ("\U0001f419 GitHub", "https://github.com/pypa/hatch"),
        ],
        "pdm": [
            ("\U0001f310 pdm-project.org", "https://pdm-project.org"),
            ("\U0001f4d6 Documentation", "https://pdm-project.org/latest/"),
            ("\U0001f419 GitHub", "https://github.com/pdm-project/pdm"),
        ],
        "pipx": [
            ("\U0001f310 pipx.pypa.io", "https://pipx.pypa.io"),
            ("\U0001f4d6 Documentation", "https://pipx.pypa.io/stable/"),
            ("\U0001f419 GitHub", "https://github.com/pypa/pipx"),
        ],
        "pixi": [
            ("\U0001f310 pixi.sh", "https://pixi.sh"),
            ("\U0001f4d6 Documentation", "https://pixi.sh/latest/"),
            ("\U0001f419 GitHub", "https://github.com/prefix-dev/pixi"),
        ],
        "poetry": [
            ("\U0001f310 python-poetry.org", "https://python-poetry.org"),
            ("\U0001f4d6 Documentation", "https://python-poetry.org/docs/"),
            ("\U0001f419 GitHub", "https://github.com/python-poetry/poetry"),
        ],
        "uv": [
            ("\U0001f310 docs.astral.sh/uv", "https://docs.astral.sh/uv/"),
            ("\U0001f4d6 Getting started",
             "https://docs.astral.sh/uv/getting-started/"),
            ("\U0001f419 GitHub", "https://github.com/astral-sh/uv"),
        ],
    }

    _TC_TOOLS = [
        # (id,          pip_pkg,   label,    icon)
        ("pip",         "pip",     "pip",    "📦"),
        ("venv",        None,      "venv",   "🐍"),
        ("micromamba",  None,      "Conda",  "🦎"),
        ("hatch",       "hatch",   "Hatch",  "🏗️"),
        ("pdm",         "pdm",     "PDM",    "📦"),
        ("pipx",        "pipx",    "pipx",   "📦"),
        ("pixi",        None,      "Pixi",   "🌊"),  # pixi uses its own installer
        ("poetry",      "poetry",  "Poetry", "📜"),
        ("uv",          "uv",      "uv",     "⚡"),
    ]

    # N65 (Bayram, 2026-08-27): toolchain jobs run ONE AT A TIME.
    #
    # Clicking Install on several rows in a row started several workers at
    # once, and Windows does not take kindly to it. From his log:
    #     09:51:56  pip install pipx   (starts)
    #     09:51:57  pip install poetry (starts -- while pipx is still writing)
    #     09:52:09  pip install poetry -> PermissionError [WinError 5]
    #     09:52:30  pip install poetry -> exit=0        (same command!)
    #     09:52:41  pixi self-update   -> WinError 32, file in use
    # Two pip processes writing the same site-packages, and pixi rewriting its
    # own exe while another job held it open. The same command failing and then
    # succeeding twenty seconds later is the signature of a race, not a bug in
    # the command.
    #
    # A queue would be nicer, but these are user-initiated actions taking a few
    # seconds each: telling the user to wait is honest and cannot itself go
    # wrong. The flag is cleared in a `finally` so a crashing job cannot wedge
    # the panel shut.
    def _tc_show_links_menu(self, table, pos):
        """Right-click a toolchain row for that tool's own documentation.

        N79: the panel lists nine tools and explains none of them. Someone
        meeting pdm or pixi here has no way from this table to what they are,
        short of leaving and searching.
        """
        from PySide6.QtWidgets import QMenu
        item = table.itemAt(pos)
        if item is None:
            return
        _row = item.row()
        _id_item = table.item(_row, 0)
        _tid = (_id_item.data(Qt.UserRole) if _id_item else "") or ""
        _links = self._TC_LINKS.get(_tid) or []
        if not _links:
            return

        _label = (_id_item.text() if _id_item else _tid).strip()
        menu = QMenu(self)
        _title = menu.addAction(f"About {_label}")
        _title.setEnabled(False)
        menu.addSeparator()
        for _text, _url in _links:
            _act = menu.addAction(_text)
            _act.setToolTip(_url)
            _act.triggered.connect(
                lambda checked=False, u=_url: self._tc_open_url(u))
        menu.exec(table.viewport().mapToGlobal(pos))

    @staticmethod
    def _tc_open_url(url: str):
        """Open a documentation link in the browser."""
        try:
            from src.utils.platform_utils import open_url
            open_url(url)
        except Exception:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                _log.warning(f"[TC] could not open {url}")

    @staticmethod
    def _tc_env_root(py_exe: str) -> str:
        """The <env> directory if py_exe belongs to one, otherwise "".

        N68 (2026-08-27): two things need this answer and they must agree --
        the location column (a tool inside the selected env is labelled Env,
        not User) and the installer (`--user` is rejected inside a virtualenv).
        One helper, so they cannot drift apart the way every other duplicated
        rule in this file has.
        """
        import os as _o
        try:
            _d1 = _o.path.dirname(py_exe)      # <env>/bin | <env>\Scripts
            _d2 = _o.path.dirname(_d1)         # <env>
            for _root in (_d2, _d1):
                if _root and (_o.path.isfile(_o.path.join(_root, "pyvenv.cfg"))
                              or _o.path.isdir(_o.path.join(_root, "conda-meta"))):
                    return _root
        except Exception:
            pass
        return ""

    def _tc_pick_copy(self, tool, py_exe, action):
        """Which copy of `tool` should `action` touch?

        N69 (Bayram, 2026-08-27): when a tool exists BOTH inside the selected
        environment and outside it, ask.

        I argued against this at first -- picking the env in the dropdown looked
        like answer enough, and we had just deleted a "User or System?" prompt.
        That was the wrong read. The removed prompt offered a choice where only
        one option ever worked; this one offers two copies that both really
        exist and are both really manageable. Guessing silently would leave the
        user unable to reach one of them at all.

        Returns (path, interpreter) for the chosen copy, or (None, None) if the
        user cancelled. When only one copy exists it returns straight away
        without troubling anyone.
        """
        import os, sys, shutil
        from PySide6.QtWidgets import QMessageBox

        _env_root = self._tc_env_root(py_exe)
        _here = self._tc_find_tool(tool, py_exe)
        if not _env_root or not _here:
            return _here, py_exe

        _outside = []
        for _c in (shutil.which(tool), shutil.which(tool + ".exe")):
            if not _c or os.path.normcase(_c).startswith(os.path.normcase(_env_root)):
                continue
            if _c not in _outside:
                _outside.append(_c)
        if not _outside:
            return _here, py_exe

        _other = _outside[0]
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        # Name the two scopes the way the rest of the application does --
        # Environment / User (or System) -- rather than "this one" and "the
        # other one", which says nothing about what is being chosen.
        _out_scope = ("System" if not self._tc_dir_is_writable(_other)
                      else "User")
        _env_name = os.path.basename(_env_root.rstrip("/\\")) or "environment"
        box.setWindowTitle(f"{tool}: two installations")
        box.setText(f"{tool} is installed in two scopes. Which installation "
                    f"should VenvStudio {action}?")
        box.setInformativeText(
            f"Environment \u2014 {_env_name}:\n{_here}\n\n"
            f"{_out_scope}-wide:\n{_other}")
        _b_env = box.addButton(f"Environment ({_env_name})",
                               QMessageBox.AcceptRole)
        _b_out = box.addButton(f"{_out_scope}-wide", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(_b_env)
        box.exec()

        if box.clickedButton() is _b_env:
            return _here, py_exe
        if box.clickedButton() is _b_out:
            # The other copy belongs to whichever interpreter owns its scripts
            # directory; find it among the entries already in the dropdown so we
            # never invent a path. Falling back to the running interpreter is
            # good enough for pip, which only needs to reach the same site.
            _owner = ""
            try:
                _dir = os.path.normcase(os.path.dirname(_other))
                for i in range(self._tc_py_combo.count()):
                    _cand = self._tc_py_combo.itemData(i) or ""
                    if not _cand or self._tc_env_root(_cand):
                        continue
                    _tag = self._tc_py_ver_tag(_cand)
                    _user = os.path.join(os.environ.get("APPDATA", ""), "Python",
                                         f"Python{_tag}", "Scripts") if _tag else ""
                    if (_dir.startswith(os.path.normcase(os.path.dirname(_cand)))
                            or (_user and _dir.startswith(os.path.normcase(_user)))):
                        _owner = _cand
                        break
            except Exception:
                _owner = ""
            return _other, (_owner or sys.executable)
        return None, None

    def _tc_begin_job(self, what: str = "operation") -> bool:
        """True if this job may start; otherwise warn and return False."""
        from PySide6.QtWidgets import QMessageBox
        if getattr(self, "_tc_job_running", False):
            QMessageBox.information(
                None, "One at a Time",
                f"Another toolchain {self._tc_job_name} is still running.\n\n"
                f"Wait for it to finish before starting the {what}. Running two "
                f"at once makes them fight over the same files.")
            return False
        self._tc_job_running = True
        self._tc_job_name = what
        return True

    def _tc_end_job(self):
        self._tc_job_running = False

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
            "uv / poetry / pipx: installed per-user, no admin needed\n"
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
        refresh_btn.setToolTip(
            "Rescan Pythons, environments and tool status")

        def _tc_refresh_all():
            # N68: rescan the SELECTOR too, not just the table.
            # Refresh used to reload tool status only, so an environment
            # created a minute earlier stayed missing from the dropdown
            # until the whole app was restarted -- Bayram hit exactly that
            # with a new env called "dl". _tc_scan_pythons ends by loading
            # the table for the current selection, so this covers both.
            if not self._tc_py_cb.isChecked():
                return
            _keep = self._tc_py_combo.currentData() or ""
            self._tc_scan_pythons()
            self._tc_load_table(
                self._tc_py_combo.currentData() or _keep, force=True)

        refresh_btn.clicked.connect(_tc_refresh_all)
        note_row.addWidget(refresh_btn)
        vl.addLayout(note_row)

        # ── Tool table ───────────────────────────────────────────────────
        tbl = QTableWidget(len(self._TC_TOOLS), 5)
        tbl.setHorizontalHeaderLabels(["Tool", "Status", "Version", "Path", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        # Actions column: give it a guaranteed width instead of
        # ResizeToContents. With Path on Stretch, Qt satisfies the stretching
        # column first and squeezes the content-sized one when the table is
        # narrower than the sum of both -- which clipped the Conda row, the
        # widest cell here (label + backend combo + THREE buttons, where
        # every other row has at most two). Sized from the same constants the
        # cell is built from: 3 buttons x 110 + combo 200 + label ~60 +
        # spacing/margins ~30. Path elides, so it is the right one to give way
        # on a narrow window. (Bayram, 2026-08-19: "yazilar bile okunmuyor")
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        tbl.setColumnWidth(4, 3 * 120 + 220 + 70 + 30)
        tbl.horizontalHeader().setMinimumSectionSize(60)
        # N12: long paths (e.g. C:\Program Files\Python314\Scripts\uv.EXE)
        # overflowed the Path column instead of being readable. Elide in the
        # middle so both the drive/leading folder and the filename stay
        # visible; the full path is still available via the tooltip set on
        # each Path cell below.
        tbl.setTextElideMode(Qt.ElideMiddle)
        tbl.setWordWrap(False)
        tbl.setMinimumWidth(720)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionMode(QAbstractItemView.NoSelection)
        tbl.setShowGrid(False)
        tbl.setAlternatingRowColors(True)
        tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        tbl.customContextMenuRequested.connect(
            lambda pos, _t=tbl: self._tc_show_links_menu(_t, pos))
        tbl.setStyleSheet(
            f"QTableWidget {{ font-size: {self._c()['fs_base']}px; }}"
            f"QTableWidget::item {{ padding: 4px 8px; }}"
        )
        for row, (tid, pkg, lbl, icon) in enumerate(self._TC_TOOLS):
            tbl.setRowHeight(row, 42)
            name = QTableWidgetItem(f"{icon}  {lbl}")
            # N88: the table's size comes from a stylesheet in PIXELS four
            # lines above, so tbl.font().pointSize() is -1 and a plain
            # copy carries that unset marker into every cell.
            name.setFont(_bold_font_from(tbl, QFont.Medium))
            # N79: the row remembers which tool it is, so the context
            # menu can find its links without re-deriving them from the
            # visible label (which is "Conda" for micromamba).
            name.setData(Qt.UserRole, tid)
            if self._TC_LINKS.get(tid):
                name.setToolTip(f"Right-click for {lbl} documentation")
            tbl.setItem(row, 0, name)
            for col in (1, 2, 3):
                ph = QTableWidgetItem("—")
                ph.setForeground(QColor(self._c()["fg_muted"]))
                tbl.setItem(row, col, ph)
            tbl.setCellWidget(row, 4, self._tc_row_btns(tid, pkg, tbl, row))
        self._tc_table = tbl
        # Size table to show all rows without scrolling
        row_h = 44
        header_h = 28
        total_h = len(self._TC_TOOLS) * row_h + header_h + 4
        tbl.setMinimumHeight(total_h)
        tbl.setMaximumHeight(total_h + 20)
        from PySide6.QtCore import Qt
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vl.addWidget(tbl)

        layout.addWidget(grp)

        # Populate combo from python_table, then auto-load
        # Auto-refresh (same as clicking the Refresh button) whenever the
        # selected Python changes -- no manual click needed. The combo is
        # disabled while the checkbox is off, so it can't receive a
        # user-driven change in that state anyway; this just makes the
        # "changing Python reloads the table" behaviour unconditional and
        # explicit rather than depending on the checkbox flag.
        self._tc_py_combo.currentIndexChanged.connect(
            lambda: self._tc_load_table(self._tc_py_combo.currentData() or ""))
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
        hl.setContentsMargins(4, 3, 4, 3)
        hl.setSpacing(4)

        def _b(text, tip="", danger=False, name=""):
            b = QPushButton(text)
            b.setMinimumHeight(30)
            b.setMinimumWidth(120)
            b.setObjectName("danger" if danger else "secondary")
            b.setToolTip(tip)
            b.setAccessibleName(name)
            b.setFocusPolicy(Qt.NoFocus)
            b.setDefault(False); b.setAutoDefault(False)
            return b

        def _ask_scope(parent_btn, cb_user, cb_system):
            """Install straight away -- there is only one scope now.

            N64 (2026-08-25): this popped a menu offering "User (no admin)"
            or "System (admin/sudo)". The system half is gone from every
            install path in this file, so the menu was offering a choice
            that no longer exists -- and asking the user to make it before
            every single install. One option is not a choice; just do it.
            `cb_system` is still accepted so no caller has to change.
            """
            cb_user()

        if tool == "micromamba":
            # ── Conda Backend selector ────────────────────────────────────
            from PySide6.QtWidgets import QComboBox as _CB2, QLabel as _LB2
            _backend_label = _LB2("Backend:")
            _backend_label.setStyleSheet(
                f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg_muted']};"
            )
            hl.addWidget(_backend_label)

            _backend_combo = _CB2()
            # setFixedHeight(26) squashed the combo below what the font needs,
            # so the glyphs were clipped along the bottom and "mamba" was
            # unreadable -- the row itself is 38px and the neighbouring
            # buttons only set a MINIMUM height, so they were free to grow
            # while the combo was not. Match them. (Bayram, 2026-08-19:
            # "su yazilar bi okunakli olsun")
            _backend_combo.setMinimumHeight(30)
            _backend_combo.setMinimumWidth(220)
            _backend_combo.setToolTip(
                "Which conda-compatible binary VenvStudio uses for creating and\n"
                "managing conda environments.\n\n"
                "  Auto          — bundled micromamba, then system micromamba\n"
                "  micromamba (bundled) — VenvStudio's own download\n"
                "  micromamba (system)  — system PATH only\n"
                "  mamba         — system mamba (faster solver)\n"
                "  conda         — system conda / Anaconda\n"
                "  miniforge     — miniforge / mambaforge installation\n"
                "  Custom path…  — browse to any compatible binary"
            )
            _BACKENDS = [
                ("auto",               "Auto (default)"),
                ("micromamba_bundled", "micromamba (bundled)"),
                ("micromamba_system",  "micromamba (system)"),
                ("mamba",              "mamba"),
                ("conda",              "conda"),
                ("miniforge",          "miniforge / mambaforge"),
                ("custom",             "Custom path…"),
            ]
            for _bid, _blbl in _BACKENDS:
                _backend_combo.addItem(_blbl, _bid)

            # Load saved value
            try:
                _saved_backend = self.config.get("conda_backend", "auto") or "auto"
                _idx = _backend_combo.findData(_saved_backend)
                if _idx >= 0:
                    _backend_combo.setCurrentIndex(_idx)
            except Exception:
                pass

            def _on_backend_changed(_i):
                _bid = _backend_combo.currentData()
                try:
                    self.config.set("conda_backend", _bid)
                    self.config.save()
                except Exception:
                    pass
                if _bid == "custom":
                    _pick_custom_path()

            def _pick_custom_path():
                from PySide6.QtWidgets import QFileDialog as _QFD
                _path, _ = _QFD.getOpenFileName(
                    self, "Select conda binary",
                    str(Path.home()),
                    "Executables (*.exe *.bat *);;All Files (*)" if sys.platform == "win32"
                    else "All Files (*)"
                )
                if _path and os.path.isfile(_path):
                    try:
                        self.config.set("conda_backend_custom_path", _path)
                        self.config.save()
                    except Exception:
                        pass

            _backend_combo.currentIndexChanged.connect(_on_backend_changed)
            hl.addWidget(_backend_combo)

            # ── Download/Upgrade/Remove buttons ──────────────────────────
            install_btn = _b("⬇ Install", "Download micromamba binary", name="install_user")
            install_btn.setVisible(True)
            upgrade_btn = _b("⬆ Upgrade", "Re-download micromamba",     name="upgrade_user")
            upgrade_btn.setVisible(False)
            remove_btn  = _b("🗑 Remove",  "Remove micromamba binary",   True, name="rm_user")
            remove_btn.setVisible(False)
            hl.addWidget(install_btn)
            hl.addWidget(upgrade_btn)
            hl.addWidget(remove_btn)
            install_btn.clicked.connect(lambda: self._tc_download_mamba(tbl, row))
            upgrade_btn.clicked.connect(lambda: self._tc_download_mamba(tbl, row))
            remove_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row:
                self._tc_do_remove(t, p, "user", tb, r))
        elif tool == "pixi":
            # Pixi: always user-local (~/.pixi/bin) — no scope popup like Conda
            install_btn = _b("⬇ Install", "Install Pixi (official installer)", name="install_user")
            upgrade_btn = _b("⬆ Upgrade", "Update Pixi (pixi self-update)",    name="upgrade_user")
            remove_btn  = _b("🗑 Remove",  "Uninstall Pixi (~/.pixi folder)",   True, name="rm_user")
            upgrade_btn.setVisible(False)
            remove_btn.setVisible(False)
            hl.addWidget(install_btn)
            hl.addWidget(upgrade_btn)
            hl.addWidget(remove_btn)
            install_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row:
                self._tc_do_install(t, p, "user", tb, r))
            upgrade_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row:
                self._tc_do_install(t, p, "user", tb, r))
            remove_btn.clicked.connect(lambda chk=False, t=tool, p=pkg, tb=tbl, r=row:
                self._tc_do_remove(t, p, "user", tb, r))
        else:
            install_btn = _b("⬇ Install", "Install this tool",   name="install_user")
            upgrade_btn = _b("⬆ Upgrade", "Upgrade this tool",   name="upgrade_user")
            remove_btn  = _b("🗑 Remove",  "Uninstall this tool", True, name="rm_user")
            upgrade_btn.setVisible(False)
            remove_btn.setVisible(False)
            hl.addWidget(install_btn)
            hl.addWidget(upgrade_btn)
            hl.addWidget(remove_btn)

            if tool == "venv":
                # venv is part of the Python stdlib — there's nothing to
                # `pip install`. "Upgrading" venv really means updating the
                # Python interpreter itself. Route to the existing Python
                # Management → Download/Update flow instead of pip install.
                install_btn.setText("⬆ Update Python")
                install_btn.setToolTip(
                    "venv is part of the Python standard library — there's\n"
                    "nothing to pip install. This checks whether a newer\n"
                    "standalone Python build is available and, if so, offers\n"
                    "to open the download dialog."
                )
                install_btn.setAccessibleName("update_python")
                remove_btn.setVisible(False)
            elif tool == "pip":
                install_btn.setText("⬆ Upgrade")
                install_btn.setToolTip("Upgrade pip")
                install_btn.setAccessibleName("upgrade_user")
                remove_btn.setVisible(False)

            if tool == "venv":
                install_btn.clicked.connect(lambda chk=False, tb=tbl, r=row:
                    self._tc_check_python_update(tb, r))
            else:
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
            # pip/venv: install_user is repurposed as Upgrade — hide upgrade_user
            if "install_user" in btns: btns["install_user"].setVisible(True)
            if "upgrade_user" in btns: btns["upgrade_user"].setVisible(False)
            if "rm_user" in btns: btns["rm_user"].setVisible(False)
        elif installed:
            if "install_user" in btns: btns["install_user"].setVisible(False)
            if "upgrade_user" in btns: btns["upgrade_user"].setVisible(True)
            if "rm_user" in btns: btns["rm_user"].setVisible(True)
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

        # N68 (Bayram, 2026-08-27): the user's own environments belong here too.
        #
        # He asked what happens when someone installs pdm/pixi/pipx INTO an env
        # they made with VenvStudio. The answer was: nothing -- this combo was
        # fed only from the Python Versions table, so an env's interpreter never
        # appeared, and the panel could not see, let alone manage, anything
        # inside it. "Onun kurduklarini kullanmak isterse?" had no answer.
        #
        # Adding them widens what this panel means: with a system interpreter
        # selected it answers "what is on this machine", with an env selected
        # "what is in this environment". The rows already say which, since the
        # Path column shows where each tool actually lives, and the entries here
        # are labelled [env] so the two are never confused.
        _sys_count = combo.count()
        try:
            # SettingsPage has no venv_manager -- that attribute lives on the
            # main window, and reaching for it here raised AttributeError which
            # the bare `except` below swallowed, leaving an empty dropdown and
            # no explanation. Build one directly, the way
            # settings_page._get_editor_venv_dir already does.
            _vm = getattr(self, "venv_manager", None)
            if _vm is None:
                # VenvManager needs its base dir -- main_window.py:79
                # builds it as VenvManager(config.get_venv_base_dir()),
                # so ask the same question here. (settings_page.py has a
                # bare VenvManager() in _get_editor_venv_dir that raises
                # TypeError and lands in its own except -- it has simply
                # never been noticed, since that path falls through to a
                # default. Worth fixing separately.)
                from src.core.venv_manager import VenvManager
                _vm = VenvManager(self.config.get_venv_base_dir())
            # Same call env_list.py uses; skip_calc keeps it off the disk-size
            # walk, which this panel has no use for.
            _envs = _vm.list_venvs_fast(skip_calc=True) or []
            _log.debug(f"[TC] env scan: {len(_envs)} environment(s) found")
        except Exception as _ee:
            # Never silently: an empty dropdown with no reason in the log is
            # exactly the kind of thing that cost this project whole sessions.
            _log.warning(f"[TC] env scan failed: {_ee!r}")
            _envs = []
        for _e in _envs:
            try:
                _ep = str(getattr(_e, "path", "") or "")
                _en = str(getattr(_e, "name", "") or "") or \
                    os.path.basename(_ep.rstrip("/\\"))
                if not _ep:
                    continue
                _cand = [os.path.join(_ep, "Scripts", "python.exe"),
                         os.path.join(_ep, "bin", "python3"),
                         os.path.join(_ep, "bin", "python")]
                _pyx = next((c for c in _cand if os.path.isfile(c)), "")
                if not _pyx:
                    _log.debug(f"[TC] env {_en!r}: no interpreter under {_ep}")
                    continue
                if os.path.normcase(_pyx) in {
                        os.path.normcase(combo.itemData(i) or "")
                        for i in range(combo.count())}:
                    continue
                _log.debug(f"[TC] env {_en!r}: adding {_pyx}")
                combo.addItem(f"\U0001f4c1 {_en}  [env]  {_pyx}", _pyx)
            except Exception as _e2:
                _log.warning(f"[TC] env entry skipped: {_e2!r}")
                continue
        _env_count = combo.count() - _sys_count

        combo.blockSignals(False)

        note = getattr(self, "_tc_py_note", None)
        if note:
            _msg = f"{_sys_count} Python installation(s) available."
            if _env_count:
                _msg += (f"  \u2022  {_env_count} environment(s) \u2014 select one "
                         f"to manage the tools installed inside it.")
            note.setText(_msg)

        # Restore previous selection or use first
        idx = 0
        if current_data:
            for i in range(combo.count()):
                if os.path.normcase(combo.itemData(i) or "") == os.path.normcase(current_data):
                    idx = i; break
        if combo.count():
            combo.setCurrentIndex(idx)
            self._tc_load_table(combo.itemData(idx) or "")


    def _tc_py_ver_tag(self, py_exe) -> str:
        """'310' / '314' for the SELECTED interpreter. Cached per exe.

        Needed because the per-user scripts directory is version-stamped on
        Windows (%APPDATA%\\Python\\Python314\\Scripts), so telling one Python's
        tools from another's means knowing which version was picked -- not
        which version VenvStudio itself happens to be running under.
        """
        cache = getattr(self, "_tc_pyver_cache", None)
        if cache is None:
            cache = self._tc_pyver_cache = {}
        key = str(py_exe)
        if key in cache:
            return cache[key]
        tag = ""
        try:
            import subprocess
            from src.utils.platform_utils import subprocess_args
            r = subprocess.run(
                [py_exe, "-c",
                 "import sys;print(f'{sys.version_info.major}{sys.version_info.minor}')"],
                **subprocess_args(capture_output=True, text=True, timeout=5))
            if r.returncode == 0:
                tag = (r.stdout or "").strip()
        except Exception:
            pass
        cache[key] = tag
        return tag

    def _tc_find_tool(self, tool, py_exe):
        """Find tool exe for the GIVEN Python. Returns path or ''."""
        import os, sys, shutil

        # N66 (Bayram, 2026-08-27): conda is resolved here too, not only in the
        # scan loop. VenvStudio downloads its OWN micromamba and the table asks
        # get_micromamba_exe() for it -- but this function knew nothing about
        # that, so it answered "nothing found" for micromamba. The row showed
        # version 2.6.2 with working buttons while Remove replied "micromamba
        # has no executable in this environment". Two resolvers, two answers,
        # for the third time this week. One resolver: everything that needs to
        # know where a tool is comes through here.
        if tool == "micromamba":
            try:
                from src.core.micromamba_installer import get_micromamba_exe
                _mm = get_micromamba_exe()
                if _mm and os.path.isfile(str(_mm)):
                    _log.debug(f"[TC] find micromamba: bundled at {_mm}")
                    return str(_mm)
            except Exception:
                pass
            for _n in ("micromamba", "conda"):
                _w = shutil.which(_n)
                if _w:
                    _log.debug(f"[TC] find micromamba: PATH copy at {_w}")
                    return _w
            _log.debug("[TC] find micromamba: nothing found")
            return ""

        cands = []

        # N68 (Bayram, 2026-08-27): if the selected interpreter belongs to an
        # ENVIRONMENT, that environment's own Scripts/bin wins over everything.
        #
        # He asked what happens when a user installs pdm/pixi/conda/pipx INTO an
        # env they made with VenvStudio. Two answers, and the second is a bug I
        # introduced earlier today.
        #
        # First: the Python selector is fed from the Python Versions table, so
        # it only offers system interpreters -- an env's tools are invisible to
        # this panel entirely. That is a design gap, filed separately; showing
        # envs here would change what the panel means ("what is on this machine"
        # vs "what is in this environment") and deserves its own decision.
        #
        # Second, and fixable right now: the per-user-first order below is right
        # for a system interpreter (that is what stopped Program Files shadowing
        # %APPDATA%), but it would be exactly wrong for an env. An environment
        # exists to be isolated; a tool sitting inside it must never lose to a
        # global copy. So when py_exe is an env's interpreter, its own directory
        # goes first and the rule above applies only to the rest.
        _env_scripts = ""
        try:
            _d1 = os.path.dirname(py_exe)                 # <env>/bin or <env>\Scripts
            _d2 = os.path.dirname(_d1)                    # <env>
            for _root in (_d2, _d1):
                if not _root:
                    continue
                if (os.path.isfile(os.path.join(_root, "pyvenv.cfg"))
                        or os.path.isdir(os.path.join(_root, "conda-meta"))):
                    _env_scripts = _d1
                    break
        except Exception:
            _env_scripts = ""
        if _env_scripts:
            for n in (tool, tool + ".exe"):
                cands.append(os.path.join(_env_scripts, n))

        # N64 (2026-08-25): the PER-USER copy is preferred over the one in
        # the interpreter's own Scripts dir.
        #
        # Both can exist at once -- Bayram has hatch.exe in
        # C:\Program Files\Python314\Scripts AND in
        # %APPDATA%\Python\Python314\Scripts. Checking the interpreter dir
        # first meant the table always reported the system copy, so the row
        # stayed "System" with no buttons and Install appeared to do nothing,
        # even though a perfectly manageable user copy was sitting right
        # there. Per-user first matches what this manager can actually act
        # on, and matches how PATH is meant to resolve it anyway.
        _user_sc = ""
        if sys.platform == "win32":
            _tag0 = self._tc_py_ver_tag(py_exe)
            if _tag0:
                _user_sc = os.path.join(os.environ.get("APPDATA",""), "Python",
                                        f"Python{_tag0}", "Scripts")
        else:
            _user_sc = os.path.expanduser("~/.local/bin")
        if _user_sc:
            for n in (tool, tool+".exe"):
                cands.append(os.path.join(_user_sc, n))

        # Then the SELECTED Python's own Scripts/bin dir.
        py_sc = os.path.join(os.path.dirname(py_exe),
            "Scripts" if sys.platform=="win32" else "bin")
        for n in (tool,tool+".exe"):
            cands.append(os.path.join(py_sc,n))

        # Per-user scripts for THIS interpreter only.
        #
        # This block used to call site.getuserbase() -- which reports the user
        # base of the Python RUNNING VenvStudio, not the one selected in the
        # dropdown -- and then, on Windows, walked every %APPDATA%\Python\*
        # directory and added them all. With 3.10 selected the table therefore
        # listed 3.14's hatch/pdm/pipx/uv, and Upgrade/Remove would have acted
        # on the wrong installation entirely. Now the version tag of the
        # selected interpreter decides. (Bayram, 2026-08-19: "her python
        # versiyonu icin ayri ayri olmasi gerekmiyor mu?")
        if sys.platform == "win32":
            _tag = self._tc_py_ver_tag(py_exe)
            if _tag:
                sc = os.path.join(os.environ.get("APPDATA",""), "Python",
                                  f"Python{_tag}", "Scripts")
                for n in (tool,tool+".exe"): cands.append(os.path.join(sc,n))
        else:
            # POSIX puts every interpreter's user scripts in the same
            # ~/.local/bin, so there is nothing to disambiguate by path here.
            for n in (tool,tool+".exe"):
                cands.append(os.path.expanduser(os.path.join("~/.local/bin", n)))

        # Global PATH search LAST, and only as a genuine fallback: a PATH hit
        # can easily belong to a different interpreter (that is how Poetry from
        # Program Files\Python314 showed up under a 3.10 selection). Accept it
        # only when the selected Python actually reports the package installed,
        # or when the tool is not pip-installable at all (pixi, micromamba).
        _path_hit = ""
        for n in (tool, tool+".exe"):
            w = shutil.which(n)
            if w:
                _path_hit = w
                break
        if _path_hit and not any(c and os.path.isfile(c) for c in cands):
            if tool in ("pixi", "micromamba", "conda", "mamba"):
                cands.append(_path_hit)
            else:
                try:
                    import subprocess
                    from src.utils.platform_utils import subprocess_args
                    _r = subprocess.run(
                        [py_exe, "-m", "pip", "show", tool],
                        **subprocess_args(capture_output=True, text=True, timeout=8))
                    if _r.returncode == 0:
                        cands.append(_path_hit)
                except Exception:
                    pass
        found = next((c for c in cands if c and os.path.isfile(c)), "")
        # Decisive logging: after a whole session of guessing why one row
        # resolved differently from its neighbours, show the actual search.
        _log.debug(f"[TC] find {tool}: chose {found or "(nothing)"} from "
                   f"{[c for c in cands if c and os.path.isfile(c)]}")
        if found:
            # For pixi: verify it's the real prefix-dev pixi, not pip-installed fake
            if tool == "pixi":
                try:
                    import subprocess as _sp
                    _r = _sp.run([found, "--version"], capture_output=True, text=True, timeout=5)
                    _out = (_r.stdout + _r.stderr).lower()
                    if "pixiv" in _out or ("pixi" not in _out):
                        found = ""  # wrong pixi, keep searching
                except Exception:
                    pass
            if found:
                return found
        # For pixi: also check user-install locations
        if tool == "pixi" and not found:
            _pixi_cands = [
                os.path.expanduser("~/.pixi/bin/pixi"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), ".pixi", "bin", "pixi.exe"),
                os.path.join(os.environ.get("USERPROFILE", ""), ".pixi", "bin", "pixi.exe"),
            ]
            for _c in _pixi_cands:
                if os.path.isfile(_c):
                    try:
                        import subprocess as _sp
                        _r = _sp.run([_c, "--version"], capture_output=True, text=True, timeout=5)
                        _out = (_r.stdout + _r.stderr).lower()
                        if "pixi" in _out and "pixiv" not in _out:
                            return _c
                    except Exception:
                        pass
        # N64 (2026-08-25): NO "available as module" fallback.
        #
        # It ran `<py> -m <tool> --version` and, on success, returned PY_EXE
        # as the tool's path -- a sentinel meaning "importable, but has no
        # launcher". Everything downstream then treated that Python as if it
        # WERE the tool: the version cell ran `<py_exe> --version` and printed
        # Python's own version (PDM and pipx both showed "3.14.6"), and the
        # path cell resolved through `pip show` to a package DIRECTORY
        # (...\Lib\site-packages\pdm) -- not something anyone can run, upgrade
        # or remove. On Bayram's box `where.exe pdm` and `where.exe pipx` both
        # come back empty: the packages are there, the launchers never got
        # created. "Not found" with an Install button is the honest answer,
        # and Install actually fixes it.
        return ""


    def _tc_load_table(self, py_exe, force=False):
        """Reload table rows for the selected Python.

        force=False (default): serve from the on-disk cache when this
        Python has been scanned before -- instant, no subprocess calls, no
        lag when switching between Pythons you've already looked at.
        force=True: always rescan (Refresh button, and after an
        install/upgrade/remove where the on-disk state just changed).
        """
        import os
        if not py_exe or not hasattr(self,"_tc_table"):
            return
        if not force:
            cached = self._tc_cache_read(py_exe)
            if cached is not None:
                self._tc_populate_table(py_exe, cached)
                self._tc_note_scan_age(self._tc_cache_age(py_exe))
                return
        import subprocess, sys
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTableWidgetItem
        tbl = self._tc_table

        def _do(callback=None):
            rows = []
            for tid, pkg, lbl, icon in self._TC_TOOLS:
                if tid == "micromamba":
                    # Prefer system conda/mamba/micromamba if available (shows as Global/User)
                    # Fall back to VenvStudio-managed micromamba (shows as Managed)
                    import shutil as _shutil
                    _sys_conda = (_shutil.which("conda") or
                                  _shutil.which("mamba") or
                                  _shutil.which("micromamba"))
                    if _sys_conda:
                        path = _sys_conda
                    else:
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
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
                            path = py_exe if r.returncode == 0 else ""
                        else:
                            r = subprocess.run([py_exe, "-m", tid, "--version"],
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
                            path = py_exe if r.returncode == 0 else ""
                    except Exception: path = ""
                else:
                    path = self._tc_find_tool(tid, py_exe)

                ver = "—"
                if path:
                    try:
                        if tid == "venv":
                            r = subprocess.run([py_exe, "--version"],
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
                            ver = (r.stdout or r.stderr).strip().replace("Python ", "")
                        elif tid == "pip":
                            r = subprocess.run([py_exe, "-m", "pip", "--version"],
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
                            out = (r.stdout or r.stderr).strip()
                            for p in out.split():
                                if p and p[0].isdigit():
                                    # "Poetry (version 2.4.1)" -> split() yields
                                    # "2.4.1)"; rstrip(",") left the bracket.
                                    ver = p.strip("(),;"); break
                        else:
                            r = subprocess.run([path, "--version"],
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
                            out = (r.stdout or r.stderr).strip()
                            for p in out.split():
                                if p and p[0].isdigit():
                                    # "Poetry (version 2.4.1)" -> split() yields
                                    # "2.4.1)"; rstrip(",") left the bracket.
                                    ver = p.strip("(),;"); break
                            if ver == "—": ver = out[:20]
                    except Exception:
                        pass
                # Resolve the real module location up front (was previously
                # done again on every table repaint, in _done on the UI
                # thread) so a cache hit never needs to run `pip show` again.
                display_path = path
                tid_local = tid
                if path and os.path.normpath(path) == os.path.normpath(py_exe):
                    try:
                        _pr = subprocess.run([py_exe, "-m", "pip", "show", tid_local],
                            **subprocess_args(capture_output=True, text=True, timeout=5))
                        _loc = next((l.split(":", 1)[1].strip()
                                     for l in _pr.stdout.splitlines()
                                     if l.startswith("Location:")), "")
                        if _loc:
                            # Build the display path from the Location: line
                            # `pip show` reported for the SELECTED python.
                            # This used to prefer importlib.find_spec(), which
                            # resolves inside the interpreter running
                            # VenvStudio -- so with 3.12 picked the pip row
                            # still pointed at /usr/lib/python3.14/site-
                            # packages/pip, overwriting the correct answer
                            # that _loc already held. (Bayram, 2026-08-19.)
                            display_path = os.path.join(_loc, tid_local)
                    except Exception:
                        pass
                rows.append((path, ver, display_path))
            import json
            return True, json.dumps({"py": py_exe, "rows": rows})

        def _done(ok, result):
            # NOT _tc_end_job() here: this scan never called _tc_begin_job,
            # so clearing the flag would release a lock belonging to a real
            # install/remove job still in flight. (My own slip -- the blanket
            # edit that added the guard caught this handler too.)
            import json
            if not ok:
                _log.warning(f"🧰 [TC] _done called with ok=False, result={result[:120]!r}")
                return
            try:
                data = json.loads(result)
                _py = data["py"]
                rows = data["rows"]
            except Exception as e:
                _log.warning(f"🧰 [TC] JSON parse error: {e!r}, result={result[:120]!r}")
                return

            # N72 (Bayram, 2026-08-27): drop results for a Python that is no
            # longer selected.
            #
            # A scan takes several seconds. Switch interpreter twice and two
            # scans are in flight; whichever finished LAST used to win and
            # paint its rows over the current selection, whatever the user was
            # actually looking at. That is why switching Python "needed a few
            # presses of Refresh" -- each press was another race, and one
            # eventually came back in the right order.
            try:
                _want = self._tc_py_combo.currentData() or ""
            except Exception:
                _want = ""
            if _want and os.path.normcase(_py) != os.path.normcase(_want):
                _log.debug(f"[TC] discarding stale scan for {_py[:40]} "
                           f"(selection is now {_want[:40]})")
                self._tc_cache_write(_py, rows)   # still worth caching
                return

            _log.debug(f"🧰 [TC] _done: {len(rows)} rows loaded for {_py[:40]}")
            self._tc_populate_table(_py, rows)
            self._tc_cache_write(_py, rows)
            self._tc_note_scan_age(0)

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
        if not hasattr(self,"_tc_ws"): self._tc_ws=[]
        self._tc_ws.append(w)

    def _tc_populate_table(self, _py, rows):
        """Fill the table from (path, ver, display_path) rows -- pure UI, no
        subprocess calls, so this is fast enough to call directly from a
        cache hit (no worker thread needed) as well as from a fresh scan."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QTableWidgetItem
        import os as _os
        if not hasattr(self, "_tc_table"):
            return
        tbl = self._tc_table
        _py_scripts = _os.path.dirname(_py)  # Python's own Scripts/bin dir
        for row, item in enumerate(rows):
            path = item[0]
            ver = item[1]
            _display_path = item[2] if len(item) > 2 else path
            ok2 = bool(path)
            # col 1: Status
            _tid = self._TC_TOOLS[row][0] if row < len(self._TC_TOOLS) else ""
            import os as _os2
            _home = _os2.path.expanduser("~").lower()
            _managed_dir = _os2.path.join(_home, ".local", "share", "venvstudio").lower()
            _managed_dir_win = _os2.path.join(
                _os2.environ.get("APPDATA", ""), "VenvStudio"
            ).lower()
            _path_lower = path.lower() if path else ""
            _is_managed = (ok2 and (
                _path_lower.startswith(_managed_dir) or
                _path_lower.startswith(_managed_dir_win)
            ))
            # Python Scripts/bin dir — only match if it's a venv-style path
            # e.g. /home/user/venv/bin, not /usr/bin
            _py_scripts_lower = _py_scripts.lower() if _py_scripts else ""
            _in_env = False
            _env_root = ""
            _is_system_scripts = any(_py_scripts_lower.startswith(p) for p in (
                "/usr/bin", "/usr/local/bin", "/bin",
                "c:\\windows", "c:\\program files"
            ))
            _is_python_local = (ok2 and not _is_managed and
                not _is_system_scripts and
                _py_scripts and
                path.lower().startswith(_py_scripts_lower))
            _is_user = (ok2 and not _is_managed and not _is_python_local and (
                _path_lower.startswith(_os2.path.join(_home, ".local").lower()) or
                _path_lower.startswith(_os2.path.join(_home, ".cargo").lower()) or
                _path_lower.startswith(_os2.environ.get("LOCALAPPDATA", "~~~").lower()) or
                _path_lower.startswith(_os2.environ.get("APPDATA", "~~~").lower())
            ))
            # Global = /usr/bin, /usr/local/bin, C:\Program Files etc.
            _global_prefixes = ("/usr/bin/", "/usr/local/bin/", "/bin/",
                "/opt/homebrew/bin/")
            _is_global_path = ok2 and any(
                path.lower().startswith(p) for p in _global_prefixes
            )
            # TWO words, nothing else. This column used to speak six dialects
            # -- Built-in / Managed / Global / Python / User / Installed -- and
            # some of them meant the same thing: pixi in ~/.pixi/bin read
            # "Installed" while pdm in ~/.local/bin read "User", both per-user.
            # The only distinction that changes what the user can DO is whether
            # writing there needs admin rights, so that is the only thing the
            # column reports now. pip and venv are classified by their location
            # like everything else; their rows already lack a Remove button, so
            # nothing is lost by dropping the "Built-in" wording.
            # (Bayram, 2026-08-19: "System ve User demen yeterliiii")
            if ok2:
                _env_root = self._tc_env_root(_py)
                _in_env = bool(_env_root and path and
                               _os2.path.normcase(path).startswith(
                                   _os2.path.normcase(_env_root)))
                if _in_env:
                    # N68: with an environment selected, a tool living INSIDE it
                    # is neither a system nor a user-global install -- and that
                    # distinction is the point of the row, because Upgrade and
                    # Remove act on this copy alone, not on the global one.
                    st_text = "\U0001f4c1 Env"
                    st_color = "#f9e2af"
                elif _is_user or _is_managed or self._tc_dir_is_writable(path):
                    st_text = "\U0001f464 User"
                    st_color = "#a6e3a1"
                else:
                    st_text = "🖥 System"
                    st_color = "#89b4fa"
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

            # col 3: Path (display_path already resolved by the scan, cached)
            pi = QTableWidgetItem(_display_path if ok2 else "\u2014")
            pi.setForeground(QColor(self._c()["fg_muted"]))
            _tip = path

            # N68 (Bayram, 2026-08-27): say when a SECOND copy exists.
            #
            # He asked whether VenvStudio should ask which copy to act on when a
            # tool is installed both inside the selected environment and
            # globally. It should not -- picking the environment in the dropdown
            # already answered that, and asking again would bring back exactly
            # the "User or System?" question we just removed. But his confusion
            # was fair: the row showed one path and gave no hint the other copy
            # existed, so it was impossible to tell what Upgrade and Remove were
            # NOT going to touch. Show it instead of asking about it.
            if _in_env and _tid:
                try:
                    import shutil as _sh6
                    _others = []
                    for _c6 in (_sh6.which(_tid), _sh6.which(_tid + ".exe")):
                        if not _c6:
                            continue
                        if _os2.path.normcase(_c6).startswith(
                                _os2.path.normcase(_env_root)):
                            continue          # that is this row's own copy
                        if _c6 not in _others:
                            _others.append(_c6)
                    if _others:
                        _tip += ("\n\nAlso installed outside this "
                                 "environment:\n"
                                 + "\n".join(_others)
                                 + "\n\nUpgrade and Remove will ask which "
                                   "installation to act on.")
                        pi.setText((_display_path if ok2 else "\u2014") + "  \u2295")
                except Exception:
                    pass
            pi.setToolTip(_tip)
            tbl.setItem(row, 3, pi)

            # Update action buttons
            self._tc_update_row_btns(tbl, row, ok2)

    def _tc_cache_age(self, py_exe) -> float:
        """Seconds since this Python's rows were scanned; 0 if unknown."""
        import json, os, time
        try:
            with open(self._tc_cache_file(), "r", encoding="utf-8") as f:
                entry = json.load(f).get(os.path.normcase(py_exe), {})
            _ts = entry.get("ts", 0)
            return max(0.0, time.time() - _ts) if _ts else 0.0
        except Exception:
            return 0.0

    def _tc_note_scan_age(self, age_seconds: float):
        """Say how old the displayed rows are.

        N73: with the one-hour expiry gone the table can show data from days
        ago, which is fine -- but only if the user can see that it is old.
        Silent staleness is what made the Conda row claim version 2.6.2 for a
        binary that had already been deleted.
        """
        note = getattr(self, "_tc_py_note", None)
        if not note:
            return
        _base = note.text().split("   \u2022   Scanned")[0]
        if age_seconds < 60:
            _when = "just now"
        elif age_seconds < 3600:
            _when = f"{int(age_seconds // 60)} min ago"
        elif age_seconds < 86400:
            _when = f"{int(age_seconds // 3600)} h ago"
        else:
            _when = f"{int(age_seconds // 86400)} d ago"
        note.setText(f"{_base}   \u2022   Scanned {_when} \u2014 press Refresh to rescan")

    def _tc_cache_file(self):
        """Path to the toolchain scan cache -- same VenvStudio config dir
        pattern already used elsewhere in this file (APPDATA/VenvStudio on
        Windows, ~/.config/VenvStudio on Linux/Mac)."""
        import os, sys
        if sys.platform == "win32":
            base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "VenvStudio")
        else:
            base = os.path.join(os.path.expanduser("~"), ".config", "VenvStudio")
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        return os.path.join(base, "toolchain_cache.json")

    def _tc_cache_read(self, py_exe):
        """Return cached rows for py_exe, or None if a rescan is needed.

        N73 (Bayram, 2026-08-27): the cache is now trusted until something
        actually invalidates it. There are exactly three reasons to rescan:

          1. this Python has never been scanned
          2. the tool list (_TC_TOOLS) changed
          3. a recorded executable is no longer on disk

        ...plus the user pressing Refresh, and any install/upgrade/remove,
        both of which call _tc_load_table(force=True) and rewrite the cache.

        What went: a one-hour expiry that threw away a perfectly good answer
        and re-ran nine `--version` subprocesses for nothing. Its purpose was
        to notice changes made outside VenvStudio, but reason 3 already covers
        a tool that disappeared, and the honest cost of the rest is that a
        version number upgraded in a terminal stays stale until Refresh.
        Bayram knows to press Refresh; he should not have to wait every hour
        for a scan he did not ask for.
        """
        import json, os, time
        try:
            fp = self._tc_cache_file()
            if not os.path.isfile(fp):
                return None
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Version fingerprint: sorted tool IDs joined
            _current_sig = ",".join(t[0] for t in self._TC_TOOLS)
            if data.get("_sig") != _current_sig:
                return None  # _TC_TOOLS changed — invalidate entire cache
            entry = data.get(os.path.normcase(py_exe))
            if not entry:
                return None
            # No expiry -- see the docstring. `ts` is still written and is
            # surfaced in the UI so stale data is visible, not silent.
            raw_rows = entry.get("rows", [])

            # N67 (Bayram, 2026-08-27): a cached path is only worth anything
            # while the file is still there.
            #
            # He removed Conda, the app crashed before it could refresh, and on
            # the next start the table happily showed "Conda 2.6.2" from the
            # hour-old cache -- while the binary was gone. Clicking Remove then
            # answered "micromamba has no executable in this environment", which
            # reads as nonsense next to a row displaying a version. The resolver
            # was right and the table was stale.
            #
            # Anything the user does OUTSIDE VenvStudio -- uninstalling a tool
            # in a terminal, a distro upgrade moving a binary -- lands us in the
            # same spot, so this is not only about the crash. A handful of
            # os.path.isfile calls is cheap next to re-running every tool's
            # --version, which is what a full rescan costs.
            try:
                import os as _os_v
                for _r in raw_rows:
                    _p = _r[1] if entry.get("keyed", False) and len(_r) > 1 else (
                        _r[0] if _r else "")
                    if _p and not _os_v.path.isfile(_p):
                        _log.debug(f"[TC] cache: {_p} is gone \u2014 rescanning")
                        return None
            except Exception:
                return None
            is_keyed = entry.get("keyed", False)
            if is_keyed:
                _id_to_row = {}
                for r in raw_rows:
                    if r and len(r) >= 2:
                        _id_to_row[r[0]] = tuple(r[1:])
                result = []
                for tid, pkg, lbl, icon in self._TC_TOOLS:
                    result.append(_id_to_row.get(tid, ("", "—", "")))
                return result
            else:
                if len(raw_rows) != len(self._TC_TOOLS):
                    return None
                return [tuple(r) for r in raw_rows]
        except Exception:
            return None

    def _tc_cache_write(self, py_exe, rows):
        """Persist scan results for py_exe so switching back to it later
        skips rescanning entirely. Rows are stored with tool_id so order
        changes in _TC_TOOLS don't corrupt the cache."""
        import json, os, time
        try:
            fp = self._tc_cache_file()
            data = {}
            if os.path.isfile(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            # Store rows keyed by tool_id, not positionally
            _keyed_rows = []
            for i, row in enumerate(rows):
                _tid = self._TC_TOOLS[i][0] if i < len(self._TC_TOOLS) else f"_unknown_{i}"
                _keyed_rows.append([_tid] + list(row))
            _current_sig = ",".join(t[0] for t in self._TC_TOOLS)
            data["_sig"] = _current_sig
            data[os.path.normcase(py_exe)] = {"rows": _keyed_rows, "ts": time.time(),
                                               "keyed": True}
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            _log.debug(f"🧰 [TC] cache write failed: {e}")

    def _tc_check_python_update(self, tbl, row):
        """Check whether a newer standalone Python build is available than
        the currently selected interpreter, and offer to open the Download
        Python dialog if so. Reuses the same version source
        (get_available_versions) as PythonDownloadDialog — no new download
        logic is introduced here, only a comparison + prompt.
        """
        from PySide6.QtWidgets import QMessageBox, QProgressDialog
        from PySide6.QtCore import Qt as _Qt

        vi = tbl.item(row, 2)
        current_ver = vi.text() if vi else ""
        if not current_ver or current_ver == "—":
            QMessageBox.warning(
                self, "Update Python",
                "Could not determine the currently selected Python version."
            )
            return

        def _ver_tuple(v):
            parts = []
            for p in str(v).split("."):
                digits = "".join(ch for ch in p if ch.isdigit())
                parts.append(int(digits) if digits else 0)
            return tuple(parts)

        def _do(callback=None):
            import json
            try:
                from src.core.python_downloader import get_available_versions
                versions = get_available_versions(mirror="astral", try_fallbacks=True)
                return True, json.dumps(versions)
            except Exception as e:
                return False, str(e)

        progress = QProgressDialog("Checking for newer Python versions...", None, 0, 0, self)
        progress.setWindowTitle("Update Python")
        progress.setWindowModality(_Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def _done(ok, result):
            self._tc_end_job()
            progress.close()
            if not ok:
                QMessageBox.warning(
                    self, "Update Python",
                    f"Could not fetch available Python versions.\n\n{result[:200]}"
                )
                return
            import json
            try:
                versions = json.loads(result)
            except Exception:
                QMessageBox.warning(self, "Update Python", "Could not parse available versions.")
                return
            if not versions:
                QMessageBox.warning(
                    self, "Update Python",
                    "Could not fetch available Python versions.\nCheck your internet connection."
                )
                return

            latest = max(versions, key=lambda v: _ver_tuple(v.get("version", "0")))
            latest_ver = latest.get("version", "")

            if _ver_tuple(latest_ver) > _ver_tuple(current_ver):
                reply = QMessageBox.question(
                    self, "Update Available",
                    f"A newer Python build is available:\n\n"
                    f"   Currently selected:  {current_ver}\n"
                    f"   Latest available:    {latest_ver}\n\n"
                    f"Open the download dialog to install it?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self._download_python()
            else:
                QMessageBox.information(
                    self, "Up to Date",
                    f"You already have the latest version ({current_ver})."
                )

        if not self._tc_begin_job("install"):
            return
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
        if not hasattr(self, "_tc_ws"): self._tc_ws = []
        self._tc_ws.append(w)

    # A USER install never needs admin rights: it writes to the per-user site
    # (~/.local, %APPDATA%\Python) and leaves any system copy alone -- the user
    # copy simply wins on PATH. An earlier version of this method tested whether
    # the EXISTING install was writable and, when it was not, refused the user
    # install and told the user to go run pip in an elevated terminal. That is
    # why choosing "User" demanded admin rights for a tool sitting in
    # /usr/bin or Program Files (Bayram, 2026-08-19: "user install da neden
    # admin yetkileri istiyorsun"). Elevation belongs to the system scope and
    # nowhere else, so the check is gone.
    @staticmethod
    def _tc_dir_is_writable(path: str) -> bool:
        """Can we write next to this executable? Used only to label the
        Status column System vs User -- never to block an action."""
        import os as _os, tempfile as _tf
        d = _os.path.dirname(path) if _os.path.isfile(path) else path
        if not d or not _os.path.isdir(d):
            return True
        try:
            with _tf.NamedTemporaryFile(dir=d, prefix=".vs-wtest-"):
                return True
        except OSError:
            return False

    def _tc_do_install(self, tool, pkg, scope, tbl, row):
        import sys, os
        from PySide6.QtGui import QColor

        # B: 'venv' has pkg=None (it's part of the Python stdlib, not a
        # separately pip-installable package) — installing/upgrading it
        # would crash subprocess.run() with a None arg. Guard it here,
        # consistent with the existing guard in _tc_do_remove.
        if tool == "venv":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Nothing to install",
                f"'{tool}' is part of the Python standard library — "
                f"it cannot be installed or upgraded separately."
            )
            return

        # Pixi: pkg=None but has its own installer — handle via WorkerThread like other tools
        if tool == "pixi" and not pkg:
            import subprocess, shutil, os, sys
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QTableWidgetItem

            # Get py_exe early for cache invalidation
            _si0 = tbl.item(row, 1)
            py_exe = (_si0.data(257) if _si0 else "") or ""
            if not py_exe and hasattr(self, "_tc_py_combo"):
                py_exe = self._tc_py_combo.currentData() or sys.executable
            if not py_exe:
                py_exe = sys.executable

            _pixi_cands = [
                os.path.expanduser("~/.pixi/bin/pixi"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), ".pixi", "bin", "pixi.exe"),
                os.path.join(os.environ.get("USERPROFILE", ""), ".pixi", "bin", "pixi.exe"),
            ]
            _pixi_exe = next((c for c in _pixi_cands if os.path.isfile(c)), None)

            si = tbl.item(row, 1)
            if si:
                si.setText("⏳ Installing...")
                si.setForeground(QColor("#89b4fa"))

            def _do_pixi(_pixi_exe=_pixi_exe, callback=None):
                import subprocess, shutil, os, sys
                if _pixi_exe:
                    # Already installed — self-update
                    r = subprocess.run([_pixi_exe, "self-update"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0:
                        return True, _pixi_exe
                    # self-update failed but pixi exists — not an error
                    _out = (r.stdout + r.stderr).lower()
                    if "already" in _out or "up to date" in _out or "latest" in _out:
                        return True, _pixi_exe
                    return False, r.stderr[:300] or r.stdout[:300]
                else:
                    # Not installed — remove pip fake, then install
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "pixi", "-y"],
                        capture_output=True, text=True, timeout=60)
                    if sys.platform == "win32":
                        _winget = shutil.which("winget")
                        if _winget:
                            r = subprocess.run([_winget, "install", "prefix-dev.pixi",
                                                "--accept-package-agreements",
                                                "--accept-source-agreements"],
                                               capture_output=True, text=True, timeout=300)
                            if r.returncode == 0:
                                _new = os.path.join(os.environ.get("USERPROFILE", ""),
                                                    ".pixi", "bin", "pixi.exe")
                                return True, _new if os.path.isfile(_new) else ""
                        # N64: absolute path. Bare "powershell" failed with
                        # PermissionError [WinError 5] Access is denied --
                        # CreateProcess resolves the bare name against PATH
                        # and can land on something it may not execute. The
                        # same lesson as pixi and conda earlier today: never
                        # launch a program by name when the path is knowable.
                        # Real System32 copy FIRST. shutil.which() is a trap
                        # here: on Windows 11 it often returns the App
                        # Execution Alias under
                        #   ...\AppData\Local\Microsoft\WindowsApps\powershell.exe
                        # which is a zero-byte reparse point, and launching it
                        # from a background thread fails with
                        #   PermissionError [WinError 5] Access is denied
                        # -- exactly what Bayram hit twice, once with the bare
                        # name and once with which(). (2026-08-25)
                        import shutil as _sh4
                        _root = os.environ.get("SystemRoot", r"C:\Windows")
                        _ps = ""
                        for _c4 in (
                            os.path.join(_root, "System32", "WindowsPowerShell",
                                         "v1.0", "powershell.exe"),
                            _sh4.which("pwsh") or "",
                            _sh4.which("powershell") or "",
                        ):
                            if _c4 and os.path.isfile(_c4) and \
                                    "windowsapps" not in _c4.lower() and \
                                    os.path.getsize(_c4) > 0:
                                _ps = _c4
                                break
                        if not _ps:
                            return False, ("Could not find a usable PowerShell to "
                                           "run the pixi installer")
                        r = subprocess.run(
                            [_ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                             "iwr -useb https://pixi.sh/install.ps1 | iex"],
                            **subprocess_args(capture_output=True, text=True, timeout=300))
                    else:
                        r = subprocess.run(
                            ["sh", "-c", "curl -fsSL https://pixi.sh/install.sh | bash"],
                            capture_output=True, text=True, timeout=300)
                    if r.returncode == 0:
                        _new = os.path.expanduser("~/.pixi/bin/pixi")
                        if not os.path.isfile(_new):
                            _new = os.path.join(os.environ.get("USERPROFILE", ""),
                                                ".pixi", "bin", "pixi.exe")
                        return True, _new if os.path.isfile(_new) else ""
                    return False, r.stderr[:300] or r.stdout[:300]

            def _on_pixi_done(ok, result, _row=row, _tbl=tbl, _py=py_exe):
                # Release the one-job-at-a-time flag. This handler was the
                # only guarded job missing it, which would have left the
                # panel refusing every later action after one pixi install.
                self._tc_end_job()
                from PySide6.QtCore import QTimer as _QTimer
                # Invalidate cache so next open shows fresh state
                try:
                    import json, os
                    fp = self._tc_cache_file()
                    if os.path.isfile(fp):
                        with open(fp, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data.pop(os.path.normcase(_py), None)
                        with open(fp, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                except Exception:
                    pass
                si2 = _tbl.item(_row, 1)
                if ok:
                    if si2:
                        si2.setText("👤 User")   # reload below re-derives it
                        si2.setForeground(QColor("#a6e3a1"))
                    _QTimer.singleShot(800, lambda: self._tc_load_table(_py, force=True))
                else:
                    if si2:
                        si2.setText("❌ Failed")
                        si2.setForeground(QColor("#f38ba8"))
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Pixi Install Failed", result)

            if not self._tc_begin_job("pixi install"):
                return
            from src.gui.package_panel import WorkerThread
            w = WorkerThread(_do_pixi, parent=self)
            w.finished.connect(_on_pixi_done)
            w.start()
            if not hasattr(self, "_tc_ws"):
                self._tc_ws = []
            self._tc_ws.append(w)
            return

        si = tbl.item(row, 1)
        py_exe = (si.data(257) if si else "") or ""
        if not py_exe and hasattr(self, "_tc_py_combo"):
            py_exe = self._tc_py_combo.currentData() or sys.executable
        if not py_exe:
            py_exe = sys.executable

        # N69: upgrading a tool that exists twice -- ask which copy. Only when
        # one is already there; a fresh install has nothing to choose between.
        if self._tc_find_tool(tool, py_exe):
            _chosen_up, _owner_up = self._tc_pick_copy(tool, py_exe, "upgrade")
            if _chosen_up is None:
                return                  # cancelled
            if _owner_up:
                py_exe = _owner_up

        if si: si.setText("\u23f3 Installing..."); si.setForeground(QColor("#89b4fa"))

        # Pre-import subprocess_args outside worker thread
        try:
            from src.utils.platform_utils import subprocess_args as _spa_fn
        except Exception:
            _spa_fn = lambda: {}

        def _do(callback=None):
            import subprocess, time, shutil as _sh

            # N64 (2026-08-25): pip is not enough on its own.
            #
            # `pip install pdm --user` answered
            #     Requirement already satisfied: pdm in
            #     C:\Program Files\Python314\Lib\site-packages (2.28.0)
            # and exited 0 -- while `where.exe pdm` stayed empty. The PACKAGE
            # was present, its LAUNCHER was not (deleted at some point), and
            # pip only ever checks the former. So Install reported success,
            # the table re-scanned, found no executable, and said Not found.
            # Round and round, with nothing in the log to show for it.
            #
            # So: run pip, then look for the executable. If it is still
            # missing, retry once with --force-reinstall (which does rebuild
            # the launcher, verified on Bayram's box) and check again. And log
            # every command and every result -- four separate bugs today hid
            # behind a silent subprocess.
            def _log_run(argv, **kw):
                _log.debug(f"[TC] run: {' '.join(str(a) for a in argv)}")
                _r = subprocess.run(argv, **kw)
                _log.debug(f"[TC]   -> exit={_r.returncode}"
                           + (f" err={(_r.stderr or '').strip()[:200]}"
                              if _r.returncode else ""))
                return _r

            def _launcher_exists():
                return bool(self._tc_find_tool(tool, py_exe))

            def _pip_user(extra=()):
                # N68: `--user` is meaningless -- and rejected -- inside a
                # virtualenv:
                #   "Can not perform a '--user' install. User site-packages are
                #    not visible in this virtualenv."
                # With an environment selected the install belongs IN that
                # environment, which is what a plain `pip install` already does.
                # Add the flag only when the target is a system interpreter.
                _argv = [py_exe, "-m", "pip", "install", pkg, "-q"]
                if not self._tc_env_root(py_exe):
                    _argv.insert(-1, "--user")
                _argv += list(extra)
                if sys.platform == "linux":
                    _argv.append("--break-system-packages")
                return _log_run(_argv,
                                **subprocess_args(capture_output=True, text=True,
                                                  timeout=180),
                                cwd=os.path.expanduser("~"))

            def _ensure_launcher():
                """True if the tool's executable exists, forcing a rebuild once."""
                if _launcher_exists():
                    return True
                _log.info(f"[TC] {tool}: pip succeeded but no launcher — "
                          f"retrying with --force-reinstall")
                _pip_user(("--force-reinstall", "--no-deps"))
                return _launcher_exists()
            # N64 (2026-08-25): `_spa` IS subprocess_args (see the import at the
            # top of this method), so every call site that wrote both
            #     **subprocess_args(...), cwd=_home, **_spa()
            # handed subprocess.run() creationflags twice and died with
            #     TypeError: got multiple values for keyword argument
            # Kept only for the two places that use it on its own.
            _spa = _spa_fn
            _is_win = sys.platform == "win32"
            _is_linux = sys.platform == "linux"
            _home = os.path.expanduser("~")

            # Build install command based on tool and scope
            # uv, poetry, pipx are standalone tools — install via pipx or pip --user
            _standalone = tool in ("uv", "poetry", "pipx")

            if _is_win:
                # N64: user scope only -- the elevated path is gone (see the
                # note in _pm_install_tool for the full reasoning).
                r = _pip_user()
                if r.returncode != 0:
                    return False, (r.stderr or r.stdout or "failed")[:300]
                if not _ensure_launcher():
                    return False, (
                        f"pip reported success but no {tool} executable "
                        f"appeared, even after a forced reinstall.")
            else:
                # Linux / macOS
                # N64: user scope only here too. The pkexec path is gone --
                # a per-user install needs no password and always works.
                # User install — prefer pipx for standalone tools
                if _standalone and tool != "pipx":
                    # Install via pipx if available, else pip --user
                    _pipx = _sh.which("pipx")
                    if _pipx:
                        r = _log_run([_pipx, "install", pkg],
                            **subprocess_args(capture_output=True, text=True, timeout=180),
                            cwd=_home)
                    else:
                        r = _pip_user()
                    if r.returncode != 0:
                        return False, (r.stderr or r.stdout or "failed")[:300]
                    if not _ensure_launcher():
                        return False, (
                            f"pip reported success but no {tool} executable "
                            f"appeared, even after a forced reinstall.")
                elif tool == "pipx":
                    r = _pip_user()
                    if r.returncode != 0:
                        return False, (r.stderr or r.stdout or "failed")[:300]
                    if not _ensure_launcher():
                        return False, (
                            f"pip reported success but no {tool} executable "
                            f"appeared, even after a forced reinstall.")
                else:
                    # hatch, pdm and anything else added later.
                    r = _pip_user()
                    if r.returncode != 0:
                        return False, (r.stderr or r.stdout or "failed")[:300]
                    if not _ensure_launcher():
                        return False, (
                            f"pip reported success but no {tool} executable "
                            f"appeared, even after a forced reinstall.")

            # Post-install: ensurepath for pipx
            if tool == "pipx":
                _pipx2 = _sh.which("pipx") or (py_exe.replace("python", "pipx") if "python" in py_exe else "")
                if _pipx2:
                    try:
                        subprocess.run([_pipx2, "ensurepath"],
                            **subprocess_args(capture_output=True, timeout=30), cwd=_home)
                    except Exception:
                        pass
            return True, "ok"

        def _done(ok, res):
            self._tc_end_job()
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
            QTimer.singleShot(500, lambda: self._tc_load_table(py_exe, force=True))

        # Conda removal takes the whole toolchain down with it, so confirm
        # first -- on the MAIN thread, where widgets are legal (N66).
        if tool == "micromamba":
            from PySide6.QtWidgets import QMessageBox as _QMB2
            if _QMB2.warning(
                    self, "Remove Conda (micromamba)",
                    "This will remove the micromamba binary managed by "
                    "VenvStudio.\n\n"
                    "⚠️ Conda environments will no longer be accessible "
                    "until you\nre-install micromamba via Toolchain "
                    "Manager.\n\nProceed?",
                    _QMB2.Yes | _QMB2.No, _QMB2.No) != _QMB2.Yes:
                return
        if not self._tc_begin_job("removal"):
            return
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
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

        # N69: if two copies exist, let the user say which one.
        _chosen, _owner = self._tc_pick_copy(tool, py_exe, "remove")
        if _chosen is None:
            return                      # cancelled
        if _owner:
            py_exe = _owner

        if si: si.setText("\u23f3 Removing..."); si.setForeground(QColor("#89b4fa"))
        _home = __import__("os").path.expanduser("~")

        def _do(callback=None):
            import subprocess, os
            from src.utils.platform_utils import subprocess_args
            # Build correct remove command per tool
            # Find the tool's own executable first
            # Resolve exactly like the table does. This used to call
            # shutil.which(), which searches PATH -- and on Bayram's box
            # C:\Program Files\Python314\Scripts comes BEFORE the per-user
            # Scripts dir, so Remove kept finding the system hatch.exe and
            # refusing, while the row itself was showing (and offering to
            # manage) the per-user copy sitting one directory away.
            # One resolver, one answer. (2026-08-25)
            # N69: the copy the user picked above wins over a fresh lookup.
            _tool_exe = (_chosen
                         or self._tc_find_tool(tool, py_exe)
                         or _shutil.which(tool)
                         or _shutil.which(tool + ".exe"))
            # N64: no module-only uninstall path any more. It elevated with
            # pkexec to run `pip uninstall`, which is exactly the kind of
            # thing this manager should not be doing -- and a tool with no
            # executable is no longer listed as installed at all (see
            # _tc_find_tool), so this branch had nothing left to act on.
            if not _tool_exe:
                return False, (
                    f"{tool} has no executable in this environment, so there "
                    f"is nothing for VenvStudio to remove.")
            if tool in ("pip", "venv"):
                return False, f"{tool} cannot be removed — it is a core Python component"
            elif tool == "micromamba":
                # N66: the confirmation used to be asked HERE, inside the
                # worker thread. Qt only allows widgets on the main thread,
                # so it produced
                #   QObject::setParent: Cannot set parent, new parent is in
                #   a different thread
                # followed by an access violation that killed the process.
                # It stayed hidden while micromamba resolved to nothing and
                # the function returned before reaching this branch; making
                # conda findable is what finally walked into it. The prompt
                # now happens before the job starts (see _tc_uninstall).
                try:
                    from src.core.micromamba_installer import get_micromamba_exe
                    _mamba_exe = get_micromamba_exe()
                    if _mamba_exe and os.path.isfile(str(_mamba_exe)):
                        os.remove(str(_mamba_exe))
                    # Also remove the managed dir if empty
                    _mamba_dir = os.path.dirname(str(_mamba_exe)) if _mamba_exe else None
                    if _mamba_dir and os.path.isdir(_mamba_dir):
                        import shutil as _sh
                        _sh.rmtree(_mamba_dir, ignore_errors=True)
                    # Every other exit from _do returns (ok, message);
                    # this one returned a bare True, so the worker died on
                    #   TypeError: cannot unpack non-iterable bool object
                    # It went unnoticed for as long as micromamba resolved
                    # to nothing and this branch was never entered.
                    return True, "Conda (micromamba) removed"
                except Exception as e:
                    return False, str(e)

            # For uv/poetry/pipx: try direct binary removal first (curl-installed)
            # then fall back to pip uninstall --break-system-packages
            _local_bin_candidates = {
                "uv": [
                    os.path.join(_home, ".local", "bin", "uv"),
                    os.path.join(_home, ".cargo", "bin", "uv"),
                ],
                "poetry": [
                    os.path.join(_home, ".local", "share", "pypoetry", "bin", "poetry"),
                    os.path.join(_home, ".local", "bin", "poetry"),
                ],
                "pipx": [
                    os.path.join(_home, ".local", "bin", "pipx"),
                ],
            }
            # 1. Try direct binary removal for user-installed tools
            for _cand in _local_bin_candidates.get(tool, []):
                if _tool_exe and os.path.normpath(_tool_exe) == os.path.normpath(_cand):
                    if os.path.isfile(_cand):
                        try:
                            os.remove(_cand)
                            # Also remove poetry home dir if it exists
                            if tool == "poetry":
                                import shutil as _sh
                                _poetry_home = os.path.join(_home, ".local", "share", "pypoetry")
                                if os.path.isdir(_poetry_home):
                                    _sh.rmtree(_poetry_home, ignore_errors=True)
                            return True, f"{tool} removed successfully"
                        except Exception as _e:
                            pass

            # 2. If tool is in a global/system path — try elevated removal
            _win_global = sys.platform == "win32" and any(
                _tool_exe.lower().startswith(p.lower()) for p in (
                    os.environ.get("ProgramFiles", "C:\\Program Files"),
                    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                    os.environ.get("ProgramData", "C:\\ProgramData"),
                    os.environ.get("SystemRoot", "C:\\Windows"),
                )
            ) if _tool_exe else False
            _linux_global = sys.platform != "win32" and _tool_exe and any(
                _tool_exe.startswith(p) for p in ("/usr/bin/", "/usr/local/bin/", "/bin/", "/opt/")
            )
            # N64: a system-located tool is simply not ours to remove.
            #
            # This block used to elevate -- UAC + Remove-Item on Windows,
            # pkexec + pacman or `rm -f` on Linux -- and when that failed it
            # dumped a terminal command on the user. Every path was wrong for
            # a desktop app: it silently deleted files owned by the system
            # package manager when it worked, and blamed the user when it did
            # not. Whoever installed it there manages it there. Rows for these
            # tools no longer offer Remove at all, so this is only reached if
            # something slipped through.
            if _win_global or _linux_global:
                return False, (
                    f"{tool} is installed in a system location:\n{_tool_exe}\n\n"
                    f"VenvStudio only manages per-user installs. Use whatever "
                    f"put it there \u2014 your system package manager, or an "
                    f"elevated terminal \u2014 to remove it.")

            # 3. Tools with no pip package (pixi, venv, micromamba) come from
            #    their own installer, so there is nothing for pip to uninstall.
            #    Feeding pkg=None to subprocess produced
            #        TypeError: expected str, bytes or os.PathLike object,
            #        not NoneType
            #    from list2cmdline, which surfaced as a bare "Error:" box.
            #    (Bayram, 2026-08-25.) Remove the launcher instead, and say
            #    plainly what is left behind rather than deleting a whole tree
            #    the user did not ask us to touch.
            if not pkg:
                if not _tool_exe or not os.path.isfile(_tool_exe):
                    return False, f"{tool} has no executable to remove."
                try:
                    os.remove(_tool_exe)
                except OSError as e:
                    return False, f"Could not remove {_tool_exe}:\n{e}"
                _home_dir = os.path.dirname(os.path.dirname(_tool_exe))
                _extra = ""
                if os.path.basename(_home_dir).lower() in (f".{tool}", tool):
                    _extra = (f"\n\nIts data directory is still there:\n{_home_dir}\n"
                              f"Delete it yourself if you want the environments "
                              f"and cached packages gone too.")
                _log.info(f"[TC] removed launcher {_tool_exe}")
                return True, f"{tool} removed ({_tool_exe}){_extra}"

            # 4. Fallback: pip uninstall with --break-system-packages
            cmd = [py_exe, "-m", "pip", "uninstall", pkg, "-y", "-q"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                               cwd=_home, **subprocess_args())
            if r.returncode != 0 and "externally-managed" in (r.stderr or r.stdout or ""):
                cmd += ["--break-system-packages"]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                   cwd=_home, **subprocess_args())
            if r.returncode != 0:
                return False, (r.stderr or r.stdout)[:200]
            return True, f"{tool} removed successfully"

        def _done(ok, res):
            self._tc_end_job()
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QMessageBox
            si2 = tbl.item(row, 1)
            if not ok:
                # Re-scan rather than guessing. This branch used to hardcode
                # "System" on any failure, which silently RELABELLED a
                # per-user tool as a system one -- hatch showed User until
                # Remove failed once, then read System from then on and the
                # row lost its buttons. A failed removal tells us nothing
                # about where the tool lives; ask again. (2026-08-25)
                QMessageBox.information(None, "Cannot Remove Automatically", res)
                QTimer.singleShot(0, lambda: self._tc_load_table(py_exe, force=True))
                return
            QTimer.singleShot(300, lambda: self._tc_load_table(py_exe, force=True))

        if not self._tc_begin_job("upgrade"):
            return
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
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
                    **subprocess_args(capture_output=True, text=True, timeout=8), cwd=__import__('os').path.expanduser('~'))
            elif tool == "pip":
                r = subprocess.run([py, "-m", "pip", "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=8), cwd=__import__('os').path.expanduser('~'))
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
                        **subprocess_args(capture_output=True, text=True, timeout=8), cwd=__import__('os').path.expanduser('~'))
                else:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Not Found", "micromamba not installed. Use Download.")
                    return
            elif exe:
                r = subprocess.run([exe, "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=8), cwd=__import__('os').path.expanduser('~'))
            else:
                r = subprocess.run([py, "-m", tool, "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=8), cwd=__import__('os').path.expanduser('~'))
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
            self._tc_end_job()
            from PySide6.QtGui import QColor
            from PySide6.QtCore import QTimer as _QT
            if ok:
                # N67: rescan instead of hand-painting cells.
                # This callback used to set only Status and Path, leaving
                # Version at "—" and the button still reading Install --
                # so a successful conda download looked like it had done
                # nothing. Every other job in this file finishes by
                # reloading the table, which fills all five columns and
                # swaps the buttons; this one was the exception.
                # Same source the rest of the panel uses for "which Python".
                _py = ""
                try:
                    _py = self._tc_py_combo.currentData() or ""
                except Exception:
                    pass
                if not _py:
                    import sys as _sys5
                    _py = _sys5.executable
                _QT.singleShot(0, lambda: self._tc_load_table(_py, force=True))
                return
            si=tbl.item(row,1)
            if si:
                si.setText(f"❌ {res[:40]}"); si.setForeground(QColor("#f38ba8"))
        if not self._tc_begin_job("operation"):
            return
        from src.gui.package_panel import WorkerThread
        w=WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
        if not hasattr(self,"_tc_ws"): self._tc_ws=[]
        self._tc_ws.append(w)


    # ─────────────────────────────────────────────────────────────────────
    # UI section builders (moved from settings_page.py)
    # ─────────────────────────────────────────────────────────────────────

    def _setup_toolchain_ui_section(self, layout):
        # ── 5b. TOOLCHAIN MANAGER ──────────────────────────────────────────
        if not hasattr(self, "_tc_built"):
            self._tc_built = True
            self._build_toolchain_ui(layout)


    def _setup_cliops_section(self, layout):
        # ── CLI/TUI OPERATIONS ──────────────────────────────────────────────────
        ops_group = QGroupBox("🎨 Themes")
        ops_layout = QVBoxLayout()
        ops_layout.setSpacing(10)

        # ── Default Terminal ──
        from src.core.cli_tools_manager import TERMINAL_APPS, get_terminal_version
        terminal_row = QHBoxLayout()
        self.terminal_cb = QCheckBox()
        self.terminal_cb.setChecked(False)
        self.terminal_cb.toggled.connect(lambda on: self.terminal_combo.setEnabled(on))
        terminal_row.addWidget(self.terminal_cb)

        self.terminal_combo = NoScrollComboBox()
        self.terminal_combo.setEnabled(False)
        _platform = get_platform()
        if _platform == "windows":
            import os as _os2, shutil as _sh2
            # Windows PowerShell (5.1, ships with Windows) — always present
            self.terminal_combo.addItem("Windows PowerShell", "powershell")
            # PowerShell 7+ (pwsh.exe) — cross-version: detect by executable,
            # not a hardcoded version, so pwsh 7/8/9 all work. Installed via
            # MSI/winget/store; lives on PATH as pwsh.exe.
            _pwsh = _sh2.which("pwsh") or _sh2.which("pwsh.exe")
            if _pwsh:
                self.terminal_combo.addItem("PowerShell 7+", "pwsh")
            self.terminal_combo.addItem("CMD", "cmd")
            self.terminal_combo.addItem("Windows Terminal", "wt")
            _git_paths = [
                r"C:/Program Files/Git/bin/bash.exe",
                r"C:/Program Files (x86)/Git/bin/bash.exe",
                _os2.path.join(_os2.environ.get("LOCALAPPDATA",""), "Programs","Git","bin","bash.exe"),
            ]
            if any(_os2.path.isfile(p) for p in _git_paths) or _sh2.which("git-bash"):
                self.terminal_combo.addItem("Git Bash", "git-bash")
        elif _platform == "macos":
            self.terminal_combo.addItem("Terminal", "terminal")
            self.terminal_combo.addItem("iTerm2", "iterm2")
        else:
            self.terminal_combo.addItem("System Default", "default")
            for _t in [("GNOME Terminal","gnome-terminal"),("Konsole","konsole"),
                       ("Xfce4 Terminal","xfce4-terminal"),("Tilix","tilix"),
                       ("Mate Terminal","mate-terminal"),("Alacritty","alacritty"),
                       ("Kitty","kitty"),("WezTerm","wezterm"),("xterm","xterm")]:
                self.terminal_combo.addItem(_t[0], _t[1])

        for _tid, _tdata in TERMINAL_APPS.items():
            if self.terminal_combo.findData(_tid) < 0 and get_terminal_version(_tid):
                self.terminal_combo.addItem(_tdata["name"], _tid)

        terminal_row.addWidget(self.terminal_combo, 1)

        if _platform == "linux":
            _detect_btn = QPushButton("🔍 Detect")
            _detect_btn.setObjectName("secondary")
            _detect_btn.setFixedWidth(90)
            _detect_btn.clicked.connect(self._detect_terminals)
            terminal_row.addWidget(_detect_btn)

        _term_form = QFormLayout()
        _term_form.addRow(f"{tr('default_terminal')}", terminal_row)
        ops_layout.addLayout(_term_form)

        # ── Install Terminal Emulators ──
        _sep1 = QFrame(); _sep1.setFrameShape(QFrame.HLine)
        _sep1.setStyleSheet(f"background: {self._c()['border']}; max-height:1px; margin:4px 0;")
        ops_layout.addWidget(_sep1)

        _inst_lbl = QLabel("  🖥️  Install Terminal Emulators")
        _inst_lbl.setStyleSheet(f"color:{self._c()['fg']}; font-size:{self._c()['fs_small']}px; font-weight:bold;")
        ops_layout.addWidget(_inst_lbl)
        _inst_desc = QLabel("WezTerm, Alacritty, Tabby, Ghostty, Hyper — all platforms.")
        _inst_desc.setStyleSheet(f"color:{self._c()['fg_muted']}; font-size:{self._c()['fs_tiny']}px;")
        ops_layout.addWidget(_inst_desc)

        _tsel_row = QHBoxLayout()
        self.term_selector = QComboBox()
        self.term_selector.setStyleSheet(
            f"QComboBox{{background:{self._c()['card']};color:{self._c()['fg']};"
            f"border:1px solid {self._c()['border']};border-radius:4px;"
            f"padding:4px 10px;font-size:{self._c()['fs_small']}px;}}"
        )
        for _tid, _tdata in TERMINAL_APPS.items():
            _ver = get_terminal_version(_tid)
            _suf = f"  ✅ {_ver.split()[0]}" if _ver else ""
            self.term_selector.addItem(f"{_tdata['icon']} {_tdata['name']}{_suf}", _tid)

        self.term_install_cb = QCheckBox()
        self.term_install_cb.setToolTip("Enable terminal installer")
        self.term_selector.setEnabled(False)
        self.term_install_cb.toggled.connect(self.term_selector.setEnabled)
        self.term_install_cb.toggled.connect(self._on_term_selector_toggled)
        _tsel_row.addWidget(self.term_install_cb)
        _tsel_row.addWidget(self.term_selector, 1)
        _tsel_row.addStretch()
        ops_layout.addLayout(_tsel_row)

        from PySide6.QtWidgets import QStackedWidget as _SW3
        self.term_stack = _SW3()
        self.term_stack.setVisible(False)
        self.term_selector.currentIndexChanged.connect(self.term_stack.setCurrentIndex)
        self.term_install_cb.toggled.connect(self.term_stack.setVisible)
        for _tid, _tdata in TERMINAL_APPS.items():
            self.term_stack.addWidget(self._make_terminal_card(_tid, _tdata))
        ops_layout.addWidget(self.term_stack)

        # ── Custom Terminals ──
        _sep2 = QFrame(); _sep2.setFrameShape(QFrame.HLine)
        _sep2.setStyleSheet(f"background:{self._c()['border']}; max-height:1px; margin:4px 0;")
        ops_layout.addWidget(_sep2)

        custom_term_group = QGroupBox("🖥️ Custom Terminals")
        custom_term_layout = QVBoxLayout()
        custom_term_layout.setSpacing(8)

        info_lbl = QLabel("Add custom terminal commands. Use {path} for env path and {activate} for activate script.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        custom_term_layout.addWidget(info_lbl)

        self.custom_term_table = QTableWidget(0, 3)
        self.custom_term_table.setHorizontalHeaderLabels(["Name", "Command", "Enabled"])
        self.custom_term_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.custom_term_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.custom_term_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.custom_term_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.custom_term_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.custom_term_table.setMaximumHeight(180)
        custom_term_layout.addWidget(self.custom_term_table)

        btn_row = QHBoxLayout()
        add_term_btn = QPushButton("➕ Add"); add_term_btn.setObjectName("secondary")
        add_term_btn.clicked.connect(self._add_custom_terminal)
        edit_term_btn = QPushButton("✏️ Edit"); edit_term_btn.setObjectName("secondary")
        edit_term_btn.clicked.connect(self._edit_custom_terminal)
        del_term_btn = QPushButton("🗑️ Remove"); del_term_btn.setObjectName("danger")
        del_term_btn.clicked.connect(self._remove_custom_terminal)
        btn_row.addWidget(add_term_btn); btn_row.addWidget(edit_term_btn)
        btn_row.addWidget(del_term_btn); btn_row.addStretch()
        custom_term_layout.addLayout(btn_row)
        custom_term_group.setLayout(custom_term_layout)
        ops_layout.addWidget(custom_term_group)

        # ── Separator ──
        _sep3 = QFrame(); _sep3.setFrameShape(QFrame.HLine)
        _sep3.setStyleSheet(f"background:{self._c()['border']}; max-height:1px; margin:4px 0;")
        ops_layout.addWidget(_sep3)

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
        ops_layout.addWidget(font_group)

        # ── Noto Color Emoji ──
        if sys.platform == "linux":
            emoji_group = QGroupBox("😀 Noto Color Emoji Font")
            emoji_inner = QHBoxLayout()
            emoji_inner.setSpacing(8)

            emoji_label = QLabel("Required for emoji icons (🔄 ⭐ 📁 🐍) to display correctly.")
            emoji_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
            emoji_label.setWordWrap(True)
            emoji_inner.addWidget(emoji_label, 1)

            self._install_emoji_btn = QPushButton("⬇️ Install Noto Color Emoji")
            self._install_emoji_btn.setObjectName("secondary")
            self._install_emoji_btn.clicked.connect(self._install_noto_emoji)
            emoji_inner.addWidget(self._install_emoji_btn)

            emoji_group.setLayout(emoji_inner)
            ops_layout.addWidget(emoji_group)

        # ── Tool selector dropdown ──
        from src.core.cli_tools_manager import (
            STARSHIP_PRESETS, STARSHIP_PRESET_NAMES, OMP_THEMES, is_tool_installed
        )

        _tool_selector_row = QHBoxLayout()
        _tool_selector_lbl = QLabel("🛠 CLI / TUI Tools:")
        _tool_selector_lbl.setStyleSheet(f"font-size: {self._c()['fs_small']}px; color: {self._c()['fg']}; font-weight: bold;")
        _tool_selector_row.addWidget(_tool_selector_lbl)

        self.cli_tool_selector = QComboBox()
        self.cli_tool_selector.setStyleSheet(
            f"QComboBox {{ background: {self._c()['card']}; color: {self._c()['fg']}; "
            f"border: 1px solid {self._c()['border']}; border-radius: 4px; "
            f"padding: 4px 10px; font-size: {self._c()['fs_small']}px; min-width: 220px; }}"
        )
        _tools = [
            ("oh-my-posh",      "🎨 Oh My Posh"),
            ("starship",        "🚀 Starship"),
            ("rich",            "✨ Rich"),
            ("textual",         "🖼️ Textual"),
            ("prompt_toolkit",  "⌨️ Prompt Toolkit"),
        ]
        for _tid, _tname in _tools:
            _installed = is_tool_installed(_tid)
            _suffix = " ✅" if _installed else ""
            self.cli_tool_selector.addItem(f"{_tname}{_suffix}", _tid)

        self.cli_tool_selector.setEnabled(False)

        # ── Tool card stack — must be created before checkbox connects to it ──
        from PySide6.QtWidgets import QStackedWidget
        self.cli_tool_stack = QStackedWidget()

        self.cli_tool_cb = QCheckBox()
        self.cli_tool_cb.setToolTip("Enable tool selector")
        self.cli_tool_cb.toggled.connect(self.cli_tool_selector.setEnabled)
        self.cli_tool_cb.toggled.connect(self.cli_tool_stack.setVisible)
        _tool_selector_row.insertWidget(0, self.cli_tool_cb)
        _tool_selector_row.addWidget(self.cli_tool_selector, 1)
        _tool_selector_row.addStretch()
        ops_layout.addLayout(_tool_selector_row)

        self.cli_tool_stack.addWidget(self._make_cli_card(
            "oh-my-posh", "🎨 Oh My Posh",
            "A prompt theme engine for any shell",
            "Theme:", OMP_THEMES, "theme"
        ))
        self.cli_tool_stack.addWidget(self._make_cli_card(
            "starship", "🚀 Starship",
            "The minimal, blazing-fast, and infinitely customizable prompt for any shell",
            "Preset:", STARSHIP_PRESET_NAMES, "preset",
            preset_descriptions=STARSHIP_PRESETS
        ))
        self.cli_tool_stack.addWidget(self._make_pip_card(
            "rich", "✨ Rich",
            "Rich text and beautiful formatting in the terminal",
        ))
        self.cli_tool_stack.addWidget(self._make_pip_card(
            "textual", "🖼️ Textual",
            "Rapid framework for terminal-based user interfaces (TUI)",
        ))
        self.cli_tool_stack.addWidget(self._make_pip_card(
            "prompt_toolkit", "⌨️ Prompt Toolkit",
            "Library for building interactive CLI applications",
        ))

        self.cli_tool_selector.currentIndexChanged.connect(self.cli_tool_stack.setCurrentIndex)
        self.cli_tool_stack.setCurrentIndex(0)
        self.cli_tool_stack.setVisible(False)
        ops_layout.addWidget(self.cli_tool_stack)

        # ── Launch Settings ──
        _sep4 = QFrame(); _sep4.setFrameShape(QFrame.HLine)
        _sep4.setStyleSheet(f"background:{self._c()['border']}; max-height:1px; margin:4px 0;")
        ops_layout.addWidget(_sep4)

        launch_group = QGroupBox("🚀 Launch Settings")
        launch_layout = QFormLayout()
        launch_layout.setSpacing(12)

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
        self.jupyter_custom_path_label.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;"
        )
        self.jupyter_custom_path_label.setVisible(False)
        launch_layout.addRow("", self.jupyter_custom_path_label)

        launch_group.setLayout(launch_layout)
        ops_layout.addWidget(launch_group)

        ops_group.setLayout(ops_layout)
        layout.addWidget(ops_group)

