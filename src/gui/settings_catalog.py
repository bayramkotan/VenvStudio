"""VenvStudio - Settings: CatalogMixin"""
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


class CatalogMixin:
    """Mixin for SettingsPage."""
    def _set_vscode_interpreter(self):
        """Set VS Code python interpreter path for the selected env."""
        env_path = self.vscode_env_combo.currentData()
        if not env_path:
            QMessageBox.warning(self, tr("warning"), "Please select an environment first.")
            return

        from src.utils.platform_utils import get_python_executable
        python_exe = get_python_executable(Path(env_path))

        import os
        norm_path = os.path.normpath(str(python_exe))

        # Try to write .vscode/settings.json in current working directory
        vscode_dir = Path.cwd() / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        settings_file = vscode_dir / "settings.json"

        import json
        settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}

        settings["python.defaultInterpreterPath"] = norm_path

        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)

            QMessageBox.information(
                self, tr("success"),
                f"VS Code interpreter set to:\n{norm_path}\n\n"
                f"Settings written to:\n{settings_file}\n\n"
                f"Tip: Install the 'Python' extension in VS Code if not already installed."
            )
        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"Failed to write VS Code settings:\n{e}")

    def _get_all_categories(self):
        """Get built-in + custom category names."""
        from src.utils.constants import PACKAGE_CATALOG
        cats = list(PACKAGE_CATALOG.keys())
        custom_cats = self.config.get("custom_categories", [])
        for c in custom_cats:
            name = c.get("name", "")
            if name:
                icon = c.get("icon", "⭐")
                full = f"{icon} {name}"
                if full not in cats:
                    cats.append(full)
        # Always include ⭐ Custom as fallback
        if "⭐ Custom" not in cats:
            cats.append("⭐ Custom")
        return cats

    def _toggle_builtin_presets(self, visible: bool):
        self.builtin_presets_table.setVisible(visible)

    def _load_custom_presets(self):
        """Load custom presets from config into table."""
        presets = self.config.get("custom_presets", {})
        self.custom_presets_table.setRowCount(0)
        for name, pkgs in presets.items():
            row = self.custom_presets_table.rowCount()
            self.custom_presets_table.insertRow(row)
            self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
            self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _save_custom_presets(self):
        """Save custom presets from table to config."""
        presets = {}
        for row in range(self.custom_presets_table.rowCount()):
            name_item = self.custom_presets_table.item(row, 0)
            pkgs_item = self.custom_presets_table.item(row, 1)
            if name_item and pkgs_item:
                name = name_item.text().strip()
                pkgs = [p.strip() for p in pkgs_item.text().split(",") if p.strip()]
                if name and pkgs:
                    presets[name] = pkgs
        self.config.set("custom_presets", presets)

    def _add_custom_preset(self):
        """Add a new custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. 🚀 My Stack")
        pkgs_edit = QLineEdit()
        pkgs_edit.setPlaceholderText("e.g. numpy, pandas, matplotlib, scikit-learn")

        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                pkgs = [p.strip() for p in pkgs_raw.split(",") if p.strip()]
                row = self.custom_presets_table.rowCount()
                self.custom_presets_table.insertRow(row)
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(", ".join(pkgs)))

    def _edit_custom_preset(self):
        """Edit selected custom preset."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a preset to edit.")
            return
        old_name = self.custom_presets_table.item(row, 0).text()
        old_pkgs = self.custom_presets_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Preset")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        pkgs_edit = QLineEdit(old_pkgs)
        hint = QLabel("Separate package names with commas.")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Preset Name:", name_edit)
        layout.addRow("Packages:", pkgs_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            pkgs_raw = pkgs_edit.text().strip()
            if name and pkgs_raw:
                self.custom_presets_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_presets_table.setItem(row, 1, QTableWidgetItem(pkgs_raw))

    def _remove_custom_preset(self):
        """Remove selected custom preset."""
        row = self.custom_presets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a preset to remove.")
            return
        name = self.custom_presets_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Preset",
            f"Remove preset '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_presets_table.removeRow(row)

    def _load_custom_categories(self):
        """Load custom categories from config."""
        custom_cats = self.config.get("custom_categories", [])
        self.custom_categories_list.setRowCount(len(custom_cats))
        for i, c in enumerate(custom_cats):
            self.custom_categories_list.setItem(i, 0, QTableWidgetItem(c.get("icon", "⭐")))
            self.custom_categories_list.setItem(i, 1, QTableWidgetItem(c.get("name", "")))

    def _save_custom_categories(self):
        """Save custom categories to config."""
        self.custom_categories_list.setCurrentItem(None)
        cats = []
        for row in range(self.custom_categories_list.rowCount()):
            icon_item = self.custom_categories_list.item(row, 0)
            name_item = self.custom_categories_list.item(row, 1)
            icon = icon_item.text().strip() if icon_item else "⭐"
            name = name_item.text().strip() if name_item else ""
            if name:
                cats.append({"icon": icon or "⭐", "name": name})
        self.config.set("custom_categories", cats)

    def _add_custom_category(self):
        """Add a new custom category."""
        row = self.custom_categories_list.rowCount()
        self.custom_categories_list.insertRow(row)
        self.custom_categories_list.setItem(row, 0, QTableWidgetItem("⭐"))
        self.custom_categories_list.setItem(row, 1, QTableWidgetItem(""))
        self.custom_categories_list.editItem(self.custom_categories_list.item(row, 1))

    def _remove_custom_category(self):
        """Remove selected custom category."""
        row = self.custom_categories_list.currentRow()
        if row >= 0:
            self.custom_categories_list.removeRow(row)
            self._save_custom_categories()
        else:
            QMessageBox.information(self, "Info", "Select a category to remove.")

    def _make_category_combo(self, current_value="⭐ Custom"):
        """Create a category dropdown for catalog table."""
        combo = QComboBox()
        combo.setStyleSheet(
            f"background-color: {self._c()['input_bg']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"padding: 3px; font-size: {self._c()['fs_small']}px;"
        )
        categories = self._get_all_categories()
        for cat in categories:
            combo.addItem(cat)
        # Set current
        idx = combo.findText(current_value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.addItem(current_value)
            combo.setCurrentIndex(combo.count() - 1)
        return combo

    def _load_custom_catalog(self):
        """Load custom catalog packages from config into the table."""
        custom_pkgs = self.config.get("custom_catalog", [])
        print(f"[DEBUG] Loading custom catalog: {custom_pkgs}")
        self.custom_catalog_table.setRowCount(len(custom_pkgs))
        for i, pkg in enumerate(custom_pkgs):
            self.custom_catalog_table.setItem(i, 0, QTableWidgetItem(pkg.get("name", "")))
            self.custom_catalog_table.setItem(i, 1, QTableWidgetItem(pkg.get("desc", "")))
            # Category as dropdown
            cat_combo = self._make_category_combo(pkg.get("category", "⭐ Custom"))
            self.custom_catalog_table.setCellWidget(i, 2, cat_combo)

    def _add_custom_catalog_pkg(self):
        """Add a new custom catalog package row."""
        row = self.custom_catalog_table.rowCount()
        self.custom_catalog_table.insertRow(row)
        self.custom_catalog_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_catalog_table.setItem(row, 1, QTableWidgetItem(""))
        cat_combo = self._make_category_combo("⭐ Custom")
        self.custom_catalog_table.setCellWidget(row, 2, cat_combo)
        self.custom_catalog_table.editItem(self.custom_catalog_table.item(row, 0))

    def _remove_custom_catalog_pkg(self):
        """Remove selected custom catalog package."""
        rows = self.custom_catalog_table.selectionModel().selectedRows()
        if rows:
            for r in sorted([r.row() for r in rows], reverse=True):
                self.custom_catalog_table.removeRow(r)
        else:
            row = self.custom_catalog_table.currentRow()
            if row >= 0:
                self.custom_catalog_table.removeRow(row)
            else:
                QMessageBox.information(self, "Info", "Select a row to remove.")
                return
        self._save_custom_catalog()

    def _save_custom_catalog(self):
        """Save custom catalog table to config."""
        self.custom_catalog_table.setCurrentItem(None)

        pkgs = []
        for row in range(self.custom_catalog_table.rowCount()):
            name_item = self.custom_catalog_table.item(row, 0)
            desc_item = self.custom_catalog_table.item(row, 1)
            cat_widget = self.custom_catalog_table.cellWidget(row, 2)
            name = name_item.text().strip() if name_item else ""
            desc = desc_item.text().strip() if desc_item else ""
            if isinstance(cat_widget, QComboBox):
                cat = cat_widget.currentText()
            else:
                cat_item = self.custom_catalog_table.item(row, 2)
                cat = cat_item.text().strip() if cat_item else "⭐ Custom"
            if name or desc:
                pkgs.append({
                    "name": name,
                    "desc": desc,
                    "category": cat if cat else "⭐ Custom",
                })
        print(f"[DEBUG] Saving custom catalog: {pkgs}")
        self.config.set("custom_catalog", pkgs)
        verify = self.config.get("custom_catalog", [])
        print(f"[DEBUG] Verify after save: {verify}")

    def _open_log_folder(self):
        """Open the log directory in file manager."""
        import os
        import subprocess
        from pathlib import Path
        # Try to get log dir from logger module, fall back to known path
        try:
            from src.utils.logger import get_log_dir
            log_dir = get_log_dir()
        except ImportError:
            import os
            log_dir = Path(os.environ.get("APPDATA", "~")) / "VenvStudio" / "logs"
            log_dir = log_dir.expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        if get_platform() == "windows":
            os.startfile(str(log_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(log_dir)])
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])

    def _open_config_folder(self):
        """Open the config directory in file manager."""
        import os
        import subprocess
        config_dir = self.config.config_file_path.parent
        if get_platform() == "windows":
            os.startfile(str(config_dir))
        elif get_platform() == "macos":
            subprocess.Popen(["open", str(config_dir)])
        else:
            subprocess.Popen(["xdg-open", str(config_dir)])

    def _add_python_to_path(self):
        """Add a Python installation to system PATH automatically."""
        import subprocess

        platform = get_platform()

        # Collect all known Python paths from table
        python_paths = []
        for row in range(self.python_table.rowCount()):
            path_item = self.python_table.item(row, 1)
            ver_item = self.python_table.item(row, 0)
            if path_item and ver_item:
                exe_path = path_item.text()
                python_paths.append({
                    "version": ver_item.text(),
                    "exe": exe_path,
                    "folder": os.path.dirname(exe_path),
                })

        if not python_paths:
            QMessageBox.warning(self, "Warning", "No Python installations found. Run Scan System first.")
            return

        # Let user choose which one
        items = [f"Python {p['version']}  —  {p['folder']}" for p in python_paths]
        item, ok = QInputDialog.getItem(
            self, "Add Python to PATH",
            "Select which Python to add to PATH:",
            items, 0, False,
        )
        if not ok or not item:
            return

        selected = python_paths[items.index(item)]
        folder = selected['folder']
        version = selected['version']

        if platform == "windows":
            scripts = os.path.join(folder, "Scripts")
            reply = QMessageBox.question(
                self, "Confirm",
                f"Add to User PATH?\n\n  {folder}\n  {scripts}\n\n"
                f"A terminal restart may be needed.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            ps_cmd = (
                f'$userPath = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'$newPaths = @("{folder}", "{scripts}"); '
                f'foreach ($p in $newPaths) {{ '
                f'  if ($userPath -notlike "*$p*") {{ '
                f'    $userPath = "$userPath;$p" '
                f'  }} '
                f'}}; '
                f'[Environment]::SetEnvironmentVariable("Path", $userPath, "User")'
            )
            try:
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    **subprocess_args(capture_output=True, text=True, timeout=15)
                )
                if result.returncode == 0:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Python {version} added to User PATH!\n\n"
                        f"  {folder}\n  {scripts}\n\n"
                        f"Restart your terminal for the change to take effect."
                    )
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update PATH:\n{result.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to run PowerShell:\n{e}")

        else:
            # Linux / macOS — write export line to shell config files
            export_line = f'export PATH="{folder}:$PATH"'

            # Detect shell config files
            home = Path.home()
            candidates = [home / ".bashrc", home / ".bash_profile", home / ".zshrc", home / ".profile"]
            existing = [str(p) for p in candidates if p.exists()]

            if not existing:
                existing = [str(home / ".bashrc")]  # fallback: create .bashrc

            # Let user pick which file
            file_choice, ok = QInputDialog.getItem(
                self, "Select Shell Config",
                f"Add  {export_line}  to which file?",
                existing, 0, False,
            )
            if not ok or not file_choice:
                return

            reply = QMessageBox.question(
                self, "Confirm",
                f"Append to {file_choice}:\n\n  {export_line}\n\n"
                f"Run  source {file_choice}  or restart terminal after.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            try:
                config_file = Path(file_choice)
                existing_text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""

                # Check if already present
                if folder in existing_text:
                    QMessageBox.information(
                        self, "Already in PATH",
                        f"{folder} is already in {file_choice}.\nNo changes made."
                    )
                    return

                with open(config_file, "a", encoding="utf-8") as f:
                    f.write(f"\n# Added by VenvStudio\n{export_line}\n")

                QMessageBox.information(
                    self, "✅ Success",
                    f"Added to {file_choice}:\n\n  {export_line}\n\n"
                    f"Run the following to apply now:\n"
                    f"  source {file_choice}"
                )
            except PermissionError:
                # Try pkexec as fallback
                import tempfile
                script = f'#!/bin/bash\necho "\n# Added by VenvStudio\n{export_line}" >> "{file_choice}"\n'
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
                    tmp.write(script)
                    tmp_path = tmp.name
                os.chmod(tmp_path, 0o755)
                try:
                    result = subprocess.run(["pkexec", "bash", tmp_path], timeout=30)
                    if result.returncode == 0:
                        QMessageBox.information(self, "✅ Success", f"Added to {file_choice} (admin).\n\nRun: source {file_choice}")
                    else:
                        QMessageBox.critical(self, "Error", f"pkexec failed. Try manually:\n  {export_line} >> {file_choice}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to write to {file_choice}:\n{e}")

    def _toggle_vs_cli(self):
        """Copy vs.bat/vs.py to venv base dir and add that dir to User PATH."""
        import shutil, subprocess

        venv_dir = str(self.config.get_venv_base_dir())
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(project_root)  # up to VenvStudio root

        vs_py_src = os.path.join(project_root, "vs.py")
        vs_bat_src = os.path.join(project_root, "vs.bat")

        if not os.path.isfile(vs_py_src):
            QMessageBox.critical(self, "Error", f"vs.py not found at:\n{vs_py_src}")
            return

        # Copy vs.py and vs.bat to venv base dir
        vs_py_dst = os.path.join(venv_dir, "vs.py")
        vs_bat_dst = os.path.join(venv_dir, "vs.bat")

        try:
            shutil.copy2(vs_py_src, vs_py_dst)
            if os.path.isfile(vs_bat_src):
                shutil.copy2(vs_bat_src, vs_bat_dst)
            else:
                # Create vs.bat pointing to vs.py in same dir
                with open(vs_bat_dst, "w") as f:
                    f.write(f'@echo off\npython "%~dp0vs.py" %*\n')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to copy CLI files:\n{e}")
            return

        if get_platform() == "windows":
            # Check if already in PATH
            ps_check = (
                f'$p = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'$p -like "*{venv_dir}*"'
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_check],
                **subprocess_args(capture_output=True, text=True, timeout=10)
            )
            already_in = "True" in result.stdout

            if already_in:
                QMessageBox.information(
                    self, "Already Active",
                    f"'vs' CLI is already active!\n\n"
                    f"Directory: {venv_dir}\n\n"
                    f"Usage:\n  vs list\n  vs create myenv\n  vs install myenv numpy"
                )
                return

            reply = QMessageBox.question(
                self, "Enable 'vs' CLI",
                f"This will:\n\n"
                f"1. Copy vs.py & vs.bat to:\n   {venv_dir}\n\n"
                f"2. Add that folder to your User PATH\n\n"
                f"After this you can use 'vs' from any terminal:\n"
                f"  vs list\n  vs create myenv\n  vs install myenv numpy\n\n"
                f"Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            ps_cmd = (
                f'$userPath = [Environment]::GetEnvironmentVariable("Path", "User"); '
                f'if ($userPath -notlike "*{venv_dir}*") {{ '
                f'  [Environment]::SetEnvironmentVariable("Path", "$userPath;{venv_dir}", "User") '
                f'}}; '
            )
            try:
                result = subprocess.run(
                    ["powershell", "-Command", ps_cmd],
                    **subprocess_args(capture_output=True, text=True, timeout=15)
                )
                if result.returncode == 0:
                    self.config.set("vs_cli_enabled", True)
                    QMessageBox.information(
                        self, "Success",
                        f"'vs' CLI enabled! ✅\n\n"
                        f"PATH added: {venv_dir}\n\n"
                        f"Restart your terminal, then try:\n"
                        f"  vs list\n  vs create myenv\n  vs install myenv numpy pandas"
                    )
                else:
                    QMessageBox.critical(self, "Error", f"Failed:\n{result.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed:\n{e}")
        else:
            self.config.set("vs_cli_enabled", True)
            QMessageBox.information(
                self, "Enable 'vs' CLI",
                f"Files copied to: {venv_dir}\n\n"
                f"Add to ~/.bashrc or ~/.zshrc:\n"
                f'  export PATH="{venv_dir}:$PATH"\n\n'
                f"Then: source ~/.bashrc"
            )

    def _clear_all_data(self):
        """Remove all config, log, and cache files."""
        import shutil
        reply = QMessageBox.warning(
            self, "Remove All Data",
            "This will delete ALL VenvStudio settings, logs, and cache.\n\n"
            "Your virtual environments will NOT be deleted.\n\n"
            "The application will close. Are you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        config_dir = self.config.config_file_path.parent
        try:
            # Close all logging handlers first (prevents WinError 32 on Windows)
            import logging
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                try:
                    handler.close()
                    root_logger.removeHandler(handler)
                except Exception:
                    pass
            # Also close any module-level loggers
            for name in list(logging.Logger.manager.loggerDict.keys()):
                lgr = logging.getLogger(name)
                for h in lgr.handlers[:]:
                    try:
                        h.close()
                        lgr.removeHandler(h)
                    except Exception:
                        pass
            # Remove config directory
            if config_dir.exists():
                # On Windows, retry with onerror handler for locked files
                import sys as _sys
                if _sys.platform == "win32":
                    import stat
                    def _remove_readonly(func, path, _):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    shutil.rmtree(str(config_dir), onerror=_remove_readonly)
                else:
                    shutil.rmtree(str(config_dir))
            QMessageBox.information(
                self, "Done",
                f"All data removed from:\n{config_dir}\n\nApplication will now close."
            )
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove data:\n{e}")

    def populate_vscode_envs(self, env_list):
        """Populate VS Code env selector from main window."""
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
        if not hasattr(self, "vscode_env_combo"):
            return
        self.vscode_env_combo.blockSignals(True)
        self.vscode_env_combo.clear()
        self.vscode_env_combo.addItem("-- Select Environment --", "")
        for name, path in env_list:
            self.vscode_env_combo.addItem(name, str(path))
        self.vscode_env_combo.blockSignals(False)

    def _toggle_builtin_categories(self, visible):
        """Show/hide built-in categories table."""
        self.builtin_cats_table.setVisible(visible)
