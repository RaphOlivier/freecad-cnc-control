#!/usr/bin/env bash
# Optional: install a FreeCAD AppImage for read-only API inspection (freecadcmd).
# Snap is not available inside dev containers, so the AppImage is the fallback
# recommended in docs/FRAMING.md. The AppImage is ~1 GB and is NOT installed
# automatically at codespace creation; run this script only when needed.
#
# Usage:
#   bash .devcontainer/install-freecad-appimage.sh <URL of the AppImage>
# Get the URL from https://github.com/FreeCAD/FreeCAD/releases
set -euo pipefail
if [ $# -ne 1 ]; then
  echo "usage: $0 <AppImage URL>" >&2
  exit 1
fi
mkdir -p ~/freecad-appimage
cd ~/freecad-appimage
curl -fL -o FreeCAD.AppImage "$1"
chmod +x FreeCAD.AppImage
./FreeCAD.AppImage --appimage-extract > /dev/null
echo "Inspect with: ~/freecad-appimage/squashfs-root/usr/bin/freecadcmd"
