"""
VenvStudio - Environment Creation Dialog
With progress bar, status messages, and cancel support
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread

from src.utils.platform_utils import find_system_pythons


class CreateWorker(QThread):
    """Worker thread for async environment creation."""
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, venv_manager, name, python_path, with_pip, system_site_packages):
        super().__init__()
        self.venv_manager = venv_manager
        self.name = name
        self.python_path = python_path
        self.with_pip = with_pip
        self.system_site_packages = system_site_packages
        self._cancelled = False

    def run(self):
        success, msg = self.venv_manager.create_venv(
            name=self.name,
            python_path=self.python_path,
            with_pip=self.with_pip,
            system_site_packages=self.system_site_packages,
            callback=self._on_progress,
        )
        if self._cancelled:
            # Cleanup if cancelled
            import shutil
            venv_path = self.venv_manager.base_dir / self.name
            if venv_path.exists():
                shutil.rmtree(venv_path, ignore_errors=True)
            self.finished.emit(False, "Creation cancelled by user")
        else:
            self.finished.emit(success, msg)

    def _on_progress(self, message):
        if not self._cancelled:
            self.progress.emit(message)

    def cancel(self):
        self._cancelled = True


class EnvCreateDialog(QDialog):
    """Dialog for creating a new virtual environment."""

    env_created = Signal(str)

    def __init__(self, venv_manager, config_manager, parent=None):
        super().__init__(parent)
        self.venv_manager = venv_manager
        self.config = config_manager
        self.pythons = find_system_pythons()
        self.worker = None

        self.setWindowTitle("Create New Environment")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Create New Environment")
        title.setObjectName("header")
        layout.addWidget(title)

        subtitle = QLabel("Set up a fresh Python virtual environment")
        subtitle.setObjectName("subheader")
        layout.addWidget(subtitle)

        # Form
        form_group = QGroupBox("Environment Settings")
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., my-project, data-science, web-api")
        self.name_input.returnPressed.connect(self._create)
        form_layout.addRow("Name:", self.name_input)

        loc_layout = QHBoxLayout()
        self.location_label = QLabel(str(self.config.get_venv_base_dir()))
        self.location_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        loc_layout.addWidget(self.location_label, 1)
        change_btn = QPushButton("Browse")
        change_btn.setObjectName("secondary")
        change_btn.setFixedHeight(28)
        change_btn.setToolTip("Browse for a different folder")
        change_btn.setFocusPolicy(Qt.NoFocus)
        change_btn.setDefault(False)
        change_btn.setAutoDefault(False)
        change_btn.clicked.connect(self._change_location)
        loc_layout.addWidget(change_btn)
        form_layout.addRow("Location:", loc_layout)

        self.python_combo = QComboBox()
        self.python_combo.addItem("System Default", "")
        for version, path in self.pythons:
            import os
            norm = os.path.normpath(path)
            self.python_combo.addItem(f"Python {version} ({norm})", norm)

        # Also add custom pythons from config
        custom_pythons = self.config.get("custom_pythons", [])
        print(f"[DEBUG] EnvDialog custom_pythons from config: {custom_pythons}")
        for entry in custom_pythons:
            import os
            raw_path = entry.get("path", "")
            if not raw_path:
                continue
            norm = os.path.normpath(raw_path)
            ver = entry.get("version", "?")
            # Avoid duplicate (case-insensitive on Windows)
            found = False
            for i in range(self.python_combo.count()):
                existing = self.python_combo.itemData(i) or ""
                if existing and os.path.normpath(existing).lower() == norm.lower():
                    found = True
                    break
            if not found:
                self.python_combo.addItem(f"Python {ver} (Custom: {norm})", norm)
                print(f"[DEBUG] Added custom python to env dialog: {ver} → {norm}")
            else:
                print(f"[DEBUG] Skipped duplicate: {norm}")

        form_layout.addRow("Python:", self.python_combo)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.upgrade_pip_cb = QCheckBox("Upgrade pip after creation")
        self.upgrade_pip_cb.setChecked(True)
        options_layout.addWidget(self.upgrade_pip_cb)

        self.system_packages_cb = QCheckBox("Include system site-packages")
        self.system_packages_cb.setChecked(False)
        options_layout.addWidget(self.system_packages_cb)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Progress area (hidden initially)
        self.progress_frame = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        progress_layout.addWidget(self.progress_bar)

        # Command hint (shows equivalent terminal commands)
        self.cmd_label = QLabel("")
        self.cmd_label.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 8px; color: #a6e3a1; "
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        self.cmd_label.setWordWrap(True)
        self.cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.cmd_label.setVisible(False)
        progress_layout.addWidget(self.cmd_label)

        self.progress_frame.setLayout(progress_layout)
        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("  Create Environment  ")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._create)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

    def _change_location(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Base Directory",
            str(self.config.get_venv_base_dir()),
        )
        if directory:
            self.config.set_venv_base_dir(directory)
            self.venv_manager.set_base_dir(Path(directory))
            self.location_label.setText(directory)

    def _create(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Warning", "Please enter an environment name.")
            return

        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in name):
            QMessageBox.warning(
                self, "Warning",
                "Environment name contains invalid characters.\n"
                "Avoid: spaces, /, \\, :, *, ?, \", <, >, |"
            )
            return

        python_path = self.python_combo.currentData() or None

        # Show progress, disable form
        self.progress_frame.setVisible(True)
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        self.name_input.setEnabled(False)
        self.python_combo.setEnabled(False)
        self.status_label.setText("⏳ Initializing environment...")
        self.cancel_btn.setText("⛔ Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setStyleSheet("")  # force style refresh

        # Show educational command hints - platform specific
        py_exe = python_path or "python"
        location = self.location_label.text()
        import os
        venv_path = os.path.join(location, name)

        from src.utils.platform_utils import get_platform
        cmds = [f"💡 Equivalent terminal commands:"]
        cmds.append(f"$ {py_exe} -m venv {venv_path}")

        if get_platform() == "windows":
            cmds.append(f"$ {venv_path}\\Scripts\\Activate.ps1")
        elif get_platform() == "macos":
            cmds.append(f"$ source {venv_path}/bin/activate")
        else:
            cmds.append(f"$ source {venv_path}/bin/activate")

        cmds.append(f"$ pip install --upgrade pip")
        self.cmd_label.setText("\n".join(cmds))
        self.cmd_label.setVisible(True)

        # Start worker
        self.worker = CreateWorker(
            self.venv_manager, name, python_path,
            with_pip=True,
            system_site_packages=self.system_packages_cb.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message):
        self.status_label.setText(f"⏳ {message}")

    def _on_finished(self, success, message):
        self.worker = None
        self._reset_ui()

        if success:
            name = self.name_input.text().strip()
            self.config.add_recent_env(name)
            self.env_created.emit(name)
            self.status_label.setText("✅ " + message)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            self.status_label.setText("❌ " + message[:200])
            QMessageBox.critical(self, "Error", message)

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel",
                "Are you sure you want to cancel environment creation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.status_label.setText("⛔ Cancelling...")
                self.worker.cancel()
                self.worker.wait(5000)
                self._reset_ui()
                self.status_label.setText("⛔ Creation cancelled")
        else:
            self.reject()

    def _reset_ui(self):
        self.create_btn.setEnabled(True)
        self.create_btn.setText("  Create Environment  ")
        self.name_input.setEnabled(True)
        self.python_combo.setEnabled(True)
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setStyleSheet("")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        super().closeEvent(event)
