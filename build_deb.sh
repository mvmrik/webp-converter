#!/usr/bin/env bash
# Usage: ./build_deb.sh [version]
# Expects:  dist/WebP-Converter  (PyInstaller onefile output)
set -euo pipefail

VERSION="${1:-1.0.0}"
# strip leading 'v' if present (e.g. v1.2.3 → 1.2.3)
VERSION="${VERSION#v}"
ARCH="amd64"
PKG="webp-converter"
BUILD="${PKG}_${VERSION}_${ARCH}"

rm -rf "$BUILD"
mkdir -p "$BUILD/DEBIAN"
mkdir -p "$BUILD/usr/bin"
mkdir -p "$BUILD/usr/share/applications"
mkdir -p "$BUILD/usr/share/pixmaps"

# Binary
cp dist/WebP-Converter "$BUILD/usr/bin/$PKG"
chmod 0755 "$BUILD/usr/bin/$PKG"

# Control file
cat > "$BUILD/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: graphics
Priority: optional
Architecture: $ARCH
Depends: libgtk-3-0 | libgtk-3-0t64, libx11-6, libxcb1
Maintainer: Doorspro <info@doorspro.bg>
Description: WebP Image Converter
 Converts PNG, JPG, JPEG, BMP and TIFF images to WebP format.
 Preserves folder structure, supports transparency and quality settings.
EOF

# Desktop entry
cat > "$BUILD/usr/share/applications/$PKG.desktop" <<EOF
[Desktop Entry]
Name=WebP Converter
Comment=Convert images to WebP format
Exec=/usr/bin/$PKG
Terminal=false
Type=Application
Categories=Graphics;
EOF

dpkg-deb --build "$BUILD"
echo "Built: ${BUILD}.deb"
