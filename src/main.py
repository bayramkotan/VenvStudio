#!/usr/bin/env python3
"""
VenvStudio entry point for PyPI installation.

Usage:
    pip install venvstudio
    venvstudio          # Launch GUI
    venvstudio --help   # CLI help
"""

import sys
import os

# Ensure parent directory is in path
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)


def main():
    """Main entry point — CLI if a subcommand is given, otherwise the GUI."""
    # Import and delegate to the real main
    sys.path.insert(0, _root)

    # ── CLI dispatch: `venvstudio list|create|delete|packages|install|uninstall|version`
    # Runs Qt-free; also works for frozen builds launched with arguments.
    from src.cli import is_cli_invocation, run_cli
    if is_cli_invocation(sys.argv):
        sys.exit(run_cli(sys.argv))

    # Check for CLI flags
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        from src.utils.constants import APP_NAME, APP_VERSION
        print(f"{APP_NAME} v{APP_VERSION}")
        return

    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        from src.utils.constants import APP_NAME, APP_VERSION
        print(f"{APP_NAME} v{APP_VERSION}")
        print(f"Lightweight Python Virtual Environment Manager\n")
        print(f"Usage:")
        print(f"  venvstudio                    Launch GUI")
        print(f"  venvstudio list               List environments")
        print(f"  venvstudio create NAME        Create a venv environment")
        print(f"  venvstudio delete NAME [-y]   Delete an environment")
        print(f"  venvstudio packages ENV       List packages in an environment")
        print(f"  venvstudio install ENV PKG..  Install packages")
        print(f"  venvstudio uninstall ENV PKG. Uninstall packages")
        print(f"  venvstudio version | -V       Show version")
        print(f"  venvstudio -h                 Show this help")
        return

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager
        from src.utils.logger import setup_logging, get_logger

        # ── Logging must be set up before anything else ──
        # Captures crashes during startup, tab switches, env changes, right-clicks, etc.
        log = setup_logging()
        log.info(f"Starting {APP_NAME}")

        # ── Version-based cache invalidation (B187 follow-up) ──
        # On version upgrade, drop the env cache so old buggy entries don't
        # survive into the new version. See src_main.py for the rationale.
        try:
            from src.utils.platform_utils import get_config_dir
            _cfg_dir = get_config_dir()
            _version_marker = _cfg_dir / ".venvstudio_last_version"
            _cache_file = _cfg_dir / "env_cache.json"
            _prev_version = ""
            if _version_marker.exists():
                try:
                    _prev_version = _version_marker.read_text(encoding="utf-8").strip()
                except Exception:
                    _prev_version = ""
            if _prev_version != APP_VERSION:
                if _cache_file.exists():
                    try:
                        _cache_file.unlink()
                        log.info(
                            f"Version change detected ({_prev_version or '<none>'} → {APP_VERSION}) — "
                            f"removed stale cache at {_cache_file}"
                        )
                    except Exception as _ce:
                        log.warning(f"Could not remove stale cache: {_ce}")
                try:
                    _cfg_dir.mkdir(parents=True, exist_ok=True)
                    _version_marker.write_text(APP_VERSION, encoding="utf-8")
                except Exception as _ve:
                    log.warning(f"Could not write version marker: {_ve}")
        except Exception as _e:
            try:
                log.warning(f"Version-based cache invalidation skipped: {_e}")
            except Exception:
                pass

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        config = ConfigManager()
        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure PySide6 is installed: pip install PySide6")
        sys.exit(1)


if __name__ == "__main__":
    main()
