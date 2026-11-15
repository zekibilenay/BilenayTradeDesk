#!/usr/bin/env sh
# Adds Bilenay Trade Desk to your application menu (no root needed). Run it from the extracted folder:
#   ./install-linux.sh            add / update the menu entry
#   ./install-linux.sh --remove   remove it again
# Moved the folder? Run the script again. The app itself needs no installation: ./BilenayTradeDesk starts it.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
FILE="$APPS/bilenay-trade-desk.desktop"

if [ "${1:-}" = "--remove" ]; then
    rm -f "$FILE"
    echo "Removed $FILE"
    exit 0
fi
if [ ! -x "$DIR/BilenayTradeDesk" ]; then
    echo "BilenayTradeDesk was not found next to this script." >&2
    exit 1
fi

mkdir -p "$APPS"
cat > "$FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Bilenay Trade Desk
Comment=Pre-trade checklist, economic calendar and trade journal
Exec="$DIR/BilenayTradeDesk"
Path=$DIR
Icon=$DIR/icon.png
Terminal=false
Categories=Office;Finance;
EOF
chmod 644 "$FILE"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS" >/dev/null 2>&1 || true
fi
echo "Done. Look for \"Bilenay Trade Desk\" in your application menu."
