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
from src.utils.platform_utils import terminal_icon as _terminal_icon

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

    # pdm can be configured for PEP 582, where there is no virtualenv at all:
    # packages go into __pypackages__/<x.y>/lib and are found through
    # PYTHONPATH. `pdm install` then succeeds while creating no .venv, which
    # is why it reported success and VenvStudio found nothing.
    #
    # There is no interpreter to point at here, so the directory itself is
    # returned; count_installed reads its site-packages layout, and the
    # package panel is told about it rather than left guessing.
    _pyp = d / "__pypackages__"
    if _pyp.is_dir():
        try:
            _vers = sorted((x for x in _pyp.iterdir() if x.is_dir()),
                           reverse=True)
            if _vers:
                return str(_vers[0])
        except OSError:
            pass

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


def ask_tool_for_env(project_dir, tool: str) -> str:
    """Ask the tool itself where its environment is. Slow, and definitive.

    The guesses above cover the common layouts, but a guess is not good enough
    for someone who has to install packages into the thing: poetry hashes the
    project's absolute path into its directory name, and no amount of matching
    on the project's name will find it when the name and the folder differ, or
    when two projects share a name.

    Each tool will simply say, given the chance:

        poetry env info --path
        pdm venv --path in-project
        hatch env find
        pixi info --json

    This runs a subprocess, which is why it is not on the refresh path -- it
    is called once, when a project's environment could not be found, and the
    answer is cached so it never runs for that project again.
    """
    import subprocess

    # Verified against each tool's --help on 2026-09-01:
    #   poetry env info -p/--path   "Only display the environment's path."
    #   pdm venv --path PATH        "Show the path to the given virtualenv"
    #   hatch env find [ENV_NAME]   "Locate environments."
    _cmds = {
        "poetry": ["poetry", "env", "info", "--path"],
        "pdm":    ["pdm", "venv", "--path", "in-project"],
        "hatch":  ["hatch", "env", "find"],
    }
    argv = _cmds.get(tool)
    if not argv:
        return ""

    # Never by bare name -- three separate bugs in this codebase came from it.
    try:
        from src.core.tool_registry import ToolRegistry
        _exe = ToolRegistry.find(argv[0])
        if _exe:
            argv = [str(_exe)] + argv[1:]
    except Exception:
        pass

    try:
        from src.utils.platform_utils import subprocess_args
        _kw = subprocess_args()
    except Exception:
        _kw = {}

    try:
        _log.info(f"[Projects] asking {tool} for its env: {' '.join(argv)}")
        r = subprocess.run(argv, cwd=str(project_dir), capture_output=True,
                           text=True, timeout=30, **_kw)
        _out = (r.stdout or "").strip().splitlines()
        for line in _out:
            line = line.strip()
            if line and os.path.isdir(line):
                _log.info(f"[Projects]   -> {line}")
                return line
    except subprocess.TimeoutExpired:
        _log.warning(f"[Projects] {tool} did not answer within 30s")
    except Exception as e:
        _log.warning(f"[Projects] asking {tool} failed: {e!r}")
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


def dir_size(path, cap_seconds: float = 2.0) -> int:
    """Bytes under `path`, giving up rather than blocking the interface.

    B46 (Bayram, 2026-09-03): the Environments page shows a size per row and a
    total in its header; Projects showed neither.

    Two things make this different from the environments case. First, walking
    a tree is slow, and this runs for every project on every refresh -- so it
    stops after `cap_seconds` and returns what it has, which is better than a
    frozen table. Second, `.venv` directories are enormous next to the source
    beside them, so the two are measured separately and shown in their own
    columns; adding them together would answer neither "how big is my code"
    nor "how much do my dependencies cost".

    The environment is skipped here and measured on its own.
    """
    import time
    if not path or not os.path.isdir(path):
        return 0
    _deadline = time.monotonic() + cap_seconds
    _skip = {".venv", "venv", "__pycache__", ".git", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", ".tox", ".nox", "__pypackages__",
             ".pixi"}
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in _skip]
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
            if time.monotonic() > _deadline:
                break
    except OSError:
        pass
    return total


def fmt_size(n: float) -> str:
    """Bytes as something a person reads, matching the environments page."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return "?"


def count_installed(env_path) -> int:
    """How many packages are installed in this environment.

    Counts `*.dist-info` directories in site-packages rather than running pip:
    this is called for every project on every refresh, and a subprocess each
    time would make the page as slow as the startup we just finished fixing.
    """
    if not env_path:
        return 0
    base = Path(env_path)
    # `lib` (no python*/ level) is pdm's PEP 582 layout:
    # __pypackages__/3.14/lib/<package>
    for site in (base.glob("lib/python*/site-packages"),
                 [base / "Lib" / "site-packages"],
                 [base / "lib"]):
        for sp in site:
            if sp.is_dir():
                try:
                    _n = sum(1 for x in sp.iterdir()
                             if x.name.endswith(".dist-info"))
                    if _n:
                        return _n
                    # pdm's PEP 582 tree may hold the packages without their
                    # .dist-info directories, so fall back to counting the
                    # importable entries: real directories and modules, minus
                    # the bookkeeping ones.
                    _skip = {"__pycache__", "bin", "Scripts", "_distutils_hack"}
                    return sum(
                        1 for x in sp.iterdir()
                        if x.name not in _skip
                        and not x.name.startswith((".", "_"))
                        and (x.is_dir() or x.suffix == ".py"))
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

    # B46: the two sizes, measured apart. Source excludes .venv and the
    # caches; the environment is whatever the tool built, wherever it put it.
    meta["src_bytes"] = dir_size(d)
    meta["env_bytes"] = dir_size(meta["env_path"]) if meta["env_path"] else 0
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

        self.projects_table = QTableWidget(0, 8)
        # "Required" and "Installed" rather than "Deps" and "Env": Bayram read
        # the old pair twice and could not tell what either meant, which is a
        # fair verdict on a column called "Deps" showing a number and one
        # called "Env" showing a tick.
        self.projects_table.setHorizontalHeaderLabels(
            ["Project", "Tool", "Python", "Required", "Installed",
             "Source", "Env Size", "Location"])
        _h = self.projects_table.horizontalHeader()
        # 300, and resizable: "test_pdm_project-copy" was cut to
        # "test_pdm_project-..." at 240, and a name you cannot read is the one
        # column that has to be legible.
        _h.setSectionResizeMode(0, QHeaderView.Interactive)
        self.projects_table.setColumnWidth(0, 300)
        for _i, _w in ((1, 110), (2, 110), (3, 100), (4, 110),
                       (5, 100), (6, 100)):
            _h.setSectionResizeMode(_i, QHeaderView.Fixed)
            self.projects_table.setColumnWidth(_i, _w)
        _h.setSectionResizeMode(7, QHeaderView.Stretch)
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
        # B46: double-click opens Packages, not a terminal. Looking at what
        # is installed is the commoner intent, and the terminal is one
        # right-click away.
        self.projects_table.itemDoubleClicked.connect(
            lambda _i: self._proj_open_packages())
        self.projects_table.itemSelectionChanged.connect(
            self._update_project_buttons)
        layout.addWidget(self.projects_table, 1)

        # ── Command Reference panel (B49) ────────────────────────────────
        # The Environments page has had this since the beginning and Projects
        # had nothing like it: the command a button is about to run, shown in
        # full before it runs. That is the first pillar of this product, and
        # leaving it off the page where the commands are least familiar --
        # `pdm add`, `hatch env create`, `uv sync` -- was the wrong way round.
        #
        # Hidden until an action populates it, exactly as the other page does.
        from PySide6.QtWidgets import QTextEdit as _QTE, QWidget as _QW
        self._proj_cmd_panel = _QW()
        _pcl = QVBoxLayout(self._proj_cmd_panel)
        _pcl.setContentsMargins(0, 0, 0, 0)
        _pcl.setSpacing(6)

        _pct = QLabel("\U0001f4a1 Command Reference")
        _pct.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #89b4fa; "
            "padding: 4px 2px 2px 2px;")
        _pcl.addWidget(_pct)

        self._proj_cmd_live = QLabel("\u25b6")
        self._proj_cmd_live.setWordWrap(True)
        self._proj_cmd_live.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._proj_cmd_live.setStyleSheet(
            "color: #f9e2af; font-size: 20px; font-weight: bold; "
            "font-family: Consolas, monospace; padding: 10px 12px; "
            "background: #181825; border: 2px solid #f9e2af; border-radius: 6px;")
        _pcl.addWidget(self._proj_cmd_live)

        self._proj_cmd_hints = _QTE()
        self._proj_cmd_hints.setReadOnly(True)
        self._proj_cmd_hints.setFixedHeight(160)
        self._proj_cmd_hints.setStyleSheet(
            "background-color: #181825; border: 1px solid #313244; "
            "border-radius: 8px; padding: 8px; color: #cdd6f4; "
            "font-family: Consolas, monospace; font-size: 16px; font-weight: bold;")
        _pcl.addWidget(self._proj_cmd_hints)

        self._proj_cmd_panel.setVisible(False)
        layout.addWidget(self._proj_cmd_panel)

        # B46: an action bar, as the Environments page has had all along.
        #
        # Everything here was reachable only by right-clicking, which is fine
        # for the occasional action and wrong for the ones you use constantly.
        # Four to begin with -- the ones a project needs day to day. Sync is
        # first because it is the command you run most: it makes the
        # environment match what the project declares.
        #
        # NOT copied from Environments, and why: "Make Default" means nothing
        # for a project, and "Rename (Full)" would have to change the folder,
        # [project] name, the src/ package directory and every
        # [project.scripts] entry together -- doing half of that breaks the
        # project.
        _actions = QHBoxLayout()
        _actions.setSpacing(8)

        self._pbtn_sync = QPushButton("\u21bb  Sync")
        self._pbtn_sync.setFixedHeight(38)
        self._pbtn_sync.setToolTip(
            "Install what this project declares, using its own tool")
        self._pbtn_sync.clicked.connect(self._proj_sync)
        _actions.addWidget(self._pbtn_sync)

        self._pbtn_add = QPushButton("\u2795  Add Package")
        self._pbtn_add.setObjectName("secondary")
        self._pbtn_add.setFixedHeight(38)
        self._pbtn_add.setToolTip(
            "Add a dependency \u2014 writes pyproject.toml and installs it")
        self._pbtn_add.clicked.connect(self._proj_add_selected)
        _actions.addWidget(self._pbtn_add)

        self._pbtn_pkgs = QPushButton("\U0001f4e6  Packages")
        self._pbtn_pkgs.setObjectName("secondary")
        self._pbtn_pkgs.setFixedHeight(38)
        self._pbtn_pkgs.clicked.connect(self._proj_open_packages)
        _actions.addWidget(self._pbtn_pkgs)

        self._pbtn_term = QPushButton(f"{_terminal_icon()}Open Terminal")
        self._pbtn_term.setObjectName("secondary")
        self._pbtn_term.setFixedHeight(38)
        self._pbtn_term.clicked.connect(self._proj_open_terminal)
        _actions.addWidget(self._pbtn_term)

        # B49: the rest of what Environments offers, minus what a project has
        # no use for. "Make Default" means nothing here -- there is no default
        # project -- and Environments' two Rename buttons collapse into one,
        # because a project's folder name, [project] name, src/ package
        # directory and [project.scripts] entries all refer to each other and
        # renaming half of them leaves it broken.
        self._pbtn_clone = QPushButton("\U0001f4cb Clone")
        self._pbtn_clone.setObjectName("secondary")
        self._pbtn_clone.setFixedHeight(38)
        self._pbtn_clone.clicked.connect(self._clone_project)
        _actions.addWidget(self._pbtn_clone)

        self._pbtn_rename = QPushButton("\u270f Rename")
        self._pbtn_rename.setObjectName("secondary")
        self._pbtn_rename.setFixedHeight(38)
        self._pbtn_rename.setToolTip(
            "Rename the folder and the project name together")
        self._pbtn_rename.clicked.connect(self._rename_project)
        _actions.addWidget(self._pbtn_rename)

        self._pbtn_export = QPushButton("\U0001f4e4 Export \u25be")
        self._pbtn_export.setObjectName("secondary")
        self._pbtn_export.setFixedHeight(38)
        _emenu = QMenu(self._pbtn_export)
        _emenu.addAction("\U0001f4c4 requirements.txt (from the environment)",
                         lambda: self._export_project("requirements"))
        _emenu.addAction("\U0001f4cb Copy pyproject.toml to clipboard",
                         lambda: self._export_project("pyproject"))
        _emenu.addSeparator()
        _emenu.addAction("\U0001f4cb Copy the project's own commands",
                         lambda: self._export_project("commands"))
        self._pbtn_export.setMenu(_emenu)
        _actions.addWidget(self._pbtn_export)

        _actions.addStretch()

        self._pbtn_delete = QPushButton("\U0001f5d1\ufe0f Delete")
        self._pbtn_delete.setObjectName("danger")
        self._pbtn_delete.setFixedHeight(38)
        self._pbtn_delete.setToolTip("Delete the project folder from disk")
        self._pbtn_delete.clicked.connect(self._delete_project)
        _actions.addWidget(self._pbtn_delete)

        layout.addLayout(_actions)

        self._refresh_projects()
        self._update_project_buttons()
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
        if not _n:
            self.projects_info.setText(
                "No projects  \u2014  create one, or press Scan for Projects "
                "to find existing ones on disk")
            return

        # B46: a summary line like the Environments page has -- grouped by
        # tool, with sizes, and a total. The sizes are already computed for
        # the table, so this costs nothing extra.
        _by_tool, _src_total, _env_total = {}, 0, 0
        for _p in paths:
            _m = read_project_meta(_p)
            if not _m["has_env"]:
                _c = self._cached_env_for(_p)
                if _c:
                    _m["env_path"] = _c
                    _m["env_bytes"] = dir_size(_c)
            _t = _m["tool"] or "other"
            _g = _by_tool.setdefault(_t, {"n": 0, "src": 0, "env": 0})
            _g["n"] += 1
            _g["src"] += _m["src_bytes"]
            _g["env"] += _m["env_bytes"]
            _src_total += _m["src_bytes"]
            _env_total += _m["env_bytes"]

        _parts = [f"\U0001f5c2 {_n} project{'s' if _n != 1 else ''}"]
        for _t in sorted(_by_tool):
            _g = _by_tool[_t]
            _icon = self._TOOL_ICONS.get(_t, "\U0001f4c1")
            _parts.append(
                f"{_icon} {_t}  \u2022  {_g['n']}  \u2022  "
                f"{fmt_size(_g['src'] + _g['env'])}")
        _parts.append(
            f"\U0001f4be total  \u2022  {fmt_size(_src_total + _env_total)}  "
            f"(source {fmt_size(_src_total)} + env {fmt_size(_env_total)})")
        self.projects_info.setText("        ".join(_parts))

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
        # N88: this table also takes its size from a stylesheet in pixels, so
        # a plain QFont(t.font()) copy would carry pointSize -1 and Qt would
        # warn when it came to draw the cells.
        from src.utils.platform_utils import bold_font_from as _bold_font
        _cell_font = _bold_font(t)
        for row, path in enumerate(paths):
            meta = read_project_meta(path)
            # A path the tool told us about earlier counts too, so poetry and
            # hatch projects stop showing a dash once they have been opened.
            if not meta["has_env"]:
                _cached = self._cached_env_for(path)
                if _cached:
                    meta["env_path"] = _cached
                    meta["has_env"] = True
                    meta["installed"] = count_installed(_cached)
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

            _src = QTableWidgetItem(
                fmt_size(meta["src_bytes"]) if meta["src_bytes"] else "\u2014")
            _src.setTextAlignment(Qt.AlignCenter)
            _src.setFont(_cell_font)
            _src.setToolTip(
                "The project's own files \u2014 the environment, .git and the "
                "caches are not counted")
            t.setItem(row, 5, _src)

            _envsz = QTableWidgetItem(
                fmt_size(meta["env_bytes"]) if meta["env_bytes"] else "\u2014")
            _envsz.setTextAlignment(Qt.AlignCenter)
            _envsz.setFont(_cell_font)
            _envsz.setToolTip(
                f"{meta['env_path']}" if meta["env_path"]
                else "No environment yet")
            t.setItem(row, 6, _envsz)

            _loc = QTableWidgetItem(path)
            _loc.setFont(_cell_font)
            try:
                _loc.setForeground(QColor(self._c()["fg_muted"]))
            except Exception:
                pass
            t.setItem(row, 7, _loc)

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
        # Always enabled. Disabling it on `has_env` looked careful and was
        # wrong: has_env only reflects the GUESS, so poetry and hatch projects
        # -- the very ones that need the tool to be asked -- had the action
        # greyed out, and the code that would have asked sits behind the click
        # it could no longer receive. Clicking now either opens the packages,
        # asks the tool, or explains what to run. All three beat a dead entry.
        menu.addAction("\U0001f4e6  Packages\u2026", self._proj_open_packages)

        # Offered on its own too, so "set this project up" does not have to be
        # discovered by clicking something else first.
        _meta_for_menu = read_project_meta(_path)
        if not _meta_for_menu["has_env"] and \
                not self._cached_env_for(_path) and \
                _meta_for_menu["tool"] in self._ENV_CREATE:
            _cmd = " ".join(self._ENV_CREATE[_meta_for_menu["tool"]])
            _act = menu.addAction(
                f"\u2699\ufe0f  Create Environment  ({_cmd})",
                lambda: self._create_project_env(_path, _meta_for_menu))
            if not _meta_for_menu.get("deps"):
                # Offering it would produce nothing and say so afterwards.
                _act.setEnabled(False)
                _act.setToolTip(
                    "This project declares no dependencies, so there is "
                    "nothing to install yet")
        # B43: adding a dependency is the thing a project is for, and the
        # only command that does it correctly -- writing pyproject.toml AND
        # installing -- is the tool's own `add`. pip would install the package
        # and leave the project declaring nothing.
        if _meta_for_menu["tool"] in self._ADD_CMD:
            menu.addAction(
                f"\u2795  Add Package\u2026  "
                f"({' '.join(self._ADD_CMD[_meta_for_menu['tool']])} \u2026)",
                lambda: self._proj_add_package(_path, _meta_for_menu))

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
        _env = _meta.get("env_path", "") or self._cached_env_for(_path)

        # Guessing covers uv, pdm and pixi, which keep the environment inside
        # the project. Poetry and hatch do not, and poetry hashes the absolute
        # path into the directory name -- so for those, ask the tool. Once.
        # An empty dependency list means there is nothing for the tool to do,
        # so asking it costs a subprocess to learn what pyproject.toml already
        # said.
        if not _env and _meta.get("deps") and \
                _meta["tool"] in ("poetry", "hatch", "pdm"):
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                _env = ask_tool_for_env(_path, _meta["tool"])
            finally:
                QApplication.restoreOverrideCursor()
            if _env:
                self._cache_env_for(_path, _env)

        if not _env:
            # B43: create it here rather than telling the user to go and do it.
            #
            # The first version printed "run `poetry install` in the project
            # folder" and Bayram's reply was the right one: why are we making
            # the user run these? An application whose whole purpose is to keep
            # people out of the terminal should not send them there for the one
            # step that stands between them and the thing they asked for.
            #
            # It still ASKS first -- these commands download packages and can
            # take minutes -- and it shows exactly what it will run, because
            # that is the other half of the bargain.
            _env = self._create_project_env(_path, _meta)
            if not _env:
                return

        _panel = getattr(self, "package_panel", None)
        if _panel is None:
            QMessageBox.warning(
                self, "Packages", "The packages page is not available.")
            return

        try:
            # Tell the panel what it is looking at: the tool comes from
            # pyproject.toml, which is better than anything the panel could
            # infer from a directory called ".venv".
            _panel.set_venv(Path(_env),
                            env_type=_meta["tool"] or "venv",
                            label=_meta["name"])
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

    _SYNC_CMD = {
        # "Install what this project declares, from its lockfile."
        # Verified against --help on 2026-09-01:
        #   uv sync          "Update the project's environment"
        #   poetry install   "Installs the project dependencies."
        #   pdm install      "Install dependencies from lock file"
        #   pixi install     resolves and installs the workspace
        #   hatch env create builds the environment for the project
        "uv":     ["uv", "sync"],
        "poetry": ["poetry", "install"],
        "pdm":    ["pdm", "install"],
        "pixi":   ["pixi", "install"],
        "hatch":  ["hatch", "env", "create"],
    }

    _ADD_CMD = {
        # Each tool's own way of adding a dependency: it edits pyproject.toml
        # and installs in one step. `pip install` into the environment would
        # do half the job and leave the project unable to describe itself.
        "uv":     ["uv", "add"],
        "poetry": ["poetry", "add"],
        "pdm":    ["pdm", "add"],
        "hatch":  ["hatch", "add"],
        "pixi":   ["pixi", "add"],
    }

    _ENV_CREATE = {
        # Verified against each tool's own documentation and --help output.
        # These are the commands that resolve dependencies and build the
        # environment; each is the one its own quickstart tells you to run.
        "uv":     ["uv", "sync"],
        "poetry": ["poetry", "install"],
        "pdm":    ["pdm", "install"],
        "hatch":  ["hatch", "env", "create"],
        "pixi":   ["pixi", "install"],
    }

    def _proj_sync(self):
        """Install what the selected project declares, with its own tool.

        B46: the command a project needs most often. `uv sync`, `poetry
        install`, `pdm install` -- each reads the project's lockfile and makes
        the environment match it.

        Shares _create_project_env, which already asks first, shows the
        command, runs it and finds the environment afterwards. A second
        implementation would drift from that one within a release.
        """
        _path = self._selected_project_path()
        if not _path:
            return
        _meta = read_project_meta(_path)
        if _meta.get("tool") not in self._SYNC_CMD:
            QMessageBox.information(
                self, "No tool",
                f"{_meta['name']} has no recognised project tool, so "
                f"VenvStudio does not know how to install its dependencies.")
            return
        self._run_project_command(
            _path, _meta, self._SYNC_CMD[_meta["tool"]], "Sync")

    def _proj_add_selected(self):
        """Add Package for the selected row (the toolbar's version)."""
        _path = self._selected_project_path()
        if not _path:
            return
        self._proj_add_package(_path, read_project_meta(_path))

    def _update_project_buttons(self):
        """Enable the action bar only when a row is selected (B46).

        Buttons that do nothing when pressed teach people not to trust them.
        Sync is disabled further when the project has no recognised tool,
        since there would be no command to run.
        """
        _path = self._selected_project_path()
        _has = bool(_path)
        for _b in (self._pbtn_add, self._pbtn_pkgs, self._pbtn_term,
                   self._pbtn_clone, self._pbtn_rename, self._pbtn_export,
                   self._pbtn_delete):
            _b.setEnabled(_has)

        if not _has:
            self._pbtn_sync.setEnabled(False)
            self._pbtn_sync.setText("\u21bb  Sync")
            return

        try:
            _meta = read_project_meta(_path)
        except Exception:
            self._pbtn_sync.setEnabled(False)
            return
        _tool = _meta.get("tool", "")
        _cmd = self._SYNC_CMD.get(_tool)
        self._pbtn_sync.setEnabled(bool(_cmd))
        # Name the command on the button: this is a tool that means to teach
        # what it runs, and "Sync" alone says nothing about which command.
        self._pbtn_sync.setText(
            f"\u21bb  {' '.join(_cmd)}" if _cmd else "\u21bb  Sync")
        self._pbtn_sync.setToolTip(
            f"Run `{' '.join(_cmd)}` in {_path}" if _cmd
            else "No recognised project tool")

    def _proj_add_package(self, project_path, meta):
        """Add a dependency with the project's own tool."""
        from PySide6.QtWidgets import QInputDialog, QApplication
        import subprocess

        argv = list(self._ADD_CMD.get(meta.get("tool", ""), []))
        if not argv:
            return

        pkgs, ok = QInputDialog.getText(
            self, "Add Package",
            f"Packages to add to {meta['name']}:\n\n"
            f"    {' '.join(argv)} <packages>\n\n"
            f"Separate several with spaces.")
        if not ok or not pkgs.strip():
            return
        argv += pkgs.split()
        self._show_project_command(
            " ".join(argv),
            f"Runs in: {project_path}\n\n"
            f"This writes the dependency into pyproject.toml AND installs it.\n"
            f"`pip install` would do only the second half, leaving the project "
            f"not declaring something it needs.")

        try:
            from src.core.tool_registry import ToolRegistry
            _exe = ToolRegistry.find(argv[0])
            if _exe:
                argv = [str(_exe)] + argv[1:]
        except Exception:
            pass

        try:
            from src.utils.logger import banner_command
            banner_command(" ".join(argv),
                           context=f"Add packages ({meta['name']})")
        except Exception:
            pass

        try:
            from src.utils.platform_utils import subprocess_args
            _kw = subprocess_args()
        except Exception:
            _kw = {}

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            _log.info(f"[Projects] {' '.join(argv)}")
            r = subprocess.run(argv, cwd=str(project_path), capture_output=True,
                               text=True, timeout=900, **_kw)
            _log.info(f"[Projects]   -> exit={r.returncode}")
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Failed", f"{type(e).__name__}: {e}")
            return
        finally:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass

        if r.returncode != 0:
            _detail = (r.stderr or r.stdout or "").strip()
            QMessageBox.warning(self, f"{argv[0]} failed",
                                _detail[:1500] or f"exit code {r.returncode}")
            return

        # The environment usually appears with the first dependency.
        _fresh = find_project_env(project_path, meta.get("tool", ""))
        if _fresh:
            self._cache_env_for(project_path, _fresh)
        self._refresh_projects()
        QMessageBox.information(
            self, "Added",
            f"\u2705  {pkgs.strip()}\n\nadded to {meta['name']} and written "
            f"to its pyproject.toml.")

    def _run_project_command(self, project_path, meta, argv, what: str) -> str:
        """Run one of the project tool's commands, asking first.

        B46: shared by Sync and by Create Environment, which do the same thing
        from different buttons -- ask, show the command, run it, then look for
        the environment the tool has just built or updated. Two copies of this
        would have drifted; there are enough examples of that in this codebase.

        Returns the environment path afterwards, or "" if the user declined or
        the command failed.
        """
        from PySide6.QtWidgets import QApplication
        import subprocess

        argv = list(argv)
        _tool = meta.get("tool", "")

        # B49: show it in the panel too, so it stays readable after the
        # dialog is gone -- and stays there while the command runs.
        self._show_project_command(
            " ".join(argv),
            f"Runs in: {project_path}\n\n"
            f"Tool: {meta.get('tool') or 'unknown'}\n"
            f"Declared dependencies: {meta.get('deps', 0)}")

        if QMessageBox.question(
                self, f"{what}?",
                f"{meta['name']}\n\n"
                f"VenvStudio will run:\n\n    {' '.join(argv)}\n\n"
                f"in {project_path}\n\n"
                f"This resolves and downloads dependencies, and may take a "
                f"few minutes. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes) != QMessageBox.Yes:
            return ""

        # Never by bare name -- three bugs in this codebase came from that.
        try:
            from src.core.tool_registry import ToolRegistry
            _exe = ToolRegistry.find(argv[0])
            if _exe:
                argv = [str(_exe)] + argv[1:]
        except Exception:
            pass

        try:
            from src.utils.logger import banner_command
            banner_command(" ".join(argv),
                           context=f"{what} ({meta['name']})")
        except Exception:
            pass

        try:
            from src.utils.platform_utils import subprocess_args
            _kw = subprocess_args()
        except Exception:
            _kw = {}

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            _log.info(f"[Projects] {' '.join(argv)}")
            r = subprocess.run(argv, cwd=str(project_path), capture_output=True,
                               text=True, timeout=900, **_kw)
            _log.info(f"[Projects]   -> exit={r.returncode}")
        except subprocess.TimeoutExpired:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self, "Timed out",
                f"{_tool} did not finish within fifteen minutes.\n\n"
                f"Right-click \u2192 Open Terminal to run it there and watch "
                f"the output.")
            return ""
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Failed", f"{type(e).__name__}: {e}")
            return ""
        finally:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass

        if r.returncode != 0:
            _detail = (r.stderr or r.stdout or "").strip()
            _log.warning(f"[Projects] {what} failed: {_detail[:400]}")
            QMessageBox.warning(
                self, f"{_tool} could not finish",
                _detail[:1500] or f"{_tool} exited with code {r.returncode}.")
            return ""

        _fresh = find_project_env(project_path, _tool) or \
            ask_tool_for_env(project_path, _tool)
        if _fresh:
            self._cache_env_for(project_path, _fresh)
        self._refresh_projects()
        self._update_project_buttons()

        if not _fresh and not meta.get("deps"):
            QMessageBox.information(
                self, "Nothing to install",
                f"{meta['name']} declares no dependencies, so {_tool} had "
                f"nothing to install.\n\nAdd one with the Add Package button "
                f"and the environment will appear with it.")
        return _fresh

    def _create_project_env(self, project_path, meta) -> str:
        """Build the project's environment with its own tool.

        B46: this is now a thin wrapper. Sync and Create Environment run the
        same shape of command and used to have their own copies of the ask,
        the run and the look-afterwards; both go through
        _run_project_command instead. Two copies of that would have drifted
        within a release, as several pairs in this codebase already have.
        """
        _tool = meta.get("tool", "")
        argv = self._ENV_CREATE.get(_tool)
        if not argv:
            QMessageBox.information(
                self, "No environment yet",
                f"{meta['name']} has no environment, and VenvStudio does not "
                f"know how to build one for a project with no recognised "
                f"tool.\n\nRight-click \u2192 Open Terminal to do it by hand.")
            return ""
        return self._run_project_command(
            project_path, meta, argv, "Create environment")

    def _cached_env_for(self, project_path) -> str:
        """An environment path previously answered by the tool itself."""
        try:
            _m = self.config.get("project_envs", {}) or {}
            _p = _m.get(os.path.normcase(str(project_path)), "")
            return _p if _p and os.path.isdir(_p) else ""
        except Exception:
            return ""

    def _cache_env_for(self, project_path, env_path):
        """Remember it, so the tool is asked once and not on every refresh."""
        try:
            _m = self.config.get("project_envs", {}) or {}
            if not isinstance(_m, dict):
                _m = {}
            _m[os.path.normcase(str(project_path))] = str(env_path)
            self.config.set("project_envs", _m)
            self.config.save()
        except Exception as e:
            _log.warning(f"[Projects] could not cache env path: {e!r}")

    def _proj_open_terminal(self):
        _path = self._selected_project_path()
        if not _path:
            return
        try:
            from src.utils.platform_utils import open_terminal_at

            # B51 (Bayram, 2026-09-03): every project terminal opened with
            # "The system cannot find the path specified".
            #
            # open_terminal_at defaults env_type to "venv" and this call passed
            # nothing, so it went looking for <project>/Scripts/activate.bat --
            # a file no project folder has. The environment is somewhere else
            # entirely, and for poetry it is in a cache directory.
            #
            # The function already knows every one of these tools by name
            # (poetry, pdm, hatch, pixi, conda) and builds the right command
            # for each: `poetry run`, `pixi shell`, and so on. It only had to
            # be told which one this is.
            #
            # An earlier attempt passed "system_tools", which cured the error
            # by removing the activation altogether -- Bayram's objection was
            # the right one. An activated shell is the point.
            _meta_t = read_project_meta(_path)
            _tool_t = _meta_t.get("tool", "")

            if _tool_t in ("poetry", "pdm", "hatch", "pixi"):
                _env_arg = _tool_t
            elif (_meta_t.get("env_path") or self._cached_env_for(_path)):
                # uv, or anything else keeping a plain virtualenv: the venv
                # branch is correct, and there is one to activate.
                _env_arg = "venv"
            else:
                # No environment yet -- there is nothing to activate, and
                # asking for one is exactly how the original error happened.
                _env_arg = "system_tools"

            if not open_terminal_at(_path, env_type=_env_arg):
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

    def _show_project_command(self, command: str, hints: str = ""):
        """Put a command in the reference panel and reveal it (B49).

        The Environments page has shown its commands this way for a long time.
        Doing the same here matters more, not less: `pdm add`, `hatch env
        create` and `uv sync` are exactly the commands a reader is least
        likely to know already.
        """
        try:
            self._proj_cmd_live.setText(f"\u25b6  {command}")
            self._proj_cmd_hints.setPlainText(hints or "")
            self._proj_cmd_hints.setVisible(bool(hints))
            self._proj_cmd_panel.setVisible(True)
        except Exception:
            pass

    def _rename_project(self):
        """Rename the folder and the declared project name together.

        B49: Environments offers two kinds of rename -- folder only, or a full
        clone-and-delete. Neither shape fits a project, where the folder name,
        the [project] name, the src/ package directory and every
        [project.scripts] entry refer to one another. Renaming some of them
        leaves a project that cannot import itself.

        So this renames the folder and the [project] name, and says plainly
        what it did NOT touch, rather than pretending the job is finished.
        """
        from PySide6.QtWidgets import QInputDialog

        _path = self._selected_project_path()
        if not _path or not os.path.isdir(_path):
            return
        _meta = read_project_meta(_path)
        _old_dir = os.path.basename(_path)
        _parent = os.path.dirname(_path)

        name, ok = QInputDialog.getText(
            self, "Rename Project",
            f"Current folder:  {_old_dir}\n"
            f"Current name:    {_meta['name']}\n\n"
            f"New name:", text=_old_dir)
        if not ok or not name.strip() or name.strip() == _old_dir:
            return
        _new = name.strip()
        _dst = os.path.join(_parent, _new)
        if os.path.exists(_dst):
            QMessageBox.warning(
                self, "Already there", f"This path already exists:\n{_dst}")
            return

        self._show_project_command(
            f'mv "{_path}" "{_dst}"' if os.name != "nt"
            else f'move "{_path}" "{_dst}"',
            "The [project] name in pyproject.toml is updated to match.\n\n"
            "NOT changed, because other files import them by name:\n"
            "  \u2022 the src/ package directory\n"
            "  \u2022 [project.scripts] entries\n"
            "  \u2022 the environment, which is rebuilt on the next sync")

        try:
            os.rename(_path, _dst)
        except Exception as e:
            QMessageBox.critical(self, "Rename failed", f"{type(e).__name__}: {e}")
            return

        try:
            _pp = os.path.join(_dst, "pyproject.toml")
            if os.path.isfile(_pp):
                with open(_pp, "r", encoding="utf-8") as fh:
                    _txt = fh.read()
                if _meta["name"]:
                    _txt = _txt.replace(f'name = "{_meta["name"]}"',
                                        f'name = "{_new}"', 1)
                    with open(_pp, "w", encoding="utf-8") as fh:
                        fh.write(_txt)
        except Exception as e:
            _log.warning(f"[Projects] renamed the folder but not the name: {e!r}")

        try:
            from src.utils.logger import banner_command
            banner_command(f'mv "{_path}" "{_dst}"',
                           context=f"Rename project ({_old_dir} \u2192 {_new})")
        except Exception:
            pass

        self._drop_project_record(_path)
        self._record_project(_dst)
        self._refresh_projects()
        _log.info(f"[Projects] renamed {_path} -> {_dst}")

    def _export_project(self, kind: str):
        """Export something useful about the project (B49).

        Not a copy of the Environments export menu: a project already declares
        its dependencies in pyproject.toml, so a requirements.txt of what it
        DECLARES would just be that file in a worse format. What is worth
        exporting is what is actually INSTALLED, which is a different list.
        """
        from PySide6.QtWidgets import QFileDialog, QApplication
        import subprocess

        _path = self._selected_project_path()
        if not _path:
            return
        _meta = read_project_meta(_path)

        if kind == "pyproject":
            _pp = os.path.join(_path, "pyproject.toml")
            if not os.path.isfile(_pp):
                QMessageBox.information(self, "Export",
                                        "This project has no pyproject.toml.")
                return
            try:
                QApplication.clipboard().setText(
                    open(_pp, encoding="utf-8").read())
                QMessageBox.information(
                    self, "Copied", "pyproject.toml is on the clipboard.")
            except Exception as e:
                QMessageBox.warning(self, "Export", f"{type(e).__name__}: {e}")
            return

        if kind == "commands":
            _tool = _meta.get("tool", "")
            _lines = []
            for _label, _table in (("Install", self._SYNC_CMD),
                                   ("Add a package", self._ADD_CMD)):
                _c = _table.get(_tool)
                if _c:
                    _lines.append(f"# {_label}\n{' '.join(_c)}")
            if not _lines:
                QMessageBox.information(
                    self, "Export",
                    "This project has no recognised tool, so there are no "
                    "commands to copy.")
                return
            _text = f"# {_meta['name']} \u2014 {_tool}\ncd {_path}\n\n" \
                    + "\n\n".join(_lines)
            QApplication.clipboard().setText(_text)
            self._show_project_command(f"cd {_path}", _text)
            QMessageBox.information(
                self, "Copied",
                "The project's own commands are on the clipboard.")
            return

        # requirements: read the environment, not the declaration
        _env = _meta.get("env_path", "") or self._cached_env_for(_path)
        if not _env:
            QMessageBox.information(
                self, "No environment",
                f"{_meta['name']} has no environment yet, so there is nothing "
                f"installed to export.\n\nUse Sync first.")
            return

        _py = os.path.join(_env, "Scripts" if os.name == "nt" else "bin",
                           "python.exe" if os.name == "nt" else "python")
        if not os.path.isfile(_py):
            QMessageBox.warning(
                self, "Export",
                f"No interpreter found in:\n{_env}")
            return

        _dst, _ = QFileDialog.getSaveFileName(
            self, "Export requirements.txt",
            os.path.join(_path, "requirements.txt"), "Text files (*.txt)")
        if not _dst:
            return

        self._show_project_command(f'"{_py}" -m pip freeze > "{_dst}"')
        try:
            from src.utils.platform_utils import subprocess_args
            _kw = subprocess_args()
        except Exception:
            _kw = {}
        try:
            r = subprocess.run([_py, "-m", "pip", "freeze"],
                               capture_output=True, text=True, timeout=60, **_kw)
            with open(_dst, "w", encoding="utf-8") as fh:
                fh.write(r.stdout)
        except Exception as e:
            QMessageBox.warning(self, "Export failed", f"{type(e).__name__}: {e}")
            return

        try:
            from src.utils.logger import banner_command
            banner_command(f'pip freeze > "{_dst}"',
                           context=f"Export requirements ({_meta['name']})")
        except Exception:
            pass
        QMessageBox.information(self, "Exported", f"Written to:\n{_dst}")

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
