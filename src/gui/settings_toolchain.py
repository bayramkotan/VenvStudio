"""VenvStudio - Settings: ToolchainMixin"""
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

            if scope == "system" and sys.platform == "win32":
                try:
                    import ctypes
                    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f"-m pip install {pkg} -q", None, 1)
                    if ret <= 32: return False, f"UAC failed (code {ret})"
                    import time; time.sleep(4)
                except Exception as e:
                    return False, f"UAC error: {e}"
            elif sys.platform != "win32" and _is_ext_managed():
                # PEP 668 — use platform package manager or official installers
                pm = _detect_pm()
                if tool == "uv":
                    # Try pacman first on Arch, else pip --break-system-packages, else curl
                    _installed_uv = False
                    if pm == "pacman" and shutil.which("pacman"):
                        r = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "uv"],
                                           capture_output=True, text=True, timeout=120)
                        _installed_uv = r.returncode == 0
                    if not _installed_uv:
                        r = subprocess.run([sys.executable, "-m", "pip", "install", "uv",
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        _installed_uv = r.returncode == 0
                    if not _installed_uv:
                        r = subprocess.run(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0: return False, r.stderr[:200]
                elif tool == "poetry":
                    _installed_poetry = False
                    _pipx = shutil.which("pipx")
                    if _pipx:
                        r = subprocess.run([_pipx, "install", "poetry"],
                                           capture_output=True, text=True, timeout=180)
                        _installed_poetry = r.returncode == 0
                    if not _installed_poetry:
                        r = subprocess.run(["sh", "-c", "curl -sSL https://install.python-poetry.org | python3 -"],
                                           capture_output=True, text=True, timeout=180,
                                           env={**os.environ, "POETRY_HOME": os.path.expanduser("~/.local/share/pypoetry")})
                        if r.returncode != 0: return False, r.stderr[:200]
                elif tool == "pipx":
                    installed = False
                    if pm == "apt":
                        r = subprocess.run(["sudo", "apt", "install", "-y", "pipx"], capture_output=True, text=True, timeout=120)
                        installed = r.returncode == 0
                    elif pm == "pacman":
                        r = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "python-pipx"], capture_output=True, text=True, timeout=120)
                        installed = r.returncode == 0
                    elif pm == "dnf":
                        r = subprocess.run(["sudo", "dnf", "install", "-y", "pipx"], capture_output=True, text=True, timeout=120)
                        installed = r.returncode == 0
                    elif pm == "zypper":
                        r = subprocess.run(["sudo", "zypper", "install", "-y", "python3-pipx"], capture_output=True, text=True, timeout=120)
                        installed = r.returncode == 0
                    if not installed:
                        r = subprocess.run([sys.executable, "-m", "pip", "install", "pipx",
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0: return False, r.stderr[:200]
                else:
                    r = subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                                        "--break-system-packages", "--user", "-q"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode != 0: return False, r.stderr[:200]
            elif scope == "system":
                r = subprocess.run(["sudo", sys.executable, "-m", "pip", "install", pkg, "-q"],
                                   **subprocess_args(capture_output=True, text=True, timeout=120))
                if r.returncode != 0: return False, (r.stderr or "failed")[:200]
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
                btn.setText(f"Install {tool} ({'User' if scope == 'user' else 'System 🔒'})")
        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do)
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
            # pip/venv: install_user is repurposed as Upgrade — hide upgrade_user
            if "install_user" in btns: btns["install_user"].setVisible(True)
            if "upgrade_user" in btns: btns["upgrade_user"].setVisible(False)
            if "rm_user" in btns: btns["rm_user"].setVisible(False)
        elif installed:
            if "install_user" in btns: btns["install_user"].setVisible(False)
            if "upgrade_user" in btns: btns["upgrade_user"].setVisible(True)
            # Hide Remove for system-wide (global) installs — can't remove without sudo
            _path_item = tbl.item(row, 3) if tbl.columnCount() > 3 else None
            _tool_path = _path_item.text() if _path_item else ""
            _is_global = any(_tool_path.startswith(p) for p in (
                "/usr/bin/", "/usr/local/bin/", "/bin/", "/opt/",
            )) if _tool_path else False
            if "rm_user" in btns:
                if _is_global:
                    btns["rm_user"].setVisible(False)
                else:
                    btns["rm_user"].setVisible(True)
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
                                    ver = p.rstrip(","); break
                        else:
                            r = subprocess.run([path, "--version"],
                                **subprocess_args(capture_output=True, text=True, timeout=5), cwd=__import__('os').path.expanduser('~'))
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
                if ok2:
                    if _tid in ("pip", "venv"):
                        st_text = "✅ Built-in"
                        st_color = "#a6e3a1"
                    elif _is_managed:
                        st_text = "📦 Managed"
                        st_color = "#cba6f7"
                    elif _is_global_path:
                        st_text = "🌐 Global"
                        st_color = "#89b4fa"
                    elif _is_user:
                        st_text = "👤 User"
                        st_color = "#a6e3a1"
                    elif _is_python_local:
                        st_text = "🐍 Python"
                        st_color = "#f9e2af"
                    else:
                        st_text = "✅ Installed"
                        st_color = "#a6e3a1"
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
                        **subprocess_args(capture_output=True, text=True, timeout=120),
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
                                **subprocess_args(capture_output=True, text=True, timeout=120), cwd=_home)
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
                                **subprocess_args(capture_output=True, text=True, timeout=120),
                                cwd=_home, **_spa())
                        else:
                            r = subprocess.run(
                                [py_exe, "-m", "pip", "install", pkg, "--user", "-q"],
                                **subprocess_args(capture_output=True, text=True, timeout=120),
                                cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    elif tool == "pipx":
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", "pipx", "--user", "-q"],
                            **subprocess_args(capture_output=True, text=True, timeout=120),
                            cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    else:
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", pkg, "--user", "-q"],
                            **subprocess_args(capture_output=True, text=True, timeout=120),
                            cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]

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
            if tool in ("pip", "venv"):
                return False, f"{tool} cannot be removed — it is a core Python component"
            elif tool == "micromamba":
                return False, "micromamba is a standalone binary — delete it manually from its install path"

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

            # 2. If tool is in a global/system path — try pkexec/pacman, else show message
            _global_prefixes = ("/usr/bin/", "/usr/local/bin/", "/bin/", "/opt/")
            if _tool_exe and any(_tool_exe.startswith(p) for p in _global_prefixes):
                _pacman_pkgs = {"uv": "uv", "poetry": "python-poetry", "pipx": "python-pipx"}
                # On Arch/CachyOS: try pkexec pacman -R (graphical auth)
                if _shutil.which("pacman") and tool in _pacman_pkgs:
                    _pkexec = _shutil.which("pkexec") or ""
                    _rm_cmd = (
                        [_pkexec, "pacman", "-R", "--noconfirm", _pacman_pkgs[tool]]
                        if _pkexec else
                        ["sudo", "pacman", "-R", "--noconfirm", _pacman_pkgs[tool]]
                    )
                    try:
                        r = subprocess.run(_rm_cmd, capture_output=True, text=True, timeout=60)
                        if r.returncode == 0:
                            return True, f"{tool} removed via pacman"
                    except Exception:
                        pass
                # Try pkexec rm (graphical sudo)
                if _shutil.which("pkexec"):
                    try:
                        r = subprocess.run(["pkexec", "rm", "-f", _tool_exe],
                                           capture_output=True, text=True, timeout=60)
                        if r.returncode == 0:
                            return True, f"{tool} removed from {_tool_exe}"
                    except Exception:
                        pass
                # Cannot remove without auth — tell user
                _ph = f"  sudo pacman -R {_pacman_pkgs.get(tool, tool)}" if _shutil.which("pacman") else ""
                return False, (
                    f"{tool} is system-installed at {_tool_exe}\n\n"
                    f"Run in terminal:\n  sudo rm {_tool_exe}"
                    + (f"\n{_ph}" if _ph else "")
                )

            # 3. Fallback: pip uninstall with --break-system-packages
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

