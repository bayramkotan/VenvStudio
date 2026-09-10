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


class _StopAllWorker(QThread):
    """Stop several servers, reporting as it goes (B118).

    One worker rather than one per server: shutting down is a request over
    HTTP followed by waiting for the process, and doing four of those at once
    gains nothing while making the progress line meaningless.
    """

    progress = Signal(int, int, int)      # done, total, port
    done = Signal(int, int)               # stopped, failed

    def __init__(self, infos, parent=None):
        super().__init__(parent)
        self._infos = list(infos)

    def run(self):
        from src.core.jupyter_servers import shutdown_server
        _ok = _bad = 0
        for _i, _s in enumerate(self._infos, 1):
            self.progress.emit(_i, len(self._infos), _s.get("port", 0))
            try:
                _r, _msg = shutdown_server(_s)
                _log.info(f"[Jupyter] stop all — port {_s.get('port')}: "
                          f"{_r} — {_msg}")
                _ok += 1 if _r else 0
                _bad += 0 if _r else 1
            except Exception as _e:                           # pragma: no cover
                _log.warning(f"[Jupyter] stop all — port {_s.get('port')}: {_e}")
                _bad += 1
        self.done.emit(_ok, _bad)


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

        # B118 (Bayram): nine leftover records on his screen, one click each.
        # Enabled only when there is more than one, so it does not sit there
        # inviting a click that would do the same as the button beside it.
        # B118: stopping every server at once. Deliberately NOT next to
        # "Clear all stale": that one deletes leftover files and cannot lose
        # anything, this one shuts down running processes and can. It is
        # placed after, styled as an ordinary button rather than a quiet one,
        # and it always asks.
        self.stop_all_btn = QPushButton("\u23f9  Stop all")
        self.stop_all_btn.setEnabled(False)
        self.stop_all_btn.clicked.connect(self._stop_all)
        btns.addWidget(self.stop_all_btn)

        self.forget_all_btn = QPushButton("\U0001f9f9  Clear all stale")
        self.forget_all_btn.setObjectName("secondary")
        self.forget_all_btn.setEnabled(False)
        self.forget_all_btn.clicked.connect(self._forget_all)
        btns.addWidget(self.forget_all_btn)

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
        """Running servers first, then the leftovers, newest first.

        B118: ten records all showing port 8888 and the same directory are
        indistinguishable, which is what made nine ghosts feel like noise
        rather than a list. Sorting puts the live one where it can be seen
        and orders the dead by when they were last heard from.
        """
        # Live first, then the leftovers. Within each group, most recent
        # first -- by last_activity when there is one, and by PID when there
        # is not, since a dead record keeps no activity timestamp and PIDs
        # rise over time on every platform this runs on.
        _all = list(servers or [])
        servers = (
            sorted([s for s in _all if s.get("alive")],
                   key=lambda s: s.get("last_activity") or "", reverse=True)
            + sorted([s for s in _all if not s.get("alive")],
                     key=lambda s: (s.get("last_activity") or "",
                                    s.get("pid") or 0), reverse=True)
        )
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
        # B118: only worth offering when there is more than one to clear --
        # with a single leftover the button beside it does the same job.
        _dead = sum(1 for _x in (self._servers or []) if not _x.get("alive"))
        self.forget_all_btn.setEnabled(_dead > 1)
        _live = sum(1 for _x in (self._servers or []) if _x.get("alive"))
        self.stop_all_btn.setEnabled(_live > 1)
        self.stop_all_btn.setText(
            f"\u23f9  Stop all ({_live})" if _live > 1 else "\u23f9  Stop all")
        self.forget_all_btn.setText(
            f"\U0001f9f9  Clear all stale ({_dead})" if _dead > 1
            else "\U0001f9f9  Clear all stale")

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

    def _stop_all(self):
        """Shut down every running server (B118).

        The warning names the total number of kernels, not just the number of
        servers: "stop 3 servers" understates it when those three are holding
        eleven notebooks whose unsaved cells are about to go.
        """
        _live = [s for s in (self._servers or []) if s.get("alive")]
        if not _live:
            return
        _kern = sum(int(s.get("kernels") or 0) for s in _live)
        _msg = (f"Stop {len(_live)} running server(s)?\n\n")
        if _kern:
            _msg += (f"{_kern} kernel(s) are running on them. Stopping the "
                     f"servers stops those too, and anything not saved in "
                     f"those notebooks is lost.\n\n")
        _msg += "Serving:\n" + "\n".join(
            f"  \u2022  port {s.get('port')} \u2014 {s.get('root_dir', '')}"
            for s in _live[:8])
        if len(_live) > 8:
            _msg += f"\n  \u2026 and {len(_live) - 8} more"
        if QMessageBox.question(self, "Stop all servers?", _msg,
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        self.stop_all_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.status.setText(f"Stopping {len(_live)} server(s)\u2026")
        self._stop = _StopAllWorker(_live, self)
        self._stop.progress.connect(
            lambda i, n, port: self.status.setText(
                f"Stopping {i}/{n} \u2014 port {port}\u2026"))
        self._stop.done.connect(self._stop_all_finished)
        self._stop.start()

    def _stop_all_finished(self, stopped, failed):
        if failed:
            self.status.setText(
                f"Stopped {stopped}, {failed} did not respond.")
        else:
            self.status.setText(f"Stopped {stopped} server(s).")
        self._start_scan()

    def _forget_all(self):
        """Remove every leftover record in one go (B118).

        A server that was killed rather than stopped leaves its JSON file
        behind, and after a few sessions the list is mostly ghosts. Deleting
        them one at a time is what the button beside this one is for.

        Running servers are never touched: `alive` is what separates a record
        that still has a process behind it from one that does not.
        """
        _dead = [s for s in (self._servers or []) if not s.get("alive")]
        if not _dead:
            return
        if QMessageBox.question(
                self, "Clear all stale",
                f"Remove {len(_dead)} leftover record(s)?\n\n"
                f"These are servers that were killed rather than stopped, so "
                f"their files were never cleaned up. Running servers are not "
                f"affected.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        from src.core.jupyter_servers import forget_dead
        _gone, _failed = 0, 0
        for _s in _dead:
            try:
                if forget_dead(_s):
                    _gone += 1
                else:
                    _failed += 1
            except Exception:
                _failed += 1
        if _failed:
            QMessageBox.warning(
                self, "Running Jupyter Servers",
                f"Removed {_gone}, but {_failed} file(s) could not be "
                f"deleted \u2014 something may still be holding them open.")
        self._start_scan()

    def closeEvent(self, event):
        for w in (self._scan, self._stop):
            if w and w.isRunning():
                w.wait(3000)
        super().closeEvent(event)
