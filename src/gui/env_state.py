"""VenvStudio - Package Panel: Environment State Mixin
set_venv, env-type tab switching, env selector, size calc, async package
loading (moved from package_panel.py). This is the core "which env am I
showing" logic — the riskiest part of this split.
"""
from src.core.venv_manager_common import _fmt_path
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt, QThread, Signal

from src.core.pip_manager import PipManager
from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.gui.package_panel_common import _EnvSizeWorker


class EnvStateMixin:
    """Mixin for PackagePanel: environment state (set_venv, tab switching, selector, size calc)."""

    def set_venv(self, venv_path: Path):
        # B175 perf fix: skip the entire reload if the same env is selected again.
        try:
            _prev = getattr(self, "_current_venv_path", None)
            if _prev is not None and Path(_prev) == Path(venv_path):
                return
        except Exception:
            pass

        backend = "pip"
        try:
            from src.core.config_manager import ConfigManager
            backend = self._get_config("package_manager", "pip")
        except Exception:
            pass

        # Detect env type from marker FIRST — needed to choose backend
        self._current_env_type = "venv"  # default
        marker = venv_path / ".venvstudio_env"
        if marker.exists():
            try:
                import json as _json
                with open(marker) as f:
                    _m = _json.load(f)
                # Backwards-compat: older pipx-tracker markers wrote the
                # field as "env_type" instead of "type"; honour both so an
                # existing on-disk marker keeps working without manual fix.
                self._current_env_type = (
                    _m.get("type")
                    or _m.get("env_type")
                    or "system_tools"
                )
            except Exception:
                self._current_env_type = "system_tools"
        else:
            # No marker — check if this is a poetry venv (inside pypoetry cache)
            _vp_str = str(venv_path)
            if "pypoetry" in _vp_str and "virtualenvs" in _vp_str:
                self._current_env_type = "poetry"
            elif "pipx" in _vp_str:
                self._current_env_type = "pipx"

        try:
            self._update_terminal_tooltip()
        except Exception:
            pass

        # Override backend based on env type
        if self._current_env_type == "uv":
            backend = "uv"
        elif self._current_env_type == "poetry":
            backend = "poetry"
        elif self._current_env_type == "conda":
            backend = "conda"
        elif self._current_env_type == "pipx":
            backend = "pipx"

        # B182 follow-up: remember the active backend so post-install
        # callbacks can refresh the env info bar without guessing.
        self._current_backend = backend

        self.pip_manager = PipManager(venv_path, backend=backend)
        self._current_venv_path = venv_path
        # Inject shared cache dir if enabled (pip/uv only)
        if self.pip_manager and self._current_env_type in ("venv", "uv"):
            try:
                _cfg = getattr(self, "config", None)
                if _cfg and _cfg.get("shared_cache_enabled", False):
                    from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
                    _cp = _cfg.get("shared_cache_dir", "") or DEFAULT_SHARED_CACHE_DIR
                    self.pip_manager._shared_cache_dir = _cp
            except Exception:
                pass

        if hasattr(self, "_env_bar_terminal_btn"):
            self._env_bar_terminal_btn.setEnabled(True)
        # Select in dropdown
        name = venv_path.name
        idx = self.env_selector.findData(str(venv_path))
        if idx < 0:
            self.env_selector.addItem(name, str(venv_path))
            idx = self.env_selector.count() - 1
        self.env_selector.blockSignals(True)
        self.env_selector.setCurrentIndex(idx)
        self.env_selector.blockSignals(False)
        self.status_label.setText(f"Loading packages for {name}...")
        self._update_env_info_bar(venv_path, backend)
        self._update_tabs_for_env_type()

        # ── Fast path: if cache exists, populate instantly before async ──
        cached = self._load_pkg_cache()
        if cached is not None:
            self.installed_package_names = set()
            for p in cached:
                n = p["name"].lower()
                self.installed_package_names.add(n)
                self.installed_package_names.add(n.replace("-", "_"))
                self.installed_package_names.add(n.replace("_", "-"))
            self._update_launcher_status()   # show installed/not-installed instantly
            self.pkg_count_label.setText(f"{len(cached)} packages")
            self.env_pkg_count.setText(f"{len(cached)} packages installed")
            self.status_label.setText(f"Environment: {name}")

        # Async refresh (updates if cache stale, runs pip list in background)
        self._async_refresh_packages()

    def _update_tabs_for_env_type(self):
        """
        Show/hide tabs based on current env type using removeTab/insertTab.
        All env types get full tabs except system_tools (launcher + manual).
        """
        if not hasattr(self, "_tab_defs"):
            return
        # Ensure visible tabs are built
        current = self.tabs.currentIndex()
        if current >= 0:
            self._ensure_tab_built(current)

        env_type = getattr(self, "_current_env_type", "venv")

        # Update manual tab description and placeholder per env type
        if True:
            _manual_descriptions = {
                "venv":   "Enter package names separated by spaces or newlines.\nYou can specify versions like: numpy==1.24.0 or pandas>=2.0",
                "uv":    "Enter package names separated by spaces or newlines.\nUses uv pip install (10-100× faster than pip).",
                "poetry": "Enter package names to add.\nUses poetry add command.",
                "conda":  "Enter package names separated by spaces or newlines.\nPackages will be installed from conda-forge.",
                "pipx":   "Enter CLI app names to install globally.\nEach app gets its own isolated environment via pipx.",
            }
            _manual_placeholders = {
                "venv":   "numpy pandas matplotlib\nscikit-learn==1.3.0\nrequests>=2.28",
                "uv":     "numpy pandas matplotlib\nscikit-learn==1.3.0",
                "poetry": "numpy pandas matplotlib",
                "conda":  "numpy pandas matplotlib\nscipy r-base",
                "pipx":   "httpie black ruff poetry cowsay",
            }
            self.manual_info_label.setText(_manual_descriptions.get(env_type, _manual_descriptions["venv"]))
            self.manual_input.setPlaceholderText(_manual_placeholders.get(env_type, _manual_placeholders["venv"]))

        # Which tab keys should be visible?
        visible_keys = {
            "venv":         {"launcher", "installed", "catalog", "presets", "manual"},
            "uv":           {"launcher", "installed", "catalog", "presets", "manual"},
            "poetry":       {"launcher", "installed", "catalog", "presets", "manual"},
            "conda":        {"launcher", "installed", "catalog", "presets", "manual"},
            "pipx":         {"launcher", "installed", "catalog", "presets", "manual"},
        }.get(env_type, {"launcher", "installed", "catalog", "presets", "manual"})

        # Remember current tab key before we remove tabs
        cur_widget = self.tabs.currentWidget()
        cur_key = None
        for key, label, widget, tooltip in self._tab_defs:
            if widget is cur_widget:
                cur_key = key
                break

        # Block signals to prevent feedback loops
        self.tabs.blockSignals(True)

        # Remove all tabs (widgets are kept alive, just removed from tab bar)
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)

        # Re-add only visible tabs in original order with env-type-aware tooltips
        _manual_tooltips = {
            "venv":   "📝 Manually install packages by name.\nYou can paste from pip install commands.",
            "uv":     "📝 Manually install packages by name.\nUses uv pip install (10-100× faster).",
            "poetry": "📝 Manually add packages.\nUses poetry add command.",
            "conda":  "📝 Manually install packages by name.\nUses conda install command.",
            "pipx":   "📝 Install CLI apps by name.\nUses pipx install command.",
        }
        _installed_tooltips = {
            "venv":   "📦 View and manage installed pip packages.",
            "uv":     "📦 View and manage installed packages (uv backend).",
            "poetry": "📦 View installed packages (Poetry environment).",
            "conda":  "📦 View installed conda packages.",
        }
        _catalog_tooltips = {
            "conda":  "🛒 Browse popular packages.\nInstalls via conda-forge channel.",
        }
        for key, label, widget, tooltip in self._tab_defs:
            if key in visible_keys:
                # Override tooltip for env-type awareness
                if key == "manual":
                    tooltip = _manual_tooltips.get(env_type, tooltip)
                elif key == "installed":
                    tooltip = _installed_tooltips.get(env_type, tooltip)
                elif key == "catalog":
                    tooltip = _catalog_tooltips.get(env_type, tooltip)
                # Build widget lazily if not yet created
                if widget is None:
                    tab_index = next((i for i, d in enumerate(self._tab_defs) if d[0] == key), -1)
                    if tab_index >= 0:
                        self._ensure_tab_built(tab_index)
                        widget = self._tab_defs[tab_index][2]
                if widget is not None:
                    idx = self.tabs.addTab(widget, label)
                    self.tabs.setTabToolTip(idx, tooltip)

        self.tabs.blockSignals(False)

        # Restore current tab if still visible, else go to Launch
        restored = False
        if cur_key and cur_key in visible_keys:
            for i, (key, label, widget, tooltip) in enumerate(self._tab_defs):
                if key == cur_key and key in visible_keys:
                    # Find its actual index in the new tab order
                    for j in range(self.tabs.count()):
                        if self.tabs.widget(j) is widget:
                            self.tabs.setCurrentIndex(j)
                            restored = True
                            break
                    break
        if not restored:
            self.tabs.setCurrentIndex(0)

        # Installed tab toolbar: disable pip-only actions for non-pip envs
        is_pip_like = env_type in ("venv", "uv", "poetry")
        if hasattr(self, "update_btn"):
            self.update_btn.setEnabled(is_pip_like)
            self.update_btn.setToolTip(
                "" if is_pip_like else f"Not available for {env_type} environments"
            )
        if hasattr(self, "uninstall_btn"):
            self.uninstall_btn.setEnabled(is_pip_like)
            self.uninstall_btn.setToolTip(
                "" if is_pip_like else f"Not available for {env_type} environments"
            )

        # Rebuild launcher grid — remove gaps from hidden cards
        if hasattr(self, "launcher_cards") and hasattr(self, "launcher_grid"):
            # Collect visible apps for this env type
            # pip-based env types share the same launcher apps as venv.
            # conda envs ship pip AND conda-forge carries these apps, so
            # they get the pip cards PLUS the conda-only system apps —
            # previously conda showed only 6 cards while Quick Launch
            # correctly listed pip apps installed in the env.
            if env_type in ("uv", "poetry", "pipx"):
                _match = {"venv"}
            elif env_type == "conda":
                _match = {"venv", "conda"}
            else:
                _match = {env_type}
            visible_apps = [
                app for app in self.app_definitions
                if _match & set(app.get("env_types",
                    ["venv"] if not app.get("system_app")
                    else ["conda", "system_tools"]))
            ]

            # Hide all cards first
            for card in self.launcher_cards.values():
                card.setVisible(False)
                self.launcher_grid.removeWidget(card)

            # Re-add only visible cards in order (no gaps)
            col_count = 3
            for idx, app in enumerate(visible_apps):
                card = self.launcher_cards.get(app["name"])
                if card:
                    row, col = divmod(idx, col_count)
                    self.launcher_grid.addWidget(card, row, col)
                    card.setVisible(True)

        # Keep the Quick Launch sidebar in sync with the newly built grid
        # (previously it only refreshed via the card-status path, so an env
        # switch alone never updated it — conda apps stayed invisible).
        try:
            self._update_quick_sidebar()
        except Exception:
            pass

        # Update preset copy button tooltips for current env type
        _cmd_prefixes = {
            "venv":   "pip install",
            "uv":     "uv pip install",
            "poetry": "poetry add",
            "conda":  "conda install",
            "pipx":   "pipx install",
        }
        _prefix = _cmd_prefixes.get(env_type, "pip install")
        if hasattr(self, "_preset_cards"):
            for pname, pdata in self._preset_cards.items():
                copy_btn = pdata.get("copy_btn")
                if copy_btn and hasattr(copy_btn, "_preset_packages"):
                    _pkgs = copy_btn._preset_packages
                    _cmd = f"{_prefix} {' '.join(_pkgs)}"
                    copy_btn.setToolTip(
                        f"<p style='font-size:14px; font-weight:bold; color:#a6e3a1;'>"
                        f"💡 Equivalent terminal command:</p>"
                        f"<p style='font-size:16px; font-family:Consolas,monospace; color:#cdd6f4; "
                        f"background-color:#1e1e2e; padding:8px; border-radius:4px;'>"
                        f"{_cmd}</p>"
                        f"<p style='font-size:11px; color:#6c7086;'>Click to copy to clipboard</p>"
                    )

    def populate_env_list(self, env_list):
        """Populate the environment dropdown from main window."""
        self.env_selector.blockSignals(True)
        current_data = self.env_selector.currentData()
        self.env_selector.clear()
        self.env_selector.addItem(tr("select_environment"), "")
        for name, path in env_list:
            self.env_selector.addItem(name, str(path))

        # Restore previous selection or auto-select first env
        restored = False
        if current_data:
            idx = self.env_selector.findData(current_data)
            if idx >= 0:
                self.env_selector.setCurrentIndex(idx)
                restored = True
            else:
                # Previously selected env was deleted — clear state safely
                self._safe_clear_env_state()

        if not restored and self.env_selector.count() > 1:
            self.env_selector.setCurrentIndex(1)
        elif not restored:
            self.env_selector.setCurrentIndex(0)

        self.env_selector.blockSignals(False)

        # Always trigger load for selected env
        current_idx = self.env_selector.currentIndex()
        if current_idx > 0:
            self._on_env_selector_changed(current_idx)
        else:
            self._safe_clear_env_state()

    def _safe_clear_env_state(self):
        """Safely clear all env-related state when no env is selected or env was deleted."""
        # Stop any running loader thread first
        self._retire_pkg_loader()

        self.pip_manager = None
        self.installed_package_names = set()
        self._launcher_py_version_cache.clear()
        if hasattr(self, "packages_table"):
            self.packages_table.setRowCount(0)
        if hasattr(self, "pkg_count_label"):
            self.pkg_count_label.setText("0 packages")
        if hasattr(self, "env_pkg_count"):
            self.env_pkg_count.setText("")
        if hasattr(self, "python_version_label"):
            self.python_version_label.setText("")
        if hasattr(self, "_env_bar_terminal_btn"):
            self._env_bar_terminal_btn.setEnabled(False)
        self.status_label.setText("Select an environment to manage packages")
        self._hide_env_info_bar()

    def _on_env_selector_changed(self, index):
        """Handle env dropdown change."""
        path_str = self.env_selector.currentData()
        if path_str:
            backend = "pip"
            try:
                from src.core.config_manager import ConfigManager
                backend = self._get_config("package_manager", "pip")
            except Exception:
                pass
            venv_path = Path(path_str)
            self._current_venv_path = venv_path

            # Detect env type from marker — same as set_venv
            self._current_env_type = "venv"
            marker = venv_path / ".venvstudio_env"
            if marker.exists():
                try:
                    import json as _json
                    with open(marker) as f:
                        _m = _json.load(f)
                    # Backwards-compat: see _set_venv comment above —
                    # accept both "type" and the older "env_type" key.
                    self._current_env_type = (
                        _m.get("type")
                        or _m.get("env_type")
                        or "system_tools"
                    )
                except Exception:
                    self._current_env_type = "system_tools"
            else:
                _vp_str = str(venv_path)
                if "pypoetry" in _vp_str and "virtualenvs" in _vp_str:
                    self._current_env_type = "poetry"
                elif "pipx" in _vp_str:
                    self._current_env_type = "pipx"

            # Override backend based on env type
            if self._current_env_type == "uv":
                backend = "uv"
            elif self._current_env_type == "poetry":
                backend = "poetry"
            elif self._current_env_type == "conda":
                backend = "conda"
            elif self._current_env_type == "pipx":
                backend = "pipx"

            self.pip_manager = PipManager(venv_path, backend=backend)
            # B182 follow-up: remember the active backend so post-install
            # callbacks can refresh the env info bar without guessing.
            self._current_backend = backend

            # Inject shared cache dir if enabled (pip/uv only)
            if self.pip_manager and self._current_env_type in ("venv", "uv"):
                try:
                    _cfg = getattr(self, "config", None)
                    if _cfg and _cfg.get("shared_cache_enabled", False):
                        from src.utils.constants import DEFAULT_SHARED_CACHE_DIR
                        _cp = _cfg.get("shared_cache_dir", "") or DEFAULT_SHARED_CACHE_DIR
                        self.pip_manager._shared_cache_dir = _cp
                except Exception:
                    pass

            # B182 fix: previously the rest of this method (info bar update,
            # tabs refresh, async pkg load, QL callback) was nested inside
            # the "venv/uv only" if-block above, so poetry/pipx/conda envs
            # silently skipped it — leaving the info bar (path, size,
            # backend, last_used) blank in the UI when those envs were
            # selected from the dropdown. Move it back out to the common
            # path.
            if hasattr(self, "_env_bar_terminal_btn"):
                self._env_bar_terminal_btn.setEnabled(True)
            self.status_label.setText("Loading packages...")
            self._update_env_info_bar(venv_path, backend)
            self._update_tabs_for_env_type()
            # Notify main window to sync QL selector immediately
            if hasattr(self, "_ql_env_changed_callback") and callable(self._ql_env_changed_callback):
                self._ql_env_changed_callback(venv_path.name)
            self._async_refresh_packages()
        else:
            self._safe_clear_env_state()

    def _update_env_info_bar(self, venv_path, backend="pip"):
        """Update all info labels for the selected environment — uses cache."""
        # Show info labels
        for lbl in self._info_labels:
            lbl.setVisible(True)

        # Try cache first for python version and size
        python_ver = ""
        size_str = ""
        try:
            from src.core.venv_manager import VenvManager
            from src.core.config_manager import ConfigManager
            vm = self._get_venv_manager()
            cached = vm._read_cache(venv_path)
            if cached:
                python_ver = cached.get("python_version", "")
                size_str = cached.get("size", "")
        except Exception:
            pass

        # 1) Python version — from cache, marker, or subprocess
        if python_ver:
            self.python_version_label.setText(f"🐍 Python {python_ver}")
        else:
            # Try marker first (for pipx, conda, system_tools envs)
            _marker_pyver = ""
            _marker_file = venv_path / ".venvstudio_env"
            if _marker_file.exists():
                try:
                    import json as _json
                    with open(_marker_file) as _mf:
                        _mdata = _json.load(_mf)
                    _marker_pyver = _mdata.get("python_version", "")
                except Exception:
                    pass
            if _marker_pyver:
                self.python_version_label.setText(f"🐍 Python {_marker_pyver}")
            else:
                try:
                    python_exe = get_python_executable(venv_path)
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        capture_output=True, text=True, timeout=10,
                        **subprocess_args()
                    )
                    ver_text = result.stdout.strip() or result.stderr.strip()
                    self.python_version_label.setText(f"🐍 {ver_text}")
                except Exception:
                    # Last fallback: system Python
                    try:
                        import sys as _sys
                        result = subprocess.run(
                            [_sys.executable, "--version"],
                            capture_output=True, text=True, timeout=5,
                            **subprocess_args()
                        )
                        ver_text = result.stdout.strip() or result.stderr.strip()
                        self.python_version_label.setText(f"🐍 {ver_text}")
                    except Exception:
                        self.python_version_label.setText("")

        # 2) Shortened path
        try:
            full_path = str(venv_path)
            home = str(Path.home())
            if full_path.startswith(home):
                display_path = "~" + full_path[len(home):]
            else:
                display_path = full_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.env_path_label.setText(f"📂 {display_path}")
            self.env_path_label.setToolTip(full_path)
        except Exception:
            self.env_path_label.setText("")

        # 3) Disk size — from cache or calculate
        # B-conda-size: "N/A", "?", "..." are sentinel values for "size
        # could not be computed" (typically conda envs where the env
        # symlink target wasn't walkable). Treat them as missing so we
        # try the async calculation again instead of leaving N/A on screen
        # for ever.
        _bad_sizes = {"N/A", "n/a", "?", "...", "…", "0 MB", "0 B"}
        if size_str and size_str.strip() not in _bad_sizes:
            self.env_disk_label.setText(f"💾 {size_str}")
        else:
            # B175 perf fix: never run os.walk on the UI thread.
            self.env_disk_label.setText("💾 …")
            self._start_size_calc_async(venv_path)

        # 4) Backend (pip/uv/conda/poetry/pipx)
        _env_type = getattr(self, "_current_env_type", "venv")
        _backend_names = {
            "venv": backend.upper() if backend else "PIP",
            "uv": "UV",
            "poetry": "Poetry",
            "pipx": "pipx",
            "conda": "Conda",
        }
        backend_display = _backend_names.get(_env_type, backend.upper() if backend else "PIP")
        self.env_backend_label.setText(f"⚙️ {backend_display}")

        # 5) Last used (modification time of pyvenv.cfg or activate script)
        try:
            candidates = [
                venv_path / "pyvenv.cfg",
                venv_path / "Scripts" / "activate.bat",
                venv_path / "bin" / "activate",
                venv_path / "conda-meta" / "history",
            ]
            latest_mtime = 0
            for c in candidates:
                if c.exists():
                    mt = c.stat().st_mtime
                    if mt > latest_mtime:
                        latest_mtime = mt
            if latest_mtime > 0:
                from datetime import datetime
                dt = datetime.fromtimestamp(latest_mtime)
                self.env_last_used_label.setText(f"🕐 {dt.strftime('%Y-%m-%d %H:%M')}")
            else:
                # Fallback: use marker created date (e.g. pipx has no activate/pyvenv.cfg)
                _marker = venv_path / ".venvstudio_env"
                _created = ""
                if _marker.exists():
                    try:
                        import json as _j
                        _created = _j.loads(_marker.read_text()).get("created", "")
                    except Exception:
                        pass
                if not _created:
                    # For poetry venvs, use dir ctime
                    try:
                        from datetime import datetime
                        _created = datetime.fromtimestamp(venv_path.stat().st_ctime).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                if _created:
                    try:
                        from datetime import datetime
                        if "T" in _created:
                            dt = datetime.fromisoformat(_created)
                            _created = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                    self.env_last_used_label.setText(f"🕐 {_created}")
                else:
                    self.env_last_used_label.setText("")
                    self._info_sep3.setVisible(False)
        except Exception:
            self.env_last_used_label.setText("")
            self._info_sep3.setVisible(False)

    def _hide_env_info_bar(self):
        """Hide all info bar labels when no env is selected."""
        for lbl in self._info_labels:
            lbl.setVisible(False)

    # B175: background env-size calculation
    def _start_size_calc_async(self, venv_path):
        try:
            prev = getattr(self, "_size_worker", None)
            if prev is not None and prev.isRunning():
                try:
                    prev.done.disconnect()
                except Exception:
                    pass
                prev.requestInterruption()
                prev.quit()
                prev.wait(500)
            self._size_worker = _EnvSizeWorker(str(venv_path), parent=self)
            _expected = str(venv_path)

            def _on_size_done(path_str: str, size_str: str):
                cur = getattr(self, "_current_venv_path", None)
                if cur is not None and str(cur) != _expected:
                    return
                if size_str:
                    self.env_disk_label.setText(f"💾 {size_str}")
                    try:
                        from pathlib import Path as _P
                        vm = self._get_venv_manager()
                        all_cache = vm._load_all_cache()
                        key = vm._cache_key(_P(path_str))
                        entry = all_cache.get(key, {}) or {}
                        entry["size"] = size_str
                        all_cache[key] = entry
                        vm._save_all_cache(all_cache)
                    except Exception:
                        pass
                else:
                    self.env_disk_label.setText("💾 ?")

            self._size_worker.done.connect(_on_size_done)
            self._size_worker.start()
        except Exception:
            try:
                self.env_disk_label.setText("💾 ?")
            except Exception:
                pass

    def _retire_pkg_loader(self):
        """Detach the running package loader instead of killing it.

        Previously this called quit() + wait() + terminate(). Both steps were
        wrong for this worker:

        * quit() only unblocks a thread with a Qt event loop. PkgLoader has
          none -- it sits inside subprocess.run() -- so quit() was a no-op.
        * terminate() then killed the OS thread while it was suspended inside
          subprocess.communicate(), corrupting the interpreter state. That is
          the access violation seen in the crash log (<invalid frame> under
          micromamba_installer.list_conda_packages), reproduced by launching a
          pipx install while a slow conda package list was still running.

        The safe alternative: disconnect the signals, flag the loader as
        abandoned so it drops its result, and keep a reference so Python does
        not garbage-collect the QThread object while the OS thread is alive
        (a destroyed-while-running QThread is fatal on Windows). The loader
        removes itself from _retired_loaders when it finishes.
        """
        loader = getattr(self, "_pkg_loader", None)
        if loader is None:
            return
        self._pkg_loader = None
        try:
            loader.done.disconnect()
        except Exception:
            pass
        if not loader.isRunning():
            return
        try:
            loader.abandon()
        except Exception:
            pass
        if not hasattr(self, "_retired_loaders"):
            self._retired_loaders = []
        self._retired_loaders.append(loader)
        try:
            from src.utils.logger import get_logger
            get_logger("venvstudio.pkg_cache").debug(
                f"\U0001f4a4 [PkgCache] loader abandoned (still running, {len(self._retired_loaders)} pending)"
            )
        except Exception:
            pass

    def _on_pkg_loader_finished(self):
        """Drop references to loaders that have finished on their own."""
        retired = getattr(self, "_retired_loaders", None)
        if retired:
            self._retired_loaders = [t for t in retired if t.isRunning()]

    def _async_refresh_packages(self, force: bool = False):
        """Load packages — from cache if available, otherwise background subprocess."""
        if not self.pip_manager:
            return

        # Try cache first (unless force=True)
        if not force:
            cached = self._load_pkg_cache()
            if cached is not None:
                try:
                    from src.utils.logger import get_logger
                    get_logger("venvstudio.pkg_cache").debug(
                        f"✅ [PkgCache] HIT key={_fmt_path(self._get_pkg_cache_key())} count={len(cached)}"
                    )
                except Exception:
                    pass
                class _Pkg:
                    def __init__(self, name, version):
                        self.name = name
                        self.version = version
                pkgs = [_Pkg(p["name"], p["version"]) for p in cached]
                _hit_path = str(self.pip_manager.venv_path) if self.pip_manager.venv_path else ""
                self._on_packages_loaded(pkgs, _hit_path)
                return
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.pkg_cache").debug(
                    f"📦 [PkgCache] MISS key={_fmt_path(self._get_pkg_cache_key())} force={force} → starting pip list"
                )
            except Exception:
                pass

        # Cancel / wait for any previous loader to avoid QThread crash
        self._retire_pkg_loader()

        # Show loading state immediately
        self.packages_table.setRowCount(1)
        loading_item = QTableWidgetItem("Loading...")
        loading_item.setFlags(loading_item.flags() & ~Qt.ItemIsEditable)
        self.packages_table.setItem(0, 0, loading_item)
        self.packages_table.setItem(0, 1, QTableWidgetItem(""))
        self.pkg_count_label.setText("Loading...")
        self.env_pkg_count.setText("Loading packages...")

        # Capture pip_manager reference (env may change before thread finishes)
        pip_mgr_snapshot = self.pip_manager
        _env_type = getattr(self, "_current_env_type", "venv")
        _venv_path = self._current_venv_path if hasattr(self, "_current_venv_path") else None

        # Use QThread for background loading
        class PkgLoader(QThread):
            # B187: emit the venv_path snapshot alongside the package list
            # so the receiver can verify the result still belongs to the
            # currently-selected env. Without this, a slow `pip list` for
            # env A finishes after the user switched to env B and the
            # callback writes A's packages under B's cache key, causing the
            # preset badges and package count to lie about what is really
            # installed. The path is a plain string to keep the Qt signal
            # signature simple and avoid pickling Path objects.
            done = Signal(list, str)
            def __init__(self, pip_mgr, env_type, venv_path, parent=None):
                super().__init__(parent)
                self.pip_mgr = pip_mgr
                self.env_type = env_type
                self.venv_path = venv_path
                self._abandoned = False

            def abandon(self):
                """Mark this loader as stale.

                The thread is blocked inside subprocess.run() and has no Qt
                event loop, so quit() is a no-op and terminate() kills it in
                the middle of subprocess.communicate() -> access violation
                (crash log showed <invalid frame> in list_conda_packages).
                Instead we let it finish naturally and drop its result.
                """
                self._abandoned = True
            def run(self):
                _emit_path = str(self.venv_path) if self.venv_path else ""
                try:
                    if self.env_type == "conda" and self.venv_path:
                        from src.core.micromamba_installer import list_conda_packages
                        raw = list_conda_packages(self.venv_path)
                        class _Pkg:
                            def __init__(self, name, version):
                                self.name = name
                                self.version = version
                        pkgs = [_Pkg(p.get("name",""), p.get("version",""))
                                for p in raw]
                    elif self.env_type == "pipx":
                        # List globally installed pipx apps
                        import subprocess, sys, json as _json
                        from src.utils.platform_utils import subprocess_args
                        class _Pkg:
                            def __init__(self, name, version):
                                self.name = name
                                self.version = version
                        pkgs = []
                        try:
                            from src.utils.platform_utils import get_pipx_executable as _get_pipx
                            _pipx_exe = _get_pipx()
                            _pipx_cmd = [_pipx_exe, "list", "--json"] if _pipx_exe else [sys.executable, "-m", "pipx", "list", "--json"]
                            r = subprocess.run(
                                _pipx_cmd,
                                capture_output=True, text=True, timeout=30,
                                **subprocess_args()
                            )
                            if r.returncode == 0 and r.stdout.strip():
                                data = _json.loads(r.stdout)
                                venvs = data.get("venvs", {})
                                for pkg_name, info in venvs.items():
                                    meta = info.get("metadata", {})
                                    ver = meta.get("main_package", {}).get("package_version", "")
                                    pkgs.append(_Pkg(pkg_name, ver))
                        except Exception:
                            pass
                    else:
                        pkgs = self.pip_mgr.list_packages()
                    if not self._abandoned:
                        self.done.emit(pkgs, _emit_path)
                except Exception:
                    if not self._abandoned:
                        self.done.emit([], _emit_path)

        self._pkg_loader = PkgLoader(pip_mgr_snapshot, _env_type, _venv_path, parent=self)
        self._pkg_loader.done.connect(self._on_packages_loaded)
        self._pkg_loader.finished.connect(self._on_pkg_loader_finished)
        self._pkg_loader.start()


