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
    "shiny": "https://shiny.posit.co/py/",
    "reflex": "https://reflex.dev/docs/",
    "nicegui": "https://nicegui.io/documentation",
    "chainlit": "https://docs.chainlit.io/",
}


def _check_pypi_wheel_availability(pkg_name, py_major, py_minor, platform_tag, timeout=5):
    """
    N9 live compatibility check (2026-08-12): query PyPI's JSON API for the
    package's latest release and check whether a wheel exists for
    (py_major, py_minor) on platform_tag ("win"/"linux"/"macos"). This is
    the fallback tier -- CONFLICT_RULES (the manual list) is always checked
    FIRST by the caller; this only runs for packages that list has no entry
    for, so a maintained manual note always wins over a live guess.

    Returns a dict, never raises:
      {"checked": bool,             # did the query succeed at all?
       "compatible": bool | None,   # True/False if determinable, else None
       "available_pyvers": [str],   # e.g. ["3.9", "3.10", "3.11"]
       "has_sdist_only": bool,      # no wheels at all for ANY python/platform
       "error": str | None}

    Ground-truth tested against real PyPI (2026-08-12): pygame/3.14/win ->
    compatible=False, available_pyvers up to 3.13; requests/3.14/win ->
    compatible=True (pure-python wheel); nonexistent package -> checked=False.
    """
    result = {"checked": False, "compatible": None, "available_pyvers": [],
              "has_sdist_only": False, "error": None}
    try:
        import urllib.request, json, re
        url = f"https://pypi.org/pypi/{pkg_name}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "VenvStudio/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        latest = data["info"]["version"]
        files = data["releases"].get(latest, [])
        if not files:
            return result

        plat_markers = {
            "win":   ("win32", "win_amd64", "win_arm64"),
            "linux": ("manylinux", "linux_"),
            "macos": ("macosx",),
        }.get(platform_tag, ())

        target_cp = f"cp{py_major}{py_minor}"
        found_wheels = []
        pure_py_wheel = False
        has_wheel_at_all = False
        cp_minors_seen = set()

        for f in files:
            fn = f["filename"]
            if f["packagetype"] != "bdist_wheel":
                continue
            has_wheel_at_all = True
            if "-none-any.whl" in fn:
                pure_py_wheel = True
            m = re.search(r'-cp3(\d{1,2})-', fn)
            if m:
                cp_minors_seen.add(int(m.group(1)))
            if target_cp in fn and any(pm in fn for pm in plat_markers):
                found_wheels.append(fn)

        result["checked"] = True
        result["available_pyvers"] = [f"3.{m}" for m in sorted(cp_minors_seen)]
        result["has_sdist_only"] = not has_wheel_at_all

        if pure_py_wheel or found_wheels:
            result["compatible"] = True
        elif has_wheel_at_all:
            result["compatible"] = False
        else:
            result["compatible"] = None

        return result
    except Exception as e:
        result["error"] = str(e)
        return result



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
            self._set_busy(False)
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
                self._set_busy(False)
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

        # This is the real end of the post-install "loading" the user
        # sees -- the packages table above is now actually populated, so
        # only now is it safe to hide the progress bar / re-enable tabs.
        # Harmless no-op if busy was never on (e.g. a plain env-switch
        # load, not an install).
        self._set_busy(False)

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
                # Copy the table's font so pointSize is valid; a bare QFont()
                # has pointSize -1 on Windows → QFont::setPointSize(-1) warning.
                name_font = QFont(self.catalog_table.font())
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
            "hatch": "hatch run pip install {packages}",
            "pdm": "pdm add {packages}",
            "pixi": "pixi add --pypi {packages}",
        }
        _uninstall_cmds = {
            "venv": "pip uninstall -y {packages}", "uv": "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda": "conda remove {packages}", "pipx": "pipx uninstall {packages}",
            "hatch": "hatch run pip uninstall -y {packages}",
            "pdm": "pdm remove {packages}",
            "pixi": "pixi remove --pypi {packages}",
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
            self.current_worker = self._make_uninstall_worker(to_uninstall)
            self.current_worker.progress.connect(self._on_progress)
            if to_install:
                self.current_worker.finished.connect(
                    lambda ok, msg: self._chain_install(ok, msg, to_install)
                )
            else:
                self.current_worker.finished.connect(self._on_install_finished)
            self.current_worker.start()
        elif to_install:
            # Büyük Girişim (Bayram, 2026-08-12/14): Catalog was the one
            # install path that bypassed the CONFLICT_RULES/dry-run
            # pre-flight -- Presets and Manual Install already went
            # through _install_packages, Catalog alone called the bare
            # _do_install with zero compatibility checking. Routed
            # through the shared method now, same as everywhere else.
            self._install_packages(to_install, hint_name="Catalog")

    def _chain_install(self, uninstall_ok, uninstall_msg, to_install):
        if not uninstall_ok:
            self._append_log(f"❌ Uninstall failed: {uninstall_msg[:300]}")
        self._append_log("✅ Uninstall done. Starting install...")
        self._install_packages(to_install, hint_name="Catalog")

    # ── Install / Uninstall ──

    def _install_packages(self, packages: list, hint_name: str = ""):
        self._pkg_op_hint = hint_name  # preset/app adı — _do_install loglar
        if not self.pip_manager:
            QMessageBox.warning(self, "Warning", "No environment selected.\nPlease select an environment first.")
            return

        # Show busy state IMMEDIATELY, before any of the pre-flight checks
        # below (installed-filter, Python version probe, CONFLICT_RULES,
        # pip --dry-run) run. Those are synchronous subprocess calls on the
        # main thread -- without this, the UI looked frozen for however long
        # they took (up to several seconds, worse with dry-run’s 25s cap)
        # with zero visual feedback until the confirm dialog suddenly
        # appeared. _set_busy(False) is called at every early-return path
        # below; _do_install() re-asserts True on the success path (harmless
        # -- it’s already True), and its own worker-finished handler is what
        # turns it back off for real.
        self._set_busy(True)
        if hasattr(self, "status_label"):
            self.status_label.setText("🔍 Checking compatibility...")

        # Pipx envs have no central <env>/bin/python, so the pre-flight checks
        # below (list_packages and `python --version`) raise FileNotFoundError
        # and surface as "Install FAILED: [Errno 2] No such file or directory:
        # '<pipx>/bin/python'" before _do_install / _do_pipx_install can run.
        # Skip them for pipx; the install path itself (_do_pipx_install) is
        # already pipx-aware and handles per-app isolation correctly.
        _env_type = getattr(self, "_current_env_type", "venv")

        # N76: the list the conflict check looks at. It starts as everything
        # the user asked for and stays that way even after the filter below
        # narrows `packages` down to what pip still has to fetch.
        _conflict_check_list = list(packages)

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
                    self._set_busy(False)
                    QMessageBox.information(self, "Info", "All packages are already installed.")
                    return
                packages = not_installed
                # N76 (Bayram, 2026-08-28): keep the FULL list for the conflict
                # check below.
                #
                # He installed one NLP preset into a fresh env and got a
                # warning; installing a second preset into the same env gave
                # none, and everything went in silently. The two presets share
                # transformers, spacy and nltk -- already installed by then, so
                # they were dropped here, and their rule violations left with
                # them.
                #
                # Being installed is not the same as being compatible. It only
                # means pip will not download it again: a package that needs
                # Python >= 3.11 in a 3.10 env is still wrong, and the user
                # asking for it a second time is exactly when to say so.
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

        # ── CONFLICT_RULES pre-flight check ───────────────────────────────────
        # Check each package against known incompatibilities before showing
        # the confirm dialog. Errors block; warnings are shown alongside.
        _conflict_errors   = []  # will definitely fail
        _conflict_warnings = []  # may fail / user should know
        try:
            from src.utils.constants import CONFLICT_RULES, CONFLICT_RULES_ALIASES
            import re as _re_cf

            # Resolve current Python version (already fetched above if available)
            _py_ver = None
            if _env_type != "pipx" and self.pip_manager:
                try:
                    venv_key = str(self.pip_manager.venv_path)
                    _py_ver = self._launcher_py_version_cache.get(venv_key)
                    if not _py_ver:
                        python_exe = get_python_executable(self.pip_manager.venv_path)
                        from src.utils.platform_utils import subprocess_args as _sa_cf
                        _rv = subprocess.run(
                            [str(python_exe), "--version"],
                            **_sa_cf(capture_output=True, text=True, timeout=5)
                        )
                        _vs = (_rv.stdout + _rv.stderr).strip().replace("Python ", "")
                        _py_ver = tuple(int(x) for x in _vs.split(".")[:2])
                        self._launcher_py_version_cache[venv_key] = _py_ver
                except Exception:
                    pass

            # The full requested set, not just what pip will fetch (N76).
            for _pkg_spec in _conflict_check_list:
                # Normalize: strip version spec, lowercase, dash→underscore
                _pkg_raw  = _re_cf.split(r'[><=!~;]', _pkg_spec)[0].strip()
                _pkg_key  = _pkg_raw.lower().replace("_", "-")
                # Check alias map first
                _rule_key = CONFLICT_RULES_ALIASES.get(_pkg_raw, CONFLICT_RULES_ALIASES.get(_pkg_key, _pkg_key))
                _rule     = CONFLICT_RULES.get(_rule_key)

                # ── N9 Aşama 5+: manual list first, then live PyPI check ──
                # Only for packages the manual list has NOTHING on (manual
                # always wins -- a maintained note beats a live guess), and
                # only for env types where PyPI wheels are actually what
                # gets installed (conda/pixi pull from conda-forge by
                # default, and pipx never resolves _py_ver at all).
                if not _rule and _py_ver and _env_type in ("venv", "uv", "hatch", "pdm", "poetry"):
                    import sys as _sys_cf
                    _plat = {"win32": "win", "linux": "linux", "darwin": "macos"}.get(_sys_cf.platform, "")
                    if _plat:
                        _live = _check_pypi_wheel_availability(_pkg_key, _py_ver[0], _py_ver[1], _plat)
                        if _live["checked"] and _live["compatible"] is False:
                            _avail = _live["available_pyvers"]
                            _avail_str = (
                                f"Python {_avail[0]}–{_avail[-1]}" if len(_avail) > 1
                                else (f"Python {_avail[0]}" if _avail else "an older Python")
                            )
                            _rule = {
                                "max_python": None, "min_python": None, "blocked_envs": [],
                                "severity": "error",
                                "note": (
                                    f"No prebuilt wheel on PyPI for Python {_py_ver[0]}.{_py_ver[1]} "
                                    f"({_plat}). Available for {_avail_str}. Create a new "
                                    f"environment with a compatible Python version, or install "
                                    f"anyway if you know it builds from source on your system."
                                ),
                                "_live_check": True,
                            }

                if not _rule:
                    continue

                _msgs = []

                # A live-PyPI-derived rule only exists because we already
                # determined it's incompatible (see the gate above) -- its
                # note carries the whole finding, there's no separate
                # min/max/blocked_envs condition left to re-check.
                if _rule.get("_live_check"):
                    _msgs.append("no compatible wheel on PyPI for this Python/platform")

                # Python version checks
                if _py_ver:
                    _max = _rule.get("max_python")
                    _min = _rule.get("min_python")
                    if _max:
                        _max_t = tuple(int(x) for x in _max.split("."))
                        if _py_ver > _max_t:
                            _msgs.append(
                                f"requires Python ≤ {_max} "
                                f"(env has Python {_py_ver[0]}.{_py_ver[1]})"
                            )
                    if _min:
                        _min_t = tuple(int(x) for x in _min.split("."))
                        if _py_ver < _min_t:
                            _msgs.append(
                                f"requires Python ≥ {_min} "
                                f"(env has Python {_py_ver[0]}.{_py_ver[1]})"
                            )

                # Env type check
                _blocked = _rule.get("blocked_envs", [])
                if _env_type in _blocked:
                    _msgs.append(f"not compatible with {_env_type} environments")

                if _msgs:
                    _detail = f"• {_pkg_raw}: {'; '.join(_msgs)}\n  ↳ {_rule['note']}"
                    if _rule.get("severity") == "error":
                        _conflict_errors.append(_detail)
                    else:
                        _conflict_warnings.append(_detail)
        except Exception:
            pass  # Never block install if conflict check itself fails

        # Show errors — these will definitely fail, ask if user wants to proceed
        if _conflict_errors:
            _err_text = (
                "⛔ The following packages are known to be incompatible with this environment:\n\n"
                + "\n\n".join(_conflict_errors)
                + "\n\nThese packages will likely fail to install."
            )
            # Third option beyond proceed/cancel: offer to open the Create
            # New Environment dialog directly, since the note text above
            # (static or live-PyPI-derived) already names a compatible
            # Python range -- the user can pick one right there instead of
            # having to go find that information themselves.
            _err_box = QMessageBox(self)
            _err_box.setWindowTitle("Compatibility Issues Detected")
            _err_box.setIcon(QMessageBox.Warning)
            _err_box.setText(_err_text)
            _install_anyway_btn = _err_box.addButton("Install Anyway", QMessageBox.AcceptRole)
            _create_env_btn = _err_box.addButton("Create New Environment…", QMessageBox.ActionRole)
            _cancel_btn = _err_box.addButton("Cancel", QMessageBox.RejectRole)
            _err_box.setDefaultButton(_cancel_btn)
            _err_box.exec()
            _clicked = _err_box.clickedButton()

            if _clicked is _create_env_btn:
                self._set_busy(False)
                # self here is PackagePanel, not MainWindow -- it has no
                # direct reference back (constructed with only config=,
                # no parent=), so _new_env() (a MainWindow method) can't
                # be called directly. hasattr(self, "_new_env") silently
                # returned False here and did nothing (found 2026-08-12).
                # Route through the same signal pattern already used for
                # env_refresh_requested -- MainWindow connects it to
                # self._new_env in main_window.py.
                self.new_environment_requested.emit()
                return
            if _clicked is not _install_anyway_btn:
                self._set_busy(False)
                return

        # Append warnings to the existing py_warning string
        if _conflict_warnings:
            py_warning += (
                "\n\n⚠️ Compatibility Notes:\n"
                + "\n\n".join(_conflict_warnings)
            )

        # ── N9 Aşama 4: pip --dry-run — gerçek resolver kontrolü ──────
        # CONFLICT_RULES yukarıda sadece elle girilmiş statik tabloyu kontrol
        # etti. Bu blok pip'in GERÇEK resolver'ını (indirme/kurulum yok,
        # sadece çözümleme) çalıştırır — tabloda hiç olmayan gerçek çakışmaları
        # (örn. iki paketin birbirine zıt sürüm istemesi) yakalar. Sadece pip’in
        # gerçekten doğrudan kurulum aracı olduğu tiplerde çalışır — uv/poetry/
        # conda/pdm/pixi/pipx kendi resolver’larını kullanır, bu kontrol onlar
        # için anlamlı değil (hatch pip'e devrettiği için dahil).
        _dry_run_error = None
        if _env_type in ("venv", "uv", "hatch") and self.pip_manager:
            if hasattr(self, "status_label"):
                self.status_label.setText("🐍 Verifying with pip’s dependency resolver...")
            try:
                _dr_python = get_python_executable(self.pip_manager.venv_path)
                _dr = subprocess.run(
                    [str(_dr_python), "-m", "pip", "install", "--dry-run"] + packages,
                    **subprocess_args(capture_output=True, text=True, timeout=25)
                )
                if _dr.returncode != 0:
                    _dr_tail = (_dr.stderr or _dr.stdout or "").strip()
                    # Son ~15 satır yeterli — pip resolver hataları uzun
                    # olabilir, gerçek özet genelde en sonda.
                    _dry_run_error = "\n".join(_dr_tail.splitlines()[-15:])
            except Exception:
                pass  # dry-run kendisi başarısız olursa install'ı asla engelleme

        if _dry_run_error:
            _dr_reply = QMessageBox.warning(
                self, "pip Dependency Check Failed",
                "⛔ pip’s real dependency resolver reports these packages "
                "cannot be installed together:\n\n" + _dry_run_error +
                "\n\nProceed anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if _dr_reply != QMessageBox.Yes:
                self._set_busy(False)
                return

        # Show ALL package names in confirm dialog
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install the following {len(packages)} package(s)?\n\n• " + "\n• ".join(packages) + py_warning,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            self._set_busy(False)
            return

        # Show command hint based on env type
        _env_type = getattr(self, "_current_env_type", "venv")
        _install_cmds = {
            "venv":   "pip install {packages}",
            "uv":     "uv pip install {packages}",
            "poetry": "poetry add {packages}",
            "conda":  "conda install {packages}",
            "pipx":   "pipx install {packages}",
            "hatch":  "hatch run pip install {packages}",
            "pdm":    "pdm add {packages}",
            "pixi":   "pixi add --pypi {packages}",
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
        _env_type = getattr(self, "_current_env_type", "venv")
        from src.utils.logger import get_logger
        get_logger("venvstudio.install").info(
            f"📦 [Install] env='{_env_name}' type={_env_type} "
            f"source='{_hint}' packages({len(_pk)}): {_shown}"
        )
        if _env_type == "conda" and self.pip_manager and self.pip_manager.venv_path:
            # Use conda install instead of pip for conda environments
            _env_path = self.pip_manager.venv_path
            _pkgs = list(packages)

            def _do_conda_install(callback=None, _src=_hint, _n=len(_pkgs)):
                from src.core.micromamba_installer import (
                    install_conda_packages, get_micromamba_exe, download_micromamba,
                )
                # Explicit start line: conda installs can run for minutes with
                # little output, which looked like nothing was happening.
                if callback:
                    callback(f"\u26a1 Installing {_n} package(s) from "
                             f"{_src or 'Manual'} via conda-forge — this can "
                             f"take a few minutes...")
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
        elif _env_type == "poetry":
            # Poetry must install through `poetry add`, run in the project
            # directory (where pyproject.toml lives), so the dependency is
            # recorded in pyproject.toml + poetry.lock. Plain `pip install`
            # would land packages in the venv but leave the project files
            # untouched -- the env-type asymmetry this file keeps hitting.
            _pkgs_add = list(packages)
            _proj_dir_add = self._poetry_project_dir()

            def _do_poetry_install(callback=None, _proj=_proj_dir_add,
                                   _pkgs=_pkgs_add):
                import subprocess, shutil
                from src.utils.platform_utils import subprocess_args
                if not _proj:
                    # No project dir known (legacy marker) -> fall back to
                    # pip so the operation still does something visible.
                    if callback:
                        callback("\u26a0 Poetry project dir unknown; "
                                 "falling back to pip install")
                    return self.pip_manager.install_packages(_pkgs, callback)
                _poetry = shutil.which("poetry")
                if not _poetry:
                    return (False, "poetry executable not found")
                if callback:
                    callback(f"poetry add {' '.join(_pkgs)}...")
                r = subprocess.run(
                    [_poetry, "add"] + _pkgs,
                    capture_output=True, text=True, timeout=600,
                    cwd=str(_proj), **subprocess_args()
                )
                if r.returncode != 0:
                    _err = (r.stderr or r.stdout or "").strip()
                    return (False, f"poetry add failed: {_err[:400]}")
                return (True, f"Installed: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_poetry_install)
        elif _env_type == "hatch":
            _pkgs_hatch = list(packages)
            # self.pip_manager.venv_path is the real hatch virtualenv (see
            # env_state.py PkgLoader comment) -- it has its own bin/pip, so
            # install directly there instead of `hatch run pip install`,
            # which needs a project-dir cwd this path no longer is.
            _hatch_path = self.pip_manager.venv_path if self.pip_manager else None

            def _do_hatch_install(callback=None, _pkgs=_pkgs_hatch, _path=_hatch_path):
                import subprocess
                from pathlib import Path as _Path
                if not _path:
                    return (False, "hatch environment path not found")
                _pip = None
                for _p in (
                    str(_Path(_path) / "Scripts" / "pip.exe"),
                    str(_Path(_path) / "bin" / "pip"),
                ):
                    if _Path(_p).exists():
                        _pip = _p; break
                if not _pip:
                    return (False, f"pip not found in hatch environment: {_path}")
                if callback:
                    callback(f"pip install {' '.join(_pkgs)}...")
                r = subprocess.run(
                    [_pip, "install"] + _pkgs,
                    capture_output=True, text=True, timeout=300,
                )
                if r.returncode != 0:
                    return (False, f"hatch install failed: {(r.stderr or r.stdout or '').strip()[:400]}")
                return (True, f"Installed: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_hatch_install)
        elif _env_type == "pdm":
            _pkgs_pdm = list(packages)
            _pdm_path = self.pip_manager.venv_path if self.pip_manager else None

            def _do_pdm_install(callback=None, _pkgs=_pkgs_pdm, _path=_pdm_path):
                import subprocess, shutil
                from src.utils.platform_utils import subprocess_args
                _pdm = shutil.which("pdm")
                if not _pdm:
                    return (False, "pdm executable not found")
                if callback:
                    callback(f"pdm add {' '.join(_pkgs)}...")
                r = subprocess.run(
                    [_pdm, "add"] + _pkgs,
                    capture_output=True, text=True, timeout=300,
                    cwd=str(_path) if _path else None, **subprocess_args()
                )
                if r.returncode != 0:
                    return (False, f"pdm add failed: {(r.stderr or r.stdout or '').strip()[:400]}")
                return (True, f"Installed: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_pdm_install)
        elif _env_type == "pixi":
            _pkgs_pixi = list(packages)
            _pixi_path = self.pip_manager.venv_path if self.pip_manager else None

            def _do_pixi_install(callback=None, _pkgs=_pkgs_pixi, _path=_pixi_path):
                import subprocess, shutil, os
                from src.utils.platform_utils import subprocess_args
                # Prefer user-installed pixi over system pixi (which may be fake)
                _pixi_cands = [
                    os.path.expanduser("~/.pixi/bin/pixi"),
                    os.path.join(os.environ.get("USERPROFILE", ""), ".pixi", "bin", "pixi.exe"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), ".pixi", "bin", "pixi.exe"),
                ]
                _pixi = next((c for c in _pixi_cands if os.path.isfile(c)), None) \
                        or shutil.which("pixi") or "pixi"
                # Pixi needs python in the environment before --pypi packages
                if callback:
                    callback("Ensuring python is in pixi environment...")
                subprocess.run(
                    [_pixi, "add", "python"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(_path) if _path else None, **subprocess_args()
                )
                if callback:
                    callback(f"pixi add --pypi {' '.join(_pkgs)}...")
                r = subprocess.run(
                    [_pixi, "add", "--pypi"] + _pkgs,
                    capture_output=True, text=True, timeout=300,
                    cwd=str(_path) if _path else None, **subprocess_args()
                )
                if r.returncode != 0:
                    return (False, f"pixi add failed: {(r.stderr or r.stdout or '').strip()[:400]}")
                return (True, f"Installed: {', '.join(_pkgs)}")

            self.current_worker = WorkerThread(_do_pixi_install)
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

    def _poetry_project_dir(self):
        """Return the poetry project directory (where pyproject.toml lives).

        For poetry envs the real venv (pip_manager.venv_path) lives under
        the pypoetry cache, NOT next to pyproject.toml. `poetry add/remove`
        must run in the project dir, so we read it from the marker written
        at create time (poetry_project_dir). Older markers predate that
        field; for them we try `poetry env info` in reverse is not possible,
        so we fall back to the marker's own folder if it holds a
        pyproject.toml, else None (caller falls back to pip).
        """
        from pathlib import Path as _P
        _vp = getattr(self.pip_manager, "venv_path", None)
        if not _vp:
            return None
        _marker = _P(_vp) / ".venvstudio_env"
        if _marker.exists():
            try:
                import json as _json
                with open(_marker) as _mf:
                    _md = _json.load(_mf)
                _pd = _md.get("poetry_project_dir", "")
                if _pd and (_P(_pd) / "pyproject.toml").exists():
                    return _pd
            except Exception:
                pass
        # Legacy fallback: marker dir itself might be the project dir
        if (_P(_vp) / "pyproject.toml").exists():
            return str(_vp)
        return None

    def _make_uninstall_worker(self, packages):
        """Build the uninstall worker that matches the environment type.

        conda and pipx do not install through pip, so they cannot uninstall
        through it either. Running pip uninstall against them removed nothing
        and still reported success -- while the command hint shown to the user
        moments earlier correctly said "conda remove" or "pipx uninstall".
        Both uninstall paths in this file go through here so the two cannot
        drift apart again.
        """
        _env_type = getattr(self, "_current_env_type", "venv")
        _pkgs_rm = list(packages)

        if _env_type == "conda" and getattr(self.pip_manager, "venv_path", None):
            _env_path_rm = self.pip_manager.venv_path

            def _do_conda_uninstall(callback=None, _n=len(_pkgs_rm)):
                from src.core.micromamba_installer import remove_conda_packages
                if callback:
                    callback(f"\u26a1 Removing {_n} package(s) via micromamba...")
                ok = remove_conda_packages(_env_path_rm, _pkgs_rm,
                                           progress_cb=callback)
                return (ok,
                        f"Removed: {', '.join(_pkgs_rm)}" if ok
                        else f"conda remove failed for: {', '.join(_pkgs_rm)}")

            return WorkerThread(_do_conda_uninstall)

        if _env_type == "pipx":

            def _do_pipx_uninstall(callback=None):
                import subprocess as _sp_rm
                from src.utils.platform_utils import (
                    get_pipx_cmd as _gpc_rm, subprocess_args as _sa_rm,
                )
                _base = _gpc_rm()
                if not _base:
                    return (False, "pipx executable not found")
                _failed_rm = []
                for _pkg_rm in _pkgs_rm:
                    if callback:
                        callback(f"pipx uninstall {_pkg_rm}...")
                    _r_rm = _sp_rm.run(
                        list(_base) + ["uninstall", _pkg_rm],
                        **_sa_rm(capture_output=True, text=True, timeout=120)
                    )
                    _out_rm = (_r_rm.stdout or "") + (_r_rm.stderr or "")
                    # pipx exits 1 with "Nothing to uninstall for X" when the
                    # app is not there. That is the desired end state, not a
                    # failure -- and the exact wording matters: an earlier
                    # guess of "not installed" never matched, so removing an
                    # already-removed package was reported as an error.
                    _gone_rm = ("nothing to uninstall" in _out_rm.lower()
                                or "not installed" in _out_rm.lower())
                    if _r_rm.returncode != 0 and not _gone_rm:
                        _failed_rm.append(_pkg_rm)
                        if callback:
                            callback(f"pipx uninstall failed: "
                                     f"{_out_rm.strip()[:200]}")
                if _failed_rm:
                    return (False,
                            f"pipx uninstall failed for: "
                            f"{', '.join(_failed_rm)}")
                return (True, f"Removed: {', '.join(_pkgs_rm)}")

            return WorkerThread(_do_pipx_uninstall)

        if _env_type == "poetry":
            _proj_dir_rm = self._poetry_project_dir()

            def _do_poetry_uninstall(callback=None, _proj=_proj_dir_rm,
                                     _pkgs=_pkgs_rm):
                import subprocess, shutil
                from src.utils.platform_utils import subprocess_args
                if not _proj:
                    if callback:
                        callback("\u26a0 Poetry project dir unknown; "
                                 "falling back to pip uninstall")
                    return self.pip_manager.uninstall_packages(_pkgs, callback)
                _poetry = shutil.which("poetry")
                if not _poetry:
                    return (False, "poetry executable not found")
                if callback:
                    callback(f"poetry remove {' '.join(_pkgs)}...")
                # `poetry remove` updates pyproject.toml + poetry.lock, which
                # `pip uninstall` never did -- the project files drifted out
                # of sync with the venv. Run in the project directory.
                r = subprocess.run(
                    [_poetry, "remove"] + _pkgs,
                    capture_output=True, text=True, timeout=300,
                    cwd=str(_proj), **subprocess_args()
                )
                _out = ((r.stdout or "") + (r.stderr or "")).lower()
                # Treat 'not found in pyproject' as already-gone, not error
                # (mirrors the pipx 'nothing to uninstall' handling above).
                _gone = ("does not contain" in _out
                         or "not found" in _out)
                if r.returncode != 0 and not _gone:
                    _err = (r.stderr or r.stdout or "").strip()
                    return (False, f"poetry remove failed: {_err[:400]}")
                return (True, f"Removed: {', '.join(_pkgs)}")

            return WorkerThread(_do_poetry_uninstall)

        return WorkerThread(self.pip_manager.uninstall_packages, _pkgs_rm)

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
        _env_type = getattr(self, "_current_env_type", "venv")
        from src.utils.logger import get_logger
        get_logger("venvstudio.install").info(
            f"🗑️ [Uninstall] env='{_env_name}' type={_env_type} "
            f"packages({len(packages)}): {_shown}"
        )

        _uninstall_cmds = {
            "venv":   "pip uninstall -y {packages}",
            "uv":     "uv pip uninstall {packages}",
            "poetry": "poetry remove {packages}",
            "conda":  "conda remove {packages}",
            "pipx":   "pipx uninstall {packages}",
            "hatch":  "hatch run pip uninstall -y {packages}",
            "pdm":    "pdm remove {packages}",
            "pixi":   "pixi remove --pypi {packages}",
        }
        cmd = _uninstall_cmds.get(_env_type, COMMAND_HINTS["uninstall"]).format(packages=" ".join(packages))
        self._show_command_hint("Uninstall Packages", cmd)

        self._set_busy(True)

        self.current_worker = self._make_uninstall_worker(packages)
        self.current_worker.progress.connect(self._on_progress)
        self.current_worker.finished.connect(self._on_install_finished)
        self.current_worker.start()

