"""VenvStudio - Projects page (B43, stage 1).

Environments have had a page of their own since the beginning: a table, a
refresh, a create button, and everything you might do to one on a right-click.
Projects had none of that. File -> New Project made them and File -> Recent
Projects remembered them, and that was all -- created, then out of sight.

Bayram's framing: "Environment gibi, nasil ki orada env lari yonetip
kopyaliyabiliyoruz, Project sekmesinde de benzer seyler yapacagiz." So this is
the counterpart page, not a second menu.

Stage 1 is what this file does now: list projects, find ones VenvStudio did not
create, and open them. Stages 2-4 (per-project commands, clone/rename/delete,
and the project-to-environment link) are in the TODO.

WHAT COUNTS AS A PROJECT: a directory with a pyproject.toml. That is the file
uv, poetry, hatch and pdm all agree on; pixi may use pixi.toml instead, so both
are accepted. The tool is read from the file's contents rather than guessed
from the directory, because a directory tells you nothing and guessing wrongly
here would send a `poetry install` at a pdm project.
"""
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.utils.logger import get_logger

_log = get_logger("venvstudio.projects")

# Where to look when scanning. Deliberately shallow: a full-disk walk would
# take minutes and turn up every vendored dependency on the machine.
_SCAN_DEPTH = 3


def detect_tool(project_dir) -> str:
    """Which tool manages this project, read from its own files.

    Returns "uv", "poetry", "hatch", "pdm", "pixi" or "" when the directory
    holds a pyproject.toml that names none of them (a plain setuptools project,
    say -- still a project, just not one of ours to drive).
    """
    d = Path(project_dir)
    if (d / "pixi.toml").is_file():
        return "pixi"

    pp = d / "pyproject.toml"
    if not pp.is_file():
        return ""
    try:
        text = pp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    # Order matters: a [tool.poetry] section is decisive, while [tool.uv] can
    # appear alongside others, so the more specific markers are tested first.
    for marker, tool in (
        ("[tool.poetry]", "poetry"),
        ("[tool.pdm", "pdm"),
        ("[tool.hatch", "hatch"),
        ("[tool.pixi", "pixi"),
        ("[tool.uv", "uv"),
    ):
        if marker in text:
            return tool

    # uv writes no [tool.uv] section for a plain project, so it needs its own
    # test. A freshly created one looks like this:
    #
    #     [build-system]
    #     requires = ["uv_build>=0.12.5,<0.13.0"]
    #     build-backend = "uv_build"
    #
    # The build backend is the reliable marker. `uv.lock` is NOT -- it appears
    # only after `uv sync`, so a project that had just been created showed no
    # tool at all, which is how this was found.
    if "uv_build" in text or 'requires = ["uv' in text:
        return "uv"
    # Older uv versions used hatchling and left only this behind.
    if (d / ".python-version").is_file() and (d / "uv.lock").is_file():
        return "uv"
    return ""


def find_project_env(project_dir, tool: str = "") -> str:
    """Where this project's virtual environment actually lives, or "".

    B43 stage 4. Each tool answers this differently, and until it is answered
    the Projects page can show that a project exists but nothing about what is
    installed in it -- which is most of what anyone wants to know.

      uv, pdm    <project>/.venv
      pixi       <project>/.pixi/envs/default
      hatch      <project>/.venv, else the shared hatch env directory
      poetry     ~/.cache/pypoetry/virtualenvs/<name>-<hash>-py<ver>

    Poetry is the hard one: the hash is poetry's own, derived from the absolute
    project path, so it cannot be recomputed here. `poetry env info -p` would
    answer exactly, but it is a subprocess per project on every refresh, which
    is the cost this page was careful to avoid. Instead the directory is
    matched by the `<name>-` prefix, and where several match -- one project
    having been built under two Python versions -- the newest wins, because
    that is the one poetry itself would use.
    """
    d = Path(project_dir)

    # The in-project layouts, which are also poetry's when in-project venvs
    # are configured, so they are tried first regardless of tool.
    for candidate in (d / ".venv", d / ".pixi" / "envs" / "default"):
        if (candidate / "bin" / "python").is_file() or \
           (candidate / "Scripts" / "python.exe").is_file():
            return str(candidate)

    if tool == "poetry":
        try:
            from src.utils.platform_utils import get_default_poetry_venvs_path
            _root = Path(get_default_poetry_venvs_path())
        except Exception:
            _root = Path.home() / ".cache" / "pypoetry" / "virtualenvs"
        if _root.is_dir():
            # Poetry slugs the project name: underscores become hyphens.
            _slug = read_project_meta_name(d).replace("_", "-").lower()
            _hits = []
            try:
                for _e in _root.iterdir():
                    if _e.is_dir() and _e.name.lower().startswith(_slug + "-"):
                        _hits.append(_e)
            except OSError:
                pass
            if _hits:
                _hits.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return str(_hits[0])

    if tool == "hatch":
        try:
            _root = Path.home() / ".local" / "share" / "hatch" / "env" / "virtual"
            if _root.is_dir():
                _slug = read_project_meta_name(d).replace("_", "-").lower()
                for _e in _root.iterdir():
                    if _e.is_dir() and _e.name.lower() == _slug:
                        for _sub in _e.rglob("pyvenv.cfg"):
                            return str(_sub.parent)
        except OSError:
            pass

    return ""


def read_project_meta_name(project_dir) -> str:
    """The project's declared name, or the folder name if it declares none."""
    d = Path(project_dir)
    pp = d / "pyproject.toml"
    if pp.is_file():
        try:
            for line in pp.read_text(encoding="utf-8", errors="replace").splitlines():
                _l = line.strip()
                if _l.startswith("name ="):
                    return _l.split("=", 1)[1].strip().strip('"\'')
        except Exception:
            pass
    return d.name


def count_installed(env_path) -> int:
    """How many packages are installed in this environment.

    Counts `*.dist-info` directories in site-packages rather than running pip:
    this is called for every project on every refresh, and a subprocess each
    time would make the page as slow as the startup we just finished fixing.
    """
    if not env_path:
        return 0
    base = Path(env_path)
    for site in (base.glob("lib/python*/site-packages"),
                 [base / "Lib" / "site-packages"]):
        for sp in site:
            if sp.is_dir():
                try:
                    return sum(1 for x in sp.iterdir()
                               if x.name.endswith(".dist-info"))
                except OSError:
                    return 0
    return 0


def read_project_meta(project_dir) -> dict:
    """Name, tool, python and dependency count for one project directory."""
    d = Path(project_dir)
    meta = {
        "name": d.name,
        "path": str(d),
        "tool": detect_tool(d),
        "python": "",
        "deps": 0,
        "has_deps_key": False,
        "has_env": False,
    }

    pp = d / "pyproject.toml"
    if pp.is_file():
        try:
            text = pp.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                _l = line.strip()
                if _l.startswith("name =") and meta["name"] == d.name:
                    meta["name"] = _l.split("=", 1)[1].strip().strip('"\'')
                elif _l.startswith("requires-python"):
                    meta["python"] = _l.split("=", 1)[1].strip().strip('"\'')
            # Counting the dependencies array rather than parsing TOML: this
            # runs for every project on every refresh, and an approximate
            # number that costs nothing beats an exact one that needs a parser.
            if "dependencies" in text:
                meta["has_deps_key"] = True
                _seg = text.split("dependencies", 1)[1]
                _seg = _seg[:_seg.find("]") + 1] if "]" in _seg else ""
                meta["deps"] = _seg.count('"') // 2 + _seg.count("'") // 2
        except Exception:
            pass

    # An environment inside the project is the common layout for uv and pdm.
    # Poetry keeps its own elsewhere -- finding that is stage 4.
    # B43 stage 4: the environment, wherever the tool decided to put it.
    meta["env_path"] = find_project_env(d, meta["tool"])
    meta["has_env"] = bool(meta["env_path"])
    meta["installed"] = count_installed(meta["env_path"])
    return meta


def scan_for_projects(roots, depth: int = _SCAN_DEPTH) -> list:
    """Find project directories under `roots`, breadth-first to `depth`.

    Skips the directories that are always noise -- virtualenvs, caches, VCS
    metadata, node_modules -- both because they never contain a project the
    user means and because descending into them is most of the cost.
    """
    _skip = {".git", ".venv", "venv", "__pycache__", "node_modules",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
             ".tox", ".nox", "dist", "build", ".cache"}
    found, seen = [], set()

    for root in roots:
        root = Path(os.path.expanduser(str(root)))
        if not root.is_dir():
            continue
        queue = [(root, 0)]
        while queue:
            d, lvl = queue.pop(0)
            try:
                key = os.path.normcase(str(d.resolve()))
                if key in seen:
                    continue
                seen.add(key)
                if (d / "pyproject.toml").is_file() or (d / "pixi.toml").is_file():
                    found.append(str(d))
                    continue        # do not descend into a project
                if lvl >= depth:
                    continue
                for child in d.iterdir():
                    if child.is_dir() and child.name not in _skip \
                            and not child.name.startswith("."):
                        queue.append((child, lvl + 1))
            except (PermissionError, OSError):
                continue
    return found


class ProjectsPageMixin:
    """Mixin for MainWindow: the Projects page."""

    _TOOL_ICONS = {"uv": "\u26a1", "poetry": "\U0001f4dc", "hatch": "\U0001f423",
                   "pdm": "\U0001f4e6", "pixi": "\U0001f9ea", "": "\U0001f4c1"}

    def _create_projects_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Projects")
        title.setObjectName("header")
        header.addWidget(title)
        header.addStretch()

        _scan = QPushButton("\U0001f50d Scan for Projects")
        _scan.setObjectName("secondary")
        _scan.setFixedHeight(40)
        _scan.setToolTip(
            "Look for projects on disk \u2014 in your project folder, or "
            "any folder you choose")
        _scan.clicked.connect(self._scan_projects)
        header.addWidget(_scan)

        # A scan that reaches too far is easy to make and tedious to undo one
        # row at a time -- Bayram's first scan pulled in four git checkouts.
        _clear = QPushButton("\u2716 Clear List")
        _clear.setObjectName("secondary")
        _clear.setFixedHeight(40)
        _clear.setToolTip(
            "Empty the list. No folders are deleted; scan or create to refill it.")
        _clear.clicked.connect(self._clear_project_list)
        header.addWidget(_clear)

        _refresh = QPushButton("\U0001f504 Refresh")
        _refresh.setObjectName("secondary")
        _refresh.setFixedHeight(40)
        _refresh.clicked.connect(self._refresh_projects)
        header.addWidget(_refresh)

        _new = QPushButton("  + New Project  ")
        _new.setFixedHeight(40)
        # WindowMenuMixin._new_project opens the dialog; reuse it rather than
        # writing a second path to the same place.
        _new.clicked.connect(self._on_new_project_clicked)
        header.addWidget(_new)
        layout.addLayout(header)

        self.projects_info = QLabel("")
        self.projects_info.setObjectName("subheader")
        self.projects_info.setWordWrap(True)
        layout.addWidget(self.projects_info)

        self.projects_table = QTableWidget(0, 6)
        # "Required" and "Installed" rather than "Deps" and "Env": Bayram read
        # the old pair twice and could not tell what either meant, which is a
        # fair verdict on a column called "Deps" showing a number and one
        # called "Env" showing a tick.
        self.projects_table.setHorizontalHeaderLabels(
            ["Project", "Tool", "Python", "Required", "Installed", "Location"])
        _h = self.projects_table.horizontalHeader()
        _h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.projects_table.setColumnWidth(0, 240)
        for _i, _w in ((1, 110), (2, 110), (3, 100), (4, 110)):
            _h.setSectionResizeMode(_i, QHeaderView.Fixed)
            self.projects_table.setColumnWidth(_i, _w)
        _h.setSectionResizeMode(5, QHeaderView.Stretch)
        self.projects_table.verticalHeader().setVisible(False)
        self.projects_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.projects_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.projects_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.projects_table.setAlternatingRowColors(True)
        # Same treatment as the environments table (B183 there): 16px, bold,
        # roomy rows. Two tables of the same kind should not read differently.
        self.projects_table.verticalHeader().setDefaultSectionSize(48)
        self.projects_table.setStyleSheet(
            f"QTableWidget {{ font-size: 16px; color: {self._c()['fg']}; }}"
            f"QTableWidget::item {{ padding: 8px 12px; font-weight: bold; "
            f"font-size: 16px; }}"
            f"QHeaderView::section {{ font-size: 15px; font-weight: bold; "
            f"padding: 10px; }}"
        )
        self.projects_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.projects_table.customContextMenuRequested.connect(
            self._show_project_context_menu)
        self.projects_table.itemDoubleClicked.connect(
            lambda _i: self._proj_open_terminal())
        layout.addWidget(self.projects_table, 1)

        self._refresh_projects()
        return page

    def _on_new_project_clicked(self):
        """Open the New Project dialog, then show the result here.

        B43: the dialog lives in WindowMenuMixin (File -> New Project). This
        page reuses it and refreshes afterwards, so a project created from
        either place appears in both.
        """
        try:
            self._new_project()
        except Exception as e:
            _log.warning(f"[Projects] new-project dialog failed: {e!r}")
            return
        self._refresh_projects()

    # ── Data ──────────────────────────────────────────────────────────────

    def _known_project_paths(self) -> list:
        """Recorded projects, newest first, dropping any that are gone."""
        try:
            entries = self.config.get("recent_projects", []) or []
        except Exception:
            entries = []
        out = []
        for e in entries:
            if isinstance(e, dict) and os.path.isdir(e.get("path", "")):
                out.append(e["path"])
        return out

    def _refresh_projects(self):
        """Redraw the table from what is already recorded -- no disk walk."""
        paths = self._known_project_paths()
        self._fill_projects_table(paths)
        _n = len(paths)
        self.projects_info.setText(
            f"{_n} project{'s' if _n != 1 else ''}"
            + ("" if _n else "  \u2014  create one, or press Scan for Projects "
                             "to find existing ones on disk"))

    def _scan_projects(self):
        """Walk the likely places and add whatever is found (B43)."""
        from PySide6.QtWidgets import QApplication

        _roots = []
        try:
            from src.gui.project_dialog import NewProjectDialog
            _roots.append(NewProjectDialog.default_project_dir())
            _last = self.config.get("last_project_dir", "")
            if _last:
                _roots.append(_last)
        except Exception:
            pass
        # B43: the home directory is NOT scanned by default.
        #
        # It was, and it swept in every git checkout on the machine -- VenvStudio
        # itself, its backup copy, LLMcompoz, dictz. All real Python projects
        # with a pyproject.toml, so not wrong exactly, but not what anyone means
        # by "my projects" either; every one of them showed an empty Tool
        # column, because none is managed by uv, poetry, pdm or pixi.
        #
        # The project directory is the right default. Anywhere else, the user
        # can say so.
        from PySide6.QtWidgets import QFileDialog
        _extra = QFileDialog.getExistingDirectory(
            self, "Scan which folder?  (Cancel to scan the project folder)",
            _roots[0] if _roots else os.path.expanduser("~"))
        if _extra:
            _roots = [_extra]

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            found = scan_for_projects(_roots)
        finally:
            QApplication.restoreOverrideCursor()

        _known = {os.path.normcase(p) for p in self._known_project_paths()}
        _new = [p for p in found if os.path.normcase(p) not in _known]

        # Everything found is recorded, so a project only has to be discovered
        # once. Scanning is the slow path; the table should not need it twice.
        for _p in _new:
            self._record_project(_p)

        _log.info(f"[Projects] scan: {len(found)} found, {len(_new)} new")
        self._refresh_projects()
        self.projects_info.setText(
            f"{len(self._known_project_paths())} projects  \u2014  "
            f"scan found {len(found)}, {len(_new)} new")

    def _fill_projects_table(self, paths):
        t = self.projects_table
        t.setRowCount(0)

        # B43: set the font on every cell, as the environments table does.
        # The stylesheet alone was not enough there either (B183) -- Qt's font
        # cascade lets a default win in places -- and copying the table's own
        # font rather than building a bare QFont() keeps the QSS pixel size and
        # avoids the setPointSize(-1) warning a fresh QFont produces.
        from PySide6.QtGui import QFont
        _cell_font = QFont(t.font())
        _cell_font.setBold(True)
        for row, path in enumerate(paths):
            meta = read_project_meta(path)
            t.insertRow(row)

            _icon = self._TOOL_ICONS.get(meta["tool"], "\U0001f4c1")
            name = QTableWidgetItem(f"  {_icon}  {meta['name']}")
            name.setData(Qt.UserRole, path)
            name.setFont(_cell_font)
            t.setItem(row, 0, name)

            _tool = QTableWidgetItem(meta["tool"] or "\u2014")
            if not meta["tool"]:
                _tool.setToolTip(
                    "A pyproject.toml with no recognised tool section \u2014 "
                    "VenvStudio can open it, but not drive it.")
            _tool.setFont(_cell_font)
            t.setItem(row, 1, _tool)

            _py = QTableWidgetItem(meta["python"] or "\u2014")
            _py.setFont(_cell_font)
            t.setItem(row, 2, _py)

            # "0" rather than a dash: an empty dependencies list is a fact
            # about the project, while a dash reads as "not known".
            _dep = QTableWidgetItem(
                str(meta["deps"]) if meta.get("has_deps_key") else "\u2014")
            _dep.setFont(_cell_font)
            _dep.setTextAlignment(Qt.AlignCenter)
            _dep.setToolTip(
                "Dependencies this project declares in pyproject.toml \u2014 "
                "what it asks for, not what is installed")
            t.setItem(row, 3, _dep)

            # Installed: how many packages are actually in the project's
            # environment, and a dash when there is no environment yet. The
            # tooltip names the path, because for poetry it is nowhere obvious.
            if meta["has_env"]:
                _inst = QTableWidgetItem(str(meta["installed"]))
                _inst.setToolTip(
                    f"{meta['installed']} packages installed in:\n"
                    f"{meta['env_path']}")
            else:
                _inst = QTableWidgetItem("\u2014")
                _inst.setToolTip(
                    "No environment yet \u2014 run the project's tool "
                    "(uv sync, poetry install, pdm install) to create one")
            _inst.setTextAlignment(Qt.AlignCenter)
            _inst.setFont(_cell_font)
            t.setItem(row, 4, _inst)

            _loc = QTableWidgetItem(path)
            _loc.setFont(_cell_font)
            try:
                _loc.setForeground(QColor(self._c()["fg_muted"]))
            except Exception:
                pass
            t.setItem(row, 5, _loc)

    # ── Actions ───────────────────────────────────────────────────────────

    def _selected_project_path(self) -> str:
        rows = self.projects_table.selectionModel().selectedRows()
        if not rows:
            return ""
        item = self.projects_table.item(rows[0].row(), 0)
        return (item.data(Qt.UserRole) if item else "") or ""

    def _show_project_context_menu(self, pos):
        item = self.projects_table.itemAt(pos)
        if item is None:
            return
        self.projects_table.selectRow(item.row())
        _path = self._selected_project_path()
        if not _path:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ font-size: {self._c()['fs_base']}px; }} "
            f"QMenu::item {{ padding: 6px 20px; }}")
        # B43: the packages question, answered where the rest of the
        # application answers it. A project has an environment; that
        # environment has packages; VenvStudio already has a page for those.
        _pkg = menu.addAction("\U0001f4e6  Packages\u2026",
                              self._proj_open_packages)
        _meta = read_project_meta(_path)
        if not _meta["has_env"]:
            _pkg.setEnabled(False)
            _pkg.setToolTip(
                "This project has no environment yet \u2014 run its tool first")
        menu.addSeparator()
        menu.addAction("\U0001f4bb  Open Terminal", self._proj_open_terminal)
        menu.addAction("\U0001f4c2  Open Folder", self._proj_open_folder)
        menu.addSeparator()
        menu.addAction("\U0001f4cb  Clone Project\u2026", self._clone_project)
        menu.addSeparator()

        # The two removals are deliberately worded to be told apart at a
        # glance, and separated from each other. One forgets a row; the other
        # destroys someone's work. Putting them side by side with similar
        # labels is how the wrong one gets clicked.
        menu.addAction("\u2716  Remove from list (keep files)",
                       self._forget_project)
        _del = menu.addAction("\U0001f5d1\ufe0f  Delete from disk\u2026",
                              self._delete_project)
        try:
            from PySide6.QtGui import QColor as _QC
            _del.setToolTip("Permanently deletes the project folder")
        except Exception:
            pass
        menu.exec(self.projects_table.viewport().mapToGlobal(pos))

    def _proj_open_packages(self):
        """Open this project's environment on the Packages page.

        B43: Bayram's question -- "bunlarin icinde de paketler yuklenemeyecek
        mi?" -- and he is right that it should be the same screen. A project
        has an environment; that environment has packages; VenvStudio already
        has a page for those, and everything it offers there (install, remove,
        catalog, presets) works on whatever environment the panel is pointed at.

        The first attempt searched the Environments table for a matching row,
        which could never work: project environments are not in that table.
        `Documents/vs_projects/first_project/.venv` is not under the venv base
        directory, and poetry's live in its own cache. So it found nothing and
        showed a warning instead of doing the job.

        set_venv is the actual door -- the same call _on_env_selected makes.
        """
        _path = self._selected_project_path()
        if not _path:
            return
        _meta = read_project_meta(_path)
        _env = _meta.get("env_path", "")

        if not _env:
            QMessageBox.information(
                self, "No environment yet",
                f"{_meta['name']} has no environment.\n\n"
                f"Run its tool first \u2014 `uv sync`, `poetry install` or "
                f"`pdm install` \u2014 and its packages will appear here.")
            return

        _panel = getattr(self, "package_panel", None)
        if _panel is None:
            QMessageBox.warning(
                self, "Packages", "The packages page is not available.")
            return

        try:
            _panel.set_venv(Path(_env))
            self.selected_env = _meta["name"]
            self._switch_page(0)
            try:
                self.statusBar().showMessage(
                    f"Packages for project: {_meta['name']}  \u2014  {_env}")
            except Exception:
                pass
            _log.info(f"[Projects] packages for {_meta['name']} -> {_env}")
        except Exception as e:
            _log.warning(f"[Projects] could not open packages: {e!r}")
            QMessageBox.warning(self, "Packages", f"{type(e).__name__}: {e}")

    def _proj_open_terminal(self):
        _path = self._selected_project_path()
        if not _path:
            return
        try:
            from src.utils.platform_utils import open_terminal_at
            if not open_terminal_at(_path):
                QMessageBox.warning(
                    self, "Terminal",
                    f"A terminal could not be opened at:\n{_path}")
        except Exception as e:
            QMessageBox.warning(self, "Terminal", f"{type(e).__name__}: {e}")

    def _proj_open_folder(self):
        _path = self._selected_project_path()
        if not _path:
            return
        try:
            from src.utils.platform_utils import open_folder
            ok, msg = open_folder(_path)
            if not ok:
                QMessageBox.warning(self, "Open Folder", msg)
        except Exception as e:
            QMessageBox.warning(self, "Open Folder", f"{type(e).__name__}: {e}")

    def _clone_project(self):
        """Copy a project to a new folder beside it.

        Copies the tree and drops the environment: `.venv` is a build product,
        tied to absolute paths inside its own `pyvenv.cfg`, and a copied one
        points at the original. The clone gets a fresh one the first time its
        tool is run, which is both correct and what the tool expects. The same
        goes for caches and version control -- a clone is a new project, not a
        second checkout of the old one's history.
        """
        from PySide6.QtWidgets import QInputDialog, QApplication
        import shutil

        _src = self._selected_project_path()
        if not _src or not os.path.isdir(_src):
            return

        _parent = os.path.dirname(_src)
        _base = os.path.basename(_src)
        _suggest = f"{_base}-copy"
        _n = 2
        while os.path.exists(os.path.join(_parent, _suggest)):
            _suggest = f"{_base}-copy{_n}"
            _n += 1

        name, ok = QInputDialog.getText(
            self, "Clone Project",
            f"Copy of:\n{_src}\n\nName for the clone:", text=_suggest)
        if not ok or not name.strip():
            return
        _dst = os.path.join(_parent, name.strip())
        if os.path.exists(_dst):
            QMessageBox.warning(
                self, "Already there",
                f"This path already exists:\n{_dst}")
            return

        _skip = shutil.ignore_patterns(
            ".venv", "venv", "__pycache__", ".git", ".mypy_cache",
            ".pytest_cache", ".ruff_cache", ".tox", ".nox", "dist", "build",
            "*.pyc", ".DS_Store")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            shutil.copytree(_src, _dst, ignore=_skip, symlinks=True)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            _log.warning(f"[Projects] clone failed: {e!r}")
            QMessageBox.critical(self, "Clone failed", f"{type(e).__name__}: {e}")
            return
        finally:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass

        # Rename the project inside pyproject.toml as well, so the clone is
        # not a second row with the same name. Only the [project] name is
        # touched: [project.scripts] entries and the src/ package directory
        # keep the original name, because changing those would break the
        # imports they refer to. Anything deeper is the user's to do.
        try:
            _pp = os.path.join(_dst, "pyproject.toml")
            if os.path.isfile(_pp):
                with open(_pp, "r", encoding="utf-8") as fh:
                    _txt = fh.read()
                _old_name = read_project_meta(_src)["name"]
                _new_name = name.strip()
                if _old_name and _old_name != _new_name:
                    _txt = _txt.replace(f'name = "{_old_name}"',
                                        f'name = "{_new_name}"', 1)
                    with open(_pp, "w", encoding="utf-8") as fh:
                        fh.write(_txt)
        except Exception as e:
            _log.warning(f"[Projects] could not rename clone in pyproject: {e!r}")

        try:
            from src.utils.logger import banner_command
            banner_command(f'cp -r "{_src}" "{_dst}"'
                           if os.name != "nt" else
                           f'robocopy "{_src}" "{_dst}" /E /XD .venv .git __pycache__',
                           context=f"Clone project ({_base})")
        except Exception:
            pass

        self._record_project(_dst)
        _log.info(f"[Projects] cloned {_src} -> {_dst}")
        self._refresh_projects()
        QMessageBox.information(
            self, "Cloned",
            f"\u2705  {os.path.basename(_dst)}\n\n{_dst}\n\n"
            f"The environment was not copied \u2014 it is tied to the original "
            f"path. Run the project's tool there to create a fresh one.")

    def _delete_project(self):
        """Delete the project folder from disk, after asking twice.

        Two gates, because this is the one action here that cannot be undone
        and the folder may hold work that exists nowhere else. The second gate
        asks for the project's name to be typed: a confirm dialog is answered
        reflexively, a name is not.
        """
        from PySide6.QtWidgets import QInputDialog, QApplication
        import shutil

        _path = self._selected_project_path()
        if not _path or not os.path.isdir(_path):
            return
        _name = os.path.basename(_path)

        if QMessageBox.warning(
                self, "Delete from disk",
                f"Permanently delete this project and everything in it?\n\n"
                f"{_path}\n\n"
                f"This cannot be undone. If you only want it off the list, "
                f"use \u201cRemove from list\u201d instead.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No) != QMessageBox.Yes:
            return

        typed, ok = QInputDialog.getText(
            self, "Confirm deletion",
            f"Type the project name to confirm:\n\n{_name}")
        if not ok or typed.strip() != _name:
            if ok:
                QMessageBox.information(
                    self, "Not deleted",
                    "The name did not match, so nothing was deleted.")
            return

        try:
            from src.utils.logger import banner_command
            banner_command(f'rm -rf "{_path}"' if os.name != "nt"
                           else f'rmdir /s /q "{_path}"',
                           context=f"Delete project ({_name})")
        except Exception:
            pass

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            shutil.rmtree(_path)
        except Exception as e:
            _log.warning(f"[Projects] delete failed: {e!r}")
            QMessageBox.critical(self, "Delete failed", f"{type(e).__name__}: {e}")
            return
        finally:
            QApplication.restoreOverrideCursor()

        _log.info(f"[Projects] deleted {_path}")
        self._drop_project_record(_path)
        self._refresh_projects()

    def _clear_project_list(self):
        """Forget every listed project. The folders themselves are untouched."""
        _n = len(self._known_project_paths())
        if not _n:
            return
        if QMessageBox.question(
                self, "Clear list",
                f"Stop listing all {_n} projects?\n\n"
                f"No folders are deleted \u2014 scan again or create a project "
                f"to refill the list.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            self.config.set("recent_projects", [])
            self.config.save()
        except Exception as e:
            _log.warning(f"[Projects] could not clear list: {e!r}")
        self._refresh_projects()

    def _record_project(self, path):
        """Add a project to the recorded list (used by clone and by scan)."""
        try:
            import datetime
            meta = read_project_meta(path)
            entries = self.config.get("recent_projects", []) or []
            if not isinstance(entries, list):
                entries = []
            entries = [e for e in entries
                       if not (isinstance(e, dict)
                               and os.path.normcase(e.get("path", ""))
                               == os.path.normcase(str(path)))]
            entries.insert(0, {
                "name": meta["name"], "path": str(path), "tool": meta["tool"],
                "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            self.config.set("recent_projects", entries[:100])
            self.config.save()
        except Exception as e:
            _log.warning(f"[Projects] could not record {path}: {e!r}")

    def _drop_project_record(self, path):
        """Remove a project from the recorded list, leaving the disk alone."""
        try:
            entries = self.config.get("recent_projects", []) or []
            entries = [e for e in entries
                       if not (isinstance(e, dict)
                               and os.path.normcase(e.get("path", ""))
                               == os.path.normcase(str(path)))]
            self.config.set("recent_projects", entries)
            self.config.save()
        except Exception as e:
            _log.warning(f"[Projects] could not drop {path}: {e!r}")

    def _forget_project(self):
        """Drop it from the list. The directory itself is left alone.

        Deleting a project from disk is stage 3, and deliberately not offered
        yet: removing a row and removing someone's work should never be one
        click apart until the second one is properly guarded.
        """
        _path = self._selected_project_path()
        if not _path:
            return
        if QMessageBox.question(
                self, "Remove from list",
                f"Stop listing this project?\n\n{_path}\n\n"
                f"The folder itself is not touched.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._drop_project_record(_path)
        self._refresh_projects()
