"""VenvStudio - Tools -> Running Jupyter Servers.

B80. A launched JupyterLab outlives the click that started it, and with
``--no-browser`` it never showed a window at all. This lists what is actually
running, opens it, and stops it.

Scanning and stopping both go through a QThread. Each server is asked over
HTTP whether it is there -- about 30 ms each, but that is a network call, and
a shutdown waits for the process to leave, which took two seconds when
measured. Neither belongs on the UI thread.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.utils.logger import get_logger

_log = get_logger(__name__)


class _ScanWorker(QThread):
    done = Signal(object, str)

    def run(self):
        try:
            from src.core.jupyter_servers import list_servers
            servers = list_servers(include_dead=True)
            _log.info(f"[Jupyter] {len(servers)} server record(s), "
                      f"{sum(1 for s in servers if s['alive'])} alive")
            self.done.emit(servers, "")
        except Exception as e:                                # pragma: no cover
            _log.warning(f"[Jupyter] scan failed: {e}")
            self.done.emit([], str(e))


class _StopWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self._info = info

    def run(self):
        try:
            from src.core.jupyter_servers import shutdown_server
            ok, msg = shutdown_server(self._info)
            _log.info(f"[Jupyter] stop port {self._info.get('port')}: "
                      f"{ok} — {msg}")
            self.done.emit(ok, msg)
        except Exception as e:                                # pragma: no cover
            self.done.emit(False, str(e))


class JupyterServersDialog(QDialog):
    """Tools -> Running Jupyter Servers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\U0001f4d3  Running Jupyter Servers")
        # Qt.Window, not an OR onto windowFlags(): a dialog that keeps
        # minimise but is not a real top-level window drags the main window
        # down with it on Windows.
        self.setWindowFlags(Qt.Window)
        self.resize(940, 420)

        self._servers = []
        self._scan = None
        self._stop = None

        root = QVBoxLayout(self)

        self.status = QLabel("Looking for running servers\u2026")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["", "Port", "Serving", "Kernels", "Last activity", "PID"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        _h = self.table.horizontalHeader()
        _h.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(5, 80)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.itemDoubleClicked.connect(lambda *_: self._open())
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.refresh_btn = QPushButton("\u21bb  Refresh")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.clicked.connect(self._start_scan)
        btns.addWidget(self.refresh_btn)

        self.open_btn = QPushButton("\U0001f310  Open in browser")
        self.open_btn.setObjectName("secondary")
        self.open_btn.clicked.connect(self._open)
        btns.addWidget(self.open_btn)

        self.stop_btn = QPushButton("\u23f9  Stop")
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.clicked.connect(self._stop_selected)
        btns.addWidget(self.stop_btn)

        # A stale record is not a running server; it is a file Jupyter left
        # behind when one was killed. Offering to remove it beats showing a
        # row that cannot be acted on.
        self.forget_btn = QPushButton("\U0001f5d1  Forget stale entry")
        self.forget_btn.setObjectName("secondary")
        self.forget_btn.clicked.connect(self._forget)
        btns.addWidget(self.forget_btn)

        btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        root.addLayout(btns)

        self._update_buttons()
        self._start_scan()

    # ── scanning ──────────────────────────────────────────────────────────
    def _start_scan(self):
        self.refresh_btn.setEnabled(False)
        self.status.setText("Looking for running servers\u2026")
        self._scan = _ScanWorker(self)
        self._scan.done.connect(self._scan_finished)
        self._scan.start()

    def _scan_finished(self, servers, err):
        self.refresh_btn.setEnabled(True)
        if err:
            self.status.setText(f"Could not look for servers: {err}")
            return
        self._servers = servers
        alive = [s for s in servers if s.get("alive")]
        stale = len(servers) - len(alive)
        if not servers:
            self.status.setText(
                "No Jupyter server is running. One started from the Launch "
                "tab or from a desktop shortcut will appear here.")
        else:
            _msg = f"{len(alive)} server(s) running"
            if stale:
                _msg += (f"  \u2014  {stale} leftover record(s) from servers "
                         f"that were killed rather than stopped")
            self.status.setText(_msg)
        self._fill(servers)
        self._update_buttons()

    def _fill(self, servers):
        self.table.setRowCount(0)
        for row, s in enumerate(servers):
            self.table.insertRow(row)
            _state = "\u25cf  running" if s.get("alive") else "\u25cb  gone"
            self.table.setItem(row, 0, QTableWidgetItem(_state))
            self.table.setItem(row, 1, QTableWidgetItem(str(s.get("port", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(s.get("root_dir", "")))
            self.table.setItem(row, 3, QTableWidgetItem(
                str(s.get("kernels", 0)) if s.get("alive") else ""))
            _act = (s.get("last_activity") or "").replace("T", " ")[:19]
            self.table.setItem(row, 4, QTableWidgetItem(_act))
            self.table.setItem(row, 5, QTableWidgetItem(str(s.get("pid", ""))))
            self.table.item(row, 2).setToolTip(s.get("url", ""))

    # ── actions ───────────────────────────────────────────────────────────
    def _selected(self):
        rows = self.table.selectionModel().selectedRows() \
            if self.table.selectionModel() else []
        if not rows:
            return None
        i = rows[0].row()
        return self._servers[i] if 0 <= i < len(self._servers) else None

    def _update_buttons(self):
        s = self._selected()
        alive = bool(s and s.get("alive"))
        self.open_btn.setEnabled(alive)
        self.stop_btn.setEnabled(alive)
        self.forget_btn.setEnabled(bool(s) and not alive)

    def _open(self):
        s = self._selected()
        if not s or not s.get("alive"):
            return
        from src.core.jupyter_servers import server_url
        # The token has to travel with the URL or the browser is met with a
        # login page for a server the user already owns.
        from src.utils.platform_utils import open_url
        open_url(server_url(s, "lab"))

    def _stop_selected(self):
        s = self._selected()
        if not s or not s.get("alive"):
            return
        if s.get("kernels"):
            if QMessageBox.question(
                    self, "Stop this server?",
                    f"{s['kernels']} kernel(s) are still running on port "
                    f"{s.get('port')}.\n\nStopping the server stops them, and "
                    f"anything not saved in those notebooks is lost.\n\n"
                    f"Serving: {s.get('root_dir', '')}\n\nStop it?"
            ) != QMessageBox.Yes:
                return
        self.stop_btn.setEnabled(False)
        self.status.setText(f"Stopping the server on port {s.get('port')}\u2026")
        self._stop = _StopWorker(s, self)
        self._stop.done.connect(self._stop_finished)
        self._stop.start()

    def _stop_finished(self, ok, msg):
        self.status.setText(
            f"Server {msg}." if ok else f"Could not stop it: {msg}")
        self._start_scan()

    def _forget(self):
        s = self._selected()
        if not s or s.get("alive"):
            return
        from src.core.jupyter_servers import forget_dead
        if forget_dead(s):
            self._start_scan()
        else:
            QMessageBox.warning(self, "Running Jupyter Servers",
                                "That leftover file could not be removed.")

    def closeEvent(self, event):
        for w in (self._scan, self._stop):
            if w and w.isRunning():
                w.wait(3000)
        super().closeEvent(event)
