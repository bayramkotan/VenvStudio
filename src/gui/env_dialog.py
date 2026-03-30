"""
VenvStudio - Environment Creation Dialog
With progress bar, status messages, and cancel support
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QProgressBar, QSizePolicy,
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
        self.setMinimumSize(920, 420)  # min size, not fixed — allows DPI scaling
        self.resize(960, 460)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        # Title
        title = QLabel("Create New Environment")
        title.setObjectName("header")
        root.addWidget(title)

        subtitle = QLabel("Set up a fresh Python virtual environment")
        subtitle.setObjectName("subheader")
        root.addWidget(subtitle)

        # Horizontal body
        body = QHBoxLayout()
        body.setSpacing(16)

        # LEFT: form + options
        left = QVBoxLayout()
        left.setSpacing(10)

        form_group = QGroupBox("Environment Settings")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., my-project, data-science, web-api")
        self.name_input.returnPressed.connect(self._create)
        form_layout.addRow("Name:", self.name_input)

        loc_layout = QHBoxLayout()
        loc_layout.setSpacing(8)
        self.location_label = QLabel(str(self.config.get_venv_base_dir()))
        self.location_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.location_label.setMinimumWidth(120)
        loc_layout.addWidget(self.location_label, 1)
        change_btn = QPushButton("Browse")
        change_btn.setObjectName("secondary")
        change_btn.setFixedHeight(28)
        change_btn.setFixedWidth(80)
        change_btn.setToolTip("Browse for a different folder")
        change_btn.setFocusPolicy(Qt.NoFocus)
        change_btn.setDefault(False)
        change_btn.setAutoDefault(False)
        change_btn.clicked.connect(self._change_location)
        loc_layout.addWidget(change_btn)
        form_layout.addRow("Location:", loc_layout)

        self.python_combo = QComboBox()
        self.python_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.python_combo.addItem("System Default", "")

        import os
        seen_real = {}
        for version, path in self.pythons:
            norm = os.path.normpath(path)
            try:
                real = os.path.realpath(path)
            except OSError:
                real = norm
            if real in seen_real:
                if len(norm) < len(seen_real[real][1]):
                    seen_real[real] = (version, norm)
            else:
                seen_real[real] = (version, norm)

        listed_paths = set()
        for _real, (version, norm) in seen_real.items():
            self.python_combo.addItem(f"Python {version} ({norm})", norm)
            listed_paths.add(os.path.normcase(norm))

        custom_pythons = self.config.get("custom_pythons", [])
        print(f"[DEBUG] EnvDialog custom_pythons from config: {custom_pythons}")
        for entry in custom_pythons:
            raw_path = entry.get("path", "")
            if not raw_path:
                continue
            norm = os.path.normpath(raw_path)
            norm_case = os.path.normcase(norm)
            ver = entry.get("version", "?")
            if norm_case in listed_paths:
                print(f"[DEBUG] Skipped duplicate: {norm}")
                continue
            listed_paths.add(norm_case)
            self.python_combo.addItem(f"Python {ver} (Custom: {norm})", norm)
            print(f"[DEBUG] Added custom python to env dialog: {ver} -> {norm}")

        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                exe_case = os.path.normcase(exe_path)
                if exe_case in listed_paths:
                    continue
                listed_paths.add(exe_case)
                ver = py.get("version", "?")
                self.python_combo.addItem(
                    f"Python {ver} (Downloaded: {exe_path})", exe_path
                )
                print(f"[DEBUG] Added downloaded python to env dialog: {ver} -> {exe_path}")
        except Exception as e:
            print(f"[DEBUG] Could not load downloaded pythons: {e}")

        form_layout.addRow("Python:", self.python_combo)

        # Seçili Python'un tam yolunu göster
        self.python_path_label = QLabel("")
        self.python_path_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.python_path_label.setWordWrap(True)
        form_layout.addRow("", self.python_path_label)
        self.python_combo.currentIndexChanged.connect(self._on_python_changed)
        self._on_python_changed(0)  # İlk seçimi göster
        form_group.setLayout(form_layout)
        left.addWidget(form_group)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        self.upgrade_pip_cb = QCheckBox("Upgrade pip after creation")
        self.upgrade_pip_cb.setChecked(True)
        options_layout.addWidget(self.upgrade_pip_cb)
        self.system_packages_cb = QCheckBox("Include system site-packages")
        self.system_packages_cb.setChecked(False)
        options_layout.addWidget(self.system_packages_cb)
        options_group.setLayout(options_layout)
        left.addWidget(options_group)
        left.addStretch()

        body.addLayout(left, stretch=4)

        # RIGHT: terminal (always visible, never causes resize)
        right_group = QGroupBox("Progress")
        right_inner = QVBoxLayout()
        right_inner.setSpacing(8)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #585b70; font-size: 12px;")
        right_inner.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        right_inner.addWidget(self.progress_bar)

        self.cmd_label = QLabel(
            "💡 Equivalent terminal commands\nwill appear here when creation starts."
        )
        self.cmd_label.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 14px; color: #585b70; "
            "font-family: Consolas, monospace; font-size: 14px;"
        )
        self.cmd_label.setWordWrap(True)
        self.cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.cmd_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.cmd_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_inner.addWidget(self.cmd_label, stretch=1)

        right_group.setLayout(right_inner)
        right_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(right_group, stretch=5)

        root.addLayout(body, stretch=1)

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

        root.addLayout(btn_layout)

    def _on_python_changed(self, index):
        """Seçili Python'un tam yolunu göster."""
        data = self.python_combo.currentData()
        if data:
            self.python_path_label.setText(f"📍 {data}")
        else:
            import shutil, sys
            # System default — hangi python kullanılacağını göster
            py = shutil.which("python") or shutil.which("python3") or sys.executable
            self.python_path_label.setText(f"📍 {py} (system default)")

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

        self.progress_bar.setVisible(True)
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        self.name_input.setEnabled(False)
        self.python_combo.setEnabled(False)
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.status_label.setText("Initializing environment...")
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setStyleSheet("")

        py_exe = python_path or "python"
        location = self.location_label.text()
        import os
        venv_path = os.path.join(location, name)

        from src.utils.platform_utils import get_platform
        cmds = ["💡  Equivalent terminal commands:", ""]
        cmds.append(f"$ {py_exe} -m venv {venv_path}")
        if get_platform() == "windows":
            cmds.append(f"$ {venv_path}\\Scripts\\Activate.ps1")
        else:
            cmds.append(f"$ source {venv_path}/bin/activate")
        cmds.append("$ pip install --upgrade pip")

        self.cmd_label.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 14px; color: #a6e3a1; "
            "font-family: Consolas, monospace; font-size: 14px;"
        )
        self.cmd_label.setText("\n".join(cmds))

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
