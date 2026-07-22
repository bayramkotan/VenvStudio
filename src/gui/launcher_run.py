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

        # Build command based on framework
        if pkg == "streamlit":
            cmd = [str(python_exe), "-m", "streamlit", "run", filepath, "--server.headless", "true"]
            url = "http://localhost:8501"
        elif pkg == "dash":
            cmd = [str(python_exe), filepath]
            url = "http://localhost:8050"
        elif pkg == "gradio":
            cmd = [str(python_exe), filepath]
            url = "http://localhost:7860"
        elif pkg == "fastapi":
            # Extract module name for uvicorn
            module = os.path.splitext(os.path.basename(filepath))[0]
            cmd = [str(python_exe), "-m", "uvicorn", f"{module}:app", "--reload"]
            url = "http://localhost:8000/docs"
        elif pkg == "panel":
            cmd = [str(python_exe), "-m", "panel", "serve", filepath, "--show"]
            url = ""
        elif pkg == "voila":
            cmd = [str(python_exe), "-m", "voila", filepath]
            url = "http://localhost:8866"
        elif pkg == "mlflow":
            cmd = [str(python_exe), filepath]
            url = ""
        elif pkg == "tensorboard":
            cmd = [str(python_exe), "-m", "tensorboard.main", "--logdir", work_dir]
            url = "http://localhost:6006"
        elif pkg == "datasette":
            cmd = [str(python_exe), "-m", "datasette", filepath]
            url = "http://localhost:8001"
        else:
            cmd = [str(python_exe), filepath]
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
                # keep extra args from '-m <mod> <args...>' (e.g. jupyter lab)
                if len(_app_cmd) >= 2 and _app_cmd[0] == "-m":
                    cmd = [_exe_path] + list(_app_cmd[2:])
                else:
                    cmd = [_exe_path]
            elif _pipx_py:
                cmd = [_pipx_py] + _app_cmd
            else:
                # fallback: python -m ...
                cmd = [str(python_exe)] + _app_cmd
        else:
            cmd = [str(python_exe)] + app_def["command"]

        _log.debug(f"🚀 [Launcher] command: {' '.join(_fmt_path(c) for c in cmd)}")
        # Check if app needs console (e.g. IPython)
        show_console = app_def.get("needs_console", False)

        # Working directory — Jupyter uses config setting, others use home
        is_jupyter = any("jupyter" in str(c).lower() for c in app_def.get("command", []))
        if is_jupyter:
            jwd = self.config.get("jupyter_workdir", "home") if hasattr(self, "config") and self.config else "home"
            jwd_custom = self.config.get("jupyter_workdir_custom", "") if hasattr(self, "config") and self.config else ""
            if jwd == "custom" and jwd_custom and os.path.isdir(jwd_custom):
                notebook_dir = jwd_custom
            elif jwd == "env":
                notebook_dir = str(venv_path)
            else:
                notebook_dir = os.path.expanduser("~")
            work_dir = notebook_dir
            # Pass --notebook-dir so Jupyter actually opens in the chosen folder
            app_def = dict(app_def)
            app_def["command"] = list(app_def["command"]) + ["--notebook-dir", notebook_dir]
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

        reply = QMessageBox.question(
            self, f"Uninstall {app_def['name']}",
            f"Are you sure you want to uninstall {app_def['name']}?\n\n"
            f"Packages to remove: {', '.join(pkgs_to_remove)}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.status_label.setText(f"Uninstalling {app_def['name']}...")
        self.current_worker = WorkerThread(
            self.pip_manager.uninstall_packages, pkgs_to_remove
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

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

