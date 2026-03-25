#!/usr/bin/env bash
# Usage: ./build_appimage.sh [version]
# Expects: dist/WebP-Converter  (PyInstaller onefile output)
set -euo pipefail

VERSION="${1:-1.0.0}"
VERSION="${VERSION#v}"   # strip leading 'v'
APP="WebP-Converter"
APPDIR="${APP}.AppDir"

# ── AppDir structure ────────────────────────────────────────────────────────
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"

cp "dist/${APP}" "${APPDIR}/usr/bin/webp-converter"
chmod +x "${APPDIR}/usr/bin/webp-converter"

# AppRun entry point
cat > "${APPDIR}/AppRun" << 'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/bin/webp-converter" "$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# Desktop entry (must be in AppDir root)
cat > "${APPDIR}/webp-converter.desktop" << 'DESKTOP'
[Desktop Entry]
Name=WebP Converter
Comment=Convert images to WebP format
Exec=webp-converter
Icon=webp-converter
Type=Application
Categories=Graphics;
Terminal=false
DESKTOP

# Simple icon generated with Pillow (already installed from requirements.txt)
python3 - << 'PYEOF'
from PIL import Image, ImageDraw
SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, SIZE-8, SIZE-8], radius=48, fill=(41, 128, 185))
# White "W" shape
pad, mid, top, bot = 55, SIZE//2, 75, SIZE-65
d.polygon([
    (pad, top), (pad+28, top), (mid, bot-30),
    (SIZE-pad-28, top), (SIZE-pad, top),
    (SIZE-pad, top+10), (mid, bot),
    (pad, top+10),
], fill="white")
img.save("WebP-Converter.AppDir/webp-converter.png")
PYEOF

# ── Download appimagetool ───────────────────────────────────────────────────
wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
     -O appimagetool
chmod +x appimagetool

# ── Build AppImage ──────────────────────────────────────────────────────────
# --appimage-extract-and-run avoids needing FUSE on the build host (CI)
ARCH=x86_64 ./appimagetool --appimage-extract-and-run \
    "${APPDIR}" "${APP}-v${VERSION}-linux.AppImage"

echo "Built: ${APP}-v${VERSION}-linux.AppImage"
