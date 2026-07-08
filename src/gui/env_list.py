"""VenvStudio - MainWindow: Environment List Mixin
Environment table refresh, selection, and detail loading (moved from main_window.py).
"""
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMenu, QMessageBox, QTableWidgetItem,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QAction

from src.gui.workers import EnvDetailWorker
from src.utils.i18n import tr


class EnvListMixin:
    """Mixin for MainWindow: environment table refresh, selection, detail loading."""

    def _refresh_env_list(self, force: bool = False):
        """Phase 1: Load from cache instantly. Phase 2: fetch missing in background.
        If force=True (manual Refresh button), invalidates all caches first.
        """
        self._log.debug(f"_refresh_env_list called (force={force})")
        self.env_table.setRowCount(0)

        # Manual refresh: invalidate all caches, show overlay, disable button
        if force:
            self.venv_manager.invalidate_all_caches()
            # Disable refresh button
            if hasattr(self, "_refresh_btn"):
                self._refresh_btn.setEnabled(False)
                self._refresh_btn.setText("⏳ Refreshing...")
            # Show prominent banner immediately
            self.loading_label.setText("🔄  Refreshing environments — please wait...")
            self.loading_label.setVisible(True)
            self.statusBar().showMessage("Refreshing environments...")
            # Force UI update so banner appears before heavy work starts
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

        # Fast load — never skip_calc (pyvenv.cfg reading is fast, no subprocess)
        envs = self.venv_manager.list_venvs_fast(skip_calc=False)
        # Sort: base_dir envs first (alphabetic), then poetry (alphabetic), then pipx
        def _env_sort_key(e):
            if e.env_type == "pipx":
                return (2, e.name.lower())
            elif e.env_type == "poetry":
                return (1, e.name.lower())
            else:
                return (0, e.name.lower())
        envs = sorted(envs, key=_env_sort_key)

        # Also show loading if some envs are missing cache in normal load
        has_missing_cache = any(e.python_version == "..." for e in envs)
        if not force:
            self.loading_label.setVisible(has_missing_cache)
            if has_missing_cache:
                self.statusBar().showMessage("Loading environments...")
        self.env_table.setRowCount(len(envs))

        # Sync quick launch env selector
        if hasattr(self, "ql_env_selector"):
            current_ql = self.ql_env_selector.currentData()
            self.ql_env_selector.blockSignals(True)
            self.ql_env_selector.clear()
            self.ql_env_selector.addItem(tr("select_environment"), "")
            for env in envs:
                if env.is_valid:
                    self.ql_env_selector.addItem(f"  {env.name}", env.name)
            idx = self.ql_env_selector.findData(current_ql)
            if idx >= 0:
                self.ql_env_selector.setCurrentIndex(idx)
            else:
                # Previously selected env no longer exists — clear QL buttons
                self.ql_env_selector.setCurrentIndex(0)
                self._rebuild_ql_buttons(set())
            self.ql_env_selector.blockSignals(False)

        _type_labels = {
            "venv":         "🐍 venv",
            "uv":           "⚡ uv",
            "poetry":       "📜 Poetry",
            "pipx":         "📦 pipx",
            "conda":        "🦎 Conda",
            "system_tools": "🗂 Tools",
        }
        # B183: previously hardcoded pastel Catppuccin Mocha colours, which
        # were illegible on a light background. Pick darker, saturated
        # versions for light themes and the original pastels for dark
        # themes. We detect light vs dark by looking at the active 'bg'
        # palette colour — light themes have a near-white bg.
        _is_light_theme = False
        try:
            _bg = (self._c().get("bg") or "").lower()
            _bg_hex = _bg.lstrip("#")
            if len(_bg_hex) >= 6:
                _r = int(_bg_hex[0:2], 16)
                _g = int(_bg_hex[2:4], 16)
                _b = int(_bg_hex[4:6], 16)
                _is_light_theme = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            self._log.debug(
                f"env_table colours: bg={_bg!r} → light_theme={_is_light_theme}"
            )
        except Exception as _e:
            self._log.debug(f"env_table colour detection failed: {_e}")
        if _is_light_theme:
            _type_colors = {
                "uv":           "#8a6d00",  # darker amber, more contrast on white
                "poetry":       "#5b2c6f",  # very deep purple
                "pipx":         "#0c5a72",  # very dark teal
                "conda":        "#1b5e20",  # dark forest green
                "system_tools": None,
            }
            _path_color_default = "#333333"  # nearly black
        else:
            _type_colors = {
                "uv":           "#f9e2af",
                "poetry":       "#cba6f7",
                "pipx":         "#89dceb",
                "conda":        "#a6e3a1",
                "system_tools": None,
            }
            _path_color_default = "#bac2de"

        # Bold font used for ALL columns (B183 — previously only name was
        # bold, other columns looked anaemic next to it on light themes)
        # B174 fix: copy from table's current font (which honours QSS pixel-size).
        # Bare QFont() yields a Windows default whose pointSize() is -1, which
        # triggers QFont::setPointSize(-1) warnings during Qt's font cascade.
        _row_font = QFont(self.env_table.font())
        _row_font.setBold(True)

        for i, env in enumerate(envs):
            etype = getattr(env, "env_type", "venv")

            # ── Name column ──
            name_item = QTableWidgetItem(f"  {env.name}")
            _color = _type_colors.get(etype)
            if etype == "system_tools":
                name_item.setForeground(QColor(self._c().get("accent", "#89b4fa")))
                name_item.setToolTip("System tools environment — install R, RStudio, Ollama, DBeaver etc. from Launch tab")
            elif _color:
                name_item.setForeground(QColor(_color))
                name_item.setToolTip(f"{_type_labels.get(etype, etype)} environment")
            elif not env.is_valid:
                name_item.setForeground(Qt.red)
                name_item.setToolTip("Invalid environment (Python not found)")
            elif _is_light_theme:
                # Default venv on light theme — needs a dark fg too
                name_item.setForeground(QColor("#1f2937"))
            name_item.setFont(_row_font)
            self.env_table.setItem(i, 0, name_item)

            # ── Type column ──
            type_item = QTableWidgetItem(f"  {_type_labels.get(etype, '🐍 venv')}")
            type_item.setData(Qt.UserRole, etype)  # store raw env_type for deletion etc.
            if _color:
                type_item.setForeground(QColor(_color))
            elif etype == "system_tools":
                type_item.setForeground(QColor(self._c().get("accent", "#89b4fa")))
            elif _is_light_theme:
                type_item.setForeground(QColor("#1f2937"))
            type_item.setFont(_row_font)
            self.env_table.setItem(i, 1, type_item)

            # ── Path column ──
            _full_path = str(env.path)
            _display_path = _full_path
            path_item = QTableWidgetItem(f"  {_display_path}")
            path_item.setToolTip(_full_path)
            path_item.setForeground(QColor(_path_color_default))
            path_item.setFont(_row_font)
            self.env_table.setItem(i, 2, path_item)

            # ── Runtime column: Python version or "----" ──
            _rv = str(env.python_version).strip()
            _runtime_str = f"  Python {_rv}" if (_rv and _rv not in ("Unknown", "?", "...")) else "  ----"
            _runtime_item = QTableWidgetItem(_runtime_str)
            _runtime_item.setFont(_row_font)
            if _is_light_theme:
                _runtime_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 3, _runtime_item)

            pkg = str(env.package_count) if env.package_count else "0"
            _pkg_item = QTableWidgetItem(f"  {pkg}")
            _pkg_item.setFont(_row_font)
            if _is_light_theme:
                _pkg_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 4, _pkg_item)

            _size = env.size if env.size and env.size not in ("N/A", "?", "...") else "0 MB"
            _size_item = QTableWidgetItem(f"  {_size}")
            _size_item.setFont(_row_font)
            if _is_light_theme:
                _size_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 5, _size_item)

            created_str = ""
            if env.created:
                try:
                    dt = datetime.fromisoformat(env.created)
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_str = env.created[:16]
            _created_item = QTableWidgetItem(f"  {created_str}")
            _created_item.setFont(_row_font)
            if _is_light_theme:
                _created_item.setForeground(QColor("#1f2937"))
            self.env_table.setItem(i, 6, _created_item)

            # Default column
            default_env = self.config.get("default_env", "")
            default_item = QTableWidgetItem("⭐" if env.name == default_env else "")
            default_item.setTextAlignment(Qt.AlignCenter)
            default_item.setFlags(default_item.flags() & ~Qt.ItemIsEditable)
            self.env_table.setItem(i, 7, default_item)

        # Group envs by location
        _base_dir = str(self.venv_manager.base_dir)
        _home = str(Path.home())
        _base_envs = [e for e in envs if str(e.path).startswith(_base_dir)]
        _poetry_envs = [e for e in envs if e.env_type == "poetry"]
        _pipx_envs = [e for e in envs if e.env_type == "pipx"]
        # Remove poetry and pipx from base count (they have their own paths)
        _base_envs = [e for e in _base_envs if e.env_type not in ("poetry", "pipx")]

        def _fmt_size(envs_list):
            total = 0
            for e in envs_list:
                s = e.size or "0 MB"
                try:
                    n, u = s.strip().split()
                    n = float(n)
                    mult = {"B":1,"KB":1024,"MB":1024**2,"GB":1024**3,"TB":1024**4}.get(u,1)
                    total += n * mult
                except Exception:
                    pass
            for unit in ["B","KB","MB","GB","TB"]:
                if total < 1024:
                    return f"{total:.1f} {unit}"
                total /= 1024
            return "?"

        parts = []
        _total_all = _fmt_size(envs)
        parts.append(f"📂 {self.venv_manager.base_dir}  •  {len(_base_envs)} env(s)  •  {_fmt_size(_base_envs)}")
        if _poetry_envs:
            parts.append(f"📜 poetry  •  {len(_poetry_envs)} env(s)  •  {_fmt_size(_poetry_envs)}")
        if _pipx_envs:
            parts.append(f"📦 pipx  •  {len(_pipx_envs)} env(s)  •  {_fmt_size(_pipx_envs)}")
        parts.append(f"🗂 total  •  {_total_all}")
        self.info_label.setText("        ".join(parts))

        # Update package panel env dropdown
        env_list = [(e.name, e.path) for e in envs]
        self._last_env_list = env_list
        if self.package_panel is not None:
            if self.package_panel is not None: self.package_panel.populate_env_list(env_list)
        if self.settings_page is not None:
            self.settings_page.populate_vscode_envs(env_list)

        if not envs:
            self.loading_label.setVisible(False)
            self.statusBar().showMessage("No environments found")
            return

        # Start background worker for any envs with missing data ("...")
        missing_names = [
            self.env_table.item(i, 0).text().strip()
            for i in range(self.env_table.rowCount())
            if self.env_table.item(i, 2) and self.env_table.item(i, 2).text().strip() in ("...", "", "----")
        ]

        if missing_names:
            # Stop previous worker if running
            if hasattr(self, "_detail_worker") and self._detail_worker.isRunning():
                self._detail_worker.quit()
                self._detail_worker.wait(2000)

            self._detail_worker = EnvDetailWorker(
                self.venv_manager,
                [e.name for e in envs]  # pass all when force=True so worker checks needs_refresh
            )
            self._detail_worker.env_detail_ready.connect(self._on_env_detail_ready)
            self._detail_worker.all_done.connect(self._on_all_details_done)
            self._detail_worker.start()
        else:
            self._on_all_details_done()

    def _on_env_detail_ready(self, row, python_version, package_count, size):
        """Update a single row with detailed info from background thread."""
        if row < self.env_table.rowCount():
            _rv = str(python_version).strip()
            if _rv and _rv not in ("Unknown", "?", "..."):
                if _rv[0].isdigit():
                    _runtime_str = f"  Python {_rv}"
                else:
                    _runtime_str = f"  Python {_rv}"
            else:
                _runtime_str = "  ----"
            self.env_table.setItem(row, 3, QTableWidgetItem(_runtime_str))
            self.env_table.setItem(row, 4, QTableWidgetItem(f"  {package_count}"))
            _size = size if size and size not in ("N/A", "?", "...") else "0 MB"
            self.env_table.setItem(row, 5, QTableWidgetItem(f"  {_size}"))

    def _on_all_details_done(self):
        self.loading_label.setVisible(False)
        self.loading_label.setText("Loading environments...")  # reset text
        count = self.env_table.rowCount()
        self.statusBar().showMessage(f"Found {count} environment(s)")
        # Re-enable refresh button
        if hasattr(self, "_refresh_btn"):
            self._refresh_btn.setEnabled(True)
            self._refresh_btn.setText(f"🔄 {tr('refresh')}")

    def _update_info_label_fast(self, count):
        base_dir = self.config.get_venv_base_dir()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _update_info_label(self):
        base_dir = self.config.get_venv_base_dir()
        count = self.env_table.rowCount()
        self.info_label.setText(f"\U0001f4c2 {base_dir}  \u2022  {count} environment(s)")

    def _on_env_selected(self):
        rows = self.env_table.selectionModel().selectedRows()
        has_selection = bool(rows)
        _sel_name = self.env_table.item(rows[0].row(), 0).text().strip() if has_selection else "(none)"
        self._log.debug(f"_on_env_selected: env={_sel_name!r} has_selection={has_selection}")
        self.btn_manage_pkgs.setEnabled(has_selection)
        self.btn_terminal.setEnabled(has_selection)
        # Resolve env_type for button visibility rules
        _sel_type = ""
        if has_selection:
            _rows = self.env_table.selectionModel().selectedRows()
            if _rows:
                _ti = self.env_table.item(_rows[0].row(), 1)
                if _ti:
                    _sel_type = _ti.data(Qt.UserRole) or _ti.text().strip().lower()
        _is_pipx   = _sel_type == "pipx"
        _is_poetry = _sel_type == "poetry"
        # Clone: hide for pipx
        self.btn_clone.setVisible(not _is_pipx)
        self.btn_clone.setEnabled(has_selection)
        # Rename: hide for pipx and poetry
        _show_rename = not _is_pipx and not _is_poetry
        self.btn_rename.setVisible(_show_rename)
        self.btn_rename.setEnabled(has_selection and _show_rename)
        if hasattr(self, "btn_rename_full"):
            self.btn_rename_full.setVisible(_show_rename)
            self.btn_rename_full.setEnabled(has_selection and _show_rename)
        self.btn_delete.setEnabled(has_selection)
        self.btn_export.setEnabled(has_selection)
        if hasattr(self, "btn_make_default"):
            self.btn_make_default.setEnabled(has_selection)

        if has_selection:
            row = rows[0].row()
            name = self.env_table.item(row, 0).text().strip()
            self.selected_env = name
            self.statusBar().showMessage(f"Selected: {name}")
            # Sync QL dropdown
            if hasattr(self, "ql_env_selector"):
                idx = self.ql_env_selector.findData(name)
                if idx >= 0:
                    self.ql_env_selector.blockSignals(True)
                    self.ql_env_selector.setCurrentIndex(idx)
                    self.ql_env_selector.blockSignals(False)
            # Sync package_panel — use actual path (handles pipx, poetry etc.)
            venv_path = self._get_env_path(name) or self.venv_manager.base_dir / name
            if venv_path.exists():
                if self.package_panel is not None: self.package_panel.set_venv(venv_path)
                # ── Track in recent envs (deferred — no UI blocking) ─────
                try:
                    type_item = self.env_table.item(row, 1)
                    raw_type = type_item.text().strip() if type_item else "venv"
                    env_type = "venv"
                    for k in ("uv", "poetry", "pipx", "conda", "venv"):
                        if k in raw_type.lower():
                            env_type = k
                            break
                    _vp = str(venv_path)
                    _nm = name
                    _et = env_type
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(300, lambda: self._track_recent(_nm, _vp, _et))
                except Exception:
                    pass
                # ─────────────────────────────────────────────────────

    def _open_default_env(self):
        """On startup, open default env in Packages if set."""
        default_env = self.config.get("default_env", "")
        if not default_env:
            return
        venv_path = self.venv_manager.base_dir / default_env
        if not venv_path.exists():
            return
        if self.package_panel is not None:
            self.package_panel.set_venv(venv_path)
        self._switch_page(0)
        # Sync env table selection
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == default_env:
                self.env_table.selectRow(row)
                break

    def _show_env_context_menu(self, pos):
        """Show right-click context menu on environment table."""
        self._log.debug(f"_show_env_context_menu at pos={pos.x()},{pos.y()}")
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        index = self.env_table.indexAt(pos)

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ font-size: {self._c()['fs_base']}px; }} QMenu::item {{ padding: 6px 20px; }}")

        if not index.isValid():
            # Boş alana sağ tık — genel işlemler
            a_new = QAction("➕ New Environment", self)
            a_new.triggered.connect(self._create_env)
            menu.addAction(a_new)

            a_refresh = QAction("🔄 Refresh", self)
            a_refresh.triggered.connect(lambda: self._refresh_env_list(force=True))
            menu.addAction(a_refresh)

            menu.exec(self.env_table.viewport().mapToGlobal(pos))
            return

        # Satırı seç
        self.env_table.selectRow(index.row())
        name = self._get_selected_env_name()
        if not name:
            return

        # Resolve env_type for this row
        _ctx_type = ""
        _type_item = self.env_table.item(index.row(), 1)
        if _type_item:
            _ctx_type = _type_item.data(Qt.UserRole) or _type_item.text().strip().lower()
        _ctx_is_pipx   = _ctx_type == "pipx"
        _ctx_is_poetry = _ctx_type == "poetry"

        a_manage = QAction("📦 Manage Packages", self)
        a_manage.triggered.connect(self._on_env_double_click)
        menu.addAction(a_manage)

        menu.addSeparator()

        a_terminal = QAction("🖥️ Open Terminal", self)
        a_terminal.triggered.connect(self._open_terminal)
        menu.addAction(a_terminal)

        a_folder = QAction("📁 Open Folder", self)
        a_folder.setToolTip("Open the environment folder in your file manager")
        a_folder.triggered.connect(self._open_env_folder)
        menu.addAction(a_folder)

        a_default = QAction("⭐ Make Default", self)
        a_default.triggered.connect(self._make_default_env)
        menu.addAction(a_default)

        menu.addSeparator()

        if not _ctx_is_pipx:
            a_clone = QAction("📋 Clone", self)
            a_clone.triggered.connect(self._clone_env)
            menu.addAction(a_clone)

        if not _ctx_is_pipx and not _ctx_is_poetry:
            a_rename = QAction("✏️ Rename (Name Only)", self)
            a_rename.setToolTip("Rename folder only — fast, but pip/python paths may break on Windows")
            a_rename.triggered.connect(self._rename_env_only)
            menu.addAction(a_rename)

            a_rename_full = QAction("🔄 Rename (Full)", self)
            a_rename_full.setToolTip("Clone with new name + delete old — slow but safe, all packages reinstalled")
            a_rename_full.triggered.connect(self._rename_env_full)
            menu.addAction(a_rename_full)

        export_sub = menu.addMenu("📤 Export")
        export_sub.addAction("📄 requirements.txt", self._export_requirements)
        export_sub.addAction("📄 requirements-frozen.txt", self._export_frozen)
        export_sub.addSeparator()
        export_sub.addAction("🐍 environment.yml (Conda)", self._export_conda_yml)
        export_sub.addAction("📦 pyproject.toml", self._export_pyproject)
        export_sub.addAction("📊 JSON", self._export_json)
        export_sub.addSeparator()
        export_sub.addAction("🐳 Dockerfile", self._export_dockerfile)
        export_sub.addAction("🐳 docker-compose.yml", self._export_docker_compose)
        export_sub.addSeparator()
        export_sub.addAction("📋 Copy to Clipboard", self._export_clipboard)

        menu.addSeparator()

        a_delete = QAction("🗑️ Delete", self)
        a_delete.setObjectName("danger")
        a_delete.triggered.connect(self._delete_env)
        menu.addAction(a_delete)

        menu.exec(self.env_table.viewport().mapToGlobal(pos))

    def _make_default_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        current_default = self.config.get("default_env", "")
        if name == current_default:
            QMessageBox.information(self, "Default Env", f"'{name}' is already the default environment.")
            return
        reply = QMessageBox.question(
            self, "Make Default Environment",
            f"Set '{name}' as the default environment?\n\nVenvStudio will open this environment on startup.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config.set("default_env", name)
            self._refresh_env_list()
            self.statusBar().showMessage(f"✅ '{name}' set as default environment")

    def _on_env_double_click(self):
        self._open_package_manager()

    def _get_env_path(self, name: str) -> "Path | None":
        """Return actual path for env — handles pipx, poetry etc."""
        # 1. Check table Path column tooltip (fast)
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == name:
                path_item = self.env_table.item(row, 2)
                if path_item and path_item.toolTip():
                    return Path(path_item.toolTip())
                break
        # 2. Fallback: scan venv list (handles pipx home)
        try:
            for env in self.venv_manager.list_venvs_fast(skip_calc=True):
                if env.name == name:
                    return env.path
        except Exception:
            pass
        return self.venv_manager.base_dir / name

    def _get_selected_env_name(self):
        rows = self.env_table.selectionModel().selectedRows()
        if rows:
            return self.env_table.item(rows[0].row(), 0).text().strip()
        return ""

