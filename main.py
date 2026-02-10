#!/usr/bin/env python3
"""
VenvStudio - Lightweight Python Virtual Environment Manager
A modern, cross-platform alternative to Anaconda.

Usage:
    python main.py
"""

import sys
import os
import traceback

# PyInstaller ile paketlendiğinde doğru path'i bul
if getattr(sys, 'frozen', False):
    # PyInstaller .exe olarak çalışıyor
    # _MEIPASS: --onefile modunda temp dizini
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    sys.path.insert(0, BASE_DIR)
    os.chdir(BASE_DIR)  # CWD'yi de ayarla
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)


def main():
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont

        from src.gui.main_window import MainWindow
        from src.utils.constants import APP_NAME, APP_VERSION
        from src.core.config_manager import ConfigManager
        from src.utils.i18n import set_language

        # Load language setting before creating UI
        config = ConfigManager()
        lang = config.get("language", "en")
        set_language(lang)

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
