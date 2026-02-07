"""
VenvStudio - Package Management Panel
Browse catalog, install, uninstall, import/export requirements
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QTabWidget, QCheckBox, QFileDialog, QMessageBox,
    QTextEdit, QComboBox, QProgressBar, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont

from src.core.pip_manager import PipManager
from src.utils.constants import PACKAGE_CATALOG, PRESETS

from pathlib import Path


class WorkerThread(QThread):
    """Generic worker thread for async operations."""
    finished = Signal(bool, str)
    progress = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.kwargs["callback"] = self.progress.emit
            success, msg = self.func(*self.args, **self.kwargs)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class PackagePanel(QWidget):
    """Package management panel with catalog browsing and pip operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pip_manager = None
        self.current_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()

        # Tab 1: Installed packages
        self.tabs.addTab(self._create_installed_tab(), "📦 Installed")

        # Tab 2: Package catalog
        self.tabs.addTab(self._create_catalog_tab(), "🛒 Catalog")

        # Tab 3: Quick install presets
        self.tabs.addTab(self._create_presets_tab(), "⚡ Presets")

        # Tab 4: Manual install
        self.tabs.addTab(self._create_manual_tab(), "⌨️ Manual Install")

        layout.addWidget(self.tabs)

        # Status bar
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(40)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(12, 4, 12, 4)

        self.status_label = QLabel("Select an environment to manage packages")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        status_layout.addWidget(self.status_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(self.status_bar)

    def _create_installed_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter installed packages...")
        self.search_input.textChanged.connect(self._filter_installed)
        toolbar.addWidget(self.search_input, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh_packages)
        toolbar.addWidget(refresh_btn)

        uninstall_btn = QPushButton("Uninstall Selected")
        uninstall_btn.setObjectName("danger")
        uninstall_btn.clicked.connect(self._uninstall_selected)
        toolbar.addWidget(uninstall_btn)

        layout.addLayout(toolbar)

        # Packages table
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

        # Bottom toolbar
        bottom = QHBoxLayout()

        self.pkg_count_label = QLabel("0 packages")
        self.pkg_count_label.setStyleSheet("color: #a6adc8;")
        bottom.addWidget(self.pkg_count_label)

        bottom.addStretch()

        export_btn = QPushButton("Export requirements.txt")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export_requirements)
        bottom.addWidget(export_btn)

        import_btn = QPushButton("Import requirements.txt")
        import_btn.setObjectName("secondary")
        import_btn.clicked.connect(self._import_requirements)
        bottom.addWidget(import_btn)

        layout.addLayout(bottom)
        return widget

    def _create_catalog_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Category selector
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

        install_selected_btn = QPushButton("Install Selected")
        install_selected_btn.setObjectName("success")
        install_selected_btn.clicked.connect(self._install_catalog_selected)
        cat_layout.addWidget(install_selected_btn)

        layout.addLayout(cat_layout)

        # Catalog table
        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(4)
        self.catalog_table.setHorizontalHeaderLabels(["", "Package", "Description", "Category"])
        self.catalog_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.catalog_table.setColumnWidth(0, 40)
        self.catalog_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.catalog_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.catalog_table.setAlternatingRowColors(True)
        self.catalog_table.verticalHeader().setVisible(False)
        layout.addWidget(self.catalog_table)

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

            # Preset name
            name_label = QLabel(preset_name)
            name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
            card_layout.addWidget(name_label)

            # Package list
            pkg_text = ", ".join(packages)
            pkg_label = QLabel(pkg_text)
            pkg_label.setWordWrap(True)
            pkg_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
            card_layout.addWidget(pkg_label)

            # Install button
            install_btn = QPushButton(f"Install ({len(packages)} packages)")
            install_btn.setObjectName("success")
            install_btn.clicked.connect(lambda checked, pkgs=packages: self._install_packages(pkgs))
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

        # Instructions
        info = QLabel(
            "Enter package names separated by spaces or newlines.\n"
            "You can specify versions like: numpy==1.24.0 or pandas>=2.0"
        )
        info.setObjectName("subheader")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Text input
        self.manual_input = QTextEdit()
        self.manual_input.setPlaceholderText(
            "numpy pandas matplotlib\n"
            "scikit-learn==1.3.0\n"
            "requests>=2.28"
        )
        layout.addWidget(self.manual_input)

        # Buttons
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

        # Output log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(200)
        self.output_log.setPlaceholderText("Installation output will appear here...")
        layout.addWidget(self.output_log)

        return widget

    def set_venv(self, venv_path: Path):
        """Set the active virtual environment."""
        self.pip_manager = PipManager(venv_path)
        self.refresh_packages()
        self.status_label.setText(f"Environment: {venv_path.name}")

    def refresh_packages(self):
        """Refresh the installed packages list."""
        if not self.pip_manager:
            return

        packages = self.pip_manager.list_packages()
        self.packages_table.setRowCount(len(packages))

        for i, pkg in enumerate(packages):
            # Package name
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            # Version
            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            # Checkbox for selection
            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        self.pkg_count_label.setText(f"{len(packages)} packages")

    def _filter_installed(self, text: str):
        """Filter installed packages by name."""
        for row in range(self.packages_table.rowCount()):
            item = self.packages_table.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.packages_table.setRowHidden(row, not match)

    def _populate_catalog(self):
        """Populate catalog table based on selected category."""
        selected = self.category_combo.currentData()
        self.catalog_table.setRowCount(0)

        categories = PACKAGE_CATALOG if selected == "all" else {selected: PACKAGE_CATALOG.get(selected, {})}
        row = 0

        for cat_name, cat_data in categories.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                self.catalog_table.insertRow(row)

                # Checkbox
                cb = QCheckBox()
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.catalog_table.setCellWidget(row, 0, cb_widget)

                # Name
                name_item = QTableWidgetItem(pkg["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_font = QFont()
                name_font.setBold(True)
                name_item.setFont(name_font)
                self.catalog_table.setItem(row, 1, name_item)

                # Description
                desc_item = QTableWidgetItem(pkg["desc"])
                desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 2, desc_item)

                # Category
                cat_item = QTableWidgetItem(cat_name)
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 3, cat_item)

                row += 1

    def _install_catalog_selected(self):
        """Install selected packages from catalog."""
        packages = []
        for row in range(self.catalog_table.rowCount()):
            cb_widget = self.catalog_table.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.catalog_table.item(row, 1)
                    if item:
                        packages.append(item.text())

        if not packages:
            QMessageBox.information(self, "Info", "No packages selected. Check the boxes next to packages you want to install.")
            return

        self._install_packages(packages)

    def _install_packages(self, packages: list):
        """Install a list of packages using a worker thread."""
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected. Please select an environment first.")
            return

        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following packages?\n\n{', '.join(packages)}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.output_log.clear()

        self.current_worker = WorkerThread(self.pip_manager.install_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _install_manual(self):
        """Install packages from manual text input."""
        text = self.manual_input.toPlainText().strip()
        if not text:
            return

        packages = text.split()
        self._install_packages(packages)

    def _uninstall_selected(self):
        """Uninstall selected packages from the installed list."""
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
            f"Uninstall the following packages?\n\n{', '.join(packages)}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _export_requirements(self):
        """Export installed packages to requirements.txt."""
        if not self.pip_manager:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Requirements",
            "requirements.txt",
            "Text Files (*.txt)",
        )
        if filepath:
            success, msg = self.pip_manager.export_requirements(Path(filepath))
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)

    def _import_requirements(self):
        """Import and install from requirements.txt."""
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Requirements",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if filepath:
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.import_requirements, Path(filepath)
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _on_progress(self, message: str):
        self.status_label.setText(message)
        self.output_log.append(message)

    def _on_install_finished(self, success: bool, message: str):
        self._set_busy(False)
        self.output_log.append(f"\n{'✅ Success' if success else '❌ Failed'}: {message[:500]}")

        if success:
            self.status_label.setText("Operation completed successfully")
            self.refresh_packages()
        else:
            self.status_label.setText("Operation failed")
            QMessageBox.critical(self, "Error", message[:500])

    def _set_busy(self, busy: bool):
        self.progress_bar.setVisible(busy)
        self.tabs.setEnabled(not busy)
