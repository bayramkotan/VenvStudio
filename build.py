#!/usr/bin/env python3
"""
VenvStudio v1.2.0 - Cross-Platform Build Script
================================================
Kullanım:
    python build.py            # Mevcut platform için build
    python build.py --debug    # Konsol açık (hata tespiti)
    python build.py --onedir   # Klasör bazlı build
    python build.py --clean    # Temizlik
    python build.py --ci       # GitHub Actions workflow oluştur
    python build.py --installer # Platform installer scriptleri

Gereksinimler:
    pip install pyinstaller PySide6
    pip install Pillow         # (isteğe bağlı, ikon için)
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path

# Windows'ta emoji/unicode print crash'ini önle
# CI ortamında sys.stdout pipe olabilir — env var ile UTF-8 zorla
import io
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

APP_NAME = "VenvStudio"
APP_VERSION = "1.2.0"
MAIN_SCRIPT = "main.py"
ICON_DIR = Path("assets")

SYSTEM = platform.system().lower()
IS_WINDOWS = SYSTEM == "windows"
IS_MACOS = SYSTEM == "darwin"
IS_LINUX = SYSTEM == "linux"

BUILD_DIR = Path("build")
DIST_DIR = Path("dist")


def get_platform_name():
    return {"windows": "Windows", "darwin": "macOS"}.get(SYSTEM, "Linux")


def check_dependencies():
    print("🔍 Bağımlılıklar kontrol ediliyor...\n")
    for mod, name in [("PyInstaller", "pyinstaller"), ("PySide6", "PySide6")]:
        try:
            m = __import__(mod)
            print(f"  ✅ {mod} {getattr(m, '__version__', '')}")
        except ImportError:
            print(f"  ❌ {mod} bulunamadı! → pip install {name}")
            sys.exit(1)
    print()


def clean_build():
    print("🧹 Temizlik...\n")
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  🗑️  {d}/ silindi")
    for f in Path(".").glob("*.spec"):
        f.unlink()
        print(f"  🗑️  {f} silindi")
    print()


def get_icon_path():
    ICON_DIR.mkdir(exist_ok=True)
    if IS_WINDOWS:
        icon = ICON_DIR / "icon.ico"
    elif IS_MACOS:
        icon = ICON_DIR / "icon.icns"
    else:
        icon = ICON_DIR / "icon.png"

    if icon.exists():
        return str(icon)

    # Try to create icon
    png = ICON_DIR / "icon.png"
    if not png.exists():
        try:
            _create_icon(png)
        except Exception as e:
            print(f"  ⚠️  İkon oluşturulamadı: {e}")

    if IS_WINDOWS and png.exists():
        try:
            _png_to_ico(png, ICON_DIR / "icon.ico")
        except Exception as e:
            print(f"  ⚠️  ICO dönüşüm hatası: {e}")
        if (ICON_DIR / "icon.ico").exists():
            return str(ICON_DIR / "icon.ico")

    if png.exists():
        return str(png)

    print("  ⚠️  İkon bulunamadı, ikonsuz devam ediliyor...")
    return ""


def _create_icon(path):
    """Pillow ile VenvStudio ikonu oluştur."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  ⚠️  Pillow yok, ikon oluşturulamadı (pip install Pillow)")
        return

    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Arka plan
    draw.rounded_rectangle([0, 0, 255, 255], radius=40, fill=(30, 30, 46))

    # Font bul
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font_big = font_sm = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_big = ImageFont.truetype(fp, 80)
                font_sm = ImageFont.truetype(fp, 22)
                break
            except Exception:
                continue
    if not font_big:
        font_big = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    # VS yazısı
    draw.text((128, 55), "VS", fill=(137, 180, 250), font=font_big, anchor="mt")

    # Python yılanı
    draw.text((128, 148), "🐍 venv", fill=(166, 227, 161), font=font_sm, anchor="mt")

    # Progress bar
    draw.rounded_rectangle([48, 185, 208, 191], radius=3, fill=(49, 50, 68))
    draw.rounded_rectangle([48, 185, 158, 191], radius=3, fill=(137, 180, 250))

    # Renkli noktalar
    for cx, color in [(80, (243, 139, 168)), (128, (166, 227, 161)), (176, (249, 226, 175))]:
        draw.ellipse([cx - 8, 210, cx + 8, 226], fill=color)

    img.save(str(path), "PNG")
    print(f"  ✅ İkon oluşturuldu: {path}")


def _png_to_ico(png, ico):
    try:
        from PIL import Image
        img = Image.open(str(png))
        img.save(str(ico), format="ICO",
                 sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"  ✅ ICO: {ico}")
    except Exception as e:
        print(f"  ⚠️  ICO dönüştürme hatası: {e}")


def get_hidden_imports():
    return [
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "src", "src.core", "src.core.config_manager", "src.core.pip_manager",
        "src.core.venv_manager",
        "src.gui", "src.gui.main_window", "src.gui.env_dialog",
        "src.gui.package_panel", "src.gui.settings_page", "src.gui.styles",
        "src.utils", "src.utils.constants", "src.utils.i18n",
        "src.utils.logger", "src.utils.platform_utils",
    ]


def get_excludes():
    return [
        "PySide6.QtWebEngine", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic", "PySide6.Qt3DExtras", "PySide6.Qt3DAnimation",
        "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
        "PySide6.QtLocation", "PySide6.QtSensors", "PySide6.QtSerialPort",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml",
        "PySide6.QtDesigner", "PySide6.QtHelp",
        "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects", "PySide6.QtScxml",
        "PySide6.QtSvg", "PySide6.QtSvgWidgets",
        "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtNetworkAuth",
        "tkinter", "unittest", "email", "html", "http", "xml",
        "pydoc", "doctest", "ftplib", "imaplib", "smtplib", "xmlrpc",
        "turtle", "turtledemo",
    ]


def build_command(one_file=True, debug=False):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME, "--noconfirm", "--clean",
    ]
    if not debug:
        cmd.append("--windowed")
    cmd.append("--onefile" if one_file else "--onedir")

    # Collect src modules
    cmd.extend(["--collect-submodules", "src"])

    # PySide6 — collect only needed submodules, not everything
    cmd.extend(["--collect-submodules", "PySide6.QtCore"])
    cmd.extend(["--collect-submodules", "PySide6.QtGui"])
    cmd.extend(["--collect-submodules", "PySide6.QtWidgets"])

    # Copy Qt plugins (platforms, styles) - critical for windowed mode
    if IS_WINDOWS:
        try:
            import PySide6
            pyside6_dir = os.path.dirname(PySide6.__file__)
            qt_plugins = os.path.join(pyside6_dir, "plugins")
            if os.path.isdir(qt_plugins):
                sep = ";"
                cmd.extend(["--add-data", f"{qt_plugins}{sep}PySide6/plugins"])
        except ImportError:
            pass

    icon = get_icon_path()
    if icon and os.path.isfile(icon):
        cmd.extend(["--icon", icon])

    for imp in get_hidden_imports():
        cmd.extend(["--hidden-import", imp])
    for exc in get_excludes():
        cmd.extend(["--exclude-module", exc])

    sep = ";" if IS_WINDOWS else ":"
    if Path("config").exists():
        cmd.extend(["--add-data", f"config{sep}config"])
    if ICON_DIR.exists():
        cmd.extend(["--add-data", f"assets{sep}assets"])

    if IS_MACOS:
        cmd.extend(["--osx-bundle-identifier", "com.venvstudio.app"])

    cmd.append(MAIN_SCRIPT)
    return cmd


def post_build():
    print("\n" + "=" * 60)
    print(f"✅ BUILD BAŞARILI — {get_platform_name()}")
    print("=" * 60)

    if IS_WINDOWS:
        p = DIST_DIR / f"{APP_NAME}.exe"
        if p.exists():
            print(f"\n  📦 {p}  ({p.stat().st_size / 1024 / 1024:.1f} MB)")
            print(f"  ▶️  .\\dist\\{APP_NAME}.exe")
    elif IS_MACOS:
        p = DIST_DIR / f"{APP_NAME}.app"
        if p.exists():
            print(f"\n  📦 {p}")
            print(f"  ▶️  open {p}")
        else:
            p = DIST_DIR / APP_NAME
            if p.exists():
                print(f"\n  📦 {p}  ({p.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        p = DIST_DIR / APP_NAME
        if p.exists():
            print(f"\n  📦 {p}  ({p.stat().st_size / 1024 / 1024:.1f} MB)")
            print(f"  ▶️  chmod +x {p} && ./{p}")
    print()


def create_desktop_file():
    if not IS_LINUX:
        return
    content = f"""[Desktop Entry]
Name={APP_NAME}
Comment=Python Virtual Environment Manager
Exec={Path.cwd() / DIST_DIR / APP_NAME}
Icon={Path.cwd() / ICON_DIR / 'icon.png' if (ICON_DIR / 'icon.png').exists() else ''}
Terminal=false
Type=Application
Categories=Development;IDE;
"""
    f = DIST_DIR / f"{APP_NAME.lower()}.desktop"
    f.write_text(content)
    os.chmod(f, 0o755)
    print(f"  📝 {f} → cp {f} ~/.local/share/applications/\n")


def create_innosetup():
    if not IS_WINDOWS:
        return
    content = f"""; VenvStudio Inno Setup Script
[Setup]
AppName={APP_NAME}
AppVersion={APP_VERSION}
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputDir=installer
OutputBaseFilename={APP_NAME}_Setup_v{APP_VERSION}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\\{APP_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "vs.py"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "vs.bat"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"

[Run]
Filename: "{{app}}\\{APP_NAME}.exe"; Description: "Launch {APP_NAME}"; Flags: postinstall nowait skipifsilent
"""
    Path("installer.iss").write_text(content, encoding="utf-8")
    print(f"  📝 installer.iss oluşturuldu\n")


def create_ci():
    """GitHub Actions — 3 platform otomatik build + release."""
    d = Path(".github/workflows")
    d.mkdir(parents=True, exist_ok=True)
    content = """name: Build & Release VenvStudio

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install PySide6 pyinstaller Pillow
      - name: Build
        id: build1
        run: python build.py
        continue-on-error: true
      - name: Retry without windowed
        if: steps.build1.outcome == 'failure'
        run: python build.py --debug
      - uses: actions/upload-artifact@v4
        with:
          name: VenvStudio-Windows
          path: dist/VenvStudio.exe
          if-no-files-found: warn

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install PySide6 pyinstaller Pillow
      - name: Build
        run: python build.py
      - uses: actions/upload-artifact@v4
        with:
          name: VenvStudio-macOS
          path: dist/VenvStudio
          if-no-files-found: warn

  build-linux-appimage:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install system deps
        run: |
          sudo apt-get update
          sudo apt-get install -y libxcb-cursor0 libxcb-xinerama0 libegl1 \\
            libxcb-icccm4 libxkbcommon-x11-0 libxcb-keysyms1 libxcb-image0 \\
            libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 libxcb-randr0 \\
            libxcb-sync1 libxcb-shm0 fuse libfuse2

      - name: Install Python deps
        run: |
          pip install PySide6 pyinstaller Pillow

      - name: Build with PyInstaller (onedir for AppImage)
        run: python build.py --onedir

      - name: Create AppImage
        run: |
          # Download linuxdeploy + Qt plugin
          wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
          wget -q https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous/linuxdeploy-plugin-qt-x86_64.AppImage
          chmod +x linuxdeploy*.AppImage

          # Create AppDir structure
          mkdir -p AppDir/usr/bin
          mkdir -p AppDir/usr/share/applications
          mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

          # Copy PyInstaller output
          cp -r dist/VenvStudio/* AppDir/usr/bin/

          # Desktop file
          cat > AppDir/usr/share/applications/venvstudio.desktop << 'DESKTOP'
          [Desktop Entry]
          Name=VenvStudio
          Comment=Python Virtual Environment Manager
          Exec=VenvStudio
          Icon=venvstudio
          Type=Application
          Categories=Development;IDE;
          Keywords=python;venv;virtualenv;
          DESKTOP
          # Fix indentation
          sed -i 's/^          //' AppDir/usr/share/applications/venvstudio.desktop

          # Icon
          if [ -f assets/icon.png ]; then
            cp assets/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/venvstudio.png
            cp assets/icon.png AppDir/venvstudio.png
          fi

          # Desktop file in root too
          cp AppDir/usr/share/applications/venvstudio.desktop AppDir/venvstudio.desktop

          # Build AppImage
          export LDAI_UPDATE_INFORMATION="zsync|https://github.com/${{ github.repository }}/releases/latest/download/VenvStudio-x86_64.AppImage.zsync"
          DEPLOY_GTK_VERSION=3 ./linuxdeploy-x86_64.AppImage \\
            --appdir AppDir \\
            --executable AppDir/usr/bin/VenvStudio \\
            --desktop-file AppDir/usr/share/applications/venvstudio.desktop \\
            --icon-file AppDir/usr/share/icons/hicolor/256x256/apps/venvstudio.png \\
            --output appimage || true

          # Fallback: if linuxdeploy fails, use appimagetool directly
          if ! ls VenvStudio*.AppImage 1>/dev/null 2>&1; then
            echo "linuxdeploy failed, trying appimagetool..."
            wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
            chmod +x appimagetool-x86_64.AppImage

            # AppRun script
            cat > AppDir/AppRun << 'APPRUN'
          #!/bin/bash
          SELF=$(readlink -f "$0")
          HERE=${SELF%/*}
          export PATH="${HERE}/usr/bin:${PATH}"
          export LD_LIBRARY_PATH="${HERE}/usr/bin:${HERE}/usr/lib:${LD_LIBRARY_PATH}"
          export QT_PLUGIN_PATH="${HERE}/usr/bin/PySide6/Qt/plugins"
          export QT_QPA_PLATFORM_PLUGIN_PATH="${HERE}/usr/bin/PySide6/Qt/plugins/platforms"
          exec "${HERE}/usr/bin/VenvStudio" "$@"
          APPRUN
            sed -i 's/^          //' AppDir/AppRun
            chmod +x AppDir/AppRun
            ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir VenvStudio-x86_64.AppImage
          fi

          ls -la *.AppImage 2>/dev/null || echo "No AppImage created"

      - uses: actions/upload-artifact@v4
        with:
          name: VenvStudio-Linux-AppImage
          path: VenvStudio*.AppImage
          if-no-files-found: warn

      # Also upload raw binary as fallback
      - uses: actions/upload-artifact@v4
        with:
          name: VenvStudio-Linux
          path: dist/VenvStudio/VenvStudio
          if-no-files-found: warn

  release:
    needs: [build-windows, build-macos, build-linux-appimage]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')

    steps:
      - uses: actions/download-artifact@v4
        continue-on-error: true

      - name: Prepare files
        continue-on-error: true
        run: |
          ls -laR
          mv VenvStudio-macOS/VenvStudio VenvStudio-macOS/VenvStudio-macOS 2>/dev/null || true

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            VenvStudio-Windows/VenvStudio.exe
            VenvStudio-Linux-AppImage/VenvStudio*.AppImage
            VenvStudio-macOS/VenvStudio-macOS
          generate_release_notes: true
          fail_on_unmatched_files: false
"""
    f = d / "build.yml"
    f.write_text(content)
    print(f"  ✅ {f}")
    return f


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION} Build")
    parser.add_argument("--onedir", action="store_true", help="Klasör bazlı")
    parser.add_argument("--clean", action="store_true", help="Temizlik")
    parser.add_argument("--debug", action="store_true", help="Konsol açık")
    parser.add_argument("--installer", action="store_true", help="Installer scriptleri")
    parser.add_argument("--ci", action="store_true", help="GitHub Actions oluştur")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🐍 {APP_NAME} v{APP_VERSION} — {get_platform_name()} ({platform.machine()})")
    print(f"   Python {platform.python_version()}")
    print(f"{'='*60}\n")

    if args.ci:
        f = create_ci()
        print(f"\n  Sonraki adımlar:")
        print(f"    git add .github/")
        print(f"    git commit -m 'Add CI/CD'")
        print(f"    git push")
        print(f"\n  Release için:")
        print(f"    git tag v{APP_VERSION}")
        print(f"    git push origin v{APP_VERSION}")
        print(f"\n  → Otomatik: Windows .exe + Linux binary + macOS binary")
        print(f"  → GitHub Releases'a yüklenir!\n")
        return

    if args.clean:
        clean_build()
        return

    check_dependencies()
    clean_build()

    cmd = build_command(one_file=not args.onedir, debug=args.debug)
    print(f"🔨 Build başlıyor...\n")

    result = subprocess.run(cmd, cwd=str(Path(__file__).parent))
    if result.returncode != 0:
        print("\n❌ BUILD BAŞARISIZ!")
        sys.exit(1)

    post_build()
    if IS_LINUX:
        create_desktop_file()
    if args.installer:
        create_innosetup()

    print("🎉 Tamamlandı!\n")


if __name__ == "__main__":
    main()
