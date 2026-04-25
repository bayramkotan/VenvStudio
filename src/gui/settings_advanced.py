"""VenvStudio - Settings: AdvancedMixin"""
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

from .settings_python_download import _UpdateCheckWorker


class AdvancedMixin:
    """Mixin for SettingsPage."""
    def _check_for_updates(self):
        """Check PyPI for new version."""
        self.update_status_label.setText("🔍 Checking...")
        self.update_status_label.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")

        # Run in background thread
        self._update_worker = _UpdateCheckWorker(parent=self)
        self._update_worker.finished.connect(self._on_update_check_done)
        self._update_worker.start()

    def _on_update_check_done(self, result):
        """Handle update check result."""
        if result.get("error"):
            self.update_status_label.setText(f"⚠️ {result['error']}")
            self.update_status_label.setStyleSheet(f"color: {self._c()['accent']}; font-size: {self._c()['fs_small']}px;")
            return

        if result["update_available"]:
            self.update_status_label.setText(
                f"🆕 New version available: v{result['latest_version']} (current: v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

            reply = QMessageBox.question(
                self, "🆕 Update Available",
                f"VenvStudio v{result['latest_version']} is available!\n"
                f"You have v{result['current_version']}.\n\n"
                f"Update with:\n  pip install --upgrade venvstudio\n\n"
                f"Or download from GitHub Releases.\n\n"
                f"Open download page?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open(result["release_url"])
        else:
            self.update_status_label.setText(
                f"✅ You're up to date! (v{result['current_version']})"
            )
            self.update_status_label.setStyleSheet(f"color: {self._c()['success']}; font-size: {self._c()['fs_small']}px;")

    def _export_settings(self):
        """Export settings to a JSON file."""
        import json
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "venvstudio_settings.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not filepath:
            return
        try:
            # Read current config file
            config_path = self.config.config_file_path
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Success", f"Settings exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _import_settings(self):
        """Import settings from a JSON file."""
        import json
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not filepath:
            return
        reply = QMessageBox.question(
            self, "Import Settings",
            "This will overwrite your current settings.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Write to config
            config_path = self.config.config_file_path
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.config.load()
            self._load_current_settings()
            QMessageBox.information(self, "Success", "Settings imported! Some changes may need a restart.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{e}")

    # ── Environment Export (from Settings page) ──

    def _pick_env_and_freeze(self):
        """Let user pick an environment, return (freeze_text, python_version) or (None, None)."""
        import subprocess
        from src.core.venv_manager import VenvManager
        from src.core.pip_manager import PipManager
        from src.utils.platform_utils import get_python_executable, subprocess_args

        vm = VenvManager(Path(self.config.get_venv_base_dir()))
        envs = vm.list_venvs()
        if not envs:
            QMessageBox.warning(self, "Warning", "No environments found.")
            return None, None

        env_names = [e.name for e in envs]
        name, ok = QInputDialog.getItem(
            self, "Select Environment",
            "Choose an environment to export:", env_names, 0, False
        )
        if not ok or not name:
            return None, None

        venv_path = vm.base_dir / name
        pm = PipManager(venv_path)
        freeze = pm.freeze()
        if not freeze:
            QMessageBox.warning(self, "Warning", f"No packages in '{name}'.")
            return None, None

        py_ver = "3.12"
        try:
            exe = get_python_executable(venv_path)
            result = subprocess.run(
                [str(exe), "--version"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            )
            ver = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            py_ver = ".".join(ver.split(".")[:2])
        except Exception:
            pass
        return freeze, py_ver

    def _export_env_requirements(self):
        freeze, _ = self._pick_env_and_freeze()
        if not freeze:
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export requirements.txt", "requirements.txt", "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_dockerfile(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        dockerfile = (
            f"# Auto-generated by VenvStudio\n"
            f"FROM python:{py_ver}-slim\nWORKDIR /app\n\n"
            f"COPY requirements.txt .\n"
            f"RUN pip install --no-cache-dir -r requirements.txt\n\n"
            f"COPY . .\n# CMD [\"python\", \"main.py\"]\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Dockerfile", "Dockerfile", "All Files (*)")
        if filepath:
            req_path = Path(filepath).parent / "requirements.txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported:\n  {filepath}\n  {req_path}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_docker_compose(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        compose = (
            f"version: '3.8'\nservices:\n  app:\n    build: .\n"
            f"    ports:\n      - \"8000:8000\"\n    volumes:\n      - .:/app\n"
        )
        dockerfile = (
            f"FROM python:{py_ver}-slim\nWORKDIR /app\n"
            f"COPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n"
            f"COPY . .\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export docker-compose.yml", "docker-compose.yml", "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            base = Path(filepath).parent
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(compose)
                with open(base / "Dockerfile", "w", encoding="utf-8") as f:
                    f.write(dockerfile)
                with open(base / "requirements.txt", "w", encoding="utf-8") as f:
                    f.write(freeze)
                QMessageBox.information(self, "✅ Success", f"Exported 3 files to {base}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_pyproject(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        deps = "\n".join(f'    "{l.strip()}",' for l in freeze.strip().splitlines()
                         if l.strip() and not l.startswith("#"))
        content = (
            f'[build-system]\nrequires = ["setuptools>=68.0", "wheel"]\n'
            f'build-backend = "setuptools.backends._legacy:_Backend"\n\n'
            f'[project]\nname = "myproject"\nversion = "0.1.0"\n'
            f'requires-python = ">={py_ver}"\ndependencies = [\n{deps}\n]\n'
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export pyproject.toml", "pyproject.toml", "TOML Files (*.toml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_conda_yml(self):
        freeze, py_ver = self._pick_env_and_freeze()
        if not freeze:
            return
        pip_deps = "\n".join(f"    - {l.strip()}" for l in freeze.strip().splitlines()
                             if l.strip() and not l.startswith("#"))
        content = (
            f"name: myenv\nchannels:\n  - defaults\n  - conda-forge\n"
            f"dependencies:\n  - python={py_ver}\n  - pip\n  - pip:\n{pip_deps}\n"
        )
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export environment.yml", "environment.yml", "YAML Files (*.yml);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                QMessageBox.information(self, "✅ Success", f"Exported to:\n{filepath}")
            except IOError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_env_clipboard(self):
        freeze, _ = self._pick_env_and_freeze()
        if not freeze:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(freeze)
        count = len(freeze.strip().splitlines())
        QMessageBox.information(self, "✅ Copied", f"{count} packages copied to clipboard.")

    def _save_settings(self):
        """Save all settings."""
        # Use batch mode to avoid writing JSON 30+ times
        self.config.begin_batch()
        # Theme
        if self.theme_cb.isChecked():
            new_theme = self.theme_combo.currentData()
        else:
            new_theme = "dark"
        old_theme = self.config.get("theme", "dark")
        self.config.set("theme", new_theme)
        if new_theme != old_theme:
            self.theme_changed.emit(new_theme)

        # Font — 3-level system
        _defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        for level_id, (def_family, def_size) in _defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            if cb.isChecked():
                self.config.set(f"font_{level_id}_family", combo.currentFont().family())
                self.config.set(f"font_{level_id}_size", spin.value())
            else:
                self.config.set(f"font_{level_id}_family", "")
                self.config.set(f"font_{level_id}_size", def_size)

        # Backward compat
        self.config.set("font_family", self.config.get("font_secondary_family", ""))
        self.config.set("font_size", self.config.get("font_secondary_size", 13))
        font_family = self.config.get("font_secondary_family", "") or "Segoe UI"
        font_size = self.config.get("font_secondary_size", 13)
        self.font_changed.emit(font_family, font_size)

        # Language
        new_lang = self.lang_combo.currentData()
        if not new_lang:
            new_lang = "en"
        old_lang = self.config.get("language", "en")
        self.config.set("language", new_lang)
        lang_changed = (new_lang != old_lang and self.lang_enabled_cb.isChecked())
        if lang_changed:
            self.language_changed.emit(new_lang)

        # Default Python
        # Default Python — only save if checkbox is enabled
        if self.default_py_cb.isChecked():
            self.config.set("default_python", self.default_python_combo.currentData() or "")
        else:
            self.config.set("default_python", "")

        # Venv directory
        new_dir = self.venv_dir_input.text()
        self.config.set_venv_base_dir(new_dir)

        # Shared package cache (pip/uv only)
        if hasattr(self, "shared_cache_cb"):
            self.config.set("shared_cache_enabled", self.shared_cache_cb.isChecked())
            _cache_path = self.shared_cache_input.text().strip()
            self.config.set("shared_cache_dir", _cache_path)

        # General
        self.config.set("auto_upgrade_pip", self.auto_pip_cb.isChecked())
        self.config.set("confirm_delete", self.confirm_delete_cb.isChecked())
        self.config.set("show_hidden_packages", self.show_hidden_cb.isChecked())
        self.config.set("check_updates", self.check_updates_cb.isChecked())
        self.config.set("save_window_geometry", self.save_window_cb.isChecked())

        # Package manager — only save if checkbox is enabled
        self.config.set("package_manager", "pip")
        # Default Terminal — only save if checkbox is enabled

        # Default environment type

        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb"):
            self.config.set("tc_py_cb_checked", self._tc_py_cb.isChecked())
        if self.terminal_cb.isChecked():
            self.config.set("default_terminal", self.terminal_combo.currentData())
        else:
            self.config.set("default_terminal", "")

        # Jupyter Working Directory
        if self.jupyter_workdir_cb.isChecked():
            self.config.set("jupyter_workdir", self.jupyter_workdir_combo.currentData() or "home")
            if self.jupyter_workdir_combo.currentData() == "custom":
                self.config.set("jupyter_workdir_custom", self.jupyter_custom_path_label.text())
            else:
                self.config.set("jupyter_workdir_custom", "")
        else:
            self.config.set("jupyter_workdir", "home")
            self.config.set("jupyter_workdir_custom", "")

        # Save custom terminals
        self._save_custom_terminals()

        # Save custom presets
        self._save_custom_presets()

        # Save custom categories
        self._save_custom_categories()

        # Save custom catalog
        self._save_custom_catalog()

        # End batch — single disk write for all settings
        self.config.end_batch()
        self.settings_saved.emit()
        QMessageBox.information(self, "Settings", "Settings saved successfully! ✅")

        if lang_changed:
            reply = QMessageBox.question(
                self, "Restart Required",
                "Language changed. VenvStudio needs to restart.\n\nRestart now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                import sys, subprocess
                from PySide6.QtWidgets import QApplication
                # Find the main script
                main_script = sys.argv[0] if sys.argv else "main.py"
                subprocess.Popen([sys.executable, main_script])
                QApplication.instance().quit()

    def _reset_all(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.warning(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from src.core.config_manager import DEFAULT_SETTINGS
            for key, value in DEFAULT_SETTINGS.items():
                self.config.set(key, value)
            self.config.set("custom_pythons", [])
            self._load_current_settings()
            self.theme_changed.emit("dark")
            QMessageBox.information(self, "Settings", "All settings reset to defaults.")

    def _reset_appearance(self):
        """Reset Appearance section to defaults."""
        self.theme_cb.setChecked(False)
        self.theme_combo.setEnabled(False)
        idx = self.theme_combo.findData("dark")
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.config.set("theme", "dark")
        self.theme_changed.emit("dark")
        self._reset_fonts()

    def _reset_language(self):
        """Reset Language section to defaults."""
        self.lang_enabled_cb.setChecked(False)
        idx = self.lang_combo.findData("en")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.config.set("language", "en")

    def _reset_general(self):
        """Reset General section to defaults."""
        from src.core.config_manager import DEFAULT_SETTINGS
        general_keys = [
            "auto_upgrade_pip", "confirm_delete", "show_hidden_packages",
            "check_updates", "remember_window", "default_terminal",
        ]
        for key in general_keys:
            if key in DEFAULT_SETTINGS:
                self.config.set(key, DEFAULT_SETTINGS[key])
        self._load_current_settings()


    # ── Shared Cache helpers ─────────────────────────────────────────────────

    def _on_shared_cache_toggled(self, checked: bool):
        """Enable/disable cache path controls based on toggle."""
        for w in (self.shared_cache_input, self._cache_browse_btn,
                  self._cache_reset_btn, self._cache_clear_btn):
            w.setEnabled(checked)

    def _browse_cache_dir(self):
        """Browse for shared cache directory."""
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "Select Shared Cache Directory",
            self.shared_cache_input.text() or str(Path.home()),
        )
        if path:
            self.shared_cache_input.setText(path)

    def _reset_cache_dir(self):
        """Reset cache dir to default."""
        from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
        self.shared_cache_input.setText(DEFAULT_SHARED_CACHE_DIR)

    def _clear_cache_dir(self):
        """Delete all files in the shared cache directory."""
        import shutil
        from PySide6.QtWidgets import QMessageBox
        cache_path = Path(self.shared_cache_input.text().strip() or "")
        if not cache_path.exists():
            QMessageBox.information(self, "Clear Cache", "Cache directory does not exist — nothing to clear.")
            return
        reply = QMessageBox.question(
            self, "Clear Shared Cache",
            f"Delete all cached packages from:\n{cache_path}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(cache_path, ignore_errors=True)
                cache_path.mkdir(parents=True, exist_ok=True)
                QMessageBox.information(self, "Clear Cache", "✅ Cache cleared successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Clear Cache", f"Failed to clear cache:\n{e}")

    def _load_cache_settings(self):
        """Load shared cache settings into UI widgets."""
        if not hasattr(self, "shared_cache_cb"):
            return
        from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
        _enabled = self.config.get("shared_cache_enabled", False)
        _path = self.config.get("shared_cache_dir", "") or DEFAULT_SHARED_CACHE_DIR
        self.shared_cache_cb.setChecked(_enabled)
        self.shared_cache_input.setText(_path)
        self._on_shared_cache_toggled(_enabled)

    # ── Package Manager helpers ───────────────────────────────────────────────
