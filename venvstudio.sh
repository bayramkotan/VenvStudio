#!/bin/bash
# VenvStudio Linux Launcher
# Bu script gerekli ortam değişkenlerini ayarlayıp VenvStudio'yu başlatır.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$SCRIPT_DIR/VenvStudio"

# Qt xcb plugin sorunları için
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR"

# libxcb-cursor0 kontrolü
if ! ldconfig -p 2>/dev/null | grep -q libxcb-cursor; then
    echo ""
    echo "⚠️  libxcb-cursor0 eksik! Qt pencere sistemi çalışmayabilir."
    echo ""
    echo "   Debian/Ubuntu:  sudo apt install libxcb-cursor0"
    echo "   Fedora:         sudo dnf install xcb-util-cursor"
    echo "   Arch:           sudo pacman -S libxcb-cursor"
    echo ""
fi

# Gerekli xcb kütüphaneleri kontrolü
MISSING=""
for lib in libxcb-cursor libxcb-xinerama libxcb-icccm libxkbcommon-x11; do
    if ! ldconfig -p 2>/dev/null | grep -q "$lib"; then
        MISSING="$MISSING $lib"
    fi
done

if [ -n "$MISSING" ]; then
    echo "⚠️  Eksik kütüphaneler:$MISSING"
    echo ""
    echo "   Hepsini yüklemek için:"
    echo "   sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxkbcommon-x11-0 libxcb-keysyms1 libxcb-image0 libxcb-render-util0"
    echo ""
fi

exec "$BINARY" "$@"
