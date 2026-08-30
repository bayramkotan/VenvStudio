"""VenvStudio - Command History Dialog

Every action VenvStudio performs has a terminal equivalent, and the point of
showing it is that you can learn it. The header strip shows the last command
and the log keeps them all, but the log interleaves them with cache lines and
progress output. This window lists the commands on their own, one per row, so
you can read back what a session actually did and copy any of them.

N77 (2026-08-28): the history now survives restarts -- it is mirrored to
command_history.json beside the config. It used to be session-only on the
grounds that the log file was the permanent record, but the log interleaves
commands with cache and progress lines, which is exactly what this window
exists to avoid. The last 500 are kept.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QApplication, QMessageBox, QLineEdit, QMenu,
)
from PySide6.QtCore import Qt, QTimer

from src.utils.logger import get_command_history, clear_command_history


class CommandHistoryDialog(QDialog):
    """Read-only list of the terminal commands VenvStudio has run."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command History")
        self.resize(980, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._entries: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Top bar: search + font size ──
        top = QHBoxLayout()
        top.addWidget(QLabel("Filter:"))
        self._filter = QLineEdit()
        self._filter.setPlaceholderText(
            "Type to narrow — package name, tool, environment…")
        self._filter.textChanged.connect(self._apply_filter)
        top.addWidget(self._filter, stretch=1)

        # Same override as the log viewer: the app-wide QPushButton stylesheet
        # adds enough padding to clip a short label at a fixed width.
        _font_btn_css = "QPushButton { padding: 4px 6px; min-width: 0; }"

        btn_font_minus = QPushButton("A-")
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

        # ── Command list ──
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        self._list.setAlternatingRowColors(True)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemDoubleClicked.connect(lambda _i: self._copy_selected())
        self._list.setToolTip(
            "Double-click a row to copy that command.\n"
            "Select several rows to copy them together.")
        self._font_size = 10
        self._apply_list_font()
        root.addWidget(self._list, stretch=1)

        # ── Bottom bar: actions ──
        bottom = QHBoxLayout()
        self._count_label = QLabel("")
        bottom.addWidget(self._count_label, stretch=1)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._load)
        bottom.addWidget(btn_refresh)

        self._btn_copy = QPushButton("Copy Selected")
        self._btn_copy.clicked.connect(self._copy_selected)
        bottom.addWidget(self._btn_copy)

        btn_copy_all = QPushButton("Copy All")
        btn_copy_all.clicked.connect(self._copy_all)
        bottom.addWidget(btn_copy_all)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("danger")
        btn_clear.setToolTip(
            "Forget the commands listed here, including earlier sessions.\n"
            "The log file keeps its own copy.")
        btn_clear.clicked.connect(self._clear)
        bottom.addWidget(btn_clear)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._load()

        # Follow along while the window stays open, so running an install in
        # the background and switching back shows it without a manual refresh.
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._load_if_changed)
        # accept()/reject() skip closeEvent; `finished` covers every exit.
        self.finished.connect(self._timer.stop)
        self._timer.start()

    # ── Loading ──────────────────────────────────────────────────────────

    def _load_if_changed(self):
        if len(get_command_history()) != len(self._entries):
            self._load()

    def _load(self):
        self._entries = get_command_history()
        self._apply_filter()

    def _apply_filter(self):
        needle = self._filter.text().strip().lower()
        # Preserve the selection across refreshes so a background install
        # ticking in does not yank the row out from under a copy.
        _selected = {
            i.data(Qt.UserRole) for i in self._list.selectedItems()
        }
        self._list.clear()
        shown = 0
        for entry in self._entries:
            _cmd = entry.get("command", "")
            _ctx = entry.get("context", "")
            if needle and needle not in (_cmd + " " + _ctx).lower():
                continue
            _label = f"{entry.get('time', '')}   {_cmd}"
            if _ctx:
                _label = f"{entry.get('time', '')}   [{_ctx}]   {_cmd}"
            item = QListWidgetItem(_label)
            item.setData(Qt.UserRole, _cmd)
            item.setToolTip(_cmd)
            self._list.addItem(item)
            if _cmd in _selected:
                item.setSelected(True)
            shown += 1
        if needle:
            self._count_label.setText(
                f"{shown} of {len(self._entries)} commands")
        else:
            self._count_label.setText(f"{len(self._entries)} commands")
        self._list.scrollToBottom()

    # ── Actions ──────────────────────────────────────────────────────────

    def _copy_selected(self):
        items = self._list.selectedItems()
        if not items:
            QMessageBox.information(
                self, "Copy", "Select one or more rows first.")
            return
        text = "\n".join(i.data(Qt.UserRole) or "" for i in items)
        QApplication.clipboard().setText(text)
        self._flash(self._btn_copy, "Copied")

    def _copy_all(self):
        if not self._entries:
            return
        text = "\n".join(e.get("command", "") for e in self._entries)
        QApplication.clipboard().setText(text)

    def _clear(self):
        if not self._entries:
            return
        reply = QMessageBox.question(
            self, "Clear Command History",
            f"Forget the {len(self._entries)} command(s) listed here, "
            f"including earlier sessions?\n\n"
            "The log file keeps its own copy, so nothing is lost.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        clear_command_history()
        self._load()

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        menu.addAction("Copy command", self._copy_selected)
        menu.addAction("Copy all", self._copy_all)
        menu.exec(self._list.mapToGlobal(pos))

    # ── Appearance ───────────────────────────────────────────────────────

    @staticmethod
    def _is_windows() -> bool:
        import os
        return os.name == "nt"

    def _apply_list_font(self):
        # Stylesheet rather than setFont(): the app-wide QSS defines font
        # rules and always wins over setFont(), which is what silently broke
        # the A-/A+ buttons in the log viewer.
        _family = "Consolas" if self._is_windows() else "monospace"
        self._list.setStyleSheet(
            f"QListWidget {{ font-family: '{_family}'; "
            f"font-size: {self._font_size}pt; }}"
        )

    def _change_font(self, delta: int):
        self._font_size = max(6, min(28, self._font_size + delta))
        self._apply_list_font()

    def _flash(self, button, text: str, revert_ms: int = 1200):
        """Confirm an action on the button itself, then put the label back."""
        _old = button.text()
        button.setText(text)
        QTimer.singleShot(revert_ms, lambda: button.setText(_old))

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
