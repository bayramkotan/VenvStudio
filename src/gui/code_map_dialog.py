"""VenvStudio - Code Map dialog: what is in a codebase and what talks to what.

B30. The window over src/core/code_map.py. Two tabs:

    Tree      folder -> file -> class -> method, each with what it is for,
              and for a selected definition, who calls it and what it calls
    Findings  names defined twice and drifted, class methods that hide a
              mixin's, constants holding the same data under two names, and
              definitions nothing appears to reach

The target is chosen at the top: VenvStudio's own source, or any folder --
so the same engine answers "what is in my project" for the user's projects,
not only for ours.

THE SCAN RUNS IN A THREAD. Reading VenvStudio's own src is 86 files and
55,000 lines and takes a few seconds; doing that on the UI thread is the
exact mistake B59 is open about elsewhere in this codebase. The window opens
immediately and fills when the reading is done.
"""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QFileDialog,
    QMessageBox, QSplitter, QWidget, QLineEdit,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.utils.logger import get_logger

_log = get_logger(__name__)


class _ScanWorker(QThread):
    """Reads a tree with src/core/code_map.py, off the UI thread."""

    done = Signal(object, str)          # (CodeMap | None, error message)

    def __init__(self, root: str, parent=None):
        super().__init__(parent)
        self._root = root

    def run(self):
        try:
            from src.core.code_map import scan
            _log.info(f"[CodeMap] scanning {self._root}")
            cmap = scan(self._root)
            _log.info(f"[CodeMap] {len(cmap.files)} files, "
                      f"{cmap.total_loc:,} lines, "
                      f"{len(cmap.duplicates)} duplicate name(s), "
                      f"{len(cmap.shadowed)} shadowed, "
                      f"{len(cmap.unreached)} unreached")
            self.done.emit(cmap, "")
        except Exception as e:                                # pragma: no cover
            _log.warning(f"[CodeMap] scan failed: {e}")
            self.done.emit(None, str(e))


class _FetchWorker(QThread):
    """Downloads the project source, off the UI thread (B72)."""

    progress = Signal(int, int, str)
    done = Signal(str, str)             # (folder, error)

    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self._version = version

    def run(self):
        try:
            from src.core.code_map import fetch_source
            path = fetch_source(
                version=self._version,
                progress=lambda d, t, m: self.progress.emit(d, t, m))
            self.done.emit(str(path), "")
        except Exception as e:
            _log.warning(f"[CodeMap] download failed: {e}")
            self.done.emit("", str(e))


class CodeMapDialog(QDialog):
    """Tools -> Code Map."""

    def __init__(self, parent=None, project_paths=None):
        super().__init__(parent)
        self.setWindowTitle("🗺️ Code Map")
        # Qt.Window rather than OR-ing onto windowFlags(): a dialog that owns
        # minimise/maximise but is not an independent top-level window drags
        # the main window down with it when minimised on Windows. That was
        # learned the hard way in an earlier session.
        self.setWindowFlags(Qt.Window)
        self.resize(1100, 720)

        self._cmap = None
        self._worker = None
        self._targets = {}

        root = QVBoxLayout(self)

        # ── target row ────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.addWidget(QLabel("Read:"))
        self.target_combo = QComboBox()
        self._fill_targets(project_paths or [])
        top.addWidget(self.target_combo, 1)

        self.browse_btn = QPushButton("📁  Browse…")
        self.browse_btn.setObjectName("secondary")
        self.browse_btn.clicked.connect(self._browse)
        top.addWidget(self.browse_btn)

        # B72: someone who installed with pip has the source only inside
        # site-packages -- read-only, and possibly not the whole repository.
        # Telling them to clone it assumes they know what that means and that
        # git is installed. This fetches it for them.
        self.fetch_btn = QPushButton("⬇  Download source…")
        self.fetch_btn.setObjectName("secondary")
        self.fetch_btn.setToolTip(
            "Download VenvStudio's own source from GitHub so you can read "
            "and edit it. About 26 MB.")
        self.fetch_btn.clicked.connect(self._download_source)
        top.addWidget(self.fetch_btn)

        self.scan_btn = QPushButton("🔍  Read")
        self.scan_btn.clicked.connect(self._start_scan)
        top.addWidget(self.scan_btn)
        root.addLayout(top)

        self.status = QLabel("Choose what to read, then press Read.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        # ── tabs ──────────────────────────────────────────────────────────
        self.tabs = QTabWidget()

        # Tree tab: definitions on the left, connections on the right.
        _tree_page = QWidget()
        _tl = QVBoxLayout(_tree_page)
        _tl.setContentsMargins(0, 0, 0, 0)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(
            "Filter by file or definition name…")
        self.filter_edit.textChanged.connect(self._apply_filter)
        _tl.addWidget(self.filter_edit)

        _split = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Lines", "What it is for"])
        self.tree.setColumnWidth(0, 340)
        self.tree.setColumnWidth(1, 70)
        self.tree.itemSelectionChanged.connect(self._show_connections)
        _split.addWidget(self.tree)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        _split.addWidget(self.detail)
        _split.setSizes([700, 380])
        _tl.addWidget(_split)
        self.tabs.addTab(_tree_page, "Tree")

        self.findings = QTextEdit()
        self.findings.setReadOnly(True)
        self.tabs.addTab(self.findings, "Findings")
        root.addWidget(self.tabs, 1)

        # ── buttons ───────────────────────────────────────────────────────
        btns = QHBoxLayout()
        self.save_btn = QPushButton("💾  Save as Markdown…")
        self.save_btn.setObjectName("secondary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        btns.addWidget(self.save_btn)
        btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        root.addLayout(btns)

    # ── targets ───────────────────────────────────────────────────────────
    def _fill_targets(self, project_paths):
        """VenvStudio's own source first, then the user's known projects."""
        self.target_combo.clear()
        self._targets = {}

        own = Path(__file__).resolve().parent.parent      # .../src
        # B72: say WHICH copy this is. A pip install puts the source under
        # site-packages, where it is read-only and may not be the whole
        # repository -- someone reading it deserves to know that before they
        # try to change a line and find they cannot.
        parts = {p.lower() for p in own.parts}
        installed = "site-packages" in parts or "dist-packages" in parts
        kind = ("installed copy, read-only" if installed
                else "your checkout, editable")
        label = f"VenvStudio source — {kind}  ({own})"
        self._targets[label] = str(own)
        self.target_combo.addItem(label)
        self._installed_copy = installed

        for p in project_paths or []:
            p = str(p)
            if not os.path.isdir(p):
                continue
            label = f"{Path(p).name}  ({p})"
            if label not in self._targets:
                self._targets[label] = p
                self.target_combo.addItem(label)

    def _download_source(self):
        """Fetch the source from GitHub and offer it as a target (B72)."""
        try:
            from src.utils.constants import APP_VERSION as _v
        except Exception:
            _v = ""
        self.fetch_btn.setEnabled(False)
        self.status.setText("Downloading the source…")
        self._fetch = _FetchWorker(str(_v), self)
        self._fetch.progress.connect(self._fetch_progress)
        self._fetch.done.connect(self._fetch_finished)
        self._fetch.start()

    def _fetch_progress(self, done, total, message):
        if total:
            self.status.setText(
                f"{message}  {done / 1048576:.1f} / {total / 1048576:.1f} MB")
        else:
            self.status.setText(message)

    def _fetch_finished(self, folder, err):
        self.fetch_btn.setEnabled(True)
        if not folder:
            self.status.setText(f"Could not download the source: {err}")
            return
        src = Path(folder) / "src"
        target = src if src.is_dir() else Path(folder)
        label = f"VenvStudio source — downloaded, editable  ({target})"
        self._targets[label] = str(target)
        if self.target_combo.findText(label) < 0:
            self.target_combo.addItem(label)
        self.target_combo.setCurrentText(label)
        self.status.setText(
            f"Downloaded to {folder}. Press Read to map it — you can also "
            f"open that folder in any editor.")

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Folder to read")
        if not d:
            return
        label = f"{Path(d).name}  ({d})"
        self._targets[label] = d
        self.target_combo.addItem(label)
        self.target_combo.setCurrentText(label)

    # ── scanning ──────────────────────────────────────────────────────────
    def _start_scan(self):
        root = self._targets.get(self.target_combo.currentText(), "")
        if not root or not os.path.isdir(root):
            QMessageBox.warning(self, "Code Map",
                                "That folder is not there any more.")
            return
        self.scan_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status.setText(f"Reading {root} …")
        self.tree.clear()
        self.detail.clear()
        self.findings.clear()

        # Kept on self: a QThread whose last reference goes out of scope is
        # deleted by C++ while still running, which crashed this application
        # on Linux once already (v1.6.61).
        self._worker = _ScanWorker(root, self)
        self._worker.done.connect(self._scan_finished)
        self._worker.start()

    def _scan_finished(self, cmap, err):
        self.scan_btn.setEnabled(True)
        if cmap is None:
            self.status.setText(f"Could not read that folder: {err}")
            return
        self._cmap = cmap
        self.save_btn.setEnabled(True)
        n_defs = sum(len(f.defs) for f in cmap.files)
        drift = len([d for d in cmap.duplicates if not d["identical"]])
        self.status.setText(
            f"{len(cmap.files)} files · {cmap.total_loc:,} lines · "
            f"{n_defs} definitions   —   {drift} drifted duplicate(s), "
            f"{len(cmap.shadowed)} shadowed, "
            f"{len(cmap.twin_constants)} twin constant(s), "
            f"{len(cmap.unreached)} with no static caller")
        self._fill_tree(cmap)
        self._fill_findings(cmap)

    # ── tree ──────────────────────────────────────────────────────────────
    def _fill_tree(self, cmap):
        self.tree.setUpdatesEnabled(False)
        try:
            for folder, files in cmap.by_folder().items():
                f_item = QTreeWidgetItem([f"{folder}/", "", ""])
                loc = sum(f.loc for f in files)
                f_item.setText(1, f"{loc:,}")
                for info in files:
                    i = QTreeWidgetItem(
                        [Path(info.path).name, f"{info.loc:,}", info.doc])
                    i.setData(0, Qt.UserRole, ("file", info.path, ""))
                    classes = [d for d in info.defs if d.kind == "class"]
                    funcs = [d for d in info.defs if d.kind == "function"]
                    for c in classes:
                        c_item = QTreeWidgetItem(
                            [f"class {c.name}", str(c.lines), c.doc])
                        c_item.setData(0, Qt.UserRole,
                                       ("def", info.path, c.name))
                        for m in info.defs:
                            if m.kind == "method" and m.owner == c.name:
                                m_item = QTreeWidgetItem(
                                    [m.name + "()", str(m.lines), m.doc])
                                m_item.setData(0, Qt.UserRole,
                                               ("def", info.path, m.qualname))
                                c_item.addChild(m_item)
                        i.addChild(c_item)
                    for fn in funcs:
                        fn_item = QTreeWidgetItem(
                            [fn.name + "()", str(fn.lines), fn.doc])
                        fn_item.setData(0, Qt.UserRole,
                                        ("def", info.path, fn.name))
                        i.addChild(fn_item)
                    f_item.addChild(i)
                self.tree.addTopLevelItem(f_item)
        finally:
            self.tree.setUpdatesEnabled(True)

    def _apply_filter(self, text):
        """Hide anything not matching, keeping parents of matches visible."""
        text = (text or "").strip().lower()

        def visit(item) -> bool:
            hit = text in item.text(0).lower() if text else True
            shown = False
            for i in range(item.childCount()):
                shown = visit(item.child(i)) or shown
            item.setHidden(not (hit or shown))
            return hit or shown

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def _show_connections(self):
        """For the selected definition: who calls it, and what it calls."""
        if not self._cmap:
            return
        items = self.tree.selectedItems()
        if not items:
            return
        data = items[0].data(0, Qt.UserRole)
        if not data:
            self.detail.clear()
            return
        kind, path, qual = data
        if kind == "file":
            info = next((f for f in self._cmap.files if f.path == path), None)
            if not info:
                return
            L = [f"<b>{info.path}</b>", f"{info.loc:,} lines", ""]
            if info.doc:
                L.append(info.doc)
                L.append("")
            L.append("<b>Imports</b>")
            L += sorted(info.imports) or ["(none)"]
            self.detail.setHtml("<br>".join(L))
            return

        name = qual.split(".")[-1]
        callers, calls = [], []
        for f in self._cmap.files:
            for d in f.defs:
                if name in d.calls and not (f.path == path
                                            and d.qualname == qual):
                    callers.append(f"{f.path} — {d.qualname}")
                if f.path == path and d.qualname == qual:
                    calls = sorted(d.calls)

        L = [f"<b>{qual}</b>", f"in {path}", ""]
        L.append(f"<b>Referenced by ({len(callers)})</b>")
        L += callers or ["(nothing found — may be reached by a signal, "
                         "a getattr, or a name built at runtime)"]
        L.append("")
        L.append(f"<b>Names it uses ({len(calls)})</b>")
        L.append(", ".join(calls) if calls else "(none)")
        self.detail.setHtml("<br>".join(L))

    # ── findings ──────────────────────────────────────────────────────────
    def _fill_findings(self, cmap):
        from src.core.code_map import to_markdown
        text = to_markdown(cmap)
        if "## The tree" in text:
            text = text.split("## The tree")[0].rstrip()
        self.findings.setPlainText(text)

    def _save(self):
        if not self._cmap:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Code Map", "CODE_MAP.md", "Markdown (*.md)")
        if not path:
            return
        try:
            from src.core.code_map import to_markdown
            Path(path).write_text(to_markdown(self._cmap), encoding="utf-8")
            self.status.setText(f"Saved to {path}")
        except OSError as e:
            QMessageBox.warning(self, "Code Map", f"Could not save: {e}")

    def closeEvent(self, event):
        """Let a running scan finish before the object goes away."""
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        super().closeEvent(event)
