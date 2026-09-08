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
from src.gui.launcher_run import resolve_launch_workdir


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

        # System apps (package == "__system__") are not Python entry points:
        # conda installs their own executable inside the env (R.exe for
        # R Console). They have no "command" key, so the normal path would
        # raise KeyError and point the shortcut at python.exe. Target the
        # executable directly instead.
        # B77: ask the SAME function the Launch button asks. Without this
        # the shortcut got app_def["command"] raw -- no --notebook-dir, no
        # --no-browser -- and ran in the environment folder whatever the
        # Jupyter Working Dir setting said. `_launch_dir` is None for apps
        # that have no opinion about a working directory, and those keep the
        # old behaviour of starting in the environment.
        # no_browser=False: the application opens the browser itself after
        # reading the server URL from the process output, so it passes
        # --no-browser. A shortcut cannot do that -- with the flag it would
        # start a server and show nothing.
        _launch_dir, app_def = resolve_launch_workdir(
            getattr(self, "config", None), venv_path, app_def,
            no_browser=False)

        # B93: Spyder needs --conf-dir pointing at a config whose interpreter
        # is this environment. That was decided inside _launch_app, so the
        # shortcut never got it and Spyder opened against the shared
        # ~/.config/spyder-py3 with an empty interpreter box. Both paths now
        # ask the same function. PackagePanel composes LauncherRunMixin, so
        # it is reachable from here; the getattr guard is for the case where
        # this mixin is used on a class that does not.
        _apply_conf = getattr(self, "apply_spyder_conf", None)
        if callable(_apply_conf) and app_def.get("command"):
            app_def = dict(app_def)
            app_def["command"] = _apply_conf(
                app_def["command"], app_def, venv_path)
        _work_dir = _launch_dir or str(venv_path)

        _target = python_exe
        _args = app_def.get("command")
        if _args is None:
            _sys_cmds = app_def.get("system_commands", {})
            _cmd = _sys_cmds.get(platform) or _sys_cmds.get("linux") or []
            if not _cmd:
                QMessageBox.warning(
                    self, tr("warning"),
                    f"{app_name} has no launch command for this platform."
                )
                return
            _exe_name = _cmd[0]
            _args = list(_cmd[1:])
            _found_exe = None
            for _sub in (venv_path / "Scripts", venv_path / "bin",
                         venv_path / "Library" / "bin"):
                for _cand in (_sub / _exe_name, _sub / (_exe_name + ".exe")):
                    if _cand.exists():
                        _found_exe = _cand
                        break
                if _found_exe:
                    break
            if _found_exe is None:
                import shutil as _sh
                _which = _sh.which(_exe_name)
                if not _which:
                    QMessageBox.warning(
                        self, tr("warning"),
                        f"Could not find {_exe_name} in {env_name}."
                    )
                    return
                _found_exe = Path(_which)
            _target = _found_exe

        # B78: every shortcut goes through the wrapper, not just conda ones.
        # Pointing at the environment's python runs the right interpreter but
        # activates nothing, so a shell escape inside the notebook found
        # /usr/bin/python. The wrapper exports VIRTUAL_ENV and PATH first,
        # which is what launcher_run.py does in-process.
        _wrapper = self._write_launch_wrapper(
            venv_path, shortcut_name, _target, _args, platform, _work_dir,
            needs_console=needs_console
        )
        if _wrapper is not None:
            _target = _wrapper
            _args = []

        try:
            if platform == "windows":
                self._create_windows_shortcut(
                    desktop, shortcut_name, _target,
                    _args, icon_path, needs_console, _work_dir, venv_path
                )
            elif platform == "linux":
                self._create_linux_shortcut(
                    desktop, shortcut_name, _target,
                    _args, icon_path, _work_dir
                )
            elif platform == "macos":
                self._create_macos_shortcut(
                    desktop, shortcut_name, _target,
                    _args, icon_path, _work_dir
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

    def _write_launch_wrapper(self, venv_path, name, exe_path, args,
                              platform, work_dir="", needs_console=True):
        """Write a small script that ACTIVATES the environment, then runs exe.

        B78 (Bayram, 2026-09-06). A shortcut used to point straight at the
        environment's python. That runs the right interpreter, but it does not
        ACTIVATE anything -- so inside the notebook a shell escape found the
        wrong one:

            !python --version   ->  Python 3.14.7   (the system one)
            !which python       ->  /usr/bin/python
            !echo $VIRTUAL_ENV  ->  (empty)

        while %pip list, which uses the KERNEL rather than the shell, listed
        the right packages. Both were true at once and only the shell was
        wrong, which is what made it confusing.

        launcher_run.py has done this since v1.6.52 -- environment-aware PATH,
        VIRTUAL_ENV set, PYTHONHOME dropped -- but it does it in-process, and
        a desktop shortcut has no process to do it in. Hence a script.

        This used to be conda-only (_write_conda_launch_wrapper), written so
        R.exe could find its DLLs in Library\\bin. The conda directories are
        still added when they exist; nothing about that case regressed. It is
        simply no longer the only case that needs an environment.

        Returns the wrapper path, or None if it could not be written -- the
        caller then falls back to the bare executable, which is what happened
        before this existed.
        """
        try:
            _pfx = Path(venv_path)
            _dirs = [_pfx, _pfx / "Scripts", _pfx / "bin",
                     _pfx / "Library" / "bin",
                     _pfx / "Library" / "mingw-w64" / "bin",
                     _pfx / "Library" / "usr" / "bin"]
            _dirs = [str(x) for x in _dirs if x.exists()]
            _safe = "".join(ch if ch.isalnum() else "_" for ch in name)
            _args_str = " ".join(f'"{a}"' for a in (args or []))
            _wrap_dir = _pfx / "venvstudio_launchers"
            _wrap_dir.mkdir(parents=True, exist_ok=True)
            _cd = work_dir or str(_pfx)
            if platform == "windows":
                # B94 (Bayram, 2026-09-08: "kisa yoldan calistirdigimizda
                # terminalin gorunmesine gerek yok"). A .bat always opens a
                # console window. Before B78 the shortcut pointed straight at
                # python.exe with WindowStyle 7, so nothing showed; making the
                # wrapper mandatory brought a console with it, which is a
                # regression I introduced.
                #
                # Two changes for apps that do not want a console. pythonw.exe
                # instead of python.exe, so the interpreter itself does not
                # allocate one -- swapped only when the target really is
                # python.exe, since a system app like R.exe must be left
                # alone. And a one-line .vbs that runs the .bat with window
                # style 0, which the shortcut targets instead: the batch file
                # still does the environment work, it simply does it unseen.
                if not needs_console and Path(exe_path).name.lower() == "python.exe":
                    _pw = Path(exe_path).with_name("pythonw.exe")
                    if _pw.is_file():
                        exe_path = _pw
                _wrapper = _wrap_dir / f"{_safe}.bat"
                _path_line = ";".join(_dirs)
                _wrapper.write_text(
                    "@echo off\r\n"
                    f'set "VIRTUAL_ENV={_pfx}"\r\n'
                    f'set "CONDA_PREFIX={_pfx}"\r\n'
                    f'set "PATH={_path_line};%PATH%"\r\n'
                    # PYTHONHOME set for another interpreter makes this one
                    # load the wrong standard library.
                    'set "PYTHONHOME="\r\n'
                    f'cd /d "{_cd}"\r\n'
                    f'"{exe_path}" {_args_str} %*\r\n',
                    encoding="utf-8",
                )
                if not needs_console:
                    _vbs = _wrap_dir / f"{_safe}.vbs"
                    # 0 = hidden window, False = do not wait for it to finish.
                    _vbs.write_text(
                        'CreateObject("WScript.Shell").Run '
                        # THREE quotes each side, not four. In VBScript a
                        # doubled quote inside a literal is an escaped one, so
                        # """path""" is the string "path" -- what Run needs
                        # for a path with spaces. Four quotes would close the
                        # literal early and leave the path as a bare token.
                        f'"""{_wrapper}""", 0, False\r\n',
                        encoding="utf-8",
                    )
                    return _vbs
            else:
                _wrapper = _wrap_dir / f"{_safe}.sh"
                _path_line = ":".join(_dirs)
                _wrapper.write_text(
                    "#!/bin/bash\n"
                    f'export VIRTUAL_ENV="{_pfx}"\n'
                    f'export CONDA_PREFIX="{_pfx}"\n'
                    f'export PATH="{_path_line}:$PATH"\n'
                    "unset PYTHONHOME\n"
                    f'cd "{_cd}"\n'
                    f'exec "{exe_path}" {_args_str} "$@"\n',
                    encoding="utf-8",
                )
                os.chmod(str(_wrapper), 0o755)
            return _wrapper
        except Exception:
            return None

    def _create_windows_shortcut(self, desktop, name, python_exe, cmd_args,
                                 icon_path, needs_console, work_dir,
                                 venv_path):
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
$s.WorkingDirectory = "{work_dir}"
$s.WindowStyle = {window_style}
{icon_line}
$s.Description = "Launched via VenvStudio"
$s.Save()
'''
        # Write temp .ps1 and execute
        import tempfile
        ps_file = Path(tempfile.gettempdir()) / "_venvstudio_shortcut_tmp.ps1"
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
            # B77: the .lnk carried a WorkingDirectory but this wrapper
            # did not, so the shortcut for a GUI app still started wherever
            # cmd happened to be. It gets the same directory as the .lnk.
            bat_content = (f'@echo off\ncd /d "{work_dir}"\n'
                           f'start "" /B "{python_exe}" {args_str}\n')
            bat_path.write_text(bat_content, encoding="utf-8")

    def _create_linux_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, work_dir):
        """Create Linux .desktop file with icon."""
        desktop_file = desktop / f"{name}.desktop"
        args_str = " ".join(cmd_args)

        icon_line = f"Icon={icon_path}" if icon_path else ""
        content = (
            f"[Desktop Entry]\n"
            f"Type=Application\n"
            f"Name={name}\n"
            f"Exec={python_exe} {args_str}\n"
            f"Path={work_dir}\n"
            f"Terminal=false\n"
            f"{icon_line}\n"
            f"Comment=Launched via VenvStudio\n"
        )
        desktop_file.write_text(content, encoding="utf-8")
        os.chmod(str(desktop_file), 0o755)

    def _create_macos_shortcut(self, desktop, name, python_exe, cmd_args, icon_path, work_dir):
        """Create macOS .command script."""
        sh_path = desktop / f"{name}.command"
        args_str = " ".join(cmd_args)
        content = f'#!/bin/bash\ncd "{work_dir}"\n"{python_exe}" {args_str}\n'
        sh_path.write_text(content, encoding="utf-8")
        os.chmod(str(sh_path), 0o755)

