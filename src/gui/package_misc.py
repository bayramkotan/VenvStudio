"""VenvStudio - Package Panel: Misc Mixin
Context menus, filters, PyPI info dialog, progress/finish callbacks,
outdated check, preset copy/uninstall, tab lifecycle (moved from
package_panel.py).
"""
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.gui.package_panel_common import WorkerThread


class PackageMiscMixin:
    """Mixin for PackagePanel: context menus, filters, info dialogs, misc callbacks."""

    def _pkg_table_context_menu(self, position):
        """Right-click context menu for packages table."""
        rows = self.packages_table.selectionModel().selectedRows()
        if not rows:
            return

        menu = QMenu(self)
        _env_type = getattr(self, "_current_env_type", "venv")
        _prefixes = {
            "venv": "pip install", "uv": "uv pip install",
            "poetry": "poetry add",
            "conda": "conda install", "pipx": "pipx install",
        }
        _prefix = _prefixes.get(_env_type, "pip install")

        # Gather selected package names
        selected_pkgs = []
        for idx in rows:
            item = self.packages_table.item(idx.row(), 0)
            ver_item = self.packages_table.item(idx.row(), 1)
            if item:
                pkg = item.text().strip()
                ver = ver_item.text().strip() if ver_item else ""
                selected_pkgs.append((pkg, ver))

        if len(selected_pkgs) == 1:
            pkg, ver = selected_pkgs[0]
            menu.addAction(f"ℹ️ Package Info", lambda: self._show_pip_info(pkg))
            menu.addSeparator()
            menu.addAction(f"📋 Copy: {_prefix} {pkg}", lambda p=pkg: self._copy_to_clipboard(f"{_prefix} {p}"))
            menu.addAction(f"📋 Copy: {_prefix} {pkg}=={ver}", lambda p=pkg, v=ver: self._copy_to_clipboard(f"{_prefix} {p}=={v}"))
            menu.addSeparator()
            menu.addAction(f"📋 Copy package name", lambda: self._copy_to_clipboard(pkg))
            menu.addAction(f"🌐 Open on PyPI", lambda: self._open_pypi(pkg))
        else:
            names = " ".join(p for p, _ in selected_pkgs)
            menu.addAction(f"📋 Copy: {_prefix} {names}", lambda: self._copy_to_clipboard(f"{_prefix} {names}"))
            pinned = " ".join(f"{p}=={v}" for p, v in selected_pkgs if v)
            if pinned:
                menu.addAction(f"📋 Copy with versions", lambda: self._copy_to_clipboard(f"{_prefix} {pinned}"))

        menu.exec(self.packages_table.viewport().mapToGlobal(position))

    def _catalog_table_context_menu(self, position):
        """Right-click context menu for catalog table — same style as Installed."""
        row = self.catalog_table.rowAt(position.y())
        if row < 0:
            return

        pkg_item = self.catalog_table.item(row, 1)
        desc_item = self.catalog_table.item(row, 2)
        if not pkg_item:
            return

        pkg = pkg_item.text().strip()
        is_installed = pkg.lower() in self.installed_package_names

        menu = QMenu(self)
        _env_type = getattr(self, "_current_env_type", "venv")
        _prefixes = {
            "venv": "pip install", "uv": "uv pip install",
            "poetry": "poetry add",
            "conda": "conda install", "pipx": "pipx install",
        }
        _prefix = _prefixes.get(_env_type, "pip install")

        menu.addAction(f"ℹ️ Package Info", lambda: self._show_pip_info(pkg))
        if not is_installed:
            menu.addAction(f"⬇️ Install {pkg}", lambda: self._install_packages([pkg], hint_name=pkg))
        menu.addSeparator()
        menu.addAction(f"📋 Copy: {_prefix} {pkg}", lambda: self._copy_to_clipboard(f"{_prefix} {pkg}"))
        menu.addAction(f"📋 Copy package name", lambda: self._copy_to_clipboard(pkg))
        menu.addSeparator()
        menu.addAction(f"🌐 Open on PyPI", lambda: self._open_pypi(pkg))
        menu.exec(self.catalog_table.viewport().mapToGlobal(position))

    def _show_pip_info(self, pkg_name: str):
        """Show package info — pip show if installed, PyPI API if not."""
        if not self.pip_manager:
            return

        info_text = ""
        from_pypi = False

        # Try pip show first (installed packages)
        try:
            python_exe = get_python_executable(self.pip_manager.venv_path)
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "show", pkg_name],
                **subprocess_args(capture_output=True, text=True, timeout=10)
            )
            output = result.stdout.strip()
            if output and "WARNING" not in output.split("\n")[0]:
                info_text = output
        except Exception:
            pass

        # Not installed — fetch from PyPI JSON API
        if not info_text:
            from_pypi = True
            try:
                import socket, ssl, json as _json
                host = "pypi.org"
                path = f"/pypi/{pkg_name}/json"
                ctx = ssl.create_default_context()
                with socket.create_connection((host, 443), timeout=8) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        req = (
                            f"GET {path} HTTP/1.1\r\n"
                            f"Host: {host}\r\n"
                            f"User-Agent: VenvStudio\r\n"
                            f"Accept: application/json\r\n"
                            f"Connection: close\r\n\r\n"
                        )
                        ssock.sendall(req.encode("utf-8"))
                        chunks = []
                        while True:
                            chunk = ssock.recv(4096)
                            if not chunk:
                                break
                            chunks.append(chunk)
                raw = b"".join(chunks).decode("utf-8", errors="replace")
                body = raw.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in raw else raw
                data = _json.loads(body)
                info = data.get("info", {})
                deps = info.get("requires_dist") or []
                info_text = (
                    f"Name: {info.get('name', pkg_name)}\n"
                    f"Version: {info.get('version', '?')}\n"
                    f"Summary: {info.get('summary', '')}\n"
                    f"Author: {info.get('author', '') or info.get('author_email', '')}\n"
                    f"License: {info.get('license', '')}\n"
                    f"Home-page: {info.get('home_page', '') or info.get('project_url', '')}\n"
                    f"Requires-Python: {info.get('requires_python', '')}\n"
                    f"Requires-Dist: {', '.join(deps[:15])}"
                )
            except Exception:
                info_text = f"Name: {pkg_name}\nStatus: Not installed — could not fetch info from PyPI"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"📦 {pkg_name} — Package Info")
        dialog.setMinimumSize(520, 400)
        dialog.resize(600, 450)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)

        # Source indicator
        if from_pypi:
            source_lbl = QLabel("⚠️ Not installed — info fetched from PyPI")
            source_lbl.setStyleSheet(f"color: {self._c().get('warning', '#f9e2af')}; font-size: {self._c()['fs_tiny']}px; padding: 2px 0;")
            layout.addWidget(source_lbl)

        # Scrollable info area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"QFrame {{ background-color: {self._c()['card']}; border: 1px solid {self._c()['border']}; border-radius: 6px; padding: 4px; }}"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)

        pypi_url = None
        for line in info_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()

                display_val = val
                if len(val) > 200:
                    display_val = val[:200] + "…"

                row = QHBoxLayout()
                key_lbl = QLabel(f"{key}:")
                key_lbl.setFixedWidth(120)
                key_lbl.setStyleSheet(f"color: {self._c()['accent']}; font-weight: bold; font-size: {self._c()['fs_small']}px;")
                key_lbl.setAlignment(Qt.AlignTop)
                val_lbl = QLabel(display_val)
                val_lbl.setWordWrap(True)
                val_lbl.setStyleSheet(f"color: {self._c()['fg']}; font-size: {self._c()['fs_small']}px;")
                val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                if val != display_val:
                    val_lbl.setToolTip(val)
                row.addWidget(key_lbl)
                row.addWidget(val_lbl, 1)
                info_layout.addLayout(row)
                if key.lower() == "home-page" and val.startswith("http"):
                    pypi_url = val

        info_layout.addStretch()
        scroll.setWidget(info_frame)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        if from_pypi:
            install_btn = QPushButton(f"⬇️ Install")
            install_btn.setObjectName("success")
            install_btn.setToolTip(f"Install {pkg_name}")
            install_btn.clicked.connect(
                lambda: (dialog.accept(), self._install_packages([pkg_name], hint_name=pkg_name))
            )
            btn_row.addWidget(install_btn)
        if pypi_url:
            home_btn = QPushButton("🌐 Home")
            home_btn.setObjectName("secondary")
            home_btn.setToolTip("Open Homepage")
            home_btn.clicked.connect(lambda: __import__("webbrowser").open(pypi_url))
            btn_row.addWidget(home_btn)
        pypi_btn = QPushButton("📦 PyPI")
        pypi_btn.setObjectName("secondary")
        pypi_btn.setToolTip(f"Open {pkg_name} on PyPI")
        pypi_btn.clicked.connect(lambda: __import__("webbrowser").open(f"https://pypi.org/project/{pkg_name}/"))
        btn_row.addWidget(pypi_btn)
        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.setToolTip("Copy all info to clipboard")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(info_text))
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec()

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_label.setText(f"📋 Copied: {text}")

    def _open_pypi(self, package_name):
        """Open package page on PyPI."""
        import webbrowser
        webbrowser.open(f"https://pypi.org/project/{package_name}/")

    def _filter_installed(self, text: str):
        for row in range(self.packages_table.rowCount()):
            item = self.packages_table.item(row, 0)
            if item:
                match = text.lower() in item.text().lower()
                self.packages_table.setRowHidden(row, not match)

    # ── Helpers ──

    def _show_command_hint(self, title, command):
        """Show command hint in output log instead of blocking dialog."""
        if hasattr(self, "output_log"):
            self._append_log("\n💡 Equivalent command:")
            self._append_log(f"   {command}\n")

    def _on_progress(self, message: str):
        self.status_label.setText(message)
        self._append_log(message)

    def _on_install_finished(self, success: bool, message: str):
        self._set_busy(False)
        self._append_log(f"\n{'✅ Success' if success else '❌ Failed'}: {message[:500]}")

        # Log for debugging (especially EXE/AppImage builds)
        try:
            from src.utils.logger import get_logger
            log = get_logger("venvstudio.install")
            _kind = getattr(self, "_pkg_op_kind", "Install")
            if success:
                log.info(f"✅ [{_kind}] OK: {message[:200]}")
            else:
                log.warning(f"❌ [{_kind}] FAILED: {message[:500]}")
        except Exception:
            pass

        if success:
            self.status_label.setText("Operation completed successfully")
            # Invalidate all caches so next read is fresh
            self._invalidate_cache()
            self._invalidate_env_cache()
            # B182 follow-up: refresh the env info bar at the top of the
            # Packages page (size + package count badges). Without this
            # the header still shows the pre-install values until the
            # user navigates away and back.
            try:
                _cur_path = getattr(self, "_current_venv_path", None)
                _cur_backend = getattr(self, "_current_backend", "pip")
                if _cur_path:
                    self._update_env_info_bar(_cur_path, _cur_backend)
            except Exception:
                pass
            # B182 race fix: refresh_packages() runs subprocess async.
            # Emitting env_refresh_requested *now* would race with the
            # cache write in _on_packages_loaded — MainWindow would read
            # the OLD pkg count from cache. Set a flag instead so
            # _on_packages_loaded emits *after* the new count is saved.
            self._emit_env_refresh_after_load = True
            self.refresh_packages()
        else:
            if "cancelled" not in message.lower():
                # Friendly log message instead of popup
                if "no matching distribution" in message.lower() or "could not find" in message.lower():
                    self.status_label.setText("⚠️ Some packages could not be found on PyPI")
                    self._append_log(
                        "\n⚠️ Some packages could not be found on PyPI.\n"
                        "Please check the package names and try again.\n"
                        "You can search at: https://pypi.org"
                    )
                else:
                    self.status_label.setText("❌ Operation failed")
                    self._append_log(f"\n❌ {message[:500]}")
            else:
                self.status_label.setText("⛔ Operation cancelled")

    def _cancel_operation(self):
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Operation",
                "Are you sure you want to cancel the current operation?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.status_label.setText("⛔ Cancelling...")
                self.current_worker.cancel()
                if not self.current_worker.wait(3000):
                    self.current_worker.terminate()
                self._set_busy(False)
                self.status_label.setText("⛔ Operation cancelled")
                self._append_log("\n⛔ Operation cancelled by user")

    def _check_outdated(self):
        """Check for outdated packages and show update option."""
        if not self.pip_manager:
            return
        self._set_busy(True)
        self.status_label.setText("Checking for updates...")

        class OutdatedWorker(QThread):
            finished = Signal(list)
            def __init__(self, pip_mgr):
                super().__init__()
                self.pip_mgr = pip_mgr
            def run(self):
                outdated = self.pip_mgr.list_outdated()
                self.finished.emit(outdated)

        self._outdated_worker = OutdatedWorker(self.pip_manager)
        self._outdated_worker.finished.connect(self._on_outdated_result)
        self._outdated_worker.start()

    def _on_outdated_result(self, outdated):
        self._set_busy(False)
        if not outdated:
            self.status_label.setText(tr("no_updates"))
            QMessageBox.information(self, tr("updates"), tr("no_updates"))
            return

        self.status_label.setText(tr("outdated_packages").format(n=len(outdated)))

        msg = tr("outdated_packages").format(n=len(outdated)) + "\n\n"
        for pkg in outdated:
            msg += f"  {pkg.name}: {pkg.version} → {pkg.latest_version}\n"
        msg += f"\n{tr('update_all')}?"

        reply = QMessageBox.question(
            self, tr("updates"), msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            pkg_names = [p.name for p in outdated]
            self._set_busy(True)
            self.current_worker = WorkerThread(
                self.pip_manager.install_packages, pkg_names, upgrade=True
            )
            self.current_worker.progress.connect(self._on_progress)
            self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()

    def _copy_preset_command(self, packages):
        """Copy install command to clipboard (env-type-aware)."""
        _env_type = getattr(self, "_current_env_type", "venv")
        _cmd_prefixes = {
            "venv":   "pip install",
            "uv":     "uv pip install",
            "poetry": "poetry add",
            "conda":  "conda install",
            "pipx":   "pipx install",
        }
        _prefix = _cmd_prefixes.get(_env_type, "pip install")
        cmd = f"{_prefix} {' '.join(packages)}"
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(cmd)
        self.status_label.setText(f"📋 {tr('command_copied')}")

    def _copy_launcher_commands(self, install_cmd: str, run_cmd: str, app_name: str):
        """Copy both install and run commands to clipboard."""
        from PySide6.QtWidgets import QApplication
        full_cmd = f"{install_cmd}\n{run_cmd}"
        QApplication.clipboard().setText(full_cmd)
        self.status_label.setText(f"📋 Copied install + run commands for {app_name}")

    def _uninstall_preset(self, packages: list, preset_name: str):
        """Uninstall all packages in a preset with confirmation."""
        if not self.pip_manager:
            QMessageBox.warning(self, tr("warning"), tr("select_environment"))
            return

        # Find which packages are actually installed
        normalized_installed = {p.lower().replace("-", "_").replace(".", "_") for p in self.installed_package_names}
        installed_pkgs = [
            p for p in packages
            if p.lower().replace("-", "_").replace(".", "_") in normalized_installed
        ]

        if not installed_pkgs:
            QMessageBox.information(self, preset_name, "No packages from this preset are installed.")
            return

        reply = QMessageBox.question(
            self, f"Uninstall {preset_name}",
            f"Are you sure you want to uninstall these packages?\n\n"
            f"{', '.join(installed_pkgs)}\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self.status_label.setText(f"Uninstalling {preset_name}...")
        self.current_worker = WorkerThread(
            self.pip_manager.uninstall_packages, installed_pkgs
        )
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _filter_catalog(self, text: str):
        """Filter catalog rows by search text."""
        for row in range(self.catalog_table.rowCount()):
            name_item = self.catalog_table.item(row, 1)
            desc_item = self.catalog_table.item(row, 2)
            if name_item:
                match = text.lower() in name_item.text().lower()
                if desc_item:
                    match = match or text.lower() in desc_item.text().lower()
                self.catalog_table.setRowHidden(row, not match)

    def _set_busy(self, busy: bool):
        self.progress_bar.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.tabs.setEnabled(not busy)
    def _on_tab_changed(self, index: int):
        """Build tab content lazily on first visit."""
        self._ensure_tab_built(index)

    def _ensure_tab_built(self, index: int):
        """Build tab widget at index if not yet built."""
        if index < 0 or index >= len(self._tab_defs):
            return
        key = self._tab_defs[index][0]
        if self._tab_built.get(key):
            return
        creators = {
            "launcher":  self._create_launcher_tab,
            "installed": self._create_installed_tab,
            "catalog":   self._create_catalog_tab,
            "presets":   self._create_presets_tab,
            "manual":    self._create_manual_tab,
        }
        creator = creators.get(key)
        if not creator:
            return
        # Clear stub widgets so creator assigns fresh ones
        stub_attrs = {
            "installed":  ["packages_table", "pkg_count_label", "search_input",
                           "update_btn", "uninstall_btn"],
            "catalog":    ["catalog_table", "category_combo", "catalog_search",
                           "apply_btn", "changes_label"],
            "presets":    [],
            "manual":     ["manual_input", "manual_info_label", "output_log"],
        }
        for attr in stub_attrs.get(key, []):
            if hasattr(self, attr):
                try:
                    getattr(self, attr).setParent(None)
                except Exception:
                    pass
                delattr(self, attr)
        # B180: build the tab inside try/except so a creator crash does NOT
        # leave the QTabWidget in an inconsistent state (previously the old
        # placeholder was removed first, then insertTab failed → duplicate
        # tabs accumulated on every retry).
        try:
            widget = creator()
        except Exception as _ce:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.tabs").error(
                    f"[B180] Tab '{key}' creator failed: {type(_ce).__name__}: {_ce}"
                )
            except Exception:
                pass
            # Build a minimal error placeholder so the user sees something
            from PySide6.QtWidgets import QWidget as _QW, QVBoxLayout as _QV, QLabel as _QL
            widget = _QW()
            _lay = _QV(widget)
            _lay.addWidget(_QL(
                f"⚠ Could not build the {key.title()} tab.\n"
                f"Error: {type(_ce).__name__}: {_ce}\n\n"
                f"This is usually a PySide6 / Python 3.13 compatibility issue (B180).\n"
                f"Please update to Python 3.13.5+ or report this on GitHub."
            ))
        # Replace placeholder with real widget — both calls always run together.
        # B180: mark the tab as built BEFORE touching tabs.* so any signal that
        # re-enters _on_tab_changed during removeTab/insertTab/setCurrentIndex
        # short-circuits at `if self._tab_built.get(key): return`. Also block
        # tab-change signals while we mutate the QTabWidget — Qt 6.10.2 on
        # Linux/Python 3.13 fires currentChanged on setCurrentIndex even when
        # the index does not actually change, which previously caused the
        # function to recurse until RecursionError.
        self._tab_built[key] = True
        _was_blocked = False
        try:
            _was_blocked = self.tabs.blockSignals(True)
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, widget, self._tab_defs[index][1])
            self.tabs.setTabToolTip(index, self._tab_defs[index][3])
            self._tab_defs[index] = (key, self._tab_defs[index][1], widget, self._tab_defs[index][3])
            self.tabs.setCurrentIndex(index)
        except Exception as _re:
            try:
                from src.utils.logger import get_logger
                get_logger("venvstudio.tabs").error(
                    f"[B180] Tab '{key}' replace failed: {_re}"
                )
            except Exception:
                pass
        finally:
            try:
                self.tabs.blockSignals(_was_blocked)
            except Exception:
                pass


