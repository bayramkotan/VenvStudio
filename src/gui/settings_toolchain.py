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
from src.utils.constants import APP_NAME, APP_VERSION
from src.utils.i18n import tr
import os, subprocess, shutil
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
                # PEP 668 system — strategy depends on scope
                pm = _detect_pm()
                if scope == "user":
                    # USER install — never use sudo/pkexec, just pip --user or official installer
                    if tool == "uv":
                        r = subprocess.run([sys.executable, "-m", "pip", "install", "uv",
                                            "--break-system-packages", "--user", "-q"],
                                           capture_output=True, text=True, timeout=120)
                        if r.returncode != 0:
                            r = subprocess.run(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                                               capture_output=True, text=True, timeout=120)
                            if r.returncode != 0: return False, r.stderr[:200]
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
                    # SYSTEM install — use pkexec/pacman
                    _pkexec = shutil.which("pkexec") or ""
                    _pkg_cmds = {
                        "apt":    ["apt", "install", "-y", pkg],
                        "pacman": ["pacman", "-S", "--noconfirm",
                                   {"pipx": "python-pipx", "poetry": "python-poetry"}.get(tool, tool)],
                        "dnf":    ["dnf", "install", "-y", pkg],
                        "zypper": ["zypper", "install", "-y", pkg],
                    }
                    if pm in _pkg_cmds:
                        _cmd = ([_pkexec] if _pkexec else ["sudo"]) + _pkg_cmds[pm]
                        r = subprocess.run(_cmd, capture_output=True, text=True, timeout=120)
                        if r.returncode != 0: return False, r.stderr[:200]
                    else:
                        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                                            "--break-system-packages", "-q"],
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
        found = next((c for c in cands if c and os.path.isfile(c)), "")
        if found:
            return found
        # Fallback: check if tool is available as python module (e.g. python3 -m pipx)
        try:
            import subprocess
            r = subprocess.run([py_exe, "-m", tool, "--version"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return py_exe  # signals "available as module"
        except Exception:
            pass
        return ""


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
                _log.warning(f"🧰 [TC] _done called with ok=False, result={result[:120]!r}")
                return
            try:
                data = json.loads(result)
                _py = data["py"]
                rows = data["rows"]
            except Exception as e:
                _log.warning(f"🧰 [TC] JSON parse error: {e!r}, result={result[:120]!r}")
                return
            _log.debug(f"🧰 [TC] _done: {len(rows)} rows loaded for {_py[:40]}")
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

                # col 3: Path — if path == py_exe, tool is module-only, show real module path
                import os as _os2
                _display_path = path
                if ok2 and _os2.path.normpath(path) == _os2.path.normpath(_py):
                    # Get real location via pip show
                    try:
                        import subprocess as _sp_path
                        _pr = _sp_path.run([_py, "-m", "pip", "show", _tid],
                                           capture_output=True, text=True, timeout=5)
                        _loc = next((l.split(":", 1)[1].strip()
                                     for l in _pr.stdout.splitlines()
                                     if l.startswith("Location:")), "")
                        if _loc:
                            import importlib.util as _iu
                            _spec = _iu.find_spec(_tid.replace("-", "_"))
                            if _spec and _spec.origin:
                                _display_path = _os2.path.dirname(_spec.origin)
                            else:
                                _display_path = _os2.path.join(_loc, _tid)
                        else:
                            _display_path = path
                    except Exception:
                        _display_path = path
                pi = QTableWidgetItem(_display_path if ok2 else "—")
                pi.setForeground(QColor(self._c()["fg_muted"]))
                pi.setToolTip(path)
                tbl.setItem(row, 3, pi)

                # Update action buttons
                self._tc_update_row_btns(tbl, row, ok2)

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
        if not hasattr(self,"_tc_ws"): self._tc_ws=[]
        self._tc_ws.append(w)

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

        from src.gui.package_panel import WorkerThread
        w = WorkerThread(_do, parent=self); w.finished.connect(_done); w.start()
        if not hasattr(self, "_tc_ws"): self._tc_ws = []
        self._tc_ws.append(w)

    def _tc_do_install(self, tool, pkg, scope, tbl, row):
        import sys, os
        from PySide6.QtGui import QColor

        # B: 'venv' has pkg=None (it's part of the Python stdlib, not a
        # separately pip-installable package) — installing/upgrading it
        # would crash subprocess.run() with a None arg. Guard it here,
        # consistent with the existing guard in _tc_do_remove.
        if tool == "venv" or not pkg:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Nothing to install",
                f"'{tool}' is part of the Python standard library — "
                f"it cannot be installed or upgraded separately."
            )
            return

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
                            _bsp3 = ["--break-system-packages"] if _is_linux else []
                            r = subprocess.run(
                                [py_exe, "-m", "pip", "install", pkg, "--user", "-q"] + _bsp3,
                                **subprocess_args(capture_output=True, text=True, timeout=120),
                                cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    elif tool == "pipx":
                        _bsp = ["--break-system-packages"] if _is_linux else []
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", "pipx", "--user", "-q"] + _bsp,
                            **subprocess_args(capture_output=True, text=True, timeout=120),
                            cwd=_home, **_spa())
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "failed")[:300]
                    else:
                        _bsp2 = ["--break-system-packages"] if _is_linux else []
                        r = subprocess.run(
                            [py_exe, "-m", "pip", "install", pkg, "--user", "-q"] + _bsp2,
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
        if si: si.setText("⏳ Removing..."); si.setForeground(QColor("#89b4fa"))
        _home = __import__("os").path.expanduser("~")

        def _do(callback=None):
            import subprocess, os
            from src.utils.platform_utils import subprocess_args
            # Build correct remove command per tool
            # Find the tool's own executable first
            _tool_exe = _shutil.which(tool) or _shutil.which(tool + ".exe")
            # If tool is only available as module (python -m tool), handle specially
            if not _tool_exe:
                import subprocess as _sp2
                r2 = _sp2.run([py_exe, "-m", tool, "--version"],
                              capture_output=True, text=True, timeout=5)
                if r2.returncode == 0:
                    # Module-only install — find via pip show
                    _loc_r = _sp2.run([py_exe, "-m", "pip", "show", tool],
                                      capture_output=True, text=True, timeout=10)
                    _loc = next((l.split(":", 1)[1].strip()
                                 for l in _loc_r.stdout.splitlines()
                                 if l.startswith("Location:")), "")
                    _pm = next((p for p in ("apt","pacman","dnf","zypper") if _shutil.which(p)), None)
                    _pacman_map = {"pipx": "python-pipx", "uv": "uv", "poetry": "python-poetry"}
                    # Try pkexec pip uninstall (graphical auth, works on all distros)
                    _pkexec2 = _shutil.which("pkexec") or ""
                    _uninstall_cmd = ([_pkexec2] if _pkexec2 else ["sudo"]) + [
                        py_exe, "-m", "pip", "uninstall", tool,
                        "--break-system-packages", "-y"
                    ]
                    try:
                        r3 = _sp2.run(_uninstall_cmd, capture_output=True, text=True, timeout=60)
                        if r3.returncode == 0:
                            return True, f"{tool} removed successfully"
                    except Exception:
                        pass
                    return False, (
                        f"{tool} is installed as a Python module.\n\n"
                        f"Run in terminal to remove:\n"
                        f"  sudo pip uninstall {tool} --break-system-packages"
                    )
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
            if _win_global or _linux_global:
                _pacman_pkgs = {"uv": "uv", "poetry": "python-poetry", "pipx": "python-pipx"}
                if _win_global:
                    # Windows: UAC elevation via PowerShell RunAs
                    try:
                        import ctypes
                        _ps_cmd = f'Remove-Item -Force "{_tool_exe}"'
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", "powershell.exe",
                            f'-NoProfile -Command "{_ps_cmd}"', None, 1)
                        if ret > 32:
                            import time; time.sleep(2)
                            if not os.path.isfile(_tool_exe):
                                return True, f"{tool} removed from {_tool_exe}"
                    except Exception:
                        pass
                    return False, (
                        f"{tool} is system-installed at {_tool_exe}\n\n"
                        f"Run in PowerShell (as Administrator):\n"
                        f'  Remove-Item -Force "{_tool_exe}"'
                    )
                # Linux global
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
                if _shutil.which("pkexec"):
                    try:
                        r = subprocess.run(["pkexec", "rm", "-f", _tool_exe],
                                           capture_output=True, text=True, timeout=60)
                        if r.returncode == 0:
                            return True, f"{tool} removed from {_tool_exe}"
                    except Exception:
                        pass
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
                # Restore original status instead of showing error in status col
                if si2:
                    si2.setText("🌐 Global")
                    si2.setForeground(QColor("#89b4fa"))
                QMessageBox.information(None, "Cannot Remove Automatically", res)
                return
            QTimer.singleShot(300, lambda: self._tc_load_table(py_exe))

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

