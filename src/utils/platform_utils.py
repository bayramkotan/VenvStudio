"""
VenvStudio - Platform-specific utilities
Cross-platform support for Windows, macOS, and Linux
"""

import logging
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple


# ── Windows console suppression ──
# Windows'ta subprocess çağrılarında konsol penceresi açılmasını engelle
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# AppImage variables that cause re-launch when inherited by subprocesses
_APPIMAGE_VARS = frozenset({
    # AppImage re-launch / identity vars
    "APPIMAGE", "APPDIR", "ARGV0", "OWD",
    "APPIMAGE_EXTRACT_AND_RUN", "APPIMAGE_STARTUP_NET_WM_PID",
    # Library path vars AppImage injects — these break PyQt5/PyQtWebEngine
    # installed inside a venv because the linker finds AppImage's .so first
    "LD_LIBRARY_PATH", "LD_PRELOAD",
    # Python path vars AppImage may set — would shadow venv's site-packages
    "PYTHONPATH", "PYTHONHOME",
    # GLib/GDK module dirs AppImage sets — can conflict with PyQt5's platform plugins
    "GDK_PIXBUF_MODULEDIR", "GDK_PIXBUF_MODULE_FILE",
    "GIO_MODULE_DIR", "GIO_EXTRA_MODULES",
    "GSETTINGS_SCHEMA_DIR",
    "XDG_DATA_DIRS",   # AppImage prepends its own share/ — can confuse Qt theme lookup
})


def appimage_clean_env() -> dict | None:
    """
    If running inside an AppImage, return a cleaned copy of os.environ
    with AppImage re-launch variables stripped out.
    Returns None if not inside an AppImage (no overhead).
    """
    if not os.environ.get("APPIMAGE"):
        return None
    return {k: v for k, v in os.environ.items() if k not in _APPIMAGE_VARS}


def subprocess_args(**kwargs):
    """
    Build kwargs for subprocess.run / subprocess.Popen:
    - Adds CREATE_NO_WINDOW on Windows to suppress console flashing.
    - On Linux inside an AppImage, strips AppImage env vars so subprocesses
      don't accidentally re-launch the AppImage instead of the intended binary.
    Use: subprocess.run(cmd, **subprocess_args(capture_output=True, text=True))
    """
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    elif sys.platform == "linux":
        clean = appimage_clean_env()
        if clean is not None:
            kwargs.setdefault("env", clean)
    return kwargs


def _project_dir_for_env(env_path, env_type: str):
    """Project directory that owns a hatch/pdm/pixi/poetry env, or None.

    N60 (Bayram, 2026-08-22). These four tools compute their environment FROM
    THE PROJECT. Running `hatch shell` from inside the env directory does not
    just fail -- hatch decides there is no project here and CREATES A NEW,
    EMPTY ENVIRONMENT. Bayram's htc env showed it plainly: the real env at
    .../virtual/htc/tWMad1mk/htc holds 237 packages and was created at 09:43,
    while .../virtual/htc/4-rJeEWq/htc holds 3 and was created at 09:44 --
    the moment he clicked Open Terminal. Every click left another one behind.

    The project directory is the one holding the `.venvstudio_env` marker, and
    the marker records the env path (`hatch_env_path`, `poetry_venv_path`...),
    so the env can be matched back to its project by scanning the base dir.
    That scan is a handful of small JSON reads over a directory the user
    already keeps their envs in.
    """
    import json as _json
    try:
        base = _get_config_path_override("venv_base_dir_enabled", "venv_base_dir") \
            or str(get_default_venv_base_dir())
        base = Path(base)
        if not base.is_dir():
            return None
        target = str(Path(env_path).resolve())
        for item in base.iterdir():
            if not item.is_dir():
                continue
            marker = item / ".venvstudio_env"
            if not marker.is_file():
                continue
            try:
                data = _json.loads(marker.read_text())
            except Exception:
                continue
            if data.get("type") != env_type:
                continue
            for key, val in data.items():
                if not key.endswith(("_env_path", "_venv_path", "_project_dir")):
                    continue
                if not val:
                    continue
                try:
                    if str(Path(val).resolve()) == target or key.endswith("_project_dir"):
                        return item if not key.endswith("_project_dir") else Path(val)
                except Exception:
                    continue
            # Same env, matched by name alone -- weaker, but better than
            # letting the tool invent a fresh environment.
            if data.get("name") and Path(env_path).parts[-2:-1] == (data["name"],):
                return item
    except Exception:
        return None
    return None



def install_qt_message_filter(logger=None):
    """Route Qt's own messages into the log, dropping the known-noisy ones.

    N93 (Bayram, 2026-09-03): this used to live inside main()'s body, so only
    `python main.py` installed it. Everything started through `vs` -- which is
    every pip installation -- ran with no handler at all.

    That single fact explains a bug chased across four attempts and three
    releases. `QFont::setPointSize: Point size <= 0 (-1)` is emitted on BOTH
    paths, by Qt, because this application styles its tables with pixel font
    sizes and Qt reports pointSize as -1 whenever a pixel size is set. It is
    cosmetic and was deliberately filtered here long ago. The source checkout
    looked clean, the installed copy did not, and the difference was never in
    the font code at all -- it was that only one of the two entry points ever
    installed the filter.

    Four separate "fixes" went into font-copying code that was working
    correctly. The lesson is in the handoff: an absent warning does not mean a
    fixed bug; it can mean a filter.
    """
    # ── Qt message handler → route to logger ──
    # Imported here, not at module scope: platform_utils is used by the
    # CLI too, which must stay Qt-free and fast.
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    from src.utils.logger import get_logger

    qt_log = logger or get_logger("venvstudio.qt")

    def _qt_message_handler(mode, context, message):
        # Suppress noisy QFont::setPointSize warnings (caused by px-based stylesheets)
        if "QFont::setPointSize" in message:
            return
        # Suppress QWindowsWindow::setGeometry positioning warnings
        if "QWindowsWindow::setGeometry" in message:
            qt_log.debug(f"Qt geometry: {message}")
            return
        # QFileSystemModel emits one of these per file every time a
        # non-native QFileDialog closes — 18 warnings for a single Export.
        # Nothing is wrong; the model is just tearing down its watcher
        # nodes. Keep them at debug so the log stays readable.
        if "No node found for item that was just removed" in message:
            return

        if mode == QtMsgType.QtDebugMsg:
            qt_log.debug(f"Qt: {message}")
        elif mode == QtMsgType.QtInfoMsg:
            qt_log.info(f"Qt: {message}")
        elif mode == QtMsgType.QtWarningMsg:
            qt_log.warning(f"Qt: {message}")
        elif mode == QtMsgType.QtCriticalMsg:
            qt_log.error(f"Qt CRITICAL: {message}")
        elif mode == QtMsgType.QtFatalMsg:
            qt_log.critical(f"Qt FATAL: {message}")

    # Install handler early — will be re-installed after QApplication
    qInstallMessageHandler(_qt_message_handler)

def setup_application_font(app, logger=None):
    """Detect the UI font, wire up emoji fallback, and apply it to `app`.

    N91 (Bayram, 2026-09-02): lifted out of main() so BOTH entry points can
    call it. `python main.py` always did this; `vs`, which comes in through
    src/main.py, never did -- and without an application font Qt keeps a
    default whose pointSize() is -1. Every table copying `table.font()` then
    inherited that, and Qt printed

        QFont::setPointSize: Point size <= 0 (-1), must be greater than 0

    on every start of the installed copy, but never from a source checkout.
    Three attempts went into blaming the font-copying code, which was fine;
    the two logs side by side settled it, one showing `UI font: ...` and the
    other showing no such line at all.
    """
    import sys
    from PySide6.QtGui import QFont
    if logger is None:
        import logging
        logger = logging.getLogger('venvstudio')

    # ── Font setup with emoji fallback ─────────────────────────────
    # Detect the best UI font (Segoe UI on Windows, Inter/Cantarell on Linux
    # if available, Helvetica on macOS) and make sure at least ONE emoji
    # font is in the fallback chain so icons like 🔄 ⭐ 📁 render.
    from PySide6.QtGui import QFontDatabase

    # QFontDatabase methods are static since Qt 6 — no instance needed.
    try:
        available_fonts = set(QFontDatabase.families())
    except Exception:
        available_fonts = set()

    # Pick the best UI font for the platform
    if sys.platform == "darwin":
        ui_font_candidates = ["SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"]
    elif sys.platform == "win32":
        ui_font_candidates = ["Segoe UI Variable Display", "Segoe UI", "Tahoma", "Arial"]
    else:  # linux / bsd
        ui_font_candidates = ["Inter", "Cantarell", "Ubuntu", "Noto Sans",
                              "DejaVu Sans", "Liberation Sans", "Arial"]

    ui_font_family = None
    for candidate in ui_font_candidates:
        if not available_fonts or candidate in available_fonts:
            ui_font_family = candidate
            break
    ui_font_family = ui_font_family or "sans-serif"

    # Detect an emoji-capable font
    emoji_font_candidates = [
        "Noto Color Emoji",      # Linux standard (Fedora/openSUSE may lack it)
        "Segoe UI Emoji",        # Windows
        "Apple Color Emoji",     # macOS
        "Twemoji Mozilla",       # Firefox / older distros
        "EmojiOne Color",        # Community
        "JoyPixels",             # Community
        "Symbola",               # Monochrome unicode fallback
        "DejaVu Sans",           # Basic unicode (last resort, no color)
    ]
    emoji_font_family = None
    for candidate in emoji_font_candidates:
        if not available_fonts or candidate in available_fonts:
            emoji_font_family = candidate
            break

    if not emoji_font_family:
        logger.warning(
            "No emoji-capable font detected. Emoji (🔄 ⭐ 📁) may render as boxes. "
            "Install 'noto-fonts-emoji' (Linux) or equivalent."
        )
        # Still set Symbola as safe fallback target
        emoji_font_family = "Symbola"

    logger.info(f"UI font: {ui_font_family}  |  Emoji font: {emoji_font_family}")

    # Qt font substitution: when the primary font is missing a glyph, Qt
    # walks the substitute chain. Register emoji font as substitute for
    # the main UI font so icons in labels/buttons fall back correctly.
    try:
        QFont.insertSubstitution(ui_font_family, emoji_font_family)
        # Also register common fallbacks so Qt can find SOMETHING for any glyph
        for fb in ("DejaVu Sans", "Noto Sans"):
            if fb != emoji_font_family and (not available_fonts or fb in available_fonts):
                QFont.insertSubstitution(ui_font_family, fb)
    except Exception as _e:
        logger.debug(f"Font substitution failed: {_e}")

    # Build application font
    font = QFont(ui_font_family, 10)
    font.setStyleHint(QFont.SansSerif)
    # Use PreferDefault → Qt applies substitutions; PreferMatch would skip them
    try:
        font.setStyleStrategy(QFont.PreferDefault)
    except Exception:
        pass
    app.setFont(font)

    # N91: main() still needs this for the Linux emoji-font prompt
    # below, so hand it back rather than making the caller rebuild it.
    return available_fonts

def terminal_icon() -> str:
    """The glyph for every "Open Terminal" control, with its trailing space.

    N75 (Bayram, 2026-08-28): there were THREE of these and all three differed
    -- main_window.py used U+1F5A5, env_list.py's context menu used the same
    codepoint plus VS16 (which asks for emoji presentation and renders
    differently again), and package_panel.py had just been changed to ">_" for
    Linux in v1.6.63. Bayram picked that last one and asked for it everywhere.

    Copying the string to the other two would have left four places to keep in
    step, so it lives here instead.

    N96 (Bayram, 2026-09-04): the same glyph on every platform now.

    It used to be U+1F5A5 on Windows and ">_" elsewhere, on the reasoning that
    Segoe UI Symbol draws the monitor as tidy monochrome. Having seen both, he
    asked for ">_" throughout, and it is the better choice for a reason beyond
    taste: ">_" is a prompt, which is what the button opens, and it reads the
    same in every font on every system. An emoji codepoint does not -- it is
    monochrome in one font, full colour in another, absent in a third, and its
    width changes with each.

    Keeping the trailing space: callers concatenate this directly with a label.
    """
    return ">_ "


def bold_font_from(widget, weight=None):
    """A bold copy of a widget's font, without Qt's unset-size warning.

    N88 (Bayram, 2026-09-02): the Qt message handler added in v1.6.66 finally
    caught the long-standing

        QFont::setPointSize: Point size <= 0 (-1), must be greater than 0

    and its stack pointed at tabs.setCurrentIndex -- meaning the bad font was
    on a widget INSIDE the tab, complained about only when Qt came to draw it.

    The cause is this pattern, used in six places:

        f = QFont(table.font()); f.setBold(True)

    When the table's size comes from a stylesheet in PIXELS -- as the toolchain
    table's does, `font-size: {fs_base}px` -- pointSize() is -1, Qt's marker
    for "unset". The copy inherits the -1 and Qt objects when it is used.

    Copying the pixel size across keeps the intent (same size as the table,
    but bold) and leaves no unset value behind.
    """
    from PySide6.QtGui import QFont
    src = widget.font()
    out = QFont(src)
    if src.pointSize() <= 0:
        _px = src.pixelSize()
        if _px > 0:
            out.setPixelSize(_px)
    if weight is not None:
        out.setWeight(weight)
    else:
        out.setBold(True)
    return out


def fit_button_width(button, minimum: int = 0, padding: int = 10):
    """Widen a button when its label needs more room than `minimum`.

    N74 (Bayram, 2026-08-28): setFixedWidth pins a button to a number chosen
    while looking at one machine. Those numbers were picked on Windows with
    Segoe UI; on his CachyOS box Cantarell is wider and the same buttons read
    "Detec", "Rese", "Browse..", "Open Termi". There are 38 setFixedWidth calls
    in the GUI, so raising each number by hand only moves the problem to the
    next font, the next translation, or the next label edit.

    Qt already knows how wide the text is. Treat the old number as a FLOOR --
    it keeps rows of buttons visually even, which is why the fixed widths were
    there -- and let sizeHint win whenever the text genuinely needs more.
    """
    try:
        needed = button.sizeHint().width() + padding
        button.setMinimumWidth(max(int(minimum), int(needed)))
    except Exception:
        if minimum:
            try:
                button.setMinimumWidth(int(minimum))
            except Exception:
                pass
    return button


def get_platform() -> str:
    """Return normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system  # 'windows' or 'linux'


def get_default_venv_base_dir() -> Path:
    """Return the default base directory for virtual environments."""
    system = get_platform()
    if system == "windows":
        return Path("C:/venv")
    elif system == "macos":
        return Path.home() / "venv"
    else:  # linux
        return Path.home() / "venv"


def get_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    system = get_platform()
    if system == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config_dir = base / "VenvStudio"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_python_executable(venv_path: Path) -> Path:
    """Return the python executable path inside a venv."""
    import sys as _sys, json as _json
    marker = venv_path / ".venvstudio_env"
    if marker.exists():
        try:
            with open(marker, encoding="utf-8") as _f:
                _data = _json.load(_f)
            _type = _data.get("type", "")
            if _type == "pipx":
                _py = _data.get("python_path", "")
                if _py and Path(_py).exists():
                    return Path(_py)
                return Path(_sys.executable)
            if _type == "poetry":
                _pvenv = _data.get("poetry_venv_path", "")
                if _pvenv and Path(_pvenv).exists():
                    _scripts = "Scripts" if get_platform() == "windows" else "bin"
                    _exe = "python.exe" if get_platform() == "windows" else "python"
                    return Path(_pvenv) / _scripts / _exe
            if _type == "pixi":
                # Pixi stores the python inside its own cache, not under venv_path.
                # Ask pixi where it put python for this project directory.
                # Cache result in marker to avoid repeated subprocess calls.
                _py_cached = _data.get("python_path", "")
                if _py_cached and Path(_py_cached).exists():
                    return Path(_py_cached)
                try:
                    import subprocess as _sp
                    _pixi_bin = __import__("shutil").which("pixi") or \
                        str(Path.home() / ".pixi" / "bin" / "pixi")
                    _r = _sp.run(
                        [_pixi_bin, "run", "which", "python"]
                        if get_platform() != "windows" else
                        [_pixi_bin, "run", "where", "python"],
                        cwd=str(venv_path),
                        capture_output=True, text=True, timeout=10
                    )
                    _found = (_r.stdout or "").strip().splitlines()
                    for _line in _found:
                        _line = _line.strip()
                        if _line and Path(_line).exists():
                            # Cache in marker so next call is instant
                            try:
                                _data["python_path"] = _line
                                with open(marker, "w", encoding="utf-8") as _wf:
                                    _json.dump(_data, _wf, indent=2)
                            except Exception:
                                pass
                            return Path(_line)
                except Exception:
                    pass
                # Fallback: system python
                return Path(_sys.executable)
        except Exception:
            pass
    if get_platform() == "windows":
        # conda envs put python.exe at the ROOT, not under Scripts\\.
        # Probing Scripts\\python.exe (which doesn't exist) caused
        # "[WinError 2] cannot find the file specified" when installing
        # pip apps (e.g. Gradio) into a conda env.
        _root_py = venv_path / "python.exe"
        _scripts_py = venv_path / "Scripts" / "python.exe"
        if _root_py.exists() and not _scripts_py.exists():
            return _root_py
        return _scripts_py
    return venv_path / "bin" / "python"


def get_pip_executable(venv_path: Path) -> Path:
    """Return the pip executable path inside a venv."""
    import sys as _sys, json as _json
    marker = venv_path / ".venvstudio_env"
    if marker.exists():
        try:
            with open(marker, encoding="utf-8") as _f:
                _data = _json.load(_f)
            _type = _data.get("type", "")
            if _type == "pipx":
                _py = _data.get("python_path", "") or _sys.executable
                _py_path = Path(_py)
                if get_platform() == "windows":
                    _pip = _py_path.parent / "Scripts" / "pip.exe"
                else:
                    _pip = _py_path.parent / "pip"
                if _pip.exists():
                    return _pip
                return _py_path.parent / ("Scripts/pip.exe" if get_platform() == "windows" else "pip")
            if _type == "poetry":
                _pvenv = _data.get("poetry_venv_path", "")
                if _pvenv and Path(_pvenv).exists():
                    _scripts = "Scripts" if get_platform() == "windows" else "bin"
                    _exe = "pip.exe" if get_platform() == "windows" else "pip"
                    return Path(_pvenv) / _scripts / _exe
        except Exception:
            pass
    if get_platform() == "windows":
        # conda: pip.exe (if present) sits in Scripts\\, but python is at root.
        _scripts_pip = venv_path / "Scripts" / "pip.exe"
        if _scripts_pip.exists():
            return _scripts_pip
        return _scripts_pip  # caller uses python -m pip when missing
    return venv_path / "bin" / "pip"

def get_pipx_executable() -> Optional[str]:
    """Find pipx executable — prefer direct binary, fallback sys.executable -m pipx."""
    import shutil, sys, os
    is_win = get_platform() == "windows"
    # 1. Direct binary in PATH
    found = shutil.which("pipx")
    if found:
        return found
    # 2. User local bin (~/.local/bin/pipx or %USERPROFILE%\.local\bin\pipx.exe)
    _bin_name = "pipx.exe" if is_win else "pipx"
    user_local = os.path.join(os.path.expanduser("~"), ".local", "bin", _bin_name)
    if os.path.isfile(user_local):
        return user_local
    # 3. AppData\Roaming\Python scripts (Windows pip install --user pipx)
    if is_win:
        appdata = os.environ.get("APPDATA", "")
        for py_ver in ("Python313", "Python312", "Python311", "Python314", "Python310"):
            candidate = os.path.join(appdata, "Python", py_ver, "Scripts", "pipx.exe")
            if os.path.isfile(candidate):
                return candidate
    # 4. Python Scripts dir next to sys.executable
    scripts = os.path.join(os.path.dirname(sys.executable),
                           "Scripts" if is_win else "bin",
                           "pipx.exe" if is_win else "pipx")
    if os.path.isfile(scripts):
        return scripts
    # 5. Check if pipx is available as a module (python3 -m pipx)
    try:
        import subprocess
        r = subprocess.run([sys.executable, "-m", "pipx", "--version"],
                           **subprocess_args(capture_output=True, text=True, timeout=5))
        if r.returncode == 0:
            return sys.executable  # caller should use [exe, "-m", "pipx", ...]
    except Exception:
        pass
    return None


def get_pipx_cmd() -> list:
    """Return the command list to invoke pipx.
    Returns ['pipx'] if binary found, or [sys.executable, '-m', 'pipx'] as fallback.
    """
    import sys as _sys
    exe = get_pipx_executable()
    if exe is None:
        return []
    # If exe == sys.executable, pipx is only available as a module
    import os as _os
    if _os.path.normpath(exe) == _os.path.normpath(_sys.executable):
        return [exe, "-m", "pipx"]
    return [exe]


def get_configured_terminal() -> str:
    """The terminal the user chose in Settings, or "" if they chose none.

    B62 (Bayram, 2026-09-05: "Open terminal'i standard bir hale getirelim!
    Bir tip terminal tipi acilsin sadece ve settings altinda var!!!!").

    The setting existed and open_terminal_at accepted it -- as a PARAMETER,
    which meant every caller had to remember to pass it, and three of the five
    did not:

        env_list.py:969        passes it
        package_panel.py:854   passes it
        window_menu.py:209     does NOT
        window_menu.py:843     does NOT
        projects_page.py:1841  does NOT

    So the same user got their chosen terminal from the Environments and
    Packages pages and whatever auto-detection found first from the menu and
    the Projects page -- which is exactly the inconsistency he reported. A
    default that each caller must opt into is not a default. Reading it here
    means a caller can still override it deliberately, but cannot forget it
    by accident, and a sixth caller inherits the behaviour for free.

    Same lazy import as _get_config_path_override above, for the same reason:
    platform_utils is imported very early in startup.
    """
    try:
        from src.core.config_manager import ConfigManager as _CM
        return _CM().get("terminal_type", "") or ""
    except Exception:
        return ""


def _get_config_path_override(key_enabled: str, key_path: str) -> Optional[str]:
    """Return a user-configured path override from VenvStudio config, or None.

    Reads config only when the matching ``key_enabled`` flag is True and the
    stored path is non-empty. Importing config_manager here (inside the
    function) avoids a circular import because platform_utils is imported very
    early in the startup sequence.
    """
    try:
        from src.core.config_manager import ConfigManager as _CM
        _cfg = _CM()
        if _cfg.get(key_enabled, False) and _cfg.get(key_path, ""):
            _p = _cfg.get(key_path, "")
            if _p:
                return _p
    except Exception:
        pass
    return None


# The Settings → Package Manager Custom Paths rows used to hard-code POSIX
# strings ("~/.cache/pypoetry/virtualenvs (platform default)") as their
# placeholders, so a Windows user was told to look in a directory that does
# not exist on Windows -- while the code below already knew the right answer.
# These three helpers exist so the UI can show the real default WITHOUT
# consulting the user's override, which is what a "(platform default)" hint
# has to mean. (Bayram, 2026-08-19.)
def get_default_poetry_venvs_path() -> str:
    """Poetry's own default virtualenvs directory for this platform."""
    import sys as _sys, os as _os
    if _sys.platform == "win32":
        return str(
            Path(_os.environ.get("LOCALAPPDATA", _os.environ.get("APPDATA", "")))
            / "pypoetry" / "Cache" / "virtualenvs"
        )
    elif _sys.platform == "darwin":
        return str(Path.home() / "Library" / "Caches" / "pypoetry" / "virtualenvs")
    return str(Path.home() / ".cache" / "pypoetry" / "virtualenvs")


def get_default_pipx_home() -> str:
    """pipx's own default home directory for this platform."""
    import sys as _sys, os as _os
    if _sys.platform == "win32":
        return str(Path(_os.environ.get("LOCALAPPDATA",
                                        _os.environ.get("APPDATA", ""))) / "pipx")
    elif _sys.platform == "darwin":
        return str(Path.home() / ".local" / "pipx")
    return str(Path.home() / ".local" / "share" / "pipx")


def get_default_conda_envs_dir() -> str:
    """micromamba's own default envs directory for this platform."""
    import sys as _sys, os as _os
    if _sys.platform == "win32":
        return str(Path(_os.environ.get("APPDATA", "")) / "mamba" / "envs")
    return str(Path.home() / ".local" / "share" / "mamba" / "envs")


def get_poetry_venvs_path() -> Optional[str]:
    """Return the poetry virtualenvs directory.

    Returns the user-configured override (Settings → Paths → Poetry virtualenvs)
    when enabled, otherwise falls back to the platform default that poetry uses.
    """
    override = _get_config_path_override(
        "poetry_venvs_path_enabled", "poetry_venvs_path"
    )
    if override:
        return override
    return get_default_poetry_venvs_path()


def get_conda_envs_dir() -> Optional[str]:
    """Return the conda/micromamba envs directory override, or None (use default)."""
    return _get_config_path_override("conda_envs_dir_enabled", "conda_envs_dir")


def get_pipx_home() -> Optional[str]:
    """Find pipx home directory (where venvs are stored)."""
    import subprocess, os, sys
    # 0. VenvStudio config override (Settings → Paths → Pipx home)
    _override = _get_config_path_override("pipx_home_enabled", "pipx_home")
    if _override:
        return _override
    # 1. Env var override
    env_home = os.environ.get("PIPX_HOME")
    if env_home and os.path.isdir(env_home):
        return env_home
    pipx_exe = get_pipx_executable()
    if pipx_exe:
        try:
            r = subprocess.run(
                [pipx_exe, "environment", "--value", "PIPX_HOME"],
                **subprocess_args(capture_output=True, text=True, timeout=10)
            )
            if r.returncode == 0 and r.stdout.strip():
                p = os.path.expanduser(r.stdout.strip())
                if os.path.isdir(p):
                    return p
        except Exception:
            pass
    # 2. Default locations
    home = os.path.expanduser("~")
    for candidate in [
        os.path.join(home, "pipx"),
        os.path.join(home, ".local", "pipx"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "pipx"),
        os.path.join(os.environ.get("APPDATA", ""), "pipx"),
    ]:
        if os.path.isdir(os.path.join(candidate, "venvs")):
            return candidate
    return None


def list_pipx_apps(pipx_home) -> list:
    """List (app_name, venv_path) for pipx-installed apps under
    pipx_home/venvs/*. A pipx home is a container of many independently
    activatable venvs, not one env itself, so terminal activation needs to
    know WHICH app's venv to enter -- this is how the caller finds out
    what's available. Only entries with a real activate script are kept."""
    import os
    apps = []
    try:
        venvs_dir = os.path.join(str(pipx_home), "venvs")
        if not os.path.isdir(venvs_dir):
            return apps
        _win = get_platform() == "windows"
        for name in sorted(os.listdir(venvs_dir)):
            venv_path = os.path.join(venvs_dir, name)
            activate = os.path.join(
                venv_path, "Scripts" if _win else "bin",
                "activate.bat" if _win else "activate")
            if os.path.isfile(activate):
                apps.append((name, venv_path))
    except Exception:
        pass
    return apps


def get_activate_command(venv_path: Path) -> str:
    """Return the activation command for a venv (for display purposes)."""
    system = get_platform()
    if system == "windows":
        return str(venv_path / "Scripts" / "activate.bat")
    return f"source {venv_path / 'bin' / 'activate'}"


_PY_VER_CACHE = None


def _python_version_stamp(exe_path) -> str:
    """Size and mtime -- enough to notice an upgraded interpreter."""
    try:
        st = os.stat(exe_path)
        return f"{int(st.st_mtime)}:{st.st_size}"
    except OSError:
        return ""


def _python_version_from_cache(exe_path) -> str:
    """A previously recorded version for this exact executable, or ""."""
    global _PY_VER_CACHE
    if _PY_VER_CACHE is None:
        try:
            import json
            from pathlib import Path as _P
            with open(_P(get_config_dir()) / "python_versions.json",
                      "r", encoding="utf-8") as fh:
                _PY_VER_CACHE = json.load(fh)
            if not isinstance(_PY_VER_CACHE, dict):
                _PY_VER_CACHE = {}
        except Exception:
            _PY_VER_CACHE = {}

    _stamp = _python_version_stamp(exe_path)
    if not _stamp:
        return ""
    hit = _PY_VER_CACHE.get(os.path.normcase(os.path.abspath(exe_path)))
    if isinstance(hit, dict) and hit.get("stamp") == _stamp:
        return hit.get("version", "")
    return ""


def _python_version_to_cache(exe_path, version: str) -> None:
    """Record it. Best-effort: a failure costs one subprocess, nothing more."""
    global _PY_VER_CACHE
    _stamp = _python_version_stamp(exe_path)
    if not _stamp or not version:
        return
    if _PY_VER_CACHE is None:
        _PY_VER_CACHE = {}
    _PY_VER_CACHE[os.path.normcase(os.path.abspath(exe_path))] = {
        "stamp": _stamp, "version": version}
    try:
        import json
        from pathlib import Path as _P
        fp = _P(get_config_dir()) / "python_versions.json"
        fp.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(fp) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_PY_VER_CACHE, fh, indent=1)
        os.replace(tmp, fp)
    except Exception:
        pass


def find_system_pythons() -> List[Tuple[str, str]]:
    """
    Find available Python installations on the system.
    Returns list of (version_string, executable_path) tuples.
    Searches PATH, Windows Registry, and known install directories.
    No version range limit — future-proof.
    """
    pythons = []
    seen_paths = set()

    # EXE/AppImage path — subprocess çağrısında bunlar tekrar başlatılmamalı
    _self_exe = os.path.normcase(os.path.normpath(sys.executable))

    def _try_add(exe_path: str):
        if not exe_path or not os.path.isfile(exe_path):
            return
        normalized = os.path.normcase(os.path.normpath(exe_path))
        if "windowsapps" in normalized:
            return
        # Kendimizi (EXE/AppImage) listeye ekleme
        if normalized == _self_exe:
            return
        if normalized in seen_paths:
            return
        seen_paths.add(normalized)

        # N87 (Bayram, 2026-09-01): ask each interpreter once, ever.
        #
        # This ran `<python> --version` for every Python on the machine every
        # time the list was wanted, and each one flashed up a console window
        # on his box. Deferring the scan in v1.6.69 moved the flashing rather
        # than removing it.
        #
        # A version only changes when the executable does, so the answer is
        # kept against the file's size and mtime. An upgraded or rebuilt
        # interpreter has a different mtime and is asked again.
        _cached = _python_version_from_cache(exe_path)
        if _cached:
            if _cached[0].isdigit():
                pythons.append((_cached, exe_path))
            return

        try:
            result = subprocess.run(
                [exe_path, "--version"],
                **subprocess_args(capture_output=True, text=True, timeout=5)
            )
            version = (result.stdout.strip() or result.stderr.strip()).replace("Python ", "")
            if version and version[0].isdigit():
                pythons.append((version, exe_path))
                _python_version_to_cache(exe_path, version)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    # 1) PATH'deki python / python3 komutları
    # NOT: Windows EXE (PyInstaller frozen) içinde shutil.which("python") EXE'nin
    # kendisini döndürebilir — bu durumda PATH aramasını atla
    if not (os.name == "nt" and getattr(sys, "frozen", False)):
        for candidate in ["python", "python3"]:
            exe = shutil.which(candidate)
            if exe:
                _try_add(exe)

    # 2) Windows: Registry + bilinen kurulum dizinleri
    if os.name == "nt":
        try:
            import winreg
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                for reg_path in [
                    r"SOFTWARE\Python\PythonCore",
                    r"SOFTWARE\WOW6432Node\Python\PythonCore",
                ]:
                    try:
                        with winreg.OpenKey(hive, reg_path) as key:
                            i = 0
                            while True:
                                try:
                                    ver = winreg.EnumKey(key, i)
                                    i += 1
                                    with winreg.OpenKey(key, ver + r"\InstallPath") as ip:
                                        install_dir = winreg.QueryValue(ip, None)
                                        exe = os.path.join(install_dir.rstrip("\\"), "python.exe")
                                        _try_add(exe)
                                except OSError:
                                    break
                    except OSError:
                        continue
        except ImportError:
            pass

        # Bilinen Windows kurulum dizinleri
        search_roots = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
            os.path.expanduser("~"),
        ]
        for root in search_roots:
            if not root or not os.path.isdir(root):
                continue
            try:
                for entry in os.scandir(root):
                    if entry.is_dir() and entry.name.lower().startswith("python"):
                        exe = os.path.join(entry.path, "python.exe")
                        _try_add(exe)
            except PermissionError:
                continue

    # 3) Linux/macOS: /usr/bin, /usr/local/bin, pyenv, .local/bin
    else:
        search_dirs = [
            "/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/.pyenv/shims"),
        ]
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for entry in os.scandir(d):
                    if entry.name.startswith("python") and entry.is_file():
                        _try_add(entry.path)
            except PermissionError:
                continue

    def _ver_key(v):
        try:
            return tuple(int(x) for x in v[0].split("."))
        except Exception:
            return (0,)
    pythons.sort(key=_ver_key, reverse=True)
    return pythons
def open_terminal_at(path: Path, terminal_type: str = "",
                     env_type: str = "venv", run_after: str = "") -> bool:
    """Open a terminal/console at the given path.
    
    env_type:
      "venv"         → activate the Python venv (Scripts/activate.bat etc.)
      "conda"        → micromamba activate <path>
      "system_tools" → just cd into the folder, no activation
    """
    # Callers hand us whatever they have -- a Path, a str from a config file,
    # a str read out of a marker. Everything below composes paths with `/`, so
    # a str argument blew up with
    #     TypeError: unsupported operand type(s) for /: 'str' and 'str'
    # and, because the whole body sits in a try/except that only LOGS, the
    # window silently did nothing while the status bar cheerfully reported
    # "Running 'poetry show'..." (Bayram, 2026-08-22). Normalise once, here.
    path = Path(path)
    # B62: no terminal named by the caller means "use the one the user chose",
    # not "guess". Only an explicit argument overrides the setting.
    if not terminal_type:
        terminal_type = get_configured_terminal()
    system = get_platform()

    # ── Build activation command based on env_type ────────────────────────
    def _make_cmd_windows(path: Path, terminal_type: str) -> str:
        if env_type in ("system_tools", "pipx"):
            # No activate script — just open shell at the folder
            if terminal_type == "wt" and shutil.which("wt"):
                return f'start wt -d "{path}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                return f'start "" "{git_bash}" --login -c "cd \'{path}\' && exec bash"'
            else:
                return f'start cmd /k "cd /d {path}"'

        elif env_type == "conda":
            from src.core.micromamba_installer import get_micromamba_exe
            mamba = get_micromamba_exe()
            mamba_str = str(mamba) if mamba else "micromamba"
            # MAMBA_ROOT_PREFIX — use parent of the mamba executable or user home
            import os as _os
            mamba_root = _os.environ.get("MAMBA_ROOT_PREFIX", "")
            if not mamba_root and mamba:
                mamba_root = str(Path(mamba).parent.parent)
                if not mamba_root or mamba_root == ".":
                    mamba_root = str(Path.home() / "micromamba")
            if not mamba_root:
                mamba_root = str(Path.home() / "micromamba")

            # Find the mamba_hook.bat (installed by 'micromamba shell init --shell cmd.exe')
            # Default locations on Windows
            def _find_mamba_hook_bat() -> Optional[str]:
                candidates = [
                    Path(_os.environ.get("APPDATA", "")) / "mamba" / "condabin" / "mamba_hook.bat",
                    Path(_os.environ.get("LOCALAPPDATA", "")) / "mamba" / "condabin" / "mamba_hook.bat",
                    Path(mamba_root) / "condabin" / "mamba_hook.bat",
                    Path.home() / ".local" / "share" / "mamba" / "condabin" / "mamba_hook.bat",
                ]
                for c in candidates:
                    if c.exists():
                        return str(c)
                return None

            # Find Activate.ps1 for PowerShell hook (also installed by 'shell init')
            def _find_mamba_hook_ps1() -> Optional[str]:
                candidates = [
                    Path(_os.environ.get("APPDATA", "")) / "mamba" / "condabin" / "Conda.psm1",
                    Path(mamba_root) / "condabin" / "Conda.psm1",
                ]
                for c in candidates:
                    if c.exists():
                        return str(c.parent)  # parent dir of the module
                return None

            mamba_hook_bat = _find_mamba_hook_bat()

            # Ensure shell init has been run — if hook files missing, run init once
            if not mamba_hook_bat:
                try:
                    subprocess.run(
                        [mamba_str, "shell", "init", "--shell", "cmd.exe",
                         "--root-prefix", mamba_root],
                        **subprocess_args(capture_output=True, text=True, timeout=30),
                    )
                    mamba_hook_bat = _find_mamba_hook_bat()
                except Exception:
                    pass
                try:
                    subprocess.run(
                        [mamba_str, "shell", "init", "--shell", "powershell",
                         "--root-prefix", mamba_root],
                        **subprocess_args(capture_output=True, text=True, timeout=30),
                    )
                except Exception:
                    pass

            # cmd.exe activation: set MAMBA_ROOT_PREFIX, CALL mamba_hook.bat, activate
            if mamba_hook_bat:
                cmd_activate = (
                    f'set "MAMBA_ROOT_PREFIX={mamba_root}" '
                    f'&& CALL "{mamba_hook_bat}" '
                    f'&& micromamba activate "{path}"'
                )
            else:
                # Fallback: run shell directly inside the env (no activation prompt, but paths work)
                cmd_activate = f'"{mamba_str}" run -p "{path}" cmd /k'

            # PowerShell activation: the init creates a profile hook; we just need to activate.
            # Try loading Conda.psm1 if present, otherwise fall back to shell hook pipe.
            ps_activate = (
                f'$env:MAMBA_ROOT_PREFIX=\'{mamba_root}\'; '
                f'try {{ (& \'{mamba_str}\' shell hook -s powershell) | Out-String | Invoke-Expression }} '
                f'catch {{ Write-Host \'Hook failed, trying direct run...\'; & \'{mamba_str}\' run -p \'{path}\' powershell -NoExit; exit }}; '
                f'micromamba activate \'{path}\''
            )

            if terminal_type == "wt" and shutil.which("wt"):
                # Windows Terminal with cmd (uses mamba_hook.bat which is most reliable)
                if mamba_hook_bat:
                    return f'start wt -d "{path}" cmd /k "{cmd_activate}"'
                return f'start wt -d "{path}" powershell -NoExit -Command "{ps_activate}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                # Git-Bash: use bash-style hook
                bash_activate = (
                    f"export MAMBA_ROOT_PREFIX='{mamba_root}'; "
                    f"eval \"$('{mamba_str}' shell hook -s bash)\"; "
                    f"micromamba activate '{path}'"
                )
                return (f'start "" "{git_bash}" --login -c '
                        f'"cd \'{path}\' && {bash_activate} && exec bash"')
            elif terminal_type == "pwsh":
                # PowerShell 7+ — same activation hook as Windows PowerShell,
                # just launched through pwsh instead of powershell.
                return (f'start pwsh -NoExit -Command '
                        f'"Set-Location \'{path}\'; {ps_activate}"')
            elif terminal_type == "powershell":
                return (f'start powershell -NoExit -Command '
                        f'"Set-Location \'{path}\'; {ps_activate}"')
            else:
                # Default: cmd.exe via mamba_hook.bat (most reliable on Windows)
                return f'start cmd /k "cd /d {path} && {cmd_activate}"'

        elif env_type in ("hatch", "pdm", "pixi"):
            # Hatch/PDM/Pixi: cd into project dir and run the tool's shell command.
            # `hatch shell`/`pixi shell`/`pdm run cmd` all drop into an
            # INTERACTIVE nested shell that blocks until the user exits
            # it -- a run_after chained with && would silently wait
            # there and never execute (Bayram, 2026-08-14 caught this
            # via the "Run Command" context menu). When run_after is
            # set, use each tool's "run one command and return" mode
            # instead of its "enter a shell" mode.
            import shutil as _sh2, os as _os2
            # Run from the PROJECT, not the env dir -- otherwise these
            # tools decide there is no project and make a new env.
            _pdir = _project_dir_for_env(path, env_type) or path
            if env_type == "hatch":
                _tool = _sh2.which("hatch") or "hatch"
                _shell_cmd = f'"{_tool}" run {run_after}' if run_after else f'"{_tool}" shell'
            elif env_type == "pixi":
                _pixi_cands = [
                    _os2.path.join(_os2.environ.get("USERPROFILE", ""), ".pixi", "bin", "pixi.exe"),
                    _os2.path.join(_os2.environ.get("LOCALAPPDATA", ""), ".pixi", "bin", "pixi.exe"),
                ]
                _tool = next((c for c in _pixi_cands if _os2.path.isfile(c)), None) \
                        or _sh2.which("pixi") or "pixi"
                _shell_cmd = f'"{_tool}" run {run_after}' if run_after else f'"{_tool}" shell'
            else:  # pdm
                _tool = _sh2.which("pdm") or "pdm"
                _shell_cmd = f'"{_tool}" run {run_after}' if run_after else f'"{_tool}" run cmd'

            if terminal_type == "wt" and shutil.which("wt"):
                return f'start wt -d "{_pdir}" cmd /k "{_shell_cmd}"'
            elif terminal_type == "pwsh":
                return f'start pwsh -NoExit -Command "Set-Location \'{_pdir}\'; {_shell_cmd}"'
            elif terminal_type == "powershell":
                return f'start powershell -NoExit -Command "Set-Location \'{_pdir}\'; {_shell_cmd}"'
            elif terminal_type == "git-bash" and shutil.which("bash"):
                git_bash = shutil.which("bash")
                return f'start "" "{git_bash}" --login -c "cd \'{_pdir}\' && {_shell_cmd} && exec bash"'
            else:
                return f'start cmd /k "cd /d {_pdir} && {_shell_cmd}"'

        elif env_type == "poetry":
            # Same self-heal as POSIX: the marker may lack poetry_venv_path
            # for envs created before that key existed, or if Poetry has
            # since recreated the venv. Fall back to asking Poetry directly.
            import json as _j
            _marker = path / ".venvstudio_env"
            _poetry_venv = ""
            _proj_dir = ""
            if _marker.exists():
                try:
                    _mdata = _j.loads(_marker.read_text())
                    _poetry_venv = _mdata.get("poetry_venv_path", "")
                    _proj_dir = _mdata.get("poetry_project_dir", "") or str(path)
                except Exception:
                    pass
            else:
                _proj_dir = str(path)
            if (not _poetry_venv or not Path(_poetry_venv).exists()) and _proj_dir:
                try:
                    _poetry_exe = shutil.which("poetry") or shutil.which("poetry.exe")
                    if _poetry_exe and Path(_proj_dir).is_dir():
                        _r = subprocess.run(
                            [_poetry_exe, "env", "info", "--path"],
                            cwd=_proj_dir, **subprocess_args(
                                capture_output=True, text=True, timeout=10))
                        _cand = _r.stdout.strip().splitlines()[-1].strip() if _r.stdout.strip() else ""
                        if _cand and Path(_cand).exists():
                            _poetry_venv = _cand
                except Exception:
                    pass
            _pv = Path(_poetry_venv) if _poetry_venv and Path(_poetry_venv).exists() else path
            activate_bat = _pv / "Scripts" / "activate.bat"
            activate_ps1 = _pv / "Scripts" / "Activate.ps1"
            # N59: activate the venv (_pv) but SIT IN the project (_cd) -- see
            # the POSIX branch below for why. Poetry's commands read
            # pyproject.toml from the working directory.
            _cd = Path(_proj_dir) if _proj_dir and Path(_proj_dir).is_dir() else _pv
            if terminal_type == "pwsh" and activate_ps1.exists():
                return (f'start pwsh -NoExit -Command '
                        f'"Set-Location \'{_cd}\'; & \'{activate_ps1}\'"')
            if terminal_type == "wt" and shutil.which("wt") and activate_ps1.exists():
                return f'start wt -d "{_cd}" powershell -NoExit -Command "& \'{activate_ps1}\'"'
            if activate_bat.exists():
                return f'start cmd /k "cd /d {_cd} && {activate_bat}"'
            return f'start cmd /k "cd /d {_cd}"'
        else:  # venv
            activate_bat = path / "Scripts" / "activate.bat"
            activate_ps1 = path / "Scripts" / "Activate.ps1"
            if terminal_type == "cmd":
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            elif terminal_type == "pwsh":
                # PowerShell 7+ via pwsh.exe; activate through Activate.ps1
                if activate_ps1.exists():
                    return (f'start pwsh -NoExit -Command '
                            f'"Set-Location \'{path}\'; & \'{activate_ps1}\'"')
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            elif terminal_type == "wt":
                if activate_ps1.exists():
                    return (f'start wt -d "{path}" powershell -NoExit -Command '
                            f'"& \'{activate_ps1}\'"')
                return f'start wt -d "{path}" cmd /k "{activate_bat}"'
            elif terminal_type == "git-bash":
                git_bash = shutil.which("bash")
                if git_bash:
                    activate_sh = path / "Scripts" / "activate"
                    return f'start "" "{git_bash}" --login -c "cd \'{path}\' && source \'{activate_sh}\' && exec bash"'
                return f'start cmd /k "cd /d {path} && {activate_bat}"'
            else:
                if shutil.which("wt"):
                    if activate_ps1.exists():
                        return (f'start wt -d "{path}" powershell -NoExit -Command '
                                f'"& \'{activate_ps1}\'"')
                    return f'start wt -d "{path}" cmd /k "{activate_bat}"'
                elif activate_ps1.exists():
                    return (f'start powershell -NoExit -Command "'
                            f'Set-Location \'{path}\'; '
                            f'& \'{activate_ps1}\'"')
                return f'start cmd /k "cd /d {path} && {activate_bat}"'

    def _make_cmd_posix(path: Path) -> str:
        if env_type in ("system_tools", "pipx"):
            return f"cd '{path}'"
        elif env_type in ("hatch", "pdm", "pixi"):
            # Same "shell blocks, run_after would never fire" issue as
            # the Windows branch above -- use each tool's "run one
            # command and return" mode when run_after is set.
            import shutil as _sh3, os as _os3
            # Run these from the PROJECT, never from the env directory -- see
            # _project_dir_for_env for what happens otherwise.
            _pdir = _project_dir_for_env(path, env_type) or path
            if env_type == "hatch":
                _tool = _sh3.which("hatch") or "hatch"
                if run_after:
                    return f"cd '{_pdir}' && '{_tool}' run {run_after}"
                # N63 (Bayram, 2026-08-22): activate directly instead of
                # `hatch shell`. Hatch's shell command spawns a NESTED bash and
                # sources the env's activate script from inside it, so the user
                # sees the source line echoed twice and then needs two exits to
                # get out. A hatch environment is an ordinary virtualenv and we
                # already know exactly where it is (`path`), so source it once
                # and stay in the same shell -- same result, none of the noise.
                _hact = Path(path) / "bin" / "activate"
                if _hact.is_file():
                    return f"cd '{_pdir}' && source '{_hact}'"
                return f"cd '{_pdir}' && '{_tool}' shell"
            elif env_type == "pixi":
                _pixi = _os3.path.expanduser("~/.pixi/bin/pixi")
                if not _os3.path.isfile(_pixi):
                    _pixi = _sh3.which("pixi") or "pixi"
                if run_after:
                    return f"cd '{_pdir}' && '{_pixi}' run {run_after}"
                return f"cd '{_pdir}' && '{_pixi}' shell"
            else:  # pdm
                _tool = _sh3.which("pdm") or "pdm"
                if run_after:
                    return f"cd '{_pdir}' && '{_tool}' run {run_after}"
                return f"cd '{_pdir}' && '{_tool}' run bash"
        elif env_type == "poetry":
            # Poetry venv is in ~/.cache/pypoetry/virtualenvs/
            import json as _j
            _marker = path / ".venvstudio_env"
            _poetry_venv = ""
            _proj_dir = ""
            if _marker.exists():
                try:
                    _mdata = _j.loads(_marker.read_text())
                    _poetry_venv = _mdata.get("poetry_venv_path", "")
                    _proj_dir = _mdata.get("poetry_project_dir", "") or str(path)
                except Exception:
                    pass
            else:
                _proj_dir = str(path)
            # Self-heal: envs created before poetry_venv_path was added to
            # the marker (or a venv poetry has since recreated) have no
            # usable stored path. Ask Poetry itself, from the project dir.
            if (not _poetry_venv or not Path(_poetry_venv).exists()) and _proj_dir:
                try:
                    _poetry_exe = shutil.which("poetry")
                    if _poetry_exe and Path(_proj_dir).is_dir():
                        _r = subprocess.run(
                            [_poetry_exe, "env", "info", "--path"],
                            cwd=_proj_dir, **subprocess_args(
                                capture_output=True, text=True, timeout=10))
                        _cand = _r.stdout.strip().splitlines()[-1].strip() if _r.stdout.strip() else ""
                        if _cand and Path(_cand).exists():
                            _poetry_venv = _cand
                except Exception:
                    pass
            if _poetry_venv and Path(_poetry_venv).exists():
                _pa = Path(_poetry_venv) / "bin" / "activate"
                # N59 (Bayram, 2026-08-22): land in the PROJECT, not the venv.
                # This used to cd into _poetry_venv, i.e.
                # ~/.cache/pypoetry/virtualenvs/<hash>, where poetry's own
                # commands cannot work at all:
                #   "Poetry could not find a pyproject.toml file in ... or its
                #    parents"
                # The venv is still what gets ACTIVATED -- only the working
                # directory changes -- so `pip list` and friends behave exactly
                # as before while `poetry show` now has its project.
                _cwd = _proj_dir if _proj_dir and Path(_proj_dir).is_dir() \
                    else _poetry_venv
                return f"cd '{_cwd}' && source '{_pa}'"
            return f"cd '{path}'"
        elif env_type == "conda":
            # Ask the installer where OUR micromamba is, exactly as the
            # Windows branch above already does.
            #
            # N61 (Bayram, 2026-08-22): this branch used to start at
            # shutil.which("micromamba") and then try a handful of hardcoded
            # locations -- none of which was
            #   ~/.local/share/VenvStudio/micromamba/micromamba
            # i.e. the copy VenvStudio downloads and uses for everything else.
            # With micromamba absent from PATH the lookup found nothing, no
            # activation command was produced, and the terminal opened into an
            # unactivated shell where `conda list` and `conda info` naturally
            # failed. Package installs worked the whole time because THAT code
            # asks get_micromamba_exe() -- the same question, asked properly.
            _mamba = ""
            try:
                from src.core.micromamba_installer import get_micromamba_exe
                _exe = get_micromamba_exe()
                if _exe and Path(_exe).exists():
                    _mamba = str(_exe)
            except Exception:
                pass
            if not _mamba:
                _mamba = shutil.which("micromamba") or ""
            _conda = shutil.which("conda") if not _mamba else None
            # Detect mamba from common install paths if still nothing
            if not _mamba and not _conda:
                import os as _os
                for _candidate in (
                    Path.home() / ".local" / "share" / "VenvStudio" / "micromamba" / "micromamba",
                    Path.home() / ".local" / "bin" / "micromamba",
                    Path.home() / "micromamba" / "bin" / "micromamba",
                    Path("/usr/local/bin/micromamba"),
                    Path("/opt/homebrew/bin/micromamba"),
                ):
                    if _candidate.exists():
                        _mamba = str(_candidate)
                        break

            if _mamba:
                import os as _os
                mamba_root = _os.environ.get("MAMBA_ROOT_PREFIX", "")
                if not mamba_root:
                    mamba_root = str(Path(_mamba).parent.parent)
                    if not mamba_root or mamba_root in ("", "."):
                        mamba_root = str(Path.home() / "micromamba")
                # bash/zsh hook → eval → activate
                # Works on Linux, macOS, FreeBSD — any POSIX shell with eval
                return (
                    f"cd '{path}' && "
                    f"export MAMBA_ROOT_PREFIX='{mamba_root}' && "
                    f"eval \"$('{_mamba}' shell hook -s bash)\" && "
                    f"micromamba activate '{path}'"
                )
            elif _conda:
                # Fallback for full conda: try 'conda activate' after sourcing profile
                return (
                    f"cd '{path}' && "
                    f"source \"$(dirname '{_conda}')/../etc/profile.d/conda.sh\" 2>/dev/null && "
                    f"conda activate '{path}' 2>/dev/null || cd '{path}'"
                )
            # Nothing found — just cd
            return f"cd '{path}'"
        else:
            activate = path / "bin" / "activate"
            if activate.exists():
                return f"cd '{path}' && source '{activate}'"
            return f"cd '{path}'"

    try:
        if system == "windows":
            if run_after:
                # First attempt spliced run_after into whatever quoting
                # style _make_cmd_windows happened to produce (cmd.exe,
                # PowerShell -Command, or wt -d ... wrapping either) --
                # wt.exe parses its OWN command line before handing off
                # to the inner shell, and a spliced ';'/'&&' can get
                # misread as wt's tab separator instead of staying
                # inside the inner command (Bayram, 2026-08-14: saw a
                # spurious extra "pip list" tab that failed to launch).
                # Force plain cmd.exe here instead -- single quote pair,
                # no wt/PowerShell nesting, most reliable place to chain
                # a command onto activation. Costs the user's preferred
                # terminal_type for just this feature; "Open Terminal"
                # (no run_after) is completely unaffected.
                cmd = _make_cmd_windows(path, "cmd")
                # hatch/pdm/pixi already bake run_after into their own
                # "run <command>" mode above (instead of "enter shell")
                # -- splicing it in again here would duplicate it.
                if env_type not in ("hatch", "pdm", "pixi"):
                    _sep = "; " if "-Command " in cmd else " && "
                    _stripped = cmd.rstrip()
                    if _stripped.endswith('"'):
                        _idx = len(_stripped) - 1
                        _exec_marker = "&& exec bash"
                        _exec_pos = cmd.rfind(_exec_marker, 0, _idx)
                        if _exec_pos != -1:
                            cmd = cmd[:_exec_pos] + f"&& {run_after} " + cmd[_exec_pos:]
                        else:
                            cmd = cmd[:_idx] + _sep + run_after + cmd[_idx:]
            else:
                cmd = _make_cmd_windows(path, terminal_type)
            subprocess.Popen(cmd, shell=True)

        elif system == "macos":
            posix_cmd = _make_cmd_posix(path)
            # hatch/pdm/pixi already bake run_after into their own
            # "run <command>" mode inside _make_cmd_posix (instead of
            # "enter shell") -- appending it again here would duplicate it.
            if run_after and env_type not in ("hatch", "pdm", "pixi"):
                posix_cmd = f"{posix_cmd} && {run_after}"
            if terminal_type == "iterm2":
                script = (
                    f'tell application "iTerm" to create window with default profile '
                    f'command "cd \'{path}\' && {posix_cmd}"'
                )
            else:
                script = (
                    f'tell application "Terminal" to do script '
                    f'"cd \'{path}\' && {posix_cmd}"'
                )
            subprocess.Popen(["osascript", "-e", script])

        else:  # linux
            posix_cmd = _make_cmd_posix(path)
            # hatch/pdm/pixi already bake run_after into their own
            # "run <command>" mode inside _make_cmd_posix (instead of
            # "enter shell") -- appending it again here would duplicate it.
            if run_after and env_type not in ("hatch", "pdm", "pixi"):
                posix_cmd = f"{posix_cmd} && {run_after}"

            # AppImage bundles override PATH — resolve the real system PATH
            host_path = os.environ.get("PATH", "")
            system_dirs = [
                "/usr/local/bin", "/usr/bin", "/bin",
                "/usr/local/sbin", "/usr/sbin", "/sbin",
                os.path.expanduser("~/.local/bin"),
            ]
            for d in reversed(system_dirs):
                if d not in host_path:
                    host_path = d + ":" + host_path

            system_bash = "/bin/bash"
            for d in ["/usr/bin", "/bin", "/usr/local/bin"]:
                candidate = os.path.join(d, "bash")
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    system_bash = candidate
                    break

            # ── Build an rcfile so shell functions (micromamba, conda activate)
            # remain loaded in the INTERACTIVE bash session.
            # Old approach `{posix_cmd} && exec bash` loses functions defined
            # via `eval $(mamba shell hook -s bash)` because exec starts a new
            # shell that re-reads ~/.bashrc only.
            import tempfile as _tempfile
            _rc_content = (
                "# VenvStudio-generated rcfile (temporary)\n"
                "# Load user's normal init so prompt/aliases work\n"
                "[ -f ~/.bashrc ] && source ~/.bashrc\n"
                "\n"
                "# VenvStudio: activate environment\n"
                f"{posix_cmd}\n"
            )
            _rc_file = _tempfile.NamedTemporaryFile(
                mode="w", suffix=".venvstudio-rc", prefix="vs-",
                delete=False, encoding="utf-8",
            )
            _rc_file.write(_rc_content)
            _rc_file.close()
            _rc_path = _rc_file.name

            # Interactive bash with our rcfile → env activated, prompt shows
            # (env) prefix, functions loaded, Ctrl-D / exit closes the shell.
            bash_cmd = f'{system_bash} --rcfile "{_rc_path}" -i'

            # Schedule rcfile cleanup: add a trap in the rcfile so when the
            # shell exits, the temp file is removed.
            _cleanup_trap = (
                f"\n# Cleanup temp rcfile when shell exits\n"
                f"trap 'rm -f \"{_rc_path}\"' EXIT\n"
            )
            with open(_rc_path, "a", encoding="utf-8") as _f:
                _f.write(_cleanup_trap)

            def _find_terminal(term: str) -> Optional[str]:
                """Find terminal executable, checking system PATH even inside AppImage."""
                # First try normal which
                found = shutil.which(term)
                if found:
                    return found
                # Search system dirs manually (AppImage may hide them)
                for d in system_dirs:
                    candidate = os.path.join(d, term)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                        return candidate
                return None

            def _launch_linux_terminal(term: str) -> bool:
                """Try to launch a specific terminal. Returns True on success."""
                term_exe = _find_terminal(term)
                if not term_exe:
                    return False

                # Clean environment for the child process:
                # Remove AppImage-specific env vars so the terminal behaves normally
                clean_env = os.environ.copy()
                clean_env["PATH"] = host_path
                for appimage_var in ("APPIMAGE", "APPDIR", "OWD",
                                     "ARGV0", "APPIMAGE_EXTRACT_AND_RUN"):
                    clean_env.pop(appimage_var, None)
                # Remove LD_LIBRARY_PATH/LD_PRELOAD that AppImage may set
                # (these can break host terminal apps)
                for ld_var in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
                    clean_env.pop(ld_var, None)

                try:
                    _snew = {"start_new_session": True}
                    if term == "xdg-terminal":
                        # openSUSE: xdg-terminal [command] — pass shell with rcfile
                        subprocess.Popen(
                            [term_exe, f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
                        )
                    elif term == "gnome-terminal":
                        subprocess.Popen(
                            [term_exe, "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term in ("konsole", "yakuake"):
                        subprocess.Popen(
                            [term_exe, "--noclose", "-e", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term in ("xfce4-terminal", "mate-terminal", "cinnamon-terminal", "lxterminal", "tilix"):
                        # These expect a single -e argument with shell+args as string
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
                        )
                    elif term == "kgx":
                        # GNOME Console (openSUSE and others)
                        subprocess.Popen(
                            [term_exe, "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "kitty":
                        subprocess.Popen(
                            [term_exe, system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "alacritty":
                        subprocess.Popen(
                            [term_exe, "-e", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "wezterm":
                        subprocess.Popen(
                            [term_exe, "start", "--", system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    elif term == "foot":
                        subprocess.Popen(
                            [term_exe, system_bash, "--rcfile", _rc_path, "-i"],
                            env=clean_env, **_snew
                        )
                    else:
                        # xterm, x-terminal-emulator and others
                        subprocess.Popen(
                            [term_exe, "-e", f"{system_bash} --rcfile '{_rc_path}' -i"],
                            env=clean_env, **_snew
                        )
                    return True
                except Exception:
                    return False

            # Explicit terminal selected (not "default" or empty)
            if terminal_type and terminal_type not in ("", "default"):
                if _launch_linux_terminal(terminal_type):
                    # B62: this was a bare `return`, so a function annotated
                    # `-> bool` handed back None -- and only on the branch
                    # where the user's CHOSEN terminal succeeded. Callers
                    # written as `if not open_terminal_at(...)` then showed a
                    # "could not open a terminal" warning over a terminal that
                    # had just opened, punishing exactly the people who set
                    # the preference. env_list.py had already worked around it
                    # locally with `if _ok is False` rather than fixing it
                    # here; projects_page.py uses `if not`, so it still shows
                    # the false warning. Fixed at the source.
                    return True

            # Auto-detect: try common terminals in order of preference
            auto_order = [
                # GNOME
                "gnome-terminal",   # Ubuntu, Fedora, Debian GNOME
                "kgx",              # openSUSE GNOME (GNOME Console)
                # KDE
                "konsole",          # KDE Plasma
                "yakuake",          # KDE drop-down
                # XFCE
                "xfce4-terminal",   # XFCE
                # Other DEs
                "mate-terminal",    # MATE
                "lxterminal",       # LXDE
                "tilix",            # GNOME tiling
                "cinnamon-terminal", # Cinnamon (rare, falls through)
                # GPU-accelerated / cross-DE
                "alacritty",
                "kitty",
                "wezterm",
                "foot",             # Wayland-native
                # Fallbacks
                "xterm",
                "x-terminal-emulator",  # Debian alternatives system
                "xdg-terminal",         # openSUSE fallback (requires xdg-terminal-exec)
            ]
            for term in auto_order:
                if _launch_linux_terminal(term):
                    break
        return True
    except Exception as e:
        logging.getLogger("venvstudio.gui.terminal").warning(
            f"⚠️ [Terminal] Could not open terminal: {e}"
        )
        # Report it. Swallowing this is why a broken terminal launch looked
        # like a successful one for three rounds of debugging.
        return False


def get_venv_size(venv_path: Path) -> str:
    """Calculate and return human-readable size of a venv directory."""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(venv_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
    except OSError:
        return "N/A"

    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"


def open_url(url: str) -> tuple[bool, str]:
    """Open a URL in the default web browser — AppImage-safe.

    Inside an AppImage, webbrowser.open() spawns xdg-open/the browser with
    the AppImage-injected environment (LD_LIBRARY_PATH, APPDIR, ...), which
    makes the host browser fail to start silently. Same root cause that
    open_folder() below already handles for file managers.

    Linux + AppImage → spawn an opener with appimage_clean_env().
    Everything else  → plain webbrowser.open() (works fine).

    Returns (success, message).
    """
    if get_platform() not in ("windows", "macos") and os.environ.get("APPIMAGE"):
        clean_env = appimage_clean_env() or os.environ.copy()
        candidates = ("xdg-open", "x-www-browser", "sensible-browser",
                      "firefox", "chromium", "chromium-browser", "google-chrome")
        for tool in candidates:
            exe = shutil.which(tool, path=clean_env.get("PATH"))
            if not exe:
                continue
            try:
                subprocess.Popen(
                    [exe, url], env=clean_env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True, f"Opened {url}"
            except Exception:
                continue
        return False, "No usable browser opener found (AppImage)"
    try:
        import webbrowser
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, f"Could not open URL: {e}"


def open_folder(path) -> tuple[bool, str]:
    """Open a folder in the system file manager.

    Cross-platform:
      - Windows  → explorer.exe "<path>"
      - macOS    → open "<path>"
      - Linux    → xdg-open "<path>"  (falls back to common file managers)
      - FreeBSD  → xdg-open (if available) / falls back like Linux

    If the given path is a file, opens the containing directory (and on Windows
    additionally selects the file).

    Returns (success, message).
    """
    try:
        p = Path(path)
    except Exception as e:
        return False, f"Invalid path: {e}"

    if not p.exists():
        return False, f"Path does not exist: {p}"

    system = get_platform()
    target = p if p.is_dir() else p.parent

    try:
        if system == "windows":
            if p.is_dir():
                # Open the directory itself
                subprocess.Popen(["explorer.exe", str(p)])
            else:
                # Open containing folder with the file selected
                subprocess.Popen(["explorer.exe", "/select,", str(p)])
            return True, f"Opened {target}"

        elif system == "macos":
            if p.is_dir():
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["open", "-R", str(p)])
            return True, f"Opened {target}"

        else:  # linux / bsd
            # Clean AppImage-injected env so the file manager uses the host
            clean_env = os.environ.copy()
            for var in ("APPIMAGE", "APPDIR", "OWD", "ARGV0",
                        "APPIMAGE_EXTRACT_AND_RUN",
                        "LD_LIBRARY_PATH", "LD_PRELOAD"):
                clean_env.pop(var, None)

            # Prefer xdg-open (DE-neutral), then fall back to specific FMs
            candidates = [
                "xdg-open",
                "gio",          # GNOME (used as: gio open <path>)
                "nautilus",     # GNOME
                "dolphin",      # KDE
                "thunar",       # XFCE
                "pcmanfm",      # LXDE
                "nemo",         # Cinnamon
                "caja",         # MATE
                "Thunar",       # openSUSE capitalised variant
                "xdg-open",     # retry (some distros have it in /usr/local/bin)
            ]
            _seen = set()
            for tool in candidates:
                if tool in _seen:
                    continue
                _seen.add(tool)
                exe = shutil.which(tool)
                if not exe:
                    # Also search /usr/bin and /usr/local/bin directly (openSUSE PATH issues)
                    for _d in ("/usr/bin", "/usr/local/bin", "/usr/bin/X11"):
                        _c = os.path.join(_d, tool)
                        if os.path.isfile(_c) and os.access(_c, os.X_OK):
                            exe = _c
                            break
                if not exe:
                    continue
                try:
                    if tool == "gio":
                        subprocess.Popen([exe, "open", str(target)], env=clean_env,
                                         start_new_session=True)
                    else:
                        subprocess.Popen([exe, str(target)], env=clean_env,
                                         start_new_session=True)
                    return True, f"Opened {target} with {tool}"
                except Exception:
                    continue

            return False, ("No file manager found. Install 'xdg-utils' or "
                           "a desktop file manager (nautilus, dolphin, thunar, ...).")

    except Exception as e:
        return False, f"Could not open folder: {e}"
