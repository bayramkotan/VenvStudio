"""VenvStudio - MainWindow: Menu Bar Mixin
Menu bar setup, desktop shortcut creation (Win/Linux/macOS), recent-envs
menu (moved from main_window.py).
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMenu, QMessageBox, QProgressDialog, QApplication,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from src.utils.i18n import tr
# N11: shared with N9's pre-flight (package_ops.py) so Install
# Launcher consults the SAME compatibility data instead of only its
# own env_types/min_python fields -- Bayram (2026-08-13) wants every
# install path to go through the same conflict-check source.
from src.gui.package_ops import _check_pypi_wheel_availability


import os as _os_pm      # N55: used by the Recent Projects menu


class WindowMenuMixin:
    """Mixin for MainWindow: menu bar, desktop shortcuts, recent-envs menu."""

    def _setup_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu(tr("file"))
        new_env_action = QAction(f"➕ &{tr('new_environment')}", self)
        new_env_action.setShortcut("Ctrl+N")
        new_env_action.triggered.connect(self._create_env)
        file_menu.addAction(new_env_action)

        # N55/B26: File -> New Project... -- create a project skeleton with
        # uv, poetry, hatch, pdm or pixi.
        #
        # It sits directly under New Environment because the two answer
        # neighbouring questions, and above the separator for the same reason:
        # both are things you make, where the entries below act on things that
        # already exist. Environment first, since that is what most sessions
        # start with.
        new_proj_action = QAction("\U0001f4c1 New &Project…", self)
        new_proj_action.setShortcut("Ctrl+Shift+N")
        new_proj_action.setStatusTip(
            "Create a project with uv, poetry, hatch, pdm or pixi")
        new_proj_action.triggered.connect(self._new_project)
        file_menu.addAction(new_proj_action)

        file_menu.addSeparator()
        # N11: File -> Install Launcher... -- pick an app, get a
        # recommended env type/Python version, install into a matching
        # existing env or create a new one. Scoped to pip-installable
        # apps for now (system_app / conda-only tools like RStudio/
        # Ollama/DBeaver use a different install path -- system package
        # manager, not pip/venv -- and need separate handling later).
        install_launcher_action = QAction("🚀 Install Launcher…", self)
        install_launcher_action.triggered.connect(self._show_install_launcher)
        file_menu.addAction(install_launcher_action)
        file_menu.addSeparator()

        # ── Recent Environments submenu ───────────────────────────────────
        self._recent_menu = QMenu("\U0001f550 Recent Environments", self)
        file_menu.addMenu(self._recent_menu)
        self._populate_recent_menu()

        # N55: the same idea for projects. Sits directly under its environment
        # counterpart because the two are the same gesture -- "take me back to
        # the thing I was working on".
        self._recent_proj_menu = QMenu("\U0001f4c1 Recent Projects", self)
        file_menu.addMenu(self._recent_proj_menu)
        self._populate_recent_projects_menu()
        file_menu.addSeparator()
        # ─────────────────────────────────────────────────────────────────

        quit_action = QAction(f"❌ {tr('quit')}", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu(tr("view"))
        refresh_action = QAction(f"🔄 {tr('refresh')}", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_env_list)
        view_menu.addAction(refresh_action)
        view_menu.addSeparator()
        dark_action = QAction(f"🌙 {tr('dark_theme')}", self)
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        view_menu.addAction(dark_action)
        light_action = QAction(f"☀️ {tr('light_theme')}", self)
        light_action.triggered.connect(lambda: self._set_theme("light"))
        view_menu.addAction(light_action)
        view_menu.addSeparator()
        settings_view_action = QAction(f"⚙️ {tr('settings')}", self)
        settings_view_action.triggered.connect(self._open_settings)
        view_menu.addAction(settings_view_action)

        tools_menu = menubar.addMenu("Tools")
        shortcut_action = QAction("🖥️ Create Desktop Shortcut", self)
        shortcut_action.triggered.connect(self._create_desktop_shortcut)
        tools_menu.addAction(shortcut_action)

        tools_menu.addSeparator()
        conflict_action = QAction("🧩 Conflict Manager", self)
        conflict_action.setToolTip(
            "Check package compatibility with the current environment.\n"
            "Search any package to see known Python version and env-type restrictions."
        )
        conflict_action.triggered.connect(self._show_conflict_manager)
        tools_menu.addAction(conflict_action)

        # B30: the Code Map. Reads a tree with ast and shows what is
        # where, what calls what, and -- the part that pays for it --
        # names defined twice, class methods hiding a mixin's, and
        # constants held under two names. Every one of those is a bug
        # this codebase has actually shipped.
        code_map_action = QAction("🗺️ Code Map", self)
        code_map_action.setToolTip(
            "What is in a codebase and what talks to what.\n"
            "Reads VenvStudio's own source or any project folder.")
        code_map_action.triggered.connect(self._show_code_map)
        tools_menu.addAction(code_map_action)

        tools_menu.addSeparator()
        commands_action = QAction("💻 View Commands", self)
        commands_action.setToolTip(
            "Every terminal command VenvStudio ran this session, "
            "one per row, ready to copy")
        commands_action.triggered.connect(self._show_command_history)
        tools_menu.addAction(commands_action)

        logs_action = QAction("🪵 View Logs", self)
        logs_action.triggered.connect(self._show_log_viewer)
        tools_menu.addAction(logs_action)

        # N42 (Bayram, 2026-08-15/16): a discoverable way to see PAST
        # crash logs (already written on every crash since v1.4.62, but
        # previously only reachable by manually browsing the logs
        # folder). Opens the same Log Viewer, pre-selected to the most
        # recent crash log via the new file-selector dropdown.
        crash_reports_action = QAction("💥 Crash Reports", self)
        crash_reports_action.setToolTip(
            "Browse past crash logs (if any) in the same Log Viewer.")
        crash_reports_action.triggered.connect(self._show_crash_reports)
        tools_menu.addAction(crash_reports_action)

        logs_folder_action = QAction("📁 Open Logs Folder", self)
        logs_folder_action.triggered.connect(self._open_logs_folder)
        tools_menu.addAction(logs_folder_action)

        help_menu = menubar.addMenu(tr("help"))
        about_action = QAction(f"ℹ️ {tr('about')}", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        update_action = QAction("🔄 Check for Updates", self)
        update_action.triggered.connect(self._check_for_updates)
        help_menu.addAction(update_action)

        help_menu.addSeparator()

        github_action = QAction("⭐ GitHub Repository", self)
        github_action.triggered.connect(lambda: __import__("src.utils.platform_utils", fromlist=["open_url"]).open_url("https://github.com/bayramkotan/VenvStudio"))
        help_menu.addAction(github_action)

        pypi_action = QAction("📦 PyPI Page", self)
        pypi_action.triggered.connect(lambda: __import__("src.utils.platform_utils", fromlist=["open_url"]).open_url("https://pypi.org/project/venvstudio/"))
        help_menu.addAction(pypi_action)

        issues_action = QAction("🐛 Report a Bug", self)
        issues_action.triggered.connect(lambda: __import__("src.utils.platform_utils", fromlist=["open_url"]).open_url("https://github.com/bayramkotan/VenvStudio/issues"))
        help_menu.addAction(issues_action)



    def _new_project(self):
        """File -> New Project... (N55/B26).

        VenvStudio has always made environments; poetry, hatch, pdm, pixi and uv
        want a PROJECT, and derive the environment from it. Creating one used to
        mean leaving for a terminal and coming back.

        The dialog offers to open the finished project in a terminal, which is
        usually the next thing anyone does -- `uv sync`, `poetry install`, and
        so on. Declining leaves the project sitting on disk, ready.
        """
        from src.gui.project_dialog import NewProjectDialog

        dlg = NewProjectDialog(self._c, config=self.config, parent=self)
        # QDialog.Accepted is a class constant in PySide6, not an instance
        # attribute -- dlg.Accepted raises AttributeError.
        from PySide6.QtWidgets import QDialog as _QDialog
        if dlg.exec() != _QDialog.Accepted or not dlg.created_path:
            return

        _path = dlg.created_path

        # The new project is on the Recent Projects menu from here on.
        try:
            self._populate_recent_projects_menu()
        except Exception:
            pass

        _box = QMessageBox(self)
        _box.setIcon(QMessageBox.Information)
        _box.setWindowTitle("Project created")
        _box.setText(f"\u2705  {_os_pm.path.basename(_path)} is ready.")
        _box.setInformativeText(
            f"{_path}\n\n"
            f"It is on the File \u2192 Recent Projects menu now.\n"
            f"Open a terminal there to install its dependencies?")
        _box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        _box.setDefaultButton(QMessageBox.Yes)
        _ask = _box.exec()
        if _ask == QMessageBox.Yes:
            try:
                from src.utils.platform_utils import open_terminal_at
                if not open_terminal_at(_path):
                    QMessageBox.warning(
                        self, "Terminal",
                        "The project was created, but a terminal could not be "
                        "opened there. Settings has a default-terminal option.")
            except Exception as e:
                QMessageBox.warning(self, "Terminal", f"{type(e).__name__}: {e}")

    def _show_command_history(self):
        """Open the command history window.

        Companion to the log viewer: the log has everything, this has only
        the commands, which is what you want when the question is "what did
        VenvStudio actually run?"
        """
        from src.gui.command_history import CommandHistoryDialog
        dlg = CommandHistoryDialog(self)
        dlg.exec()

    def _show_log_viewer(self):
        """Open the log viewer dialog (frozen builds have no terminal)."""
        from src.gui.log_viewer import LogViewerDialog
        dlg = LogViewerDialog(self)
        dlg.exec()

    def _show_crash_reports(self):
        """N42: open the Log Viewer pre-selected to the most recent
        crash_*.log, or tell the user there are none instead of just
        opening on the regular venvstudio.log looking like nothing
        happened."""
        from src.utils.logger import get_log_dir
        from PySide6.QtWidgets import QMessageBox
        try:
            crash_logs = sorted(
                get_log_dir().glob("crash_*.log"),
                key=lambda p: p.stat().st_mtime, reverse=True,
            )
        except Exception:
            crash_logs = []
        if not crash_logs:
            QMessageBox.information(
                self, "Crash Reports",
                "No crash reports found — VenvStudio has not crashed "
                "(or none have been logged) this install.")
            return
        from src.gui.log_viewer import LogViewerDialog
        dlg = LogViewerDialog(self, initial_file=crash_logs[0].name)
        dlg.exec()

    def _open_logs_folder(self):
        """Open the logs directory in the system file manager."""
        from src.utils.logger import get_log_dir
        from src.utils.platform_utils import open_folder
        ok, msg = open_folder(get_log_dir())
        if not ok:
            QMessageBox.warning(self, "Open Logs Folder", msg or "Could not open folder.")

    def _create_desktop_shortcut(self):
        """Create a desktop shortcut that runs 'venvstudio' command (pip-installed).
        If venvstudio is not found in PATH, installs it first via pip.
        No terminal window opens when the shortcut is launched.
        """
        import sys, os, shutil, platform, subprocess
        from PySide6.QtWidgets import QMessageBox, QProgressDialog
        from PySide6.QtCore import Qt

        system = platform.system()
        app_name = "VenvStudio"

        # ── Step 1: Find venvstudio executable ──────────────────────────────
        vs_exe = shutil.which("venvstudio")

        if not vs_exe:
            # Not in PATH — offer to install
            reply = QMessageBox.question(
                self, "VenvStudio Not Found",
                "⚠️  The 'venvstudio' command was not found in PATH.\n\n"
                "This usually means VenvStudio was not installed via pip.\n\n"
                "Install now with pip? (requires internet connection)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # Show progress
            prog = QProgressDialog("Installing VenvStudio via pip...", None, 0, 0, self)
            prog.setWindowTitle("Installing...")
            prog.setWindowModality(Qt.WindowModal)
            prog.show()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade",
                     "venvstudio", "--break-system-packages"],
                    capture_output=True, text=True, timeout=120
                )
                prog.close()
                if result.returncode != 0:
                    # Try without --break-system-packages
                    result2 = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "--upgrade", "venvstudio"],
                        capture_output=True, text=True, timeout=120
                    )
                    if result2.returncode != 0:
                        QMessageBox.critical(self, "Install Failed",
                            f"pip install failed:\n{result2.stderr[:500]}")
                        return
            except Exception as e:
                prog.close()
                QMessageBox.critical(self, "Error", str(e))
                return

            # Re-check
            vs_exe = shutil.which("venvstudio")
            if not vs_exe:
                # Try Scripts / bin path
                scripts_dir = os.path.join(os.path.dirname(sys.executable),
                                           "Scripts" if system == "Windows" else "bin")
                candidate = os.path.join(scripts_dir,
                                         "venvstudio.exe" if system == "Windows" else "venvstudio")
                if os.path.isfile(candidate):
                    vs_exe = candidate
                else:
                    QMessageBox.warning(self, "Not Found",
                        "Installed but 'venvstudio' still not found.\n"
                        f"Scripts dir: {scripts_dir}\n"
                        "Try adding it to PATH and running this again.")
                    return

        # ── Step 2: Create shortcut using vs_exe ────────────────────────────
        try:
            if system == "Windows":
                self._create_shortcut_windows(vs_exe, app_name)
            elif system == "Linux":
                self._create_shortcut_linux(vs_exe, app_name)
            elif system == "Darwin":
                self._create_shortcut_macos(vs_exe, app_name)
            else:
                QMessageBox.warning(self, "Unsupported",
                    f"Desktop shortcut not supported on {system}.")
                return

            QMessageBox.information(self, "Done",
                f"✅ Desktop shortcut created!\n\n"
                f"Command: {vs_exe}\n\n"
                "You can now launch VenvStudio from your desktop\n"
                "without opening a terminal.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create shortcut:\n{e}")

    def _create_shortcut_windows(self, vs_exe, app_name):
        """Create a .lnk on Windows Desktop using PowerShell."""
        import os, subprocess

        desktop = os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop"
        )
        lnk_path = os.path.join(desktop, f"{app_name}.lnk")
        scripts_dir = os.path.dirname(vs_exe)

        icon_candidate = os.path.join(scripts_dir, "venvstudio.ico")
        icon_line = f'$s.IconLocation = "{icon_candidate}";' if os.path.isfile(icon_candidate) else ""

        ps = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s  = $ws.CreateShortcut("{lnk_path}"); '
            f'$s.TargetPath     = "{vs_exe}"; '
            f'$s.WorkingDirectory = "{scripts_dir}"; '
            f'$s.Description    = "VenvStudio — Python Virtual Environment Manager"; '
            f'{icon_line} '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, timeout=15, capture_output=True)


    def _create_shortcut_linux(self, vs_exe, app_name):
        """Create a .desktop file on Linux — Terminal=false."""
        import os, subprocess

        # Find icon
        icon_path = vs_exe  # fallback
        for candidate in [
            os.path.join(os.path.dirname(vs_exe), "..", "share", "pixmaps", "venvstudio.png"),
            os.path.expanduser("~/.local/share/icons/venvstudio.png"),
        ]:
            if os.path.isfile(candidate):
                icon_path = os.path.abspath(candidate)
                break

        content = (
            "[Desktop Entry]\n"
            "Version=1.0\n"
            f"Name={app_name}\n"
            "Comment=Python Virtual Environment Manager\n"
            f"Exec={vs_exe}\n"
            f"Icon={icon_path}\n"
            "Terminal=false\n"
            "Type=Application\n"
            "Categories=Development;\n"
            "StartupNotify=true\n"
        )

        # XDG applications dir
        apps_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(apps_dir, exist_ok=True)
        xdg_path = os.path.join(apps_dir, "venvstudio.desktop")
        with open(xdg_path, "w") as f:
            f.write(content)
        os.chmod(xdg_path, 0o755)

        # Desktop dir — try xdg-user-dir first, then fallbacks
        desktop_dir = None
        try:
            desktop_dir = subprocess.check_output(
                ["xdg-user-dir", "DESKTOP"], text=True, timeout=5
            ).strip()
        except Exception:
            pass
        if not desktop_dir or not os.path.isdir(desktop_dir):
            for d in [os.path.expanduser("~/Desktop"),
                      os.path.expanduser("~/Masaüstü")]:
                if os.path.isdir(d):
                    desktop_dir = d
                    break

        if desktop_dir and os.path.isdir(desktop_dir):
            dest = os.path.join(desktop_dir, "venvstudio.desktop")
            with open(dest, "w") as f:
                f.write(content)
            os.chmod(dest, 0o755)
            try:
                subprocess.run(["gio", "set", dest, "metadata::trusted", "true"],
                               timeout=5, capture_output=True)
            except Exception:
                pass

    def _create_shortcut_macos(self, vs_exe, app_name):
        """Create a .command launcher on macOS Desktop."""
        import os, stat
        script = os.path.expanduser(f"~/Desktop/{app_name}.command")
        with open(script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'"{vs_exe}"\n')
        os.chmod(script, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

    def _show_code_map(self):
        """Open the Code Map dialog (B30)."""
        try:
            from src.gui.code_map_dialog import CodeMapDialog
            # Offer the user's own projects as targets too: the same engine
            # answers "what is in this project" for their code, not only ours.
            _projects = []
            try:
                for _e in (self.config.get("recent_projects", []) or []):
                    _p = _e.get("path") if isinstance(_e, dict) else _e
                    if _p:
                        _projects.append(_p)
            except Exception:
                pass
            # Shown non-modally: a scan takes seconds and there is no reason
            # to freeze the rest of the application while reading a tree.
            # Kept on self so Python does not collect it the moment show()
            # returns -- unlike exec(), show() comes straight back.
            self._code_map_dlg = CodeMapDialog(parent=self,
                                               project_paths=_projects)
            self._code_map_dlg.show()
            self._code_map_dlg.raise_()
            self._code_map_dlg.activateWindow()
        except Exception as e:
            QMessageBox.warning(self, "Code Map",
                                f"Could not open the Code Map:\n{e}")

    def _show_conflict_manager(self):
        """Open the Conflict Manager dialog."""
        try:
            from src.gui.conflict_manager import ConflictManagerDialog
            _env_type = "venv"
            _py_ver   = None
            _installed = []
            _pip_mgr  = None
            if hasattr(self, "package_panel") and self.package_panel:
                _env_type = getattr(self.package_panel, "_current_env_type", "venv") or "venv"
                _pip_mgr  = getattr(self.package_panel, "pip_manager", None)
                _vkey = str(getattr(_pip_mgr, "venv_path", "") or "")
                _py_ver = getattr(self.package_panel,
                                  "_launcher_py_version_cache", {}).get(_vkey)
                # installed package names from cache
                _installed = list(getattr(self.package_panel,
                                          "installed_package_names", set()))
            dlg = ConflictManagerDialog(
                parent=self,
                env_type=_env_type,
                py_version=_py_ver,
                installed_packages=_installed,
                pip_manager=_pip_mgr,
            )
            # .exec() keeps MainWindow modally blocked even while the
            # dialog is minimized -- minimize only affects the window's
            # visual state, not Qt's modal event loop, so Bayram
            # (2026-08-13) could not get back to VenvStudio after
            # minimizing Conflict Manager. .show() makes it non-modal --
            # matches the intent of adding minimize/maximize in the
            # first place (an independent window, not a blocking
            # popup). Keep a reference on self so Python doesn't
            # garbage-collect it the moment this method returns (exec()
            # didn't need this since it blocked until closed; show()
            # returns immediately).
            self._conflict_mgr_dlg = dlg
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()
        except Exception as _e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Could not open Conflict Manager:\n{_e}")


    def _install_launcher_env_status(self, app_def):
        """N11: for a pip-based app_def, find every compatible existing env
        across ALL of app_def["env_types"] (not just the first one --
        Bayram, 2026-08-13: "neden sadece venv'i oneriyor? neden uv,
        hatch... bunlari oner miyor?" -- venv/uv/hatch/pdm/poetry all
        ultimately install via pip, so an app good for one is good for
        all of them; only conda/pixi/pipx genuinely differ) and, if set,
        min/max_python. Returns (list[VenvInfo], recommended_types,
        min_py, max_py, note) -- matches may span several env types at
        once, list may be empty/one/several (Bayram: "birden fazla varsa
        dropdown yap" -- let the user pick, don't silently take the first).

        Compatibility source priority -- SAME order as N9's pre-flight
        check in package_ops.py (Bayram, 2026-08-13: every install path
        should go through the same conflict-check source):
          1. CONFLICT_RULES (constants.py) -- the shared, maintained list.
             If it has an entry for this app's package, ITS min/max_python
             wins over whatever launcher_ui.py has for this app -- one
             source of truth instead of two that could quietly disagree.
          2. launcher_ui.py's own min_python/max_python (already researched
             from PyPI's requires_python per app, see v1.6.44 session notes)
             -- used when CONFLICT_RULES has nothing for this package.
          3. Live PyPI wheel check (_check_pypi_wheel_availability, the
             same function N9 falls back to) -- only when NEITHER of the
             above has any data at all, i.e. a package nobody has entered
             constraints for anywhere yet.
        """
        rec_types = app_def.get("env_types") or ["venv"]
        min_py = app_def.get("min_python")
        max_py = app_def.get("max_python")
        note = None

        pkg_name = app_def.get("package", "")
        if pkg_name and pkg_name != "__system__":
            try:
                from src.utils.constants import CONFLICT_RULES, CONFLICT_RULES_ALIASES
                _pkg_key = pkg_name.lower().replace("_", "-")
                _rule_key = CONFLICT_RULES_ALIASES.get(pkg_name, CONFLICT_RULES_ALIASES.get(_pkg_key, _pkg_key))
                _rule = CONFLICT_RULES.get(_rule_key)
                if _rule:
                    if _rule.get("min_python"):
                        min_py = _rule["min_python"]
                    if _rule.get("max_python"):
                        max_py = _rule["max_python"]
                    note = _rule.get("note")
            except Exception:
                pass

            # Nothing in CONFLICT_RULES AND nothing in launcher_ui.py's own
            # data either -- last resort, ask PyPI directly (same function,
            # same platform-tag mapping N9 uses).
            if not min_py and not max_py and not note:
                try:
                    import sys as _sys_il
                    _plat = {"win32": "win", "linux": "linux", "darwin": "macos"}.get(_sys_il.platform, "")
                    if _plat:
                        _cur = sys.version_info
                        _live = _check_pypi_wheel_availability(pkg_name, _cur.major, _cur.minor, _plat)
                        if _live.get("checked") and _live.get("available_pyvers"):
                            _avail = _live["available_pyvers"]
                            min_py, max_py = _avail[0], _avail[-1]
                except Exception:
                    pass

        def _in_range(py_ver_str):
            try:
                parts = py_ver_str.split(".")
                major, minor = int(parts[0]), int(parts[1])
            except Exception:
                return True  # unknown version string -- don't block on it
            if min_py:
                mn = tuple(int(x) for x in min_py.split("."))
                if (major, minor) < mn:
                    return False
            if max_py:
                mx = tuple(int(x) for x in max_py.split("."))
                if (major, minor) > mx:
                    return False
            return True

        try:
            envs = self.venv_manager.list_venvs_fast()
        except Exception:
            envs = []
        matches = [info for info in envs
                   if info.env_type in rec_types and _in_range(info.python_version)]
        return matches, rec_types, min_py, max_py, note

    def _show_install_launcher(self):
        """N11: File -> Install Launcher... -- pick an app, get a
        recommended env type/Python version, install into a matching
        existing env or create a new one."""
        apps = getattr(self.package_panel, "app_definitions", []) if hasattr(self, "package_panel") else []
        # Scoped to pip-installable apps for now -- system_app entries
        # (RStudio, Ollama, DBeaver, R Console, jamovi, JASP) install via
        # a system package manager, not pip/venv, and need a separate flow.
        apps = [a for a in apps if not a.get("system_app")]
        if not apps:
            QMessageBox.information(self, "Install Launcher", "No installable apps found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Install Launcher")
        dlg.setMinimumWidth(420)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("Choose an app to install:"))
        combo = QComboBox()
        for a in apps:
            combo.addItem(f"{a.get('icon', '')} {a['name']}", a)
        layout.addWidget(combo)

        status_label = QLabel()
        status_label.setWordWrap(True)
        layout.addWidget(status_label)

        # Shown only when there's more than one compatible existing env --
        # Bayram: "recommended kisminda birden fazla varsa onlari da
        # dropdown yap" (2026-08-13). One match: install button already
        # names it, no extra picker needed. Zero matches: hidden, nothing
        # to pick from.
        env_pick_label = QLabel("Install into:")
        env_pick_combo = QComboBox()
        layout.addWidget(env_pick_label)
        layout.addWidget(env_pick_combo)
        env_pick_label.setVisible(False)
        env_pick_combo.setVisible(False)

        btn_row = QHBoxLayout()
        install_btn = QPushButton("Install")
        create_btn = QPushButton("Create New Environment…")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(install_btn)
        btn_row.addWidget(create_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        state = {"matches": [], "app": None}

        def _refresh():
            app_def = combo.currentData()
            state["app"] = app_def
            matches, rec_types, min_py, max_py, note = self._install_launcher_env_status(app_def)
            state["matches"] = matches
            rec_txt = ", ".join(rec_types)
            py_txt = ""
            if min_py or max_py:
                py_txt = f" • Python {min_py or '?'}–{max_py or 'latest'}"
            # note comes from CONFLICT_RULES when that shared list has an
            # entry for this app's package (e.g. a distutils/build-from-
            # source warning like pygame's) -- surface it, it's exactly
            # the kind of thing the central conflict list exists to say.
            note_txt = f"\nℹ️ {note}" if note else ""

            env_pick_combo.clear()
            if len(matches) > 1:
                # Matches can now span several env types at once (venv AND
                # uv AND hatch...) -- show which type each one is, not just
                # its name, so the choice is meaningful.
                for info in matches:
                    env_pick_combo.addItem(f"{info.name} ({info.env_type}, Python {info.python_version})", info)
                env_pick_label.setVisible(True)
                env_pick_combo.setVisible(True)
                status_label.setText(
                    f"Compatible with: {rec_txt}{py_txt}{note_txt}\n"
                    f"✅ Found {len(matches)} compatible environments — pick one below."
                )
                install_btn.setEnabled(True)
                install_btn.setText("Install")
            elif len(matches) == 1:
                env_pick_label.setVisible(False)
                env_pick_combo.setVisible(False)
                status_label.setText(
                    f"Compatible with: {rec_txt}{py_txt}{note_txt}\n"
                    f"✅ Found compatible environment: {matches[0].name} ({matches[0].env_type}, Python {matches[0].python_version})"
                )
                install_btn.setEnabled(True)
                install_btn.setText(f"Install into '{matches[0].name}'")
            else:
                env_pick_label.setVisible(False)
                env_pick_combo.setVisible(False)
                status_label.setText(
                    f"Compatible with: {rec_txt}{py_txt}{note_txt}\n"
                    f"⚠️ No compatible existing environment found."
                )
                install_btn.setEnabled(False)
                install_btn.setText("Install")

        combo.currentIndexChanged.connect(_refresh)
        _refresh()

        def _do_install():
            app_def = state["app"]
            matches = state["matches"]
            if not matches or not app_def:
                return
            # One match -> that one. Several -> whichever the dropdown has
            # selected (defaults to the first, same as before this change
            # if the user never touches it).
            target_info = env_pick_combo.currentData() if len(matches) > 1 else matches[0]
            if target_info is None:
                return
            packages = app_def.get("install_packages", [app_def.get("package")])
            target = target_info.name
            for row in range(self.env_table.rowCount()):
                _ni = self.env_table.item(row, 0)
                if _ni and _ni.text().strip() == target:
                    self.env_table.selectRow(row)
                    self._on_env_selected()
                    break
            self._switch_page(0)
            if hasattr(self, "package_panel"):
                QTimer.singleShot(400, lambda: self.package_panel._install_packages(packages, hint_name=app_def["name"]) if self.package_panel else None)
            dlg.accept()

        def _do_create():
            dlg.accept()
            self._create_env()

        install_btn.clicked.connect(_do_install)
        create_btn.clicked.connect(_do_create)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _populate_recent_menu(self):
        """Rebuild the Recent Environments submenu from recent_envs.json."""
        self._recent_menu.clear()
        try:
            from src.core.recent_envs import RecentEnvsManager
            mgr = RecentEnvsManager()
            entries = mgr.load()
        except Exception:
            entries = []

        if not entries:
            empty_action = QAction("  (No recent environments)", self)
            empty_action.setEnabled(False)
            self._recent_menu.addAction(empty_action)
            return

        # TYPE icons
        _icons = {
            "venv": "🐍", "uv": "⚡", "poetry": "📜",
            "pipx": "📦", "conda": "🦎",
        }
        for entry in entries:
            name       = entry.get("name", "?")
            path       = entry.get("path", "")
            env_type   = entry.get("type", "venv")
            last_opened = entry.get("last_opened", "")[:16].replace("T", "  ")
            icon       = _icons.get(env_type, "🐍")
            label      = f"{icon} {name}   —   {last_opened}"
            action = QAction(label, self)
            action.setToolTip(path)
            action.triggered.connect(
                lambda checked=False, p=path, n=name: self._open_recent_env(n, p)
            )
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()
        clear_action = QAction("🗑️ Clear Recent List", self)
        clear_action.triggered.connect(self._clear_recent_envs)
        self._recent_menu.addAction(clear_action)

    def _populate_recent_projects_menu(self):
        """Rebuild the Recent Projects submenu from the config.

        Projects are recorded by the New Project dialog rather than by a
        manager class: unlike environments, VenvStudio does not own them after
        creation -- the tool does -- so there is nothing to keep in sync beyond
        the path.
        """
        self._recent_proj_menu.clear()
        try:
            entries = self.config.get("recent_projects", []) or []
        except Exception:
            entries = []

        _live = [e for e in entries
                 if isinstance(e, dict) and _os_pm.path.isdir(e.get("path", ""))]

        if not _live:
            empty_action = QAction("  (No recent projects)", self)
            empty_action.setEnabled(False)
            self._recent_proj_menu.addAction(empty_action)
            return

        _icons = {"uv": "\u26a1", "poetry": "\U0001f4dc", "hatch": "\U0001f423",
                  "pdm": "\U0001f4e6", "pixi": "\U0001f9ea"}
        for entry in _live:
            name = entry.get("name", "?")
            path = entry.get("path", "")
            tool = entry.get("tool", "")
            when = entry.get("created", "")
            icon = _icons.get(tool, "\U0001f4c1")
            label = f"{icon} {name}   \u2014   {when}"

            # A submenu rather than a single action: opening a terminal is the
            # likelier next step, but not the only one -- sometimes you just
            # want to see the files. Guessing which would be wrong half the
            # time, and the guess is cheap to avoid.
            _sub = QMenu(label, self)
            _sub.setToolTipsVisible(True)

            _act_term = QAction("\U0001f4bb  Open Terminal", self)
            _act_term.setToolTip(path)
            _act_term.triggered.connect(
                lambda checked=False, p=path: self._open_recent_project(p))
            _sub.addAction(_act_term)

            _act_dir = QAction("\U0001f4c2  Open Folder", self)
            _act_dir.setToolTip(path)
            _act_dir.triggered.connect(
                lambda checked=False, p=path: self._open_project_folder(p))
            _sub.addAction(_act_dir)

            _sub.addSeparator()
            _act_path = QAction(f"   {path}", self)
            _act_path.setEnabled(False)
            _sub.addAction(_act_path)

            self._recent_proj_menu.addMenu(_sub)

        self._recent_proj_menu.addSeparator()
        clear_action = QAction("\U0001f5d1\ufe0f Clear Recent List", self)
        clear_action.triggered.connect(self._clear_recent_projects)
        self._recent_proj_menu.addAction(clear_action)

    def _open_recent_project(self, path: str):
        """Open a terminal in the project.

        A project is not something VenvStudio displays -- it is a folder its
        tool works in -- so the useful thing to do with one is to be there.
        """
        if not _os_pm.path.isdir(path):
            QMessageBox.warning(
                self, "Not there any more",
                f"This project folder no longer exists:\n{path}")
            self._populate_recent_projects_menu()
            return
        try:
            from src.utils.platform_utils import open_terminal_at
            if not open_terminal_at(path):
                QMessageBox.warning(
                    self, "Terminal",
                    f"A terminal could not be opened at:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Terminal", f"{type(e).__name__}: {e}")

    def _open_project_folder(self, path: str):
        """Show the project in the system file manager."""
        if not _os_pm.path.isdir(path):
            QMessageBox.warning(
                self, "Not there any more",
                f"This project folder no longer exists:\n{path}")
            self._populate_recent_projects_menu()
            return
        try:
            from src.utils.platform_utils import open_folder
            ok, msg = open_folder(path)
            if not ok:
                QMessageBox.warning(self, "Open Folder", msg)
        except Exception as e:
            QMessageBox.warning(self, "Open Folder", f"{type(e).__name__}: {e}")

    def _clear_recent_projects(self):
        try:
            self.config.set("recent_projects", [])
            self.config.save()
        except Exception:
            pass
        self._populate_recent_projects_menu()

    def _open_recent_env(self, name: str, path: str):
        """Select env in table by path; show Packages panel."""
        from pathlib import Path as _Path
        # Find row in env table matching this path. My first attempt
        # read Qt.UserRole off column 0 -- but env_list.py never
        # actually WRITES a path there (that UserRole slot holds the
        # env_type string on column 1 instead). The real full path
        # lives as a TOOLTIP on the Path column (column 2) --
        # confirmed via _get_env_path()'s existing, working reads of
        # `self.env_table.item(row, 2).toolTip()`. Comparison still
        # uses Path.resolve() (not raw normcase) for robustness
        # against textual formatting differences.
        def _norm(p):
            try:
                return str(_Path(str(p)).resolve()).casefold()
            except Exception:
                return str(p).casefold()
        _target = _norm(path)
        if not hasattr(self, "env_table"):
            return
        for row in range(self.env_table.rowCount()):
            path_item = self.env_table.item(row, 2)
            item_path = path_item.toolTip() if path_item else None
            if item_path and _norm(item_path) == _target:
                self.env_table.selectRow(row)
                # _on_env_selected takes no arguments -- it reads the
                # current selection from self.env_table itself. This
                # line was passing `row` (pre-existing bug, never hit
                # before because the loop above never found a match
                # until this fix -- see the tooltip/UserRole fix
                # above) -- Bayram (2026-08-14) hit it via a real
                # TypeError as soon as the match-finding started
                # working.
                self._on_env_selected()
                # Bayram (2026-08-14): "neden explorer'da yerine
                # goturmuyor" -- selecting the row in VenvStudio's
                # own table wasn't the whole expectation; also open
                # the folder in the system file manager, reusing the
                # exact same mechanism as the "📁 Open Folder" context-
                # menu action. Relies on the selectRow() above already
                # having set the table selection _open_env_folder reads.
                if hasattr(self, "_open_env_folder"):
                    self._open_env_folder()
                # Update recency
                try:
                    from src.core.recent_envs import RecentEnvsManager
                    RecentEnvsManager().touch(name, path)
                    self._populate_recent_menu()
                except Exception:
                    pass
                return
        # Env not found in table (deleted) — remove from recent list
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().remove(path)
            self._populate_recent_menu()
        except Exception:
            pass
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Not Found",
            f"Environment '{name}' could not be found.\n"
            f"It may have been deleted or moved.\n\n{path}"
        )

    def _clear_recent_envs(self):
        """Clear the recent environments list."""
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().clear()
            self._populate_recent_menu()
        except Exception:
            pass

    def _track_recent(self, name: str, path: str, env_type: str):
        """Write recent env entry and refresh menu (called deferred)."""
        try:
            from src.core.recent_envs import RecentEnvsManager
            RecentEnvsManager().touch(name, path, env_type=env_type)
            if hasattr(self, "_recent_menu"):
                self._populate_recent_menu()
        except Exception:
            pass

