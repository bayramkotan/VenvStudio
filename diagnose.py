"""
VenvStudio - Windows Tanılama Scripti
======================================
Bu scripti CMD'de çalıştır:
    cd venvstudio
    python diagnose.py

Sonucu kopyalayıp yapıştır.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

print("=" * 60)
print("VenvStudio - Tanılama Raporu")
print("=" * 60)

# 1. Sistem bilgisi
print(f"\n[Sistem]")
print(f"  OS:      {platform.system()} {platform.release()} ({platform.machine()})")
print(f"  Python:  {sys.version}")
print(f"  Exe:     {sys.executable}")
print(f"  CWD:     {os.getcwd()}")

# 2. Proje dosyaları kontrol
print(f"\n[Proje Dosyalari]")
required_files = [
    "main.py",
    "build.py",
    "src/__init__.py",
    "src/gui/__init__.py",
    "src/gui/main_window.py",
    "src/gui/env_dialog.py",
    "src/gui/package_panel.py",
    "src/gui/styles.py",
    "src/core/__init__.py",
    "src/core/venv_manager.py",
    "src/core/pip_manager.py",
    "src/core/config_manager.py",
    "src/utils/__init__.py",
    "src/utils/platform_utils.py",
    "src/utils/constants.py",
]
for f in required_files:
    exists = Path(f).exists()
    status = "OK" if exists else "EKSIK!"
    print(f"  {'✅' if exists else '❌'} {f} -> {status}")

# 3. PySide6 kontrol
print(f"\n[PySide6]")
try:
    import PySide6
    print(f"  ✅ PySide6 {PySide6.__version__}")
    from PySide6.QtWidgets import QApplication
    print(f"  ✅ QtWidgets import OK")
    from PySide6.QtCore import Qt
    print(f"  ✅ QtCore import OK")
except ImportError as e:
    print(f"  ❌ PySide6 HATA: {e}")
except Exception as e:
    print(f"  ❌ PySide6 beklenmeyen hata: {e}")

# 4. src modülleri import test
print(f"\n[src Modulleri Import Testi]")
modules = [
    "src.utils.constants",
    "src.utils.platform_utils",
    "src.core.config_manager",
    "src.core.venv_manager",
    "src.core.pip_manager",
    "src.gui.styles",
    "src.gui.env_dialog",
    "src.gui.package_panel",
    "src.gui.main_window",
]
for mod in modules:
    try:
        __import__(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod} -> {type(e).__name__}: {e}")

# 5. PyInstaller kontrol
print(f"\n[PyInstaller]")
try:
    import PyInstaller
    print(f"  ✅ PyInstaller {PyInstaller.__version__}")
except ImportError:
    print(f"  ❌ PyInstaller yüklü değil")

# 6. dist/ kontrol
print(f"\n[Build Ciktisi]")
dist = Path("dist")
if dist.exists():
    for item in dist.iterdir():
        size_mb = 0
        if item.is_file():
            size_mb = item.stat().st_size / (1024 * 1024)
            print(f"  📦 {item.name} ({size_mb:.1f} MB)")
        elif item.is_dir():
            print(f"  📁 {item.name}/")
            for sub in list(item.iterdir())[:10]:
                if sub.is_file():
                    sub_size = sub.stat().st_size / (1024 * 1024)
                    print(f"      {sub.name} ({sub_size:.1f} MB)")
else:
    print("  ❌ dist/ klasörü yok - build henüz yapılmamış")

# 7. GUI başlatma testi
print(f"\n[GUI Baslama Testi]")
try:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    from src.gui.main_window import MainWindow
    window = MainWindow()
    print(f"  ✅ MainWindow oluşturuldu")
    print(f"  ✅ Pencere boyutu: {window.width()}x{window.height()}")
    # Kapatma - sadece test
    window.close()
    del window
    print(f"  ✅ GUI testi BASARILI")
except Exception as e:
    print(f"  ❌ GUI HATA: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'=' * 60}")
print("Rapor tamamlandi. Bu ciktiyi kopyalayip yapistr.")
print("=" * 60)
