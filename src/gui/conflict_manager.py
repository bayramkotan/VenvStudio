"""VenvStudio — Conflict Manager Dialog
Tools → Conflict Manager: search packages for known compatibility issues.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QSizePolicy, QAbstractItemView, QProgressBar,
    QGroupBox, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QColor

from src.utils.constants import CONFLICT_RULES, CONFLICT_RULES_ALIASES

_ENV_TYPES = ["venv", "uv", "poetry", "conda", "pipx", "hatch", "pdm", "pixi"]

_SEVERITY_COLOR = {
    "error":   ("#f38ba8", "⛔"),
    "warning": ("#f9e2af", "⚠️"),
    "ok":      ("#a6e3a1", "✅"),
}


def _normalize(pkg: str) -> str:
    return pkg.strip().lower().replace("_", "-")


def _lookup(pkg: str):
    key = _normalize(pkg)
    rule_key = CONFLICT_RULES_ALIASES.get(pkg, CONFLICT_RULES_ALIASES.get(key, key))
    return rule_key, CONFLICT_RULES.get(rule_key)


def _check_package(pkg: str, env_type: str, py_ver):
    _, rule = _lookup(pkg)
    if not rule:
        return [("ok", "No known compatibility issues.")]
    issues = []
    sev = rule.get("severity", "warning")
    if py_ver:
        max_py = rule.get("max_python")
        min_py = rule.get("min_python")
        if max_py and py_ver > tuple(int(x) for x in max_py.split(".")):
            issues.append((sev, f"Requires Python ≤ {max_py} (env has Python {py_ver[0]}.{py_ver[1]})"))
        if min_py and py_ver < tuple(int(x) for x in min_py.split(".")):
            issues.append((sev, f"Requires Python ≥ {min_py} (env has Python {py_ver[0]}.{py_ver[1]})"))
    if env_type in rule.get("blocked_envs", []):
        issues.append((sev, f"Not compatible with {env_type} environments."))
    if not issues:
        issues.append(("ok", "No issues for the selected Python/env combination."))
    note = rule.get("note", "")
    if note:
        issues.append(("note", f"ℹ️ {note}"))
    return issues


class _ScanWorker(QThread):
    done = Signal(list)   # list of (pkg_name, issues)

    def __init__(self, pkg_names, env_type, py_ver, parent=None):
        super().__init__(parent)
        self._pkgs    = pkg_names
        self._env_type = env_type
        self._py_ver  = py_ver

    def run(self):
        results = []
        for pkg in self._pkgs:
            issues = _check_package(pkg, self._env_type, self._py_ver)
            # Bayram (2026-08-13): "hepsi gorunsun, ister uyumlu ister
            # uyumsuz" -- show every scanned package's verdict, not just
            # the ones with a problem. This also matters for the planned
            # dependency view (5000+ packages someday): a package with no
            # issues today is still relevant context once its deps show up.
            results.append((pkg, issues))
        self.done.emit(results)


class ConflictManagerDialog(QDialog):

    def __init__(self, parent=None, env_type="venv",
                 py_version=None, installed_packages=None,
                 pip_manager=None):
        super().__init__(parent)
        self.setWindowTitle("🧩 Conflict Manager")
        # QDialog's default flags show only a close button on most
        # platforms. Just OR-ing in the minimize/maximize hints on top
        # of the default Dialog flags (first attempt) made this an
        # "owned" child window of MainWindow -- Windows then minimizes
        # the OWNER along with an owned window to keep them together,
        # so clicking minimize here took VenvStudio down with it
        # (Bayram, 2026-08-13). Setting Qt.Window as the base flag
        # instead of Qt.Dialog makes this a genuinely independent
        # top-level window with its own taskbar entry, so minimize/
        # maximize behave independently of MainWindow.
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.resize(860, 600)
        self._env_type         = env_type
        self._py_ver           = py_version      # (major, minor) or None
        self._installed_pkgs   = installed_packages or []  # list of pkg names
        self._pip_manager      = pip_manager
        self._scan_worker      = None

        self._build_ui()
        self._populate_all_table()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── top bar ───────────────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Env type:"))
        self._env_cb = QComboBox()
        self._env_cb.addItems(_ENV_TYPES)
        if self._env_type in _ENV_TYPES:
            self._env_cb.setCurrentText(self._env_type)
        self._env_cb.setFixedWidth(110)
        bar.addWidget(self._env_cb)

        bar.addSpacing(16)
        bar.addWidget(QLabel("Python:"))
        self._py_cb = QComboBox()
        self._py_cb.setFixedWidth(160)
        self._py_cb.setEditable(False)
        self._populate_python_dropdown()
        bar.addWidget(self._py_cb)

        bar.addStretch()
        self._scan_btn = QPushButton("🔎 Scan Installed Packages")
        self._scan_btn.setToolTip(
            "Check all packages installed in the current environment\n"
            "against known compatibility rules."
        )
        self._scan_btn.setEnabled(bool(self._installed_pkgs or self._pip_manager))
        bar.addWidget(self._scan_btn)
        root.addLayout(bar)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # ── search ────────────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍 Search package:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Type a package name…")
        search_row.addWidget(self._search_edit, 1)
        self._search_btn = QPushButton("Check")
        self._search_btn.setFixedWidth(80)
        search_row.addWidget(self._search_btn)
        root.addLayout(search_row)

        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setTextFormat(Qt.RichText)
        self._result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        root.addWidget(self._result_label)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        root.addWidget(sep2)

        # ── table (all rules + scan results) ──────────────────────────────────
        self._table_label = QLabel("<b>All Known Rules</b> — filtered by selected env / Python:")
        root.addWidget(self._table_label)

        filter_row = QHBoxLayout()
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter by package name…")
        filter_row.addWidget(self._filter_edit, 1)
        self._show_all_btn = QPushButton("Show All")
        self._show_all_btn.setMinimumWidth(90)
        self._show_all_btn.setCheckable(True)
        self._show_all_btn.setChecked(True)
        filter_row.addWidget(self._show_all_btn)
        self._export_btn = QPushButton("📄 Export…")
        self._export_btn.setMinimumWidth(100)
        self._export_btn.setToolTip("Save the table currently shown (Scan Results or All Rules) as CSV or JSON")
        filter_row.addWidget(self._export_btn)
        root.addLayout(filter_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        root.addWidget(self._progress)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Package", "Min Python", "Max Python", "Blocked Envs", "Note"])
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, 1)

        # ── detail panel (Bayram, 2026-08-13: "basit ama bol secenekli" --
        # stays hidden until a row is clicked, so the default view is just
        # the table; clicking a package expands into full explanation +
        # the real install command + directive action buttons) ──
        self._detail_box = QGroupBox("Package Detail")
        self._detail_box.setVisible(False)
        detail_layout = QVBoxLayout(self._detail_box)
        self._detail_label = QLabel("")
        self._detail_label.setWordWrap(True)
        self._detail_label.setTextFormat(Qt.RichText)
        detail_layout.addWidget(self._detail_label)
        self._detail_cmd_label = QLabel("")
        self._detail_cmd_label.setWordWrap(True)
        self._detail_cmd_label.setStyleSheet(
            "font-family: Consolas, monospace; background-color: rgba(255,255,255,20); "
            "padding: 6px; border-radius: 4px;"
        )
        detail_layout.addWidget(self._detail_cmd_label)
        detail_btn_row = QHBoxLayout()
        self._detail_install_btn = QPushButton("🚀 Install")
        self._detail_create_env_btn = QPushButton("🌱 Create New Environment…")
        self._detail_alt_btn = QPushButton("🔄 Try alternative…")
        self._detail_learn_btn = QPushButton("📚 Open in Learn")
        detail_btn_row.addWidget(self._detail_install_btn)
        detail_btn_row.addWidget(self._detail_create_env_btn)
        detail_btn_row.addWidget(self._detail_alt_btn)
        detail_btn_row.addWidget(self._detail_learn_btn)
        detail_btn_row.addStretch()
        detail_layout.addLayout(detail_btn_row)
        root.addWidget(self._detail_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(90)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        # ── connections ───────────────────────────────────────────────────────
        self._search_btn.clicked.connect(self._do_search)
        self._search_edit.returnPressed.connect(self._do_search)
        self._env_cb.currentTextChanged.connect(self._on_context_changed)
        self._py_cb.currentTextChanged.connect(self._on_context_changed)
        self._filter_edit.textChanged.connect(self._populate_all_table)
        self._show_all_btn.toggled.connect(self._populate_all_table)
        self._scan_btn.clicked.connect(self._do_scan)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        self._detail_install_btn.clicked.connect(self._on_detail_install)
        self._detail_create_env_btn.clicked.connect(self._on_detail_create_env)
        self._detail_learn_btn.clicked.connect(self._on_detail_open_learn)
        self._detail_alt_btn.clicked.connect(self._on_detail_try_alternative)
        self._export_btn.clicked.connect(self._on_export)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._populate_all_table)
        self._filter_edit.textChanged.connect(lambda _: self._filter_timer.start())

    # ── Python dropdown ───────────────────────────────────────────────────────

    def _populate_python_dropdown(self):
        """Fill Python dropdown with Python installations from Settings → Python."""
        import subprocess, os
        try:
            from src.utils.platform_utils import find_system_pythons
            system_pythons = find_system_pythons()
        except Exception:
            system_pythons = []

        seen = {}  # version_str -> path (deduplicate)
        for version, path in system_pythons:
            try:
                r = subprocess.run(
                    [str(path), "-c",
                     "import sys; print('%d.%d' % sys.version_info[:2])"],
                    capture_output=True, text=True, timeout=5
                )
                if r.returncode == 0:
                    v = r.stdout.strip()
                    if v not in seen:
                        seen[v] = str(path)
            except Exception:
                pass

        for v in sorted(seen.keys(), reverse=True,
                        key=lambda x: tuple(int(i) for i in x.split("."))):
            self._py_cb.addItem(f"Python {v}", v)

        # Select current env's Python version
        if self._py_ver:
            txt = f"{self._py_ver[0]}.{self._py_ver[1]}"
            for i in range(self._py_cb.count()):
                if self._py_cb.itemData(i) == txt:
                    self._py_cb.setCurrentIndex(i)
                    return
            # Not found — add it
            self._py_cb.insertItem(0, f"Python {txt}", txt)
            self._py_cb.setCurrentIndex(0)
        elif self._py_cb.count() > 0:
            self._py_cb.setCurrentIndex(0)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _current_py_ver(self):
        # itemData stores "X.Y" string; fallback to parsing display text
        data = self._py_cb.currentData()
        txt  = data or self._py_cb.currentText().strip().replace("Python ", "")
        try:
            parts = txt.split(".")
            return (int(parts[0]), int(parts[1]))
        except Exception:
            return None

    def _on_context_changed(self):
        if self._search_edit.text().strip():
            self._do_search()
        self._populate_all_table()

    # ── search ────────────────────────────────────────────────────────────────

    def _do_search(self):
        pkg = self._search_edit.text().strip()
        if not pkg:
            self._result_label.setText("")
            return
        env_type = self._env_cb.currentText()
        py_ver   = self._current_py_ver()
        issues   = _check_package(pkg, env_type, py_ver)
        lines    = [f"<b>Results for <code>{pkg}</code>:</b><br>"]
        for sev, msg in issues:
            col = {"ok": "#a6e3a1", "error": "#f38ba8",
                   "warning": "#f9e2af"}.get(sev, "#89b4fa")
            icon = {"ok": "✅", "error": "⛔", "warning": "⚠️"}.get(sev, "ℹ️")
            lines.append(f'<span style="color:{col}">{icon} {msg}</span><br>')
        self._result_label.setText("".join(lines))

    # ── scan ──────────────────────────────────────────────────────────────────

    def _do_scan(self):
        """Scan installed packages in background thread."""
        self._scan_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate

        # Collect package names
        pkgs = list(self._installed_pkgs)
        if not pkgs and self._pip_manager:
            try:
                pkgs = [p.name for p in self._pip_manager.list_packages()]
            except Exception:
                pass

        env_type = self._env_cb.currentText()
        py_ver   = self._current_py_ver()

        self._scan_worker = _ScanWorker(pkgs, env_type, py_ver, parent=self)
        self._scan_worker.done.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_done(self, results):
        self._scan_btn.setEnabled(True)
        self._progress.setVisible(False)

        if not results:
            # Only reachable now if there were literally no packages to
            # scan (empty env) -- results always has an entry per package
            # since the worker stopped discarding "ok" ones.
            self._table_label.setText(
                "<b>Scan complete</b> — no packages found to check.")
            self._populate_all_table()
            return

        problem_count = sum(
            1 for _, issues in results
            if any(s in ("error", "warning") for s, _ in issues)
        )
        if problem_count:
            self._table_label.setText(
                f"<b>Scan Results</b> — {len(results)} package(s) checked, "
                f"⚠️ {problem_count} with known issues:")
        else:
            self._table_label.setText(
                f"<b>Scan Results</b> — {len(results)} package(s) checked, "
                f"✅ no compatibility issues found.")

        # Bayram (2026-08-13): "hepsi gorunsun, ister uyumlu ister
        # uyumsuz" -- leave the toggle as the user last set it instead of
        # forcing "problems only". The worker now includes every scanned
        # package regardless, so this table already shows everything.
        self._table.setRowCount(len(results))
        for r, (pkg, issues) in enumerate(results):
            worst = "ok"
            for sev, _ in issues:
                if sev == "error":
                    worst = "error"
                    break
                if sev == "warning":
                    worst = "warning"
            icon = _SEVERITY_COLOR.get(worst, ("", ""))[1]
            self._table.setItem(r, 0, QTableWidgetItem(f"{icon} {pkg}"))

            _, rule = _lookup(pkg)
            if rule:
                self._table.setItem(r, 1, QTableWidgetItem(rule.get("min_python") or "—"))
                self._table.setItem(r, 2, QTableWidgetItem(rule.get("max_python") or "—"))
                blocked = ", ".join(rule.get("blocked_envs", [])) or "—"
                self._table.setItem(r, 3, QTableWidgetItem(blocked))
                self._table.setItem(r, 4, QTableWidgetItem(rule.get("note", "")))
            else:
                self._table.setItem(r, 1, QTableWidgetItem("—"))
                self._table.setItem(r, 2, QTableWidgetItem("—"))
                self._table.setItem(r, 3, QTableWidgetItem("—"))
                self._table.setItem(r, 4, QTableWidgetItem("No known compatibility issues."))

            if worst in ("error", "warning"):
                bg = QColor(_SEVERITY_COLOR[worst][0])
                bg.setAlpha(60)
                for c in range(5):
                    item = self._table.item(r, c)
                    if item:
                        item.setBackground(bg)

        self._table.resizeRowsToContents()

    # ── detail panel (2026-08-13, educational/directive Conflict Manager) ──

    def _on_export(self):
        """Save whatever is CURRENTLY shown in the table (Scan Results or
        All Rules, whichever the user is looking at -- reads straight from
        self._table's actual cells, not the underlying data source, so the
        export always matches what's on screen) to CSV or JSON."""
        row_count = self._table.rowCount()
        if row_count == 0:
            QMessageBox.information(self, "Nothing to Export", "The table is empty -- scan an environment or show the full rules list first.")
            return

        path, chosen_filter = QFileDialog.getSaveFileName(
            self, "Export Conflict Manager Results", "conflict_manager_export.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        if not path:
            return

        headers = ["Package", "Min Python", "Max Python", "Blocked Envs", "Note"]
        rows = []
        for r in range(row_count):
            row = []
            for c in range(5):
                item = self._table.item(r, c)
                row.append(item.text() if item else "")
            rows.append(row)

        is_json = path.lower().endswith(".json") or "JSON" in chosen_filter
        try:
            if is_json:
                import json as _json
                data = [dict(zip(headers, row)) for row in rows]
                with open(path, "w", encoding="utf-8") as f:
                    _json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                import csv as _csv
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = _csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not save the file:\n{e}")
            return

        QMessageBox.information(self, "Exported", f"Saved {len(rows)} row(s) to:\n{path}")

    def _install_command_for(self, pkg_name, env_type):
        """Real, literal command a user would type -- the 'live demonstration'
        part of the educational pillar. Not run automatically; shown as text
        (see _on_detail_install for the actual, safe, one-click version that
        reuses N9's real install pipeline instead of shelling out blind)."""
        cmds = {
            "venv": f"pip install {pkg_name}",
            "uv": f"uv pip install {pkg_name}",
            "poetry": f"poetry add {pkg_name}",
            "conda": f"conda install {pkg_name}",
            "pipx": f"pipx install {pkg_name}",
            "hatch": f"hatch run pip install {pkg_name}",
            "pdm": f"pdm add {pkg_name}",
            "pixi": f"pixi add {pkg_name}",
        }
        return cmds.get(env_type, f"pip install {pkg_name}")

    def _find_learn_topic(self, pkg_name):
        """Best-effort match against LEARN_CATEGORIES' existing "Library —
        Description" title convention (e.g. "NumPy — Fast N-Dimensional
        Arrays") -- no manual per-package curation needed, and packages with
        no matching topic simply get no button (Bayram, 2026-08-13: graceful
        degradation over forcing a match). A few common PyPI-name-vs-display-
        name aliases are handled explicitly since they don't share a substring
        (torch/PyTorch, scikit-learn/sklearn, transformers/Hugging Face)."""
        try:
            from src.gui.learn_content import LEARN_CATEGORIES
        except Exception:
            return None
        aliases = {
            "torch": "pytorch", "sklearn": "scikit-learn",
            "transformers": "hugging face transformers",
            "langchain": "langchain",
        }
        pkg_norm = pkg_name.lower().replace("-", "").replace("_", "")
        alt_norm = aliases.get(pkg_name.lower(), "").replace("-", "").replace(" ", "")
        for cat in LEARN_CATEGORIES:
            for topic in cat.get("topics", []):
                title = topic.get("title", "")
                subject = title.split("—")[0].strip()
                subject_norm = subject.lower().replace("-", "").replace("_", "").replace(" ", "")
                if pkg_norm and pkg_norm in subject_norm:
                    return title
                if alt_norm and alt_norm in subject_norm:
                    return title
        return None

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows() if self._table.selectionModel() else []
        if not rows:
            self._detail_box.setVisible(False)
            return
        item = self._table.item(rows[0].row(), 0)
        if not item:
            self._detail_box.setVisible(False)
            return
        # Column 0 text is "{icon} {pkg_name}" -- strip the icon prefix.
        raw_text = item.text()
        pkg_name = raw_text.split(" ", 1)[1].strip() if " " in raw_text else raw_text.strip()
        self._detail_pkg = pkg_name

        env_type = self._env_cb.currentText()
        py_ver = self._current_py_ver()
        issues = _check_package(pkg_name, env_type, py_ver)
        worst = "ok"
        note_lines = []
        for sev, msg in issues:
            if sev == "error":
                worst = "error"
            elif sev == "warning" and worst != "error":
                worst = "warning"
            note_lines.append(f"{_SEVERITY_COLOR.get(sev, ('', 'ℹ️'))[1]} {msg}")

        color, icon = _SEVERITY_COLOR.get(worst, ("", "✅"))
        self._detail_label.setText(
            f"<b>{icon} {pkg_name}</b><br>" + "<br>".join(note_lines)
        )
        self._detail_cmd_label.setText(self._install_command_for(pkg_name, env_type))

        # Directive buttons: Install only makes sense (and is only offered)
        # when the CURRENT env is actually compatible -- otherwise the only
        # sensible next step is creating a new, compatible one, matching
        # N9/N11's existing "don't offer a button that would just fail"
        # philosophy.
        self._detail_install_btn.setVisible(worst != "error")
        self._detail_create_env_btn.setVisible(worst == "error")

        learn_title = self._find_learn_topic(pkg_name)
        self._detail_learn_title = learn_title
        self._detail_learn_btn.setVisible(learn_title is not None)

        # Bayram (2026-08-13): auto-suggest a known-good replacement
        # when one exists in CONFLICT_RULES' "alternative" field (e.g.
        # PyQt5 -> PySide6, pycrypto -> pycryptodome). Only curated,
        # genuinely-recommended substitutes have this field -- most
        # problem packages don't (no real drop-in replacement exists),
        # and the button just stays hidden for those, same graceful-
        # degradation approach as the Learn-topic button above.
        _, _rule = _lookup(pkg_name)
        alt_pkg = _rule.get("alternative") if _rule else None
        self._detail_alt_pkg = alt_pkg
        if alt_pkg:
            self._detail_alt_btn.setText(f"🔄 Try {alt_pkg} instead")
        self._detail_alt_btn.setVisible(alt_pkg is not None)

        self._detail_box.setVisible(True)

    def _on_detail_install(self):
        pkg_name = getattr(self, "_detail_pkg", None)
        if not pkg_name:
            return
        parent = self.parent()
        if parent is not None and hasattr(parent, "package_panel") and parent.package_panel:
            parent.package_panel._install_packages([pkg_name], hint_name="Conflict Manager")

    def _on_detail_try_alternative(self):
        """Look up the suggested alternative in the search box instead of
        jumping straight to install -- lets the user read its own
        compatibility info first (it might have its own caveats) rather
        than silently swapping one package for another."""
        alt_pkg = getattr(self, "_detail_alt_pkg", None)
        if not alt_pkg:
            return
        self._search_edit.setText(alt_pkg)
        self._do_search()

    def _on_detail_create_env(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_create_env"):
            parent._create_env()

    def _on_detail_open_learn(self):
        title = getattr(self, "_detail_learn_title", None)
        parent = self.parent()
        if not title or parent is None:
            return
        if hasattr(parent, "_switch_page"):
            parent._switch_page(3)
        if hasattr(parent, "learn_page") and parent.learn_page:
            parent.learn_page._jump_to_topic(title)

    # ── all-rules table ────────────────────────────────────────────────────

    def _populate_all_table(self):
        env_type = self._env_cb.currentText()
        py_ver   = self._current_py_ver()
        filt     = self._filter_edit.text().strip().lower()
        show_all = self._show_all_btn.isChecked()

        rows = []
        for pkg_key, rule in sorted(CONFLICT_RULES.items()):
            if filt and filt not in pkg_key:
                continue
            row_sev = "ok"
            if py_ver:
                max_py = rule.get("max_python")
                min_py = rule.get("min_python")
                if max_py and py_ver > tuple(int(x) for x in max_py.split(".")):
                    row_sev = rule.get("severity", "warning")
                if min_py and py_ver < tuple(int(x) for x in min_py.split(".")):
                    row_sev = rule.get("severity", "warning")
            if env_type in rule.get("blocked_envs", []):
                row_sev = rule.get("severity", "warning")
            if not show_all and row_sev == "ok":
                continue
            rows.append((pkg_key, rule, row_sev))

        self._table.setRowCount(len(rows))
        for r, (pkg_key, rule, sev) in enumerate(rows):
            icon = _SEVERITY_COLOR.get(sev, ("", ""))[1]
            self._table.setItem(r, 0, QTableWidgetItem(f"{icon} {pkg_key}"))
            self._table.setItem(r, 1, QTableWidgetItem(rule.get("min_python") or "—"))
            self._table.setItem(r, 2, QTableWidgetItem(rule.get("max_python") or "—"))
            blocked = ", ".join(rule.get("blocked_envs", [])) or "—"
            self._table.setItem(r, 3, QTableWidgetItem(blocked))
            self._table.setItem(r, 4, QTableWidgetItem(rule.get("note", "")))
            if sev in ("error", "warning"):
                bg = QColor(_SEVERITY_COLOR[sev][0])
                bg.setAlpha(50)
                for c in range(5):
                    item = self._table.item(r, c)
                    if item:
                        item.setBackground(bg)

        self._table.resizeRowsToContents()
