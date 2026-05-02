"""
VenvStudio - Comprehensive Logging & Crash Protection System
=============================================================

Features:
  - Rotating file logs (venvstudio.log, 2 MB × 5 backups)
  - Dedicated crash reports (crash_YYYYMMDD_HHMMSS.log) with full context
  - Global sys.excepthook for unhandled exceptions
  - threading.excepthook for background thread crashes (Python 3.8+)
  - QThread-safe signal/slot error wrapper
  - Subprocess call logger with timeout protection
  - Performance timer context manager
  - Structured session context (OS, Python, Qt, screen info)
  - @safe_slot decorator for Qt slot crash protection
  - Log cleanup (auto-delete crash logs older than 30 days)

Log directory:
  Windows : %APPDATA%/VenvStudio/logs/
  macOS   : ~/Library/Application Support/VenvStudio/logs/
  Linux   : ~/.local/share/VenvStudio/logs/
"""

import functools
import logging
import os
import platform
import subprocess
import sys
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, List, Optional

# ─── Module-level logger (set after setup_logging) ───
_root_logger: Optional[logging.Logger] = None
_log_dir: Optional[Path] = None
_session_id: str = ""


# =====================================================================
#  LOG DIRECTORY
# =====================================================================

def _get_log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    log_dir = base / "VenvStudio" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_dir() -> Path:
    """Public accessor for log directory path."""
    global _log_dir
    if _log_dir is None:
        _log_dir = _get_log_dir()
    return _log_dir


# =====================================================================
#  SESSION CONTEXT — collected once at startup
# =====================================================================

def _collect_session_context() -> dict:
    """Gather system info for crash reports and session header."""
    ctx = {
        "timestamp": datetime.now().isoformat(),
        "platform": sys.platform,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "python_full": sys.version,
        "executable": sys.executable,
        "frozen": getattr(sys, "frozen", False),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }

    # VenvStudio version
    try:
        from src.utils.constants import APP_VERSION
        ctx["app_version"] = APP_VERSION
    except Exception:
        ctx["app_version"] = "unknown"

    # Qt / PySide6 version
    try:
        import PySide6
        from PySide6.QtCore import qVersion
        ctx["pyside6"] = PySide6.__version__
        ctx["qt"] = qVersion()
    except Exception:
        ctx["pyside6"] = "N/A"
        ctx["qt"] = "N/A"

    # Screen info (may fail before QApplication)
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screens = app.screens()
            ctx["screens"] = [
                {
                    "name": s.name(),
                    "geometry": f"{s.geometry().width()}x{s.geometry().height()}",
                    "dpr": s.devicePixelRatio(),
                }
                for s in screens
            ]
        else:
            ctx["screens"] = []
    except Exception:
        ctx["screens"] = []

    return ctx


# =====================================================================
#  SETUP
# =====================================================================

# =====================================================================
#  CONSOLE STYLING — ANSI fallback + banner helpers
# =====================================================================

# ANSI SGR codes
_ANSI = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "italic":  "\033[3m",
    # Foreground
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "gray":    "\033[90m",
    # Bright
    "br_red":     "\033[91m",
    "br_green":   "\033[92m",
    "br_yellow":  "\033[93m",
    "br_blue":    "\033[94m",
    "br_magenta": "\033[95m",
    "br_cyan":    "\033[96m",
}


def _ansi_supported() -> bool:
    """Detect if the current stdout supports ANSI color codes."""
    # Windows 10+ with modern terminals supports ANSI, older cmd.exe doesn't
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    if sys.platform == "win32":
        # Windows Terminal / ANSICON / ConEmu / VSCode terminal → supports
        if os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"):
            return True
        # Try enabling ANSI mode via kernel32
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True


class _AnsiFormatter(logging.Formatter):
    """Colored formatter with level-based coloring for ANSI terminals."""

    LEVEL_COLORS = {
        logging.DEBUG:    _ANSI["gray"],
        logging.INFO:     _ANSI["br_cyan"],
        logging.WARNING:  _ANSI["yellow"],
        logging.ERROR:    _ANSI["br_red"],
        logging.CRITICAL: _ANSI["bold"] + _ANSI["br_red"],
    }

    LEVEL_ICONS = {
        logging.DEBUG:    "·",
        logging.INFO:     "ℹ",
        logging.WARNING:  "⚠",
        logging.ERROR:    "✗",
        logging.CRITICAL: "☠",
    }

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color and _ansi_supported()

    def format(self, record):
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        icon = self.LEVEL_ICONS.get(record.levelno, "·")
        reset = _ANSI["reset"] if self.use_color else ""
        dim = _ANSI["dim"] if self.use_color else ""
        gray = _ANSI["gray"] if self.use_color else ""
        bold = _ANSI["bold"] if self.use_color else ""

        if not self.use_color:
            level_color = ""

        # Shorten the logger name (venvstudio.core.venv_manager → core.venv_manager)
        name = record.name
        if name.startswith("venvstudio."):
            name = name[len("venvstudio."):]

        # Compose: "HH:MM:SS │ icon level │ name  │ message"
        line = (
            f"{gray}{ts}{reset} {dim}│{reset} "
            f"{level_color}{icon} {record.levelname:<7}{reset} {dim}│{reset} "
            f"{bold}{name:<22}{reset} {dim}│{reset} "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def _build_ansi_console_handler() -> logging.Handler:
    """Build a stream handler with the ANSI colored formatter."""
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_AnsiFormatter(use_color=True))
    return ch


# =====================================================================
#  BANNER HELPERS — visually highlight major events
# =====================================================================

def _has_rich() -> bool:
    """Check if Rich is importable."""
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def _visual_width(s: str) -> int:
    """Approximate terminal cell width of `s`.
    Emoji and CJK wide characters = 2 cells, others = 1.
    Invisible joiners (VS16, ZWJ, combining marks) = 0.
    """
    width = 0
    for ch in s:
        cp = ord(ch)
        if cp == 0x200D or 0xFE00 <= cp <= 0xFE0F or 0x0300 <= cp <= 0x036F:
            continue
        if (
            0x1F300 <= cp <= 0x1F64F or
            0x1F680 <= cp <= 0x1F6FF or
            0x1F700 <= cp <= 0x1F77F or
            0x1F780 <= cp <= 0x1F7FF or
            0x1F800 <= cp <= 0x1F8FF or
            0x1F900 <= cp <= 0x1F9FF or
            0x1FA00 <= cp <= 0x1FA6F or
            0x1FA70 <= cp <= 0x1FAFF or
            0x2600  <= cp <= 0x26FF  or
            0x2700  <= cp <= 0x27BF  or
            0x2300  <= cp <= 0x23FF  or
            0x2B00  <= cp <= 0x2BFF  or
            0x3000  <= cp <= 0x303F  or
            0x3040  <= cp <= 0x30FF  or
            0x3400  <= cp <= 0x4DBF  or
            0x4E00  <= cp <= 0x9FFF  or
            0xFF00  <= cp <= 0xFF60  or
            0xFFE0  <= cp <= 0xFFE6
        ):
            width += 2
        else:
            width += 1
    return width


def banner(title: str, style: str = "info", details: Optional[List[str]] = None,
           logger: Optional[logging.Logger] = None) -> None:
    """
    Print a visually distinct banner for major events.

    Styles:
      - "start"    → 🚀 blue/cyan, for operations beginning
      - "success"  → ✅ green, for completed operations
      - "warning"  → ⚠️  yellow
      - "error"    → ❌ red, for failures
      - "info"     → ℹ️  cyan (default)

    `details` is an optional list of bullet points shown under the title.
    If a `logger` is passed, the banner is also recorded at INFO level
    (with ANSI codes stripped for clean log files).

    Cross-platform: uses Rich panel if available, otherwise ANSI box art.
    """
    style_config = {
        "start":   {"color": "br_cyan",    "icon": "🚀", "rich_style": "bold cyan"},
        "success": {"color": "br_green",   "icon": "✅", "rich_style": "bold green"},
        "warning": {"color": "br_yellow",  "icon": "⚠️ ", "rich_style": "bold yellow"},
        "error":   {"color": "br_red",     "icon": "❌", "rich_style": "bold red"},
        "info":    {"color": "br_cyan",    "icon": "ℹ️ ", "rich_style": "cyan"},
    }
    cfg = style_config.get(style, style_config["info"])

    # ── Try Rich panel ──
    if _has_rich():
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text

            content_lines = [Text(f"{cfg['icon']}  {title}", style=cfg["rich_style"])]
            if details:
                for d in details:
                    content_lines.append(Text(f"   • {d}", style="dim"))

            # Combine into a single renderable
            combined = Text()
            for i, line in enumerate(content_lines):
                if i > 0:
                    combined.append("\n")
                combined.append_text(line)

            console = Console(force_terminal=True, color_system="auto")
            panel = Panel(
                combined,
                border_style=cfg["rich_style"],
                padding=(0, 2),
                expand=False,
            )
            console.print(panel)

            if logger:
                logger.info(f"[{style.upper()}] {title}" +
                            (" · " + " · ".join(details) if details else ""))
            return
        except Exception:
            pass  # fall through to ANSI

    # ── ANSI fallback ──
    use_color = _ansi_supported()
    color = _ANSI[cfg["color"]] if use_color else ""
    bold = _ANSI["bold"] if use_color else ""
    dim = _ANSI["dim"] if use_color else ""
    reset = _ANSI["reset"] if use_color else ""

    # Compute box width (at least title + 8, cap at 78)
    lines = [f"{cfg['icon']}  {title}"]
    if details:
        lines.extend(f"   • {d}" for d in details)
    inner_width = min(max(max(_visual_width(line) for line in lines) + 4, 40), 78)

    top = f"{color}{bold}╭{'─' * (inner_width - 2)}╮{reset}"
    bot = f"{color}{bold}╰{'─' * (inner_width - 2)}╯{reset}"
    print(top)
    for i, line in enumerate(lines):
        pad = inner_width - 2 - _visual_width(line) - 2  # - 2 for leading/trailing space
        if pad < 0:
            pad = 0
        if i == 0:
            print(f"{color}{bold}│{reset} {color}{bold}{line}{reset}{' ' * pad} {color}{bold}│{reset}")
        else:
            print(f"{color}│{reset} {dim}{line}{reset}{' ' * pad} {color}│{reset}")
    print(bot)

    if logger:
        logger.info(f"[{style.upper()}] {title}" +
                    (" · " + " · ".join(details) if details else ""))


def banner_start(title: str, details: Optional[List[str]] = None,
                 logger: Optional[logging.Logger] = None) -> None:
    """Convenience: start banner for beginning of an operation."""
    banner(title, "start", details, logger)


def banner_success(title: str, details: Optional[List[str]] = None,
                   logger: Optional[logging.Logger] = None) -> None:
    """Convenience: success banner for completed operation."""
    banner(title, "success", details, logger)


def banner_error(title: str, details: Optional[List[str]] = None,
                 logger: Optional[logging.Logger] = None) -> None:
    """Convenience: error banner for failed operation."""
    banner(title, "error", details, logger)


def banner_warning(title: str, details: Optional[List[str]] = None,
                   logger: Optional[logging.Logger] = None) -> None:
    """Convenience: warning banner."""
    banner(title, "warning", details, logger)


# =====================================================================
#  ORIGINAL SETUP_LOGGING (below, unchanged in structure)
# =====================================================================


def setup_logging() -> logging.Logger:
    """
    Initialize the VenvStudio logging system.

    Call once at application startup (in main.py).
    Returns the root 'venvstudio' logger.

    Sets up:
      - Rotating file handler (venvstudio.log)
      - Optional console handler (VENVSTUDIO_DEBUG=1)
      - sys.excepthook for unhandled exceptions
      - threading.excepthook for background threads (Python 3.8+)
      - Auto-cleanup of old crash logs (>30 days)
    """
    global _root_logger, _log_dir, _session_id

    log_dir = _get_log_dir()
    _log_dir = log_dir

    logger = logging.getLogger("venvstudio")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        _root_logger = logger
        return logger  # Already initialized

    _session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{os.getpid()}"

    # ── Formatter ──
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)-24s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Rotating file handler ──
    fh = RotatingFileHandler(
        log_dir / "venvstudio.log",
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # ── Console handler ──
    # Verbose console output is ON by default when:
    #   1. Running from a terminal (sys.stdout is a TTY), OR
    #   2. VENVSTUDIO_DEBUG env var is set, OR
    #   3. VENVSTUDIO_QUIET is NOT set (user opt-out)
    # This makes every create/delete/config/subprocess event visible in terminal,
    # while packaged GUI EXE (no stdout) stays silent.
    _quiet = os.environ.get("VENVSTUDIO_QUIET", "").lower() in ("1", "true", "yes")
    _has_tty = False
    try:
        _has_tty = bool(sys.stdout and sys.stdout.isatty())
    except Exception:
        _has_tty = False
    _debug_env = bool(os.environ.get("VENVSTUDIO_DEBUG"))

    if (_has_tty or _debug_env) and not _quiet:
        # ── Try Rich first (pretty colors + syntax highlighting + tracebacks) ──
        _console_handler = None
        try:
            from rich.logging import RichHandler
            from rich.console import Console
            _rich_console = Console(
                force_terminal=True,
                color_system="auto",
                stderr=False,
            )
            rh = RichHandler(
                console=_rich_console,
                show_time=True,
                show_level=True,
                show_path=False,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
                omit_repeated_times=False,
            )
            rh.setLevel(logging.DEBUG)
            # Rich handles level/time formatting; we only want the message
            rh.setFormatter(logging.Formatter("%(name)-22s  %(message)s"))
            _console_handler = rh
        except ImportError:
            # ── Fallback: ANSI colored console handler ──
            _console_handler = _build_ansi_console_handler()

        logger.addHandler(_console_handler)

    # ── Session header ──
    ctx = _collect_session_context()
    logger.info("=" * 72)
    logger.info(f"  VenvStudio v{ctx['app_version']} — Session {_session_id}")
    logger.info(f"  OS: {ctx['os']} | Python: {ctx['python']} | Qt: {ctx['qt']} | PySide6: {ctx['pyside6']}")
    logger.info(f"  Frozen: {ctx['frozen']} | PID: {ctx['pid']}")
    if ctx["screens"]:
        for s in ctx["screens"]:
            logger.info(f"  Screen: {s['name']} {s['geometry']} @{s['dpr']}x")
    logger.info("=" * 72)

    _root_logger = logger

    # ── Install crash handlers ──
    _install_sys_excepthook(log_dir, logger)
    _install_threading_excepthook(logger)

    # ── Cleanup old crash logs ──
    _cleanup_old_crash_logs(log_dir, logger, max_age_days=30)

    return logger


# =====================================================================
#  CRASH HANDLERS
# =====================================================================

def _safe_format_exception(exc_type, exc_value, exc_tb) -> str:
    """Format an exception without triggering Python 3.13 + PySide6 6.10.2
    shibokensupport recursion bug.

    Both `traceback.format_exception()` and `traceback.format_tb()` go
    through `_should_show_carets()` → `import ast` → shiboken signature
    loader → recursion. We walk the frames manually instead — that path
    never imports ast and is safe.
    """
    # Always-safe header
    type_name = getattr(exc_type, "__name__", str(exc_type))
    header = f"{type_name}: {exc_value}\n"

    # Walk traceback manually — no format_tb, no carets, no ast import
    if exc_tb is None:
        return header
    try:
        frames = []
        tb = exc_tb
        depth = 0
        while tb is not None and depth < 50:  # cap to prevent infinite tb chain
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            filename = frame.f_code.co_filename
            funcname = frame.f_code.co_name
            frames.append(f'  File "{filename}", line {lineno}, in {funcname}')
            tb = tb.tb_next
            depth += 1
        return "Traceback (most recent call last):\n" + "\n".join(frames) + "\n" + header
    except RecursionError:
        return header + "(traceback walk hit RecursionError)\n"
    except Exception as _fe:
        return header + f"(traceback walk failed: {_fe})\n"


def _install_sys_excepthook(log_dir: Path, logger: logging.Logger):
    """Replace sys.excepthook to catch all unhandled exceptions in the main thread."""

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        crash_msg = _safe_format_exception(exc_type, exc_value, exc_tb)
        logger.critical(f"UNHANDLED EXCEPTION (main thread):\n{crash_msg}")

        _write_crash_report(log_dir, crash_msg, context="main_thread")

        # Show on stderr as well
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = handle_exception


def _install_threading_excepthook(logger: logging.Logger):
    """Catch unhandled exceptions in background threads (Python 3.8+)."""
    if sys.version_info < (3, 8):
        return

    def handle_thread_exception(args):
        if issubclass(args.exc_type, SystemExit):
            return

        crash_msg = _safe_format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )
        thread_name = args.thread.name if args.thread else "unknown"
        logger.critical(
            f"UNHANDLED EXCEPTION (thread: {thread_name}):\n{crash_msg}"
        )

        _write_crash_report(
            get_log_dir(), crash_msg,
            context=f"thread:{thread_name}",
        )

    threading.excepthook = handle_thread_exception


def _write_crash_report(log_dir: Path, crash_msg: str, context: str = ""):
    """Write a dedicated crash report file with full system context."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_file = log_dir / f"crash_{timestamp}.log"

    try:
        ctx = _collect_session_context()
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write("╔══════════════════════════════════════════════════════════════╗\n")
            f.write("║            VenvStudio Crash Report                          ║\n")
            f.write("╚══════════════════════════════════════════════════════════════╝\n\n")
            f.write(f"Time      : {ctx['timestamp']}\n")
            f.write(f"Session   : {_session_id}\n")
            f.write(f"Context   : {context}\n")
            f.write(f"App Ver   : {ctx['app_version']}\n")
            f.write(f"OS        : {ctx['os']}\n")
            f.write(f"Python    : {ctx['python_full']}\n")
            f.write(f"PySide6   : {ctx['pyside6']}\n")
            f.write(f"Qt        : {ctx['qt']}\n")
            f.write(f"Frozen    : {ctx['frozen']}\n")
            f.write(f"PID       : {ctx['pid']}\n")
            f.write(f"CWD       : {ctx['cwd']}\n")
            f.write(f"Executable: {ctx['executable']}\n")
            if ctx["screens"]:
                f.write(f"Screens   : {len(ctx['screens'])}\n")
                for s in ctx["screens"]:
                    f.write(f"            {s['name']} {s['geometry']} @{s['dpr']}x\n")
            f.write("\n" + "─" * 62 + "\n")
            f.write("TRACEBACK:\n")
            f.write("─" * 62 + "\n")
            f.write(crash_msg)
            f.write("\n" + "─" * 62 + "\n")

            # Thread dump
            f.write("\nACTIVE THREADS:\n")
            for t in threading.enumerate():
                daemon_flag = " (daemon)" if t.daemon else ""
                f.write(f"  - {t.name}{daemon_flag} [alive={t.is_alive()}]\n")
    except Exception:
        pass  # Crash handler must never crash


# =====================================================================
#  LOG CLEANUP
# =====================================================================

def _cleanup_old_crash_logs(log_dir: Path, logger: logging.Logger, max_age_days: int = 30):
    """Delete crash_*.log files older than max_age_days."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    count = 0
    try:
        for f in log_dir.glob("crash_*.log"):
            if f.stat().st_mtime < cutoff.timestamp():
                f.unlink()
                count += 1
        if count:
            logger.info(f"Cleaned up {count} old crash log(s) (>{max_age_days} days)")
    except Exception as e:
        logger.debug(f"Crash log cleanup failed: {e}")


# =====================================================================
#  GET LOGGER
# =====================================================================

def get_logger(name: str = "venvstudio") -> logging.Logger:
    """
    Get a child logger.

    Usage in any module:
        from src.utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Something happened")
    """
    return logging.getLogger(name)


# =====================================================================
#  @safe_slot — Qt SLOT CRASH PROTECTION
# =====================================================================

def safe_slot(func: Callable = None, *, fallback=None, log_name: str = ""):
    """
    Decorator for Qt slots that catches exceptions and logs them
    instead of letting Qt silently swallow or crash.

    Usage:
        @safe_slot
        def _on_button_clicked(self):
            ...

        @safe_slot(fallback=None, log_name="package_panel")
        def _on_install_finished(self, success, msg):
            ...
    """
    def decorator(fn):
        _log_name = log_name or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger = get_logger("venvstudio.slot")
                tb = traceback.format_exc()
                logger.error(f"SLOT CRASH in {_log_name}:\n{tb}")

                _write_crash_report(
                    get_log_dir(), tb,
                    context=f"slot:{_log_name}",
                )

                # Try to show error to user (non-blocking)
                try:
                    from PySide6.QtWidgets import QMessageBox, QApplication
                    app = QApplication.instance()
                    if app:
                        QMessageBox.warning(
                            None, "VenvStudio — Internal Error",
                            f"An error occurred in {_log_name}:\n\n"
                            f"{type(e).__name__}: {e}\n\n"
                            f"Details have been logged. The application will try to continue.",
                        )
                except Exception:
                    pass

                return fallback

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


# =====================================================================
#  safe_call — GENERIC EXCEPTION WRAPPER
# =====================================================================

def safe_call(func: Callable, *args, context: str = "", fallback=None, **kwargs):
    """
    Call a function with exception protection.
    Logs any error and returns fallback value instead of crashing.

    Usage:
        result = safe_call(some_risky_function, arg1, arg2, context="loading config")
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_logger("venvstudio.safe_call")
        tb = traceback.format_exc()
        ctx_str = f" ({context})" if context else ""
        logger.error(f"SAFE_CALL failed{ctx_str}: {type(e).__name__}: {e}\n{tb}")
        return fallback


# =====================================================================
#  SUBPROCESS WRAPPER — logged, timeout-protected
# =====================================================================

def logged_subprocess(
    cmd: list,
    *,
    timeout: int = 30,
    context: str = "",
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with logging, timeout protection, and error handling.

    Usage:
        from src.utils.logger import logged_subprocess
        result = logged_subprocess(
            ["pip", "install", "requests"],
            timeout=60,
            context="pip install",
        )

    Returns CompletedProcess on success.
    Raises subprocess.TimeoutExpired or subprocess.CalledProcessError on failure
    (both are logged before re-raising).
    """
    logger = get_logger("venvstudio.subprocess")
    cmd_str = " ".join(str(c) for c in cmd)
    ctx_str = f" [{context}]" if context else ""

    logger.debug(f"SUBPROCESS{ctx_str}: {cmd_str} (timeout={timeout}s)")
    start = time.monotonic()

    # B151: On Windows, add CREATE_NO_WINDOW so subprocesses don't flash a
    # console window. Harmless on Linux/macOS (ignored unless platform-specific).
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", 0x08000000)  # subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            **kwargs,
        )
        elapsed = time.monotonic() - start

        if result.returncode == 0:
            logger.debug(f"SUBPROCESS OK{ctx_str}: {elapsed:.1f}s | rc={result.returncode}")
        else:
            stderr_preview = (result.stderr or "")[:500]
            logger.warning(
                f"SUBPROCESS FAIL{ctx_str}: {elapsed:.1f}s | rc={result.returncode}\n"
                f"  cmd: {cmd_str}\n"
                f"  stderr: {stderr_preview}"
            )

        if check:
            result.check_returncode()

        return result

    except subprocess.TimeoutExpired as e:
        elapsed = time.monotonic() - start
        logger.error(
            f"SUBPROCESS TIMEOUT{ctx_str}: {elapsed:.1f}s (limit={timeout}s)\n"
            f"  cmd: {cmd_str}"
        )
        raise

    except subprocess.CalledProcessError as e:
        elapsed = time.monotonic() - start
        stderr_preview = (e.stderr or "")[:500] if hasattr(e, "stderr") else ""
        logger.error(
            f"SUBPROCESS ERROR{ctx_str}: {elapsed:.1f}s | rc={e.returncode}\n"
            f"  cmd: {cmd_str}\n"
            f"  stderr: {stderr_preview}"
        )
        raise

    except FileNotFoundError:
        logger.error(f"SUBPROCESS NOT FOUND{ctx_str}: {cmd[0]!r} not in PATH")
        raise

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(
            f"SUBPROCESS UNEXPECTED{ctx_str}: {type(e).__name__}: {e}\n"
            f"  cmd: {cmd_str}\n"
            f"  {traceback.format_exc()}"
        )
        raise


# =====================================================================
#  PERFORMANCE TIMER
# =====================================================================

@contextmanager
def log_perf(operation: str, log_name: str = "venvstudio.perf"):
    """
    Context manager to log execution time of a block.

    Usage:
        with log_perf("scan_pythons"):
            result = find_system_pythons()

        with log_perf("create_venv", log_name="venvstudio.core"):
            manager.create_venv(...)
    """
    logger = get_logger(log_name)
    logger.debug(f"PERF START: {operation}")
    start = time.monotonic()
    try:
        yield
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(f"PERF FAIL: {operation} ({elapsed:.3f}s)")
        raise
    else:
        elapsed = time.monotonic() - start
        level = logging.WARNING if elapsed > 5.0 else logging.DEBUG
        logger.log(level, f"PERF END: {operation} ({elapsed:.3f}s)")


# =====================================================================
#  QThread SAFETY MIXIN
# =====================================================================

class SafeWorkerMixin:
    """
    Mixin for QThread workers that adds crash protection to run().

    Usage:
        class MyWorker(QThread, SafeWorkerMixin):
            error_occurred = Signal(str)

            def run(self):
                with self.safe_run("MyWorker"):
                    # actual work here
                    ...

    If an exception escapes the with block, it's logged and
    error_occurred is emitted (if the signal exists).
    """

    @contextmanager
    def safe_run(self, worker_name: str = ""):
        """Context manager that wraps QThread.run() with crash protection."""
        name = worker_name or type(self).__name__
        logger = get_logger(f"venvstudio.worker.{name}")
        logger.debug(f"Worker started: {name}")
        start = time.monotonic()

        try:
            yield
        except Exception as e:
            elapsed = time.monotonic() - start
            tb = traceback.format_exc()
            logger.critical(
                f"WORKER CRASH: {name} ({elapsed:.1f}s)\n{tb}"
            )

            _write_crash_report(
                get_log_dir(), tb,
                context=f"worker:{name}",
            )

            # Emit error signal if available
            if hasattr(self, "error_occurred"):
                try:
                    self.error_occurred.emit(f"{type(e).__name__}: {e}")
                except Exception:
                    pass
        else:
            elapsed = time.monotonic() - start
            logger.debug(f"Worker finished: {name} ({elapsed:.1f}s)")


# =====================================================================
#  OPEN LOG DIRECTORY (for Settings UI)
# =====================================================================

def open_log_directory():
    """Open the log directory in the system file manager."""
    log_dir = get_log_dir()
    try:
        if sys.platform == "win32":
            os.startfile(str(log_dir))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(log_dir)])
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])
    except Exception as e:
        get_logger().warning(f"Could not open log dir: {e}")


def get_recent_crash_logs(max_count: int = 10) -> list[dict]:
    """
    Return recent crash log summaries for display in Settings/About.

    Returns list of dicts: [{"file": "crash_20250315_...", "time": datetime, "size": int}, ...]
    """
    log_dir = get_log_dir()
    crashes = []
    try:
        for f in sorted(log_dir.glob("crash_*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
            crashes.append({
                "file": f.name,
                "path": str(f),
                "time": datetime.fromtimestamp(f.stat().st_mtime),
                "size": f.stat().st_size,
            })
            if len(crashes) >= max_count:
                break
    except Exception:
        pass
    return crashes
