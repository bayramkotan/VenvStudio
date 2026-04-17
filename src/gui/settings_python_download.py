"""VenvStudio - Settings: Python Download Dialog & Workers"""
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


class _DownloadWorker(QThread):
    """Background worker for downloading Python."""
    progress = Signal(str)
    finished = Signal(bool, str)  # success, message

    def __init__(self, version_info, parent=None):
        super().__init__(parent)
        self.version_info = version_info

    def run(self):
        try:
            from src.core.python_downloader import download_python
            result = download_python(self.version_info, progress_callback=self.progress.emit)
            self.finished.emit(True, str(result))
        except Exception as e:
            self.finished.emit(False, str(e))

class _UpdateCheckWorker(QThread):
    """Background worker for checking PyPI updates."""
    finished = Signal(dict)

    def run(self):
        try:
            from src.core.updater import check_for_update
            result = check_for_update()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e), "update_available": False})

class _FetchWorker(QThread):
    """Background worker for fetching available versions."""
    progress = Signal(str)
    finished = Signal(list)

    def __init__(self, mirror: str = "astral", custom_url: str = "",
                 try_fallbacks: bool = True, parent=None):
        super().__init__(parent)
        self.mirror = mirror
        self.custom_url = custom_url
        self.try_fallbacks = try_fallbacks

    def run(self):
        try:
            from src.core.python_downloader import get_available_versions
            versions = get_available_versions(
                progress_callback=self.progress.emit,
                mirror=self.mirror,
                custom_url=self.custom_url,
                try_fallbacks=self.try_fallbacks,
            )
            self.finished.emit(versions)
        except Exception:
            self.finished.emit([])

class PythonDownloadDialog(QDialog):
    """Dialog for downloading standalone Python builds."""

    def _c(self) -> dict:
        """Return current theme color palette."""
        from src.gui.styles import get_colors
        p = self.parent()
        if p and hasattr(p, "config"):
            return get_colors(p.config.get("theme", "dark"))
        return get_colors("dark")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⬇️ Download Python")
        self.setMinimumSize(550, 420)
        self._versions = []
        self._setup_ui()
        self._fetch_versions()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "Download standalone Python builds for local use"
        )
        header.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        header.setWordWrap(True)
        layout.addWidget(header)

        # ── Mirror selector ─────────────────────────────────────────
        mirror_row = QHBoxLayout()
        mirror_label = QLabel("🌐 Source:")
        mirror_label.setStyleSheet(f"color: {self._c()['fg']}; font-size: {self._c()['fs_base']}px;")
        mirror_row.addWidget(mirror_label)

        self.mirror_combo = QComboBox()
        self.mirror_combo.setStyleSheet(f"font-size: {self._c()['fs_base']}px;")
        from src.core.python_downloader import get_all_mirror_infos
        self._mirror_infos = get_all_mirror_infos()
        for info in self._mirror_infos:
            self.mirror_combo.addItem(info["name"], userData=info["id"])
            idx = self.mirror_combo.count() - 1
            self.mirror_combo.setItemData(idx, info["description"], Qt.ToolTipRole)

        # Preselect saved preference
        try:
            from src.core.config_manager import ConfigManager
            saved = ConfigManager().get("python_download_mirror", "astral")
            for i in range(self.mirror_combo.count()):
                if self.mirror_combo.itemData(i) == saved:
                    self.mirror_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass

        self.mirror_combo.currentIndexChanged.connect(self._on_mirror_changed)
        mirror_row.addWidget(self.mirror_combo, 1)

        self.refetch_btn = QPushButton("🔄")
        self.refetch_btn.setToolTip("Re-fetch versions from selected source")
        self.refetch_btn.setFixedWidth(36)
        self.refetch_btn.clicked.connect(self._fetch_versions)
        mirror_row.addWidget(self.refetch_btn)
        layout.addLayout(mirror_row)

        # ── Custom URL input (shown only when Custom is selected) ────
        self.custom_url_row = QWidget()
        custom_layout = QHBoxLayout(self.custom_url_row)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        cu_label = QLabel("🔗 URL:")
        cu_label.setStyleSheet(f"color: {self._c()['fg']}; font-size: {self._c()['fs_base']}px;")
        custom_layout.addWidget(cu_label)
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText(
            "https://example.com/cpython-3.13.12-x86_64-linux.tar.gz"
        )
        self.custom_url_input.setStyleSheet(f"font-size: {self._c()['fs_base']}px;")
        # Load saved custom URL
        try:
            from src.core.config_manager import ConfigManager
            saved_url = ConfigManager().get("python_download_custom_url", "")
            if saved_url:
                self.custom_url_input.setText(saved_url)
        except Exception:
            pass
        self.custom_url_input.editingFinished.connect(self._on_custom_url_changed)
        custom_layout.addWidget(self.custom_url_input, 1)
        self.custom_url_row.setVisible(False)
        layout.addWidget(self.custom_url_row)

        # Mirror description line
        self.mirror_desc = QLabel("")
        self.mirror_desc.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; "
            f"padding: 2px 4px 4px 4px; font-style: italic;"
        )
        self.mirror_desc.setWordWrap(True)
        layout.addWidget(self.mirror_desc)
        self._update_mirror_desc()

        # Version list
        self.version_list = QListWidget()
        self.version_list.setStyleSheet(
            f"QListWidget {{ font-size: {self._c()['fs_base']}px; }}"
            f"QListWidget::item {{ padding: 6px; }}"
            f"QListWidget::item:selected {{ background-color: {self._c()['accent']}; color: {self._c()['accent_fg']}; }}"
        )
        layout.addWidget(self.version_list)

        # Progress
        self.progress_label = QLabel("Fetching available versions...")
        self.progress_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        # Install locations
        import os as _os
        from src.core.python_downloader import get_pythons_dir
        user_dir = get_pythons_dir()
        if _os.name == "nt":
            system_dir = _os.path.join(_os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Python")
        else:
            system_dir = "/usr/local/bin"
        loc_label = QLabel(
            f"🖥️ System location: {system_dir}\n"
            f"👤 User location: {user_dir}"
        )
        loc_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        loc_label.setWordWrap(True)
        layout.addWidget(loc_label)

        # Buttons
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("👤 User Install")
        self.download_btn.setToolTip("Install to VenvStudio pythons folder (no admin)")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(lambda: self._start_download("user"))
        btn_layout.addWidget(self.download_btn)

        self.system_download_btn = QPushButton("🖥️ System Install")
        self.system_download_btn.setToolTip("Install to Program Files (admin required)")
        self.system_download_btn.setEnabled(False)
        self.system_download_btn.clicked.connect(lambda: self._start_download("system"))
        btn_layout.addWidget(self.system_download_btn)

        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.version_list.currentRowChanged.connect(self._on_selection_changed)

    def _get_current_mirror(self) -> str:
        """Return the currently selected mirror id."""
        data = self.mirror_combo.currentData()
        return data if data else "astral"

    def _get_current_custom_url(self) -> str:
        return self.custom_url_input.text().strip()

    def _update_mirror_desc(self):
        idx = self.mirror_combo.currentIndex()
        if idx >= 0 and idx < len(self._mirror_infos):
            self.mirror_desc.setText(self._mirror_infos[idx]["description"])

    def _on_mirror_changed(self, idx):
        """User picked a different mirror."""
        mirror = self._get_current_mirror()
        self.custom_url_row.setVisible(mirror == "custom")
        self._update_mirror_desc()

        # Persist preference
        try:
            from src.core.config_manager import ConfigManager
            ConfigManager().set("python_download_mirror", mirror)
        except Exception:
            pass

        # Re-fetch unless custom (without URL yet)
        if mirror == "custom" and not self._get_current_custom_url():
            self.progress_label.setText("Enter a URL above, then press 🔄")
            self.version_list.clear()
            return

        self._fetch_versions()

    def _on_custom_url_changed(self):
        """Save custom URL and re-fetch."""
        url = self._get_current_custom_url()
        try:
            from src.core.config_manager import ConfigManager
            ConfigManager().set("python_download_custom_url", url)
        except Exception:
            pass
        if self._get_current_mirror() == "custom" and url:
            self._fetch_versions()

    def _fetch_versions(self):
        """Fetch available versions in background using the selected mirror."""
        mirror = self._get_current_mirror()
        custom_url = self._get_current_custom_url() if mirror == "custom" else ""

        # Reset UI
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText(f"Fetching versions from {mirror}...")
        self.version_list.clear()

        # For custom, no fallbacks (the user picked that URL deliberately)
        try_fallbacks = (mirror != "custom")
        self._fetch_worker = _FetchWorker(
            mirror=mirror, custom_url=custom_url, try_fallbacks=try_fallbacks, parent=self,
        )
        self._fetch_worker.progress.connect(self._on_progress)
        self._fetch_worker.finished.connect(self._on_versions_fetched)
        self._fetch_worker.start()

    def _on_versions_fetched(self, versions):
        self._versions = versions
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        if not versions:
            self.progress_label.setText("❌ Could not fetch versions. Check your internet connection.")
            return

        # Also get installed versions
        from src.core.python_downloader import get_installed_pythons
        installed = {py["version"] for py in get_installed_pythons()}

        self.version_list.clear()
        for v in versions:
            size_mb = v.get("size", 0) / (1024 * 1024)
            is_installed = v["version"] in installed

            if is_installed:
                text = f"✅ Python {v['version']}  —  {size_mb:.0f} MB  (installed)"
            else:
                text = f"🐍 Python {v['version']}  —  {size_mb:.0f} MB"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, v)
            if is_installed:
                item.setForeground(QColor(self._c()['success']))
            self.version_list.addItem(item)

        self.progress_label.setText(f"Found {len(versions)} available versions.")
        self.download_btn.setEnabled(True)
        self.system_download_btn.setEnabled(True)

    def _on_selection_changed(self, row):
        if row < 0:
            self.download_btn.setEnabled(False)
            self.system_download_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return
        item = self.version_list.item(row)
        v = item.data(Qt.UserRole)
        from src.core.python_downloader import get_installed_pythons
        installed = {py["version"] for py in get_installed_pythons()}
        is_installed = v["version"] in installed
        self.download_btn.setEnabled(not is_installed)
        self.system_download_btn.setEnabled(not is_installed)
        self.remove_btn.setEnabled(is_installed)

    def _on_progress(self, text):
        self.progress_label.setText(text)
        # Parse percentage if available
        if "%" in text:
            try:
                pct_str = text.split("(")[-1].split("%")[0]
                pct = int(float(pct_str))
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(pct)
            except (ValueError, IndexError):
                pass

    def _start_download(self, mode="user"):
        row = self.version_list.currentRow()
        if row < 0:
            return

        item = self.version_list.item(row)
        version_info = item.data(Qt.UserRole).copy()
        version_info["_install_mode"] = mode

        if mode == "system":
            from src.utils.platform_utils import get_platform
            version = version_info["version"]
            plat = get_platform()

            if plat == "windows":
                ver_short = version.replace(".", "")[:3]
                target_dir = f"C:\\Program Files\\Python{ver_short}"
            elif plat == "macos":
                target_dir = f"/usr/local/python/{version}"
            else:  # linux
                target_dir = f"/opt/python/{version}"

            confirm = QMessageBox.question(
                self, "🖥️ System Install",
                f"Install Python {version} to:\n\n"
                f"  📂 {target_dir}\n\n"
                f"This requires {'admin' if plat == 'windows' else 'sudo'} permission.\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        self.download_btn.setEnabled(False)
        self.system_download_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)

        self._dl_worker = _DownloadWorker(version_info, parent=self)
        self._dl_worker.progress.connect(self._on_progress)
        self._dl_worker.finished.connect(
            lambda ok, msg: self._on_download_finished(ok, msg, mode)
        )
        self._dl_worker.start()

    def _on_download_finished(self, success, message, mode="user"):
        self.progress_bar.setRange(0, 100)
        if success:
            if mode == "system":
                # Move from user dir to Program Files via admin
                self._move_to_system(message)
            else:
                self.progress_bar.setValue(100)
                self.progress_label.setText("✅ Download complete!")
                QMessageBox.information(self, "✅ Success", f"Python installed to:\n{message}")
                self._fetch_versions()
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"❌ Download failed")
            QMessageBox.critical(self, "Error", f"Download failed:\n{message}")
            self.download_btn.setEnabled(True)
            self.system_download_btn.setEnabled(True)

    def _move_to_system(self, source_dir):
        """Move downloaded Python to system directory (admin/sudo required)."""
        import subprocess, tempfile, os, shutil
        from src.utils.platform_utils import get_platform, subprocess_args
        from pathlib import Path

        source = Path(source_dir)
        plat = get_platform()

        # Find python executable to detect version
        from src.core.python_downloader import get_python_exe
        exe = get_python_exe(source)
        if not exe:
            QMessageBox.critical(self, "Error", "Could not find python executable in downloaded files.")
            return

        try:
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10,
                **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
        except Exception:
            ver = source.name.replace("cpython-", "")

        # The extracted content has a 'python' subfolder
        python_subdir = source / "python"
        actual_source = str(python_subdir) if python_subdir.exists() else str(source)

        # Determine target based on platform
        if plat == "windows":
            ver_short = ver.replace(".", "")[:3]
            target = Path(f"C:\\Program Files\\Python{ver_short}")
        elif plat == "macos":
            target = Path(f"/usr/local/python/{ver}")
        else:  # linux
            target = Path(f"/opt/python/{ver}")

        self.progress_label.setText(f"Installing to {target}...")

        try:
            if plat == "windows":
                self._system_install_windows(actual_source, target, ver, source)
            else:
                self._system_install_unix(actual_source, target, ver, source, plat)
        except Exception as e:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_label.setText("❌ System install failed")
            QMessageBox.critical(self, "Error", f"System install failed:\n{e}")

    def _system_install_windows(self, actual_source, target, ver, source):
        """Windows system install via PowerShell admin elevation."""
        import subprocess, tempfile, os, shutil
        from src.utils.platform_utils import subprocess_args

        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_result.txt")
        ps_script = f'''
try {{
    if (Test-Path '{target}') {{ Remove-Item -Recurse -Force '{target}' }}
    Copy-Item -Recurse '{actual_source}' '{target}'
    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        ps_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_py.ps1")
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_script)

        if os.path.exists(result_file):
            os.unlink(result_file)

        try:
            subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    f"Start-Process -FilePath 'powershell.exe' "
                    f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"{ps_file}\"' "
                    f"-Verb RunAs -Wait"
                ],
                capture_output=True, text=True, timeout=300,
                **subprocess_args()
            )

            import time
            time.sleep(1)

            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_text = f.read().strip()
                if result_text.startswith("OK"):
                    shutil.rmtree(str(source), ignore_errors=True)
                    self._show_system_install_success(ver, target)
                    return
                else:
                    raise RuntimeError(result_text)

            raise RuntimeError("Admin operation may have been cancelled.")
        finally:
            for fp in [ps_file, result_file]:
                try:
                    os.unlink(fp)
                except Exception:
                    pass

    def _system_install_unix(self, actual_source, target, ver, source, plat):
        """Linux/macOS system install via sudo."""
        import subprocess, shutil

        # Build shell script
        script = f'''#!/bin/bash
set -e
if [ -d "{target}" ]; then
    rm -rf "{target}"
fi
mkdir -p "{target}"
cp -a "{actual_source}/." "{target}/"

# Create symlinks in /usr/local/bin
PYTHON_EXE=""
if [ -f "{target}/bin/python3" ]; then
    PYTHON_EXE="{target}/bin/python3"
elif [ -f "{target}/bin/python" ]; then
    PYTHON_EXE="{target}/bin/python"
fi

if [ -n "$PYTHON_EXE" ]; then
    VER_SHORT=$(echo "{ver}" | cut -d. -f1,2)
    ln -sf "$PYTHON_EXE" "/usr/local/bin/python$VER_SHORT" 2>/dev/null || true
fi

echo "OK"
'''
        import tempfile, os
        script_file = os.path.join(tempfile.gettempdir(), "_venvstudio_install_py.sh")
        with open(script_file, 'w') as f:
            f.write(script)
        os.chmod(script_file, 0o755)

        try:
            # Try pkexec first (graphical sudo), fallback to sudo in terminal
            sudo_cmds = [
                ["pkexec", "bash", script_file],
                ["sudo", "bash", script_file],
            ]

            success = False
            for cmd in sudo_cmds:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120
                    )
                    if result.returncode == 0 and "OK" in result.stdout:
                        success = True
                        break
                except FileNotFoundError:
                    continue

            if success:
                shutil.rmtree(str(source), ignore_errors=True)
                symlink_note = ""
                if plat == "linux":
                    ver_short = ".".join(ver.split(".")[:2])
                    symlink_note = f"\n\nSymlink created: /usr/local/bin/python{ver_short}"
                self._show_system_install_success(ver, target, symlink_note)
            else:
                raise RuntimeError(
                    "sudo/pkexec failed. You can manually install with:\n"
                    f"  sudo cp -a {actual_source} {target}"
                )
        finally:
            try:
                os.unlink(script_file)
            except Exception:
                pass

    def _show_system_install_success(self, ver, target, extra_note=""):
        """Show success message after system install."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("✅ System install complete!")
        QMessageBox.information(
            self, "✅ Success",
            f"Python {ver} installed to:\n{target}{extra_note}\n\n"
            f"You may want to add it to PATH or use 'Set System Default'."
        )
        self._fetch_versions()

    def _remove_selected(self):
        row = self.version_list.currentRow()
        if row < 0:
            return

        item = self.version_list.item(row)
        version_info = item.data(Qt.UserRole)
        version = version_info["version"]

        confirm = QMessageBox.question(
            self, "Remove Python",
            f"Remove Python {version}?\nThis will delete the standalone installation.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        from src.core.python_downloader import get_installed_pythons, remove_python
        for py in get_installed_pythons():
            if py["version"] == version:
                remove_python(py["path"])
                break

        self._fetch_versions()

        # ── LAUNCH SETTINGS ──
        launch_group = QGroupBox("🚀 Launch Settings")
        launch_layout = QFormLayout()
        launch_layout.setSpacing(12)

        # Jupyter Working Directory — protected by checkbox
        jupyter_dir_row = QHBoxLayout()
        self.jupyter_workdir_cb = QCheckBox()
        self.jupyter_workdir_cb.setChecked(False)
        self.jupyter_workdir_cb.toggled.connect(lambda on: self.jupyter_workdir_combo.setEnabled(on))
        jupyter_dir_row.addWidget(self.jupyter_workdir_cb)

        self.jupyter_workdir_combo = NoScrollComboBox()
        self.jupyter_workdir_combo.addItem("🏠 Home Directory", "home")
        self.jupyter_workdir_combo.addItem("📁 Environment Folder", "env")
        self.jupyter_workdir_combo.addItem("📂 Custom Path...", "custom")
        self.jupyter_workdir_combo.setEnabled(False)
        self.jupyter_workdir_combo.currentIndexChanged.connect(self._on_jupyter_workdir_changed)
        jupyter_dir_row.addWidget(self.jupyter_workdir_combo, 1)

        self.jupyter_custom_path_btn = QPushButton("📂")
        self.jupyter_custom_path_btn.setFixedWidth(36)
        self.jupyter_custom_path_btn.setToolTip("Pick custom folder")
        self.jupyter_custom_path_btn.setEnabled(False)
        self.jupyter_custom_path_btn.clicked.connect(self._pick_jupyter_workdir)
        jupyter_dir_row.addWidget(self.jupyter_custom_path_btn)

        launch_layout.addRow("Jupyter Working Dir:", jupyter_dir_row)

        self.jupyter_custom_path_label = QLabel("")
        self.jupyter_custom_path_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        self.jupyter_custom_path_label.setVisible(False)
        launch_layout.addRow("", self.jupyter_custom_path_label)

        launch_group.setLayout(launch_layout)
        layout.addWidget(launch_group)
        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── SAVE / RESET BUTTONS (scroll dışında, üstte sabit) ──
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(12, 6, 12, 6)

        save_btn = QPushButton(f"  💾 {tr('save_settings')}  ")
        save_btn.setObjectName("success")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()

        reset_all_btn = QPushButton(tr("reset_defaults"))
        reset_all_btn.setObjectName("danger")
        reset_all_btn.clicked.connect(self._reset_all)
        btn_layout.addWidget(reset_all_btn)

        main_layout.addLayout(btn_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {self._c()['border']}; max-height: 1px;")
        main_layout.addWidget(sep)

        main_layout.addWidget(scroll)

