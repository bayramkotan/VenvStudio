"""VenvStudio - Log Viewer Dialog

In frozen builds (Windows .exe, macOS .app, Linux AppImage) there is no
terminal, so console logs are invisible. This dialog exposes the rotating
file log (venvstudio.log) from the Tools menu: view, filter by level,
refresh, copy, and open the logs folder.
"""
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QComboBox, QLabel, QApplication, QMessageBox, QCheckBox, QMenu,
    QInputDialog,
)
from PySide6.QtCore import Qt, QTimer

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

        self._live_cb = QCheckBox("🔴 Live")
        self._live_cb.setToolTip("Auto-refresh every 2 seconds — follow ongoing operations")
        self._live_cb.setChecked(True)
        self._live_cb.toggled.connect(self._toggle_live)
        top.addWidget(self._live_cb)

        # NOTE: the app-wide QPushButton stylesheet adds generous padding;
        # with a 36px fixed width the label got clipped to nothing. Override
        # the padding locally and give the label room to breathe.
        _font_btn_css = "QPushButton { padding: 4px 6px; min-width: 0; }"

        btn_font_minus = QPushButton("A−")
        btn_font_minus.setFixedWidth(48)
        btn_font_minus.setStyleSheet(_font_btn_css)
        btn_font_minus.setToolTip("Decrease font size")
        btn_font_minus.clicked.connect(lambda: self._change_font(-1))
        top.addWidget(btn_font_minus)

        btn_font_plus = QPushButton("A+")
        btn_font_plus.setFixedWidth(48)
        btn_font_plus.setStyleSheet(_font_btn_css)
        btn_font_plus.setToolTip("Increase font size")
        btn_font_plus.clicked.connect(lambda: self._change_font(+1))
        top.addWidget(btn_font_plus)
        root.addLayout(top)

        # ── Log text area ──
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.NoWrap)
        # Font is applied via stylesheet, NOT setFont(): the app-wide QSS
        # defines font rules and stylesheets always win over setFont(),
        # which silently broke the A-/A+ buttons.
        self._font_size = 10
        self._apply_text_font()
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

        btn_delete = QPushButton("🧹 Delete…")
        _dm = QMenu(btn_delete)
        _dm.addAction("Older than 7 days", lambda: self._delete_old(7))
        _dm.addAction("Older than 30 days", lambda: self._delete_old(30))
        _dm.addAction("Before a date…", self._delete_before_date)
        _dm.addSeparator()
        _dm.addAction("Delete ALL logs", self._delete_all)
        btn_delete.setMenu(_dm)
        bottom.addWidget(btn_delete)

        btn_folder = QPushButton("📁 Open Logs Folder")
        btn_folder.clicked.connect(self._open_folder)
        bottom.addWidget(btn_folder)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._load()

        self._live_timer = QTimer(self)
        self._live_timer.setInterval(2000)
        self._live_timer.timeout.connect(self._load)
        # accept()/reject() (Close button, ESC) do NOT go through closeEvent,
        # which previously leaked a forever-running 2s timer on a hidden
        # dialog. `finished` fires for every way the dialog ends.
        self.finished.connect(self._live_timer.stop)
        if self._live_cb.isChecked():
            self._live_timer.start()

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
        sb = self._text.verticalScrollBar()
        _was_at_bottom = sb.value() >= sb.maximum() - 4
        _old_pos = sb.value()
        self._text.setPlainText("".join(shown))
        self._count_label.setText(f"{len(shown)} / {len(self._all_lines)} lines (last {_MAX_LINES} max)")
        # Follow the tail only if the user was already at the bottom
        # (Live mode must not fight the user's scroll position)
        sb.setValue(sb.maximum() if _was_at_bottom else min(_old_pos, sb.maximum()))

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

    # ── Font & Live ────────────────────────────────────────────────────

    def _apply_text_font(self):
        _family = "Consolas" if self._is_windows() else "monospace"
        self._text.setStyleSheet(
            f"QPlainTextEdit {{ font-family: '{_family}'; "
            f"font-size: {self._font_size}pt; }}"
        )

    def _change_font(self, delta: int):
        self._font_size = max(6, min(28, self._font_size + delta))
        self._apply_text_font()

    def _toggle_live(self, on: bool):
        if on:
            self._live_timer.start()
        else:
            self._live_timer.stop()

    def closeEvent(self, event):
        self._live_timer.stop()
        super().closeEvent(event)

    # ── Deletion ─────────────────────────────────────────────────

    def _file_handler(self):
        """Find the app's RotatingFileHandler so we can pause it safely."""
        import logging
        for h in logging.getLogger("venvstudio").handlers:
            if hasattr(h, "baseFilename") and h.baseFilename == str(self._log_file):
                return h
        return None

    def _rewrite_log(self, keep_line) -> int:
        """Rewrite venvstudio.log keeping only lines where keep_line(ts) is True.

        Continuation lines (tracebacks) follow their parent record's fate.
        The rotating handler is paused and its stream reopened around the
        rewrite so it never writes into a stale file offset.
        """
        from datetime import datetime
        h = self._file_handler()
        if h:
            h.acquire()
            try:
                h.stream.close()
            except Exception:
                pass
        removed = 0
        try:
            lines = []
            if self._log_file.exists():
                with open(self._log_file, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            kept, keep = [], True
            for line in lines:
                try:
                    ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
                    keep = keep_line(ts)
                except ValueError:
                    pass  # continuation line — inherit previous decision
                if keep:
                    kept.append(line)
                else:
                    removed += 1
            with open(self._log_file, "w", encoding="utf-8") as fh:
                fh.writelines(kept)
        finally:
            if h:
                try:
                    h.stream = h._open()
                except Exception:
                    pass
                h.release()
        return removed

    def _delete_old(self, days: int):
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        removed = self._rewrite_log(lambda ts: ts >= cutoff)
        self._delete_backups()
        self._load()
        QMessageBox.information(self, "Delete Logs",
                                f"Removed {removed} line(s) older than {days} days\n"
                                f"(rotated backup files were also deleted).")

    def _delete_before_date(self):
        from datetime import datetime
        text, ok = QInputDialog.getText(
            self, "Delete Before Date",
            "Delete log entries before (DD.MM.YYYY):")
        if not ok or not text.strip():
            return
        try:
            cutoff = datetime.strptime(text.strip(), "%d.%m.%Y")
        except ValueError:
            QMessageBox.warning(self, "Delete Logs",
                                f"Could not parse date: {text!r}\nExpected format: DD.MM.YYYY")
            return
        removed = self._rewrite_log(lambda ts: ts >= cutoff)
        self._delete_backups()
        self._load()
        QMessageBox.information(self, "Delete Logs",
                                f"Removed {removed} line(s) before {cutoff:%d.%m.%Y}.")

    def _delete_all(self):
        reply = QMessageBox.warning(
            self, "Delete ALL Logs",
            "Delete the entire log file and all rotated backups?\n"
            "This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._rewrite_log(lambda ts: False)
        self._delete_backups()
        self._load()

    def _delete_backups(self):
        """Remove rotated venvstudio.log.1 .. .N files."""
        for i in range(1, 10):
            b = self._log_file.with_name(self._log_file.name + f".{i}")
            try:
                if b.exists():
                    b.unlink()
            except Exception:
                pass
