"""VenvStudio - Settings: PythonMixin"""
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
from src.gui.settings_python_download import PythonDownloadDialog


class PythonMixin:
    """Mixin for SettingsPage."""
    def _load_current_settings(self):
        """Load current settings into UI widgets."""
        # Theme
        theme = self.config.get("theme", "dark")
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        if theme != "dark":
            self.theme_cb.setChecked(True)
            self.theme_combo.setEnabled(True)
        else:
            self.theme_cb.setChecked(False)
            self.theme_combo.setEnabled(False)

        # Font — 3-level system load
        _font_defaults = {
            "primary":   ("Segoe UI", 22),
            "secondary": ("Segoe UI", 13),
            "tertiary":  ("Segoe UI", 11),
        }
        _sys_fonts = ("", "Segoe UI", "Yu Gothic UI", "MS Shell Dlg 2", "Arial", "Tahoma")
        for level_id, (def_family, def_size) in _font_defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            saved_family = self.config.get(f"font_{level_id}_family", "")
            saved_size = self.config.get(f"font_{level_id}_size", def_size)
            if saved_family and saved_family not in _sys_fonts:
                cb.setChecked(True)
                combo.setEnabled(True)
                combo.setCurrentFont(QFont(saved_family))
                spin.setEnabled(True)
                spin.setValue(saved_size)
            elif saved_size != def_size and saved_size > 0:
                cb.setChecked(True)
                combo.setEnabled(True)
                spin.setEnabled(True)
                spin.setValue(saved_size)
            else:
                cb.setChecked(False)
                combo.setEnabled(False)
                spin.setEnabled(False)
                spin.setValue(def_size)

        # Language
        lang = self.config.get("language", "en")
        idx = self.lang_combo.findData(lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        # Always start unticked — user must tick to change language
        self.lang_enabled_cb.setChecked(False)
        self.lang_combo.setEnabled(False)

        # Venv dir
        self.venv_dir_input.setText(str(self.config.get_venv_base_dir()))

        # General options
        self.auto_pip_cb.setChecked(self.config.get("auto_upgrade_pip", True))
        self.confirm_delete_cb.setChecked(self.config.get("confirm_delete", True))
        self.show_hidden_cb.setChecked(self.config.get("show_hidden_packages", False))
        self.check_updates_cb.setChecked(self.config.get("check_updates", False))
        self.save_window_cb.setChecked(self.config.get("save_window_geometry", True))

        # Package manager


        # Toolchain Manager Python checkbox
        if hasattr(self, "_tc_py_cb") and hasattr(self, "_tc_py_combo"):
            tc_py_on = self.config.get("tc_py_cb_checked", False)
            self._tc_py_cb.setChecked(tc_py_on)
            self._tc_py_combo.setEnabled(tc_py_on)

        # Terminal — only enable if explicitly set to non-default
        terminal = self.config.get("default_terminal", "")
        if terminal and terminal.strip():
            idx = self.terminal_combo.findData(terminal)
            if idx > 0:
                self.terminal_cb.setChecked(True)
                self.terminal_combo.setEnabled(True)
                self.terminal_combo.setCurrentIndex(idx)
            else:
                self.terminal_cb.setChecked(False)
                self.terminal_combo.setEnabled(False)
                self.terminal_combo.setCurrentIndex(0)
        else:
            self.terminal_cb.setChecked(False)
            self.terminal_combo.setEnabled(False)
            self.terminal_combo.setCurrentIndex(0)

        # Load custom terminals into table and combo
        self._load_custom_terminals()

        # Load custom presets
        self._load_custom_presets()

        # Scan pythons
        self._scan_pythons()

        # Load custom categories
        self._load_custom_categories()

        # Load custom catalog
        self._load_custom_catalog()

        # Jupyter working dir
        jwd = self.config.get("jupyter_workdir", "home")
        jwd_custom = self.config.get("jupyter_workdir_custom", "")
        idx_jwd = self.jupyter_workdir_combo.findData(jwd)
        if idx_jwd >= 0:
            self.jupyter_workdir_combo.setCurrentIndex(idx_jwd)
        if jwd != "home":
            self.jupyter_workdir_cb.setChecked(True)
            self.jupyter_workdir_combo.setEnabled(True)
        if jwd == "custom" and jwd_custom:
            self.jupyter_custom_path_label.setText(jwd_custom)
            self.jupyter_custom_path_label.setVisible(True)
            self.jupyter_custom_path_btn.setEnabled(True)

    def _on_jupyter_workdir_changed(self, idx):
        """Enable/disable custom path button based on selection."""
        data = self.jupyter_workdir_combo.currentData()
        is_custom = data == "custom" and self.jupyter_workdir_cb.isChecked()
        self.jupyter_custom_path_btn.setEnabled(is_custom)
        self.jupyter_custom_path_label.setVisible(is_custom)

    def _pick_jupyter_workdir(self):
        """Open folder picker for custom Jupyter working directory."""
        import os
        current = self.jupyter_custom_path_label.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Jupyter Working Directory", current)
        if folder:
            self.jupyter_custom_path_label.setText(folder)
            self.jupyter_custom_path_label.setVisible(True)

    def _scan_pythons(self):
        """Scan system for Python installations."""
        import os
        import shutil
        self.python_table.setRowCount(0)
        self.default_python_combo.clear()
        self.default_python_combo.addItem("System Default", "")

        excluded_pythons = {
            os.path.normcase(os.path.normpath(p))
            for p in self.config.get("excluded_pythons", [])
        }

        # Which Python is system default — detect from PATH directly (registry on Windows)
        default_norm = ""
        try:
            if os.name == "nt":
                import subprocess as _sp
                _CNW = 0x08000000  # CREATE_NO_WINDOW
                # Read System PATH from registry (fresh, not cached process env)
                sys_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'Machine')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                usr_path = _sp.run(
                    ["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                    capture_output=True, text=True, timeout=5, creationflags=_CNW
                ).stdout.strip()
                # User PATH takes priority (prepended by Set Default)
                for p in (usr_path + ";" + sys_path).split(";"):
                    p = p.strip()
                    if not p:
                        continue
                    candidate = os.path.join(p, "python.exe")
                    if os.path.isfile(candidate) and "windowsapps" not in p.lower():
                        default_norm = os.path.normcase(os.path.normpath(candidate))
                        break
            else:
                import shutil
                exe = shutil.which("python") or shutil.which("python3") or ""
                default_norm = os.path.normcase(os.path.normpath(exe)) if exe else ""
        except Exception:
            # Fallback: use saved config value
            saved_default = self.config.get("system_default_python", "")
            default_norm = os.path.normcase(os.path.normpath(saved_default)) if saved_default else ""

        # All pythons from system scan — deduplicate symlinks
        system_pythons = find_system_pythons()
        listed_paths = set()
        c = self._c()

        # ── System Default Python'u tabloya garanti olarak ilk satıra ekle ──
        if default_norm and os.path.isfile(default_norm):
            try:
                import subprocess as _sp
                result = _sp.run(
                    [default_norm, "--version"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000 if __import__('os').name == "nt" else 0
                )
                sys_version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                sys_version = "?"
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(sys_version))
            _dn_norm = os.path.normpath(default_norm)
            if len(_dn_norm) >= 2 and _dn_norm[1] == ":":
                _dn_norm = _dn_norm[0].upper() + _dn_norm[1:]
            self.python_table.setItem(row, 1, QTableWidgetItem(_dn_norm))
            source_item = QTableWidgetItem("System Default")
            source_item.setForeground(QColor(c['success']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {sys_version} (System Default)", _dn_norm)
            listed_paths.add(default_norm)
            # Also add realpath to prevent symlink duplicates (e.g. python vs python3)
            try:
                listed_paths.add(os.path.normcase(os.path.realpath(default_norm)))
            except Exception:
                pass

        # Resolve symlinks: group by real binary, keep shortest path
        seen_real = {}  # realpath -> (version, norm_path)
        for version, path in system_pythons:
            norm_path = os.path.normpath(path)
            norm_case = os.path.normcase(norm_path)
            if norm_case in excluded_pythons:
                continue
            try:
                real = os.path.realpath(path)
            except OSError:
                real = norm_path
            if real in seen_real:
                # Keep the shorter/cleaner path (e.g. /usr/bin/python over /usr/bin/python3.14)
                existing = seen_real[real]
                if len(norm_path) < len(existing[1]):
                    seen_real[real] = (version, norm_path)
            else:
                seen_real[real] = (version, norm_path)

        for _real, (version, norm_path) in seen_real.items():
            norm_case = os.path.normcase(norm_path)
            # Skip if this realpath was already listed (symlink duplicate)
            real_norm = os.path.normcase(_real)
            if norm_case in listed_paths or real_norm in listed_paths:
                continue
            listed_paths.add(norm_case)
            listed_paths.add(real_norm)

            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            if len(norm_path) >= 2 and norm_path[1] == ":":
                norm_path = norm_path[0].upper() + norm_path[1:]
            if len(norm_path) >= 2 and norm_path[1] == ":":
                norm_path = norm_path[0].upper() + norm_path[1:]
            self.python_table.setItem(row, 0, QTableWidgetItem(version))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))

            # Source label: System / User Install / Custom
            import os as _os
            import sys as _sys
            _home = _os.path.expanduser("~").lower()
            _localappdata = _os.environ.get("LOCALAPPDATA", "").lower()
            _appdata = _os.environ.get("APPDATA", "").lower()
            _progfiles = _os.environ.get("PROGRAMFILES", "C:\\Program Files").lower()
            _progfiles86 = _os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)").lower()
            _windir = _os.environ.get("WINDIR", "C:\\Windows").lower()
            _norm_lower = norm_path.lower()

            _this_exe = _os.path.normcase(_os.path.normpath(_sys.executable)).lower()
            _is_this_python = (_os.path.normcase(norm_path).lower() == _this_exe)

            if _is_this_python and getattr(_sys, "frozen", False):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_progfiles and _norm_lower.startswith(_progfiles)) or
                (_progfiles86 and _norm_lower.startswith(_progfiles86)) or
                (_windir and _norm_lower.startswith(_windir)) or
                "/usr/" in _norm_lower or
                "/opt/" in _norm_lower or
                _norm_lower.startswith("/bin/") or
                _norm_lower.startswith("/usr/bin/")
            ):
                source_item = QTableWidgetItem("System")
                source_item.setForeground(QColor(c['success']))
            elif (
                (_home and _norm_lower.startswith(_home)) or
                (_localappdata and _norm_lower.startswith(_localappdata)) or
                (_appdata and _norm_lower.startswith(_appdata)) or
                "/.local/" in _norm_lower or
                "/.pyenv/" in _norm_lower or
                "/home/" in _norm_lower
            ):
                source_item = QTableWidgetItem("User Install")
                source_item.setForeground(QColor(c['accent']))
            else:
                source_item = QTableWidgetItem("Custom")
                source_item.setForeground(QColor(c['fg_muted']))

            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(f"Python {version}", norm_path)

        # Custom pythons from config (skip already listed)
        custom_pythons = self.config.get("custom_pythons", [])
        cleaned_custom = []
        for entry in custom_pythons:
            norm_path = os.path.normpath(entry.get("path", ""))
            norm_case = os.path.normcase(norm_path)
            if norm_case in listed_paths:
                continue  # already shown above
            cleaned_custom.append(entry)
            listed_paths.add(norm_case)
            row = self.python_table.rowCount()
            self.python_table.insertRow(row)
            self.python_table.setItem(row, 0, QTableWidgetItem(entry.get("version", "?")))
            self.python_table.setItem(row, 1, QTableWidgetItem(norm_path))
            source_item = QTableWidgetItem("Custom")
            source_item.setForeground(QColor(c['accent']))
            self.python_table.setItem(row, 2, source_item)
            self.default_python_combo.addItem(
                f"Python {entry.get('version', '?')} (Custom)", norm_path
            )

        if len(cleaned_custom) != len(custom_pythons):
            self.config.set("custom_pythons", cleaned_custom)

        # Standalone (downloaded) Pythons
        try:
            from src.core.python_downloader import get_installed_pythons
            for py in get_installed_pythons():
                exe_path = os.path.normpath(str(py["python_exe"]))
                if os.path.normcase(exe_path) in listed_paths:
                    continue
                listed_paths.add(os.path.normcase(exe_path))
                row = self.python_table.rowCount()
                self.python_table.insertRow(row)
                self.python_table.setItem(row, 0, QTableWidgetItem(py["version"]))
                self.python_table.setItem(row, 1, QTableWidgetItem(exe_path))
                source_item = QTableWidgetItem("Downloaded")
                source_item.setForeground(QColor(c['success']))
                self.python_table.setItem(row, 2, source_item)
                self.default_python_combo.addItem(
                    f"Python {py['version']} (Downloaded)", exe_path
                )
        except Exception:
            pass

        # Set default python combo selection
        default_py = self.config.get("default_python", "")
        if default_py and default_py.strip():
            default_py_norm = os.path.normpath(default_py)
            found_idx = -1
            for i in range(self.default_python_combo.count()):
                item_data = self.default_python_combo.itemData(i) or ""
                if item_data and os.path.normpath(item_data).lower() == default_py_norm.lower():
                    found_idx = i
                    break
            if found_idx > 0:
                self.default_py_cb.setChecked(True)
                self.default_python_combo.setEnabled(True)
                self.default_python_combo.setCurrentIndex(found_idx)
            else:
                self.default_py_cb.setChecked(False)
                self.default_python_combo.setEnabled(False)
                self.default_python_combo.setCurrentIndex(0)
                self.config.set("default_python", "")
        else:
            self.default_py_cb.setChecked(False)
            self.default_python_combo.setEnabled(False)
            self.default_python_combo.setCurrentIndex(0)

    def _add_custom_python(self):
        """Add a custom Python executable path."""
        import os
        import subprocess
        from src.utils.platform_utils import subprocess_args as sp_args

        if get_platform() == "windows":
            filter_str = "Python Executable (python.exe);;All Files (*)"
        else:
            filter_str = "All Files (*)"

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Python Executable", "", filter_str
        )
        if not filepath:
            return

        filepath = os.path.normpath(filepath)

        # If user selected a directory or a non-exe file, try to find python inside
        if os.path.isdir(filepath):
            candidates = []
            if get_platform() == "windows":
                candidates = [
                    os.path.join(filepath, "python.exe"),
                    os.path.join(filepath, "Scripts", "python.exe"),
                ]
            else:
                candidates = [
                    os.path.join(filepath, "bin", "python3"),
                    os.path.join(filepath, "bin", "python"),
                    os.path.join(filepath, "python3"),
                    os.path.join(filepath, "python"),
                ]
            found = None
            for c in candidates:
                if os.path.isfile(c):
                    found = c
                    break
            if not found:
                QMessageBox.warning(self, "Error", f"Could not find python executable in:\n{filepath}")
                return
            filepath = os.path.normpath(found)

        # If selected file is not named python*, try to find it in parent dir
        basename = os.path.basename(filepath).lower()
        if not basename.startswith("python") and os.path.isfile(filepath):
            parent = os.path.dirname(filepath)
            if get_platform() == "windows":
                alt = os.path.join(parent, "python.exe")
            else:
                alt = os.path.join(parent, "python3")
                if not os.path.isfile(alt):
                    alt = os.path.join(parent, "python")
            if os.path.isfile(alt):
                filepath = os.path.normpath(alt)

        # Verify it's a valid Python
        try:
            result = subprocess.run(
                [filepath, "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            if result.returncode != 0:
                QMessageBox.critical(self, "Error", f"Not a valid Python executable:\n{filepath}")
                return
            version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Not a valid Python executable:\n{e}")
            return

        # Save to config
        custom_pythons = self.config.get("custom_pythons", [])
        for entry in custom_pythons:
            if os.path.normpath(entry.get("path", "")) == filepath:
                QMessageBox.information(self, "Info", "This Python path is already added.")
                return

        custom_pythons.append({"version": version, "path": filepath})
        self.config.set("custom_pythons", custom_pythons)
        self._scan_pythons()

        QMessageBox.information(self, "Success", f"Added Python {version}\n{filepath}")

    def _remove_custom_python(self):
        """Remove a custom or downloaded Python path."""
        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version to remove.")
            return

        row = rows[0].row()
        source = self.python_table.item(row, 2).text()
        version = self.python_table.item(row, 0).text()
        path = self.python_table.item(row, 1).text()

        if source == "System":
            QMessageBox.information(
                self, "Info",
                "System-detected Python installations cannot be removed here.\n"
                "Use your system package manager to uninstall them."
            )
            return

        if source == "User Install":
            reply = QMessageBox.question(
                self, "Remove User Install",
                f"Remove Python {version} from the list?\n\n"
                f"  {path}\n\n"
                f"Note: This only removes it from VenvStudio's list.\n"
                f"To fully uninstall, use: pip uninstall python (or your package manager).",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                # Save to config as excluded path so it won't reappear on next scan
                excluded = self.config.get("excluded_pythons", [])
                if path not in excluded:
                    excluded.append(path)
                    self.config.set("excluded_pythons", excluded)
                self._scan_pythons()
            return

        if source == "Downloaded":
            reply = QMessageBox.question(
                self, "Remove Downloaded Python",
                f"Permanently delete Python {version}?\n\n"
                f"  {path}\n\n"
                f"This will remove the downloaded files from disk.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            try:
                from src.core.python_downloader import get_installed_pythons, remove_python
                for py in get_installed_pythons():
                    if py["version"] == version or os.path.normpath(str(py.get("python_exe", ""))) == os.path.normpath(path):
                        remove_python(py["path"])
                        break
                self._scan_pythons()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove Python {version}:\n{e}")
            return

        # source == "Custom"
        custom_pythons = self.config.get("custom_pythons", [])
        custom_pythons = [e for e in custom_pythons if e.get("path") != path]
        self.config.set("custom_pythons", custom_pythons)
        self._scan_pythons()

    def _set_python_default(self, scope="user"):
        """
        Set selected Python as default.
        scope='user'   → Update User PATH (no admin needed if System PATH is clean)
        scope='system' → Update System PATH (admin required)
        Both modes remove OTHER Python entries from BOTH scopes.
        """
        import os, subprocess, tempfile
        from src.utils.platform_utils import get_platform, subprocess_args

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()

        platform = get_platform()

        # ── Linux / macOS ──
        if platform != "windows":
            self._set_python_default_unix(version, python_path, scope)
            return

        python_dir = os.path.normpath(os.path.dirname(python_path))
        scripts_dir = os.path.join(python_dir, "Scripts")

        scope_label = "User" if scope == "user" else "System"

        # Read both PATHs
        try:
            user_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('Path', 'User')"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            ).stdout.strip() or ""

            system_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('Path', 'Machine')"],
                capture_output=True, text=True, timeout=10, **subprocess_args()
            ).stdout.strip() or ""
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read PATH:\n{e}")
            return

        # Find ALL Python dirs in a PATH string (excluding our target)
        def find_python_dirs(path_str, exclude_dirs):
            """Find PATH entries that belong to OTHER Python installations.
            ONLY removes dirs where python.exe exists directly,
            or Scripts dirs whose PARENT contains python.exe AND pip.exe.
            Never touches non-Python dirs like winget, oh-my-posh, etc.
            """
            exclude_set = {os.path.normcase(d.rstrip("\\")) for d in exclude_dirs}
            found = []
            for p in path_str.split(";"):
                p = p.strip()
                if not p:
                    continue
                p_norm = os.path.normcase(p.rstrip("\\"))
                if p_norm in exclude_set:
                    continue
                # Must have python.exe directly in this dir
                if os.path.exists(os.path.join(p, "python.exe")):
                    found.append(p)
                    continue
                # Scripts dir — ONLY if parent has BOTH python.exe AND pip.exe
                if os.path.basename(p).lower() == "scripts":
                    parent = os.path.dirname(p)
                    has_python = os.path.exists(os.path.join(parent, "python.exe"))
                    has_pip = os.path.exists(os.path.join(p, "pip.exe"))
                    if has_python and has_pip:
                        found.append(p)
            return found

        target_dirs = [python_dir, scripts_dir]
        other_in_user = find_python_dirs(user_path, target_dirs)
        other_in_system = find_python_dirs(system_path, target_dirs)

        # Build confirmation message
        changes = [f"✅ Add to {scope_label} PATH:\n   📂 {python_dir}\n   📂 {scripts_dir}"]

        if other_in_user:
            changes.append("🗑️ Remove from User PATH:\n" +
                          "\n".join(f"   ❌ {p}" for p in other_in_user))
        if other_in_system:
            changes.append("🗑️ Remove from System PATH:\n" +
                          "\n".join(f"   ❌ {p}" for p in other_in_system))

        needs_admin = scope == "system" or bool(other_in_system)
        admin_note = "\n\n🔒 Admin permission required." if needs_admin else ""

        confirm = QMessageBox.question(
            self, f"Set {scope_label} Default",
            f"Set Python {version} as {scope_label} default?\n\n" +
            "\n\n".join(changes) + admin_note,
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # Build set of ALL dirs to remove (+ their Scripts counterparts)
        all_remove = set()
        for p in other_in_user + other_in_system:
            norm = os.path.normcase(p.rstrip("\\"))
            all_remove.add(norm)
            all_remove.add(os.path.normcase(os.path.join(p, "Scripts").rstrip("\\")))
            if os.path.basename(p).lower() == "scripts":
                all_remove.add(os.path.normcase(os.path.dirname(p).rstrip("\\")))

        # Also include target dirs in removal filter (we re-add them at top)
        all_remove.add(os.path.normcase(python_dir.rstrip("\\")))
        all_remove.add(os.path.normcase(scripts_dir.rstrip("\\")))

        def build_ps_filter(dirs):
            conds = []
            for d in sorted(dirs):
                escaped = d.replace("'", "''")
                conds.append(f"($lower -ne '{escaped}')")
            return " -and ".join(conds) if conds else "$true"

        result_file = os.path.join(tempfile.gettempdir(), "_venvstudio_path_result.txt")

        # SAFE approach: only PREPEND selected Python to PATH — never delete anything else
        # This avoids accidentally removing winget, oh-my-posh, or other tools from PATH.
        # Users with multiple Python versions can use `py -3.x` launcher to choose.
        if scope == "user":
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from User PATH (to avoid duplicates), then prepend
    $uPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $uParts = ($uPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newUser = ('{python_dir};{scripts_dir};' + ($uParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newUser, 'User')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''
        else:  # system
            ps_script = f'''
try {{
    # Remove only the exact target Python dirs from System PATH (to avoid duplicates), then prepend
    $sPath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $sParts = ($sPath -split ';') | Where-Object {{ $_.Trim() -ne '' }} | Where-Object {{
        $lower = $_.ToLower().TrimEnd('\\')
        ($lower -ne '{python_dir.lower()}') -and ($lower -ne '{scripts_dir.lower()}')
    }}
    $newSys = ('{python_dir};{scripts_dir};' + ($sParts -join ';'))
    [Environment]::SetEnvironmentVariable('Path', $newSys, 'Machine')

    'OK' | Out-File -FilePath '{result_file}' -Encoding utf8
}} catch {{
    $_.Exception.Message | Out-File -FilePath '{result_file}' -Encoding utf8
}}
'''

        # Write and execute
        ps_file = os.path.join(tempfile.gettempdir(), "_venvstudio_set_path.ps1")
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_script)

        if os.path.exists(result_file):
            os.unlink(result_file)

        try:
            if needs_admin:
                subprocess.run(
                    [
                        "powershell", "-NoProfile", "-Command",
                        f"Start-Process -FilePath 'powershell.exe' "
                        f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"{ps_file}\"' "
                        f"-Verb RunAs -Wait"
                    ],
                    capture_output=True, text=True, timeout=120,
                    **subprocess_args()
                )
            else:
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", ps_file],
                    capture_output=True, text=True, timeout=30,
                    **subprocess_args()
                )

            import time
            time.sleep(1)

            success = False
            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
                    result_text = f.read().strip()
                if "OK" in result_text:
                    success = True
                else:
                    raise RuntimeError(result_text)

            if not success:
                target_scope_name = 'Machine' if scope == 'system' else 'User'
                verify = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[Environment]::GetEnvironmentVariable('Path', '{target_scope_name}')"],
                    capture_output=True, text=True, timeout=10,
                    **subprocess_args()
                )
                if python_dir.lower() in verify.stdout.strip().lower():
                    success = True

            if success:
                # Verify pip.exe actually exists in Scripts dir
                pip_status = ""
                if not os.path.isfile(pip_exe):
                    pip_status = (
                        f"\n\n⚠️ pip.exe not found in Scripts folder!\n"
                        f"   Run: python -m pip install --upgrade pip\n"
                        f"   (in an admin terminal)"
                    )
                else:
                    pip_status = f"\n\n✅ pip.exe found in Scripts folder."

                QMessageBox.information(
                    self, "✅ Success",
                    f"Python {version} is now the {scope_label} default!\n\n"
                    f"📂 Added to PATH:\n"
                    f"   {python_dir}\n"
                    f"   {scripts_dir}"
                    f"{pip_status}\n\n"
                    f"Open a new terminal and type:\n"
                    f"  python --version\n"
                    f"  pip --version"
                )
                self.config.set("system_default_python", python_path)
                # Save as system default so _scan_pythons shows correct Source
                self.config.set("system_default_python", python_path)
                self._scan_pythons()
            else:
                QMessageBox.warning(
                    self, "⚠️ Partial",
                    f"Could not verify the change.\n"
                    f"Admin permission may have been denied.\n\n"
                    f"Check Environment Variables manually."
                )
                self._scan_pythons()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update PATH:\n{e}")
        finally:
            for fp in [ps_file, result_file]:
                try:
                    os.unlink(fp)
                except Exception:
                    pass

    def _download_python(self):
        """Open dialog to download a standalone Python version."""
        dlg = PythonDownloadDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._scan_pythons()

    def _browse_venv_dir(self):
        """Browse for environment base directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Base Directory for Environments",
            self.venv_dir_input.text(),
        )
        if directory:
            self.venv_dir_input.setText(directory)

    def _reset_venv_dir(self):
        """Reset venv directory to default."""
        from src.utils.platform_utils import get_default_venv_base_dir
        self.venv_dir_input.setText(str(get_default_venv_base_dir()))
