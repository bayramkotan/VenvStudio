"""
VenvStudio - Package Management Panel
Full featured: cancel, catalog status, command hints, apply changes toggle
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTabWidget, QCheckBox, QFileDialog, QMessageBox,
    QTextEdit, QComboBox, QProgressBar, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QSizePolicy, QDialog, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QColor

from src.core.pip_manager import PipManager
from src.utils.constants import PACKAGE_CATALOG, PRESETS, COMMAND_HINTS

from pathlib import Path


class WorkerThread(QThread):
    """Worker thread with cancel support."""
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
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
            self.finished.emit(False, str(e))

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
        info.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(info)

        cmd_frame = QFrame()
        cmd_frame.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 8px; padding: 12px;"
        )
        cmd_layout = QVBoxLayout(cmd_frame)
        cmd_label = QLabel(f"<code style='font-size:14px; color:#a6e3a1;'>{command}</code>")
        cmd_label.setTextFormat(Qt.RichText)
        cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cmd_layout.addWidget(cmd_label)
        layout.addWidget(cmd_frame)

        tip = QLabel("💡 You can copy this command and run it in any terminal.")
        tip.setStyleSheet("font-size: 11px; color: #6c7086;")
        layout.addWidget(tip)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PackagePanel(QWidget):
    """Package management panel with catalog browsing and pip operations."""
    env_refresh_requested = Signal()  # Signal to refresh env list in main window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pip_manager = None
        self.current_worker = None
        self.installed_package_names = set()
        self._catalog_initial_state = {}  # Track original checkbox states
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Environment indicator at top
        self.env_bar = QFrame()
        self.env_bar.setFixedHeight(44)
        self.env_bar.setStyleSheet(
            "background-color: rgba(137, 180, 250, 0.1); "
            "border-bottom: 1px solid #313244;"
        )
        env_bar_layout = QHBoxLayout(self.env_bar)
        env_bar_layout.setContentsMargins(16, 0, 16, 0)

        self.env_name_label = QLabel("No environment selected")
        self.env_name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        env_bar_layout.addWidget(self.env_name_label)
        env_bar_layout.addStretch()

        self.env_pkg_count = QLabel("")
        self.env_pkg_count.setStyleSheet("color: #a6adc8; font-size: 12px;")
        env_bar_layout.addWidget(self.env_pkg_count)

        layout.addWidget(self.env_bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_installed_tab(), "📦 Installed")
        self.tabs.addTab(self._create_catalog_tab(), "🛒 Catalog")
        self.tabs.addTab(self._create_presets_tab(), "⚡ Presets")
        self.tabs.addTab(self._create_manual_tab(), "⌨️ Manual Install")
        layout.addWidget(self.tabs)

        # Status bar with cancel button
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(44)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(12, 4, 12, 4)

        self.status_label = QLabel("Select an environment to manage packages")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        status_layout.addWidget(self.status_label, 1)

        self.cancel_btn = QPushButton("⛔ Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_operation)
        status_layout.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(self.status_bar)

    # ── Tab Builders ──

    def _create_installed_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter installed packages...")
        self.search_input.textChanged.connect(self._filter_installed)
        toolbar.addWidget(self.search_input, 1)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh_packages)
        toolbar.addWidget(refresh_btn)

        uninstall_btn = QPushButton("🗑️ Uninstall Selected")
        uninstall_btn.setObjectName("danger")
        uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(uninstall_btn)

        layout.addLayout(toolbar)

        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(3)
        self.packages_table.setHorizontalHeaderLabels(["Package", "Version", ""])
        self.packages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.packages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.packages_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.packages_table.setColumnWidth(2, 40)
        self.packages_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.packages_table.setAlternatingRowColors(True)
        self.packages_table.verticalHeader().setVisible(False)
        layout.addWidget(self.packages_table)

        bottom = QHBoxLayout()
        self.pkg_count_label = QLabel("0 packages")
        self.pkg_count_label.setStyleSheet("color: #a6adc8;")
        bottom.addWidget(self.pkg_count_label)
        bottom.addStretch()

        export_btn = QPushButton("📤 Export requirements.txt")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export_requirements)
        bottom.addWidget(export_btn)

        import_btn = QPushButton("📥 Import requirements.txt")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_requirements)
        bottom.addWidget(import_btn)

        layout.addLayout(bottom)
        return widget

    def _create_catalog_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        cat_layout = QHBoxLayout()
        cat_label = QLabel("Category:")
        cat_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "all")
        for cat_name in PACKAGE_CATALOG:
            self.category_combo.addItem(cat_name, cat_name)
        self.category_combo.currentIndexChanged.connect(self._populate_catalog)
        cat_layout.addWidget(self.category_combo, 1)
        cat_layout.addStretch()

        legend = QLabel("☑ installed  |  Check→install  Uncheck→remove")
        legend.setStyleSheet("color: #a6adc8; font-size: 11px;")
        cat_layout.addWidget(legend)
        layout.addLayout(cat_layout)

        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(4)
        self.catalog_table.setHorizontalHeaderLabels(["Install", "Package", "Description", "Category"])
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.catalog_table.setColumnWidth(0, 55)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.verticalHeader().setVisible(False)
        layout.addWidget(self.catalog_table)

        # Bottom: changes summary + Apply button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.changes_label = QLabel("")
        self.changes_label.setStyleSheet("color: #f9e2af; font-size: 12px;")
        bottom_layout.addWidget(self.changes_label)

        self.apply_btn = QPushButton("  ✅ Apply Changes  ")
        self.apply_btn.setObjectName("success")
        self.apply_btn.setFixedHeight(38)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_catalog_changes)
        bottom_layout.addWidget(self.apply_btn)

        layout.addLayout(bottom_layout)

        self._populate_catalog()
        return widget

    def _create_presets_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)
        grid.setContentsMargins(12, 12, 12, 12)

        row = 0
        for preset_name, packages in PRESETS.items():
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)

            name_label = QLabel(preset_name)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            card_layout.addWidget(name_label)

            pkg_text = ", ".join(packages)
            pkg_label = QLabel(pkg_text)
            pkg_label.setWordWrap(True)
            pkg_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
            card_layout.addWidget(pkg_label)

            install_btn = QPushButton(f"Install ({len(packages)} packages)")
            install_btn.setObjectName("success")
            install_btn.clicked.connect(
                lambda checked, pkgs=packages, name=preset_name: self._install_packages(pkgs, hint_name=name)
            )
            card_layout.addWidget(install_btn)

            grid.addWidget(card, row // 2, row % 2)
            row += 1

        grid.setRowStretch(row // 2 + 1, 1)
        scroll.setWidget(container)
        return scroll

    def _create_manual_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "Enter package names separated by spaces or newlines.\n"
            "You can specify versions like: numpy==1.24.0 or pandas>=2.0"
        )
        info.setObjectName("subheader")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.manual_input = QTextEdit()
        self.manual_input.setPlaceholderText(
            "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28"
        )
        layout.addWidget(self.manual_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.manual_input.clear)
        btn_layout.addWidget(clear_btn)

        install_btn = QPushButton("Install Packages")
        install_btn.setObjectName("success")
        install_btn.clicked.connect(self._install_manual)
        btn_layout.addWidget(install_btn)

        layout.addLayout(btn_layout)

        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(200)
        self.output_log.setPlaceholderText("Installation output will appear here...")
        layout.addWidget(self.output_log)

        return widget

    # ── Public Methods ──

    def set_venv(self, venv_path: Path):
        self.pip_manager = PipManager(venv_path)
        self.env_name_label.setText(f"🐍 Environment: {venv_path.name}")
        self.refresh_packages()
        self.status_label.setText(f"Environment: {venv_path.name}")

    def refresh_packages(self):
        """Refresh installed packages list - shows ALL packages."""
        if not self.pip_manager:
            return

        packages = self.pip_manager.list_packages()
        self.installed_package_names = {pkg.name.lower() for pkg in packages}

        self.packages_table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        count = len(packages)
        self.pkg_count_label.setText(f"{count} packages")
        self.env_pkg_count.setText(f"{count} packages installed")

        # Update catalog checkboxes
        self._populate_catalog()

    # ── Catalog ──

    def _populate_catalog(self):
        selected = self.category_combo.currentData()
        self.catalog_table.setRowCount(0)
        self._catalog_initial_state = {}

        categories = PACKAGE_CATALOG if selected == "all" else {selected: PACKAGE_CATALOG.get(selected, {})}
        row = 0

        for cat_name, cat_data in categories.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                self.catalog_table.insertRow(row)

                is_installed = pkg["name"].lower() in self.installed_package_names

                cb = QCheckBox()
                cb.setChecked(is_installed)
                cb.stateChanged.connect(self._on_catalog_checkbox_changed)
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.catalog_table.setCellWidget(row, 0, cb_widget)

                name_item = QTableWidgetItem(pkg["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_font = QFont()
                name_font.setBold(True)
                name_item.setFont(name_font)
                if is_installed:
                    name_item.setForeground(QColor("#a6e3a1"))
                self.catalog_table.setItem(row, 1, name_item)

                desc_item = QTableWidgetItem(pkg["desc"])
                desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 2, desc_item)

                cat_item = QTableWidgetItem(cat_name)
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 3, cat_item)

                self._catalog_initial_state[row] = is_installed
                row += 1

        self._update_apply_button()

    def _on_catalog_checkbox_changed(self):
        self._update_apply_button()

    def _update_apply_button(self):
        """Enable Apply button only if there are actual changes."""
        to_install, to_uninstall = self._get_catalog_changes()
        has_changes = bool(to_install or to_uninstall)
        self.apply_btn.setEnabled(has_changes)

        if has_changes:
            parts = []
            if to_install:
                parts.append(f"+{len(to_install)} install")
            if to_uninstall:
                parts.append(f"-{len(to_uninstall)} remove")
            self.changes_label.setText(" | ".join(parts))
        else:
            self.changes_label.setText("")

    def _get_catalog_changes(self):
        to_install = []
        to_uninstall = []

        for row in range(self.catalog_table.rowCount()):
            cb_widget = self.catalog_table.cellWidget(row, 0)
            if not cb_widget:
                continue
            cb = cb_widget.findChild(QCheckBox)
            if not cb:
                continue
            name_item = self.catalog_table.item(row, 1)
            if not name_item:
                continue

            pkg_name = name_item.text()
            is_checked = cb.isChecked()
            was_installed = self._catalog_initial_state.get(row, False)

            if is_checked and not was_installed:
                to_install.append(pkg_name)
            elif not is_checked and was_installed:
                to_uninstall.append(pkg_name)

        return to_install, to_uninstall

    def _apply_catalog_changes(self):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return

        to_install, to_uninstall = self._get_catalog_changes()

        if not to_install and not to_uninstall:
            QMessageBox.information(self, "No Changes", "No changes detected.")
            return

        # Build detailed confirm message
        msg_parts = []
        if to_uninstall:
            msg_parts.append(f"🗑️ Remove ({len(to_uninstall)}):\n  • " + "\n  • ".join(to_uninstall))
        if to_install:
            msg_parts.append(f"📦 Install ({len(to_install)}):\n  • " + "\n  • ".join(to_install))

        reply = QMessageBox.question(
            self, "Apply Changes",
            "Apply the following changes?\n\n" + "\n\n".join(msg_parts),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint
        cmds = []
        if to_uninstall:
            cmds.append(COMMAND_HINTS["uninstall"].format(packages=" ".join(to_uninstall)))
        if to_install:
            cmds.append(COMMAND_HINTS["install"].format(packages=" ".join(to_install)))
        self._show_command_hint("Apply Changes", " && ".join(cmds))

        self._set_busy(True)
        self.output_log.clear()

        if to_uninstall:
            self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, to_uninstall)
            self.current_worker.progress.connect(self._on_progress)
            if to_install:
                self.current_worker.finished.connect(
                    lambda ok, msg: self._chain_install(ok, msg, to_install)
                )
            else:
                self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
        elif to_install:
            self._do_install(to_install)

    def _chain_install(self, uninstall_ok, uninstall_msg, to_install):
        if not uninstall_ok:
            self.output_log.append(f"❌ Uninstall failed: {uninstall_msg[:300]}")
        self.output_log.append("✅ Uninstall done. Starting install...")
        self._do_install(to_install)

    # ── Install / Uninstall ──

    def _install_packages(self, packages: list, hint_name: str = ""):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.\nPlease select an environment first.")
            return

        # Show ALL package names in confirm dialog
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following {len(packages)} package(s)?\n\n• " + "\n• ".join(packages),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint
        cmd = COMMAND_HINTS["install"].format(packages=" ".join(packages))
        self._show_command_hint(hint_name or "Install Packages", cmd)

        self._do_install(packages)

    def _do_install(self, packages):
        """Actually start install worker (no confirm dialog)."""
        self._set_busy(True)
        self.output_log.clear()
        self.current_worker = WorkerThread(self.pip_manager.install_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _install_manual(self):
        text = self.manual_input.toPlainText().strip()
        if not text:
            return
        packages = text.split()
        self._install_packages(packages)

    def _uninstall_selected(self):
        if not self.pip_manager:
            return

        packages = []
        for row in range(self.packages_table.rowCount()):
            cb_widget = self.packages_table.cellWidget(row, 2)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.packages_table.item(row, 0)
                    if item:
                        packages.append(item.text())

        if not packages:
            QMessageBox.information(self, "Info", "No packages selected for uninstall.")
            return

        reply = QMessageBox.warning(
            self, "Confirm Uninstall",
            f"Uninstall {len(packages)} package(s)?\n\n• " + "\n• ".join(packages),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        cmd = COMMAND_HINTS["uninstall"].format(packages=" ".join(packages))
        self._show_command_hint("Uninstall Packages", cmd)

        self._set_busy(True)
        self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _export_requirements(self):
        if not self.pip_manager:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            success, msg = self.pip_manager.export_requirements(Path(filepath))
            self._show_command_hint("Export Requirements", COMMAND_HINTS["freeze"])
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)

    def _import_requirements(self):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Requirements", "", "Text Files (*.txt);;All Files (*)"
        )
        if filepath:
            self._show_command_hint("Import Requirements", COMMAND_HINTS["import_req"])
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.import_requirements, Path(filepath)
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _filter_installed(self, text: str):
        for row in range(self.packages_table.rowCount()):
            item = self.packages_table.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.packages_table.setRowHidden(row, not match)

    # ── Helpers ──

    def _show_command_hint(self, title, command):
        """Show educational command hint dialog."""
        dlg = CommandHintDialog(title, command, self)
        dlg.exec()

    def _on_progress(self, message: str):
        self.status_label.setText(message)
        self.output_log.append(message)

    def _on_install_finished(self, success: bool, message: str):
        self._set_busy(False)
        self.output_log.append(f"\n{'✅ Success' if success else '❌ Failed'}: {message[:500]}")

        if success:
            self.status_label.setText("Operation completed successfully")
            self.refresh_packages()
            # Signal main window to also refresh env list (package counts changed)
            self.env_refresh_requested.emit()
        else:
            self.status_label.setText("Operation failed")
            if "cancelled" not in message.lower():
                QMessageBox.critical(self, "Error", message[:500])

    def _cancel_operation(self):
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Operation",
                "Are you sure you want to cancel the current operation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.status_label.setText("⛔ Cancelling...")
                self.current_worker.cancel()
                if not self.current_worker.wait(3000):
                    self.current_worker.terminate()
                self._set_busy(False)
                self.status_label.setText("⛔ Operation cancelled")
                self.output_log.append("\n⛔ Operation cancelled by user")

    def _set_busy(self, busy: bool):
        self.progress_bar.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.tabs.setEnabled(not busy)
