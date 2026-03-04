"""
VenvStudio - Logging System
Writes logs to AppData/Roaming/VenvStudio/logs/
Also catches unhandled exceptions and crashes.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


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


def setup_logging() -> logging.Logger:
    """
    Set up rotating file logging.
    - venvstudio.log      → current session (rotates at 2MB, keeps 5)
    - crash_YYYYMMDD.log  → only on unhandled exceptions
    """
    log_dir = _get_log_dir()
    logger = logging.getLogger("venvstudio")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # Already set up

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler — venvstudio.log
    fh = RotatingFileHandler(
        log_dir / "venvstudio.log",
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=5,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler (only in debug/dev mode)
    if os.environ.get("VENVSTUDIO_DEBUG"):
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    logger.info(f"=== VenvStudio session started ===")
    logger.info(f"Log dir: {log_dir}")
    logger.info(f"Platform: {sys.platform} | Python: {sys.version}")

    # Install global exception handler — catches crashes
    _install_crash_handler(log_dir, logger)

    return logger


def _install_crash_handler(log_dir: Path, logger: logging.Logger):
    """Catch unhandled exceptions and write crash log."""

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        crash_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        # Write dedicated crash file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = log_dir / f"crash_{timestamp}.log"
        try:
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(f"VenvStudio Crash Report\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write(f"Python: {sys.version}\n")
                f.write("=" * 60 + "\n")
                f.write(crash_msg)
        except Exception:
            pass

        # Also log to main log
        logger.critical(f"UNHANDLED EXCEPTION:\n{crash_msg}")

        # Show original error on stderr
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = handle_exception


def get_logger(name: str = "venvstudio") -> logging.Logger:
    """Get a child logger. Call setup_logging() first."""
    return logging.getLogger(name)
