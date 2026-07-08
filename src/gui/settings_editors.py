"""VenvStudio - Settings: EditorsMixin"""
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


class EditorsMixin:
    """Mixin for SettingsPage: Editor Integration section (VS Code, Cursor, Windsurf, Zed, PyCharm...)."""

    # ─────────────────────────────────────────────────────────────────────
    # UI section builders (moved from settings_page.py)
    # ─────────────────────────────────────────────────────────────────────

    def _setup_vscode_ui_section(self, layout):
        # ── 6. EDITOR INTEGRATION (VS Code, Cursor, Windsurf, Zed, PyCharm...) ──
        ed_group = QGroupBox("📝 Editor Integration")
        ed_layout = QVBoxLayout()
        ed_layout.setSpacing(10)

        info = QLabel(
            "Register VenvStudio's default venv folder with installed editors so "
            "they can discover your environments automatically."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;"
        )
        ed_layout.addWidget(info)

        # Venv directory row: shows what will be registered
        dir_row = QHBoxLayout()
        dir_lbl = QLabel(f"📁 Venv directory:")
        dir_lbl.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px; "
            f"border: none; padding: 0;"
        )
        dir_row.addWidget(dir_lbl)
        self._ed_venv_dir_lbl = QLabel("(detecting...)")
        self._ed_venv_dir_lbl.setStyleSheet(
            f"color: {self._c()['accent']}; font-size: {self._c()['fs_small']}px; "
            f"border: none; padding: 0; "
            f"font-family: Consolas, monospace;"
        )
        dir_row.addWidget(self._ed_venv_dir_lbl, 1)
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Re-detect installed editors")
        refresh_btn.setFixedWidth(36)
        refresh_btn.clicked.connect(self._refresh_editor_list)
        dir_row.addWidget(refresh_btn)

        reg_all_btn = QPushButton("Register all installed")
        reg_all_btn.setObjectName("secondary")
        reg_all_btn.clicked.connect(self._register_all_editors)
        dir_row.addWidget(reg_all_btn)
        ed_layout.addLayout(dir_row)

        # Editor list table
        self._ed_table = QTableWidget()
        self._ed_table.setStyleSheet(self._table_style(12))
        self._ed_table.setColumnCount(5)
        self._ed_table.setHorizontalHeaderLabels(
            ["Editor", "Status", "Current Path", "", ""]
        )
        hdr = self._ed_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        self._ed_table.setColumnWidth(0, 160)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed)
        self._ed_table.setColumnWidth(1, 100)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        self._ed_table.setColumnWidth(3, 130)
        hdr.setSectionResizeMode(4, QHeaderView.Fixed)
        self._ed_table.setColumnWidth(4, 130)
        self._ed_table.verticalHeader().setVisible(False)
        self._ed_table.verticalHeader().setDefaultSectionSize(42)
        self._ed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._ed_table.setSelectionMode(QTableWidget.NoSelection)
        self._ed_table.setMinimumHeight(280)
        ed_layout.addWidget(self._ed_table)

        # Help line
        help_lbl = QLabel(
            "Registering writes to the editor's user settings file. "
            "A backup (.vs-backup) is created before any change. "
            "Unregister cleanly removes the entries VenvStudio added."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; "
            f"font-style: italic;"
        )
        ed_layout.addWidget(help_lbl)

        ed_group.setLayout(ed_layout)
        layout.addWidget(ed_group)

        # Initial population — deferred so base_dir is available
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._refresh_editor_list)

    # ─────────────────────────────────────────────────────────────────────
    # Editor integration — helpers
    # ─────────────────────────────────────────────────────────────────────

    def _get_editor_venv_dir(self) -> str:
        """Best-effort resolution of the current default venv directory.
        Tries multiple sources so this works even before VenvManager is ready.
        """
        # 1. config (most reliable — this is what Settings writes)
        try:
            if hasattr(self, "config") and self.config:
                base = self.config.get("default_path", "") or self.config.get("base_dir", "")
                if base:
                    import os
                    return os.path.expanduser(str(base))
        except Exception:
            pass
        # 2. VenvManager — may fail on first call; guard heavily
        try:
            from src.core.venv_manager import VenvManager
            vm = VenvManager()
            if getattr(vm, "base_dir", None):
                return str(vm.base_dir)
        except Exception:
            pass
        # 3. Reasonable default
        import os
        return os.path.expanduser("~/venv")

    def _refresh_editor_list(self):
        """Detect installed editors and fill the table."""
        try:
            from src.core.editor_integration import detect_editors, current_registered_path
        except Exception as e:
            self._ed_venv_dir_lbl.setText(f"(error: {e})")
            return

        editors = detect_editors()
        self._ed_table.setRowCount(len(editors))

        venv_dir = self._get_editor_venv_dir()
        self._ed_venv_dir_lbl.setText(venv_dir or "(not set)")

        c = self._c()
        for row, ed in enumerate(editors):
            # Col 0: icon + name
            name_item = QTableWidgetItem(f"{ed.icon}  {ed.name}")
            self._ed_table.setItem(row, 0, name_item)

            # Col 1: installed / not-found badge
            if ed.installed:
                status_item = QTableWidgetItem("● Installed")
                status_item.setForeground(QColor("#a6e3a1"))  # green
            else:
                status_item = QTableWidgetItem("○ Not found")
                status_item.setForeground(QColor("#6c7086"))  # dim
            status_item.setTextAlignment(Qt.AlignCenter)
            self._ed_table.setItem(row, 1, status_item)

            # Col 2: current registered path (or "(not registered)")
            current = current_registered_path(ed) if ed.installed else None
            if current:
                path_item = QTableWidgetItem(current)
                path_item.setForeground(QColor(c["accent"]))
            else:
                path_item = QTableWidgetItem(
                    "(not registered)" if ed.installed else ""
                )
                path_item.setForeground(QColor(c["fg_muted"]))
            self._ed_table.setItem(row, 2, path_item)

            # Col 3: Register button (disabled if editor not installed)
            reg_btn = QPushButton("Register")
            reg_btn.setEnabled(ed.installed)
            reg_btn.setMinimumWidth(110)
            reg_btn.setToolTip(
                ed.note if ed.note else
                f"Register VenvStudio's venv directory with {ed.name}."
            )
            reg_btn.clicked.connect(lambda _=None, e=ed: self._register_editor(e))
            self._ed_table.setCellWidget(row, 3, reg_btn)

            # Col 4: Unregister button
            unreg_btn = QPushButton("Unregister")
            unreg_btn.setEnabled(ed.installed and current is not None)
            unreg_btn.setObjectName("danger")
            unreg_btn.setMinimumWidth(110)
            unreg_btn.clicked.connect(lambda _=None, e=ed: self._unregister_editor(e))
            self._ed_table.setCellWidget(row, 4, unreg_btn)

    def _register_editor(self, editor):
        """Register with one editor."""
        from src.core.editor_integration import register
        from PySide6.QtWidgets import QMessageBox
        from pathlib import Path
        import logging

        _lg = logging.getLogger("venvstudio.settings.editor")
        venv_dir = Path(self._get_editor_venv_dir())
        _lg.info(f"_register_editor: {editor.id} → {venv_dir}")

        # Create dir if it doesn't exist — editors need a real directory to scan
        if not venv_dir.exists():
            try:
                venv_dir.mkdir(parents=True, exist_ok=True)
                _lg.info(f"created venv dir: {venv_dir}")
            except Exception as e:
                QMessageBox.warning(
                    self, f"{editor.name} — Failed",
                    f"Venv directory doesn't exist and could not be created:\n{venv_dir}\n\n{e}"
                )
                return

        try:
            result = register(editor, venv_dir)
        except Exception as e:
            _lg.exception("register raised")
            QMessageBox.critical(
                self, f"{editor.name} — Error",
                f"{type(e).__name__}: {e}"
            )
            return

        _lg.info(f"register result: ok={result.ok} msg={result.message}")
        if result.ok:
            QMessageBox.information(self, f"{editor.name} — Registered", result.message)
        else:
            QMessageBox.warning(self, f"{editor.name} — Failed", result.message)
        self._refresh_editor_list()

    def _unregister_editor(self, editor):
        """Unregister from one editor, with confirmation."""
        from src.core.editor_integration import unregister
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            f"Unregister {editor.name}?",
            f"Remove VenvStudio's entries from {editor.name} settings?\n\n"
            f"A backup (.vs-backup) will be made before any change. "
            f"Other settings stay untouched.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            result = unregister(editor)
        except Exception as e:
            QMessageBox.critical(
                self, f"{editor.name} — Error",
                f"{type(e).__name__}: {e}"
            )
            return

        if result.ok:
            QMessageBox.information(self, f"{editor.name} — Unregistered", result.message)
        else:
            QMessageBox.warning(self, f"{editor.name} — Failed", result.message)
        self._refresh_editor_list()

    def _register_all_editors(self):
        """Bulk register with every installed editor."""
        from src.core.editor_integration import register_all
        from PySide6.QtWidgets import QMessageBox
        from pathlib import Path

        venv_dir = Path(self._get_editor_venv_dir())
        if not venv_dir.exists():
            try:
                venv_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.warning(
                    self, "Venv directory error",
                    f"Could not create {venv_dir}:\n{e}"
                )
                return

        results = register_all(venv_dir)
        if not results:
            QMessageBox.information(
                self, "No editors",
                "No supported editors detected on this machine."
            )
            return

        ok = [r for r in results if r.ok]
        fail = [r for r in results if not r.ok]
        msg_parts = []
        if ok:
            msg_parts.append(
                "Registered successfully:\n" +
                "\n".join(f"  ✓ {r.editor_id}: {r.message}" for r in ok)
            )
        if fail:
            msg_parts.append(
                "\nFailed:\n" +
                "\n".join(f"  ✗ {r.editor_id}: {r.message}" for r in fail)
            )
        QMessageBox.information(
            self, "Register all — Results", "\n".join(msg_parts)
        )
        self._refresh_editor_list()
