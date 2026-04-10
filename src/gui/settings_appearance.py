"""VenvStudio - Settings: AppearanceMixin"""
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


class AppearanceMixin:
    """Mixin for SettingsPage."""
    def _reset_fonts(self):
        """Reset all font settings to system defaults."""
        _defaults = {"primary": 22, "secondary": 13, "tertiary": 11}
        for level_id, def_size in _defaults.items():
            cb = getattr(self, f"font_{level_id}_cb")
            combo = getattr(self, f"font_{level_id}_combo")
            spin = getattr(self, f"font_{level_id}_size")
            cb.setChecked(False)
            combo.setEnabled(False)
            combo.setCurrentFont(QFont("Segoe UI"))
            spin.setEnabled(False)
            spin.setValue(def_size)
            self.config.set(f"font_{level_id}_family", "")
            self.config.set(f"font_{level_id}_size", def_size)
        self.config.set("font_family", "")
        self.config.set("font_size", 13)
        self.font_changed.emit("Segoe UI", 13)



    def _on_theme_cb_toggled(self, on):
        """Enable/disable theme combo and apply theme live."""
        self.theme_combo.setEnabled(on)
        if on:
            self._on_theme_live_preview()
        else:
            # Checkbox unchecked → revert to dark
            self.config.set("theme", "dark")
            self.theme_changed.emit("dark")

    def _on_theme_live_preview(self, _idx=None):
        """Apply theme instantly when dropdown changes — no Save needed."""
        if not self.theme_cb.isChecked():
            return
        theme = self.theme_combo.currentData()
        if theme:
            self.config.set("theme", theme)
            self.theme_changed.emit(theme)
            self._refresh_styles()

    def _cli_log_append(self, text: str):
        import html as _html
        c = self._c()
        for line in text.split("\n"):
            t = line.strip()
            if not t:
                continue
            escaped = _html.escape(t)
            if t.startswith("✅"):
                color = c['success']
            elif t.startswith("❌"):
                color = c['danger']
            elif t.startswith("⬇️") or t.startswith("📦"):
                color = c['accent']
            elif t.startswith("⚠️"):
                color = c.get('warning', '#f9e2af')
            else:
                color = c['fg']
            self.cli_log.append(f'<span style="color:{color};">{escaped}</span>')

    def _make_cli_card(self, tool_id, title, desc, preset_label, presets, preset_key,
                        preset_descriptions=None):
        """Create a card widget for binary CLI tools (starship, oh-my-posh)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"cli_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Title + status
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"\u2705 {version}" if installed else "\u274c Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        status_lbl.setObjectName(f"status_{tool_id.replace('-','_')}")
        header.addWidget(status_lbl)
        header.addStretch()
        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # Preset selector + buttons
        controls = QHBoxLayout()
        controls.setSpacing(6)

        cb_key = f"cb_preset_{tool_id.replace('-','_')}"
        preset_cb = QCheckBox(preset_label)
        preset_cb.setStyleSheet(f"font-size: {self._c()['fs_tiny']}px; color: {self._c()['fg']};")
        preset_cb.setObjectName(cb_key)
        controls.addWidget(preset_cb)

        combo = QComboBox()
        combo.setMaximumWidth(200)
        for p in presets:
            label = p
            if preset_descriptions and p in preset_descriptions:
                label = f"{p}  \u2014  {preset_descriptions[p]}"
            combo.addItem(label, p)
        combo.setObjectName(f"preset_{tool_id.replace('-','_')}")
        combo.setEnabled(False)
        preset_cb.toggled.connect(combo.setEnabled)
        controls.addWidget(combo)

        # Preset description label (updates on selection)
        desc_hint = None
        if preset_descriptions:
            desc_hint = QLabel("")
            desc_hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; font-style: italic;")
            desc_hint.setFixedHeight(16)

            def _update_preset_hint(idx, _dh=desc_hint, _c=combo, _pd=preset_descriptions):
                key = _c.itemData(idx)
                if key and key in _pd:
                    _dh.setText(_pd[key])
                else:
                    _dh.setText("")

            combo.currentIndexChanged.connect(_update_preset_hint)
            _update_preset_hint(0)

        controls.addStretch()

        install_btn = QPushButton("\u2b07\ufe0f Install" if not installed else "\U0001f504 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        controls.addWidget(install_btn)

        if installed:
            cfg_btn = QPushButton("\u2699\ufe0f Configure Shell")
            cfg_btn.setObjectName("secondary")
            cfg_btn
            cfg_btn.clicked.connect(lambda _, t=tool_id, c=combo, pk=preset_key: self._cli_configure(t, c, pk))
            controls.addWidget(cfg_btn)

            # Starship-specific: Edit Config + Test buttons
            if tool_id == "starship":
                edit_btn = QPushButton("\U0001f4dd Edit Config")
                edit_btn.setObjectName("secondary")
                edit_btn
                edit_btn.setToolTip("Open starship.toml inline editor")
                edit_btn.clicked.connect(self._open_starship_editor)
                controls.addWidget(edit_btn)

                test_btn = QPushButton("\u25b6\ufe0f Test")
                test_btn.setObjectName("secondary")
                test_btn
                test_btn.setToolTip("Open a terminal to test your Starship prompt")
                test_btn.clicked.connect(self._test_starship_in_terminal)
                controls.addWidget(test_btn)

            uninst_btn = QPushButton("\U0001f5d1\ufe0f Uninstall")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            controls.addWidget(uninst_btn)

        layout.addLayout(controls)

        # Preset description below controls
        if desc_hint:
            layout.addWidget(desc_hint)

        return card

    def _make_pip_card(self, tool_id, title, desc):
        """Create a card widget for pip-based tools (rich, textual, prompt_toolkit)."""
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        card = QFrame()
        card.setObjectName(f"pip_card_{tool_id.replace('-','_')}")
        card.setStyleSheet(self._frame_style())
        self._theme_frames.append(card)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: {self._c()['fs_base']}px; color: {self._c()['fg']};")
        header.addWidget(title_lbl)

        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl = QLabel(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        header.addWidget(status_lbl)
        header.addStretch()

        install_btn = QPushButton("⬇️ Install" if not installed else "🔄 Reinstall")
        install_btn.setObjectName("secondary")
        install_btn
        install_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_install(t, sb, sl))
        header.addWidget(install_btn)

        if installed:
            uninst_btn = QPushButton("🗑️")
            uninst_btn.setObjectName("danger")
            uninst_btn
            uninst_btn.setMinimumWidth(32)
            uninst_btn.clicked.connect(lambda _, t=tool_id, sb=install_btn, sl=status_lbl: self._cli_uninstall(t, sb, sl))
            header.addWidget(uninst_btn)

        layout.addLayout(header)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addWidget(desc_lbl)
        return card

    def _cli_install(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        btn.setEnabled(False)
        btn.setText("⏳ Installing...")
        self.cli_log.clear()
        self._cli_worker = CliToolWorker("install", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_uninstall(self, tool_id, btn, status_lbl):
        from src.core.cli_tools_manager import CliToolWorker
        reply = QMessageBox.question(self, "Uninstall", f"Uninstall {tool_id}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._cli_worker = CliToolWorker("uninstall", tool_id, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg, b=btn, sl=status_lbl, t=tool_id: self._cli_done(ok, msg, b, sl, t)
        )
        self._cli_worker.start()

    def _cli_configure(self, tool_id, combo, preset_key):
        from src.core.cli_tools_manager import CliToolWorker
        theme = combo.currentData() or combo.currentText()
        self._cli_worker = CliToolWorker("configure", tool_id, {preset_key: theme}, parent=self)
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()


    def _open_starship_editor(self):
        """Open inline editor for starship.toml."""
        from src.core.cli_tools_manager import read_starship_toml, write_starship_toml, get_starship_toml_path
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel, QMessageBox
        from PySide6.QtGui import QFont

        dlg = QDialog(self)
        dlg.setWindowTitle("📝 Starship Config Editor — starship.toml")
        dlg.resize(700, 500)
        dlg.setStyleSheet(
            f"QDialog {{ background: {self._c()['bg']}; }}"
            f"QPlainTextEdit {{ background: {self._c()['sidebar']}; color: {self._c()['fg']}; border: 1px solid {self._c()['border']}; "
            f"border-radius: 4px; font-family: 'Consolas', 'JetBrains Mono', monospace; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton {{ padding: 6px 16px; border-radius: 4px; font-size: {self._c()['fs_small']}px; }}"
            f"QPushButton#save {{ background: {self._c()['success']}; color: {self._c()['accent_fg']}; font-weight: bold; }}"
            "QPushButton#save:hover { background: #94d89d; }"
            f"QPushButton#secondary {{ background: {self._c()['secondary']}; color: {self._c()['fg']}; }}"
            "QPushButton#secondary:hover { background: #45475a; }"
            f"QLabel {{ color: #6c7086; font-size: {self._c()['fs_tiny']}px; }}"
        )

        layout = QVBoxLayout(dlg)

        path_label = QLabel(f"📂 {get_starship_toml_path()}")
        layout.addWidget(path_label)

        editor = QPlainTextEdit()
        editor.setFont(QFont("Consolas", 12))
        editor.setPlainText(read_starship_toml())
        editor.setTabStopDistance(28)
        layout.addWidget(editor)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.setObjectName("secondary")
        reload_btn.clicked.connect(lambda: editor.setPlainText(read_starship_toml()))
        btn_row.addWidget(reload_btn)

        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setObjectName("secondary")
        open_folder_btn.clicked.connect(lambda: __import__("subprocess").Popen(
            ["explorer" if __import__("sys").platform == "win32" else "xdg-open",
             str(get_starship_toml_path().parent)]
        ))
        btn_row.addWidget(open_folder_btn)

        save_btn = QPushButton("💾 Save")
        save_btn.setObjectName("save")
        def _do_save():
            if write_starship_toml(editor.toPlainText()):
                self._cli_log_append("✅ starship.toml saved")
                QMessageBox.information(dlg, "Saved", "starship.toml saved successfully! ✅\n\nOpen a new terminal to see changes.")
            else:
                QMessageBox.critical(dlg, "Error", "Failed to save starship.toml")
        save_btn.clicked.connect(_do_save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        dlg.exec()

    def _test_starship_in_terminal(self):
        """Open a terminal so user can see their Starship prompt in action."""
        import sys as _sys
        from src.core.cli_tools_manager import is_tool_installed
        if not is_tool_installed("starship"):
            QMessageBox.warning(self, "Starship", "Starship is not installed.")
            return
        try:
            if _sys.platform == "win32":
                import subprocess
                # Open PowerShell with starship init
                subprocess.Popen(
                    ["powershell", "-NoExit", "-Command",
                     "Invoke-Expression (&starship init powershell)"],
                    creationflags=0x00000010  # CREATE_NEW_CONSOLE
                )
            elif _sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal"])
            else:
                import subprocess
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    import shutil
                    if shutil.which(term):
                        subprocess.Popen([term])
                        break
            self._cli_log_append("✅ Terminal opened — check your Starship prompt!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open terminal:\n{e}")

    def _cli_done(self, ok, msg, btn, status_lbl, tool_id):
        from src.core.cli_tools_manager import is_tool_installed, get_tool_version
        self._cli_log_append(msg)
        installed = is_tool_installed(tool_id)
        version = get_tool_version(tool_id) or ""
        status_lbl.setText(f"✅ {version}" if installed else "❌ Not installed")
        status_lbl.setStyleSheet(f"color: {self._c()['success'] if installed else self._c()['danger']}; font-size: {self._c()['fs_tiny']}px;")
        btn.setEnabled(True)
        btn.setText("🔄 Reinstall" if installed else "⬇️ Install")

    def _install_nerd_font(self):
        from src.core.cli_tools_manager import CliToolWorker
        if not self.nerd_font_cb.isChecked():
            QMessageBox.information(self, "Info", "Enable the Font checkbox first to select a font.")
            return
        font_id   = self.nerd_font_combo.currentData()
        font_name = self.nerd_font_combo.currentText()
        self.cli_log.clear()
        self._cli_worker = CliToolWorker(
            "install_font", "font",
            {"font_id": font_id, "font_name": font_name},
            parent=self
        )
        self._cli_worker.progress.connect(self._cli_log_append)
        self._cli_worker.finished.connect(
            lambda ok, msg: self._cli_log_append(msg)
        )
        self._cli_worker.start()

    def _verify_pip_venv(self):
        """Check pip and venv for selected Python, offer to fix if missing."""
        import os, subprocess
        from src.utils.platform_utils import subprocess_args as sp_args, get_platform

        rows = self.python_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Select a Python version first.")
            return

        row = rows[0].row()
        version = self.python_table.item(row, 0).text()
        python_path = self.python_table.item(row, 1).text()
        is_windows = get_platform() == "windows"
        if is_windows:
            scripts_dir = os.path.join(os.path.dirname(python_path), "Scripts")
        else:
            # On Linux/macOS, python is already in /usr/bin or similar — no "bin" subdir
            scripts_dir = os.path.dirname(python_path)


        # ── pip check ──
        pip_version_str = ""
        pip_runnable = False
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "--version"],
                **sp_args(capture_output=True, text=True, timeout=10)
            )
            if result.returncode == 0:
                pip_runnable = True
                pip_version_str = result.stdout.strip()
        except Exception:
            pass

        # ── venv check ──
        venv_available = False
        try:
            result = subprocess.run(
                [python_path, "-c", "import venv; print(venv.__name__)"],
                **sp_args(capture_output=True, text=True, timeout=10)
            )
            if result.returncode == 0 and "venv" in result.stdout:
                venv_available = True
        except Exception:
            pass

        # Check if selected python is the system default (which python / which python3)
        scripts_in_path = False
        if is_windows:
            current_path = os.environ.get("PATH", "")
            path_sep = ";"
            scripts_in_path = scripts_dir.lower().rstrip("/\\") in [
                p.lower().rstrip("/\\") for p in current_path.split(path_sep)
            ]
        else:
            try:
                real_selected = os.path.realpath(python_path)
                default_in_path = False
                for cmd in ["python", "python3"]:
                    result = subprocess.run(
                        ["which", cmd],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        which_path = result.stdout.strip()
                        if os.path.realpath(which_path) == real_selected:
                            default_in_path = True
                            break
                scripts_in_path = default_in_path
            except Exception:
                pass

        pip_status = "✅ Working" if pip_runnable else "❌ Not working"
        venv_status = "✅ Available" if venv_available else "❌ Not available"
        path_status = "✅ Yes" if scripts_in_path else "⚠️ Not in current session"

        msg = (
            f"Python: {version}\n"
            f"Path:   {python_path}\n\n"
            f"pip:              {pip_status}\n"
            f"venv:            {venv_status}\n"
            f"Scripts in PATH: {path_status}"
        )
        if pip_runnable and pip_version_str:
            msg += "\n\n" + pip_version_str

        issues = []
        if not pip_runnable:
            issues.append("pip is not working — python -m pip failed.")
        if not venv_available:
            if is_windows:
                issues.append("venv module not available — try reinstalling Python with 'pip' option enabled.")
            else:
                issues.append("venv module not available — install python3-venv:\n"
                              "    Debian/Ubuntu: sudo apt install python3-venv\n"
                              "    Arch: included in python package")
        if not scripts_in_path:
            issues.append("Scripts folder not in current PATH — open a new terminal after Set Default.")

        if issues:
            msg += "\n\nIssues found:\n" + "\n".join("  * " + i for i in issues)
            fix_actions = []
            if not pip_runnable:
                fix_actions.append("reinstall pip")
            if not venv_available and not is_windows:
                fix_actions.append("install python3-venv (requires sudo)")

            if fix_actions:
                msg += "\n\nWould you like to fix now? (" + ", ".join(fix_actions) + ")"
                reply = QMessageBox.question(self, "pip & venv Status", msg, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if not pip_runnable:
                        self._fix_pip(python_path, version)
                    if not venv_available and not is_windows:
                        self._fix_venv()
            else:
                QMessageBox.warning(self, "pip & venv Status", msg)
        else:
            QMessageBox.information(self, "✅ pip & venv OK", msg)

    def _fix_venv(self):
        """Attempt to install python3-venv on Linux."""
        import subprocess, shutil
        if shutil.which("apt"):
            cmd = "sudo apt install -y python3-venv"
        elif shutil.which("pacman"):
            QMessageBox.information(self, "venv", "On Arch, venv is included in the python package.\nTry: sudo pacman -S python")
            return
        elif shutil.which("dnf"):
            cmd = "sudo dnf install -y python3-venv"
        else:
            QMessageBox.information(self, "venv", "Please install python3-venv using your package manager.")
            return
        try:
            subprocess.Popen(["sh", "-c", f"x-terminal-emulator -e '{cmd}' || xterm -e '{cmd}'"])
        except Exception as e:
            QMessageBox.warning(self, "venv Install", f"Could not start terminal:\n{e}\n\nRun manually: {cmd}")

    def _fix_pip(self, python_path, version):
        """Reinstall pip for the given Python executable."""
        import subprocess
        from src.utils.platform_utils import subprocess_args as sp_args

        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pip"],
                **sp_args(capture_output=True, text=True, timeout=60)
            )
            if result.returncode == 0:
                QMessageBox.information(
                    self, "pip Fixed",
                    "pip reinstalled for Python " + version + "!\n\n"
                    "Open a new terminal and run: pip --version"
                )
            else:
                err = result.stderr.strip() or result.stdout.strip()
                QMessageBox.critical(
                    self, "pip Fix Failed",
                    "Could not reinstall pip.\n\n" + err + "\n\n"
                    "Try manually (as admin):\n"
                    '  "' + python_path + '" -m pip install --upgrade --force-reinstall pip'
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to run pip fix:\n" + str(e))
        self._scan_pythons()

    def _set_python_default_unix(self, version, python_path, scope):
        """Set default Python on Linux/macOS using update-alternatives or symlinks."""
        import subprocess, shutil

        platform = get_platform()
        ver_short = ".".join(version.split(".")[:2])  # e.g. "3.12"
        ver_nodot = ver_short.replace(".", "")          # e.g. "312"

        if platform == "linux":
            # Use update-alternatives if available
            if shutil.which("update-alternatives"):
                priority = 100

                reply = QMessageBox.question(
                    self, f"Set Default Python",
                    f"Register Python {version} as system default?\n\n"
                    f"  python3   → {python_path}\n"
                    f"  python3.{ver_short.split('.')[-1]} → {python_path}\n\n"
                    f"Uses update-alternatives (requires admin password).",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                cmds = [
                    ["update-alternatives", "--install",
                     "/usr/bin/python3", "python3", python_path, str(priority)],
                    ["update-alternatives", "--install",
                     "/usr/bin/python", "python", python_path, str(priority)],
                    ["update-alternatives", "--set", "python3", python_path],
                    ["update-alternatives", "--set", "python", python_path],
                ]

                success = True
                for cmd in cmds:
                    for sudo in [["pkexec"], ["sudo"]]:
                        try:
                            r = subprocess.run(
                                sudo + cmd,
                                capture_output=True, text=True, timeout=30
                            )
                            if r.returncode == 0:
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    else:
                        success = False
                        break

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Python {version} set as system default!\n\n"
                        f"Verify with:  python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not set default Python.\n\n"
                        f"Try manually:\n"
                        f"  sudo update-alternatives --install /usr/bin/python3 python3 {python_path} 100\n"
                        f"  sudo update-alternatives --set python3 {python_path}"
                    )
            else:
                # No update-alternatives — create symlink in /usr/local/bin
                reply = QMessageBox.question(
                    self, "Set Default Python",
                    f"Create symlinks for Python {version}?\n\n"
                    f"  /usr/local/bin/python3  → {python_path}\n"
                    f"  /usr/local/bin/python   → {python_path}\n\n"
                    f"Requires admin password.",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                script = (
                    f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                    f"ln -sf '{python_path}' /usr/local/bin/python"
                )
                success = False
                for sudo in [["pkexec", "bash", "-c"], ["sudo", "bash", "-c"]]:
                    try:
                        r = subprocess.run(sudo + [script], capture_output=True, text=True, timeout=30)
                        if r.returncode == 0:
                            success = True
                            break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

                if success:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(
                        self, "❌ Failed",
                        f"Could not create symlinks.\n\nTry manually:\n"
                        f"  sudo ln -sf {python_path} /usr/local/bin/python3"
                    )

        elif platform == "macos":
            # macOS: symlink in /usr/local/bin
            reply = QMessageBox.question(
                self, "Set Default Python",
                f"Create symlinks for Python {version}?\n\n"
                f"  /usr/local/bin/python3  → {python_path}\n"
                f"  /usr/local/bin/python   → {python_path}\n\n"
                f"Requires admin password.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            script = (
                f"ln -sf '{python_path}' /usr/local/bin/python3 && "
                f"ln -sf '{python_path}' /usr/local/bin/python"
            )
            try:
                r = subprocess.run(
                    ["osascript", "-e",
                     f'do shell script "{script}" with administrator privileges'],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0:
                    QMessageBox.information(
                        self, "✅ Success",
                        f"Symlinks created for Python {version}.\n\nVerify: python3 --version"
                    )
                else:
                    QMessageBox.critical(self, "❌ Failed", f"Could not create symlinks:\n{r.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_custom_terminals(self):
        """Load custom terminals from config into table."""
        terminals = self.config.get("custom_terminals", [])
        self.custom_term_table.setRowCount(0)
        for t in terminals:
            row = self.custom_term_table.rowCount()
            self.custom_term_table.insertRow(row)
            self.custom_term_table.setItem(row, 0, QTableWidgetItem(t.get("name", "")))
            self.custom_term_table.setItem(row, 1, QTableWidgetItem(t.get("command", "")))
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked if t.get("enabled", True) else Qt.Unchecked)
            self.custom_term_table.setItem(row, 2, chk)
            # Also add to terminal_combo if enabled
            if t.get("enabled", True):
                name = t.get("name", "")
                if self.terminal_combo.findData(f"custom:{name}") < 0:
                    self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _save_custom_terminals(self):
        """Save custom terminals from table to config."""
        terminals = []
        for row in range(self.custom_term_table.rowCount()):
            name = self.custom_term_table.item(row, 0).text() if self.custom_term_table.item(row, 0) else ""
            cmd = self.custom_term_table.item(row, 1).text() if self.custom_term_table.item(row, 1) else ""
            chk = self.custom_term_table.item(row, 2)
            enabled = chk.checkState() == Qt.Checked if chk else True
            if name and cmd:
                terminals.append({"name": name, "command": cmd, "enabled": enabled})
        self.config.set("custom_terminals", terminals)

    def _add_custom_terminal(self):
        """Add a new custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g. My Terminal")
        cmd_edit = QLineEdit()
        cmd_edit.setPlaceholderText('e.g. wt -d "{path}" cmd /k "{activate}"')

        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")

        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            cmd = cmd_edit.text().strip()
            if name and cmd:
                row = self.custom_term_table.rowCount()
                self.custom_term_table.insertRow(row)
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(cmd))
                chk = QTableWidgetItem()
                chk.setCheckState(Qt.Checked)
                self.custom_term_table.setItem(row, 2, chk)
                # Add to combo
                self.terminal_combo.addItem(f"⚡ {name}", f"custom:{name}")

    def _edit_custom_terminal(self):
        """Edit selected custom terminal."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Please select a terminal to edit.")
            return
        old_name = self.custom_term_table.item(row, 0).text()
        old_cmd = self.custom_term_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Custom Terminal")
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(old_name)
        cmd_edit = QLineEdit(old_cmd)
        hint = QLabel("Variables: {path} = env path, {activate} = activate script")
        hint.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        layout.addRow("Name:", name_edit)
        layout.addRow("Command:", cmd_edit)
        layout.addRow(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addRow(btns)

        if dialog.exec() == QDialog.Accepted:
            new_name = name_edit.text().strip()
            new_cmd = cmd_edit.text().strip()
            if new_name and new_cmd:
                self.custom_term_table.setItem(row, 0, QTableWidgetItem(new_name))
                self.custom_term_table.setItem(row, 1, QTableWidgetItem(new_cmd))
                # Update combo
                idx = self.terminal_combo.findData(f"custom:{old_name}")
                if idx >= 0:
                    self.terminal_combo.setItemText(idx, f"⚡ {new_name}")
                    self.terminal_combo.setItemData(idx, f"custom:{new_name}")

    def _remove_custom_terminal(self):
        """Remove selected custom terminal."""
        row = self.custom_term_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Please select a terminal to remove.")
            return
        name = self.custom_term_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Remove Terminal",
            f"Remove '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.custom_term_table.removeRow(row)
            idx = self.terminal_combo.findData(f"custom:{name}")
            if idx >= 0:
                self.terminal_combo.removeItem(idx)

    def _detect_terminals(self):
        """Scan for installed terminals on Linux, offer to install missing ones via pkexec."""
        import shutil

        ALL_TERMINALS = [
            ("GNOME Terminal", "gnome-terminal", "gnome-terminal"),
            ("Konsole", "konsole", "konsole"),
            ("Xfce4 Terminal", "xfce4-terminal", "xfce4-terminal"),
            ("Tilix", "tilix", "tilix"),
            ("Mate Terminal", "mate-terminal", "mate-terminal"),
            ("Alacritty", "alacritty", "alacritty"),
            ("Kitty", "kitty", "kitty"),
            ("xterm", "xterm", "xterm"),
        ]

        installed = [(label, data) for label, data, cmd in ALL_TERMINALS if shutil.which(cmd)]
        not_installed = [(label, data, cmd) for label, data, cmd in ALL_TERMINALS if not shutil.which(cmd)]

        # Update dropdown — show only installed + System Default
        current_data = self.terminal_combo.currentData()
        self.terminal_combo.blockSignals(True)
        self.terminal_combo.clear()
        self.terminal_combo.addItem("System Default", "default")
        for label, data in installed:
            self.terminal_combo.addItem(f"✅ {label}", data)
        for label, data, _ in not_installed:
            self.terminal_combo.addItem(f"❌ {label} (not installed)", data)
        # Restore selection
        idx = self.terminal_combo.findData(current_data)
        self.terminal_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.terminal_combo.blockSignals(False)

        if not installed:
            msg = "No supported terminals found on your system.\n\n"
        else:
            names = ", ".join(l for l, _ in installed)
            msg = f"Found: {names}\n\n"

        if not not_installed:
            QMessageBox.information(self, "Terminal Detection", msg + "All supported terminals are installed.")
            return

        missing_names = "\n".join(f"  • {l}" for l, _, _ in not_installed)
        reply = QMessageBox.question(
            self, "Terminal Detection",
            msg + f"Not installed:\n{missing_names}\n\n"
            f"Install a terminal? (requires admin password)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Let user pick which one to install
        items = [l for l, _, _ in not_installed]
        from PySide6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self, "Install Terminal",
            "Select a terminal to install:",
            items, 0, False,
        )
        if not ok or not choice:
            return

        pkg = next((cmd for l, _, cmd in not_installed if l == choice), None)
        if not pkg:
            return

        # Try pkexec first, fallback to sudo
        import subprocess
        success = False
        for sudo_cmd in [["pkexec"], ["sudo"]]:
            try:
                result = subprocess.run(
                    sudo_cmd + ["apt-get", "install", "-y", pkg],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    success = True
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        if success:
            QMessageBox.information(
                self, "✅ Installed",
                f"{choice} installed successfully!\n\nIt has been added to the terminal list.",
            )
            self._detect_terminals()  # Refresh dropdown
        else:
            QMessageBox.critical(
                self, "❌ Failed",
                f"Could not install {choice}.\n\n"
                f"Try manually:\n  sudo apt-get install {pkg}",
            )

    def _toggle_language(self, enabled):
        """Enable/disable language combo based on checkbox."""
        self.lang_combo.setEnabled(enabled)
