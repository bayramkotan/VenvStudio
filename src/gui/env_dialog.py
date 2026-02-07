"""
VenvStudio - Environment Creation Dialog
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.utils.platform_utils import find_system_pythons


class EnvCreateDialog(QDialog):
    """Dialog for creating a new virtual environment."""

    env_created = Signal(str)  # emits env name on success

    def __init__(self, venv_manager, config_manager, parent=None):
        super().__init__(parent)
        self.venv_manager = venv_manager
        self.config = config_manager
        self.pythons = find_system_pythons()

        self.setWindowTitle("Create New Environment")
        self.setMinimumWidth(500)
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

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., my-project, data-science, web-api")
        form_layout.addRow("Name:", self.name_input)

        # Location
        loc_layout = QHBoxLayout()
        self.location_label = QLabel(str(self.config.get_venv_base_dir()))
        self.location_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        loc_layout.addWidget(self.location_label, 1)
        change_btn = QPushButton("Change")
        change_btn.setObjectName("secondary")
        change_btn.setFixedWidth(80)
        change_btn.clicked.connect(self._change_location)
        loc_layout.addWidget(change_btn)
        form_layout.addRow("Location:", loc_layout)

        # Python version
        self.python_combo = QComboBox()
        self.python_combo.addItem("System Default (python3)", "")
        for version, path in self.pythons:
            self.python_combo.addItem(f"Python {version} ({path})", path)
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

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.create_btn = QPushButton("  Create Environment  ")
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
            self.venv_manager.set_base_dir(__import__("pathlib").Path(directory))
            self.location_label.setText(directory)

    def _create(self):
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Warning", "Please enter an environment name.")
            return

        # Validate name
        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in name):
            QMessageBox.warning(
                self, "Warning",
                "Environment name contains invalid characters.\n"
                "Avoid: spaces, /, \\, :, *, ?, \", <, >, |"
            )
            return

        python_path = self.python_combo.currentData() or None

        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")

        success, message = self.venv_manager.create_venv(
            name=name,
            python_path=python_path,
            with_pip=True,
            system_site_packages=self.system_packages_cb.isChecked(),
        )

        self.create_btn.setEnabled(True)
        self.create_btn.setText("  Create Environment  ")

        if success:
            self.config.add_recent_env(name)
            self.env_created.emit(name)
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)
