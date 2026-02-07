#!/usr/bin/env python3
"""
VenvStudio - Cross-Platform Build Script
=========================================
Bu script PyInstaller kullanarak VenvStudio'yu paketler:
  - Windows: .exe (tek dosya)
  - macOS:   .app bundle
  - Linux:   tek dosya binary

Kullanım:
    python build.py            # Mevcut platform için build
    python build.py --onefile  # Tek dosya (varsayılan)
    python build.py --onedir   # Klasör bazlı build
    python build.py --clean    # Önceki build dosyalarını temizle

Gereksinimler:
    pip install pyinstaller PySide6
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path


# ── Sabitler ──
APP_NAME = "VenvStudio"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"
ICON_DIR = Path("assets")

# Platform tespiti
SYSTEM = platform.system().lower()
IS_WINDOWS = SYSTEM == "windows"
IS_MACOS = SYSTEM == "darwin"
IS_LINUX = SYSTEM == "linux"

# Build çıktı klasörü
BUILD_DIR = Path("build")
DIST_DIR = Path("dist")


def get_platform_name() -> str:
    if IS_WINDOWS:
        return "Windows"
    elif IS_MACOS:
        return "macOS"
    return "Linux"


def check_dependencies():
    """PyInstaller ve PySide6 yüklü mü kontrol et."""
    print("🔍 Bağımlılıklar kontrol ediliyor...\n")

    # PyInstaller
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  ❌ PyInstaller bulunamadı!")
        print("     Yüklemek için: pip install pyinstaller")
        sys.exit(1)

    # PySide6
    try:
        import PySide6
        print(f"  ✅ PySide6 {PySide6.__version__}")
    except ImportError:
        print("  ❌ PySide6 bulunamadı!")
        print("     Yüklemek için: pip install PySide6")
        sys.exit(1)

    print()


def clean_build():
    """Önceki build dosyalarını temizle."""
    print("🧹 Önceki build dosyaları temizleniyor...\n")

    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  🗑️  {d}/ silindi")

    spec_files = list(Path(".").glob("*.spec"))
    for f in spec_files:
        f.unlink()
        print(f"  🗑️  {f} silindi")

    print()


def get_icon_path() -> str:
    """Platform'a uygun ikon dosyasını bul."""
    if IS_WINDOWS:
        icon = ICON_DIR / "icon.ico"
    elif IS_MACOS:
        icon = ICON_DIR / "icon.icns"
    else:
        icon = ICON_DIR / "icon.png"

    if icon.exists():
        return str(icon)

    print(f"  ⚠️  İkon dosyası bulunamadı: {icon}")
    print(f"      İkonsuz devam ediliyor...\n")
    return ""


def get_hidden_imports() -> list:
    """PySide6 ve src modülleri için gerekli hidden import'lar."""
    return [
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        # VenvStudio src modülleri - bunlar OLMADAN exe çalışmaz!
        "src",
        "src.gui",
        "src.gui.main_window",
        "src.gui.env_dialog",
        "src.gui.package_panel",
        "src.gui.styles",
        "src.core",
        "src.core.venv_manager",
        "src.core.pip_manager",
        "src.core.config_manager",
        "src.utils",
        "src.utils.platform_utils",
        "src.utils.constants",
    ]


def get_excludes() -> list:
    """Paket boyutunu küçültmek için hariç tutulanlar."""
    return [
        # Kullanılmayan Qt modülleri
        "PySide6.QtNetwork",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DAnimation",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtLocation",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtXml",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        # Kullanılmayan standart kütüphaneler
        "tkinter",
        "unittest",
        "email",
        "html",
        "http",
        "xml",
        "pydoc",
        "doctest",
        "ftplib",
        "imaplib",
        "mailbox",
        "smtplib",
        "xmlrpc",
    ]


def build_pyinstaller_command(one_file: bool = True, debug: bool = False) -> list:
    """PyInstaller komutunu oluştur."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconfirm",          # Önceki dist/ üzerine yaz
        "--clean",              # Cache temizle
    ]

    # Debug modunda konsol açık kalır (hataları görmek için)
    if not debug:
        cmd.append("--windowed")    # Konsol penceresi açma (GUI app)

    # Tek dosya mı klasör mü
    if one_file:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # src/ paketini topla - EN ÖNEMLİ KISIM
    cmd.extend(["--collect-submodules", "src"])

    # İkon
    icon = get_icon_path()
    if icon:
        cmd.extend(["--icon", icon])

    # Hidden imports
    for imp in get_hidden_imports():
        cmd.extend(["--hidden-import", imp])

    # Exclude'lar
    for exc in get_excludes():
        cmd.extend(["--exclude-module", exc])

    # Veri dosyaları - config klasörü
    if Path("config").exists():
        sep = ";" if IS_WINDOWS else ":"
        cmd.extend(["--add-data", f"config{sep}config"])

    # Assets klasörü
    if ICON_DIR.exists():
        sep = ";" if IS_WINDOWS else ":"
        cmd.extend(["--add-data", f"assets{sep}assets"])

    # macOS özel ayarlar
    if IS_MACOS:
        cmd.extend([
            "--osx-bundle-identifier", "com.venvstudio.app",
        ])

    # Ana script
    cmd.append(MAIN_SCRIPT)

    return cmd


def post_build_info():
    """Build sonrası bilgi göster."""
    print("\n" + "=" * 60)
    print(f"✅ BUILD BAŞARILI - {get_platform_name()}")
    print("=" * 60)

    if IS_WINDOWS:
        exe_path = DIST_DIR / f"{APP_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n  📦 Çıktı: {exe_path}")
            print(f"  📏 Boyut: {size_mb:.1f} MB")
            print(f"\n  Çalıştırmak için:")
            print(f"    {exe_path}")
        else:
            dir_path = DIST_DIR / APP_NAME
            if dir_path.exists():
                print(f"\n  📦 Çıktı klasörü: {dir_path}/")
                print(f"    Çalıştırmak için: {dir_path / (APP_NAME + '.exe')}")

    elif IS_MACOS:
        app_path = DIST_DIR / f"{APP_NAME}.app"
        if app_path.exists():
            print(f"\n  📦 Çıktı: {app_path}")
            print(f"\n  Çalıştırmak için:")
            print(f"    open {app_path}")
            print(f"\n  Applications'a taşımak için:")
            print(f"    cp -r {app_path} /Applications/")
        else:
            binary = DIST_DIR / APP_NAME
            if binary.exists():
                size_mb = binary.stat().st_size / (1024 * 1024)
                print(f"\n  📦 Çıktı: {binary}")
                print(f"  📏 Boyut: {size_mb:.1f} MB")

    else:  # Linux
        binary = DIST_DIR / APP_NAME
        if binary.exists():
            size_mb = binary.stat().st_size / (1024 * 1024)
            print(f"\n  📦 Çıktı: {binary}")
            print(f"  📏 Boyut: {size_mb:.1f} MB")
            print(f"\n  Çalıştırmak için:")
            print(f"    chmod +x {binary}")
            print(f"    ./{binary}")
            print(f"\n  /usr/local/bin'e kopyalamak için:")
            print(f"    sudo cp {binary} /usr/local/bin/{APP_NAME.lower()}")
        else:
            dir_path = DIST_DIR / APP_NAME
            if dir_path.exists():
                print(f"\n  📦 Çıktı klasörü: {dir_path}/")

    print()


def create_desktop_file():
    """Linux için .desktop dosyası oluştur."""
    if not IS_LINUX:
        return

    desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment=Lightweight Python Virtual Environment Manager
Exec={Path.cwd() / DIST_DIR / APP_NAME}
Icon={Path.cwd() / ICON_DIR / 'icon.png' if (ICON_DIR / 'icon.png').exists() else ''}
Terminal=false
Type=Application
Categories=Development;IDE;
Keywords=python;venv;virtualenv;environment;
"""
    desktop_file = DIST_DIR / f"{APP_NAME.lower()}.desktop"
    with open(desktop_file, "w") as f:
        f.write(desktop_content)
    os.chmod(desktop_file, 0o755)
    print(f"  📝 Desktop dosyası oluşturuldu: {desktop_file}")
    print(f"     Kopyalamak için: cp {desktop_file} ~/.local/share/applications/\n")


def create_innosetup_script():
    """Windows için Inno Setup script oluştur (isteğe bağlı installer)."""
    if not IS_WINDOWS:
        return

    iss_content = f"""; VenvStudio Inno Setup Script
; Inno Setup: https://jrsoftware.org/isinfo.php

[Setup]
AppName={APP_NAME}
AppVersion={APP_VERSION}
AppPublisher=VenvStudio Team
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputDir=installer
OutputBaseFilename={APP_NAME}_Setup_v{APP_VERSION}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\\{APP_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek görevler:"

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "{APP_NAME}'yu başlat"; Flags: postinstall nowait skipifsilent
"""
    iss_file = Path("installer.iss")
    with open(iss_file, "w", encoding="utf-8") as f:
        f.write(iss_content)
    print(f"  📝 Inno Setup script oluşturuldu: {iss_file}")
    print(f"     Windows installer oluşturmak için Inno Setup ile derleyin.\n")


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Build Script")
    parser.add_argument("--onefile", action="store_true", default=True,
                        help="Tek dosya olarak paketle (varsayılan)")
    parser.add_argument("--onedir", action="store_true",
                        help="Klasör bazlı paketle")
    parser.add_argument("--clean", action="store_true",
                        help="Sadece temizlik yap, build yapma")
    parser.add_argument("--installer", action="store_true",
                        help="Platform-spesifik installer scriptleri de oluştur")
    parser.add_argument("--debug", action="store_true",
                        help="Debug modu: konsol açık kalır, hataları görebilirsin")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print(f"🐍 {APP_NAME} v{APP_VERSION} - Build Script")
    print(f"   Platform: {get_platform_name()} ({platform.machine()})")
    print(f"   Python:   {platform.python_version()}")
    print("=" * 60)
    print()

    # Temizlik
    if args.clean:
        clean_build()
        print("✅ Temizlik tamamlandı.")
        return

    # Bağımlılık kontrolü
    check_dependencies()

    # Önceki build'i temizle
    clean_build()

    # Build komutu
    one_file = not args.onedir
    cmd = build_pyinstaller_command(one_file=one_file, debug=args.debug)

    mode_str = 'tek dosya' if one_file else 'klasör'
    if args.debug:
        mode_str += ' + DEBUG (konsol açık)'
    print(f"🔨 Build başlıyor ({mode_str})...\n")
    print(f"   Komut: {' '.join(cmd)}\n")

    # PyInstaller'ı çalıştır
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent))

    if result.returncode != 0:
        print("\n❌ BUILD BAŞARISIZ!")
        print("   PyInstaller hata verdi. Yukarıdaki çıktıyı kontrol edin.")
        sys.exit(1)

    # Post-build
    post_build_info()

    # Platform-spesifik extras
    if IS_LINUX:
        create_desktop_file()

    if args.installer:
        if IS_WINDOWS:
            create_innosetup_script()

    print("🎉 Tamamlandı!\n")


if __name__ == "__main__":
    main()
