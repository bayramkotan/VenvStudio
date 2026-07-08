"""VenvStudio - MainWindow: Menu Bar Mixin
Menu bar setup, desktop shortcut creation (Win/Linux/macOS), recent-envs
menu (moved from main_window.py).
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QMenu, QMessageBox, QProgressDialog, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from src.utils.i18n import tr


class WindowMenuMixin:
    """Mixin for MainWindow: menu bar, desktop shortcuts, recent-envs menu."""

    def _setup_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu(tr("file"))
        new_env_action = QAction(f"➕ &{tr('new_environment')}", self)
        new_env_action.setShortcut("Ctrl+N")
        new_env_action.triggered.connect(self._create_env)
        file_menu.addAction(new_env_action)
        file_menu.addSeparator()

        # ── Recent Environments submenu ───────────────────────────────────
        self._recent_menu = QMenu("🕐 Recent Environments", self)
        file_menu.addMenu(self._recent_menu)
        self._populate_recent_menu()
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
        logs_action = QAction("🪵 View Logs", self)
        logs_action.triggered.connect(self._show_log_viewer)
        tools_menu.addAction(logs_action)

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
        github_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/bayramkotan/VenvStudio"))
        help_menu.addAction(github_action)

        pypi_action = QAction("📦 PyPI Page", self)
        pypi_action.triggered.connect(lambda: __import__("webbrowser").open("https://pypi.org/project/venvstudio/"))
        help_menu.addAction(pypi_action)

        issues_action = QAction("🐛 Report a Bug", self)
        issues_action.triggered.connect(lambda: __import__("webbrowser").open("https://github.com/bayramkotan/VenvStudio/issues"))
        help_menu.addAction(issues_action)



    def _show_log_viewer(self):
        """Open the log viewer dialog (frozen builds have no terminal)."""
        from src.gui.log_viewer import LogViewerDialog
        dlg = LogViewerDialog(self)
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

    def _open_recent_env(self, name: str, path: str):
        """Select env in table by path; show Packages panel."""
        import os
        # Find row in env table matching this path
        model = self.env_table.model() if hasattr(self, "env_table") else None
        if model is None:
            return
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            item_path = model.data(idx, Qt.UserRole)  # env path stored as UserRole
            if item_path and os.path.normcase(str(item_path)) == os.path.normcase(path):
                self.env_table.selectRow(row)
                self._on_env_selected(row)
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

