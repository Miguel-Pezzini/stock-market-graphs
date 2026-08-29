#!/usr/bin/env bash
# Instala autostart do Stock Desktop para sessões GNOME/Ubuntu.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
DESKTOP_FILE="$AUTOSTART_DIR/stock-desktop.desktop"
APP_DESKTOP_FILE="$APPLICATIONS_DIR/com.stockdesktop.app.desktop"
ICON_NAME="com.stockdesktop.app"
ICON_FILE="$ICON_DIR/$ICON_NAME.svg"
PYTHON="${PYTHON:-python3}"

mkdir -p "$AUTOSTART_DIR" "$APPLICATIONS_DIR" "$ICON_DIR"
cp "$PROJECT_DIR/assets/app-icon.svg" "$ICON_FILE"

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f "${ICON_DIR%/scalable/apps}" 2>/dev/null || true
fi

write_desktop_file() {
  local target="$1"
  cat > "$target" << EOF
[Desktop Entry]
Type=Application
Name=Stock Desktop
Comment=Dashboard de ações B3 no desktop
Exec=$PYTHON -m src.main
Path=$PROJECT_DIR
Icon=$ICON_NAME
Terminal=false
Categories=Finance;
StartupNotify=false
EOF
}

write_desktop_file "$APP_DESKTOP_FILE"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Stock Desktop
Comment=Dashboard de ações B3 no desktop
Exec=$PYTHON -m src.main
Path=$PROJECT_DIR
Icon=$ICON_NAME
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
Categories=Finance;
StartupNotify=false
X-GNOME-Autostart-Delay=3
EOF

chmod 644 "$DESKTOP_FILE" "$APP_DESKTOP_FILE" "$ICON_FILE"
echo "Autostart instalado em: $DESKTOP_FILE"
echo "Atalho do app instalado em: $APP_DESKTOP_FILE"
echo "Ícone instalado em: $ICON_FILE"
echo "Modo de janela: configure window_mode em ~/.config/stock-desktop/config.json"
