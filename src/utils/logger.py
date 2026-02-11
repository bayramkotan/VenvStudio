"""
VenvStudio - Logging System
File-based logging for debugging and error tracking
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from src.utils.platform_utils import get_config_dir


def setup_logging(level=logging.DEBUG) -> logging.Logger:
    """Set up application-wide logging to file and console."""
    log_dir = get_config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Rotate: keep last 5 log files
    log_files = sorted(log_dir.glob("venvstudio_*.log"), reverse=True)
    for old_log in log_files[4:]:
        try:
            old_log.unlink()
        except OSError:
            pass

    log_file = log_dir / f"venvstudio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("VenvStudio")
    logger.setLevel(level)

    # File handler
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler (INFO+)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    logger.info(f"VenvStudio logging started → {log_file}")
    return logger


def get_logger(name: str = "VenvStudio") -> logging.Logger:
    """Get a named child logger."""
    return logging.getLogger(name)


def get_log_dir() -> Path:
    """Return path to log directory."""
    return get_config_dir() / "logs"
