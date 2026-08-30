"""VenvStudio - New Project dialog (N55 / B26).

VenvStudio has always created ENVIRONMENTS. But poetry, hatch, pdm, pixi and uv
are project tools: they expect a pyproject.toml and a source layout, and the
environment is something they derive from it. Until now a user had to run
`poetry new` in a terminal and then point VenvStudio at the result -- which is
the wrong way round for an application whose whole purpose is to keep people
out of that terminal until they choose to be there.

pip, venv, conda and pipx are deliberately absent: none of them has a notion of
a project to create.

EVERY FLAG BELOW WAS READ OUT OF `--help` ON 2026-08-30, not remembered:

  uv init [PATH] --name X [--app|--lib] [--vcs git|none] [--no-readme]
  poetry new <path> --name X [--src|--flat]
  hatch new <NAME> [LOCATION] [--cli]
  pdm init -p <path> --name X -n [--no-git] [--backend B]
  pixi init [PATH] --format pixi|pyproject|mojoproject

Two of those are worth remembering. `pdm init` asks questions unless it is
given `-n/--non-interactive`, which would hang a GUI subprocess forever. And
`hatch new` takes the project NAME first and the location second, where every
other tool here takes a path -- so hatch gets its arguments built separately
rather than through the same code path.
"""
import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from src.utils.logger import get_logger
from src.utils.platform_utils import fit_button_width, subprocess_args

_log = get_logger("venvstudio.project")


# Tool id -> (label, the executable to look for, description shown in the form)
PROJECT_TOOLS = [
    ("uv",     "uv",     "Fast, Rust-based. Creates pyproject.toml and .python-version."),
    ("poetry", "poetry", "Mature dependency manager with its own lockfile."),
    ("hatch",  "hatch",  "Project manager from the PyPA, environments defined in pyproject.toml."),
    ("pdm",    "pdm",    "PEP 582 / PEP 621 project manager, several build backends."),
    ("pixi",   "pixi",   "Conda-based; handles non-Python dependencies too."),
]


class NewProjectDialog(QDialog):
    """Create a project with uv, poetry, hatch, pdm or pixi."""

    def __init__(self, colors_fn, config=None, parent=None):
        super().__init__(parent)
        self._c = colors_fn
        self._config = config
        self.created_path = ""      # set on success, so the caller can react

        self.setWindowTitle("New Project")
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        intro = QLabel(
            "Create a project skeleton — pyproject.toml, a source folder and "
            "the tool's own configuration. This is different from creating an "
            "environment: the tool manages the environment from the project."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_small']}px;")
        root.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(8)

        # ── Tool ──
        self._tool = QComboBox()
        for _id, _label, _desc in PROJECT_TOOLS:
            self._tool.addItem(_label, _id)
        self._tool.currentIndexChanged.connect(self._on_tool_changed)
        form.addRow("Tool:", self._tool)

        self._tool_note = QLabel("")
        self._tool_note.setWordWrap(True)
        self._tool_note.setStyleSheet(
            f"color: {self._c()['fg_muted']}; font-size: {self._c()['fs_tiny']}px;")
        form.addRow("", self._tool_note)

        # ── Name ──
        self._name = QLineEdit()
        self._name.setPlaceholderText("my-project")
        self._name.textChanged.connect(self._update_preview)
        form.addRow("Project name:", self._name)

        # ── Location ──
        _loc_row = QHBoxLayout()
        self._location = QLineEdit()
        self._location.setPlaceholderText("Where the project folder will be created")
        self._location.textChanged.connect(self._update_preview)
        _loc_row.addWidget(self._location, 1)
        _browse = QPushButton("Browse...")
        _browse.setObjectName("secondary")
        fit_button_width(_browse, 90)
        _browse.clicked.connect(self._browse)
        _loc_row.addWidget(_browse)
        _loc_widget = QWidget()
        _loc_widget.setLayout(_loc_row)
        form.addRow("Location:", _loc_widget)

        # ── Per-tool options ──
        # Only the choices that change the generated layout are offered. Every
        # tool has many more flags; putting them all here would turn a dialog
        # into a manual page, and the ones left out have sensible defaults.
        self._layout_choice = QComboBox()
        form.addRow("Layout:", self._layout_choice)

        self._git = QCheckBox("Initialize a git repository")
        self._git.setChecked(True)
        form.addRow("", self._git)

        # The location was remembered silently before. Making it a visible,
        # optional choice matters because the default is a good one: someone
        # who puts a single project on another drive should not have to
        # navigate back to Documents on every visit afterwards.
        self._remember = QCheckBox("Remember this location for next time")
        self._remember.setChecked(True)
        self._remember.setToolTip(
            "Unchecked, the dialog reopens at "
            f"{self.default_project_dir()}")
        form.addRow("", self._remember)

        root.addLayout(form)

        # ── Command preview ──
        # The command is shown before it runs, for the same reason the rest of
        # the application shows its commands: this is a tool people learn from.
        self._preview = QLabel("")
        self._preview.setWordWrap(True)
        self._preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._preview.setStyleSheet(
            f"background: {self._c()['sidebar']}; color: {self._c()['success']}; "
            f"border: 1px solid {self._c()['border']}; border-radius: 6px; "
            f"padding: 8px; font-family: Consolas, monospace; "
            f"font-size: {self._c()['fs_small']}px;")
        root.addWidget(self._preview)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        # ── Buttons ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Create Project")
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._ok_btn = buttons.button(QDialogButtonBox.Ok)

        self._restore_location()
        self._on_tool_changed()

    # ── Form behaviour ────────────────────────────────────────────────────

    @staticmethod
    def default_project_dir() -> str:
        """`Documents/vs_projects` under the user's home.

        Not the venv directory: environments and projects are different things
        and mixing them in one folder makes both harder to find. Not the bare
        home directory either -- that was the first version of this and it
        would have scattered project folders across the top of $HOME.

        Documents is the right neighbourhood on all three platforms, and it is
        where a user would look for their own work. On Windows the folder can
        be redirected (OneDrive, or a different drive), so the real location is
        read from the shell rather than assumed to be %USERPROFILE%\\Documents.
        """
        home = os.path.expanduser("~")
        docs = os.path.join(home, "Documents")

        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
                buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                if ctypes.windll.shell32.SHGetFolderPathW(
                        None, 5, None, 0, buf) == 0 and buf.value:
                    docs = buf.value
            except Exception:
                pass        # fall back to the plain join above
        elif os.path.isfile(os.path.join(home, ".config", "user-dirs.dirs")):
            # Linux: the folder is localised (Dokumente, Belgeler, ...), and
            # XDG records where it actually is.
            try:
                with open(os.path.join(home, ".config", "user-dirs.dirs"),
                          "r", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("XDG_DOCUMENTS_DIR"):
                            _val = line.split("=", 1)[1].strip().strip('"')
                            _val = _val.replace("$HOME", home)
                            if _val:
                                docs = _val
                            break
            except Exception:
                pass

        return os.path.join(docs, "vs_projects")

    def _restore_location(self):
        """Start where the user last created a project, or in the default."""
        _last = ""
        try:
            if self._config:
                _last = self._config.get("last_project_dir", "") or ""
        except Exception:
            _last = ""
        self._location.setText(_last or self.default_project_dir())

    def _on_tool_changed(self):
        _id = self._tool.currentData()
        _desc = next((d for i, _l, d in PROJECT_TOOLS if i == _id), "")
        self._tool_note.setText(_desc)

        self._layout_choice.blockSignals(True)
        self._layout_choice.clear()
        if _id == "uv":
            self._layout_choice.addItem("Application", "app")
            self._layout_choice.addItem("Library", "lib")
        elif _id == "poetry":
            self._layout_choice.addItem("src layout", "src")
            self._layout_choice.addItem("flat layout", "flat")
        elif _id == "hatch":
            self._layout_choice.addItem("Standard", "")
            self._layout_choice.addItem("With a command-line interface", "cli")
        elif _id == "pixi":
            self._layout_choice.addItem("pyproject.toml", "pyproject")
            self._layout_choice.addItem("pixi.toml", "pixi")
        else:                       # pdm
            self._layout_choice.addItem("pdm-backend", "pdm-backend")
            self._layout_choice.addItem("hatchling", "hatchling")
            self._layout_choice.addItem("setuptools", "setuptools")
            self._layout_choice.addItem("flit-core", "flit-core")
        self._layout_choice.blockSignals(False)
        self._layout_choice.currentIndexChanged.connect(self._update_preview)

        # Only uv and pdm expose a git flag; for the others the checkbox would
        # be a promise the command cannot keep.
        self._git.setEnabled(_id in ("uv", "pdm"))
        self._git.setToolTip(
            "" if _id in ("uv", "pdm")
            else f"{_id} does not offer a flag for this; it uses its own default.")
        self._update_preview()

    def _browse(self):
        _start = self._location.text().strip() or os.path.expanduser("~")
        _picked = QFileDialog.getExistingDirectory(
            self, "Where should the project folder be created?", _start)
        if _picked:
            self._location.setText(_picked)

    # ── Command construction ──────────────────────────────────────────────

    def _build_command(self):
        """Return (argv, project_path) or (None, "") when the form is incomplete."""
        _name = self._name.text().strip()
        _loc = self._location.text().strip()
        if not _name or not _loc:
            return None, ""

        _id = self._tool.currentData()
        _choice = self._layout_choice.currentData()
        _path = os.path.join(_loc, _name)
        _git = self._git.isChecked()

        if _id == "uv":
            argv = ["uv", "init", _path, "--name", _name]
            argv += ["--app"] if _choice == "app" else ["--lib"]
            argv += ["--vcs", "git" if _git else "none"]

        elif _id == "poetry":
            argv = ["poetry", "new", _path, "--name", _name]
            argv += ["--src"] if _choice == "src" else ["--flat"]

        elif _id == "hatch":
            # NAME first, LOCATION second -- the odd one out.
            argv = ["hatch", "new", _name, _path]
            if _choice == "cli":
                argv.append("--cli")

        elif _id == "pdm":
            # -n is not optional here: without it pdm asks questions and a GUI
            # subprocess has no one to answer them.
            argv = ["pdm", "init", "-p", _path, "--name", _name,
                    "-n", "--backend", _choice or "pdm-backend"]
            if not _git:
                argv.append("--no-git")

        else:                       # pixi
            argv = ["pixi", "init", _path, "--format", _choice or "pyproject"]

        return argv, _path

    def _update_preview(self):
        argv, _path = self._build_command()
        if not argv:
            self._preview.setText("Fill in a name and a location.")
            if hasattr(self, "_ok_btn"):
                self._ok_btn.setEnabled(False)
            return
        self._preview.setText(" ".join(
            f'"{a}"' if " " in a else a for a in argv))
        if hasattr(self, "_ok_btn"):
            self._ok_btn.setEnabled(True)

    # ── Creation ──────────────────────────────────────────────────────────

    def _create(self):
        argv, _path = self._build_command()
        if not argv:
            return

        if os.path.exists(_path):
            QMessageBox.warning(
                self, "Already there",
                f"This path already exists:\n{_path}\n\n"
                f"Choose another name, or another location.")
            return

        _tool = argv[0]
        _name = self._name.text().strip()
        _exe = self._resolve_tool(_tool)
        if not _exe:
            QMessageBox.warning(
                self, f"{_tool} not found",
                f"{_tool} is not installed, or is not on PATH.\n\n"
                f"Settings → Toolchain Manager can install it.")
            return
        argv[0] = _exe          # never launch by bare name

        # The default location does not exist until the first project is
        # made there; create it now rather than when the dialog opens, so
        # merely looking at this window leaves no folders behind.
        os.makedirs(os.path.dirname(_path) or ".", exist_ok=True)

        # B39-a: record it in the command history like every other action.
        #
        # This was missing: the dialog logged the command to its own logger but
        # never called banner_command, so Tools -> View Commands showed
        # environments being created and never projects. The whole point of
        # that window is that it answers "what did VenvStudio run?", and a
        # gap in it is worse than a long list.
        try:
            from src.utils.logger import banner_command
            banner_command(
                " ".join(f'"{a}"' if " " in a else a for a in argv),
                context=f"New project ({_tool})")
        except Exception:
            pass

        self._status.setText("Creating…")
        self._ok_btn.setEnabled(False)
        try:
            _log.info(f"[Project] run: {' '.join(argv)}")
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=180,
                **subprocess_args())
            _log.info(f"[Project]   -> exit={proc.returncode}")
        except subprocess.TimeoutExpired:
            self._status.setText("")
            self._ok_btn.setEnabled(True)
            QMessageBox.warning(
                self, "Timed out",
                f"{_tool} did not finish within three minutes.")
            return
        except Exception as e:
            self._status.setText("")
            self._ok_btn.setEnabled(True)
            QMessageBox.critical(self, "Failed", f"{type(e).__name__}: {e}")
            return

        if proc.returncode != 0 or not os.path.isdir(_path):
            _detail = (proc.stderr or proc.stdout or "").strip()
            _log.warning(f"[Project] failed: {_detail[:400]}")
            self._status.setText("")
            self._ok_btn.setEnabled(True)
            QMessageBox.warning(
                self, f"{_tool} could not create the project",
                _detail[:1200] or f"{_tool} exited with code {proc.returncode}.")
            return

        try:
            if self._config:
                if self._remember.isChecked():
                    self._config.set(
                        "last_project_dir", self._location.text().strip())
                else:
                    # Explicitly forget, so unchecking takes effect straight
                    # away rather than leaving an older value in place.
                    self._config.set("last_project_dir", "")
                # Recent Projects, newest first, deduplicated by path (N55).
                _recent = self._config.get("recent_projects", []) or []
                if not isinstance(_recent, list):
                    _recent = []
                _recent = [r for r in _recent
                           if isinstance(r, dict)
                           and os.path.normcase(r.get("path", ""))
                           != os.path.normcase(_path)]
                import datetime as _dt
                _recent.insert(0, {
                    "name": _name,
                    "path": _path,
                    "tool": _tool,
                    "created": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                self._config.set("recent_projects", _recent[:15])
                self._config.save()
        except Exception:
            pass

        self.created_path = _path
        _log.info(f"[Project] created {_path} with {_tool}")
        self.accept()

    @staticmethod
    def _resolve_tool(tool: str) -> str:
        """Absolute path to the tool, or "" if it cannot be found.

        Bare names have gone wrong three times in this codebase (pixi resolving
        to an unrelated system program, conda, powershell), so ask the registry
        that already knows where these live before falling back to PATH.
        """
        try:
            from src.core.tool_registry import ToolRegistry
            found = ToolRegistry.find(tool)
            if found:
                return str(found)
        except Exception:
            pass
        import shutil
        return shutil.which(tool) or shutil.which(tool + ".exe") or ""
