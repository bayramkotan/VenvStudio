"""VenvStudio - Package Panel: Launcher Run Mixin
Launching apps/scripts, install/uninstall for launcher tools
(moved from package_panel.py).
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.core.venv_manager_common import _fmt_path

_log = logging.getLogger("venvstudio.gui.launcher")
from src.gui.package_panel_common import WorkerThread


class LauncherRunMixin:
    """Mixin for PackagePanel: launch/install/uninstall logic for launcher tools."""

    def _launch_system_app(self, app_def: dict):
        """
        Detect and launch a system-level application.
        Checks: (1) conda install if in conda env, (2) portable install, (3) system PATH.
        Offers appropriate install if not found.
        """
        import shutil as _shutil
        from src.utils.platform_utils import get_platform
        from src.core.system_tools_installer import get_installer

        plat = get_platform()
        name = app_def["name"]
        _log.info(f"🚀 [Launcher] Launching system app '{name}' (platform={plat})")
        icon_key = app_def.get("icon_key", "")
        installer = get_installer(icon_key)

        # Detect env type
        env_path = None
        env_type = getattr(self, "_current_env_type", "venv")
        if self.pip_manager:
            vp = self.pip_manager.venv_path
            marker = vp / ".venvstudio_env"
            if marker.exists():
                env_path = vp

        # ── Windows: RStudio has no working conda-forge build ────────────
        # rstudio-desktop "installs" on Windows but ships NO rstudio.exe
        # (verified: nothing under the env matches rstudio*.exe). Point the
        # user to the official installer instead of a phantom conda install.
        # r-base still comes from conda so RStudio finds an R interpreter.
        if plat == "windows" and app_def.get("icon_key") == "rstudio":
            from PySide6.QtWidgets import QMessageBox as _QMB
            import webbrowser as _wb
            _r = _QMB.question(
                self, name,
                "RStudio has no Windows build on conda-forge, so it can't be "
                "installed here automatically.\n\n"
                "Open the official RStudio download page?\n"
                "(Tip: install r-base from the R Console card first so RStudio "
                "detects R.)",
                _QMB.Yes | _QMB.No,
            )
            if _r == _QMB.Yes:
                _wb.open("https://posit.co/download/rstudio-desktop/")
            return

        # ── Conda env: use micromamba to install ─────────────────────────
        if env_type == "conda" and env_path:
            conda_pkgs = app_def.get("conda_packages", [])
            conda_channels = app_def.get("conda_channels", ["conda-forge"])

            if not conda_pkgs:
                QMessageBox.information(
                    self, name,
                    f"{name} is not available as a conda package.\n"
                    f"Try switching to a Python or Tool Environment."
                )
                return

            # Check if already installed via conda
            from src.core.micromamba_installer import (
                list_conda_packages, install_conda_packages,
                get_micromamba_exe, download_micromamba,
            )
            installed_pkgs = {p.get("name", "").lower()
                              for p in list_conda_packages(env_path)}
            primary_pkg = conda_pkgs[0].lower()

            if primary_pkg not in installed_pkgs:
                reply = QMessageBox.question(
                    self, f"Install {name}?",
                    f"{name} is not installed in this conda environment.\n\n"
                    f"Install via conda-forge:\n"
                    f"  {', '.join(conda_pkgs)}\n\n"
                    f"Install now?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

                self._set_busy(True)
                self.status_label.setText(f"Installing {name} via conda-forge...")

                _env_path = env_path
                _pkgs = conda_pkgs
                _channels = conda_channels

                def _do_conda_install(callback=None):
                    if not get_micromamba_exe():
                        if callback:
                            callback("Downloading micromamba...")
                        download_micromamba(progress_cb=callback)
                    ok = install_conda_packages(
                        _env_path, _pkgs,
                        channels=_channels,
                        progress_cb=callback,
                    )
                    return (ok,
                            f"{name} installed!" if ok
                            else f"{name} conda install failed")

                self.current_worker = WorkerThread(_do_conda_install)
                self.current_worker.progress.connect(self._on_progress)
                self.current_worker.finished.connect(
                    lambda ok, msg, a=app_def:
                        self._on_system_install_finished(ok, msg, a)
                )
                self.current_worker.start()
                return

            # Already installed — find exe in conda env and launch
            conda_bin = env_path / ("Scripts" if plat == "windows" else "bin")
            # The REAL executable name comes from the card's system_commands
            # (e.g. "R Console" → R.exe). Deriving it from the display name
            # produced nonsense like "Scripts\r console" (bug seen on R).
            exe_candidates = []
            _sys_cmd = (app_def.get("system_commands") or {}).get(plat) or []
            if _sys_cmd:
                _first = _sys_cmd[0]
                exe_candidates += [_first,
                                   _first[:-4] if _first.lower().endswith(".exe")
                                   else _first + ".exe"]
            exe_candidates += [name, name.lower(), name + ".exe",
                               name.upper(), name.upper() + ".exe"]
            exe_path = None
            for candidate in exe_candidates:
                p = conda_bin / candidate
                if p.exists():
                    exe_path = str(p)
                    break
            if not exe_path:
                exe_path = _shutil.which(name) or _shutil.which(name.lower())

            if exe_path:
                self._launch_exe(exe_path, app_def, conda_prefix=env_path)
            else:
                QMessageBox.information(
                    self, name,
                    f"{name} is installed but executable not found.\n"
                    f"Try launching from terminal:\n"
                    f"  {conda_bin / (exe_candidates[0] if exe_candidates else name)}"
                )
            return
        # ─────────────────────────────────────────────────────────────────

        # 1. Check portable install in env
        exe_path = None
        if installer and env_path:
            exe_path = installer.get_portable_exe(env_path)

        # 2. Check system PATH / known locations
        if not exe_path and installer:
            exe_path = installer.get_system_exe()

        # 3. Fallback: shutil.which using system_commands
        if not exe_path:
            sys_cmds = app_def.get("system_commands", {})
            cmd_parts = sys_cmds.get(plat) or sys_cmds.get("linux", [])
            if cmd_parts:
                exe_path = _shutil.which(cmd_parts[0])

        # 4. Not found — offer install
        if not exe_path:
            if installer is None:
                QMessageBox.information(
                    self, f"{name} — Not Found",
                    f"{name} is not installed.\n\nPlease install it manually."
                )
                return

            # Choose install mode
            if env_path:
                msg = (
                    f"{name} is not installed.\n\n"
                    f"VenvStudio can install it portably into this environment:\n"
                    f"  {env_path / 'apps' / icon_key}\n\n"
                    f"No system-wide changes will be made.\n"
                    f"Install {name} now?"
                )
            else:
                msg = (
                    f"{name} is not installed.\n\n"
                    f"VenvStudio can download and install it automatically.\n"
                    f"Install {name} now?"
                )

            reply = QMessageBox.question(
                self, f"Install {name}?", msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            self._set_busy(True)
            self.status_label.setText(f"Installing {name}...")

            _env_path = env_path  # capture for closure

            def _do_install(callback=None):
                ok = installer.install(
                    env_path=_env_path,
                    progress_cb=callback,
                    portable=(_env_path is not None),
                )
                return (ok,
                        f"{name} installed successfully" if ok
                        else f"{name} installation failed")

            self.current_worker = WorkerThread(_do_install)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(
                lambda ok, msg, a=app_def: self._on_system_install_finished(ok, msg, a)
            )
            self.current_worker.start()
            return

        # 5. Found — launch
        self._launch_exe(exe_path, app_def)

    @staticmethod
    def _is_spyder_app(app_def) -> bool:
        """True for the Spyder card, whichever way it is launched."""
        if (app_def.get("package") or "").lower() == "spyder":
            return True
        return any("spyder" in str(c).lower()
                   for c in app_def.get("command", []) or [])

    def _prepare_spyder_conf(self, venv_path):
        """Write a Spyder config dir inside the env, pinned to its Python.

        Verified against Spyder 6.1.5: the setting lives in two files under
        <conf-dir>/config/ --

            spyder.ini      [main_interpreter] default=False, custom=True
            transient.ini   [main_interpreter] custom_interpreter=<path>,
                                               custom_interpreters_list=[...]

        Both are needed: transient.ini holds the path, spyder.ini is the
        switch that makes Spyder use it. Writing only one leaves the box
        empty, which is the bug this fixes.

        Returns the conf dir, or None if anything went wrong -- Spyder then
        starts with its own defaults rather than not starting at all.
        """
        import configparser
        from pathlib import Path as _P
        try:
            from src.utils.platform_utils import get_python_executable
            _env = _P(venv_path)
            _py = str(get_python_executable(_env))
            if not os.path.isfile(_py):
                return None
            _conf = _env / ".spyder"
            _cfg = _conf / "config"
            _cfg.mkdir(parents=True, exist_ok=True)

            # spyder.ini — the switch. Merge, never overwrite: the user's
            # theme, shortcuts and layout live in this file too.
            _main = _cfg / "spyder.ini"
            _c1 = configparser.ConfigParser()
            _c1.optionxform = str
            if _main.exists():
                _c1.read(_main, encoding="utf-8")
            if not _c1.has_section("main_interpreter"):
                _c1.add_section("main_interpreter")
            _c1["main_interpreter"]["default"] = "False"
            _c1["main_interpreter"]["custom"] = "True"
            with open(_main, "w", encoding="utf-8") as _f:
                _c1.write(_f)

            # transient.ini — the path itself.
            _tr = _cfg / "transient.ini"
            _c2 = configparser.ConfigParser()
            _c2.optionxform = str
            if _tr.exists():
                _c2.read(_tr, encoding="utf-8")
            if not _c2.has_section("main_interpreter"):
                _c2.add_section("main_interpreter")
            _c2["main_interpreter"]["custom_interpreter"] = _py
            _c2["main_interpreter"]["custom_interpreters_list"] = f"['{_py}']"
            with open(_tr, "w", encoding="utf-8") as _f:
                _c2.write(_f)

            _log.info(f"🕷️ [Spyder] config at {_fmt_path(_conf)} "
                      f"-> interpreter {_fmt_path(_py)}")
            return _conf
        except Exception as _e:
            _log.warning(f"[Spyder] could not prepare config: {_e}")
            return None

    def _log_launch_command(self, cmd, app_def):
        """Box the command used to start an app, so the log teaches it.

        The launcher already wrote this at DEBUG level, which meant the one
        thing a curious user would want to copy was buried among cache lines.
        """
        try:
            if not self._get_config("show_commands", True):
                return
            from src.utils.logger import banner_command
            _env = ""
            if getattr(self, "pip_manager", None) and getattr(
                    self.pip_manager, "venv_path", None):
                _env = self.pip_manager.venv_path.name
            _name = app_def.get("name", "app")
            _ctx = f"Launch {_name} (env: {_env})" if _env else f"Launch {_name}"
            _cmd_str = " ".join(str(c) for c in cmd if c)
            banner_command(_cmd_str, context=_ctx)
            self._set_env_cmd_strip(_cmd_str)
        except Exception:
            pass

    def _launch_exe(self, exe_path: str, app_def: dict, conda_prefix=None):
        """Launch an executable with proper detach/console flags.

        conda_prefix: if the exe lives in a conda env, its runtime DLLs
        (Library\\bin, mingw-w64) must be on PATH — launching bare R.exe
        gave "libgcc_s_seh-1.dll was not found" on Windows.
        """
        from src.utils.platform_utils import get_platform
        plat = get_platform()
        name = app_def["name"]
        self._conda_launch_env = None
        if conda_prefix:
            from pathlib import Path as _P
            _pfx = _P(conda_prefix)
            _extra = [_pfx, _pfx / "Scripts", _pfx / "bin",
                      _pfx / "Library" / "bin",
                      _pfx / "Library" / "mingw-w64" / "bin",
                      _pfx / "Library" / "usr" / "bin"]
            _env = dict(os.environ)
            _env["PATH"] = os.pathsep.join(
                [str(x) for x in _extra if x.exists()] + [_env.get("PATH", "")])
            _env["CONDA_PREFIX"] = str(_pfx)
            self._conda_launch_env = _env
        sys_cmds = app_def.get("system_commands", {})
        cmd_parts = sys_cmds.get(plat) or sys_cmds.get("linux", [exe_path])
        cmd = [exe_path] + list(cmd_parts[1:])
        _log.info(f"🚀 [Launcher] Launching '{name}' exe: {_fmt_path(exe_path)}")
        work_dir = os.path.expanduser("~")
        self._log_launch_command(cmd, app_def)
        try:
            show_console = app_def.get("needs_console", False)
            if plat == "windows":
                if show_console:
                    subprocess.Popen(cmd, cwd=work_dir,
                                     env=getattr(self, "_conda_launch_env", None),
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(cmd, cwd=work_dir,
                                     env=getattr(self, "_conda_launch_env", None),
                                     creationflags=0x00000008 | 0x08000000,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            else:
                if show_console:
                    from src.gui.platform_utils import launch_in_terminal
                    terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                    launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)
                else:
                    from src.utils.platform_utils import appimage_clean_env
                    _ai_env = appimage_clean_env()
                    _popen_kw2 = dict(cwd=work_dir, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, start_new_session=True)
                    if _ai_env is not None:
                        _popen_kw2["env"] = _ai_env
                    _cenv = getattr(self, "_conda_launch_env", None)
                    if _cenv is not None:
                        _popen_kw2["env"] = {**_popen_kw2.get("env", {}), **_cenv} \
                            if _popen_kw2.get("env") else _cenv
                    subprocess.Popen(cmd, **_popen_kw2)
            self.status_label.setText(f"✅ {name} launched")
            url = app_def.get("open_browser")
            if url:
                from PySide6.QtCore import QTimer
                from src.utils.platform_utils import open_url
                delay = app_def.get("browser_delay", 2)
                QTimer.singleShot(delay * 1000, lambda: open_url(url))
        except Exception as e:
            QMessageBox.critical(self, f"{name} — Launch Error", str(e))

    def _on_system_install_finished(self, success: bool, message: str, app_def: dict):
        """Called after a system tool silent install completes."""
        self._set_busy(False)
        # Invalidate system tool cache so is_installed re-checks
        self._system_tool_cache.clear()
        name = app_def["name"]
        if success:
            self.status_label.setText(f"✅ {name} installed. Launching...")
            # Invalidate conda package cache so status refreshes correctly
            if self.pip_manager:
                _cache_key = f"_conda_installed_cache_{self.pip_manager.venv_path}"
                if hasattr(self, _cache_key):
                    delattr(self, _cache_key)
                # B141: refresh env table too (conda pkg count changes)
                try:
                    from src.core.venv_manager import VenvManager
                    _vm = self._get_venv_manager(self.pip_manager.venv_path.parent)
                    _vm.invalidate_cache(self.pip_manager.venv_path)
                except Exception:
                    pass
            # B182 follow-up: refresh the Packages page header (size + pkg
            # count) after a system tool install. Without this the badge
            # at the top would stay stale until the user navigates away.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            self.env_refresh_requested.emit(-1)
            # Refresh card states then launch
            self._update_launcher_status()
            from PySide6.QtCore import QTimer
            # Rebuild the Quick Launch sidebar in MainWindow. Package
            # installs go through package_ops and call this callback, but the
            # conda system-app path never did -- so an app installed here
            # (R Console via r-base) showed "Installed (conda-forge)" on its
            # card while the sidebar still said "No apps installed" until the
            # user switched environments and came back.
            #
            # Delayed: the sidebar detects system apps by probing the env for
            # the executable, and those files are not reliably visible the
            # instant micromamba exits.
            def _refresh_quick_launch():
                _cb = getattr(self, "_ql_update_callback", None)
                if callable(_cb):
                    _env_name = (self.pip_manager.venv_path.name
                                 if self.pip_manager else "")
                    try:
                        _cb(env_name=_env_name)
                    except Exception:
                        pass

            QTimer.singleShot(1500, _refresh_quick_launch)
            QTimer.singleShot(500, lambda: self._launch_system_app(app_def))
        else:
            self.status_label.setText(f"❌ {name} install failed")
            QMessageBox.critical(
                self, f"{name} — Install Failed",
                f"Could not install {name} automatically.\n\n"
                f"{message}\n\n"
                f"Please install it manually and try again.\n"
            )

    def _get_orange3_packages(self, python_exe) -> list:
        """Return the right Orange3 packages based on Python version.
        Orange3 requires PyQt5 + PyQtWebEngine (uses AnyQt, does not support PySide6).
        chardet<4.0 required for Orange.data.io_util compatibility.
        """
        try:
            from src.utils.platform_utils import subprocess_args
            result = subprocess.run(
                [str(python_exe), "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            ver_parts = tuple(int(x) for x in ver_str.split(".")[:2])
        except Exception:
            ver_parts = (3, 11)  # safe default

        if ver_parts <= (3, 9):
            return ["PyQt5", "PyQtWebEngine", "chardet<4.0", "orange3<=3.36.2"]
        else:
            return ["PyQt5", "PyQtWebEngine", "chardet<4.0", "orange3"]

    def _launch_script(self, app_def: dict):
        """Let user pick a .py file and run it with the selected framework."""
        import os
        from PySide6.QtWidgets import QFileDialog

        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, f"Select Python script for {app_def['name']}", "",
            "Python Files (*.py);;All Files (*)"
        )
        if not filepath:
            return

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)
        work_dir = os.path.dirname(filepath)
        pkg = app_def["package"].lower()
        _is_pixi_script = getattr(self, "_current_env_type", "venv") == "pixi"

        def _py(*args):
            """Build command: pixi run python <args> for pixi, else python <args>."""
            if _is_pixi_script:
                import shutil as _sh3
                _pb = _sh3.which("pixi") or str(Path.home() / ".pixi" / "bin" / "pixi")
                return [_pb, "run", "python"] + list(args)
            return [str(python_exe)] + list(args)

        # Build command based on framework
        if pkg == "streamlit":
            cmd = _py("-m", "streamlit", "run", filepath, "--server.headless", "true")
            url = "http://localhost:8501"
        elif pkg == "dash":
            cmd = _py(filepath)
            url = "http://localhost:8050"
        elif pkg == "gradio":
            cmd = _py(filepath)
            url = "http://localhost:7860"
        elif pkg == "fastapi":
            module = os.path.splitext(os.path.basename(filepath))[0]
            cmd = _py("-m", "uvicorn", f"{module}:app", "--reload")
            url = "http://localhost:8000/docs"
        elif pkg == "panel":
            cmd = _py("-m", "panel", "serve", filepath, "--show")
            url = ""
        elif pkg == "voila":
            cmd = _py("-m", "voila", filepath)
            url = "http://localhost:8866"
        elif pkg == "mlflow":
            cmd = _py(filepath)
            url = ""
        elif pkg == "tensorboard":
            cmd = _py("-m", "tensorboard.main", "--logdir", work_dir)
            url = "http://localhost:6006"
        elif pkg == "datasette":
            cmd = _py("-m", "datasette", filepath)
            url = "http://localhost:8001"
        else:
            cmd = _py(filepath)
            url = ""

        try:
            from src.utils.platform_utils import get_platform
            import subprocess
            if get_platform() == "windows":
                subprocess.Popen(cmd, cwd=work_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                from src.gui.platform_utils import launch_in_terminal
                terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)

            self.status_label.setText(f"🚀 Running {os.path.basename(filepath)}")

            if url:
                import threading, time as _t
                from src.utils.platform_utils import open_url
                def _open(u):
                    _t.sleep(3)
                    open_url(u)
                threading.Thread(target=_open, args=(url,), daemon=True).start()

        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"Failed to launch script:\n{e}")

    def _launch_app(self, app_def: dict):
        """Launch an app from the selected environment."""
        import os
        from PySide6.QtWidgets import QFileDialog

        _env_name = ""
        if self.pip_manager and getattr(self.pip_manager, "venv_path", None):
            _env_name = self.pip_manager.venv_path.name
        _log.info(f"🚀 [Launcher] Launching '{app_def.get('name', '?')}' in env '{_env_name or '(none)'}'")

        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        # ── System-level app (R, RStudio, Ollama, DBeaver, Quarto…) ─────────
        if app_def.get("system_app"):
            self._launch_system_app(app_def)
            return

        # TensorBoard and similar tools need a log directory
        if app_def.get("pick_logdir", False):
            logdir = QFileDialog.getExistingDirectory(
                self,
                f"Select log directory for {app_def['name']}",
                os.path.expanduser("~")
            )
            if not logdir:
                return
            # Replace "." in command with chosen dir
            app_def = dict(app_def)
            app_def["command"] = [
                c if c != "." else logdir for c in app_def["command"]
            ]

        venv_path = self.pip_manager.venv_path
        python_exe = get_python_executable(venv_path)

        # Jupyter: work out --notebook-dir/--no-browser and mutate
        # app_def["command"] HERE, before ANY cmd list gets built from
        # it below (the pipx branch snapshots app_def["command"] into
        # _app_cmd even earlier than the plain-venv branch does) --
        # doing this later (as a previous attempt did) mutated a dict
        # that had already been copied into `cmd`, so --no-browser
        # never actually reached the real subprocess (Bayram,
        # 2026-08-14, caught via the launch log showing the bare
        # "python -m jupyter lab" with neither flag present).
        self._jupyter_notebook_dir = None
        if any("jupyter" in str(c).lower() for c in app_def.get("command", [])):
            jwd = self.config.get("jupyter_workdir", "home") if hasattr(self, "config") and self.config else "home"
            jwd_custom = self.config.get("jupyter_workdir_custom", "") if hasattr(self, "config") and self.config else ""
            if jwd == "custom" and jwd_custom and os.path.isdir(jwd_custom):
                notebook_dir = jwd_custom
            elif jwd == "env":
                notebook_dir = str(venv_path)
            else:
                notebook_dir = os.path.expanduser("~")
            self._jupyter_notebook_dir = notebook_dir
            app_def = dict(app_def)
            app_def["command"] = list(app_def["command"]) + ["--notebook-dir", notebook_dir, "--no-browser"]

        pkg_name = app_def["package"].lower()
        # pip normalizes package names: quarto-cli ↔ quarto_cli — check both
        pkg_name_alt = pkg_name.replace("-", "_") if "-" in pkg_name else pkg_name.replace("_", "-")
        is_installed = pkg_name in self.installed_package_names or pkg_name_alt in self.installed_package_names

        if not is_installed:
            # Check min/max Python version if specified
            min_py = app_def.get("min_python")
            max_py = app_def.get("max_python")
            note = app_def.get("note", "")
            if min_py or max_py:
                try:
                    from src.utils.platform_utils import subprocess_args
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        **subprocess_args(capture_output=True, text=True, timeout=5)
                    )
                    ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                    ver_parts = tuple(int(x) for x in ver_str.split(".")[:2])

                    if min_py:
                        min_parts = tuple(int(x) for x in min_py.split(".")[:2])
                        if ver_parts < min_parts:
                            QMessageBox.warning(
                                self, app_def["name"],
                                f"{app_def['name']} requires Python ≥{min_py}\n"
                                f"This environment uses Python {ver_str}.\n\n"
                                f"Create a new environment with Python ≥{min_py} and try again."
                            )
                            return

                    if max_py:
                        max_parts = tuple(int(x) for x in max_py.split(".")[:2])
                        if ver_parts > max_parts:
                            QMessageBox.warning(
                                self, app_def["name"],
                                f"{app_def['name']} supports Python {min_py or '3.x'}–{max_py} only.\n"
                                f"This environment uses Python {ver_str}.\n\n"
                                f"Create a new environment with Python ≤{max_py} and try again."
                            )
                            return
                except Exception:
                    pass

            msg = f"{app_def['name']} is not installed in this environment.\n\nInstall '{app_def['package']}' now?"
            if note:
                msg += f"\n\nNote: {note}"

            reply = QMessageBox.question(
                self, app_def["name"], msg,
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            # Install it — determine packages to install
            pkgs_to_install = app_def.get("install_packages", [app_def["package"]])

            # Dynamic package resolution for Orange3 based on Python version
            if app_def["package"] == "orange3":
                pkgs_to_install = self._get_orange3_packages(python_exe)
            self._set_busy(True)
            self.status_label.setText(f"Installing {', '.join(pkgs_to_install)}...")
            # Log launcher-driven installs like Packages-tab installs do.
            _et = getattr(self, "_current_env_type", "venv")
            _app_name = app_def.get("name", "?")
            _n_pk = len(pkgs_to_install)
            _shown_pk = ", ".join(pkgs_to_install[:8])
            if _n_pk > 8:
                _shown_pk += f" (+{_n_pk - 8} more)"
            try:
                from src.utils.logger import get_logger as _gl
                _gl("venvstudio.install").info(
                    f"📦 [Install] env='{_env_name}' type={_et} "
                    f"source='Launcher: {_app_name}' "
                    f"packages({_n_pk}): {_shown_pk}"
                )
            except Exception:
                pass

            # Equivalent command, same as the package tabs show. pipx installs
            # the main app and injects the rest, so the hint says so rather
            # than pretending every package is a separate install.
            _inst_cmds = {
                "venv":   "pip install {packages}",
                "uv":     "uv pip install {packages}",
                "poetry": "poetry add {packages}",
                "conda":  "conda install {packages}",
                "hatch":  "pip install {packages}",
                "pdm":    "pdm add {packages}",
                "pixi":   "pixi add {packages}",
            }
            if _et == "pipx":
                _main_hint = app_def.get("package") or pkgs_to_install[0]
                _extra_hint = [p for p in pkgs_to_install if p != _main_hint]
                _hint_cmd = f"pipx install {_main_hint}"
                for _e in _extra_hint:
                    _hint_cmd += f" && pipx inject {_main_hint} {_e}"
            else:
                _hint_cmd = _inst_cmds.get(
                    _et, "pip install {packages}"
                ).format(packages=" ".join(pkgs_to_install))
            self._show_command_hint(f"Install {_app_name}", _hint_cmd)

            # pipx env: use pipx install instead of pip
            if getattr(self, "_current_env_type", "venv") == "pipx":
                import shutil as _shutil
                _pipx_bin = _shutil.which("pipx")
                _pipx_python = None
                if self.pip_manager and self.pip_manager.venv_path:
                    _marker = self.pip_manager.venv_path / ".venvstudio_env"
                    if _marker.exists():
                        try:
                            import json as _json
                            with open(_marker) as _mf:
                                _mdata = _json.load(_mf)
                            _pipx_python = _mdata.get("python_path", "")
                        except Exception:
                            pass
                # Correct pipx model: install ONE main app, then `pipx inject`
                # any extra libraries into that app's venv. The old code ran a
                # separate `pipx install` for every dependency, so library-only
                # packages (e.g. PyQtWebEngine, a dep of Orange3) failed with
                # "no apps". Main pkg = the card's "package"; the rest are deps.
                _main_pkg = app_def["package"]
                _extra_pkgs = [p for p in pkgs_to_install if p != _main_pkg]

                def _do_pipx_launch_install(callback=None,
                                            _main=_main_pkg, _extras=_extra_pkgs,
                                            _bin=_pipx_bin, _py=_pipx_python):
                    import subprocess, sys
                    from src.utils.platform_utils import subprocess_args
                    _base = [_bin] if _bin else [sys.executable, "-m", "pipx"]

                    # 1) install the main application
                    if callback:
                        callback(f"pipx install {_main}...")
                    cmd = _base + ["install", _main]
                    if _py:
                        cmd += ["--python", _py]
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=600, **subprocess_args())
                    # "already installed" is not a failure
                    if r.returncode != 0 and "already seems to be installed" not in (r.stdout + r.stderr):
                        return (False, f"pipx install failed for {_main}:\n"
                                       f"{(r.stderr or r.stdout)[:400]}")

                    # 2) inject any extra libraries INTO the app's venv
                    failed = []
                    for pkg in _extras:
                        if callback:
                            callback(f"pipx inject {_main} {pkg}...")
                        cmd = _base + ["inject", _main, pkg]
                        r = subprocess.run(cmd, capture_output=True, text=True,
                                           timeout=300, **subprocess_args())
                        if r.returncode != 0:
                            failed.append(pkg)
                    if failed:
                        return (False, "pipx inject failed for: "
                                       + ", ".join(failed))
                    return (True, f"pipx installed: {_main}"
                            + (f" (+{len(_extras)} injected)" if _extras else ""))
                self.current_worker = WorkerThread(_do_pipx_launch_install)
            elif _et == "pixi":
                _pixi_pkgs = list(pkgs_to_install)
                _pixi_env_path = self.pip_manager.venv_path

                def _do_pixi_install(callback=None,
                                     _pkgs=_pixi_pkgs, _ep=_pixi_env_path):
                    import subprocess as _sp, shutil as _sh
                    from src.utils.platform_utils import subprocess_args as _sa
                    _pixi_bin = _sh.which("pixi") or str(Path.home() / ".pixi" / "bin" / "pixi")
                    # Packages not available on conda-forge — must use --pypi
                    _PYPI_ONLY = {"pyqt5", "pyqtwebengine", "pyqt6", "pyqt6-webengine"}
                    _failed = []
                    for _pkg in _pkgs:
                        if callback:
                            callback(f"pixi add {_pkg}...")
                        # Try conda channel first; if pkg is pypi-only, use --pypi directly
                        _pkg_lower = _pkg.split("<")[0].split(">")[0].split("=")[0].lower()
                        _use_pypi = _pkg_lower in _PYPI_ONLY
                        _cmd = [_pixi_bin, "add"] + (["--pypi"] if _use_pypi else []) + [_pkg]
                        _r = _sp.run(
                            _cmd,
                            cwd=str(_ep),
                            **_sa(capture_output=True, text=True, timeout=300)
                        )
                        if _r.returncode != 0 and not _use_pypi:
                            # conda channel failed — retry with --pypi
                            if callback:
                                callback(f"conda channel failed, retrying via PyPI...")
                            _r = _sp.run(
                                [_pixi_bin, "add", "--pypi", _pkg],
                                cwd=str(_ep),
                                **_sa(capture_output=True, text=True, timeout=300)
                            )
                        if _r.returncode != 0:
                            _failed.append(_pkg)
                            if callback:
                                callback(f"pixi add failed: {(_r.stderr or _r.stdout)[:200]}")
                    if _failed:
                        return (False, f"pixi add failed for: {', '.join(_failed)}")
                    return (True, f"pixi installed: {', '.join(_pkgs)}")

                self.current_worker = WorkerThread(_do_pixi_install)
            elif _et == "pdm":
                _pdm_pkgs = list(pkgs_to_install)
                _pdm_env_path = self.pip_manager.venv_path

                def _do_pdm_install(callback=None,
                                    _pkgs=_pdm_pkgs, _ep=_pdm_env_path):
                    import subprocess as _sp, shutil as _sh
                    from src.utils.platform_utils import subprocess_args as _sa
                    _pdm_bin = _sh.which("pdm")
                    if not _pdm_bin:
                        return (False, "pdm executable not found")
                    _failed = []
                    for _pkg in _pkgs:
                        if callback:
                            callback(f"pdm add {_pkg}...")
                        _r = _sp.run(
                            [_pdm_bin, "add", _pkg],
                            cwd=str(_ep),
                            **_sa(capture_output=True, text=True, timeout=300)
                        )
                        if _r.returncode != 0:
                            _failed.append(_pkg)
                            if callback:
                                callback(f"pdm add failed: {(_r.stderr or _r.stdout)[:200]}")
                    if _failed:
                        return (False, f"pdm add failed for: {', '.join(_failed)}")
                    return (True, f"pdm installed: {', '.join(_pkgs)}")

                self.current_worker = WorkerThread(_do_pdm_install)
            else:
                self.current_worker = WorkerThread(
                    self.pip_manager.install_packages, pkgs_to_install
                )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(
                lambda ok, msg, a=app_def: self._on_app_install_finished(ok, msg, a)
            )
            self.current_worker.start()
            return

        # Launch the app — check console toggle
        # pipx env: find app executable in pipx venv or local bin
        if getattr(self, "_current_env_type", "venv") == "pipx":
            from src.utils.platform_utils import get_pipx_home, get_platform as _gp
            import os as _os, shutil as _sh
            _pipx_home = get_pipx_home()
            _pkg = app_def["package"].lower()
            _app_cmd = app_def.get("command", [])
            _is_win = _gp() == "windows"
            _exe_suffix = ".exe" if _is_win else ""
            _scripts_dir = "Scripts" if _is_win else "bin"
            # Package -> primary executable name mapping
            _pipx_exe_map = {
                "jupyterlab":  "jupyter-lab",
                "notebook":    "jupyter-notebook",
                "orange3":     "orange-canvas",
                "spyder":      "spyder",
                "ipython":     "ipython",
                "streamlit":   "streamlit",
                "gradio":      "gradio",
                "dash":        "dash",
                "panel":       "panel",
                "voila":       "voila",
                "mlflow":      "mlflow",
                "tensorboard": "tensorboard",
                "marimo":      "marimo",
                "datasette":   "datasette",
            }
            _exe_name = _pipx_exe_map.get(_pkg)
            if not _exe_name:
                # fallback: derive from command "-m jupyter lab" -> "jupyter"
                if len(_app_cmd) >= 2 and _app_cmd[0] == "-m":
                    _exe_name = _app_cmd[1].split(".")[0]
                else:
                    _exe_name = _pkg
            _exe_path = None
            # 1. pipx venvs/<pkg>/Scripts/<exe>
            if _pipx_home:
                _venv_exe = _os.path.join(_pipx_home, "venvs", _pkg,
                    _scripts_dir, _exe_name + _exe_suffix)
                if _os.path.isfile(_venv_exe):
                    _exe_path = _venv_exe
            # 2. ~/.local/bin/<exe> (pipx exposed apps)
            if not _exe_path:
                _local_bin = _os.path.join(_os.path.expanduser("~"), ".local", "bin", _exe_name + _exe_suffix)
                if _os.path.isfile(_local_bin):
                    _exe_path = _local_bin
            # 3. shutil.which (PATH)
            if not _exe_path:
                _exe_path = _sh.which(_exe_name)
            # Cards whose command is Python code (-c ...) must NOT be started
            # via the bare console script: e.g. `gradio.exe` requires a
            # demo_path argument and exits immediately. Run the card's code
            # with the app's OWN pipx venv python instead.
            _pipx_py = None
            if _pipx_home:
                _cand = _os.path.join(_pipx_home, "venvs", _pkg, _scripts_dir,
                                      "python" + _exe_suffix)
                if _os.path.isfile(_cand):
                    _pipx_py = _cand
            if _app_cmd and _app_cmd[0] == "-c" and _pipx_py:
                cmd = [_pipx_py] + _app_cmd
            elif _exe_path:
                # keep extra args from '-m <mod> <args...>' (e.g. mlflow ui)
                if len(_app_cmd) >= 2 and _app_cmd[0] == "-m":
                    _extra = list(_app_cmd[2:])
                    # Some pipx entry points already encode the subcommand:
                    # jupyterlab exposes "jupyter-lab", not "jupyter". Passing
                    # the subcommand again turned `jupyter lab` into
                    # `jupyter-lab lab`, and the server read "lab" as the
                    # directory to serve -- "No such file or directory:
                    # ~/lab". Drop the token the executable already carries.
                    if _extra and not _extra[0].startswith("-"):
                        _exe_base = _os.path.basename(_exe_path)
                        if _exe_suffix and _exe_base.endswith(_exe_suffix):
                            _exe_base = _exe_base[:-len(_exe_suffix)]
                        if _exe_base.endswith("-" + _extra[0]):
                            _extra = _extra[1:]
                    cmd = [_exe_path] + _extra
                else:
                    cmd = [_exe_path]
            elif _pipx_py:
                cmd = [_pipx_py] + _app_cmd
            else:
                # fallback: python -m ...
                cmd = [str(python_exe)] + _app_cmd
        else:
            # Pixi env: run via `pixi run python <cmd>` so pixi sets up the
            # correct environment variables and site-packages are found.
            if getattr(self, "_current_env_type", "venv") == "pixi":
                import shutil as _sh2
                _pixi_bin2 = _sh2.which("pixi") or str(Path.home() / ".pixi" / "bin" / "pixi")
                cmd = [_pixi_bin2, "run", "python"] + list(app_def["command"])
            else:
                cmd = [str(python_exe)] + app_def["command"]

        # Spyder: point it at a per-environment config directory whose
        # interpreter is already set to this environment. Otherwise every
        # environment shares ~/.config/spyder-py3 and the interpreter box
        # comes up empty, leaving the user to browse for a path VenvStudio
        # already knows.
        if self._is_spyder_app(app_def):
            _conf = self._prepare_spyder_conf(venv_path)
            if _conf and "--conf-dir" not in cmd:
                cmd = list(cmd) + ["--conf-dir", str(_conf)]

        _log.debug(f"🚀 [Launcher] command: {' '.join(_fmt_path(c) for c in cmd)}")
        self._log_launch_command(cmd, app_def)
        # Check if app needs console (e.g. IPython)
        show_console = app_def.get("needs_console", False)

        # Working directory — Jupyter uses config setting (already computed
        # above, before cmd was built, and reused here), others use home
        if self._jupyter_notebook_dir is not None:
            work_dir = self._jupyter_notebook_dir
        elif getattr(self, "_current_env_type", "venv") == "pixi":
            # pixi run must be executed from the project dir (where pixi.toml lives)
            work_dir = str(venv_path)
        elif get_platform() == "windows":
            work_dir = os.environ.get("USERPROFILE", "C:\\")
        else:
            work_dir = os.environ.get("HOME", os.path.expanduser("~"))

        try:
            if get_platform() == "windows":
                if show_console:
                    subprocess.Popen(
                        cmd, cwd=work_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                else:
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NO_WINDOW = 0x08000000
                    subprocess.Popen(
                        cmd, cwd=work_dir,
                        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                    )
            else:
                if show_console:
                    from src.gui.platform_utils import launch_in_terminal
                    terminal_type = self.config.get("terminal_type", "") if hasattr(self, "config") and self.config else ""
                    launch_in_terminal(cmd, cwd=work_dir, terminal_type=terminal_type)
                else:
                    from src.utils.platform_utils import appimage_clean_env
                    _ai_env = appimage_clean_env()
                    _popen_kw = dict(
                        cwd=work_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    if _ai_env is not None:
                        _popen_kw["env"] = _ai_env
                    subprocess.Popen(cmd, **_popen_kw)

            self.status_label.setText(f"🚀 Launched {app_def['name']}")

            # Open browser if app requested it (e.g. Streamlit, Jupyter)
            open_browser_url = app_def.get("open_browser", "")
            if open_browser_url:
                import threading, time as _time
                from src.utils.platform_utils import open_url
                delay = app_def.get("browser_delay", 3)
                def _open_browser(url, d):
                    _time.sleep(d)
                    open_url(url)
                threading.Thread(target=_open_browser, args=(open_browser_url, delay), daemon=True).start()

        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                f"Failed to launch {app_def['name']}:\n{e}"
            )

    def _on_app_install_finished(self, success, message, app_def):
        """After installing an app package, refresh and launch."""
        self._set_busy(False)
        if success:
            # ── Orange3 AppImage post-install verification ──────────────────
            # On AppImage, PyQt5/.so links can be broken even when pip reports
            # success. Verify with a clean-env import test before launching.
            if app_def.get("package") == "orange3" and self.pip_manager:
                import os, sys
                from src.utils.platform_utils import subprocess_args, get_platform
                if os.environ.get("APPIMAGE") or getattr(sys, "frozen", False):
                    python_exe = get_python_executable(self.pip_manager.venv_path)
                    sp_kw = subprocess_args(capture_output=True, text=True, timeout=20)
                    # subprocess_args already strips LD_LIBRARY_PATH etc on AppImage
                    try:
                        verify = subprocess.run(
                            [str(python_exe), "-c",
                             "import PyQt5; import Orange; print('OK')"],
                            **sp_kw
                        )
                        if verify.returncode != 0 or "OK" not in verify.stdout:
                            err = verify.stderr.strip() or verify.stdout.strip()
                            QMessageBox.warning(
                                self, "Orange3 — Import Check Failed",
                                "Orange3 was installed but could not be imported.\n\n"
                                "This usually means a library conflict with the AppImage "
                                "environment.\n\n"
                                f"Details:\n{err[:600]}\n\n"
                                "Workaround: install VenvStudio via pip instead of AppImage, "
                                "or run Orange3 directly from its own conda environment."
                            )
                            self.status_label.setText("⚠️ Orange3 installed but import failed — see warning")
                            self._invalidate_pkg_cache()
                            self._async_refresh_packages(force=True)
                            return
                    except Exception:
                        pass  # verification failed silently — proceed optimistically
            # ────────────────────────────────────────────────────────────────
            self.status_label.setText(f"✅ {app_def['package']} installed. Launching...")
            # Must wait for package list to refresh before launching,
            # otherwise installed_package_names won't contain the new package
            # and _launch_app will show the install dialog again.
            self._invalidate_pkg_cache()

            # ── B141: Tell main_window to refresh the env table ─────────────
            # When installing to a pipx env (and any other env type), the env
            # row in the main table shows stale package count / size. Signal
            # the parent so it re-queries list_venvs_fast with force=True.
            try:
                from src.core.venv_manager import VenvManager
                _vm = self._get_venv_manager(self.pip_manager.venv_path.parent)  # base_dir
                _vm.invalidate_cache(self.pip_manager.venv_path)
                # For pipx we also invalidate the shared pipx tree — many apps share
                # /pipx cache state.
                venv_path_str = str(self.pip_manager.venv_path)
                if "pipx" in venv_path_str.lower():
                    _vm.invalidate_all_caches()
            except Exception:
                pass
            # B182 follow-up: refresh the Packages page header (size + pkg
            # count) after a launch app install. Without this the badge
            # at the top would stay stale until the user navigates away.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            self.env_refresh_requested.emit(-1)
            # ─────────────────────────────────────────────────────────────────

            self._async_refresh_packages(force=True)
            # Connect one-shot signal to launch after refresh completes
            def _launch_after_refresh():
                try:
                    self._pkg_loader.done.disconnect(_launch_after_refresh)
                except Exception:
                    pass
                self._launch_app(app_def)
            if self._pkg_loader:
                self._pkg_loader.done.connect(_launch_after_refresh)
            else:
                self._launch_app(app_def)
        else:
            self.status_label.setText(tr("operation_failed"))
            from src.utils.platform_utils import get_platform
            platform = get_platform()

            # Detect Python version for better error messages
            py_ver_str = ""
            try:
                python_exe = get_python_executable(self.pip_manager.venv_path)
                from src.utils.platform_utils import subprocess_args
                result = subprocess.run(
                    [str(python_exe), "--version"],
                    **subprocess_args(capture_output=True, text=True, timeout=5)
                )
                py_ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            except Exception:
                pass

            short_msg = f"Failed to install {app_def['package']}.\n\n"

            if "No matching distribution" in message or "Could not find" in message:
                short_msg += (
                    f"No compatible version found for Python {py_ver_str}.\n\n"
                    f"This package may not support your Python version yet.\n"
                    f"Try creating an environment with Python 3.12 or 3.13."
                )
            elif "error: subprocess-exited-with-error" in message or "build" in message.lower():
                if platform == "windows":
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install Visual C++ Build Tools:\n"
                        "https://visualstudio.microsoft.com/visual-cpp-build-tools/"
                    )
                elif platform == "macos":
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install Xcode Command Line Tools:\n"
                        "xcode-select --install"
                    )
                else:
                    short_msg += (
                        "A C/C++ build dependency failed to compile.\n\n"
                        "Install build tools:\n"
                        "sudo apt install build-essential python3-dev"
                    )
                if py_ver_str and tuple(int(x) for x in py_ver_str.split(".")[:2]) >= (3, 14):
                    short_msg += (
                        f"\n\n⚠️ Python {py_ver_str} is very new.\n"
                        f"Many packages don't have pre-built wheels yet.\n"
                        f"Consider using Python 3.12 or 3.13."
                    )
            elif "Permission" in message:
                short_msg += "Permission denied. Try running as administrator."
            else:
                lines = [l.strip() for l in message.strip().splitlines() if l.strip()]
                tail = "\n".join(lines[-5:]) if len(lines) > 5 else "\n".join(lines)
                short_msg += tail

            note = app_def.get("note", "")
            if note:
                short_msg += f"\n\nNote: {note}"

            QMessageBox.critical(self, tr("error"), short_msg)

    def _uninstall_app(self, app_def: dict):
        """Uninstall an app from the selected environment with confirmation."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        pkg_name = app_def["package"]
        # Get all packages to uninstall
        pkgs_to_remove = app_def.get("install_packages", [pkg_name])

        # System apps have package == "__system__" and are installed as conda
        # packages (r-base for R Console, and so on). Uninstalling them with
        # pip removes nothing, so route them to micromamba instead.
        _is_conda_app = (
            (app_def.get("system_app")
             or app_def.get("package", "").lower() == "__system__")
            and app_def.get("conda_packages")
            and getattr(self, "_current_env_type", "venv") == "conda"
        )
        if _is_conda_app:
            pkgs_to_remove = list(app_def["conda_packages"])

        # pipx keeps every app in its own environment under venvs/<app>/, so
        # "pip uninstall" against the pipx home removes nothing and returns
        # success -- the progress bar flashed and the app stayed installed.
        # pipx has its own uninstall verb.
        _is_pipx_env = getattr(self, "_current_env_type", "venv") == "pipx"

        reply = QMessageBox.question(
            self, f"Uninstall {app_def['name']}",
            f"Are you sure you want to uninstall {app_def['name']}?\n\n"
            f"Packages to remove: {', '.join(pkgs_to_remove)}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Log launcher-driven uninstalls too.
        _et2 = getattr(self, "_current_env_type", "venv")
        _env_name2 = ""
        if self.pip_manager and getattr(self.pip_manager, "venv_path", None):
            _env_name2 = self.pip_manager.venv_path.name
        _app_name2 = app_def.get("name", "?")
        _n_rm = len(pkgs_to_remove)
        _shown_rm = ", ".join(pkgs_to_remove[:8])
        if _n_rm > 8:
            _shown_rm += f" (+{_n_rm - 8} more)"
        try:
            from src.utils.logger import get_logger as _gl2
            _gl2("venvstudio.install").info(
                f"🗑️ [Uninstall] env='{_env_name2}' type={_et2} "
                f"source='Launcher: {_app_name2}' "
                f"packages({_n_rm}): {_shown_rm}"
            )
        except Exception:
            pass

        # Show the equivalent command, like the package tabs do. pipx removes
        # only the main app (its injected libraries go with the venv), so the
        # hint has to reflect what actually runs, not the full package list.
        _rm_cmds = {
            "venv":   "pip uninstall -y {packages}",
            "uv":     "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda":  "conda remove {packages}",
            "pipx":   "pipx uninstall {packages}",
            "pdm":    "pdm remove {packages}",
            "pixi":   "pixi remove {packages}",
            "hatch":  "pip uninstall -y {packages}",
        }
        _hint_pkgs = pkgs_to_remove
        if _is_pipx_env:
            _hint_pkgs = [app_def.get("package") or pkgs_to_remove[0]]
        self._show_command_hint(
            f"Uninstall {app_def['name']}",
            _rm_cmds.get(_et2, "pip uninstall -y {packages}")
            .format(packages=" ".join(_hint_pkgs))
        )

        self._set_busy(True)
        self.status_label.setText(f"Uninstalling {app_def['name']}...")

        if _is_pipx_env:
            import subprocess as _sp_px
            from src.utils.platform_utils import (
                get_pipx_cmd as _gpc, subprocess_args as _sa_px,
            )
            # Mirror the install path: pipx installs ONE app and injects the
            # rest into that app's venv. So only the main package is a pipx
            # app -- "pipx uninstall uvicorn" just answers "Nothing to
            # uninstall", because uvicorn lives inside the fastapi venv.
            # Removing the app removes everything injected into it.
            _main_px = app_def.get("package") or (pkgs_to_remove[0]
                                                  if pkgs_to_remove else "")
            _rm_pkgs_px = [_main_px] if _main_px else list(pkgs_to_remove)
            _app_label_px = app_def["name"]

            def _do_pipx_remove(callback=None):
                _cmd_base = _gpc()
                if not _cmd_base:
                    return (False, "pipx executable not found")
                _failed = []
                for _pkg in _rm_pkgs_px:
                    if callback:
                        callback(f"pipx uninstall {_pkg}...")
                    _r = _sp_px.run(
                        list(_cmd_base) + ["uninstall", _pkg],
                        **_sa_px(capture_output=True, text=True, timeout=120)
                    )
                    _out = (_r.stdout or "") + (_r.stderr or "")
                    # pipx exits 1 with "Nothing to uninstall for X" when the
                    # app is not there. That is the desired end state, not a
                    # failure -- and the exact wording matters: an earlier
                    # guess of "not installed" never matched, so removing an
                    # already-removed package was reported as an error.
                    _gone = ("nothing to uninstall" in _out.lower()
                             or "not installed" in _out.lower())
                    if _r.returncode != 0 and not _gone:
                        _failed.append(_pkg)
                        if callback:
                            callback(f"pipx uninstall failed: {_out.strip()[:200]}")
                if _failed:
                    return (False,
                            f"pipx uninstall failed for: {', '.join(_failed)}")
                return (True, f"{_app_label_px} removed")

            self.current_worker = WorkerThread(_do_pipx_remove)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
            return

        if _is_conda_app:
            from src.core.micromamba_installer import remove_conda_packages
            _env_path = self.pip_manager.venv_path
            _rm_pkgs = pkgs_to_remove
            _app_label = app_def["name"]

            def _do_conda_remove(callback=None):
                ok = remove_conda_packages(_env_path, _rm_pkgs,
                                           progress_cb=callback)
                return (ok,
                        f"{_app_label} removed"
                        if ok else f"{_app_label} conda remove failed")

            self.current_worker = WorkerThread(_do_conda_remove)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(
                lambda ok, msg, a=app_def:
                    self._on_system_uninstall_finished(ok, msg, a)
            )
            self.current_worker.start()
            return

        if _et2 == "pixi":
            _pixi_rm_pkgs = list(pkgs_to_remove)
            _pixi_rm_path = self.pip_manager.venv_path
            _pixi_lbl = app_def["name"]

            def _do_pixi_remove(callback=None,
                                _pkgs=_pixi_rm_pkgs, _ep=_pixi_rm_path,
                                _lbl=_pixi_lbl):
                import subprocess as _sp, shutil as _sh
                from src.utils.platform_utils import subprocess_args as _sa
                _pixi_bin = _sh.which("pixi") or str(Path.home() / ".pixi" / "bin" / "pixi")
                _failed = []
                for _pkg in _pkgs:
                    if callback:
                        callback(f"pixi remove {_pkg}...")
                    _r = _sp.run(
                        [_pixi_bin, "remove", _pkg],
                        cwd=str(_ep),
                        **_sa(capture_output=True, text=True, timeout=300)
                    )
                    if _r.returncode != 0:
                        _failed.append(_pkg)
                if _failed:
                    return (False, f"pixi remove failed for: {', '.join(_failed)}")
                return (True, f"{_lbl} removed")

            self.current_worker = WorkerThread(_do_pixi_remove)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
            return

        if _et2 == "pdm":
            _pdm_rm_pkgs = list(pkgs_to_remove)
            _pdm_rm_path = self.pip_manager.venv_path
            _pdm_lbl = app_def["name"]

            def _do_pdm_remove(callback=None,
                               _pkgs=_pdm_rm_pkgs, _ep=_pdm_rm_path,
                               _lbl=_pdm_lbl):
                import subprocess as _sp, shutil as _sh
                from src.utils.platform_utils import subprocess_args as _sa
                _pdm_bin = _sh.which("pdm")
                if not _pdm_bin:
                    return (False, "pdm executable not found")
                _failed = []
                for _pkg in _pkgs:
                    if callback:
                        callback(f"pdm remove {_pkg}...")
                    _r = _sp.run(
                        [_pdm_bin, "remove", _pkg],
                        cwd=str(_ep),
                        **_sa(capture_output=True, text=True, timeout=300)
                    )
                    if _r.returncode != 0:
                        _failed.append(_pkg)
                if _failed:
                    return (False, f"pdm remove failed for: {', '.join(_failed)}")
                return (True, f"{_lbl} removed")

            self.current_worker = WorkerThread(_do_pdm_remove)
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
            return

        self.current_worker = WorkerThread(
            self.pip_manager.uninstall_packages, pkgs_to_remove
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _on_system_uninstall_finished(self, success: bool, message: str,
                                      app_def: dict):
        """After removing a conda system app: clear caches and refresh."""
        self._set_busy(False)
        self._system_tool_cache.clear()
        name = app_def["name"]
        if not success:
            self.status_label.setText(f"Failed to uninstall {name}")
            QMessageBox.critical(
                self, f"{name} - Uninstall Failed",
                f"Could not remove {name}.\n\n{message}"
            )
            return
        self.status_label.setText(f"{name} uninstalled")
        if self.pip_manager:
            _cache_key = f"_conda_installed_cache_{self.pip_manager.venv_path}"
            if hasattr(self, _cache_key):
                delattr(self, _cache_key)
            try:
                _vm = self._get_venv_manager(self.pip_manager.venv_path.parent)
                _vm.invalidate_cache(self.pip_manager.venv_path)
            except Exception:
                pass
        try:
            _cur_path = getattr(self, "_current_venv_path", None)
            _cur_backend = getattr(self, "_current_backend", "pip")
            if _cur_path:
                self._update_env_info_bar(_cur_path, _cur_backend)
        except Exception:
            pass
        self.env_refresh_requested.emit(-1)
        self._update_launcher_status()
        from PySide6.QtCore import QTimer

        def _refresh_quick_launch():
            _cb = getattr(self, "_ql_update_callback", None)
            if callable(_cb):
                _env_name = (self.pip_manager.venv_path.name
                             if self.pip_manager else "")
                try:
                    _cb(env_name=_env_name)
                except Exception:
                    pass

        QTimer.singleShot(1500, _refresh_quick_launch)

    def _get_app_icon_path(self, app_def: dict) -> str | None:
        """Return the absolute path to the app's .ico (Windows) or .png (Linux/macOS) icon."""
        icon_key = app_def.get("icon_key", "")
        if not icon_key:
            return None

        # Determine base dir: frozen (PyInstaller) vs source
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS) / "assets" / "app_icons"
        else:
            base = Path(__file__).resolve().parent.parent.parent / "assets" / "app_icons"

        platform = get_platform()
        if platform == "windows":
            icon = base / f"{icon_key}.ico"
        else:
            icon = base / f"{icon_key}_256.png"

        return str(icon) if icon.exists() else None

