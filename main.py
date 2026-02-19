#!/usr/bin/env python3
"""
VenvStudio - Lightweight Python Virtual Environment Manager
A modern, cross-platform virtual environment manager.

Usage:
    python main.py
"""

import sys
import os
import traceback
import multiprocessing

# PyInstaller freeze support — Windows'ta subprocess yeni pencere açmasını engeller
multiprocessing.freeze_support()

# PyInstaller ile paketlendiğinde doğru path'i bul
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    sys.path.insert(0, BASE_DIR)

    # Qt plugin path — PyInstaller bundle içindeki doğru yolu ayarla
    qt_plugin_path = os.path.join(BASE_DIR, "PySide6", "Qt", "plugins")
    if not os.path.isdir(qt_plugin_path):
        qt_plugin_path = os.path.join(BASE_DIR, "PySide6", "plugins")
    if os.path.isdir(qt_plugin_path):
        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path

    # Linux'ta xcb platform plugin sorunları için
    if sys.platform == "linux":
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
        # libxcb-cursor0 yoksa offscreen dene
        platform_dir = os.path.join(qt_plugin_path, "platforms") if os.path.isdir(qt_plugin_path) else ""
        if platform_dir and os.path.isdir(platform_dir):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platform_dir
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler
        from PySide6.QtGui import QFont

        # Suppress noisy QFont::setPointSize warnings (caused by px-based stylesheets)
        def _qt_message_handler(mode, context, message):
            if "QFont::setPointSize" in message:
                return  # suppress
            if mode == QtMsgType.QtWarningMsg:
                print(f"[Qt Warning] {message}")
            elif mode == QtMsgType.QtCriticalMsg:
                print(f"[Qt Critical] {message}")
            elif mode == QtMsgType.QtFatalMsg:
                print(f"[Qt Fatal] {message}")

        qInstallMessageHandler(_qt_message_handler)

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager
        from src.utils.i18n import set_language
        from src.utils.logger import setup_logging

        # Initialize logging
        logger = setup_logging()
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

        # Load language setting before creating UI
        config = ConfigManager()
        lang = config.get("language", "en")
        set_language(lang)
        logger.info(f"Language: {lang}")

        # High DPI support
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("VenvStudio")

        # Set default font
        font = QFont("Segoe UI", 10)
        font.setStyleHint(QFont.SansSerif)
        app.setFont(font)

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        # EXE'de hata olursa göster
        error_msg = f"VenvStudio Başlatma Hatası:\n\n{type(e).__name__}: {e}\n\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)

        # Eğer GUI henüz başlamadıysa, basit bir hata penceresi göster
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "VenvStudio - Hata", error_msg)
        except Exception:
            pass

        # Konsol açıksa kullanıcı okuyabilsin
        if getattr(sys, 'frozen', False):
            input("\nDevam etmek için Enter'a bas...")
        sys.exit(1)


if __name__ == "__main__":
    main()
