"""VenvStudio - Log Viewer Dialog

In frozen builds (Windows .exe, macOS .app, Linux AppImage) there is no
terminal, so console logs are invisible. This dialog exposes the rotating
file log (venvstudio.log) from the Tools menu: view, filter by level,
refresh, copy, and open the logs folder.
"""
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QComboBox, QLabel, QApplication, QMessageBox,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from src.utils.logger import get_log_dir

# Read at most this many lines from the end of the file (the rotating
# handler caps files at 2 MB, but tailing keeps the dialog snappy).
_MAX_LINES = 3000

_LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# File-log format starts with "YYYY-MM-DD HH:MM:SS [LEVEL   ] ..." — capture
# the level token so filtering can keep continuation lines (tracebacks)
# attached to their parent record.
_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.*?\[\s*(\w+)\s*\]")


class LogViewerDialog(QDialog):
    """Read-only viewer for the current venvstudio.log file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🪵 Log Viewer — venvstudio.log")
        self.resize(980, 620)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._log_file = get_log_dir() / "venvstudio.log"
        self._all_lines: list[str] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Top bar: file path + level filter ──
        top = QHBoxLayout()
        self._path_label = QLabel(str(self._log_file))
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self._path_label, stretch=1)

        top.addWidget(QLabel("Level:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(_LEVELS)
        self._level_combo.currentTextChanged.connect(self._apply_filter)
        top.addWidget(self._level_combo)
        root.addLayout(top)

        # ── Log text area ──
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.NoWrap)
        _mono = QFont("Consolas" if self._is_windows() else "Monospace")
        _mono.setStyleHint(QFont.Monospace)
        self._text.setFont(_mono)
        root.addWidget(self._text, stretch=1)

        # ── Bottom bar: actions ──
        bottom = QHBoxLayout()
        self._count_label = QLabel("")
        bottom.addWidget(self._count_label, stretch=1)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._load)
        bottom.addWidget(btn_refresh)

        btn_copy = QPushButton("📋 Copy All")
        btn_copy.clicked.connect(self._copy_all)
        bottom.addWidget(btn_copy)

        btn_folder = QPushButton("📁 Open Logs Folder")
        btn_folder.clicked.connect(self._open_folder)
        bottom.addWidget(btn_folder)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._load()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_windows() -> bool:
        import os
        return os.name == "nt"

    def _load(self):
        """(Re)read the tail of the log file and apply the current filter."""
        try:
            if not self._log_file.exists():
                self._all_lines = []
                self._text.setPlainText(
                    f"Log file not found:\n{self._log_file}\n\n"
                    "It is created on first launch; if you just cleared the "
                    "logs folder, new entries will appear after a refresh."
                )
                self._count_label.setText("0 lines")
                return
            with open(self._log_file, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            self._all_lines = lines[-_MAX_LINES:]
            self._apply_filter()
        except Exception as e:
            self._text.setPlainText(f"Could not read log file:\n{e}")
            self._count_label.setText("")

    def _apply_filter(self):
        level = self._level_combo.currentText()
        if level == "ALL":
            shown = self._all_lines
        else:
            # Keep matching records AND their continuation lines (tracebacks
            # etc. don't start with a timestamp, so they inherit the parent
            # record's visibility).
            wanted = _LEVELS.index(level)
            shown = []
            keep = False
            for line in self._all_lines:
                m = _LINE_RE.match(line)
                if m:
                    lvl = m.group(1).upper()
                    keep = lvl in _LEVELS and _LEVELS.index(lvl) >= wanted
                if keep:
                    shown.append(line)
        self._text.setPlainText("".join(shown))
        self._count_label.setText(f"{len(shown)} / {len(self._all_lines)} lines (last {_MAX_LINES} max)")
        # Auto-scroll to the newest entries
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_all(self):
        QApplication.clipboard().setText(self._text.toPlainText())

    def _open_folder(self):
        try:
            from src.utils.platform_utils import open_folder
            ok, msg = open_folder(get_log_dir())
            if not ok:
                QMessageBox.warning(self, "Open Logs Folder", msg or "Could not open folder.")
        except Exception as e:
            QMessageBox.warning(self, "Open Logs Folder", str(e))
