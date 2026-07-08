"""VenvStudio - Package Panel: Launcher Shortcuts Mixin
Desktop shortcut creation for launcher apps (Win/Linux/macOS)
(moved from package_panel.py).
"""
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args


class LauncherShortcutsMixin:
    """Mixin for PackagePanel: desktop shortcut creation for launcher apps."""

    def _create_desktop_shortcut(self, app_def: dict):
        """Create a desktop shortcut for the app — .lnk (Windows), .desktop (Linux), .command (macOS)."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)
        app_name = app_def["name"]
        env_name = venv_path.name
        shortcut_name = f"{app_name} ({env_name})"
        icon_path = self._get_app_icon_path(app_def)
        needs_console = app_def.get("needs_console", False)

        platform = get_platform()
        desktop = Path.home() / "Desktop"

        try:
            if platform == "windows":
                self._create_windows_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, needs_console, venv_path
                )
            elif platform == "linux":
                self._create_linux_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, venv_path
                )
            elif platform == "macos":
                self._create_macos_shortcut(
                    desktop, shortcut_name, python_exe,
                    app_def["command"], icon_path, venv_path
                )

            # Show success
            QMessageBox.information(
                self, tr("success"),
                tr("shortcut_created").format(app=app_name) + f"\n\n📁 Desktop / {shortcut_name}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                f"Failed to create shortcut:\n{e}"
            )

    def _create_windows_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, needs_console, venv_path):
        """Create Windows .lnk shortcut via PowerShell (no COM dependency)."""
        args_str = " ".join(cmd_args)
        lnk_path = desktop / f"{name}.lnk"

        # Use PowerShell to create .lnk — works without pywin32
        # WindowStyle: 1=Normal, 7=Minimized; for GUI apps we hide console
        window_style = 1 if needs_console else 7
        icon_line = f'$s.IconLocation = "{icon_path}"' if icon_path else ""

        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{lnk_path}")
$s.TargetPath = "{python_exe}"
$s.Arguments = "{args_str}"
$s.WorkingDirectory = "{venv_path}"
$s.WindowStyle = {window_style}
{icon_line}
$s.Description = "Launched via VenvStudio"
$s.Save()
'''
        # Write temp .ps1 and execute
        ps_file = desktop / f"_venvstudio_shortcut_tmp.ps1"
        ps_file.write_text(ps_script, encoding="utf-8")
        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_file)],
                capture_output=True, text=True, timeout=15,
                **subprocess_args()
            )
            if result.returncode != 0:
                raise RuntimeError(f"PowerShell error: {result.stderr.strip()}")
        finally:
            ps_file.unlink(missing_ok=True)

        # For GUI apps, also create a hidden-console .bat wrapper
        if not needs_console:
            bat_path = venv_path / "scripts" / f"launch_{name.replace(' ', '_')}.bat"
            bat_path.parent.mkdir(parents=True, exist_ok=True)
            bat_content = f'@echo off\nstart "" /B "{python_exe}" {args_str}\n'
            bat_path.write_text(bat_content, encoding="utf-8")

    def _create_linux_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, venv_path):
        """Create Linux .desktop file with icon."""
        desktop_file = desktop / f"{name}.desktop"
        args_str = " ".join(cmd_args)

        icon_line = f"Icon={icon_path}" if icon_path else ""
        content = (
            f"[Desktop Entry]\n"
            f"Type=Application\n"
            f"Name={name}\n"
            f"Exec={python_exe} {args_str}\n"
            f"Path={venv_path}\n"
            f"Terminal=false\n"
            f"{icon_line}\n"
            f"Comment=Launched via VenvStudio\n"
        )
        desktop_file.write_text(content, encoding="utf-8")
        os.chmod(str(desktop_file), 0o755)

    def _create_macos_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, venv_path):
        """Create macOS .command script."""
        sh_path = desktop / f"{name}.command"
        args_str = " ".join(cmd_args)
        content = f'#!/bin/bash\ncd "{venv_path}"\n"{python_exe}" {args_str}\n'
        sh_path.write_text(content, encoding="utf-8")
        os.chmod(str(sh_path), 0o755)

