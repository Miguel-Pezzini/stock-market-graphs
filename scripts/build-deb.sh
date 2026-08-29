#!/usr/bin/env bash
# Gera um .deb instalável (sem venv/pip para o usuário final).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')"
ARCH="$(dpkg --print-architecture)"
PKG="stock-desktop"
DEB="${PKG}_${VERSION}_${ARCH}.deb"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

install -d "$STAGE/DEBIAN"
install -d "$STAGE/usr/lib/stock-desktop"
install -d "$STAGE/usr/bin"
install -d "$STAGE/usr/share/applications"
install -d "$STAGE/usr/share/icons/hicolor/scalable/apps"
install -d "$STAGE/usr/share/doc/$PKG"

cp -r src "$STAGE/usr/lib/stock-desktop/"
find "$STAGE/usr/lib/stock-desktop" -depth -type d -name __pycache__ -exec rm -rf {} +
find "$STAGE/usr/lib/stock-desktop" -name '*.pyc' -delete
install -m 755 packaging/stock-desktop.sh "$STAGE/usr/bin/stock-desktop"
install -m 644 packaging/com.stockdesktop.app.desktop "$STAGE/usr/share/applications/"
install -m 644 share/icons/hicolor/scalable/apps/com.stockdesktop.app.svg \
  "$STAGE/usr/share/icons/hicolor/scalable/apps/"
install -m 644 packaging/copyright "$STAGE/usr/share/doc/$PKG/"

sed "s/@VERSION@/$VERSION/" packaging/debian-control > "$STAGE/DEBIAN/control"
install -m 755 packaging/debian-postinst "$STAGE/DEBIAN/postinst"

mkdir -p dist
dpkg-deb --root-owner-group --build "$STAGE" "dist/$DEB"

echo "Pacote gerado: dist/$DEB"
echo "Instalar: sudo apt install ./dist/$DEB"
