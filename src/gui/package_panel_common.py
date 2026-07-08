"""VenvStudio - Package Panel: Common/Shared Classes
`_EnvSizeWorker`, `WorkerThread`, `CommandHintDialog` — dependency-free module.
Kept separate (no import from package_panel.py or any mixin) to avoid circular
imports, since multiple mixins need WorkerThread. package_panel.py re-exports
these so `from src.gui.package_panel import WorkerThread` (used elsewhere in
the codebase, e.g. settings_toolchain.py) keeps working unchanged.
"""
import os

from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QVBoxLayout,
)
from PySide6.QtCore import Qt, QThread, Signal


class _EnvSizeWorker(QThread):
    """Background worker that totals the on-disk size of a venv directory.

    Runs os.walk + getsize off the UI thread (B175). Emits ``done(path, size_str)``
    when finished. ``size_str`` is empty on failure. The walk respects
    interruption requests so the worker can be cancelled when the user
    selects a different env.
    """
    done = Signal(str, str)

    _SIZE_CAP_BYTES = 10 * 1024 * 1024 * 1024

    def __init__(self, venv_path_str: str, parent=None):
        super().__init__(parent)
        self._venv_path_str = venv_path_str

    def run(self):
        total = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(self._venv_path_str):
                if self.isInterruptionRequested():
                    self.done.emit(self._venv_path_str, "")
                    return
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        # B-conda-size: skip symlinks so the env size matches
                        # `du -sh` and the env table column. Without this,
                        # symlinks were counted as full file sizes — conda
                        # envs (which symlink Python's stdlib) would report
                        # roughly double the real on-disk usage.
                        if os.path.islink(fp):
                            continue
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
                if total > self._SIZE_CAP_BYTES:
                    break
            if total < 1024 * 1024:
                size_str = f"{total / 1024:.0f} KB"
            elif total < 1024 * 1024 * 1024:
                size_str = f"{total / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total / (1024 * 1024 * 1024):.2f} GB"
            self.done.emit(self._venv_path_str, size_str)
        except Exception:
            self.done.emit(self._venv_path_str, "")


class WorkerThread(QThread):
    """Worker thread with cancel support."""
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, func, *args, parent=None, **kwargs):
        # B186 — accept a keyword-only `parent` so callers can attach the
        # thread to the QObject hierarchy (so MainWindow.closeEvent can find
        # it via findChildren). `parent` is keyword-only to avoid colliding
        # with arbitrary positional args forwarded to `func`.
        super().__init__(parent)
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False

    def run(self):
        try:
            self.kwargs["callback"] = self._on_progress
            success, msg = self.func(*self.args, **self.kwargs)
            if self._cancelled:
                self.finished.emit(False, "Operation cancelled by user")
            else:
                self.finished.emit(success, msg)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.worker").error(f"WorkerThread CRASH:\n{tb}")
            except Exception:
                print(f"[WorkerThread ERROR] {tb}")
            self.finished.emit(False, f"Error: {e}")

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True

class CommandHintDialog(QDialog):
    """Shows the equivalent pip command for educational purposes."""

    def __init__(self, title, command, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"💡 {title}")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        info = QLabel("Equivalent terminal command:")
        info.setStyleSheet(f"font-size: {self._c()['fs_small']}px; color: {self._c()['fg_muted']};")
        layout.addWidget(info)

        cmd_frame = QFrame()
        cmd_frame.setStyleSheet(
            "background-color: " + self._c()['sidebar'] + "; border: 1px solid " + self._c()['border'] + "; "
            "border-radius: 8px; padding: 12px;"
        )
        cmd_layout = QVBoxLayout(cmd_frame)
        cmd_label = QLabel(f"<code style='font-size:{self._c()['fs_subheader']}px; color:{self._c()['success']};'>{command}</code>")
        cmd_label.setTextFormat(Qt.RichText)
        cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cmd_layout.addWidget(cmd_label)
        layout.addWidget(cmd_frame)

        tip = QLabel("💡 You can copy this command and run it in any terminal.")
        tip.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg_muted']};")
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("📋 Copy Command")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(lambda: (
            QApplication.clipboard().setText(command),
            copy_btn.setText("✅ Copied!"),
        ))
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        ok_btn = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn.accepted.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

