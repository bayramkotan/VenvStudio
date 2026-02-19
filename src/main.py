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
    """Main entry point — launches VenvStudio GUI."""
    # Import and delegate to the real main
    sys.path.insert(0, _root)

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
        print(f"  venvstudio          Launch GUI")
        print(f"  venvstudio -V       Show version")
        print(f"  venvstudio -h       Show this help")
        return

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        config = ConfigManager()
        window = MainWindow(config)
        window.show()

        sys.exit(app.exec())
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure PySide6 is installed: pip install PySide6")
        sys.exit(1)


if __name__ == "__main__":
    main()
