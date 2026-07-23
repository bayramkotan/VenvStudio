"""VenvStudio - MainWindow: Quick Launch Mixin
Quick Launch panel logic — env selector, installed-package buttons
(moved from main_window.py).
"""
from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtCore import QThread, Signal

from src.core.venv_manager import VenvManager


class QuickLaunchMixin:
    """Mixin for MainWindow: Quick Launch panel."""

    def _on_ql_env_changed(self, idx):
        """Sol sidebar QL dropdown değişti — her şeyi sync et."""
        if not hasattr(self, "ql_env_selector"):
            return
        venv_name = self.ql_env_selector.itemData(idx)
        if not venv_name:
            self._rebuild_ql_buttons(set())
            return
        venv_path = self._get_env_path(venv_name) or self.venv_manager.base_dir / venv_name
        if not venv_path.exists() and not (venv_path.parent / ".venvstudio_env").exists():
            pass  # pipx path may not have standard structure
        # Env tablosunda ilgili satırı seç
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == venv_name:
                self.env_table.blockSignals(True)
                self.env_table.selectRow(row)
                self.env_table.blockSignals(False)
                break
        # package_panel sync (sayfa değiştirme!)
        if self.package_panel is not None: self.package_panel.set_venv(venv_path)

    def _ql_load_env_packages(self, venv_name: str):
        """Sadece QL için paket listesi yükle — sağ paneli değiştirme."""
        from pathlib import Path
        from src.core.pip_manager import PipManager
        from src.core.venv_manager import VenvManager
        import json

        venv_path = self._get_env_path(venv_name) or self.venv_manager.base_dir / venv_name
        if not venv_path.exists() and not (venv_path.parent / ".venvstudio_env").exists():
            pass  # pipx path may not have standard structure

        class _QLWorker(QThread):
            done = Signal(str, list)
            def __init__(self, venv_path, parent=None):
                super().__init__(parent)
                self._vp = venv_path
            def run(self):
                try:
                    import subprocess, sys
                    python = self._vp / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                    # B151: suppress console flash on Windows
                    _kw = dict(capture_output=True, text=True, timeout=30)
                    if sys.platform == "win32":
                        _kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
                    r = subprocess.run(
                        [str(python), "-m", "pip", "list", "--format=json"],
                        **_kw
                    )
                    if r.returncode == 0:
                        pkgs = json.loads(r.stdout)
                        self.done.emit(self._vp.name, pkgs)
                except Exception:
                    self.done.emit(self._vp.name, [])

        def _on_done(env_name, pkgs):
            # Cache'e kaydet
            try:
                vm = VenvManager(self.config.get_venv_base_dir())
                all_cache = vm._load_all_cache()
                key = "pkg_list:" + str(self.venv_manager.base_dir / env_name).replace("\\", "/")
                all_cache[key] = {"packages": [{"name": p["name"], "version": p["version"]} for p in pkgs], "needs_refresh": 0}
                vm._save_all_cache(all_cache)
            except Exception:
                pass
            # Sadece QL hâlâ bu env'i gösteriyorsa güncelle
            if hasattr(self, "ql_env_selector") and self.ql_env_selector.currentData() == env_name:
                installed = {p["name"].lower() for p in pkgs}
                self._rebuild_ql_buttons(installed)

        self._ql_worker = _QLWorker(venv_path, parent=self)
        self._ql_worker.done.connect(_on_done)
        self._ql_worker.start()

    def _get_installed_from_cache(self, env_name: str) -> set:
        """Cache'den paket isimlerini oku — subprocess yok."""
        try:
            from src.core.venv_manager import VenvManager
            vm = VenvManager(self.config.get_venv_base_dir())
            all_cache = vm._load_all_cache()
            venv_path = self.venv_manager.base_dir / env_name
            our_path = str(venv_path).lower().replace("\\", "/")
            for key, entry in all_cache.items():
                if not key.startswith("pkg_list:"):
                    continue
                key_path = key[len("pkg_list:"):].lower().replace("\\", "/")
                if key_path == our_path and entry.get("needs_refresh", 1) == 0:
                    pkgs = entry.get("packages", [])
                    if pkgs:
                        return {p["name"].lower() for p in pkgs}
        except Exception:
            pass
        return set()

    def _sync_ql_selector(self, env_name: str):
        """Üst dropdown değişince QL + env tablosunu sync et."""
        # QL selector
        if hasattr(self, "ql_env_selector"):
            idx = self.ql_env_selector.findData(env_name)
            if idx >= 0:
                self.ql_env_selector.blockSignals(True)
                self.ql_env_selector.setCurrentIndex(idx)
                self.ql_env_selector.blockSignals(False)
        # Env tablosu satırı
        for row in range(self.env_table.rowCount()):
            item = self.env_table.item(row, 0)
            if item and item.text().strip() == env_name:
                self.env_table.blockSignals(True)
                self.env_table.selectRow(row)
                self.env_table.blockSignals(False)
                break

    def _update_ql_buttons(self, env_name: str = ""):
        """package_panel'deki yükleme bittikten sonra çağrılır — fresh data kullan."""
        # installed_package_names her zaman şu anki package_panel env'ine aittir
        installed = getattr(self.package_panel, "installed_package_names", set())
        self._rebuild_ql_buttons(installed)
        # QL selector'ı package_panel'in env'iyle sync et
        if hasattr(self, "ql_env_selector") and self.package_panel is not None and self.package_panel.pip_manager:
            current_env = self.package_panel.pip_manager.venv_path.name
            self._sync_ql_selector(current_env)

    def _rebuild_ql_buttons(self, installed: set):
        """Verilen installed set'e göre QL butonlarını yeniden oluştur."""
        if not hasattr(self, "ql_buttons_layout"):
            return
        while self.ql_buttons_layout.count():
            item = self.ql_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        c = self._c()
        app_defs = getattr(self.package_panel, "app_definitions", [])
        has_any = False
        # env path for detecting system apps installed INSIDE a conda env
        _envp = None
        if self.package_panel is not None and getattr(self.package_panel, "pip_manager", None):
            _envp = self.package_panel.pip_manager.venv_path

        def _system_app_present(app) -> bool:
            """System apps (package == '__system__') aren't pip packages, so
            the pip-list check never matched them — R/DBeaver etc. installed
            into a conda env were always filtered out. Detect them by exe:
            on system PATH, or inside the current env's bin/Scripts."""
            import shutil as _sh
            from pathlib import Path as _P
            from src.utils.platform_utils import get_platform as _gp
            _cmds = app.get("system_commands", {})
            _exe = (_cmds.get(_gp()) or _cmds.get("linux", [""]))[0]
            if not _exe:
                return False
            if _sh.which(_exe):
                return True
            if _envp:
                for sub in (_P(_envp) / "Scripts", _P(_envp) / "bin",
                            _P(_envp) / "Library" / "bin"):
                    if (sub / _exe).exists() or (sub / (_exe + ".exe")).exists():
                        return True
            return False

        # Respect each card's env_types, exactly like the launcher grid does.
        # Without this, system apps that also exist on the system PATH (R,
        # DBeaver...) showed up under EVERY env, not just conda ones.
        _env_type = getattr(self.package_panel, "_current_env_type", "venv")
        if _env_type in ("uv", "poetry", "pipx"):
            _match = {"venv"}
        elif _env_type == "conda":
            _match = {"venv", "conda"}
        else:
            _match = {_env_type}

        for app in app_defs:
            _types = set(app.get("env_types",
                ["venv"] if not app.get("system_app")
                else ["conda", "system_tools"]))
            if not (_match & _types):
                continue
            if app.get("system_app") or app.get("package", "").lower() == "__system__":
                if not _system_app_present(app):
                    continue
            elif app["package"].lower() not in installed:
                continue
            has_any = True
            btn = QPushButton(f"{app['icon']} {app['name']}")
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ font-size: {self._c()['fs_small']}px; text-align: left; padding: 2px 8px; "
                f"background-color: {c['sidebar']}; color: {c['fg']}; "
                f"border: 1px solid {c['border']}; border-radius: 4px; }}"
                f"QPushButton:hover {{ background-color: {c['hover']}; border-color: {c['accent']}; }}"
            )
            btn.clicked.connect(lambda checked, a=app: self.package_panel._launch_app(a) if self.package_panel else None)
            self.ql_buttons_layout.addWidget(btn)
        if not has_any:
            lbl = QLabel("  No apps installed")
            lbl.setStyleSheet(f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px; padding: 4px;")
            self.ql_buttons_layout.addWidget(lbl)

