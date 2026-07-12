"""VenvStudio - MainWindow: Environment Operations Mixin
Create/rename/delete/clone environment logic (moved from main_window.py).
"""
from PySide6.QtWidgets import (
    QMessageBox, QInputDialog, QProgressDialog, QTableWidgetItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from src.core.venv_manager import VenvManager
from src.gui.workers import (
    CloneWorker, DeleteWorker, RenameOnlyWorker, RenameFullWorker,
)


class EnvOperationsMixin:
    """Mixin for MainWindow: create/rename/delete/clone environment operations."""

    def _create_env(self):
        from src.gui.env_dialog import EnvCreateDialog
        dialog = EnvCreateDialog(self.venv_manager, self.config, self)
        _created = {"any": False}

        def _on_env_created(name):
            _created["any"] = True
            self._log.info(f"env_created: name={name!r} → invalidating cache + refreshing list")
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()

        dialog.env_created.connect(_on_env_created)
        dialog.exec()
        # Previously this ALWAYS invalidated every env cache after the
        # dialog closed — even on Cancel — causing a full multi-second
        # subprocess rescan of all envs (and a SECOND one after a real
        # creation, since _on_env_created had already done it).
        if _created["any"]:
            self._log.debug("_create_env: dialog closed after creation → final list refresh")
            self._refresh_env_list()
        else:
            self._log.debug("_create_env: dialog closed without creating → skipping invalidate/refresh")

    def _get_new_name_for_rename(self, name):
        """Yeni isim giriş dialog'u — ortak kullanım."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Environment",
            f"Enter new name for '{name}':",
            text=name,
        )
        if not ok or not new_name.strip() or new_name.strip() == name:
            return None
        new_name = new_name.strip()
        invalid_chars = set(' /\\:*?"<>|')
        if any(c in invalid_chars for c in new_name):
            QMessageBox.warning(self, "Warning", "Name contains invalid characters.")
            return None
        return new_name

    def _rename_env_only(self):
        """Rename (Name Only) — sadece klasör rename, hızlı."""
        name = self._get_selected_env_name()
        if not name:
            return
        new_name = self._get_new_name_for_rename(name)
        if not new_name:
            return

        # Get env type and path from selected row for cmd panel display
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / name)

        # Update educational cmd panel
        self._update_cmd_panel(action="rename", env_type=_env_type, name=name, env_path=_display_path)

        self.rename_progress = QProgressDialog(
            f"Renaming '{name}' → '{new_name}'...", None, 0, 0, self
        )
        self.rename_progress.setWindowTitle("Renaming Environment")
        self.rename_progress.setMinimumWidth(400)
        self.rename_progress.setWindowModality(Qt.WindowModal)
        self.rename_progress.show()

        self._rename_worker = RenameOnlyWorker(self.venv_manager, name, new_name)
        self._rename_worker.progress.connect(
            lambda msg: self.rename_progress.setLabelText(f"⏳ {msg}")
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    def _rename_env_full(self):
        """Rename (Full) — clone + delete, tüm paketler yeniden kurulur."""
        name = self._get_selected_env_name()
        if not name:
            return
        new_name = self._get_new_name_for_rename(name)
        if not new_name:
            return

        reply = QMessageBox.question(
            self, "Rename (Full)",
            f"This will create '{new_name}' with all packages from '{name}', then delete '{name}'.\n\n"
            f"This may take a while. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Get env type and path from selected row for cmd panel display
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / name)

        # Update educational cmd panel
        self._update_cmd_panel(action="rename", env_type=_env_type, name=name, env_path=_display_path)

        self.rename_progress = QProgressDialog(
            f"Renaming '{name}' → '{new_name}'...", "Cancel", 0, 0, self
        )
        self.rename_progress.setWindowTitle("Renaming Environment (Full)")
        self.rename_progress.setMinimumWidth(400)
        self.rename_progress.setWindowModality(Qt.WindowModal)
        self.rename_progress.show()

        self._rename_worker = RenameFullWorker(self.venv_manager, name, new_name)
        self._rename_worker.progress.connect(
            lambda msg: self.rename_progress.setLabelText(f"⏳ {msg}")
        )
        self._rename_worker.finished.connect(self._on_rename_finished)
        self._rename_worker.start()

    # Eski fonksiyon — geriye dönük uyumluluk
    def _rename_env(self):
        self._rename_env_only()

    def _on_rename_finished(self, success, message):
        self.rename_progress.close()
        if success:
            # Force memory cache clear so deleted env disappears immediately
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            first_line = message.splitlines()[0] if message else "Failed"
            QMessageBox.critical(self, "Error", message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _delete_env(self):
        name = self._get_selected_env_name()
        if not name:
            return
        # B182 fix: figure out env type BEFORE the confirm dialog, so pipx
        # users see a meaningful warning. The previous wording suggested
        # the "environment" would be deleted along with all its packages
        # — for pipx that would mean wiping pipx itself plus every app
        # the user installed outside VenvStudio. Be explicit instead.
        _env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _env_type = _type_item.data(Qt.UserRole) or "venv"

        if _env_type == "pipx":
            confirm_msg = (
                f"Delete the '{name}' pipx environment?\n\n"
                f"⚠ This will permanently remove ALL pipx apps installed in "
                f"this environment.\n\n"
                f"After deletion an empty pipx environment will be re-created "
                f"so you can install fresh apps."
            )
        else:
            confirm_msg = (
                f"Are you sure you want to delete '{name}'?\n\n"
                f"This will permanently remove the environment and all installed packages."
            )

        reply = QMessageBox.warning(
            self, "Delete Environment", confirm_msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # No popup — progress shown in Command Reference panel below

            self._deleting_env_name = name
            _display_path = _env_path or str(self.venv_manager.base_dir / name)
            # B182: remember the real env path/type for cache invalidation in
            # _on_delete_finished — pipx/poetry/uv envs live OUTSIDE
            # venv_manager.base_dir, so the old code that built the cache key
            # from `base_dir / name` was looking up the wrong key and the
            # stale entry survived a delete.
            self._deleting_env_path = _env_path
            self._deleting_env_type = _env_type

            # Update the educational command panel at the bottom of the env page
            self._update_cmd_panel(action="delete", env_type=_env_type, name=name, env_path=_display_path)

            self._delete_worker = DeleteWorker(self.venv_manager, name, env_path=_env_path, env_type=_env_type)
            def _on_del_progress(msg):
                if hasattr(self, "_cmd_panel_live"):
                    self._cmd_panel_live.setText(f"▶ {msg}")
            self._delete_worker.progress.connect(_on_del_progress)
            self._delete_worker.finished.connect(self._on_delete_finished)
            self._delete_worker.start()

    def _on_delete_finished(self, success, message):
        deleted_name = getattr(self, "_deleting_env_name", "")
        deleted_path = getattr(self, "_deleting_env_path", None)
        deleted_type = getattr(self, "_deleting_env_type", "venv")
        if success:
            self._log.info(
                f"env_deleted: name={deleted_name!r} type={deleted_type!r} "
                f"path={deleted_path!r} → cleaning cache + removing row"
            )
            # Remove pkg_list cache entry for the deleted env
            try:
                from src.core.venv_manager import VenvManager
                from pathlib import Path as _P
                vm = VenvManager(_P(self.config.get_venv_base_dir()))
                all_cache = vm._load_all_cache()
                # B182: pipx/poetry/uv envs live OUTSIDE base_dir — use the
                # actual env path captured in _delete_env, not the assumed
                # `base_dir / name`. Falls back to base_dir/name only if the
                # real path is missing (legacy / classic venv path).
                real_path = _P(deleted_path) if deleted_path else (self.venv_manager.base_dir / deleted_name)
                if deleted_name:
                    # Cache key uses the same normalisation as venv_manager
                    try:
                        norm_path = vm._cache_key(real_path)
                    except Exception:
                        norm_path = str(real_path).replace("\\", "/")
                    pkg_key = "pkg_list:" + norm_path
                    if pkg_key in all_cache:
                        all_cache.pop(pkg_key, None)
                        self._log.debug(f"env_deleted: removed pkg_list cache key={pkg_key!r}")
                    # Also remove env meta cache entry by the same normalised key
                    if norm_path in all_cache:
                        all_cache.pop(norm_path, None)
                        self._log.debug(f"env_deleted: removed env meta cache key={norm_path!r}")
                    vm._save_all_cache(all_cache)
                    vm.invalidate_cache(real_path)
            except Exception as e:
                self._log.warning(f"env_deleted: cache cleanup error: {e}")
            # Clear package panel launcher state
            if self.package_panel is not None:
                self.package_panel._launcher_py_version_cache.clear()
                self.package_panel._update_launcher_status()
            # B182: previously called _refresh_env_list(force=True) here, which
            # re-scanned every env on disk and ran subprocess calls for each.
            # Even though only one row changed, the user saw a "Refreshing
            # environments — please wait..." banner stuck for several seconds.
            # Now we do a surgical update: remove the row from the table and
            # purge the in-memory env list cache for this env. Anything else
            # the user is looking at stays exactly as it was.
            self._remove_env_row_inplace(deleted_name, deleted_path)

            # B182: for pipx, the user expects the row to come back as a
            # fresh empty pipx tracker (zero apps installed via VenvStudio).
            # Re-create the marker file and add the row back to the table
            # in one shot — no full _refresh_env_list, no "Refreshing..."
            # banner, no subprocess scans.
            if deleted_type == "pipx":
                try:
                    self._readd_empty_pipx_row()
                except Exception as _e:
                    self._log.warning(f"pipx readd skipped: {_e}")

            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            self._log.warning(f"env_delete_failed: name={deleted_name!r} error={message!r}")
            first_line = message.splitlines()[0] if message else "Failed"
            QMessageBox.critical(self, "Error", message)
            # Failure path: do a normal refresh (no force) so the user sees
            # the actual current state without a heavy re-scan.
            self._refresh_env_list()
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _refresh_current_env_row(self, pkg_count: int = -1) -> None:
        """Update only the active env's row after a package / launch app /
        preset install or uninstall finishes. We invalidate the env's
        cache (so package_count + size are recomputed), then re-read the
        single row in place. The other rows in the table aren't touched
        and the user doesn't see a "Refreshing..." banner.

        ``pkg_count`` is the authoritative new package count from the
        package panel (-1 = unknown). When provided, we bypass the
        list_venvs_fast cache lookup entirely for the count to avoid the
        race where the async pip-list refresh hasn't written the new
        cache value yet.

        Falls back to a normal _refresh_env_list if anything goes wrong —
        the user always ends up with a current view, just maybe not as
        snappy.
        """
        self._log.info(f"refresh_current_row: called (pkg_count={pkg_count})")
        try:
            # Find the active env path from the package panel
            pp = getattr(self, "package_panel", None)
            if pp is None:
                self._refresh_env_list()
                return
            cur_path = getattr(pp, "_current_venv_path", None)
            if not cur_path:
                self._refresh_env_list()
                return
            from pathlib import Path as _P
            cur_path = _P(str(cur_path))

            # 1) Drop cache entries for this env so the next read recomputes
            try:
                self.venv_manager.invalidate_cache(cur_path)
            except Exception as _e:
                self._log.debug(f"refresh_current_row: invalidate_cache: {_e}")

            # Also drop pkg_list and any meta cache entries from the on-disk cache
            try:
                from src.core.venv_manager import VenvManager
                vm = VenvManager(_P(self.config.get_venv_base_dir()))
                all_cache = vm._load_all_cache()
                try:
                    norm_path = vm._cache_key(cur_path)
                except Exception:
                    norm_path = str(cur_path).replace("\\", "/")
                changed = False
                for _k in (norm_path, "pkg_list:" + norm_path):
                    if _k in all_cache:
                        all_cache.pop(_k, None)
                        changed = True
                if changed:
                    vm._save_all_cache(all_cache)
            except Exception as _e:
                self._log.debug(f"refresh_current_row: cache prune: {_e}")

            # 2) Locate the row in the env table by path or name
            row = -1
            for r in range(self.env_table.rowCount()):
                _path_item = self.env_table.item(r, 2)
                _row_path = ""
                if _path_item:
                    _row_path = _path_item.toolTip() or _path_item.text().strip()
                if _row_path and _P(_row_path).resolve() == cur_path.resolve():
                    row = r
                    break
            if row < 0:
                # Couldn't pinpoint the row; do a normal (light) refresh
                self._refresh_env_list()
                return

            # 3) Re-read the env's metadata and update the row's cells in-place
            env_info = None
            try:
                # list_venvs_fast returns all envs; pick the one with a matching path
                _envs = self.venv_manager.list_venvs_fast(skip_calc=False)
                for _e in _envs:
                    try:
                        if _P(str(_e.path)).resolve() == cur_path.resolve():
                            env_info = _e
                            break
                    except Exception:
                        pass
            except Exception as _e:
                self._log.debug(f"refresh_current_row: list_venvs_fast: {_e}")

            if env_info is None:
                # Last resort — a normal refresh will rebuild the whole table
                self._refresh_env_list()
                return

            # Update only the cells that change: runtime (3), packages (4),
            # size (5). Name / type / path / created stay the same.
            from PySide6.QtWidgets import QTableWidgetItem
            from PySide6.QtGui import QFont as _QFont, QColor as _QColor

            _is_light = False
            try:
                _bg = (self._c().get("bg") or "").lstrip("#")
                if len(_bg) >= 6:
                    _r = int(_bg[0:2], 16)
                    _g = int(_bg[2:4], 16)
                    _b = int(_bg[4:6], 16)
                    _is_light = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            except Exception:
                pass
            # B174 fix: see env-table loop above — copy table font to preserve QSS pixel-size.
            _bold = _QFont(self.env_table.font())
            _bold.setBold(True)
            _fg_dark = _QColor("#1f2937") if _is_light else None

            _rv = str(env_info.python_version).strip()
            _runtime_str = (
                f"  Python {_rv}" if (_rv and _rv not in ("Unknown", "?", "...")) else "  ----"
            )
            _runtime_item = QTableWidgetItem(_runtime_str)
            _runtime_item.setFont(_bold)
            if _fg_dark is not None:
                _runtime_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 3, _runtime_item)

            _pkg = str(env_info.package_count) if env_info.package_count else "0"
            # B182 race fix: when caller passed an authoritative pkg count,
            # use it instead of env_info.package_count (which may still be
            # the pre-install value while the async pip-list refresh runs).
            if pkg_count >= 0:
                _pkg = str(pkg_count)
            _pkg_item = QTableWidgetItem(f"  {_pkg}")
            _pkg_item.setFont(_bold)
            if _fg_dark is not None:
                _pkg_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 4, _pkg_item)

            _size = (
                env_info.size if env_info.size and env_info.size not in ("N/A", "?", "...")
                else "0 MB"
            )
            _size_item = QTableWidgetItem(f"  {_size}")
            _size_item.setFont(_bold)
            if _fg_dark is not None:
                _size_item.setForeground(_fg_dark)
            self.env_table.setItem(row, 5, _size_item)

            # Refresh the header summary strip (e.g. "3 env(s) · 2.4 GB")
            try:
                if hasattr(self, "_update_env_summary"):
                    self._update_env_summary()
            except Exception:
                pass
            self._log.info(
                f"refresh_current_row: updated row {row} "
                f"(pkgs={_pkg}, size={_size})"
            )
        except Exception as e:
            self._log.warning(f"_refresh_current_env_row failed: {e} — fallback to list refresh")
            try:
                self._refresh_env_list()
            except Exception:
                pass

    def _remove_env_row_inplace(self, name: str, path: str = None) -> None:
        """B182: surgically drop a single row from the env table without
        triggering a full _refresh_env_list. Also drops the env from the
        VenvManager's in-memory list cache so a later normal refresh
        (e.g. switching pages) won't bring it back from the in-process
        cache.

        Falls back to a normal (non-force) refresh if the row can't be
        located by name+path — that path still avoids the heavy
        force=True rescan that put a "Refreshing..." banner on screen.
        """
        try:
            removed_row = -1
            for r in range(self.env_table.rowCount()):
                name_item = self.env_table.item(r, 0)
                path_item = self.env_table.item(r, 2)
                row_name = (name_item.text().strip() if name_item else "")
                row_path = ""
                if path_item:
                    row_path = path_item.toolTip() or path_item.text().strip()
                if row_name == name and (not path or row_path == path or not row_path):
                    removed_row = r
                    break
            if removed_row >= 0:
                self.env_table.removeRow(removed_row)
                self._log.debug(f"env_deleted: removed row {removed_row} from table")
            else:
                # Fallback — couldn't pinpoint the row, do a light refresh
                self._log.debug(
                    f"env_deleted: row not found for name={name!r} path={path!r} "
                    f"→ falling back to light refresh"
                )
                self._refresh_env_list()
                return

            # Drop the env from the in-memory list cache for this base_dir
            try:
                from src.core.venv_manager import VenvManager
                base_key = getattr(self.venv_manager, "_base_key", None)
                if base_key and base_key in VenvManager._mem_envs:
                    VenvManager._mem_envs[base_key] = [
                        e for e in VenvManager._mem_envs[base_key]
                        if e.name != name
                    ]
            except Exception as e:
                self._log.debug(f"env_deleted: in-memory cache prune skipped: {e}")

            # Also sync the quick-launch env selector if present
            if hasattr(self, "ql_env_selector"):
                idx = self.ql_env_selector.findData(name)
                if idx >= 0:
                    self.ql_env_selector.removeItem(idx)

            # Update header counters (e.g. "3 env(s) · 2.4 GB"). These come
            # from the venv_manager's list, so re-render that strip only.
            try:
                if hasattr(self, "_update_env_summary"):
                    self._update_env_summary()
            except Exception:
                pass
        except Exception as e:
            self._log.warning(f"_remove_env_row_inplace failed: {e} — falling back")
            self._refresh_env_list()

    def _readd_empty_pipx_row(self) -> None:
        """B182: re-create the pipx tracker marker and insert a fresh row
        into the env table — without calling _refresh_env_list (which
        would re-scan every env on disk and freeze the UI for seconds).

        We assume the user just deleted the pipx row, which removed the
        ``.venvstudio_env`` marker but left ``~/.local/share/pipx``
        (or ``%LOCALAPPDATA%\\pipx`` on Windows) intact. We write a new
        empty marker, then add a row with package_count=0 to the table.
        Real package counts and python versions will be picked up on the
        next natural refresh — by then it's irrelevant because the row
        is already on screen.
        """
        from pathlib import Path as _P
        import json as _json
        import sys as _sys
        import os as _os
        from datetime import datetime as _dt

        # 1) Locate pipx home (same logic as venv_manager.list_venvs_fast)
        try:
            from src.utils.platform_utils import get_pipx_home
            pipx_home = get_pipx_home()
        except Exception:
            pipx_home = None
        if not pipx_home:
            if _sys.platform == "win32":
                pipx_home = _os.path.join(_os.environ.get("LOCALAPPDATA", ""), "pipx")
            else:
                pipx_home = _os.path.join(_os.path.expanduser("~"), ".local", "share", "pipx")
        pipx_path = _P(pipx_home)
        if not pipx_path.exists():
            self._log.debug(f"pipx readd: pipx_home not found at {pipx_path} — nothing to track")
            return

        # 2) Re-create the marker so VenvStudio recognises it again next start
        marker = pipx_path / ".venvstudio_env"
        try:
            marker_data = {
                "name": "pipx",
                "type": "pipx",
                "created": _dt.now().strftime("%Y-%m-%d %H:%M"),
                "python_version": f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}",
            }
            with open(marker, "w", encoding="utf-8") as f:
                _json.dump(marker_data, f, indent=2)
            self._log.info(f"pipx readd: wrote marker at {marker}")
        except Exception as e:
            self._log.warning(f"pipx readd: marker write failed: {e}")
            return

        # 3) Add row to the env table directly — no subprocess, no rescan
        try:
            row = self.env_table.rowCount()
            self.env_table.insertRow(row)

            from PySide6.QtWidgets import QTableWidgetItem
            from PySide6.QtCore import Qt as _Qt
            from PySide6.QtGui import QColor as _QColor, QFont as _QFont

            # Detect light theme for colour choices (matches _refresh_env_list)
            _is_light = False
            try:
                _bg = (self._c().get("bg") or "").lstrip("#")
                if len(_bg) >= 6:
                    _r = int(_bg[0:2], 16)
                    _g = int(_bg[2:4], 16)
                    _b = int(_bg[4:6], 16)
                    _is_light = (_r * 299 + _g * 587 + _b * 114) / 1000 > 128
            except Exception:
                pass
            _pipx_color = "#0e7490" if _is_light else "#89dceb"
            _path_color = (self._c().get("fg_secondary")
                           or self._c().get("fg")
                           or ("#444" if _is_light else "#bac2de"))
            # B174 fix: copy env_table font to preserve QSS pixel-size.
            _bold = _QFont(self.env_table.font())
            _bold.setBold(True)

            # Column 0: Name
            name_item = QTableWidgetItem("  pipx")
            name_item.setFlags(name_item.flags() & ~_Qt.ItemIsEditable)
            name_item.setForeground(_QColor(_pipx_color))
            name_item.setFont(_bold)
            self.env_table.setItem(row, 0, name_item)

            # Column 1: Type — store env_type in UserRole so other code paths
            # (clone, delete, etc.) can read it back.
            type_item = QTableWidgetItem("  📦 pipx")
            type_item.setData(_Qt.UserRole, "pipx")
            type_item.setFlags(type_item.flags() & ~_Qt.ItemIsEditable)
            type_item.setForeground(_QColor(_pipx_color))
            type_item.setFont(_bold)
            self.env_table.setItem(row, 1, type_item)

            # Column 2: Path
            path_item = QTableWidgetItem(f"  {pipx_path}")
            path_item.setToolTip(str(pipx_path))
            path_item.setFlags(path_item.flags() & ~_Qt.ItemIsEditable)
            path_item.setForeground(_QColor(_path_color))
            self.env_table.setItem(row, 2, path_item)

            # Column 3: Runtime (Python version)
            py_ver = marker_data["python_version"]
            runtime_item = QTableWidgetItem(py_ver)
            runtime_item.setFlags(runtime_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 3, runtime_item)

            # Column 4: Packages — empty pipx == 0
            pkg_item = QTableWidgetItem("0")
            pkg_item.setFlags(pkg_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 4, pkg_item)

            # Column 5: Size — directory was just wiped by delete_venv, so
            # the fresh pipx home is empty (0 B). Reflect that in the cell
            # instead of an inscrutable "—" so the user sees their delete
            # actually freed the space.
            size_item = QTableWidgetItem("0.0 B")
            size_item.setFlags(size_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 5, size_item)

            # Column 6: Created
            created_item = QTableWidgetItem(marker_data["created"])
            created_item.setFlags(created_item.flags() & ~_Qt.ItemIsEditable)
            self.env_table.setItem(row, 6, created_item)

            self._log.info(f"pipx readd: row inserted at index {row}")

            # Refresh the header summary line ("/home/... • N env(s) • X GB",
            # "pipx • 1 env(s) • Y MB", "total • Z GB") so it reflects the
            # post-delete state. Without this the header still shows the
            # pre-delete pipx size until the next manual Refresh.
            try:
                if hasattr(self, "_update_env_summary"):
                    self._update_env_summary()
            except Exception as _se:
                self._log.debug(f"pipx readd: summary refresh skipped: {_se}")
        except Exception as e:
            self._log.warning(f"pipx readd: table insert failed: {e}")
            # Last resort: just trigger a light refresh, no force
            self._refresh_env_list()

    def _clone_env(self):
        source = self._get_selected_env_name()
        if not source:
            return
        new_name, ok = QInputDialog.getText(
            self, "Clone Environment",
            f"Enter name for the clone of '{source}':",
            text=f"{source}-clone",
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        # Get env type and path for educational cmd panel
        _src_env_type = "venv"
        _env_path = None
        _sel_row = self.env_table.currentRow()
        if _sel_row >= 0:
            _path_item = self.env_table.item(_sel_row, 2)
            _type_item = self.env_table.item(_sel_row, 1)
            if _path_item:
                _env_path = _path_item.toolTip() or _path_item.text().strip()
            if _type_item:
                _src_env_type = _type_item.data(Qt.UserRole) or "venv"
        _display_path = _env_path or str(self.venv_manager.base_dir / source)

        # Update educational cmd panel
        self._update_cmd_panel(action="clone", env_type=_src_env_type, name=source, env_path=_display_path)

        # Progress dialog
        self.clone_progress = QProgressDialog(
            f"Cloning '{source}' to '{new_name}'...", "Cancel", 0, 0, self
        )
        self.clone_progress.setWindowTitle("Cloning Environment")
        self.clone_progress.setMinimumWidth(400)
        self.clone_progress.setWindowModality(Qt.WindowModal)
        self.clone_progress.show()

        # Worker
        self.clone_worker = CloneWorker(self.venv_manager, source, new_name)
        def _on_clone_progress(msg):
            self.clone_progress.setLabelText(f"⏳ {msg}")
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"▶ {msg}")
        self.clone_worker.progress.connect(_on_clone_progress)
        self.clone_worker.finished.connect(self._on_clone_finished)
        self.clone_progress.canceled.connect(self._on_clone_cancel)
        self.clone_worker.start()

    def _on_clone_finished(self, success, message):
        self.clone_progress.close()
        if success:
            # Force memory cache clear so deleted env disappears immediately
            self.venv_manager.invalidate_all_caches()
            self._refresh_env_list()
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                self._cmd_panel_live.setText(f"✅ {message}")
        else:
            if "cancelled" not in message.lower():
                QMessageBox.critical(self, "Error", message)
            self.statusBar().showMessage(message)
            if hasattr(self, "_cmd_panel_live"):
                first_line = message.splitlines()[0] if message else "Failed"
                self._cmd_panel_live.setText(f"❌ {first_line}")

    def _on_clone_cancel(self):
        if hasattr(self, 'clone_worker') and self.clone_worker.isRunning():
            self.clone_worker.cancel()
            self.clone_worker.wait(5000)
            self._refresh_env_list()

