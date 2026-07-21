"""VenvStudio - Package Panel: Package Operations Mixin
Catalog population, install/uninstall, apply-changes logic
(moved from package_panel.py).
"""
from src.core.venv_manager_common import _fmt_path
import os
import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QMessageBox, QPushButton, QTableWidgetItem, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from src.utils.i18n import tr
from src.utils.platform_utils import get_platform, get_python_executable, subprocess_args
from src.utils.constants import PACKAGE_CATALOG, COMMAND_HINTS
from src.gui.package_panel_common import WorkerThread

# Docs URLs for popular packages
_PACKAGE_DOCS = {
    "numpy": "https://numpy.org/doc/",
    "pandas": "https://pandas.pydata.org/docs/",
    "matplotlib": "https://matplotlib.org/stable/",
    "scipy": "https://docs.scipy.org/doc/scipy/",
    "scikit-learn": "https://scikit-learn.org/stable/documentation.html",
    "tensorflow": "https://www.tensorflow.org/api_docs",
    "torch": "https://pytorch.org/docs/stable/",
    "keras": "https://keras.io/api/",
    "xgboost": "https://xgboost.readthedocs.io/",
    "lightgbm": "https://lightgbm.readthedocs.io/",
    "seaborn": "https://seaborn.pydata.org/",
    "plotly": "https://plotly.com/python/",
    "bokeh": "https://docs.bokeh.org/",
    "altair": "https://altair-viz.github.io/",
    "dash": "https://dash.plotly.com/",
    "streamlit": "https://docs.streamlit.io/",
    "gradio": "https://www.gradio.app/docs/",
    "panel": "https://panel.holoviz.org/",
    "voila": "https://voila.readthedocs.io/",
    "mlflow": "https://mlflow.org/docs/latest/index.html",
    "tensorboard": "https://www.tensorflow.org/tensorboard",
    "datasette": "https://docs.datasette.io/",
    "fastapi": "https://fastapi.tiangolo.com/",
    "flask": "https://flask.palletsprojects.com/",
    "django": "https://docs.djangoproject.com/",
    "sqlalchemy": "https://docs.sqlalchemy.org/",
    "requests": "https://requests.readthedocs.io/",
    "httpx": "https://www.python-httpx.org/",
    "aiohttp": "https://docs.aiohttp.org/",
    "pydantic": "https://docs.pydantic.dev/",
    "celery": "https://docs.celeryq.dev/",
    "redis": "https://redis-py.readthedocs.io/",
    "pillow": "https://pillow.readthedocs.io/",
    "opencv-python": "https://docs.opencv.org/",
    "nltk": "https://www.nltk.org/",
    "spacy": "https://spacy.io/api",
    "transformers": "https://huggingface.co/docs/transformers/",
    "pytest": "https://docs.pytest.org/",
    "black": "https://black.readthedocs.io/",
    "mypy": "https://mypy.readthedocs.io/",
    "jupyter": "https://jupyter.org/documentation",
    "jupyterlab": "https://jupyterlab.readthedocs.io/",
    "ipython": "https://ipython.readthedocs.io/",
    "rich": "https://rich.readthedocs.io/",
    "click": "https://click.palletsprojects.com/",
    "typer": "https://typer.tiangolo.com/",
    "pyside6": "https://doc.qt.io/qtforpython/",
    "pyqt6": "https://www.riverbankcomputing.com/static/Docs/PyQt6/",
    "sqlmodel": "https://sqlmodel.tiangolo.com/",
    "alembic": "https://alembic.sqlalchemy.org/",
    "paramiko": "https://www.paramiko.org/",
    "cryptography": "https://cryptography.io/en/latest/",
    "arrow": "https://arrow.readthedocs.io/",
    "pendulum": "https://pendulum.eustace.io/docs/",
    "dask": "https://docs.dask.org/",
    "polars": "https://docs.pola.rs/",
    "pyarrow": "https://arrow.apache.org/docs/python/",
    "numba": "https://numba.readthedocs.io/",
    "sympy": "https://docs.sympy.org/",
    "statsmodels": "https://www.statsmodels.org/stable/",
    "networkx": "https://networkx.org/documentation/",
    "scrapy": "https://docs.scrapy.org/",
    "beautifulsoup4": "https://www.crummy.com/software/BeautifulSoup/bs4/doc/",
    "selenium": "https://selenium-python.readthedocs.io/",
    "playwright": "https://playwright.dev/python/docs/intro",
    "pymongo": "https://pymongo.readthedocs.io/",
    "motor": "https://motor.readthedocs.io/",
    "psycopg2": "https://www.psycopg.org/docs/",
    "aiomysql": "https://aiomysql.readthedocs.io/",
    "boto3": "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html",
    "google-cloud-storage": "https://cloud.google.com/python/docs/reference/storage/latest",
    "azure-storage-blob": "https://learn.microsoft.com/en-us/python/api/azure-storage-blob/",
    "docker": "https://docker-py.readthedocs.io/",
    "fabric": "https://docs.fabfile.org/",
    "ansible": "https://docs.ansible.com/",
    # CLI/TUI
    "rich": "https://rich.readthedocs.io/",
    "textual": "https://textual.textualize.io/",
    "prompt_toolkit": "https://python-prompt-toolkit.readthedocs.io/",
    "questionary": "https://questionary.readthedocs.io/",
    "blessed": "https://blessed.readthedocs.io/",
    "urwid": "http://urwid.org/",
    "asciimatics": "https://asciimatics.readthedocs.io/",
    "tqdm": "https://tqdm.github.io/",
    "alive-progress": "https://github.com/rsalmei/alive-progress",
    "colorama": "https://github.com/tartley/colorama",
    "click": "https://click.palletsprojects.com/",
    "typer": "https://typer.tiangolo.com/",
    "tabulate": "https://github.com/astanin/python-tabulate",
    "prettytable": "https://prettytable.readthedocs.io/",
}


class PackageOpsMixin:
    """Mixin for PackagePanel: catalog population, install/uninstall, apply changes."""

    def _get_catalog_lookup(self) -> dict:
        """Build {pkg_name_lower: (desc, category)} from PACKAGE_CATALOG.
        Uses EXACTLY the same iteration as _populate_catalog.
        """
        lookup = {}
        for cat_name, cat_data in PACKAGE_CATALOG.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                name = pkg["name"]
                desc = pkg["desc"]
                lookup[name.lower()] = (desc, cat_name)
                lookup[name.lower().replace("-", "_")] = (desc, cat_name)
                lookup[name.lower().replace("_", "-")] = (desc, cat_name)
        return lookup

    def _on_packages_loaded(self, packages, loaded_for_path: str = ""):
        """Called when async package loading finishes.

        ``loaded_for_path`` is the venv path the background worker was
        scanning when it emitted. If the user has switched envs since the
        scan started, that snapshot won't match the currently-selected
        pip_manager.venv_path — in that case we **must** discard the result
        instead of caching it. Otherwise env A's packages get written under
        env B's cache key, which silently breaks the preset badges, the
        package count header, and any other code that trusts the cache.
        """
        try:
            from src.utils.logger import get_logger
            _current_path = ""
            if self.pip_manager and getattr(self.pip_manager, "venv_path", None):
                _current_path = str(self.pip_manager.venv_path)
            get_logger("venvstudio.pkg_cache").debug(
                f"📥 [PkgCache] _on_packages_loaded called count={len(packages) if packages else 0} "
                f"loaded_for={_fmt_path(loaded_for_path)} current={_fmt_path(_current_path)}"
            )
        except Exception:
            pass
        if not self.pip_manager:
            return

        # Stale-result check (B187 race fix): if the worker emitted for a
        # different env than the one currently selected, drop the result.
        # Comparing string forms because the worker captures a snapshot.
        try:
            _current = str(self.pip_manager.venv_path) if self.pip_manager.venv_path else ""
            if loaded_for_path and _current and loaded_for_path != _current:
                from src.utils.logger import get_logger
                get_logger("venvstudio.pkg_cache").info(
                    f"🗑️ [PkgCache] discarding stale result: was for {_fmt_path(loaded_for_path)}, "
                    f"now on {_fmt_path(_current)}"
                )
                return
        except Exception:
            pass

        # Save to cache
        self._save_pkg_cache(packages)

        # Store both dash and underscore variants for robust matching (e.g. quarto-cli ↔ quarto_cli)
        self.installed_package_names = set()
        for pkg in packages:
            n = pkg.name.lower()
            self.installed_package_names.add(n)
            self.installed_package_names.add(n.replace("-", "_"))
            self.installed_package_names.add(n.replace("_", "-"))

        self.packages_table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        count = len(packages)
        self.pkg_count_label.setText(f"{count} packages")
        self.env_pkg_count.setText(f"{count} packages installed")
        env_name = self.env_selector.currentText()
        self.status_label.setText(f"Environment: {env_name}")

        self._populate_catalog()
        self._update_launcher_status()
        self._update_preset_badges()
        # Notify main window to update quick launch buttons
        if hasattr(self, "_ql_update_callback") and callable(self._ql_update_callback):
            _current_env = self.pip_manager.venv_path.name if self.pip_manager else ""
            self._ql_update_callback(env_name=_current_env)

        # B182 race fix: if an install/uninstall just finished and asked us
        # to notify MainWindow when the new pkg count is known, emit now.
        # The cache was just written above by _save_pkg_cache(packages), so
        # MainWindow's _refresh_current_env_row will see the fresh value
        # instead of racing with the async load.
        if getattr(self, "_emit_env_refresh_after_load", False):
            self._emit_env_refresh_after_load = False
            try:
                self.env_refresh_requested.emit(len(packages))
            except Exception:
                pass

    def refresh_packages(self):
        """Refresh installed packages list - invalidates cache and async reloads."""
        self._invalidate_pkg_cache()
        self._async_refresh_packages(force=True)
        return

    def _refresh_packages_sync_legacy(self):
        """Legacy sync refresh - kept for internal use only."""
        if not self.pip_manager:
            return

        packages = self.pip_manager.list_packages()
        # Store both dash and underscore variants for robust matching (e.g. quarto-cli ↔ quarto_cli)
        self.installed_package_names = set()
        for pkg in packages:
            n = pkg.name.lower()
            self.installed_package_names.add(n)
            self.installed_package_names.add(n.replace("-", "_"))
            self.installed_package_names.add(n.replace("_", "-"))

        self.packages_table.setRowCount(len(packages))
        for i, pkg in enumerate(packages):
            name_item = QTableWidgetItem(pkg.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 0, name_item)

            ver_item = QTableWidgetItem(pkg.version)
            ver_item.setFlags(ver_item.flags() & ~Qt.ItemIsEditable)
            self.packages_table.setItem(i, 1, ver_item)

            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.packages_table.setCellWidget(i, 2, cb_widget)

        count = len(packages)
        self.pkg_count_label.setText(f"{count} packages")
        self.env_pkg_count.setText(f"{count} packages installed")

        # Update catalog checkboxes
        self._populate_catalog()
        # Update launcher app status
        self._update_launcher_status()
        # Update preset badges
        self._update_preset_badges()

    # ── Catalog ──

    def _populate_catalog(self):
        selected = self.category_combo.currentData()
        self.catalog_table.setRowCount(0)
        self._catalog_initial_state = {}

        categories = PACKAGE_CATALOG if selected == "all" else {selected: PACKAGE_CATALOG.get(selected, {})}

        # Include custom catalog packages from config
        from src.core.config_manager import ConfigManager
        try:
            config = self.config if self.config else __import__("src.core.config_manager", fromlist=["ConfigManager"]).ConfigManager()
            custom_pkgs = config.get("custom_catalog", [])
        except Exception:
            custom_pkgs = []

        if custom_pkgs:
            # Group custom packages by category
            custom_groups = {}
            for p in custom_pkgs:
                cat = p.get("category", "⭐ Custom")
                if cat not in custom_groups:
                    custom_groups[cat] = {"icon": "⭐", "packages": []}
                custom_groups[cat]["packages"].append({"name": p["name"], "desc": p.get("desc", "")})

            for cat_name, cat_data in custom_groups.items():
                if selected == "all" or selected == cat_name:
                    if cat_name not in categories:
                        categories[cat_name] = cat_data
                    else:
                        # Merge into existing category
                        categories[cat_name]["packages"].extend(cat_data["packages"])

        row = 0
        for cat_name, cat_data in categories.items():
            if not cat_data:
                continue
            for pkg in cat_data.get("packages", []):
                self.catalog_table.insertRow(row)

                is_installed = pkg["name"].lower() in self.installed_package_names

                cb = QCheckBox()
                cb.setChecked(is_installed)
                cb.stateChanged.connect(self._on_catalog_checkbox_changed)
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.catalog_table.setCellWidget(row, 0, cb_widget)

                name_item = QTableWidgetItem(pkg["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_font = QFont()
                name_font.setBold(True)
                name_item.setFont(name_font)
                if is_installed:
                    name_item.setForeground(QColor("#a6e3a1"))
                self.catalog_table.setItem(row, 1, name_item)

                desc_item = QTableWidgetItem(pkg["desc"])
                desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 2, desc_item)

                cat_item = QTableWidgetItem(cat_name)
                cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
                self.catalog_table.setItem(row, 3, cat_item)

                self._catalog_initial_state[row] = is_installed

                # Links column: PyPI + optional Docs
                links_widget = QWidget()
                links_layout = QHBoxLayout(links_widget)
                links_layout.setContentsMargins(2, 1, 2, 1)
                links_layout.setSpacing(3)
                pkg_name_for_link = pkg["name"]
                docs_url = _PACKAGE_DOCS.get(pkg_name_for_link.lower())

                pypi_btn = QPushButton("PyPI")
                pypi_btn.setFixedSize(34, 20)
                pypi_btn.setStyleSheet(
                    f"QPushButton {{ font-size: {self._c()['fs_tiny']}px; padding: 0; background: {self._c()['secondary']}; "
                    "color: #89b4fa; border: 1px solid #45475a; border-radius: 3px; }"
                    "QPushButton:hover { background: #45475a; }"
                )
                pypi_btn.clicked.connect(lambda _, n=pkg_name_for_link: self._open_pypi(n))
                links_layout.addWidget(pypi_btn)

                if docs_url:
                    docs_btn = QPushButton("Docs")
                    docs_btn.setFixedSize(34, 20)
                    docs_btn.setStyleSheet(
                        f"QPushButton {{ font-size: {self._c()['fs_tiny']}px; padding: 0; background: {self._c()['secondary']}; "
                        "color: #a6e3a1; border: 1px solid #45475a; border-radius: 3px; }"
                        "QPushButton:hover { background: #45475a; }"
                    )
                    docs_btn.clicked.connect(lambda _, u=docs_url: __import__("src.utils.platform_utils", fromlist=["open_url"]).open_url(u))
                    links_layout.addWidget(docs_btn)

                links_layout.addStretch()
                self.catalog_table.setCellWidget(row, 4, links_widget)

                row += 1

        self._update_apply_button()

    def _on_catalog_checkbox_changed(self):
        self._update_apply_button()

    def _update_apply_button(self):
        """Enable Apply button only if there are actual changes."""
        to_install, to_uninstall = self._get_catalog_changes()
        has_changes = bool(to_install or to_uninstall)
        self.apply_btn.setEnabled(has_changes)

        if has_changes:
            parts = []
            if to_install:
                parts.append(f"+{len(to_install)} install")
            if to_uninstall:
                parts.append(f"-{len(to_uninstall)} remove")
            self.changes_label.setText(" | ".join(parts))
        else:
            self.changes_label.setText("")

    def _get_catalog_changes(self):
        to_install = []
        to_uninstall = []

        for row in range(self.catalog_table.rowCount()):
            cb_widget = self.catalog_table.cellWidget(row, 0)
            if not cb_widget:
                continue
            cb = cb_widget.findChild(QCheckBox)
            if not cb:
                continue
            name_item = self.catalog_table.item(row, 1)
            if not name_item:
                continue

            pkg_name = name_item.text()
            is_checked = cb.isChecked()
            was_installed = self._catalog_initial_state.get(row, False)

            if is_checked and not was_installed:
                to_install.append(pkg_name)
            elif not is_checked and was_installed:
                to_uninstall.append(pkg_name)

        return to_install, to_uninstall

    def _apply_catalog_changes(self):
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.")
            return

        to_install, to_uninstall = self._get_catalog_changes()

        if not to_install and not to_uninstall:
            QMessageBox.information(self, "No Changes", "No changes detected.")
            return

        # Build detailed confirm message
        msg_parts = []
        if to_uninstall:
            msg_parts.append(f"🗑️ Remove ({len(to_uninstall)}):\n  • " + "\n  • ".join(to_uninstall))
        if to_install:
            msg_parts.append(f"📦 Install ({len(to_install)}):\n  • " + "\n  • ".join(to_install))

        reply = QMessageBox.question(
            self, "Apply Changes",
            "Apply the following changes?\n\n" + "\n\n".join(msg_parts),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint (env-type aware)
        _env_type = getattr(self, "_current_env_type", "venv")
        _install_cmds = {
            "venv": "pip install {packages}", "uv": "uv pip install {packages}",
            "poetry": "poetry add {packages}",
            "conda": "conda install {packages}", "pipx": "pipx install {packages}",
        }
        _uninstall_cmds = {
            "venv": "pip uninstall -y {packages}", "uv": "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda": "conda remove {packages}", "pipx": "pipx uninstall {packages}",
        }
        cmds = []
        if to_uninstall:
            cmds.append(_uninstall_cmds.get(_env_type, COMMAND_HINTS["uninstall"]).format(packages=" ".join(to_uninstall)))
        if to_install:
            cmds.append(_install_cmds.get(_env_type, COMMAND_HINTS["install"]).format(packages=" ".join(to_install)))
        self._show_command_hint("Apply Changes", " && ".join(cmds))

        self._set_busy(True)
        self.output_log.clear()

        if to_uninstall:
            self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, to_uninstall)
            self.current_worker.progress.connect(self._on_progress)
            if to_install:
                self.current_worker.finished.connect(
                    lambda ok, msg: self._chain_install(ok, msg, to_install)
                )
            else:
                self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
        elif to_install:
            self._do_install(to_install)

    def _chain_install(self, uninstall_ok, uninstall_msg, to_install):
        if not uninstall_ok:
            self._append_log(f"❌ Uninstall failed: {uninstall_msg[:300]}")
        self._append_log("✅ Uninstall done. Starting install...")
        self._do_install(to_install)

    # ── Install / Uninstall ──

    def _install_packages(self, packages: list, hint_name: str = ""):
        self._pkg_op_hint = hint_name  # preset/app adı — _do_install loglar
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.\nPlease select an environment first.")
            return

        # Pipx envs have no central <env>/bin/python, so the pre-flight checks
        # below (list_packages and `python --version`) raise FileNotFoundError
        # and surface as "Install FAILED: [Errno 2] No such file or directory:
        # '<pipx>/bin/python'" before _do_install / _do_pipx_install can run.
        # Skip them for pipx; the install path itself (_do_pipx_install) is
        # already pipx-aware and handles per-app isolation correctly.
        _env_type = getattr(self, "_current_env_type", "venv")

        # Kurulu paketleri filtrele — sadece kurulu olmayanları kur
        if _env_type != "pipx":
            try:
                installed = {p.name.lower() for p in self.pip_manager.list_packages()}
                import re
                not_installed = []
                already_installed = []
                for pkg in packages:
                    pkg_name = re.split(r'[><=!~;]', pkg)[0].lower().replace("-", "_")
                    pkg_name2 = pkg_name.replace("_", "-")
                    if pkg_name in installed or pkg_name2 in installed:
                        already_installed.append(pkg)
                    else:
                        not_installed.append(pkg)
                if not not_installed:
                    QMessageBox.information(self, "Info", "All packages are already installed.")
                    return
                packages = not_installed
            except Exception:
                pass  # Filtreleme başarısız olursa tüm paketlerle devam et

        # Check Python version — warn if old (some packages may not have pre-built wheels)
        py_warning = ""
        if _env_type != "pipx" and self.pip_manager:
            try:
                venv_key = str(self.pip_manager.venv_path)
                env_py_version = self._launcher_py_version_cache.get(venv_key)
                if not env_py_version:
                    python_exe = get_python_executable(self.pip_manager.venv_path)
                    from src.utils.platform_utils import subprocess_args
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        **subprocess_args(capture_output=True, text=True, timeout=5)
                    )
                    ver_str = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
                    env_py_version = tuple(int(x) for x in ver_str.split(".")[:2])
                    self._launcher_py_version_cache[venv_key] = env_py_version
                if env_py_version and env_py_version < (3, 10):
                    py_warning = (
                        f"\n\n⚠️ Warning: This environment uses Python {env_py_version[0]}.{env_py_version[1]}.\n"
                        f"Some packages (e.g. spacy, torch) may fail to install because\n"
                        f"pre-built wheels are not available for older Python versions.\n"
                        f"Consider creating a new environment with Python 3.11+."
                    )
            except Exception:
                pass

        # Show ALL package names in confirm dialog
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following {len(packages)} package(s)?\n\n• " + "\n• ".join(packages) + py_warning,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Show command hint based on env type
        _env_type = getattr(self, "_current_env_type", "venv")
        _install_cmds = {
            "venv":   "pip install {packages}",
            "uv":     "uv pip install {packages}",
            "poetry": "poetry add {packages}",
            "conda":  "conda install {packages}",
            "pipx":   "pipx install {packages}",
        }
        _cmd_template = _install_cmds.get(_env_type, COMMAND_HINTS["install"])
        cmd = _cmd_template.format(packages=" ".join(packages))
        self._show_command_hint(hint_name or "Install Packages", cmd)

        self._do_install(packages)

    def _do_install(self, packages):
        """Actually start install worker (no confirm dialog)."""
        self._set_busy(True)
        self.output_log.clear()

        # ── Merkezi kurulum logu: env + kaynak (preset/uygulama) + paketler ──
        _env_name = ""
        if self.pip_manager and getattr(self.pip_manager, "venv_path", None):
            _env_name = self.pip_manager.venv_path.name
        _hint = getattr(self, "_pkg_op_hint", "") or "Manual/Direct"
        self._pkg_op_hint = ""
        self._pkg_op_kind = "Install"
        _pk = list(packages)
        _shown = ", ".join(_pk[:8]) + (f" (+{len(_pk) - 8} more)" if len(_pk) > 8 else "")
        from src.utils.logger import get_logger
        get_logger("venvstudio.install").info(
            f"📦 [Install] env='{_env_name}' source='{_hint}' "
            f"packages({len(_pk)}): {_shown}"
        )

        _env_type = getattr(self, "_current_env_type", "venv")
        if _env_type == "conda" and self.pip_manager and self.pip_manager.venv_path:
            # Use conda install instead of pip for conda environments
            _env_path = self.pip_manager.venv_path
            _pkgs = list(packages)

            def _do_conda_install(callback=None):
                from src.core.micromamba_installer import (
                    install_conda_packages, get_micromamba_exe, download_micromamba,
                )
                if not get_micromamba_exe():
                    if callback:
                        callback("Downloading micromamba...")
                    download_micromamba(progress_cb=callback)
                ok = install_conda_packages(
                    _env_path, _pkgs,
                    channels=["conda-forge"],
                    progress_cb=callback,
                )
                return (ok,
                        f"Installed: {', '.join(_pkgs)}" if ok
                        else f"conda install failed for: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_conda_install)
        elif _env_type == "pipx":
            # Use pipx install for each package — with selected Python from marker
            _pkgs = list(packages)
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

            def _do_pipx_install(callback=None):
                import subprocess, sys, shutil
                from src.utils.platform_utils import subprocess_args
                # Find pipx executable — prefer direct binary over python -m pipx
                _pipx_bin = shutil.which("pipx")
                installed = []
                failed = []
                for pkg in _pkgs:
                    if callback:
                        callback(f"pipx install {pkg}...")
                    if _pipx_bin:
                        cmd = [_pipx_bin, "install", pkg]
                    else:
                        _pipx_exe2 = shutil.which("pipx")
                        cmd = [_pipx_exe2, "install", pkg] if _pipx_exe2 else [sys.executable, "-m", "pipx", "install", pkg]
                    # --include-deps lets library packages (numpy, pandas,
                    # flask, sqlalchemy, ...) install successfully. Without
                    # it pipx refuses with "No apps associated with package
                    # X" because pipx is built for CLI tools only. Pipx
                    # itself documents this flag as the workaround. Apps of
                    # dependent packages (e.g. numpy's f2py) are still
                    # exposed which is harmless.
                    cmd.append("--include-deps")
                    if _pipx_python:
                        cmd += ["--python", _pipx_python]
                    r = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=300,
                        **subprocess_args()
                    )
                    if r.returncode == 0:
                        installed.append(pkg)
                    else:
                        failed.append(pkg)
                        # Surface pipx's own error so we can diagnose future
                        # failures without re-running by hand. Truncated to
                        # keep log readable.
                        try:
                            from src.utils.logger import get_logger as _gl
                            _err = (r.stderr or r.stdout or "").strip()
                            if _err:
                                _gl("venvstudio.install").warning(
                                    f"pipx install {pkg} failed (rc={r.returncode}): {_err[:400]}"
                                )
                        except Exception:
                            pass
                if failed:
                    return (False, f"pipx install failed for: {', '.join(failed)}")
                return (True, f"pipx installed: {', '.join(installed)}")

            self.current_worker = WorkerThread(_do_pipx_install)
        else:
            self.current_worker = WorkerThread(self.pip_manager.install_packages, packages)

        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

    def _copy_install_command(self):
        """Copy the install command for entered packages (env-type aware)."""
        text = self.manual_input.toPlainText().strip()
        if not text:
            self.status_label.setText("⚠️ No packages entered")
            return

        # Clean the input (same logic as _install_manual)
        import re
        noise = {"pip", "pip3", "python", "python3", "-m", "install", "uninstall",
                 "--upgrade", "--user", "-U", "-r", "--force-reinstall", "--no-cache-dir",
                 "--break-system-packages", "sudo", "&&", "||", "|", ";"}
        cleaned = []
        seen = set()
        for line in text.splitlines():
            line = line.strip().replace(",", " ")
            if not line or line.startswith("#"):
                continue
            for token in line.split():
                t = token.strip()
                if not t or t.lower() in noise or t.startswith("-") or t.isdigit():
                    continue
                if not re.search(r'[a-zA-Z]', t):
                    continue
                key = t.lower()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(t)

        if cleaned:
            _env_type = getattr(self, "_current_env_type", "venv")
            _cmd_prefixes = {
                "venv":   "pip install",
                "uv":     "uv pip install",
                "poetry": "poetry add",
                "conda":  "conda install",
                "pipx":   "pipx install",
            }
            _prefix = _cmd_prefixes.get(_env_type, "pip install")
            cmd = f"{_prefix} {' '.join(cleaned)}"
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(cmd)
            self.status_label.setText(f"📋 Copied: {cmd}")
        else:
            self.status_label.setText("⚠️ No valid package names found")

    def _install_manual(self):
        text = self.manual_input.toPlainText().strip()
        if not text:
            return

        # Normalize non-ASCII characters → ASCII equivalents
        # Türkçe ve diğer dillerdeki harfler → İngilizce karşılıkları
        import unicodedata
        _char_map = str.maketrans({
            'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
            'ş': 's', 'Ş': 'S', 'ç': 'c', 'Ç': 'C',
            'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
            'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'õ': 'o',
        })
        text = text.translate(_char_map)

        # Normalize version separators: == = => >=, kurulum => install
        # "numpy=1.0" veya "numpy =1.0" → "numpy==1.0"
        import re
        # Boşluklu versiyon: "numpy == 1.0" → "numpy==1.0"
        text = re.sub(r'\s*([><=!~]+)\s*', r'\1', text)
        # Tek = (atama değil paket versiyonu): "numpy=1.0" → "numpy==1.0"
        text = re.sub(r'(?<![=<>!~])=(?!=)', '==', text)

        # Noise words to filter out
        noise = {"pip", "pip3", "python", "python3", "-m", "install", "uninstall",
                 "--upgrade", "--user", "-u", "-r", "--force-reinstall", "--no-cache-dir",
                 "--break-system-packages", "sudo", "&&", "||", "|", ";",
                 "list", "freeze", "show", "search", "check", "download",
                 "wheel", "hash", "config", "cache", "debug", "index",
                 "requirements.txt", "setup.py", "pyproject.toml"}

        cleaned = []
        seen = set()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Replace commas, semicolons, pipes with spaces
            line = line.replace(",", " ").replace(";", " ").replace("|", " ")
            for token in line.split():
                t = token.strip()
                if not t:
                    continue
                # Küçük harfe çevir (paket adı kısmını)
                pkg_and_ver = re.split(r'([><=!~;])', t, maxsplit=1)
                pkg_name_raw = pkg_and_ver[0].lower()
                rest = "".join(pkg_and_ver[1:]) if len(pkg_and_ver) > 1 else ""
                t_normalized = pkg_name_raw + rest

                # Skip noise words
                if pkg_name_raw in noise:
                    continue
                # Skip pure numbers
                if t_normalized.isdigit():
                    continue
                # Skip flags
                if t_normalized.startswith("-"):
                    continue
                # Skip tokens with no letters
                if not re.search(r'[a-zA-Z]', t_normalized):
                    continue
                # Valid package name check
                pkg_name = re.split(r'[><=!~;]', t_normalized)[0]
                if not pkg_name or not re.match(r'^[a-z0-9]', pkg_name):
                    continue
                # Deduplicate
                key = pkg_name_raw
                if key not in seen:
                    seen.add(key)
                    cleaned.append(t_normalized)

        if not cleaned:
            QMessageBox.information(
                self, "Info",
                "No valid package names found.\n\n"
                "Just enter package names, e.g.:\n"
                "numpy pandas matplotlib"
            )
            return

        self._install_packages(cleaned)

    def _uninstall_selected(self):
        if not self.pip_manager:
            return

        packages = []
        for row in range(self.packages_table.rowCount()):
            cb_widget = self.packages_table.cellWidget(row, 2)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    item = self.packages_table.item(row, 0)
                    if item:
                        packages.append(item.text())

        if not packages:
            QMessageBox.information(self, "Info", "No packages selected for uninstall.")
            return

        reply = QMessageBox.warning(
            self, "Confirm Uninstall",
            f"Uninstall {len(packages)} package(s)?\n\n• " + "\n• ".join(packages),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        _env_name = ""
        if self.pip_manager and getattr(self.pip_manager, "venv_path", None):
            _env_name = self.pip_manager.venv_path.name
        self._pkg_op_kind = "Uninstall"
        _shown = ", ".join(packages[:8]) + (f" (+{len(packages) - 8} more)" if len(packages) > 8 else "")
        from src.utils.logger import get_logger
        get_logger("venvstudio.install").info(
            f"🗑️ [Uninstall] env='{_env_name}' packages({len(packages)}): {_shown}"
        )

        _env_type = getattr(self, "_current_env_type", "venv")
        _uninstall_cmds = {
            "venv":   "pip uninstall -y {packages}",
            "uv":     "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda":  "conda remove {packages}",
            "pipx":   "pipx uninstall {packages}",
        }
        cmd = _uninstall_cmds.get(_env_type, COMMAND_HINTS["uninstall"]).format(packages=" ".join(packages))
        self._show_command_hint("Uninstall Packages", cmd)

        self._set_busy(True)
        self.current_worker = WorkerThread(self.pip_manager.uninstall_packages, packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

