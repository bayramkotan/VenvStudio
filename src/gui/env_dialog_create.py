"""VenvStudio - Env Create Dialog: Create Mixin
Environment creation logic for EnvCreateDialog (moved from env_dialog.py).

`_create` is now a thin dispatcher; the original per-env-type bodies are
preserved VERBATIM (including their own `if env_type == ...:` guard) inside
`_create_conda`, `_create_alt_env`, and `_create_venv` to avoid any
re-indentation/transcription risk during the split.
"""
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

# Terminal banners — shown when conda/poetry/uv/pipx envs are created
try:
    from src.utils.logger import banner_start, banner_success, banner_error
except Exception:
    def banner_start(*a, **k): pass
    def banner_success(*a, **k): pass
    def banner_error(*a, **k): pass

# B151: suppress Windows console flash on all subprocess calls
try:
    from src.utils.platform_utils import subprocess_args
except Exception:
    def subprocess_args(**kw): return kw

from src.gui.workers import CreateWorker


class EnvCreateMixin:
    """Mixin for EnvCreateDialog: environment creation dispatch + per-type logic."""

    def _create(self):
        name = self.name_input.text().strip()

        # ── Determine env type early for pipx-specific validation ─────
        env_type = self.env_type_combo.currentData() if hasattr(self, "env_type_combo") else "venv"

        if not name:
            QMessageBox.warning(self, "Warning", "Please enter an environment name.")
            return

        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in name):
            QMessageBox.warning(
                self, "Warning",
                "Environment name contains invalid characters.\n"
                "Avoid: spaces, /, \\, :, *, ?, \", <, >, |"
            )
            return

        if env_type == "conda":
            return self._create_conda(name, env_type)

        if env_type in ("uv", "poetry", "pipx"):
            return self._create_alt_env(name, env_type)

        return self._create_venv(name)

    # ─────────────────────────────────────────────────────────────────────
    # Per-env-type creation bodies (moved verbatim from _create)
    # ─────────────────────────────────────────────────────────────────────

    def _create_conda(self, name, env_type):
        if env_type == "conda":
            import os
            location = self.location_label.text()
            env_path = Path(os.path.join(location, name))
            python_version = self.conda_python_combo.currentData() \
                if hasattr(self, "conda_python_combo") else "3.12"

            self.progress_bar.setVisible(True)
            self.create_btn.setEnabled(False)
            self.create_btn.setText("Creating...")
            self.name_input.setEnabled(False)
            self.env_type_combo.setEnabled(False)
            self.status_label.setStyleSheet("color: #89b4fa; font-size: 15px; font-weight: bold;")
            self.status_label.setText("⚙️ Preparing micromamba...")

            # Terminal banner — conda env creation start
            banner_start(
                f"Creating environment '{name}'",
                details=[
                    f"Type: conda (micromamba)",
                    f"Python: {python_version or 'none'}",
                    f"Location: {env_path}",
                ],
            )

            def _do_conda_create(callback=None):
                from src.core.micromamba_installer import (
                    get_micromamba_exe, download_micromamba,
                    create_conda_env, write_conda_marker,
                )
                import datetime, json
                # Step 1: ensure micromamba available
                if not get_micromamba_exe():
                    if callback:
                        callback("Downloading micromamba...")
                    download_micromamba(progress_cb=callback)

                if not get_micromamba_exe():
                    return False, "Could not download micromamba"

                # Step 2: create env
                ok = create_conda_env(
                    env_path=env_path,
                    python_version=python_version,
                    progress_cb=callback,
                )
                if not ok:
                    return False, "conda env creation failed"

                # Step 3: write marker
                write_conda_marker(env_path, python_version=python_version)

                return True, f"Conda environment '{name}' created!"

            def _on_conda_done(success, message):
                self.progress_bar.setVisible(False)
                self.create_btn.setEnabled(True)
                self.create_btn.setText("Create Environment")
                self.name_input.setEnabled(True)
                self.env_type_combo.setEnabled(True)
                if success:
                    banner_success(
                        f"Environment '{name}' is ready!",
                        details=[
                            f"Type: conda",
                            f"Path: {env_path}",
                            f"Python: {python_version or 'none'}",
                        ],
                    )
                    self.status_label.setStyleSheet("color: #a6e3a1; font-size: 15px; font-weight: bold;")
                    self.status_label.setText(f"✅ {message}")
                    self.env_created.emit(name)
                    # Keep dialog open so user can see commands. Cancel → Close.
                    self.cancel_btn.setText("Close")
                else:
                    banner_error(f"Could not create '{name}'", details=[str(message)])
                    self.status_label.setStyleSheet("color: #f38ba8; font-size: 15px; font-weight: bold;")
                    self.status_label.setText(f"❌ {message}")
                    self.cancel_btn.setText("Close")

            from src.gui.package_panel import WorkerThread
            self.worker = WorkerThread(_do_conda_create)
            self.worker.progress.connect(
                lambda msg: (self.progress_msg_label.setVisible(bool(msg)), self.progress_msg_label.setText(msg)))
            self.worker.finished.connect(_on_conda_done)
            self.worker.start()
            return

    def _create_alt_env(self, name, env_type):
        if env_type in ("uv", "poetry", "pipx"):
            import os, shutil as _shutil
            location = self.location_label.text()

            if env_type == "pipx":
                # pipx uses its own home dir — not the user-selected base dir
                from src.utils.platform_utils import get_pipx_home
                _pipx_home = get_pipx_home()
                if _pipx_home:
                    env_path = Path(_pipx_home)
                else:
                    # Default pipx home locations
                    if sys.platform == "win32":
                        _pipx_home = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "pipx")
                    else:
                        _pipx_home = os.path.join(os.path.expanduser("~"), ".local", "share", "pipx")
                    env_path = Path(_pipx_home)
                env_path.mkdir(parents=True, exist_ok=True)
            else:
                env_path = Path(os.path.join(location, name))

            python_path = self.python_combo.currentData() or None

            # ── Pre-check: is the required tool available? ────────────
            from src.core.tool_registry import ToolRegistry
            _registry = ToolRegistry()

            _tool_checks = {
                "uv":     ("uv",     "pip install uv"),
                "poetry": ("poetry", "pip install poetry"),
                "pipx":   ("pipx",   "pip install --user pipx"),
            }
            _tool_name, _tool_install = _tool_checks.get(env_type, ("", ""))

            # Use registry first, then shutil.which, then python -m
            _tool_path = _registry.find(_tool_name)
            _tool_found = bool(_tool_path)

            if not _tool_found and env_type in ("uv", "poetry", "pipx"):
                import sys as _sys, subprocess as _sp
                try:
                    _t = _sp.run(
                        [_sys.executable, "-m", _tool_name, "--version"],
                        capture_output=True, text=True, timeout=5
                    )
                    if _t.returncode == 0:
                        _tool_found = True
                        _ver = _t.stdout.strip().split()[-1] if _t.stdout.strip() else ""
                        _registry.register(_tool_name,
                                           f"python -m {_tool_name}",
                                           version=_ver,
                                           installed_by="python_module")
                except Exception:
                    pass

            if not _tool_found:
                _msg = (
                    f"'{_tool_name}' is not installed on your system.\n\n"
                    f"VenvStudio can try to install it automatically.\n"
                    f"Manual install: {_tool_install}\n\n"
                    f"Install '{_tool_name}' now?"
                )
                reply = QMessageBox.question(
                    self, f"{_tool_name} Not Found",
                    _msg,
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
            # ── End pre-check ─────────────────────────────────────────

            self.progress_bar.setVisible(True)
            self.create_btn.setEnabled(False)
            self.create_btn.setText("Creating...")
            self.name_input.setEnabled(False)
            self.env_type_combo.setEnabled(False)
            self.status_label.setStyleSheet("color: #89b4fa; font-size: 15px; font-weight: bold;")
            self.status_label.setText(f"⚙️ Creating {env_type} environment...")

            # Terminal banner — uv/poetry/pipx env creation start
            banner_start(
                f"Creating environment '{name}'",
                details=[
                    f"Type: {env_type}",
                    f"Python: {python_path or 'system default'}",
                    f"Location: {env_path}",
                ],
            )

            _env_path = env_path
            _python  = python_path
            _name    = name
            _etype   = env_type

            def _do_alt_create(callback=None):
                import subprocess, shutil, sys, json, datetime, re
                from src.utils.platform_utils import get_platform, subprocess_args
                plat = get_platform()

                # Route progress to BOTH the UI label (via callback) and the
                # terminal log. Without the log copy, poetry create steps
                # (version detection, requires-python relax, env use output)
                # were invisible when diagnosing why a picked Python was
                # ignored -- the whole point of adding them.
                try:
                    from src.utils.logger import get_logger as _gl_cr
                    _crlog = _gl_cr("venvstudio.create")
                except Exception:
                    _crlog = None

                def _cb(msg):
                    if callback:
                        callback(msg)
                    if _crlog is not None:
                        try:
                            _crlog.info(f"[{_etype}] {msg}")
                        except Exception:
                            pass
                    # Direct stdout so the step is visible even when the
                    # logger's console handler doesn't pick up worker-thread
                    # records. This is the line that makes create diagnosable.
                    try:
                        print(f"[CREATE:{_etype}] {msg}", flush=True)
                    except Exception:
                        pass

                # Registry for tracking tool paths
                from src.core.tool_registry import ToolRegistry
                _reg = ToolRegistry()

                def _find_tool_registered(name_):
                    """Find tool: registry → shutil.which → Scripts dir."""
                    # 1. Registry
                    reg_path = _reg.find(name_)
                    if reg_path and os.path.isfile(reg_path):
                        return reg_path
                    # 2. shutil.which
                    found = shutil.which(name_) or shutil.which(name_ + ".exe")
                    if found:
                        _reg.register(name_, found, installed_by="system")
                        return found
                    # 3. Scripts dir
                    scripts = os.path.join(os.path.dirname(sys.executable),
                        "Scripts" if sys.platform == "win32" else "bin")
                    for n in (name_, name_ + ".exe"):
                        cand = os.path.join(scripts, n)
                        if os.path.isfile(cand):
                            _reg.register(name_, cand, installed_by="system")
                            return cand
                    return None

                # _find_tool available for all env types
                def _find_tool(name_):
                    return _find_tool_registered(name_)

                if _etype == "uv":
                    # ── uv ───────────────────────────────────────────────
                    uv_exe = _find_tool("uv")
                    if not uv_exe:
                        _cb("Installing uv...")
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", "uv", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        uv_exe = _find_tool("uv")
                        if uv_exe:
                            _reg.register("uv", uv_exe, installed_by="venvstudio")
                        elif not uv_exe:
                            # Try python -m uv
                            t = subprocess.run([sys.executable, "-m", "uv", "--version"],
                                               capture_output=True, **subprocess_args())
                            if t.returncode == 0:
                                uv_exe = f"{sys.executable} -m uv"
                            else:
                                return False, "Could not install uv — try: pip install uv"

                    if " -m " in str(uv_exe):
                        cmd = uv_exe.split() + ["venv", str(_env_path)]
                    else:
                        cmd = [uv_exe, "venv", str(_env_path)]
                    if _python:
                        cmd += ["--python", _python]
                    _cb(f"$ {' '.join(cmd)}")
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=120, **subprocess_args())
                    if r.returncode != 0:
                        return False, r.stderr[:400] or "uv venv failed"
                    # Detect Python version in new env
                    _uv_pyver = ""
                    try:
                        if plat == "windows":
                            _uv_py = _env_path / "Scripts" / "python.exe"
                        else:
                            _uv_py = _env_path / "bin" / "python"
                        if _uv_py.exists():
                            _vr = subprocess.run(
                                [str(_uv_py), "--version"],
                                capture_output=True, text=True, timeout=5,
                                **subprocess_args()
                            )
                            _uv_pyver = (_vr.stdout.strip() or _vr.stderr.strip()
                                          ).replace("Python ", "")
                    except Exception:
                        pass
                    # Write marker
                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({"type": "uv", "name": _name,
                                   "python_version": _uv_pyver,
                                   "created": datetime.datetime.now().isoformat()}, f, indent=2)
                    _cb(f"✅ uv environment '{_name}' created!")
                    return True, f"uv environment '{_name}' created"

                elif _etype == "poetry":
                    # ── Poetry ───────────────────────────────────────────
                    poetry_exe = _find_tool("poetry")
                    if not poetry_exe:
                        _cb("Installing Poetry...")
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", "poetry", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        poetry_exe = _find_tool("poetry")
                        if poetry_exe:
                            _reg.register("poetry", poetry_exe, installed_by="venvstudio")
                        elif not poetry_exe:
                            return False, (
                                "Could not install Poetry automatically.\n\n"
                                "Install manually:\n"
                                "  pip install poetry\n\n"
                                "Or visit: https://python-poetry.org/docs/#installation"
                            )
                    _env_path.mkdir(parents=True, exist_ok=True)
                    cmd = [poetry_exe, "new", str(_env_path)]
                    _cb(f"$ {' '.join(cmd)}")
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=120, cwd=str(_env_path.parent),
                                       **subprocess_args())
                    if r.returncode != 0:
                        # poetry new fails if dir exists — try init
                        cmd2 = [poetry_exe, "init", "--no-interaction",
                                "--name", _name]
                        r2 = subprocess.run(cmd2, capture_output=True, text=True,
                                            timeout=60, cwd=str(_env_path),
                                            **subprocess_args())
                        if r2.returncode != 0:
                            return False, r.stderr[:400] or "poetry new failed"

                    # ── Honour the selected Python ───────────────────────
                    # `poetry new` writes a pyproject.toml whose
                    # requires-python is pinned to whatever Python ran poetry
                    # (the default). `poetry env use <picked>` is then REFUSED
                    # when the picked version is outside that range -- and
                    # Poetry returns exit 0 while doing nothing (verified: it
                    # prints "not supported by the project (>=3.x)" and rc=0).
                    # `poetry install` then builds the venv with the default.
                    # Fix: relax requires-python to admit the picked version
                    # BEFORE env use. This step is mandatory; if we cannot
                    # detect the picked version we relax to >=3.0 so nothing
                    # is refused.
                    _pyproject = _env_path / "pyproject.toml"

                    def _detect_pyver(py_path):
                        """Return 'X.Y' for a python executable, or ''.

                        Tries running it; if that fails (odd Windows launcher,
                        quoting, etc.) falls back to parsing the path, e.g.
                        'Python310\\python.exe' -> '3.10'.
                        """
                        import re as _re2
                        try:
                            _vr = subprocess.run(
                                [str(py_path), "-c",
                                 "import sys;print('%d.%d'%sys.version_info[:2])"],
                                capture_output=True, text=True, timeout=8,
                                **subprocess_args()
                            )
                            _o = (_vr.stdout or "").strip() or (_vr.stderr or "").strip()
                            _m = _re2.search(r"(\d+)\.(\d+)", _o)
                            if _m:
                                return f"{_m.group(1)}.{_m.group(2)}"
                        except Exception:
                            pass
                        # Fallback: parse version out of the path itself
                        _m2 = _re2.search(r"[Pp]ython[\\/]?(\d)\.?(\d{1,2})",
                                          str(py_path))
                        if _m2:
                            return f"{_m2.group(1)}.{_m2.group(2)}"
                        return ""

                    if _python:
                        _sel_xy = _detect_pyver(_python)
                        _cb(f"Selected Python resolves to version: "
                            f"{_sel_xy or 'UNKNOWN'} (from {_python})")
                        # Relax to the detected minor, or to >=3.0 if unknown,
                        # so `poetry env use` is never refused on constraint.
                        _new_req = f'>={_sel_xy}' if _sel_xy else '>=3.0'
                        if _pyproject.exists():
                            try:
                                _txt = _pyproject.read_text(encoding="utf-8")
                                # PEP 621: [project] requires-python = ">=3.x"
                                _txt2 = re.sub(
                                    r'(?m)^(\s*requires-python\s*=\s*)"[^"]*"',
                                    lambda m: m.group(1) + f'"{_new_req}"',
                                    _txt,
                                )
                                # Legacy [tool.poetry.dependencies] python="^3.x"
                                _txt2 = re.sub(
                                    r'(?m)^(\s*python\s*=\s*)"[^"]*"',
                                    lambda m: m.group(1) + f'"{_new_req}"',
                                    _txt2,
                                )
                                if _txt2 != _txt:
                                    _pyproject.write_text(_txt2, encoding="utf-8")
                                    _cb(f"Adjusted requires-python to {_new_req}")
                                else:
                                    _cb("⚠ requires-python line not found in "
                                        "pyproject.toml — env use may be refused")
                            except Exception as _e_req:
                                _cb(f"(Could not adjust requires-python: {_e_req})")

                        def _run_env_use():
                            _c = [poetry_exe, "env", "use", _python]
                            _cb(f"$ {' '.join(_c)}")
                            return subprocess.run(_c, capture_output=True,
                                                  text=True, timeout=60,
                                                  cwd=str(_env_path),
                                                  **subprocess_args())

                        _euse = _run_env_use()
                        _uout = ((_euse.stdout or "") + (_euse.stderr or "")).strip()
                        if _uout:
                            _cb(f"env use output: {_uout[:300]}")
                        # Poetry returns rc=0 even when it REFUSES (prints "not
                        # supported by the project"). Detect that text and, as a
                        # last resort, strip the constraint entirely and retry.
                        _refused = ("not supported by the project" in _uout.lower()
                                    or "loosen the python constraint" in _uout.lower())
                        if _refused and _pyproject.exists():
                            _cb("env use refused on constraint — removing "
                                "requires-python entirely and retrying")
                            try:
                                _txt = _pyproject.read_text(encoding="utf-8")
                                _txt = re.sub(
                                    r'(?m)^\s*requires-python\s*=\s*"[^"]*"\s*\r?\n',
                                    '', _txt)
                                _txt = re.sub(
                                    r'(?m)^\s*python\s*=\s*"[^"]*"',
                                    'python = ">=3.0"', _txt)
                                _pyproject.write_text(_txt, encoding="utf-8")
                            except Exception as _e2:
                                _cb(f"(constraint strip failed: {_e2})")
                            _euse = _run_env_use()
                            _uout2 = ((_euse.stdout or "") +
                                      (_euse.stderr or "")).strip()
                            if _uout2:
                                _cb(f"env use retry output: {_uout2[:300]}")
                        if _euse.returncode != 0:
                            _err = (_euse.stderr or _euse.stdout or "").strip()
                            _cb(f"⚠ poetry env use failed: {_err[:300]}")

                    # Run poetry install to actually create the venv
                    _cb("Running poetry install to create virtual environment...")
                    _inst = subprocess.run(
                        [poetry_exe, "install", "--no-root"],
                        capture_output=True, text=True, timeout=120,
                        cwd=str(_env_path), **subprocess_args()
                    )
                    if _inst.returncode != 0:
                        # No packages yet — still ok, venv should be created
                        _cb("(No packages yet — continuing...)")

                    # Get real venv path via poetry env info --path
                    _po_venv_path = None
                    try:
                        _einfo = subprocess.run(
                            [poetry_exe, "env", "info", "--path"],
                            capture_output=True, text=True, timeout=30,
                            cwd=str(_env_path), **subprocess_args()
                        )
                        _einfo_path = _einfo.stdout.strip()
                        if _einfo_path and Path(_einfo_path).exists():
                            _po_venv_path = _einfo_path
                            _cb(f"Poetry venv: {_po_venv_path}")
                    except Exception:
                        pass

                    # Detect Python version from real venv (the actual result,
                    # so a failed env-use shows the true version, not a wish)
                    _po_pyver = ""
                    try:
                        if _po_venv_path:
                            _po_py = (Path(_po_venv_path) /
                                      ("Scripts" if plat == "windows" else "bin") /
                                      ("python.exe" if plat == "windows" else "python"))
                        elif _python:
                            _po_py = Path(_python)
                        else:
                            _po_py = Path(shutil.which("python3") or shutil.which("python") or sys.executable)
                        if _po_py.exists():
                            _vr = subprocess.run(
                                [str(_po_py), "--version"],
                                capture_output=True, text=True, timeout=5,
                                **subprocess_args()
                            )
                            _po_pyver = (_vr.stdout.strip() or _vr.stderr.strip()
                                          ).replace("Python ", "")
                    except Exception:
                        pass

                    # Warn if the resulting Python is not what the user picked
                    if _python:
                        _want = _detect_pyver(_python)
                        if _want and _po_pyver and not _po_pyver.startswith(_want):
                            _cb(f"⚠ Requested Python {_want} but env uses "
                                f"{_po_pyver} — check requires-python in "
                                f"pyproject.toml")

                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({
                            "type": "poetry",
                            "name": _name,
                            "python_version": _po_pyver,
                            "poetry_venv_path": _po_venv_path or "",
                            "poetry_project_dir": str(_env_path),
                            "created": datetime.datetime.now().isoformat()
                        }, f, indent=2)
                    _cb(f"✅ Poetry environment '{_name}' created!")
                    return True, f"Poetry environment '{_name}' created"

                elif _etype == "pipx":
                    # ── pipx ─────────────────────────────────────────────
                    # Just create a marker folder — pipx apps are managed
                    # from Installed/Catalog tabs after env creation.
                    def _find_pipx():
                        # 1. shutil.which
                        found = shutil.which("pipx") or shutil.which("pipx.exe")
                        if found:
                            return found
                        # 2. Scripts/bin dir next to current python
                        import os
                        scripts = os.path.join(os.path.dirname(sys.executable),
                                               "Scripts" if sys.platform == "win32" else "bin")
                        for name_ in ("pipx", "pipx.exe"):
                            cand = os.path.join(scripts, name_)
                            if os.path.isfile(cand):
                                return cand
                        # 3. User base Scripts
                        import site
                        user_scripts = os.path.join(site.getusersitepackages(),
                                                     "..", "..", "Scripts" if sys.platform == "win32" else "bin")
                        for name_ in ("pipx", "pipx.exe"):
                            cand = os.path.normpath(os.path.join(user_scripts, name_))
                            if os.path.isfile(cand):
                                return cand
                        return None

                    # Ensure pipx is available on the system
                    pipx_exe = _find_pipx()
                    if not pipx_exe:
                        _cb("Installing pipx...")
                        r = subprocess.run(
                            [sys.executable, "-m", "pip", "install", "--user", "pipx", "-q"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        pipx_exe = _find_pipx()
                        if pipx_exe:
                            _reg.register("pipx", pipx_exe, installed_by="venvstudio")

                    if not pipx_exe:
                        # Test python -m pipx works
                        test = subprocess.run(
                            [sys.executable, "-m", "pipx", "--version"],
                            capture_output=True, text=True, **subprocess_args()
                        )
                        if test.returncode != 0:
                            return False, (
                                "Could not install pipx.\n\n"
                                "Install manually:\n  pip install pipx\n"
                                "Then: pipx ensurepath"
                            )

                    # Get Python version from selected Python
                    _pipx_python = _python or sys.executable
                    _pipx_pyver = ""
                    try:
                        _pv = subprocess.run(
                            [_pipx_python, "--version"],
                            capture_output=True, text=True, timeout=5,
                            **subprocess_args()
                        )
                        _pipx_pyver = (
                            _pv.stdout.strip() or _pv.stderr.strip()
                        ).replace("Python ", "")
                    except Exception:
                        pass

                    # Create marker inside pipx home (not a subdir per name)
                    _env_path.mkdir(parents=True, exist_ok=True)
                    with open(_env_path / ".venvstudio_env", "w") as f:
                        json.dump({
                            "type": "pipx",
                            "name": _name,
                            "python_version": _pipx_pyver,
                            "python_path": _pipx_python,
                            "created": datetime.datetime.now().isoformat(),
                        }, f, indent=2)

                    _cb(f"✅ pipx environment ready at {_env_path}")
                    return True, f"pipx environment '{_name}' ready"

                return False, f"Unknown env type: {_etype}"

            def _on_alt_done(success, message):
                self.progress_bar.setVisible(False)
                self.create_btn.setEnabled(True)
                self.create_btn.setText("Create Environment")
                self.name_input.setEnabled(True)
                self.env_type_combo.setEnabled(True)
                if success:
                    banner_success(
                        f"Environment '{_name}' is ready!",
                        details=[
                            f"Type: {_etype}",
                            f"Path: {_env_path}",
                        ],
                    )
                    self.status_label.setStyleSheet("color: #a6e3a1; font-size: 15px; font-weight: bold;")
                    self.status_label.setText(f"✅ {message}")
                    self.env_created.emit(_name)
                    # Keep dialog open so user can see commands. Cancel → Close.
                    self.cancel_btn.setText("Close")
                else:
                    banner_error(f"Could not create '{_name}'", details=[str(message)])
                    self.status_label.setStyleSheet("color: #f38ba8; font-size: 15px; font-weight: bold;")
                    self.status_label.setText(f"❌ Failed")
                    self.cancel_btn.setText("Close")

            from src.gui.package_panel import WorkerThread
            self.worker = WorkerThread(_do_alt_create)
            self.worker.progress.connect(lambda msg: (self.progress_msg_label.setVisible(bool(msg)), self.progress_msg_label.setText(msg)))
            self.worker.finished.connect(_on_alt_done)
            self.worker.start()
            return

    def _create_venv(self, name):
        python_path = self.python_combo.currentData() or None

        self.progress_bar.setVisible(True)
        self.create_btn.setEnabled(False)
        self.create_btn.setText("Creating...")
        self.name_input.setEnabled(False)
        self.python_combo.setEnabled(False)
        self.status_label.setStyleSheet("color: #89b4fa; font-size: 15px; font-weight: bold;")
        self.status_label.setText("⚙️ Initializing...")
        self.cancel_btn.setText("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setStyleSheet("")

        py_exe = python_path or "python"
        location = self.location_label.text()
        import os
        venv_path = os.path.join(location, name)

        from src.utils.platform_utils import get_platform
        def _c(t): return f"<span style='color:#89b4fa;font-family:Consolas,monospace;font-size:15px;'>{t}</span>"
        def _p(t): return f"<span style='color:#a6e3a1;font-family:Consolas,monospace;font-size:15px;'>{t}</span>"
        def _k(t): return f"<span style='color:#cba6f7;font-family:Consolas,monospace;font-weight:bold;font-size:15px;'>{t}</span>"
        def _ln(t): return f"<p style='margin:4px 0;font-size:15px;font-family:Consolas,monospace;color:#cdd6f4;background:#11111b;padding:4px 10px;border-radius:4px;'>{t}</p>"
        def _nt(t): return f"<p style='margin:10px 0 2px 0;font-size:12px;color:#6c7086;font-style:italic;'>{t}</p>"
        def _ttl(icon,txt,col): return f"<p style='font-size:20px;font-weight:bold;color:{col};margin:10px 0 6px 0;'>{icon}&nbsp; {txt}</p>"
        if get_platform() == "windows":
            activate_cmd = _ln(_p(venv_path + "\\Scripts\\Activate.ps1"))
            activate_note = _nt("Activate (Windows PowerShell):")
        else:
            activate_cmd = _ln(_c("source") + " " + _p(f"{venv_path}/bin/activate"))
            activate_note = _nt("Activate (Linux/macOS):")
        html = (
            _ttl("🐍", "Python venv", "#89b4fa") +
            _nt("Create virtual environment:") +
            _ln(_k("python") + " -m " + _c("venv") + " " + _p(venv_path)) +
            activate_note +
            activate_cmd +
            _nt("Upgrade pip:") +
            _ln(_c("pip") + " install --upgrade " + _k("pip")) +
            _nt("Install packages:") +
            _ln(_c("pip") + " install " + _k("numpy") + " " + _k("pandas")) +
            _nt("Save dependencies:") +
            _ln(_c("pip") + " freeze > " + _p("requirements.txt")) +
            _nt("Deactivate:") +
            _ln(_c("deactivate"))
        )
        self.cmd_label.setHtml(html)

        self.worker = CreateWorker(
            self.venv_manager, name, python_path,
            with_pip=True,
            system_site_packages=self.system_packages_cb.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

