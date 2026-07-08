"""VenvStudio - Env Create Dialog: Tools Mixin
Tool detection & installation for EnvCreateDialog (moved from env_dialog.py):
_find_tool_exe, _install_tool.
"""

# B151: suppress Windows console flash on all subprocess calls
try:
    from src.utils.platform_utils import subprocess_args
except Exception:
    def subprocess_args(**kw): return kw


class EnvDialogToolsMixin:
    """Mixin for EnvCreateDialog: uv/poetry/pipx tool detection & install."""

    @staticmethod
    def _find_tool_exe(tool: str) -> str:
        """Search for a tool executable in all known locations. Returns path or ''."""
        import shutil, os, sys, site

        candidates = []

        # 1. shutil.which (current PATH)
        for n in (tool, tool + ".exe"):
            w = shutil.which(n)
            if w:
                candidates.append(w)

        # 2. ToolRegistry
        try:
            from src.core.tool_registry import ToolRegistry
            rp = ToolRegistry().get_path(tool)
            if rp:
                candidates.append(rp)
        except Exception:
            pass

        # 3. User Scripts/bin (site.getuserbase)
        try:
            ub = site.getuserbase()
            scripts = os.path.join(ub,
                "Scripts" if sys.platform == "win32" else "bin")
            for n in (tool, tool + ".exe"):
                candidates.append(os.path.join(scripts, n))
        except Exception:
            pass

        # 4. Scripts next to sys.executable
        py_scripts = os.path.join(os.path.dirname(sys.executable),
            "Scripts" if sys.platform == "win32" else "bin")
        for n in (tool, tool + ".exe"):
            candidates.append(os.path.join(py_scripts, n))

        # 5. Windows: %APPDATA%\Python\PythonXY\Scripts
        if sys.platform == "win32":
            py_appdata = os.path.join(os.environ.get("APPDATA", ""), "Python")
            if os.path.isdir(py_appdata):
                for sub in os.listdir(py_appdata):
                    s = os.path.join(py_appdata, sub, "Scripts")
                    for n in (tool, tool + ".exe"):
                        candidates.append(os.path.join(s, n))

        # 6. Poetry official installer location (~/.local/share/pypoetry/bin/)
        if tool == "poetry":
            candidates.append(os.path.join(os.path.expanduser("~"),
                ".local", "share", "pypoetry", "bin", "poetry"))
            # Windows: %APPDATA%\pypoetry\bin\poetry.exe
            if sys.platform == "win32":
                candidates.append(os.path.join(
                    os.environ.get("APPDATA", ""), "pypoetry", "bin", "poetry.exe"))

        # 7. ~/.local/bin (common for curl-based installers on Linux)
        if sys.platform != "win32":
            candidates.append(os.path.join(
                os.path.expanduser("~"), ".local", "bin", tool))

        # 8. Cargo/rustup bin (~/.cargo/bin) — for tools installed via cargo
        candidates.append(os.path.join(
            os.path.expanduser("~"), ".cargo", "bin", tool))

        return next((c for c in candidates if c and os.path.isfile(c)), "")

    def _install_tool(self, scope: str = "user"):
        """Install the missing tool via pip — user install or system with UAC."""
        env_type = self.env_type_combo.currentData() if hasattr(self, "env_type_combo") else ""
        if not env_type:
            return
        import sys
        _pip_pkgs = {"uv": "uv", "poetry": "poetry", "pipx": "pipx"}
        pkg = _pip_pkgs.get(env_type, env_type)
        python_path = self.python_combo.currentData() or sys.executable

        # Disable both buttons while installing
        for btn_name in ("tool_install_user_btn", "tool_install_system_btn"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setEnabled(False)
        if hasattr(self, "tool_status_label"):
            self.tool_status_label.setText(
                f"⏳ Installing {env_type} ({'user' if scope == 'user' else 'system-wide'})...")
            self.tool_status_label.setStyleSheet("font-size: 11px; color: #89b4fa;")

        def _do_install(callback=None):
            import subprocess, shutil, os, site

            # ── Platform-aware install strategy ──────────────────────────
            # On Linux with PEP 668 (Debian/Ubuntu/Pardus), pip install is
            # blocked for system Python. Use official installers instead.
            def _is_externally_managed():
                try:
                    import sysconfig
                    stdlib = sysconfig.get_path("stdlib")
                    if stdlib and os.path.exists(os.path.join(stdlib, "EXTERNALLY-MANAGED")):
                        return True
                except Exception:
                    pass
                return False

            def _install_uv_linux(user_scope: bool):
                """Install uv: pacman → pip --break-system-packages → curl installer."""
                pm = _detect_pkg_manager() if '_detect_pkg_manager' in dir() else None
                # 1. pacman (Arch/CachyOS) — avoids cross-device move error
                if shutil.which("pacman"):
                    r = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "uv"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                # 2. pip --break-system-packages
                r = subprocess.run([python_path, "-m", "pip", "install", "uv",
                                    "--break-system-packages", "--user", "-q"],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode == 0: return True, ""
                # 3. curl official installer (last resort)
                try:
                    r = subprocess.run(
                        ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                        capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                    return False, r.stderr[:300]
                except Exception as e:
                    return False, str(e)

            def _install_poetry_linux(user_scope: bool):
                """Install poetry via official installer, fallback to pipx install poetry."""
                # Official installer works on all distros including Arch
                try:
                    r = subprocess.run(
                        ["sh", "-c", "curl -sSL https://install.python-poetry.org | python3 -"],
                        capture_output=True, text=True, timeout=180,
                        env={**os.environ, "POETRY_HOME": os.path.expanduser("~/.local/share/pypoetry")}
                    )
                    if r.returncode == 0:
                        return True, ""
                except Exception:
                    pass
                # Fallback: pipx install poetry (if pipx available)
                _pipx = shutil.which("pipx")
                if _pipx:
                    try:
                        r = subprocess.run([_pipx, "install", "poetry"],
                                           capture_output=True, text=True, timeout=180)
                        if r.returncode == 0:
                            return True, ""
                    except Exception:
                        pass
                # Last resort: pip --break-system-packages
                r = subprocess.run(
                    [python_path, "-m", "pip", "install", "poetry",
                     "--break-system-packages", "--user", "-q"],
                    capture_output=True, text=True, timeout=180)
                if r.returncode == 0:
                    return True, ""
                return False, r.stderr[:300]

            def _detect_pkg_manager():
                """Detect system package manager."""
                for pm in ("apt", "pacman", "dnf", "zypper", "emerge"):
                    if shutil.which(pm):
                        return pm
                return None

            def _install_pipx_linux(user_scope: bool):
                """Install pipx via system package manager or pip --break-system-packages."""
                pm = _detect_pkg_manager()
                if pm == "apt":
                    r = subprocess.run(["sudo", "apt", "install", "-y", "pipx"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                elif pm == "pacman":
                    # Arch/CachyOS/Manjaro — python-pipx is in official repos
                    r = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "python-pipx"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                elif pm == "dnf":
                    r = subprocess.run(["sudo", "dnf", "install", "-y", "pipx"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                elif pm == "zypper":
                    r = subprocess.run(["sudo", "zypper", "install", "-y", "python3-pipx"],
                                       capture_output=True, text=True, timeout=120)
                    if r.returncode == 0: return True, ""
                # Fallback: pip with --break-system-packages
                cmd = [python_path, "-m", "pip", "install", "pipx",
                       "--break-system-packages", "--user", "-q"]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r.returncode == 0: return True, ""
                return False, r.stderr[:300]

            if scope == "system":
                if sys.platform == "win32":
                    try:
                        import ctypes
                        args = f'-m pip install {pkg} -q'
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", python_path, args, None, 1)
                        if ret <= 32:
                            return False, f"UAC elevation failed (code {ret})"
                        import time; time.sleep(4)
                    except Exception as e:
                        return False, f"UAC error: {e}"
                else:
                    # Linux/macOS system install
                    if _is_externally_managed():
                        # PEP 668 — use official installers
                        if env_type == "uv":
                            ok, err = _install_uv_linux(False)
                            if not ok:
                                return False, f"uv install failed: {err}"
                        elif env_type == "poetry":
                            ok, err = _install_poetry_linux(False)
                            if not ok:
                                return False, f"poetry install failed: {err}"
                        elif env_type == "pipx":
                            ok, err = _install_pipx_linux(False)
                            if not ok:
                                return False, f"pipx install failed: {err}"
                        else:
                            r = subprocess.run(
                                ["sudo", python_path, "-m", "pip", "install", pkg,
                                 "--break-system-packages", "-q"],
                                **subprocess_args(capture_output=True, text=True, timeout=120))
                            if r.returncode != 0:
                                return False, (r.stderr or r.stdout or "install failed")[:200]
                    else:
                        r = subprocess.run(
                            ["sudo", python_path, "-m", "pip", "install", pkg, "-q"],
                            **subprocess_args(capture_output=True, text=True, timeout=120))
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "sudo install failed")[:200]
            else:
                # User install
                if sys.platform != "win32" and _is_externally_managed():
                    # PEP 668 — use official installers
                    if env_type == "uv":
                        ok, err = _install_uv_linux(True)
                        if not ok:
                            return False, f"uv install failed: {err}"
                    elif env_type == "poetry":
                        ok, err = _install_poetry_linux(True)
                        if not ok:
                            return False, f"poetry install failed: {err}"
                    elif env_type == "pipx":
                        ok, err = _install_pipx_linux(True)
                        if not ok:
                            return False, f"pipx install failed: {err}"
                    else:
                        r = subprocess.run(
                            [python_path, "-m", "pip", "install", pkg,
                             "--break-system-packages", "--user", "-q"],
                            **subprocess_args(capture_output=True, text=True, timeout=120))
                        if r.returncode != 0:
                            return False, (r.stderr or r.stdout or "pip install failed")[:200]
                else:
                    r = subprocess.run(
                        [python_path, "-m", "pip", "install", pkg, "--user", "-q"],
                        **subprocess_args(capture_output=True, text=True, timeout=120))
                    if r.returncode != 0:
                        return False, (r.stderr or r.stdout or "pip install failed")[:200]

            # For pipx: run ensurepath to register Scripts dir
            if env_type == "pipx":
                try:
                    subprocess.run(
                        [python_path, "-m", "pipx", "ensurepath"],
                        capture_output=True, text=True, timeout=30)
                except Exception:
                    pass

            # Use shared search helper (covers PATH, registry, APPDATA)
            found = EnvCreateDialog._find_tool_exe(env_type)
            if found:
                return True, found
            return False, (
                f"{env_type} installed but not found in PATH.\n"
                f"Run: python -m {env_type} ensurepath (if supported)\n"
                f"Then restart VenvStudio."
            )


        def _on_done(success, result):
            if success:
                if hasattr(self, "tool_status_label"):
                    self.tool_status_label.setText(f"✅ {env_type} installed")
                    self.tool_status_label.setStyleSheet("font-size: 11px; color: #a6e3a1;")
                for btn_name in ("tool_install_user_btn", "tool_install_system_btn"):
                    btn = getattr(self, btn_name, None)
                    if btn:
                        btn.setVisible(False)
                try:
                    from src.core.tool_registry import ToolRegistry
                    ToolRegistry().register(env_type, result, installed_by="venvstudio")
                except Exception:
                    pass
            else:
                if hasattr(self, "tool_status_label"):
                    self.tool_status_label.setText(f"❌ {result}")
                    self.tool_status_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
                for btn_name in ("tool_install_user_btn", "tool_install_system_btn"):
                    btn = getattr(self, btn_name, None)
                    if btn:
                        btn.setEnabled(True)

        from src.gui.package_panel import WorkerThread
        _w = WorkerThread(_do_install)
        _w.finished.connect(_on_done)
        _w.start()
        self._install_worker = _w

